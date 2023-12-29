import uuid
import random

from django.test import TestCase

from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog
from django.contrib.auth import get_user_model

User = get_user_model()


class MockClient:
    VALID_CATALOGS_ID = ["0123456789010", "1123456789011"]

    def enable_catalog(self, waba_id, catalog_id):
        return {"success": True}

    def disable_catalog(self, waba_id, catalog_id):
        return {"success": True}

    def get_connected_catalog(self, waba_id):
        return {
            "data": [
                {
                    "name": "catalogo teste",
                    "vertical": "commerce",
                    "id": "3625585124356927",
                }
            ]
        }

    def toggle_cart(self, wa_phone_number_id, enable=True):
        return {"success": True}

    def toggle_catalog_visibility(self, wa_phone_number_id, make_visible=True):
        return {"success": True}

    def get_wpp_commerce_settings(self, wa_phone_number_id):
        return {
            "data": [
                {
                    "is_cart_enabled": True,
                    "is_catalog_visible": True,
                    "id": "012345678901234",
                }
            ]
        }

    def create_catalog(self, business_id, name):
        if name == "Valid Catalog":
            return {"id": self.VALID_CATALOGS_ID[0]}
        else:
            return None

    def destroy_catalog(self, catalog_id):
        if catalog_id in self.VALID_CATALOGS_ID:
            return True
        else:
            return False


class TestFacebookService(TestCase):
    def generate_unique_facebook_catalog_id(self):
        return "".join(random.choices("0123456789", k=10))

    def setUp(self):
        user, _bool = User.objects.get_or_create(email="user-fbaservice@marketplace.ai")

        self.mock_client = MockClient()
        self.service = FacebookService(client=self.mock_client)
        config = {
            "wa_business_id": "202020202020",
            "wa_waba_id": "10101010",
            "wa_phone_number_id": "0123456789",
        }

        self.app = App.objects.create(
            code="wpp-cloud",
            config=config,
            created_by=user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.catalog = Catalog.objects.create(
            app=self.app,
            facebook_catalog_id=self.generate_unique_facebook_catalog_id(),
            name="catalog test",
            category="commerce",
        )

    def test_get_app_facebook_credentials(self):
        expected_config = {
            "wa_business_id": "202020202020",
            "wa_waba_id": "10101010",
            "wa_phone_number_id": "0123456789",
        }
        credentials = self.service._get_app_facebook_credentials(self.app)
        self.assertEqual(credentials, expected_config)

    def test_enable_catalog(self):
        status, response = self.service.enable_catalog(self.catalog)
        self.assertEqual(response, {"success": True})
        self.assertEqual(True, status)

    def test_disable_catalog(self):
        status, response = self.service.disable_catalog(self.catalog)
        self.assertEqual(response, {"success": True})
        self.assertEqual(True, status)

    def test_get_connected_catalog(self):
        catalog_id = self.service.get_connected_catalog(self.app)
        self.assertEqual(catalog_id, "3625585124356927")

    def test_toggle_cart(self):
        response = self.service.toggle_cart(self.app, enable=True)
        self.assertEqual(response, {"success": True})

    def test_toggle_catalog_visibility(self):
        response = self.service.toggle_catalog_visibility(self.app, visible=True)
        self.assertEqual(response, {"success": True})

    def test_wpp_commerce_settings(self):
        settings = self.service.wpp_commerce_settings(self.app)
        self.assertEqual(settings["data"][0]["is_cart_enabled"], True)
        self.assertEqual(settings["data"][0]["is_catalog_visible"], True)
        self.assertEqual(settings["data"][0]["id"], "012345678901234")

    def test_get_connected_catalog_with_no_data(self):
        original_method = self.mock_client.get_connected_catalog
        self.mock_client.get_connected_catalog = lambda waba_id: {"data": []}

        result = self.service.get_connected_catalog(self.app)
        self.assertEqual(result, [])

        self.mock_client.get_connected_catalog = original_method

    def test_get_app_facebook_credentials_with_missing_values(self):
        self.app.config["wa_business_id"] = None
        self.app.save()
        with self.assertRaises(ValueError) as context:
            self.service._get_app_facebook_credentials(self.app)

        self.assertIn(
            "Not found 'wa_waba_id', 'wa_business_id' or wa_phone_number_id in app.config",
            str(context.exception),
        )

        self.app.config["wa_business_id"] = "202020202020"
        self.app.save()


class TestFacebookCreateDeleteService(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="user@example.com")
        self.mock_client = MockClient()
        self.service = FacebookService(client=self.mock_client)
        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
            config={
                "wa_business_id": "business-id",
                "wa_waba_id": "waba-id",
                "wa_phone_number_id": "phone-id",
            },
        )
        self.vtex_app = App.objects.create(
            code="vtex",
            created_by=self.user,
            project_uuid=self.app.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            configured=True,
        )
        self.catalog = Catalog.objects.create(
            app=self.app,
            facebook_catalog_id=MockClient.VALID_CATALOGS_ID[0],
            name="Test Catalog",
            category="commerce",
        )

    # TODO: resolve error "Key (facebook_catalog_id, app_id)=(0123456789010, 3) already exists." when running tests
    # def test_create_vtex_catalog_success(self):
    #     validated_data = {"name": "Valid Catalog"}
    #     catalog, fb_catalog_id = self.service.create_vtex_catalog(
    #         validated_data, self.app, self.vtex_app, self.user
    #     )
    #     self.assertIsNotNone(catalog)
    #     self.assertEqual(fb_catalog_id, MockClient.VALID_CATALOGS_ID[0])

    # def test_create_vtex_catalog_failure(self):
    #     validated_data = {"name": "Invalid Catalog"}
    #     catalog, fb_catalog_id = self.service.create_vtex_catalog(
    #         validated_data, self.app, self.vtex_app, self.user
    #     )
    #     self.assertIsNone(catalog)
    #     self.assertIsNone(fb_catalog_id)

    # def test_catalog_deletion_success(self):
    #     success = self.service.catalog_deletion(self.catalog)
    #     self.assertTrue(success)

    # def test_catalog_deletion_failure(self):
    #     self.catalog.facebook_catalog_id = "invalid-id"
    #     success = self.service.catalog_deletion(self.catalog)
    #     self.assertFalse(success)
