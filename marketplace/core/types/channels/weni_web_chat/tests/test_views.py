import uuid

from unittest.mock import patch
from unittest.mock import MagicMock

from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from ..views import WeniWebChatViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization

from ..type import WeniWebChatType

apptype = WeniWebChatType()


class CreateWeniWebChatAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    url = reverse("wwc-app-list")
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

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
        # Remove authorization but ensure system permission
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_permission_and_authorization(self):
        # Remove authorization and permissions
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveWeniWebChatAppTestCase(APIBaseTestCase):
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wwc",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wwc-app-detail", kwargs={"uuid": self.app.uuid})

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
class DestroyWeniWebChatAppTestCase(APIBaseTestCase):
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wwc",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("wwc-app-detail", kwargs={"uuid": self.app.uuid})

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


class MockAppStorage(MagicMock):
    def open(self, name, mode):
        mock_file = MagicMock()
        mock_file.name = name
        mock_file.__enter__.return_value = mock_file
        return mock_file

    def url(self, name):
        return f"https://weni-test.invalidurl.com/apptypes/{str(uuid.uuid4)}/{str(uuid.uuid4)}/{name}"


class ConfigureWeniWebChatTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()
        self.app = WeniWebChatType().create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.url = reverse("wwc-app-configure", kwargs={"uuid": self.app.uuid})
        self.body = {
            "config": {
                "title": "teste1",
                "inputTextFieldHint": "teste",
                "timeBetweenMessages": 1,
                "mainColor": "#009E96",
            }
        }

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.ConnectProjectClient"
    )
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_project_authorization(self, mock_connect_project_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_connect_project_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
            "mainColor": "#009E96",
            "keepHistory": True,
            "timeBetweenMessages": 1,
            "customCss": "body { background-color: red; }",
        }

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_without_permission_or_authorization(self):
        ProjectAuthorization.objects.filter(user=self.user).delete()
        self.clear_permissions(self.user)

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.ConnectProjectClient"
    )
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_internal_permission_only(self, mock_connect_project_client):
        self.grant_permission(self.user, "can_communicate_internally")
        ProjectAuthorization.objects.filter(user=self.user).delete()

        mock_connect_project_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
            "mainColor": "#009E96",
            "keepHistory": True,
            "timeBetweenMessages": 1,
            "customCss": "body { background-color: red; }",
        }

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_denied_without_permission_and_authorization(self):
        self.clear_permissions(self.user)
        ProjectAuthorization.objects.filter(user=self.user).delete()

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
