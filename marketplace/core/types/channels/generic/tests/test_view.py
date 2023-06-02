import uuid

from django.urls import reverse
from django.test import override_settings
from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase

from marketplace.core.types.channels.generic.views import GenericChannelViewSet
from marketplace.core.types.channels.generic.views import DetailChannelType
from marketplace.core.types.channels.generic.views import GetIcons
from marketplace.core.types.channels.generic.views import GenericAppTypes
from marketplace.core.types.channels.generic.views import search_icon

from marketplace.applications.models import App
from marketplace.applications.models import AppTypeAsset

from marketplace.accounts.models import ProjectAuthorization

from unittest.mock import patch
from unittest.mock import Mock


User = get_user_model()


class FakeRequestsResponse:
    def __init__(self, data, status_code):
        self.data = data
        self.json = lambda: self.data
        self.status_code = status_code


class CreateGenericAppTestCase(APIBaseTestCase):
    url = "/api/v1/apptypes/generic/apps/"
    view_class = GenericChannelViewSet
    channels_code = ["twt", "sl", "tm"]

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

    @patch("marketplace.core.types.channels.generic.views.search_icon")
    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    def test_create_list_of_channels(self, mock_list_channel_types, mock_search_icon):
        """Testing list of channels"""
        response_data = {
            "attributes": {
                "code": "TEST",
                "slug": "slack",
                "name": "Teste",
                "icon": "icon-cord",
                "courier_url": "^sl/(?P<uuid>[a-z0-9\\-]+)/receive$",
                "claim_blurb": "Test.",
            },
            "form": [
                {
                    "name": "user_token",
                    "type": "text",
                },
            ],
        }
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channel_types.return_value = mock_response

        mock_search_icon.return_value = "https://url.test.com.br/icon.jpg"

        for channel in self.channels_code:
            self.body["channel_code"] = channel
            response = self.request.post(self.url, self.body, code=channel)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_channel_empty_code(self):
        """Testing create channel with code be empty"""
        url = f"{self.url}/ /apps/"
        response = self.request.post(url, self.body, code=" ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_app_without_project_uuid(self):
        """Testing create channel without project_uuid"""
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("marketplace.core.types.channels.generic.views.search_icon")
    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    def test_create_app_platform(self, mock_list_channel_types, mock_search_icon):
        """Testing if create channels have platform"""
        response_data = {
            "attributes": {
                "code": "TEST",
                "slug": "slack",
                "name": "Teste",
                "icon": "icon-cord",
                "courier_url": "^sl/(?P<uuid>[a-z0-9\\-]+)/receive$",
                "claim_blurb": "Test.",
            },
            "form": [
                {
                    "name": "user_token",
                    "type": "text",
                },
            ],
        }
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channel_types.return_value = mock_response

        mock_search_icon.return_value = "https://url.test.com.br/icon.jpg"

        response = self.request.post(self.url, self.body)
        for channel in self.channels_code:
            self.body["channel_code"] = channel
            response = self.request.post(self.url, self.body, code=channel)
            self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_create_app_without_permission(self):
        """Testing create generic channels without permission"""
        self.user_authorization.delete()
        for channel in self.channels_code:
            url = f"{self.url}/apps/"
            response = self.request.post(url, self.body, code=channel)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveGenericAppTestCase(APIBaseTestCase):
    view_class = GenericChannelViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="generic",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("generic-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid, code="generic")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid, code="generic")
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class ConfigureGenericAppTestCase(APIBaseTestCase):
    view_class = GenericChannelViewSet

    def setUp(self):
        super().setUp()

        data = {
            "channel_code": "TWT",
            "channel_name": "Twitter",
            "channel_icon_url": "twitter/url/icon",
            "channel_claim_blurb": "twitter/url/claim",
        }

        self.app = App.objects.create(
            code="generic",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=data,
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("generic-app-configure", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch(
        "marketplace.core.types.channels.generic.serializers.ConnectProjectClient.create_channel"
    )
    def test_configure_channel_success(self, mock_configure):
        mock_configure.return_value = {"channelUuid": str(uuid.uuid4())}
        keys_values = {
            "api_key": str(uuid.uuid4()),
            "api_secret": str(uuid.uuid4()),
            "access_token": str(uuid.uuid4()),
            "access_token_secret": str(uuid.uuid4()),
            "env_name": "Teste",
        }
        payload = {
            "user": str(self.user),
            "project_uuid": str(uuid.uuid4()),
            "config": {"auth_token": keys_values},
        }

        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_channel_without_config(self):
        """Request without config field"""
        response_data = {"config": ["This field is required."]}
        payload = {
            "user": str(self.user),
            "project_uuid": str(uuid.uuid4()),
        }
        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response_data, response.json)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DetailChannelAppTestCase(APIBaseTestCase):
    view_class = DetailChannelType

    def setUp(self):
        super().setUp()
        self.url = reverse("channel-type-detail", kwargs={"code_channel": "tg"})

    @property
    def view(self):
        return self.view_class.as_view({"get": "retrieve"})

    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    def test_retrieve_success(self, mock_list_channels_type):
        response_data = {
            "channel_types": {
                "TG": {
                    "attributes": {
                        "code": "TG",
                        "category": {"name": "SOCIAL_MEDIA", "value": 2},
                    }
                }
            }
        }
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channels_type.return_value = mock_response

        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, response_data)

    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    def test_retrieve_fail(self, mock_list_channels_type):
        response_data = None
        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 404
        mock_list_channels_type.return_value = mock_response

        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(USE_GRPC=False)
class DestroyTelegramAppTestCase(APIBaseTestCase):
    view_class = GenericChannelViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="generic",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.code = "generic"
        self.url = reverse("generic-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def test_destroy_generic_app(self):
        response = self.request.delete(self.url, uuid=self.app.uuid, code=self.code)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_generic_channel_with_authorization_contributor(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        response = self.request.delete(self.url, uuid=self.app.uuid, code=self.code)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_generic_channel_with_authorization_viewer(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        response = self.request.delete(self.url, uuid=self.app.uuid, code=self.code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_generic_channel_with_authorization_not_setted(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid, code=self.code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class GetIconsTestCase(APIBaseTestCase):
    view_class = GetIcons

    def setUp(self):
        super().setUp()
        self.url = reverse("get-icons-list")

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    @patch("marketplace.core.types.channels.generic.views.search_icon")
    def test_get_icons_success(self, mock_search_icon, mock_list_channels_type):
        response_data = {
            "channel_types": {
                "D3": "http://example.com/icon.png",
                "ZVW": "http://example.com/icon.png",
                "TMS": "http://example.com/icon.png",
                "AT": "http://example.com/icon.png",
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channels_type.return_value = mock_response

        mock_search_icon.return_value = "http://example.com/icon.png"
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, response_data["channel_types"])

    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    @patch("marketplace.core.types.channels.generic.views.search_icon")
    def test_get_icons_fail(self, mock_search_icon, mock_list_channels_type):
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_list_channels_type.return_value = mock_response

        mock_search_icon.return_value = None
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GenericAppTypesTestCase(APIBaseTestCase):
    view_class = GenericAppTypes

    def setUp(self):
        super().setUp()
        self.url = reverse("my-apps-list")

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    def test_list_genericapptypes_success(self, mock_list_channels_type):
        response_data = {
            "channel_types": {
                "D3": {"attributes": {"key": "value"}},
                "TM": {"attributes": {"key": "value"}},
                "TWT": {"attributes": {"key": "value"}},
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channels_type.return_value = mock_response

        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, response_data["channel_types"])


class SearchIconTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.channel_code = "test_code"
        self.icon_url = "example.com/icon.png"
        self.path = "/media/"
        self.user = User.objects.create_superuser(email="user@marketplace.ai")
        self.apptype_asset = AppTypeAsset.objects.create(
            code=self.channel_code.lower(),
            attachment=self.icon_url,
            created_by=self.user,
        )
        self.generic_apptype_asset = AppTypeAsset.objects.create(
            code="generic", attachment=self.icon_url, created_by=self.user
        )

    def test_search_icon_with_existing_code(self):
        result = search_icon(self.channel_code)
        self.assertEqual(result, f"{self.path}{self.icon_url}")

    def test_search_icon_with_non_existing_code(self):
        non_existing_code = "non_existing_code"
        result = search_icon(non_existing_code)
        generic_apptype_asset = AppTypeAsset.objects.filter(code="generic").first()
        expected_url = (
            generic_apptype_asset.attachment.url if generic_apptype_asset else None
        )
        self.assertEqual(result, expected_url)

    def test_search_icon_with_generic_code(self):
        generic_code = "generic"
        result = search_icon(generic_code)
        generic_apptype_asset = AppTypeAsset.objects.filter(code="generic").first()
        expected_url = (
            generic_apptype_asset.attachment.url if generic_apptype_asset else None
        )
        self.assertEqual(result, expected_url)

    def test_search_icon_with_invalid_code_and_missing_generic_asset(self):
        AppTypeAsset.objects.all().delete()
        invalid_code = "invalid_code"
        icon_url = search_icon(invalid_code)
        self.assertIsNone(icon_url)
        # Recreates the apptype_asset objects
        self.apptype_asset = AppTypeAsset.objects.create(
            code=self.channel_code.lower(),
            attachment=self.icon_url,
            created_by=self.user,
        )
        self.generic_apptype_asset = AppTypeAsset.objects.create(
            code="generic", attachment=self.icon_url, created_by=self.user
        )
