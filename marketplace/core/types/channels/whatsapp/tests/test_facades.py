from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from ..facades import request, BaseWhatsAppAPI
from ..type import WhatsAppType


FAKE_URL = "https://wenifakeurl.com"
APP_TYPE = WhatsAppType()


class FakeResponse(object):
    def __init__(self, content: dict = {}):
        self._content = content

    def json(self) -> dict:
        return self._content


class RequestTestCase(TestCase):
    @patch("requests.get")
    def test_request_get_is_called(self, mock_get: MagicMock):
        mock_get.return_value = dict(is_called=True)
        response = request(FAKE_URL, "get")
        self.assertTrue(response.get("is_called"))


class BaseWhatsAppAPITestCase(TestCase):
    def setUp(self):
        super().setUp()

        class FakeWhatsAppAPI(BaseWhatsAppAPI):
            def _get_url(self):
                return FAKE_URL

        self.fake_whatsapp_api = FakeWhatsAppAPI(APP_TYPE)

    def test_declare_class_without_the__get_url_method(self):
        with self.assertRaises(TypeError) as error:

            class FakeWhatsAppAPI(BaseWhatsAppAPI):
                pass

            FakeWhatsAppAPI(APP_TYPE)

    @patch("requests.get")
    def test_request_response_ok(self, mock_get: MagicMock):
        mock_get.return_value = FakeResponse()
        response = self.fake_whatsapp_api._request(self.fake_whatsapp_api._get_url())
        self.assertEqual(response.json(), {})

    @patch("requests.get")
    def test_request_raises_validation_error(self, mock_get: MagicMock):
        error_message = "Fake validation error!"
        mock_get.return_value = FakeResponse({"error": {"message": error_message}})

        with self.assertRaisesMessage(ValidationError, error_message):
            self.fake_whatsapp_api._request(self.fake_whatsapp_api._get_url())
