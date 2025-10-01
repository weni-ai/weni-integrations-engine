import uuid

from unittest.mock import patch

from django.urls import reverse

from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from ..views import TelegramViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization

from ..type import TelegramType


apptype = TelegramType()


class CreateTelegramAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    url = reverse("tg-app-list")
    view_class = TelegramViewSet

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
        """Removing ProjectAuthorization should prevent creation"""
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_with_internal_permission_only(self):
        """Allow creation if user has only global permission"""
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_permission_and_authorization(self):
        """Deny creation if user has neither permission nor auth"""
        self.user_authorization.delete()
        self.clear_permissions(self.user)
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveTelegramAppTestCase(APIBaseTestCase):
    view_class = TelegramViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="tg",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("tg-app-detail", kwargs={"uuid": self.app.uuid})

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


class DestroyTelegramAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    view_class = TelegramViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="tg",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("tg-app-detail", kwargs={"uuid": self.app.uuid})

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

    def test_destroy_with_internal_permission_only(self):
        """Should allow deletion if the user only has internal permission"""
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_without_permission_and_authorization(self):
        """Should return 403 if the user has neither internal permission nor project authorization"""
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ConfigureTelegramAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    view_class = TelegramViewSet

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("tg-app-configure", kwargs={"uuid": self.app.uuid})

        self.payload = {
            "user": str(self.user),
            "project_uuid": self.app.project_uuid,
            "config": {
                "token": str(uuid.uuid4()),
            },
        }

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch(
        "marketplace.core.types.channels.telegram.views.ConnectProjectClient.create_channel"
    )
    def test_configure_telegram_success(self, mock_create_external_service):
        mock_create_external_service.return_value = {
            "channelUuid": str(uuid.uuid4()),
            "title": "Test",
        }

        response = self.request.patch(self.url, self.payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, 200)

    def test_configure_telegram_without_permission_and_authorization(self):
        """Should return 403 if the user has neither internal permission nor project authorization"""
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.patch(self.url, self.payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, 403)

    @patch(
        "marketplace.core.types.channels.telegram.views.ConnectProjectClient.create_channel"
    )
    def test_configure_telegram_with_internal_permission_only(
        self, mock_create_external_service
    ):
        """Should allow configuration if user only has internal permission"""
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        mock_create_external_service.return_value = {
            "channelUuid": str(uuid.uuid4()),
            "title": "Test",
        }

        response = self.request.patch(self.url, self.payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, 200)
