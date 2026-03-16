"""
Tests for FacebookClient.get_preverified_numbers (BusinessMetaRequests).
Held under applications.tests so Django test discovery runs them (marketplace.clients is not an app).
"""
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from marketplace.clients.facebook.client import FacebookClient


class FacebookClientGetPreverifiedNumbersTestCase(TestCase):
    """Tests for BusinessMetaRequests.get_preverified_numbers (used via FacebookClient)."""

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456789")
    @patch("marketplace.clients.facebook.client.RequestClient.make_request")
    def test_get_preverified_numbers_calls_meta_with_expected_params(
        self, mock_make_request
    ):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "111", "phone_number": "5511999999999"},
                {"id": "222", "phone_number": "5522988888888"},
            ],
        }
        mock_make_request.return_value = mock_response

        client = FacebookClient(access_token="fake_token")
        result = client.get_preverified_numbers()

        self.assertEqual(result, {"data": mock_response.json.return_value["data"]})
        mock_make_request.assert_called_once()
        call_args, call_kwargs = mock_make_request.call_args
        url = call_args[0]
        self.assertEqual(call_kwargs["method"], "GET")
        self.assertIn("123456789", url)
        self.assertIn("preverified_numbers", url)
        self.assertEqual(call_kwargs["params"]["limit"], 100)
        self.assertEqual(call_kwargs["params"]["code_verification_status"], "VERIFIED")
        self.assertEqual(call_kwargs["params"]["availability_status"], "AVAILABLE")
        self.assertIn("Authorization", call_kwargs["headers"])
        self.assertIn("Content-Type", call_kwargs["headers"])

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="999")
    @patch("marketplace.clients.facebook.client.RequestClient.make_request")
    def test_get_preverified_numbers_returns_empty_data_when_meta_returns_empty(
        self, mock_make_request
    ):
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_make_request.return_value = mock_response

        client = FacebookClient(access_token="fake_token")
        result = client.get_preverified_numbers()

        self.assertEqual(result, {"data": []})
        mock_make_request.assert_called_once()
