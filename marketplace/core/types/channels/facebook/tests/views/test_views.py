import uuid

from unittest.mock import patch

from django.urls import reverse

from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from ...views import FacebookViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization

from ...type import FacebookType

apptype = FacebookType()


class CreateFacebookAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    url = reverse("fba-app-list")
    view_class = FacebookViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def setUp(self):
        super().setUp()
        self.project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": self.project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

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

    def test_create_app_with_internal_permission_only(self):
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_permission_and_authorization(self):
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveFacebookAppTestCase(APIBaseTestCase):
    view_class = FacebookViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="fba",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("fba-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

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


class DestroyFacebookAppTestCase(APIBaseTestCase):
    view_class = FacebookViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="fba",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("fba-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

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


class ConfigureFacebookAppTestCase(APIBaseTestCase):
    view_class = FacebookViewSet

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("fba-app-configure", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch("marketplace.clients.flows.client.FlowsClient.create_channel")
    def test_configure_facebook_success(self, mock_create_external_service):
        data = {
            "title": "Test",
            "address": "url",
            "config": {"page_name": "PageTest"},
        }
        mock_create_external_service.return_value = data
        payload = {
            "user": str(self.user),
            "project_uuid": str(uuid.uuid4()),
            "config": {
                "user_access_token": str(uuid.uuid4),
                "fb_user_id": str(uuid.uuid4),
                "page_name": "TestPage",
                "page_id": "0123456789",
            },
        }
        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
