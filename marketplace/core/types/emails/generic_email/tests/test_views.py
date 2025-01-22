import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types.emails.generic_email.views import GenericEmailViewSet
from marketplace.core.types.emails.generic_email.type import GenericEmailType

apptype = GenericEmailType()


class MockFlowsService:
    def __init__(self, *args, **kwargs):
        pass

    def create_channel(self, user_email, project_uuid, data, channeltype_code):
        return {"uuid": str(uuid.uuid4()), "name": "Test Email Channel"}


class SetUpTestBase(APIBaseTestCase):
    current_view_mapping = {}
    view_class = GenericEmailViewSet

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
            code="email",
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


class CreateGenericEmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"post": "create"}
    url = reverse("email-app-list")

    def setUp(self):
        super().setUp()
        self.body = {
            "project_uuid": self.project_uuid,
            "user_name": "email@example.com",
            "password": "123456",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "imap_host": "imap.example.com",
            "imap_port": 993,
        }

    def test_request_ok(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ConfigureGenericEmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"patch": "configure"}

    def setUp(self):
        super().setUp()
        self.url = reverse("email-app-configure", kwargs={"uuid": self.app.uuid})
        self.body = {
            "user": str(self.user),
            "project_uuid": self.app.project_uuid,
            "config": {
                "username": "email@example.com",
                "password": "123456",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "imap_host": "imap.example.com",
                "imap_port": 993,
            },
        }

    def test_configure_generic_email_success(self):
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_email_without_permission(self):
        self.user_authorization.delete()
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveGenericEmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"get": "retrieve"}

    def setUp(self):
        super().setUp()
        self.url = reverse("email-app-detail", kwargs={"uuid": self.app.uuid})

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


class DestroyGenericEmailAppTestCase(SetUpTestBase):
    current_view_mapping = {"delete": "destroy"}

    def setUp(self):
        super().setUp()
        self.url = reverse("email-app-detail", kwargs={"uuid": self.app.uuid})

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
