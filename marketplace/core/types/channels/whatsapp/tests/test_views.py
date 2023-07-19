import uuid

from unittest.mock import patch
from unittest.mock import MagicMock

from django.urls import reverse
from django.utils.crypto import get_random_string
from django.test import override_settings
from rest_framework import status

from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)
from marketplace.core.tests.base import APIBaseTestCase, FakeRequestsResponse
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from ..views import WhatsAppViewSet


class RetrieveWhatsAppTestCase(APIBaseTestCase):
    view_class = WhatsAppViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-app-detail", kwargs={"uuid": self.app.uuid})

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


class DestroyWhatsAppTestCase(APIBaseTestCase):
    view_class = WhatsAppViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("wpp-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    # def test_destroy_app_ok(self):
    #     response = self.request.delete(self.url, uuid=self.app.uuid)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # def test_destroy_with_authorization_contributor(self):
    #     self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
    #     response = self.request.delete(self.url, uuid=self.app.uuid)
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_with_authorization_contributor_and_another_user(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.request.set_user(self.super_user)
        self.super_user.authorizations.create(
            project_uuid=self.app.project_uuid,
            role=ProjectAuthorization.ROLE_CONTRIBUTOR,
        )

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_viewer(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_not_setted(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SharedWabasWhatsAppTestCase(APIBaseTestCase):
    url = reverse("wpp-app-shared-wabas")
    view_class = WhatsAppViewSet

    @override_settings(SYSTEM_USER_ACCESS_TOKEN=get_random_string(32))
    def setUp(self):
        super().setUp()
        self.input_token = get_random_string(32)
        self.set_responses()

    def set_responses(self):
        self.debug_token_response = FakeRequestsResponse(
            {
                "data": {
                    "granular_scopes": [
                        {
                            "scope": "business_management",
                            "target_ids": ["1075799863665884"],
                        },
                        {
                            "scope": "whatsapp_business_management",
                            "target_ids": ["1075799863265884", "1072999863265884"],
                        },
                    ]
                }
            }
        )

        self.debug_token_without_business_response = FakeRequestsResponse(
            {
                "data": {
                    "granular_scopes": [
                        {
                            "scope": "business_management",
                            "target_ids": ["1075799863665884"],
                        },
                    ]
                }
            }
        )

        error_message = "The access token could not be decrypted"
        self.debug_token_error_response = FakeRequestsResponse(
            {"data": {"error": {"message": error_message}}}, error_message
        )

        self.target_responses = [
            FakeRequestsResponse(dict(id="1075799863265884", name="Fake target 1")),
            FakeRequestsResponse(dict(id="1072999863265884", name="Fake target 2")),
        ]

    @property
    def view(self):
        return self.view_class.as_view(dict(get="shared_wabas"))

    @patch("requests.get")
    def test_request_ok(self, requests):
        requests.side_effect = [self.debug_token_response] + self.target_responses

        response = self.request.get(self.url + f"?input_token={self.input_token}")
        response_json = response.json
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_json), 2)

        for waba in response_json:
            self.assertTrue(waba.get("id", False))
            self.assertTrue(waba.get("name", False))

    def test_request_without_input_token(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["input_token is a required parameter!"])

    @patch("requests.get")
    def test_request_with_invalid_input_token(self, requests):
        requests.side_effect = [self.debug_token_error_response]
        response = self.request.get(self.url + f"?input_token={self.input_token}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, [self.debug_token_error_response.error_message])

    @patch("requests.get")
    def test_response_without_whatsapp_business_management(self, requests):
        requests.side_effect = [self.debug_token_without_business_response]
        response = self.request.get(self.url + f"?input_token={self.input_token}")
        self.assertEqual(response.json, [])


class UpdateWhatsAppWebHookTestCase(APIBaseTestCase):
    view_class = WhatsAppViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-app-update-webhook", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"patch": "update_webhook"})

    @patch("marketplace.flows.client.FlowsClient.detail_channel")
    @patch("marketplace.flows.client.FlowsClient.update_config")
    def test_update_webhook_success(self, mock_flows_client, mock_detail):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock_flows_client.return_value = mock

        webhook = {
            "url": "https://webhook.site/60f72b28-ff2e-4eaa-8655-e9fe76584555",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer 1203alksdalksjd1029alksjda",
                "Content-type": "application/json",
            },
        }
        data = {"config": {"webhook": webhook}}
        config = {
            "tests_key": "test_value",
            "config": {"key1": "value1", "key2": "value2"},
        }
        mock_detail.return_value = config

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        app = App.objects.get(uuid=self.app.uuid)
        app.config["webhook"] = webhook
        app.save()

        self.assertEqual(app.config["webhook"], webhook)

    def test_update_webhook_invalid_key(self):
        data = {"invalid_key": {}}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.json, {"detail": "Missing key: 'config'"})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class WhatsAppReportSentMessagesTestCase(APIBaseTestCase):
    view_class = WhatsAppViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse(
            "wpp-app-report-sent-messages", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view({"get": "report_sent_messages"})

    @patch("marketplace.flows.client.FlowsClient.get_sent_messagers")
    def test_report_sent_messages_success(self, mock_flows_client):
        mock_flows_client.return_value.status_code = status.HTTP_200_OK

        params = {
            "project_uuid": str(self.app.project_uuid),
            "start_date": "01-05-2023",
            "end_date": "12-05-2023",
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_report_sent_messages_without_params(self):
        # Without project_uuid
        params = {
            "start_date": "01-05-2023",
            "end_date": "12-05-2023",
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Without start_date
        params = {
            "project_uuid": str(self.app.project_uuid),
            "end_date": "12-05-2023",
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Without end_date
        params = {
            "project_uuid": str(self.app.project_uuid),
            "start_date": "01-05-2023",
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MockConversation(object):
    def __dict__(self) -> dict:
        return dict(
            user_initiated=2,
            business_initiated=2099,
            total=2101,
        )


class WhatsAppOnPremisseConversationsTestCase(APIBaseTestCase):
    view_class = WhatsAppViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp",
            created_by=self.user,
            config={
                "fb_access_token": str(uuid.uuid4()),
                "fb_business_id": "0123456789",
            },
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.start_date = "6-1-2023"
        self.end_date = "6-30-2023"
        self.url = reverse("wpp-app-conversations", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"get": "conversations"})

    @patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.FacebookConversationAPI.conversations"
    )
    def test_get_conversations(self, mock_conversations):
        mock_conversations.return_value = MockConversation()

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.FacebookConversationAPI.conversations"
    )
    def test_get_conversations_with_facebook_api_exception(self, mock_conversations):
        error_message = "Facebook API exception"
        mock_conversations.side_effect = FacebookApiException(error_message)

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Facebook API exception"])
