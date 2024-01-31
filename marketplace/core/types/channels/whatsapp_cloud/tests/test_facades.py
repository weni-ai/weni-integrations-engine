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
