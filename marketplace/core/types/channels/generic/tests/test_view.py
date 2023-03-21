import uuid

from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.generic.views import GenericChannelViewSet
from marketplace.core.types.channels.generic.views import DetailChannelType
from marketplace.core.types.channels.generic.views import GetIcons
from marketplace.core.types.channels.generic.views import GenericAppTypes

from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.flows.client import FlowsClient

from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock

from rest_framework.response import Response


MOCK_DATA = {"channelUuid": str(uuid.uuid4())}


class FakeRequestsResponse:
    def __init__(self, data, status_code):
        self.data = data
        self.json = lambda: self.data
        self.status_code = status_code


class CreateGenericAppTestCase(APIBaseTestCase):
    url = "/api/v1/apptypes/generic/apps/"
    view_class = GenericChannelViewSet
    channels_code = ["tg", "ac", "wwc", "wpp-demo", "wpp-cloud", "wpp"]

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

    def test_create_list_of_channels(self):
        """Testing list of channels"""
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

    def test_create_app_platform(self):
        """Testing if create channels have platform"""
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
            "channel_claim_blurb": "twitter/url/claim"
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
        self.url = reverse(
            "generic-app-configure", kwargs={"uuid": self.app.uuid}
            )

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    @patch("marketplace.core.types.channels.generic.serializers.GenericConfigSerializer._create_channel")
    def test_configure_channel_success(self, mock_configure):
        mock_configure.return_value = Response(MOCK_DATA, status=status.HTTP_200_OK)
        keys_values = {
            "api_key": str(uuid.uuid4()),
            "api_secret": str(uuid.uuid4()),
            "access_token": str(uuid.uuid4()),
            "access_token_secret": str(uuid.uuid4()),
            "env_name": "Teste",
        }
        payload = {
            "user": str(self.user),
            "project_uuid":  str(uuid.uuid4()),
            "config": {
                "auth_token":  keys_values
            },
            "channeltype_code": "TWT"
        }

        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("marketplace.core.types.channels.generic.serializers.GenericConfigSerializer._create_channel")
    def test_configure_channel_without_config(self, mock_configure):
        """ Request without config field """
        response_data = {'config': ['This field is required.']}

        mock_configure.return_value = Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        payload = {
            "user": str(self.user),
            "project_uuid":  str(uuid.uuid4()),
            "channeltype_code": "TWT"
        }

        response = self.request.patch(self.url, payload, uuid=self.app.uuid)

        self.assertEqual(response_data, response.json)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DetailChannelAppTestCase(APIBaseTestCase):
    view_class = DetailChannelType

    def setUp(self):
        super().setUp()
        self.url = reverse(
            "channel-type-detail", kwargs={"code_channel": "tg"}
            )

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
                        "category": {
                            "name": "SOCIAL_MEDIA",
                            "value": 2
                        }
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


class ConnectChannelTypesTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.channels_code = ["AC", "WA", "WWC"]

    @patch("requests.get")
    def test_list_channel_types_error(self, mock):
        fake_response = FakeRequestsResponse(data={}, status_code=400)

        with patch("requests.get", return_value=fake_response):
            client = FlowsClient()
            response = client.list_channel_types(channel_code=None)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("requests.get")
    def test_list_channel_types(self, mock):
        payload = {
            "AC": {"attributes": {"code": "AC"}},
            "WA": {"attributes": {"code": "WA"}},
            "WWC": {"attributes": {"code": "WWC"}},
        }
        success_fake_response = FakeRequestsResponse(data=payload, status_code=200)

        with patch("requests.get", return_value=success_fake_response):
            client = FlowsClient()
            response = client.list_channel_types(channel_code=None)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            for channel in payload:
                self.assertEqual(response.json().get(channel), payload.get(channel))

    @patch("requests.get")
    def test_retrieve_channel_types(self, mock):
        payload = {
            "AC": {"attributes": {"code": "AC"}},
            "WA": {"attributes": {"code": "WA"}},
            "WWC": {"attributes": {"code": "WWC"}},
        }
        success_fake_response = FakeRequestsResponse(data=payload, status_code=200)

        with patch("requests.get", return_value=success_fake_response):
            for channel in self.channels_code:
                client = FlowsClient()
                response = client.list_channel_types(channel_code=channel)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.json().get(channel).get("attributes").get("code"), channel
                )

    @patch("requests.get")
    def test_retrieve_channel_types_error(self, mock):
        fake_response = FakeRequestsResponse(data={}, status_code=400)

        with patch("requests.get", return_value=fake_response):
            for channel in self.channels_code:
                client = FlowsClient()
                response = client.list_channel_types(channel_code=channel)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
                "AT": "http://example.com/icon.png"
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
    def test_get_genericapptypes_success(self, mock_list_channels_type):
        response_data = {
            "channel_types": {
                "D3": {
                    "attributes": {"key": "value"}
                },
                "TM": {
                    "attributes": {"key": "value"}
                },
                "TWT": {
                    "attributes": {"key": "value"}
                }
            }
        }

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.status_code = 200
        mock_list_channels_type.return_value = mock_response

        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, response_data["channel_types"])

    # TODO: Create test to GenericAppTypes
    # @patch("marketplace.flows.client.FlowsClient.list_channel_types")
    # def test_get_genericapptypes_fail(self, mock_list_channels_type):
    #     mock_response = MagicMock()
    #     mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
    #         "HTTPError", response=requests.Response(status_code=500)
    #     )
    #     # mock_response.response.status_code = 500
    #     mock_list_channels_type.return_value = mock_response
    #     response = self.request.get(self.url)
    #     self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # TODO: Create test to search_icon()
