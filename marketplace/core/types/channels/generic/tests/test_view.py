import uuid

from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import GenericChannelViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.tests.base import FakeRequestsResponse
from marketplace.connect.client import ConnectProjectClient

from unittest import TestCase
from unittest.mock import patch


class CreateTelegramAppTestCase(APIBaseTestCase):
    url = '/api/v1/apptypes/generic/apps/'
    view_class = GenericChannelViewSet
    channels_code = ['tg', 'ac', 'wwc', 'wpp-demo', 'wpp-cloud', 'wpp']

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
        """ Testing list of channels """
        for channel in self.channels_code:
            self.body["channel_code"] = channel
            response = self.request.post(self.url, self.body, code=channel)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_channel_empty_code(self):
        """ Testing create channel with code be empty """
        url = f'{self.url}/ /apps/'
        response = self.request.post(url, self.body, code=" ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_app_without_project_uuid(self):
        """ Testing create channel without project_uuid """
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        """ Testing if create channels have platform"""
        response = self.request.post(self.url, self.body)
        for channel in self.channels_code:
            self.body["channel_code"] = channel
            response = self.request.post(self.url, self.body, code=channel)
            self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_create_app_without_permission(self):
        """ Testing create generic channels without permission"""
        self.user_authorization.delete()
        for channel in self.channels_code:
            url = f'{self.url}/apps/'
            response = self.request.post(url, self.body, code=channel)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveGenericAppTestCase(APIBaseTestCase):
    view_class = GenericChannelViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="generic", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
        )
        
        self.user_authorization = self.user.authorizations.create(project_uuid=self.app.project_uuid)
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


@override_settings(USE_GRPC=False)
class DestroyTelegramAppTestCase(APIBaseTestCase):
    view_class = GenericChannelViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="generic", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
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

    def test_destroy_generic_channel_with_authorization_contributor_and_another_user(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.request.set_user(self.super_user)
        self.super_user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

        response = self.request.delete(self.url, uuid=self.app.uuid, code=self.code)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400
        mock.side_effect = [fake_response, fake_response, fake_response]

        client = ConnectProjectClient()
        response = client.list_availables_channels()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("requests.get")
    def test_list_channel_types(self, mock):
        payload = {
            "AC" : { "attributes" : {"code": "AC"}},
            "WA" : { "attributes" : {"code": "WA"}},
            "WWC" : { "attributes" : {"code": "WWC"}}
        }
        success_fake_response = FakeRequestsResponse(data=payload)
        success_fake_response.status_code = 200
        mock.side_effect = [success_fake_response, success_fake_response, success_fake_response]

        client = ConnectProjectClient()
        response = client.list_availables_channels()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for channel in payload:
            self.assertEqual(response.json().get(channel), payload.get(channel))

    def test_retrieve_channel_types(self):
        payload = {
            "AC" : { "attributes" : {"code": "AC"}},
            "WA" : { "attributes" : {"code": "WA"}},
            "WWC" : { "attributes" : {"code": "WWC"}}
        }
        success_fake_response = FakeRequestsResponse(data=payload)
        success_fake_response.status_code = 200

        client = ConnectProjectClient()
        for channel in self.channels_code:
            response = client.detail_channel_type(channel_code=channel)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json().get("attributes").get("code"), channel)

    @patch("requests.get")
    def test_retrieve_channel_types_error(self, mock):
        fake_response = FakeRequestsResponse(data={})
        fake_response.status_code = 400
        mock.side_effect = [fake_response, fake_response, fake_response]

        client = ConnectProjectClient()
        for channel in self.channels_code:
            response = client.detail_channel_type(channel_code=channel)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
