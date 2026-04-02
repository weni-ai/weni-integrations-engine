import uuid

from unittest.mock import patch
from unittest.mock import MagicMock

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import ValidationError

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from ..views import WeniWebChatViewSet
from ..serializers import AvatarImageField, OpenLauncherImageField
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


class AvatarImageFieldTestCase(TestCase):
    def setUp(self):
        self.field = AvatarImageField()

    def test_valid_url_returns_string(self):
        url = "https://example.com/avatar.png"
        result = self.field.to_internal_value(url)
        self.assertEqual(result, url)

    def test_invalid_string_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.field.to_internal_value("not-a-url-or-base64")

    def test_non_string_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.field.to_internal_value(12345)

    def test_base64_returns_content_file(self):
        base64_image = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        result = self.field.to_internal_value(base64_image)
        self.assertIsInstance(result, ContentFile)
        self.assertEqual(result.name, "avatar.png")


class OpenLauncherImageFieldTestCase(TestCase):
    def setUp(self):
        self.field = OpenLauncherImageField()

    def test_valid_url_returns_string(self):
        url = "https://example.com/launcher.png"
        result = self.field.to_internal_value(url)
        self.assertEqual(result, url)

    def test_invalid_string_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.field.to_internal_value("not-a-url-or-base64")

    def test_non_string_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.field.to_internal_value(12345)

    def test_base64_returns_content_file(self):
        base64_image = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        result = self.field.to_internal_value(base64_image)
        self.assertIsInstance(result, ContentFile)
        self.assertEqual(result.name, "launcher.png")


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

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_project_authorization(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
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

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_internal_permission_only(self, mock_flows_client):
        self.grant_permission(self.user, "can_communicate_internally")
        ProjectAuthorization.objects.filter(user=self.user).delete()

        mock_flows_client.return_value.create_channel.return_value = {
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

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_render_percentage(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        self.body["config"]["renderPercentage"] = 50
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config.get("renderPercentage"), 50)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_without_render_percentage(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertNotIn("renderPercentage", self.app.config)

    def test_configure_with_invalid_render_percentage_above_max(self):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.body["config"]["renderPercentage"] = 150
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_configure_with_invalid_render_percentage_below_min(self):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.body["config"]["renderPercentage"] = -10
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_conversation_starters_pdp(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        self.body["config"]["conversationStartersPDP"] = True
        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config["conversationStarters"]["pdp"], True)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_without_conversation_starters_pdp(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config["conversationStarters"]["pdp"], False)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_url_avatar(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        avatar_url = "https://example.com/avatar.png"
        self.body["config"]["profileAvatar"] = avatar_url

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config["profileAvatar"], avatar_url)
        self.assertNotIn("openLauncherImage", self.app.config)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_base64_avatar(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        base64_avatar = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        self.body["config"]["profileAvatar"] = base64_avatar

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertIn("profileAvatar", self.app.config)
        self.assertTrue(self.app.config["profileAvatar"].startswith("https://"))

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_with_separate_open_launcher_image(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        avatar_url = "https://example.com/avatar.png"
        launcher_url = "https://example.com/launcher.png"
        self.body["config"]["profileAvatar"] = avatar_url
        self.body["config"]["openLauncherImage"] = launcher_url

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config["profileAvatar"], avatar_url)
        self.assertEqual(self.app.config["openLauncherImage"], launcher_url)

    @patch("marketplace.core.types.channels.weni_web_chat.serializers.FlowsClient")
    @patch(
        "marketplace.core.types.channels.weni_web_chat.serializers.AppStorage",
        MockAppStorage,
    )
    def test_configure_preserves_render_percentage_on_update(self, mock_flows_client):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        mock_flows_client.return_value.create_channel.return_value = {
            "uuid": str(uuid.uuid4()),
        }

        self.body["config"]["renderPercentage"] = 10
        self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.app.refresh_from_db()
        self.assertEqual(self.app.config["renderPercentage"], 10)

        body_without_render = {
            "config": {
                "title": "updated_title",
                "mainColor": "#009E96",
                "timeBetweenMessages": 1,
            }
        }
        response = self.request.patch(self.url, body_without_render, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.app.refresh_from_db()
        self.assertEqual(self.app.config.get("renderPercentage"), 10)

    def test_configure_with_invalid_avatar(self):
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.body["config"]["profileAvatar"] = "not-a-url-or-base64"

        response = self.request.patch(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
