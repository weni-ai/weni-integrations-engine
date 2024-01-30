import uuid

from django.test import TestCase

from marketplace.applications.models import App
from marketplace.services.vtex.generic_service import VtexService, APICredentials
from marketplace.services.vtex.exceptions import (
    NoVTEXAppConfiguredException,
    MultipleVTEXAppsConfiguredException,
    CredentialsValidationError,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class MockPrivateClient:
    def __init__(self, app_key, app_token):
        self.app_key = app_key
        self.app_token = app_token

    def is_valid_credentials(self, domain):
        return domain == "valid.domain.com"


class MockPrivateProductsService:
    def __init__(self, client):
        self.client = client

    def validate_private_credentials(self, domain):
        return self.client.is_valid_credentials(domain)


class VtexServiceTestCase(TestCase):
    def setUp(self):
        self.mock_private_client = MockPrivateClient("fake_key", "fake_token")
        self.mock_private_service = MockPrivateProductsService(self.mock_private_client)

        self.service = VtexService()
        self.service._pvt_service = self.mock_private_service
        self.project_uuid = uuid.uuid4()
        self.user = User.objects.create_superuser(email="user@marketplace.ai")
        # Vtex APp
        self.app = App.objects.create(
            code="vtex",
            config={},
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_VTEX,
            configured=True,
        )
        # Duplicated Apps
        self.duplicate_project = uuid.uuid4()
        self.duplicate_app_1 = App.objects.create(
            code="vtex",
            config={},
            created_by=self.user,
            project_uuid=self.duplicate_project,
            platform=App.PLATFORM_VTEX,
            configured=True,
        )
        self.duplicate_app_2 = App.objects.create(
            code="vtex",
            config={},
            created_by=self.user,
            project_uuid=self.duplicate_project,
            platform=App.PLATFORM_VTEX,
            configured=True,
        )
        # Wpp cloud App to Vtex App
        self.wpp_cloud = App.objects.create(
            code="wpp_cloud",
            config={},
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_VTEX,
            configured=True,
        )

    def test_get_vtex_app_or_error_found(self):
        response = self.service.app_manager.get_vtex_app_or_error(self.project_uuid)
        self.assertEqual(True, response.configured)

    def test_get_vtex_app_or_error_not_found(self):
        project_uuid = uuid.uuid4()

        with self.assertRaises(NoVTEXAppConfiguredException):
            self.service.app_manager.get_vtex_app_or_error(project_uuid)

    def test_get_vtex_app_or_error_multiple_found(self):
        with self.assertRaises(MultipleVTEXAppsConfiguredException):
            self.service.app_manager.get_vtex_app_or_error(self.duplicate_project)

    def test_check_is_valid_credentials_valid(self):
        credentials = APICredentials(
            domain="valid.domain.com", app_key="key", app_token="token"
        )
        is_valid = self.service.check_is_valid_credentials(credentials)
        self.assertTrue(is_valid)

    def test_check_is_valid_credentials_invalid(self):
        credentials = APICredentials(
            domain="invalid.domain.com", app_key="key", app_token="token"
        )
        with self.assertRaises(CredentialsValidationError):
            self.service.check_is_valid_credentials(credentials)

    def test_configure(self):
        credentials = APICredentials(
            domain="valid.domain.com", app_key="key", app_token="token"
        )
        wpp_cloud_uuid = str(self.wpp_cloud.uuid)
        configured_app = self.service.configure(self.app, credentials, wpp_cloud_uuid)

        self.assertTrue(configured_app.configured)
        self.assertEqual(
            configured_app.config["api_credentials"], credentials.to_dict()
        )
        self.assertEqual(configured_app.config["wpp_cloud_uuid"], wpp_cloud_uuid)

    def test_initial_sync_products_completed(self):
        response = self.service.app_manager.initial_sync_products_completed(self.app)
        self.assertEqual(response, True)
        self.assertEqual(self.app.config["initial_sync_completed"], True)

    def test_initial_sync_products_completed_error(self):
        with self.assertRaises(Exception):
            # send a app.uuid will raise a exception
            self.service.app_manager.initial_sync_products_completed(self.app.uuid)
