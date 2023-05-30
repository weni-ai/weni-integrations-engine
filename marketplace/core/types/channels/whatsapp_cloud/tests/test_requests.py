from django.test import TestCase
from unittest.mock import patch

from marketplace.core.tests.base import FakeRequestsResponse

from ..requests import PhoneNumbersRequest
from ...whatsapp_base.exceptions import FacebookApiException


class MockObjectTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.patch_get = patch("requests.get")
        cls.patch_sleep = patch(
            "marketplace.core.types.channels.whatsapp_cloud.requests.time",
            return_value=None,
        )
        cls.mock_get = cls.patch_get.start()
        cls.mock_sleep = cls.patch_sleep.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_get.stop()
        cls.mock_sleep.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()


class PhoneNumbersRequestTestCase(MockObjectTest):
    def setUp(self):
        super().setUp()
        self.phone_numbers_request = PhoneNumbersRequest("32153243223")
        # Fail response
        self.fail_fake_response = FakeRequestsResponse(data={})
        self.fail_fake_response.status_code = 400
        # Success response
        self.success_fake_response = FakeRequestsResponse(data=dict(data=[1, 2]))
        self.success_fake_response.status_code = 200

    def test_get_phone_numbers(self):
        # There are 3 items in the list because they are simulations of 3 requests
        # 2 failures and 1 success
        self.mock_get.side_effect = [
            self.fail_fake_response,
            self.fail_fake_response,
            self.success_fake_response,
        ]
        response = self.phone_numbers_request.get_phone_numbers("431332")
        self.assertEqual(response, [1, 2])

    def test_get_phone_numbers_error(self):
        # There are 3 items in the list because they are simulations of 3 failures requests
        self.mock_get.side_effect = [
            self.fail_fake_response,
            self.fail_fake_response,
            self.fail_fake_response,
        ]
        with self.assertRaises(FacebookApiException):
            self.phone_numbers_request.get_phone_numbers("431332")
