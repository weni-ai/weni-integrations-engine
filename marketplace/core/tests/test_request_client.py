from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketplace.clients.base import RequestClient
from marketplace.clients.exceptions import CustomAPIException


class RequestClientMetaUsageLoggingTestCase(SimpleTestCase):
    def setUp(self):
        self.client = RequestClient()

    def _response(self, status_code=200, headers=None, payload=None, text=""):
        response = MagicMock()
        response.status_code = status_code
        response.headers = headers or {}
        response.text = text
        response.url = "https://graph.facebook.com/v16.0/me"
        if payload is None:
            response.json.side_effect = ValueError("no json")
        else:
            response.json.return_value = payload
        return response

    @patch("marketplace.clients.base.logger")
    @patch("marketplace.clients.base.requests.request")
    def test_logs_usage_headers_on_success(self, mock_request, mock_logger):
        mock_request.return_value = self._response(
            headers={
                "x-app-usage": '{"call_count": 10}',
                "x-business-use-case-usage": '{"123": [{"call_count": 4}]}',
            }
        )

        self.client.make_request("https://graph.facebook.com/x", "GET")

        mock_logger.info.assert_called()
        extra = mock_logger.info.call_args.kwargs["extra"]
        self.assertEqual(extra["x-app-usage"], {"call_count": 10})
        self.assertEqual(
            extra["x-business-use-case-usage"], {"123": [{"call_count": 4}]}
        )

    @patch("marketplace.clients.base.logger")
    @patch("marketplace.clients.base.requests.request")
    def test_does_not_log_when_usage_headers_absent_on_success(
        self, mock_request, mock_logger
    ):
        mock_request.return_value = self._response(headers={})

        self.client.make_request("https://example.com/x", "GET")

        mock_logger.info.assert_not_called()

    @patch("marketplace.clients.base.logger")
    @patch("marketplace.clients.base.requests.request")
    def test_logs_error_codes_on_400(self, mock_request, mock_logger):
        mock_request.return_value = self._response(
            status_code=400,
            headers={"x-app-usage": '{"call_count": 99}'},
            payload={
                "error": {
                    "code": 4,
                    "error_subcode": 80004,
                    "error_data": {"estimated_time_to_regain_access": 60},
                }
            },
        )

        with self.assertRaises(CustomAPIException):
            self.client.make_request("https://graph.facebook.com/x", "GET")

        mock_logger.warning.assert_called()
        extra = mock_logger.warning.call_args.kwargs["extra"]
        self.assertEqual(extra["error_code"], 4)
        self.assertEqual(extra["error_subcode"], 80004)
        self.assertEqual(extra["estimated_time_to_regain_access"], 60)
        self.assertEqual(extra["x-app-usage"], {"call_count": 99})

    def test_parse_meta_usage_header_falls_back_to_raw_string(self):
        self.assertEqual(self.client._parse_meta_usage_header("not-json"), "not-json")
        self.assertIsNone(self.client._parse_meta_usage_header(None))
