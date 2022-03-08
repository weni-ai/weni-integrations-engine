from unittest.mock import patch, MagicMock

from django.test import TestCase

from ..facades import request


class RequestTestCase(TestCase):
    @patch("requests.get")
    def test_request_get_is_called(self, mock_get: MagicMock):
        mock_get.return_value = dict(is_called=True)
        response = request("https://weniexample.com", "get")
        self.assertTrue(response.get("is_called"))
