from unicodedata import name
from unittest.mock import patch

from django.urls import reverse
from django.utils.crypto import get_random_string
from django.test import override_settings
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import WhatsAppViewSet


class FakeResponse(object):
    def __init__(self, data: dict, error_message: str = None):
        self._data = data
        self.error_message = error_message

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class SharedWabasWhatsAppTestCase(APIBaseTestCase):
    url = reverse("wpp-app-shared-wabas")
    view_class = WhatsAppViewSet

    @override_settings(SYSTEM_USER_ACCESS_TOKEN=get_random_string(32))
    def setUp(self):
        super().setUp()
        self.input_token = get_random_string(32)
        self.set_responses()

    def set_responses(self):
        self.debug_token_response = FakeResponse(
            {
                "data": {
                    "granular_scopes": [
                        {"scope": "business_management", "target_ids": ["1075799863665884"]},
                        {
                            "scope": "whatsapp_business_management",
                            "target_ids": ["1075799863265884", "1072999863265884"],
                        },
                    ]
                }
            }
        )

        self.debug_token_without_business_response = FakeResponse(
            {
                "data": {
                    "granular_scopes": [
                        {"scope": "business_management", "target_ids": ["1075799863665884"]},
                    ]
                }
            }
        )

        error_message = "The access token could not be decrypted"
        self.debug_token_error_response = FakeResponse({"data": {"error": {"message": error_message}}}, error_message)

        self.target_responses = [
            FakeResponse(dict(id="1075799863265884", name="Fake target 1")),
            FakeResponse(dict(id="1072999863265884", name="Fake target 2")),
        ]

    @property
    def view(self):
        return self.view_class.as_view(dict(get="shared_wabas"))

    @patch("requests.get")
    def test_request_ok(self, requests):
        requests.side_effect = [self.debug_token_response] + self.target_responses

        response = self.request.get(self.url + f"?input_token={self.input_token}")
        response_json = response.json
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_json), 2)

        for waba in response_json:
            self.assertTrue(waba.get("id", False))
            self.assertTrue(waba.get("name", False))

    def test_request_without_input_token(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["input_token is a required parameter!"])

    @patch("requests.get")
    def test_request_with_invalid_input_token(self, requests):
        requests.side_effect = [self.debug_token_error_response]
        response = self.request.get(self.url + f"?input_token={self.input_token}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, [self.debug_token_error_response.error_message])

    @patch("requests.get")
    def test_response_without_whatsapp_business_management(self, requests):
        requests.side_effect = [self.debug_token_without_business_response]
        response = self.request.get(self.url + f"?input_token={self.input_token}")
        self.assertEqual(response.json, [])
