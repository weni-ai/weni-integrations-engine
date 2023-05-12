from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from unittest.mock import MagicMock

from django.test import TestCase

from marketplace.core.tests import FakeRequestsResponse
from ..apis import FacebookConversationAPI
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)


class ConversationTestCase(TestCase):
    ...  # TODO: Implement tests


class FacebookConversationAPITestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.api = FacebookConversationAPI()

    @patch("requests.get")
    def test_requests_ok(self, mock: "MagicMock"):
        mock.return_value = FakeRequestsResponse({"conversation_analytics": {}})
        response = self.api._request()
        self.assertIn("conversation_analytics", response.json())

    @patch("requests.get")
    def test_requests_with_error_response(self, mock: "MagicMock"):
        error_message = "Fake error message"
        mock.return_value = FakeRequestsResponse({"error": {"message": error_message}})

        with self.assertRaisesMessage(FacebookApiException, error_message):
            self.api._request()

    def test_get_fields_method(self):
        fields = self.api._get_fields("123", "321")
        self.assertIn("start(123)", fields)
        self.assertIn("end(321)", fields)
