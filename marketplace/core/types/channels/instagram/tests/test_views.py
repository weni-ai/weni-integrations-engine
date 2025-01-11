import uuid

from unittest.mock import patch

from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import InstagramViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization

from ..type import InstagramType

apptype = InstagramType()


class CreateInstagramAppTestCase(APIBaseTestCase):
    url = reverse("ig-app-list")
    view_class = InstagramViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
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

    # TODO: Fix this test broken due to PR #594.
    # def test_create_app_without_permission(self):
    #     self.user_authorization.delete()
    #     response = self.request.post(self.url, self.body)
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveInstagramAppTestCase(APIBaseTestCase):
    view_class = InstagramViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="ig",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("ig-app-detail", kwargs={"uuid": self.app.uuid})

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


@override_settings(USE_GRPC=False)
class DestroyInstagramAppTestCase(APIBaseTestCase):
    view_class = InstagramViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="ig",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("ig-app-detail", kwargs={"uuid": self.app.uuid})

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


class ConfigureInstagramAppTestCase(APIBaseTestCase):
    view_class = InstagramViewSet

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("ig-app-configure", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch(
        "marketplace.core.types.channels.instagram.views.ConnectProjectClient.create_channel"
    )
    def test_configure_instagram_success(self, mock_create_external_service):
        data = {
            "channelUuid": str(uuid.uuid4()),
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
