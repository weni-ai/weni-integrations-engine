import uuid

from django.urls import reverse

from rest_framework import status

from unittest.mock import (
    patch,
    call,
    MagicMock,
)

from django.contrib.auth import get_user_model

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)
from marketplace.core.types.channels.whatsapp_base.serializers import (
    WhatsAppBusinessContactSerializer,
)

from ..views import WhatsAppCloudViewSet

User = get_user_model()


class RetrieveWhatsAppCloudTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-cloud-app-detail", kwargs={"uuid": self.app.uuid})

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


class DestroyWhatsAppCloudTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("wpp-cloud-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def test_destroy_app_ok(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpdateWhatsAppCloudWebHookTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
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
            "wpp-cloud-app-update-webhook", kwargs={"uuid": self.app.uuid}
        )

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


class WhatsAppCloudReportSentMessagesTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
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
            "wpp-cloud-app-report-sent-messages", kwargs={"uuid": self.app.uuid}
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


class WhatsAppCloudConversationsTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            config={"fb_access_token": str(uuid.uuid4()), "wa_waba_id": "0123456789"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.start_date = "6-1-2023"
        self.end_date = "6-30-2023"
        self.url = reverse(
            "wpp-cloud-app-conversations", kwargs={"uuid": self.app.uuid}
        )

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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.views.settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN",
        None,
    )
    def test_get_conversations_without_access_token(self):
        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json, ["This app does not have fb_access_token in settings"]
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.views.settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN",
        None,
    )
    def test_get_conversations_without_wa_waba_id(self):
        app = App.objects.create(
            code="wpp-cloud",
            config={"fb_access_token": str(uuid.uuid4())},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        authorization = self.user.authorizations.create(project_uuid=app.project_uuid)
        authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=app.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json,
            ["This app does not have WABA (Whatsapp Business Account ID) configured"],
        )


class CreateWhatsAppCloudTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.payload = {
            "project_uuid": str(uuid.uuid4()),
            "auth_code": "token0123456789",
            "waba_id": "0123456789",
            "phone_number_id": "0123456789",
        }
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.payload["project_uuid"]
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-cloud-app-list")

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    @patch("requests.get")
    @patch("requests.post")
    @patch("marketplace.core.types.channels.whatsapp_cloud.views.PhoneNumbersRequest")
    @patch("marketplace.core.types.channels.whatsapp_cloud.views.ConnectProjectClient")
    @patch("marketplace.core.types.channels.whatsapp_cloud.views.celery_app.send_task")
    def test_create_whatsapp_cloud(
        self,
        mock_send_task,
        mock_ConnectProjectClient,
        mock_PhoneNumbersRequest,
        mock_post,
        mock_get,
    ):
        mock_get.return_value.status_code = status.HTTP_200_OK
        mock_get.return_value.status_code = status.HTTP_200_OK
        mock_post.return_value.status_code = status.HTTP_200_OK
        mock_get.return_value.json.return_value = {
            "message_template_namespace": "some value",
            "on_behalf_of_business_info": {"id": "02020202"},
        }
        mock_post.return_value.json.return_value = {
            "allocation_config_id": "Some Value"
        }
        phone_number_request_instance = mock_PhoneNumbersRequest.return_value
        phone_number_request_instance.get_phone_number.return_value = {
            "display_phone_number": "123456789",
            "verified_name": "Some Name",
        }
        connect_project_client_instance = mock_ConnectProjectClient.return_value
        connect_project_client_instance.create_wac_channel.return_value = {
            "uuid": str(uuid.uuid4())
        }

        response = self.request.post(self.url, body=self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_task.assert_has_calls(
            [
                call(name="sync_whatsapp_cloud_wabas"),
                call(name="sync_whatsapp_cloud_phone_numbers"),
            ]
        )

    @patch("requests.get")
    def test_create_wpp_cloud_failure_on_get_user_token(
        self,
        mock_get,
    ):

        mock_get.return_value = MagicMock(status_code=status.HTTP_400_BAD_REQUEST)

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("requests.get")
    @patch("requests.post")
    def test_create_wpp_cloud_failure_on_assigned_users(
        self,
        mock_post,
        mock_get,
    ):
        mock_get.return_value = MagicMock(status_code=status.HTTP_200_OK)

        returns_for_post = [
            MagicMock(
                status_code=status.HTTP_400_BAD_REQUEST,
                json=lambda: {"error_message": "Some Error Assigned Users"},
            )
        ]
        mock_post.side_effect = returns_for_post

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, {"error_message": "Some Error Assigned Users"})

    @patch("requests.get")
    @patch("requests.post")
    def test_create_wpp_cloud_failure_on_credit_sharing_and_attach(
        self,
        mock_post,
        mock_get,
    ):
        mock_get.return_value = MagicMock(
            status_code=status.HTTP_200_OK,
            json=lambda: {
                "message_template_namespace": "some value",
                "on_behalf_of_business_info": {"id": "02020202"},
            },
        )

        first_post_return = MagicMock(
            status_code=status.HTTP_200_OK, json=lambda: {"some_key": "some value"}
        )
        second_post_return = MagicMock(
            status_code=status.HTTP_400_BAD_REQUEST,
            json=lambda: {"error_message": "Some Error Sharing"},
        )
        mock_post.side_effect = [first_post_return, second_post_return]

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, {"error_message": "Some Error Sharing"})

    @patch("requests.get")
    @patch("requests.post")
    def test_create_wpp_cloud_failure_on_subscribed_apps(
        self,
        mock_post,
        mock_get,
    ):
        mock_get.return_value = MagicMock(status_code=status.HTTP_200_OK)

        returns_for_post = [
            MagicMock(status_code=status.HTTP_200_OK),
            MagicMock(status_code=status.HTTP_200_OK),
            MagicMock(
                status_code=status.HTTP_400_BAD_REQUEST,
                json=lambda: {"error_message": "Some Error Subscribed Apps"},
            ),
        ]
        mock_post.side_effect = returns_for_post

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, {"error_message": "Some Error Subscribed Apps"})

    @patch("requests.get")
    @patch("requests.post")
    def test_create_wpp_cloud_failure_on_register(
        self,
        mock_post,
        mock_get,
    ):
        mock_get.return_value = MagicMock(status_code=status.HTTP_200_OK)

        returns_for_post = [
            MagicMock(status_code=status.HTTP_200_OK),
            MagicMock(status_code=status.HTTP_200_OK),
            MagicMock(status_code=status.HTTP_200_OK),
            MagicMock(
                status_code=status.HTTP_400_BAD_REQUEST,
                json=lambda: {"error_message": "Some Error Subscribed Apps"},
            ),
        ]
        mock_post.side_effect = returns_for_post

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, {"error_message": "Some Error Subscribed Apps"})


