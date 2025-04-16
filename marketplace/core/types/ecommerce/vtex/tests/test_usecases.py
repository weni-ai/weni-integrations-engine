import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import MagicMock

from rest_framework.exceptions import NotFound
from rest_framework.exceptions import APIException

from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)
from marketplace.applications.models import App
from marketplace.services.flows.service import FlowsService
from marketplace.clients.exceptions import CustomAPIException
from marketplace.core.types.ecommerce.vtex.publisher.vtex_app_created_publisher import (
    VtexAppCreatedPublisher,
)
from marketplace.core.types.ecommerce.vtex.usecases.create_vtex_integration import (
    CreateVtexIntegrationUseCase,
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


class CreateVtexIntegrationUseCaseTestCase(TestCase):
    def setUp(self):
        self.flows_service = MagicMock(spec=FlowsService)
        self.publisher = MagicMock(spec=VtexAppCreatedPublisher)

        self.use_case = CreateVtexIntegrationUseCase(self.flows_service, self.publisher)

        self.user = MagicMock()
        self.user.email = "test@example.com"

        self.project_uuid = str(uuid.uuid4())
        self.app = MagicMock(spec=App)
        self.app.project_uuid = self.project_uuid
        self.app.created_by = self.user
        self.app.config = {}

        self.vtex_data = {
            "account": "test-account",
            "store_type": "test-type",
            "project_uuid": self.project_uuid,
        }

    def test_configure_app(self):
        configured_app = self.use_case.configure_app(self.app, self.vtex_data)

        self.assertEqual(configured_app.config["account"], "test-account")
        self.assertEqual(configured_app.config["store_type"], "test-type")
        self.assertEqual(configured_app.config["initial_sync_completed"], False)
        self.assertEqual(configured_app.config["connected_catalog"], False)
        self.assertTrue(configured_app.configured)

        self.app.save.assert_called_once()

    def test_notify_flows_success(self):
        self.flows_service.update_vtex_integration_status.return_value = True

        result = self.use_case.notify_flows(self.app)

        self.assertTrue(result)
        self.flows_service.update_vtex_integration_status.assert_called_once_with(
            self.app.project_uuid, self.app.created_by.email, action="POST"
        )

    def test_notify_flows_failure(self):
        exception = CustomAPIException("Erro ao notificar flows")

        self.flows_service.update_vtex_integration_status.return_value = exception

        result = self.use_case.notify_flows(self.app)

        self.assertEqual(result, exception)
        self.flows_service.update_vtex_integration_status.assert_called_once_with(
            self.app.project_uuid, self.app.created_by.email, action="POST"
        )

    def test_publish_to_queue_success(self):
        self.publisher.create_event.return_value = True

        data = {"key": "value"}

        result = self.use_case.publish_to_queue(data)
        self.assertIsNone(result)
        self.publisher.create_event.assert_called_once_with(data)

    def test_publish_to_queue_failure(self):
        self.publisher.create_event.return_value = False

        data = {"key": "value"}

        with self.assertRaises(APIException) as context:
            self.use_case.publish_to_queue(data)

        self.assertEqual(
            context.exception.detail, {"error": "Failed to publish Vtex app creation."}
        )
        self.publisher.create_event.assert_called_once_with(data)

    def test_integration_flow(self):
        self.flows_service.update_vtex_integration_status.return_value = True
        self.publisher.create_event.return_value = True

        data = {"key": "value"}
        configured_app = self.use_case.configure_app(self.app, self.vtex_data)
        notify_result = self.use_case.notify_flows(configured_app)
        publish_result = self.use_case.publish_to_queue(data)

        self.assertEqual(configured_app, self.app)
        self.assertTrue(notify_result)
        self.assertIsNone(publish_result)
        self.app.save.assert_called_once()
        self.flows_service.update_vtex_integration_status.assert_called_once_with(
            self.app.project_uuid, self.app.created_by.email, action="POST"
        )
        self.publisher.create_event.assert_called_once_with(data)
