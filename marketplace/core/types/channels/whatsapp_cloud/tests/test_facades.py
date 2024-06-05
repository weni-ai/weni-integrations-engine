from unittest import TestCase
from unittest.mock import Mock, patch

from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import PhotoAPIService, CloudProfileService
from marketplace.core.types.channels.whatsapp_cloud.facades import (
    CloudProfileContactFacade,
    CloudProfileFacade,
)


class MockPhotoAPIRequests:
    def __init__(self):
        self.set_photo = Mock()

    def create_upload_session(self, file_length: int, file_type: str) -> str:
        return "mock_upload_session_id"

    def upload_photo(
        self, upload_session_id: str, photo: str, is_uploading: bool = False
    ) -> str:
        return "mock_upload_handle"

    def get_url(self) -> str:
        return "http://mock.url"


class CloudProfileFacadeTestCase(TestCase):
    def setUp(self):
        self.access_token = "fake_access_token"
        self.phone_number_id = "fake_phone_number_id"

        self.mock_facebook_client = Mock(spec=FacebookClient)
        self.mock_profile_service = Mock(spec=CloudProfileService)
        self.mock_photo_api_requests = MockPhotoAPIRequests()

        with patch(
            "marketplace.clients.facebook.client.FacebookClient",
            return_value=self.mock_facebook_client,
        ):
            with patch.object(
                FacebookClient,
                "get_profile_requests",
                return_value=self.mock_profile_service,
            ):
                self.facade = CloudProfileFacade(
                    self.access_token, self.phone_number_id
                )

        self.mock_photo_service = PhotoAPIService(client=self.mock_photo_api_requests)
        self.facade._photo_api = self.mock_photo_service
        self.facade._profile_api = self.mock_profile_service

    def test_get_profile(self):
        self.mock_profile_service.get_profile.return_value = {
            "business": {"vertical": "AUTO"}
        }
        expected_profile = {"business": {"vertical": "Automotive"}}

        profile = self.facade.get_profile()
        self.assertEqual(profile, expected_profile)
        self.mock_profile_service.get_profile.assert_called_once()

    def test_set_profile_with_photo(self):
        photo = Mock()
        photo.file.getvalue.return_value = b"photo_data"
        photo.content_type = "image/jpeg"
        status = "new status"
        business = {"vertical": "Automotive"}

        self.facade.set_profile(photo=photo, status=status, business=business)

        self.mock_photo_api_requests.set_photo.assert_called_once_with(
            photo, self.phone_number_id
        )
        self.mock_profile_service.set_profile.assert_called_once_with(
            about=status, vertical="AUTO"
        )

    def test_set_profile_with_business_fields(self):
        photo = None
        status = "new status"
        business = {
            "vertical": "Automotive",
            "email": "test@example.com",
            "phone": "1234567890",
        }

        self.facade.set_profile(photo=photo, status=status, business=business)

        expected_data = {
            "about": status,
            "vertical": "AUTO",
            "email": "test@example.com",
            "phone": "1234567890",
        }

        self.mock_profile_service.set_profile.assert_called_once_with(**expected_data)

    def test_delete_profile_photo(self):
        self.facade.delete_profile_photo()
        self.mock_profile_service.delete_profile_photo.assert_called_once()


class CloudProfileContactFacadeTestCase(TestCase):
    def setUp(self):
        self.access_token = "fake_access_token"
        self.phone_number_id = "fake_phone_number_id"

        self.mock_facebook_client = Mock(spec=FacebookClient)
        self.mock_profile_service = Mock(spec=CloudProfileService)

        with patch(
            "marketplace.clients.facebook.client.FacebookClient",
            return_value=self.mock_facebook_client,
        ):
            with patch.object(
                FacebookClient,
                "get_profile_requests",
                return_value=self.mock_profile_service,
            ):
                self.facade = CloudProfileContactFacade(
                    self.access_token, self.phone_number_id
                )

        # Ensure get_url property is mockable
        self.mock_profile_service.client = Mock()
        self.mock_profile_service.client.get_url = Mock(return_value="http://fake.url")

    def test_get_profile(self):
        expected_profile = {"key": "value"}
        self.mock_profile_service.get_profile.return_value = expected_profile

        profile = self.facade.get_profile()
        self.assertEqual(profile, expected_profile)
        self.mock_profile_service.get_profile.assert_called_once()

    def test_set_profile(self):
        data = {"key": "value"}

        self.facade.set_profile(data)
        self.mock_profile_service.set_profile.assert_called_once_with(**data)

    def test_delete_profile_photo(self):
        self.facade.delete_profile_photo()
        self.mock_profile_service.delete_profile_photo.assert_called_once()
