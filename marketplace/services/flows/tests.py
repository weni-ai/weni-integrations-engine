import uuid
from django.test import TestCase
from unittest.mock import MagicMock, patch
from marketplace.accounts.backends import User
from marketplace.applications.models import App

from marketplace.services.flows.service import FlowsService
from marketplace.wpp_products.models import Catalog


class FlowsServiceTestCase(TestCase):
    def setUp(self):
        self.client_mock = MagicMock()
        self.flows_service = FlowsService(self.client_mock)

    def test_update_vtex_integration_status(self):
        project_uuid = "123456789"
        user_email = "test@example.com"
        action = "active"

        with patch.object(
            self.client_mock, "update_vtex_integration_status"
        ) as mock_method:
            mock_method.return_value = "Mocked Result"
            result = self.flows_service.update_vtex_integration_status(
                project_uuid, user_email, action
            )

        mock_method.assert_called_once_with(project_uuid, user_email, action)
        self.assertEqual(result, "Mocked Result")

    def test_update_vtex_products(self):
        products = [1, 2, 3]
        flow_object_uuid = "456965858"
        dict_catalog = {"catalog_id": 789}

        with patch.object(self.client_mock, "update_vtex_products") as mock_method:
            mock_method.return_value = "Mocked Result"
            result = self.flows_service.update_vtex_products(
                products, flow_object_uuid, dict_catalog
            )

        mock_method.assert_called_once_with(products, flow_object_uuid, dict_catalog)
        self.assertEqual(result, "Mocked Result")

    def test_update_webhook_vtex_products(self):
        products = [4, 5, 6]
        app_mock = MagicMock()

        user = User.objects.create_superuser(email="user@marketplace.ai")

        app = App.objects.create(
            code="wpp-cloud",
            created_by=user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        catalog1 = Catalog.objects.create(
            app=app,
            facebook_catalog_id="3526987411",
            name="catalog test",
            category="commerce",
        )
        catalog2 = Catalog.objects.create(
            app=app,
            facebook_catalog_id="9876543210",
            name="catalog test",
            category="commerce",
        )
        app_mock.catalogs.all.return_value = [catalog1, catalog2]

        with patch.object(self.client_mock, "update_vtex_products") as mock_method:
            mock_method.return_value = "Mocked Result"
            result = self.flows_service.update_webhook_vtex_products(products, app)

        mock_method.assert_any_call(products, str(app.flow_object_uuid), "3526987411")
        mock_method.assert_any_call(products, str(app.flow_object_uuid), "9876543210")

        self.assertEqual(mock_method.call_count, 2)
        self.assertEqual(result, True)
