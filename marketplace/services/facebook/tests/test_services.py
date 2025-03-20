import uuid
import random

from unittest.mock import Mock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog
from marketplace.services.facebook.service import (
    FacebookService,
    TemplateService,
    PhotoAPIService,
    PhoneNumbersService,
    CloudProfileService,
    BusinessMetaService,
)


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

    def create_template_message(self, waba_id, name, category, components, language):
        return {"id": "template_id"}

    def get_template_analytics(self, waba_id, fields):
        return {"analytics": "data"}

    def enable_template_insights(self, waba_id):
        return {"success": True}

    def list_template_messages(self, waba_id):
        return {"messages": []}

    def get_template_namespace(self, waba_id):
        return "namespace"

    def update_template_message(self, message_template_id, name, components):
        return {"success": True}

    def delete_template_message(self, waba_id, name):
        return {"success": True}

    def create_upload_session(self, file_length, file_type):
        return "upload_session_id"

    def upload_photo(self, upload_session_id, photo, is_uploading=False):
        return "upload_handle"

    def set_photo(self, photo, phone_number_id):
        return Mock(status_code=200)

    def upload_session(self, upload_session_id, file_type, data):
        return {"h": "mock_upload_handle"}

    def get_phone_numbers(self, waba_id):
        return [{"phone_number": "1234567890"}]

    def get_phone_number(self, phone_number_id):
        return {"phone_number": "1234567890"}

    def get_profile(self):
        return {"profile": "data"}

    def set_profile(self, **kwargs):
        return {"success": True}

    def delete_profile_photo(self):
        return {"success": True}

    def exchange_auth_code_to_token(self, auth_code):
        return {"access_token": "mock_access_token"}

    def get_waba_info(self, fields, user_access_token, waba_id):
        return {
            "on_behalf_of_business_info": {"id": "mock_business_id"},
            "message_template_namespace": "mock_namespace",
        }

    def assign_system_user(self, waba_id, permission):
        return {"success": True}

    def share_credit_line(self, waba_id, waba_currency):
        return {"allocation_config_id": "mock_allocation_id"}

    def subscribe_app(self, waba_id):
        return {"success": True}

    def register_phone_number(self, phone_number_id, user_access_token, data):
        return {"success": True}

    def create_product_feed(self, product_catalog_id, name):
        return {"id": "mock_feed_id"}

    def upload_product_feed(
        self, feed_id, file, file_name, file_content_type, update_only=False
    ):
        return {"id": "upload_id"}

    def get_upload_status_by_feed(self, feed_id, upload_id):
        return True

    def get_uploads_in_progress_by_feed(self, feed_id):
        return "upload_id"

    def create_library_template_message(self, waba_id, template_data):
        """
        Mock method for creating library template messages
        Returns a mock response similar to the Facebook API
        """
        return {
            "id": "0123456789",
            "status": "APPROVED",
            "category": template_data.get("category", "UTILITY"),
        }


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

    def test_create_vtex_catalog(self):
        validated_data = {"name": "Valid Catalog"}
        catalog, fb_catalog_id = self.service.create_vtex_catalog(
            validated_data, self.app, self.app, self.app.created_by
        )
        self.assertIsNotNone(catalog)
        self.assertEqual(fb_catalog_id, MockClient.VALID_CATALOGS_ID[0])

    def test_create_vtex_catalog_failure(self):
        validated_data = {"name": "Invalid Catalog"}
        catalog, fb_catalog_id = self.service.create_vtex_catalog(
            validated_data, self.app, self.app, self.app.created_by
        )
        self.assertIsNone(catalog)
        self.assertIsNone(fb_catalog_id)

    def test_catalog_deletion(self):
        validated_data = {"name": "Valid Catalog"}
        catalog, fb_catalog_id = self.service.create_vtex_catalog(
            validated_data, self.app, self.app, self.app.created_by
        )
        success = self.service.catalog_deletion(catalog)
        self.assertTrue(success)

    def test_catalog_deletion_failure(self):
        self.catalog.facebook_catalog_id = "invalid-id"
        success = self.service.catalog_deletion(self.catalog)
        self.assertFalse(success)

    def test_create_product_feed(self):
        response = self.service.create_product_feed("product_catalog_id", "name")
        self.assertEqual(response, {"id": "mock_feed_id"})

    def test_upload_product_feed(self):
        response = self.service.upload_product_feed(
            "feed_id", "file", "file_name", "file_content_type"
        )
        self.assertEqual(response, {"id": "upload_id"})

    def test_get_upload_status_by_feed(self):
        status = self.service.get_upload_status_by_feed("feed_id", "upload_id")
        self.assertTrue(status)

    def test_get_in_process_uploads_by_feed(self):
        upload_id = self.service.get_in_process_uploads_by_feed("feed_id")
        self.assertEqual(upload_id, "upload_id")

    def test_update_product_feed(self):
        response = self.service.update_product_feed("feed_id", "csv_file", "file_name")
        self.assertEqual(response, "upload_id")

    def test_uploads_in_progress(self):
        upload_id = self.service.uploads_in_progress("feed_id")
        self.assertEqual(upload_id, "upload_id")

    def test_uploads_in_progress_no_uploads(self):
        with patch.object(
            self.mock_client, "get_uploads_in_progress_by_feed", return_value=None
        ):
            upload_id = self.service.uploads_in_progress("feed_id")
            self.assertFalse(upload_id)

    def test_wait_for_upload_completion(self):
        with patch.object(self.service, "get_upload_status_by_feed", return_value=True):
            result = self.service._wait_for_upload_completion("feed_id", "upload_id")
            self.assertTrue(result)

    def test_wait_for_upload_completion_timeout(self):
        with patch.object(
            self.service, "get_upload_status_by_feed", return_value=False
        ):
            with patch("time.sleep", return_value=None):
                result = self.service._wait_for_upload_completion(
                    "feed_id", "upload_id"
                )
                self.assertFalse(result)


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


