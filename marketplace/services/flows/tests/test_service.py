import uuid
from unittest.mock import MagicMock, Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog
from marketplace.services.flows.service import FlowsService

User = get_user_model()

MOCK_CONFIG = {
    "title": "+55 84 99999-9999",
    "wa_pin": "12345678",
    "wa_number": "+55 84 99999-9999",
    "wa_waba_id": "123456789",
    "wa_currency": "USD",
    "wa_business_id": "202020202020",
    "wa_phone_number_id": "0123456789",
}


class MockFlowsClient:
    def detail_channel(self, flow_object_uuid):
        return {
            "uuid": "f32295af-9596-49f4-807e-235bdd5131f8",
            "name": "Test - Weni",
            "config": MOCK_CONFIG,
            "address": "123456789",
            "org": "518c2683-7be5-4649-9a5c-30c6999a6a97",
            "is_active": True,
        }

    def update_config(self, data, flow_object_uuid):
        mock_response = Mock()
        mock_response.status_code = 200
        return mock_response

    def update_status_catalog(self, flow_object_uuid, fba_catalog_id, is_active):
        mock_response = Mock()
        mock_response.status_code = 200
        return mock_response

    def update_facebook_templates_webhook(
        self, flow_object_uuid, webhook, template_data, template_name
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        return mock_response

    def create_wac_channel(self, user, project_uuid, phone_number_id, config):
        return {"uuid": str(uuid.uuid4())}

    def update_vtex_integration_status(self, project_uuid, user_email, action):
        return "Mocked Result"

    def update_vtex_products(self, products, flow_object_uuid, dict_catalog):
        return "Mocked Result"

    def update_vtex_ads_status(self, app, vtex_ads, action):
        return "Mocked Result"

    def create_channel(self, user_email, project_uuid, data, channeltype_code):
        return {"uuid": str(uuid.uuid4()), "name": "Test Channel"}


class FlowsServiceTestCase(TestCase):
    def setUp(self):
        user, _bool = User.objects.get_or_create(email="user-fbaservice@marketplace.ai")

        self.mock_client = MockFlowsClient()
        self.flows_service = FlowsService(client=self.mock_client)

        self.app = App.objects.create(
            code="wpp-cloud",
            config=MOCK_CONFIG,
            created_by=user,
            project_uuid="518c2683-7be5-4649-9a5c-30c6999a6a97",
            platform=App.PLATFORM_WENI_FLOWS,
        )

    def test_update_vtex_integration_status(self):
        project_uuid = "123456789"
        user_email = "test@example.com"
        action = "active"

        with patch.object(
            self.mock_client, "update_vtex_integration_status"
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

        with patch.object(self.mock_client, "update_vtex_products") as mock_method:
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

        with patch.object(self.mock_client, "update_vtex_products") as mock_method:
            mock_method.return_value = "Mocked Result"
            result = self.flows_service.update_webhook_vtex_products(products, app)

        mock_method.assert_any_call(products, str(app.flow_object_uuid), "3526987411")
        mock_method.assert_any_call(products, str(app.flow_object_uuid), "9876543210")

        self.assertEqual(mock_method.call_count, 2)
        self.assertEqual(result, True)

    def test_update_facebook_templates_webhook(self):
        flow_object_uuid = "456965858"
        webhook = "https://example.com/webhook"
        template_data = {"template": "data"}
        template_name = "template_name"

        with patch.object(
            self.mock_client, "update_facebook_templates_webhook"
        ) as mock_method:
            mock_method.return_value = Mock(status_code=200)
            response = self.flows_service.update_facebook_templates_webhook(
                flow_object_uuid, webhook, template_data, template_name
            )

        mock_method.assert_called_once_with(
            flow_object_uuid, webhook, template_data, template_name
        )
        self.assertEqual(response.status_code, 200)

    def test_update_treshold(self):
        response = self.flows_service.update_treshold(self.app, 3.5)
        self.assertEqual(response, True)

    def test_update_catalog_to_active(self):
        response = self.flows_service.update_catalog_to_active(self.app, "123456789")
        self.assertEqual(response.status_code, 200)

    def test_update_catalog_to_inactive(self):
        response = self.flows_service.update_catalog_to_inactive(self.app, "123456789")
        self.assertEqual(response.status_code, 200)

    def test_create_wac_channel(self):
        user = "user@example.com"
        project_uuid = "123456789"
        phone_number_id = "0123456789"
        config = {"key": "value"}

        with patch.object(self.mock_client, "create_wac_channel") as mock_method:
            mock_method.return_value = {"uuid": "mock_uuid"}
            result = self.flows_service.create_wac_channel(
                user, project_uuid, phone_number_id, config
            )

        mock_method.assert_called_once_with(user, project_uuid, phone_number_id, config)
        self.assertEqual(result, {"uuid": "mock_uuid"})

    def test_update_vtex_ads_status(self):
        vtex_ads = True
        action = "active"

        with patch.object(self.mock_client, "update_vtex_ads_status") as mock_method:
            mock_method.return_value = "Mocked Result"
            result = self.flows_service.update_vtex_ads_status(
                self.app, vtex_ads, action
            )

        mock_method.assert_called_once_with(
            self.app.project_uuid, self.app.created_by.email, action, vtex_ads
        )
        self.assertEqual(result, "Mocked Result")

    def test_create_channel(self):
        """
        Test to verify that the create_channel method correctly delegates
        the call to the client and returns the expected result.
        """
        user_email = "test@example.com"
        project_uuid = "123456789"
        data = {"key": "value"}
        channeltype_code = "email"

        # Patch the create_channel method of the mock_client
        with patch.object(self.mock_client, "create_channel") as mock_method:
            mock_method.return_value = {"uuid": "mock_uuid", "name": "Test Channel"}

            # Call the create_channel method of the FlowsService
            result = self.flows_service.create_channel(
                user_email=user_email,
                project_uuid=project_uuid,
                data=data,
                channeltype_code=channeltype_code,
            )

        # Verify that the mock client's create_channel was called with the correct parameters
        mock_method.assert_called_once_with(
            user_email, project_uuid, data, channeltype_code
        )

        # Assert that the result matches the mock return value
        self.assertEqual(result, {"uuid": "mock_uuid", "name": "Test Channel"})