class MockCloudProfileContactFacade:
    def get_profile(self):
        return {
            "websites": ["https://example.com"],
            "email": "contact@example.com",
            "address": "123 Example St.",
        }

    def set_profile(self, data: dict):
        pass


class WhatsAppCloudContactTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            config={
                "fb_access_token": str(uuid.uuid4()),
                "wa_waba_id": "0123456789",
                "wa_phone_number_id": "1234567890",
                "wa_user_token": "123456789",
            },
            created_by=self.user,
            project_uuid=uuid.uuid4(),
            flow_object_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-cloud-app-contact", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"get": "contact"})

    def test_contact_without_wa_phone_number_id(self):
        app_without_phone_number_id = App.objects.create(
            code="wpp-cloud",
            config={"fb_access_token": str(uuid.uuid4()), "wa_waba_id": "0123456789"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        authorization = self.user.authorizations.create(
            project_uuid=app_without_phone_number_id.project_uuid
        )
        authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        response_url = reverse(
            "wpp-cloud-app-contact", kwargs={"uuid": app_without_phone_number_id.uuid}
        )
        response = self.request.get(response_url, uuid=app_without_phone_number_id.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["The phone number is not configured"])

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.views.WhatsAppCloudViewSet.business_profile_class"
    )
    def test_get_contact_success(self, MockBusinessProfileClass):
        profile_data = {
            "websites": ["https://example.com"],
            "email": "contact@example.com",
            "address": "123 Example St.",
        }

        mock_instance = MockBusinessProfileClass.return_value
        mock_instance.get_profile.return_value = profile_data

        with patch.object(
            WhatsAppCloudViewSet, "serializer_class", WhatsAppBusinessContactSerializer
        ):
            view = self.view_class()
            view.business_profile_class = mock_instance
            response = self.request.get(self.url, uuid=self.app.uuid)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, profile_data)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.views.WhatsAppCloudViewSet.business_profile_class"
    )
    def test_get_contact_with_facebook_api_exception(self, MockBusinessProfileClass):
        def raise_facebook_api_exception(*args, **kwargs):
            raise FacebookApiException("Simulated exception")

        mock_instance = MockBusinessProfileClass.return_value
        mock_instance.get_profile.side_effect = raise_facebook_api_exception

        with patch.object(
            WhatsAppCloudViewSet, "serializer_class", WhatsAppBusinessContactSerializer
        ):
            view = self.view_class()
            view.business_profile_class = mock_instance
            response = self.request.get(self.url, uuid=self.app.uuid)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            self.assertEqual(
                response.json[0],
                "There was a problem requesting the On-Premise API, check if your authentication token is correct",
            )
