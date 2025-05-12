import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import Mock, patch

from rest_framework.exceptions import NotFound

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog
from marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand import (
    SyncOnDemandUseCase,
)
from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)


User = get_user_model()


class VtexIntegrationTest(TestCase):
    def setUp(self):
        self.project_uuid = uuid.uuid4()

        self.user = User.objects.create_superuser(
            email="admin@marketplace.ai", password="fake@pass#$"
        )

        self.vtex_app = App.objects.create(
            code="vtex",
            project_uuid=self.project_uuid,
            created_by=self.user,
            config={
                "operator_token": {
                    "app_key": "key123",
                    "app_token": "token123",
                    "domain": "vtex.com",
                }
            },
        )

    def test_get_integration_details_success(self):
        # Test if VTEX integration credentials are returned correctly
        result = VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(result["app_key"], "key123")
        self.assertEqual(result["app_token"], "token123")
        self.assertEqual(result["domain"], "https://vtex.com")

    def test_get_integration_details_not_found(self):
        # Test if the NotFound exception is raised when the App is not found
        invalid_uuid = uuid.uuid4()
        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(invalid_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "A vtex-app integration was not found for the provided project UUID.",
        )

    def test_ensure_https_with_http(self):
        # Test if ensure_https method correctly adds 'https://' to the domain
        domain = "vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, "https://vtex.com")

    def test_ensure_https_already_secure(self):
        # Test if ensure_https method does not modify domains that already start with 'https://'
        domain = "https://vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, domain)

    def test_ensure_https_empty(self):
        # Test if ensure_https method handles None and empty strings correctly
        result = VtexIntegration.ensure_https(None)
        self.assertIsNone(result)

        result = VtexIntegration.ensure_https("")
        self.assertEqual(result, "")

    def test_get_integration_details_operator_token_not_found(self):
        # Test whether the NotFound exception is raised when the operator_token is not found
        # Remove operator_token from App configuration
        self.vtex_app.config.pop("operator_token")
        self.vtex_app.save()

        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "The operator_token was not found for the provided project UUID.",
        )


class SyncOnDemandUseCaseTest(TestCase):
    def setUp(self):
        self.mock_celery_app = Mock()
        self.use_case = SyncOnDemandUseCase(celery_app=self.mock_celery_app)

        self.mock_catalog = Mock(spec=Catalog)
        self.mock_app = Mock(spec=App)
        self.mock_app.vtex_catalogs.first.return_value = self.mock_catalog
        self.mock_app.config = {"celery_queue_name": "test_queue"}
        self.mock_app.uuid = "fake-uuid"

    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._get_vtex_app"
    )
    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._is_product_valid"
    )
    def test_execute_triggers_tasks_for_valid_products(
        self, mock_is_valid, mock_get_app
    ):
        mock_get_app.return_value = self.mock_app
        mock_is_valid.return_value = True

        data = {"seller": "seller1", "sku_ids": ["sku1", "sku2"]}
        flow_uuid = "flow-uuid"

        self.use_case.execute(data, flow_uuid)

        self.assertEqual(self.mock_celery_app.send_task.call_count, 4)
        self.mock_celery_app.send_task.assert_any_call(
            "task_enqueue_webhook",
            kwargs={"app_uuid": "fake-uuid", "seller": "seller1", "sku_id": "sku1"},
            queue="test_queue",
            ignore_result=True,
        )
        self.mock_celery_app.send_task.assert_any_call(
            "task_dequeue_webhooks",
            kwargs={"app_uuid": "fake-uuid", "celery_queue": "test_queue"},
            queue="test_queue",
            ignore_result=True,
        )

    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._get_vtex_app"
    )
    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._is_product_valid"
    )
    def test_execute_raises_validation_error_for_invalid_product(
        self, mock_is_valid, mock_get_app
    ):
        mock_get_app.return_value = self.mock_app
        mock_is_valid.side_effect = [True, False]

        data = {"seller": "seller1", "sku_ids": ["sku1", "sku2"]}
        flow_uuid = "flow-uuid"

        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.use_case.execute(data, flow_uuid)

        self.assertEqual(self.mock_celery_app.send_task.call_count, 2)

    @patch("marketplace.applications.models.App.objects.get")
    def test_get_vtex_app_returns_app(self, mock_get):
        mock_app = Mock()
        mock_get.return_value = mock_app

        result = self.use_case._get_vtex_app("some-uuid")

        mock_get.assert_called_once_with(flow_object_uuid="some-uuid", code="vtex")
        self.assertEqual(result, mock_app)

    @patch("marketplace.applications.models.App.objects.get")
    def test_get_vtex_app_raises_not_found(self, mock_get):
        mock_get.side_effect = App.DoesNotExist

        with self.assertRaises(NotFound) as cm:
            self.use_case._get_vtex_app("some-uuid")

        self.assertIn(
            "No VTEX App configured with the provided flow UUID", str(cm.exception)
        )

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_is_product_valid_returns_true(self, mock_filter):
        mock_filter.return_value.exists.return_value = True

        result = self.use_case._is_product_valid("sku1", "mock_catalog")

        mock_filter.assert_called_once_with(
            sku_id="sku1", is_valid=True, catalog="mock_catalog"
        )
        self.assertTrue(result)

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_is_product_valid_returns_false(self, mock_filter):
        mock_filter.return_value.exists.return_value = False

        result = self.use_case._is_product_valid("sku2", "mock_catalog")

        mock_filter.assert_called_once_with(
            sku_id="sku2", is_valid=True, catalog="mock_catalog"
        )
        self.assertFalse(result)
