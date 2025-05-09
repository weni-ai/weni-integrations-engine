import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from marketplace.core.types.emails.gmail.views import GmailViewSet
from marketplace.core.types.emails.gmail.type import GmailType


apptype = GmailType()


class MockFlowsService:
    def __init__(self, *args, **kwargs):
        pass

    def create_channel(self, user_email, project_uuid, data, channeltype_code):
        return {"uuid": str(uuid.uuid4()), "name": "Test Gmail Channel"}


class SetUpTestBase(PermissionTestCaseMixin, APIBaseTestCase):
    current_view_mapping = {}
    view_class = GmailViewSet

    def setUp(self):
        super().setUp()

        # Mocking the FlowsService directly in setUp
        self.mock_flows_service = patch.object(
            self.view_class, "flows_service", new_callable=MockFlowsService
        )
        self.mock_flows_service.start()
        self.addCleanup(self.mock_flows_service.stop)

        self.project_uuid = str(uuid.uuid4())
        self.app = App.objects.create(
            code="gmail",
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)


class CreateGmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"post": "create"}
    url = reverse("gmail-app-list")

    def setUp(self):
        super().setUp()
        self.body = {
            "project_uuid": self.project_uuid,
            "access_token": "mock-access_token",
            "refresh_token": "mock-refresh-token",
        }

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)

    @patch("marketplace.core.types.emails.gmail.serializers.requests.get")
    def test_request_ok(self, mock_requests_get):
        mock_requests_get.return_value.json.return_value = {
            "emailAddress": "gmail@example.com"
        }
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("marketplace.core.types.emails.gmail.serializers.requests.get")
    def test_create_app_platform(self, mock_requests_get):
        mock_requests_get.return_value.json.return_value = {
            "emailAddress": "gmail@example.com"
        }
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("marketplace.core.types.emails.gmail.serializers.requests.get")
    def test_create_app_without_permission(self, mock_requests_get):
        self.user_authorization.delete()
        mock_requests_get.return_value.json.return_value = {
            "emailAddress": "gmail@example.com"
        }
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("marketplace.core.types.emails.gmail.serializers.requests.get")
    def test_create_app_with_internal_permission_only(self, mock_requests_get):
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")
        mock_requests_get.return_value.json.return_value = {
            "emailAddress": "gmail@example.com"
        }
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("marketplace.core.types.emails.gmail.serializers.requests.get")
    def test_create_app_without_permission_and_authorization(self, mock_requests_get):
        self.user_authorization.delete()
        self.clear_permissions(self.user)
        mock_requests_get.return_value.json.return_value = {
            "emailAddress": "gmail@example.com"
        }
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveGmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"get": "retrieve"}

    def setUp(self):
        super().setUp()
        self.url = reverse("gmail-app-detail", kwargs={"uuid": self.app.uuid})

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class DestroyGmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"delete": "destroy"}

    def setUp(self):
        super().setUp()
        self.url = reverse("gmail-app-detail", kwargs={"uuid": self.app.uuid})

    def test_destroy_app_ok(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_with_authorization_contributor(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_with_authorization_viewer(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_not_setted(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
