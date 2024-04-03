from unittest import TestCase
from unittest.mock import patch

from marketplace.core.types.channels.whatsapp_cloud.facades import (
    CloudProfileContactFacade,
    CloudProfileFacade,
)
from marketplace.core.types.channels.whatsapp_cloud.requests import CloudProfileRequest


class CloudProfileFacadeTestCase(TestCase):
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest",
        autospec=True,
    )
    def test_init(self, profile_api_mock):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"

        instance = CloudProfileFacade(access_token, phone_number_id)

        self.assertEqual(instance._profile_api, profile_api_mock.return_value)

        profile_api_mock.assert_called_once_with(access_token, phone_number_id)


class CloudProfileContactFacadeTest(TestCase):
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_init(self, profile_api_mock):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"

        instance = CloudProfileContactFacade(access_token, phone_number_id)

        self.assertEqual(instance._profile_api, profile_api_mock.return_value)

        profile_api_mock.assert_called_once_with(access_token, phone_number_id)

    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_get_profile(self, mock_profile_api):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileContactFacade(access_token, phone_number_id)

        facade.get_profile()
        mock_profile_api.return_value.get_profile.assert_called_once()

    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_set_profile(self, mock_profile_api):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileContactFacade(access_token, phone_number_id)

        data = {"about": "New Status"}
        facade.set_profile(data)
        mock_profile_api.return_value.set_profile.assert_called_once_with(**data)


class CloudProfileRequestTest(TestCase):
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.requests.ProfileHandlerInterface"
    )
    def test_init(self, profile_handler_interface_mock):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"

        instance = CloudProfileRequest(access_token, phone_number_id)

        self.assertEqual(instance._access_token, access_token)
        self.assertEqual(instance._phone_number_id, phone_number_id)


class CloudProfileGetProfile(TestCase):
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.PhotoAPIRequest")
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_get_profile(self, mock_profile_api, mock_photo_api):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileFacade(access_token, phone_number_id)

        mock_profile_api.return_value.get_profile.return_value = {
            "business": {"vertical": "HEALTH"}
        }

        profile = facade.get_profile()

        self.assertEqual(profile["business"]["vertical"], "Medical and Health")
        mock_profile_api.return_value.get_profile.assert_called_once()

    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.PhotoAPIRequest")
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_set_profile_with_non_vertical_business_key(
        self, mock_profile_api, mock_photo_api
    ):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileFacade(access_token, phone_number_id)
        business = {"description": "A test business description"}
        facade.set_profile(business=business)
        mock_profile_api.return_value.set_profile.assert_called_once_with(
            description="A test business description"
        )


class CloudProfileSetProfile(TestCase):
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.PhotoAPIRequest")
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_set_profile(self, mock_profile_api, mock_photo_api):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileFacade(access_token, phone_number_id)

        photo = "photo_data"
        status = "New Status"
        business = {"vertical": "Education"}

        facade.set_profile(photo=photo, status=status, business=business)

        mock_photo_api.return_value.set_photo.assert_called_once_with(
            photo, phone_number_id
        )
        mock_profile_api.return_value.set_profile.assert_called_once_with(
            about=status, vertical="EDU"
        )


class CloudProfileDeleteProfile(TestCase):
    @patch("marketplace.core.types.channels.whatsapp_cloud.facades.CloudProfileRequest")
    def test_delete_profile_photo(self, mock_profile_api):
        access_token = "fake_access_token"
        phone_number_id = "fake_phone_number_id"
        facade = CloudProfileFacade(access_token, phone_number_id)

        try:
            facade.delete_profile_photo()
        except Exception as e:
            self.fail(f"delete_profile_photo raised an exception: {e}")
