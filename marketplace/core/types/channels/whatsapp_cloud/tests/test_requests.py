from django.test import TestCase
from unittest.mock import patch

from marketplace.core.tests.base import FakeRequestsResponse

from ..requests import PhoneNumbersRequest
from ...whatsapp_base.exceptions import FacebookApiException


class PhoneNumbersRequestTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.phone_numbers_request = PhoneNumbersRequest("32153243223")

    @patch("requests.get")
    def test_get_phone_numbers(self, mock):
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400

        success_fake_response = FakeRequestsResponse(data=dict(data=[1, 2]))
        success_fake_response.status_code = 200

        mock.side_effect = [fake_response, fake_response, success_fake_response]

        response = self.phone_numbers_request.get_phone_numbers("431332")

        self.assertEqual(response, [1, 2])

    @patch("requests.get")
    def test_get_phone_numbers_error(self, mock):
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400

        mock.side_effect = [fake_response, fake_response, fake_response]

        with self.assertRaises(FacebookApiException):
            self.phone_numbers_request.get_phone_numbers("431332")
