from django.test import TestCase
from unittest.mock import MagicMock, Mock, patch

from marketplace.core.tests.base import FakeRequestsResponse

from ..requests import CloudProfileRequest, PhoneNumbersRequest, PhotoAPIRequest
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

    def test_get_phone_number_fail(self):
        fail_response = Mock()
        fail_response.status_code = 400
        fail_response.json.return_value = {"error": "Bad Request"}

        with patch("requests.get") as mock_get:
            mock_get.return_value = fail_response
            with self.assertRaises(FacebookApiException):
                self.phone_numbers_request.get_phone_number("phone_number_id")


class CloudProfileRequestTestCase(MockObjectTest):
    def setUp(self):
        super().setUp()
        self.cloud_profile_request = CloudProfileRequest(
            "fake_access_token", "123456789"
        )

        self.success_profile_response = FakeRequestsResponse(
            data={"data": [{"about": "Test About", "email": "test@example.com"}]}
        )
        self.success_profile_response.status_code = 200

        self.fail_profile_response = FakeRequestsResponse(data={})
        self.fail_profile_response.status_code = 400

    def test_get_profile_success(self):
        self.mock_get.return_value = self.success_profile_response
        profile = self.cloud_profile_request.get_profile()
        self.assertEqual(profile.get("status"), "Test About")
        self.assertEqual(profile.get("email"), "test@example.com")

    def test_set_profile_success(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self.success_profile_response
            try:
                self.cloud_profile_request.set_profile(about="New About")
            except FacebookApiException:
                self.fail("set_profile raised FacebookApiException unexpectedly!")

    def test_set_profile_fail(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self.fail_profile_response
            with self.assertRaises(FacebookApiException):
                self.cloud_profile_request.set_profile(about="New About")


class PhotoAPIRequestTestCase(MockObjectTest):
    def setUp(self):
        super().setUp()
        self.photo_api_request = PhotoAPIRequest("fake_access_token")

        self.mock_photo = MagicMock()
        self.mock_photo.content_type = "image/jpeg"
        self.mock_photo.file.getvalue.return_value = b"photo_data"

        self.success_upload_session_response = FakeRequestsResponse(
            data={"id": "upload_session_id"}
        )
        self.success_upload_session_response.status_code = 200

        self.fail_upload_session_response = FakeRequestsResponse(data={})
        self.fail_upload_session_response.status_code = 400

    def test_create_upload_session_success(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self.success_upload_session_response
            upload_session_id = self.photo_api_request.create_upload_session(
                1000, "image/jpeg"
            )
            self.assertEqual(upload_session_id, "upload_session_id")

    def test_create_upload_session_fail(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self.fail_upload_session_response
            with self.assertRaises(FacebookApiException):
                self.photo_api_request.create_upload_session(1000, "image/jpeg")

    def test_upload_photo_success(self):
        with patch("requests.post") as mock_post:
            success_upload_response = FakeRequestsResponse(data={"h": "handle_value"})
            success_upload_response.status_code = 200
            mock_post.return_value = success_upload_response

            upload_handle = self.photo_api_request.upload_photo(
                "upload_session_id", self.mock_photo
            )
            self.assertEqual(upload_handle, "handle_value")

    def test_upload_photo_fail(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = self.fail_upload_session_response
            with self.assertRaises(FacebookApiException):
                self.photo_api_request.upload_photo(
                    "upload_session_id", self.mock_photo
                )

    def test_set_photo_success(self):
        with patch("requests.post") as mock_post:
            success_set_photo_response = FakeRequestsResponse(data={})
            success_set_photo_response.status_code = 200
            mock_post.return_value = success_set_photo_response

            with patch.object(
                self.photo_api_request,
                "create_upload_session",
                return_value="upload_session_id",
            ), patch.object(
                self.photo_api_request, "upload_photo", return_value="upload_handle"
            ):
                try:
                    self.photo_api_request.set_photo(self.mock_photo, "phone_number_id")
                except FacebookApiException:
                    self.fail("set_photo raised FacebookApiException unexpectedly!")

    def test_set_photo_fail(self):
        with patch("requests.post") as mock_post:
            fail_set_photo_response = FakeRequestsResponse(data={})
            fail_set_photo_response.status_code = 400
            mock_post.return_value = fail_set_photo_response

            with patch.object(
                self.photo_api_request,
                "create_upload_session",
                return_value="upload_session_id",
            ), patch.object(
                self.photo_api_request, "upload_photo", return_value="upload_handle"
            ):
                with self.assertRaises(FacebookApiException):
                    self.photo_api_request.set_photo(self.mock_photo, "phone_number_id")
