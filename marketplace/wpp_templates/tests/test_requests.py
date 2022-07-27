from django.test import TestCase
from unittest.mock import patch

from marketplace.core.tests.base import FakeRequestsResponse

from ..requests import TemplateMessageRequest
from marketplace.core.types.channels.whatsapp_base.exceptions import FacebookApiException


class TemplateMessageRequestTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.template_message_request = TemplateMessageRequest("32153243223")

    @patch("requests.post")
    def test_create_template_message_error(self, mock):
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400

        mock.side_effect = [fake_response]

        with self.assertRaises(FacebookApiException):
            self.template_message_request.create_template_message("431332", "teste", "TRANSACTIONAL", list(), "en_US")

    @patch("requests.delete")
    def test_delete_template_message_error(self, mock):
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400

        mock.side_effect = [fake_response]

        with self.assertRaises(FacebookApiException):
            self.template_message_request.delete_template_message("431332", "teste")