class TestTemplateService(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="template-test@example.com")
        self.client = MockClient()
        self.service = TemplateService(client=self.client)

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
            config={
                "wa_business_id": "business-id",
                "wa_waba_id": "test_waba_id",
                "wa_phone_number_id": "phone-id",
            },
        )

    def test_create_template_message(self):
        response = self.service.create_template_message(
            "waba_id", "name", "category", ["components"], "language"
        )
        self.assertEqual(response, {"id": "template_id"})

    def test_get_template_analytics(self):
        response = self.service.get_template_analytics("waba_id", {"fields": "value"})
        self.assertEqual(response, {"analytics": "data"})

    def test_enable_template_insights(self):
        response = self.service.enable_template_insights("waba_id")
        self.assertEqual(response, {"success": True})

    def test_list_template_messages(self):
        response = self.service.list_template_messages("waba_id")
        self.assertEqual(response, {"messages": []})

    def test_get_template_namespace(self):
        response = self.service.get_template_namespace("waba_id")
        self.assertEqual(response, "namespace")

    def test_update_template_message(self):
        response = self.service.update_template_message(
            "message_template_id", "name", "components"
        )
        self.assertEqual(response, {"success": True})

    def test_delete_template_message(self):
        response = self.service.delete_template_message("waba_id", "name")
        self.assertEqual(response, {"success": True})


class TestPhotoAPIService(TestCase):
    def setUp(self):
        self.client = MockClient()
        self.service = PhotoAPIService(client=self.client)

    def test_create_upload_session(self):
        response = self.service.create_upload_session(1024, "image/png")
        self.assertEqual(response, "upload_session_id")

    def test_upload_photo(self):
        response = self.service.upload_photo("upload_session_id", "photo_data")
        self.assertEqual(response, "upload_handle")

    def test_set_photo(self):
        response = self.service.set_photo("photo_data", "phone_number_id")
        self.assertEqual(response.status_code, 200)

    def test_upload_session(self):
        response = self.service.upload_session(
            "upload_session_id", "image/png", b"data"
        )
        self.assertEqual(response, {"h": "mock_upload_handle"})


class TestPhoneNumbersService(TestCase):
    def setUp(self):
        self.client = MockClient()
        self.service = PhoneNumbersService(client=self.client)

    def test_get_phone_numbers(self):
        response = self.service.get_phone_numbers("waba_id")
        self.assertEqual(response, [{"phone_number": "1234567890"}])

    def test_get_phone_number(self):
        response = self.service.get_phone_number("phone_number_id")
        self.assertEqual(response, {"phone_number": "1234567890"})


class TestCloudProfileService(TestCase):
    def setUp(self):
        self.client = MockClient()
        self.service = CloudProfileService(client=self.client)

    def test_get_profile(self):
        response = self.service.get_profile()
        self.assertEqual(response, {"profile": "data"})

    def test_set_profile(self):
        response = self.service.set_profile(key="value")
        self.assertEqual(response, {"success": True})

    def test_delete_profile_photo(self):
        response = self.service.delete_profile_photo()
        self.assertEqual(response, {"success": True})


class TestBusinessMetaService(TestCase):
    def setUp(self):
        self.client = MockClient()
        self.service = BusinessMetaService(client=self.client)

    def test_exchange_auth_code_to_token(self):
        response = self.service.exchange_auth_code_to_token("auth_code")
        self.assertEqual(response, {"access_token": "mock_access_token"})

    def test_get_waba_info(self):
        response = self.service.get_waba_info("fields", "user_access_token", "waba_id")
        self.assertEqual(
            response,
            {
                "on_behalf_of_business_info": {"id": "mock_business_id"},
                "message_template_namespace": "mock_namespace",
            },
        )

    def test_assign_system_user(self):
        response = self.service.assign_system_user("waba_id", "permission")
        self.assertEqual(response, {"success": True})

    def test_share_credit_line(self):
        response = self.service.share_credit_line("waba_id", "USD")
        self.assertEqual(response, {"allocation_config_id": "mock_allocation_id"})

    def test_subscribe_app(self):
        response = self.service.subscribe_app("waba_id")
        self.assertEqual(response, {"success": True})

    def test_register_phone_number(self):
        response = self.service.register_phone_number(
            "phone_number_id", "user_access_token", {"key": "value"}
        )
        self.assertEqual(response, {"success": True})

    def test_configure_whatsapp_cloud(self):
        response = self.service.configure_whatsapp_cloud(
            "auth_code", "waba_id", "phone_number_id", "USD"
        )
        self.assertEqual(
            response,
            {
                "user_access_token": "mock_access_token",
                "business_id": "mock_business_id",
                "message_template_namespace": "mock_namespace",
                "allocation_config_id": "mock_allocation_id",
            },
        )
