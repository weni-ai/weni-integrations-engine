import uuid

from django.urls import reverse
from django.test import override_settings

from rest_framework import status

from unittest.mock import patch, MagicMock, Mock

from django.contrib.auth import get_user_model

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)
from marketplace.core.types.channels.whatsapp_base.serializers import (
    WhatsAppBusinessContactSerializer,
)
from ..views import WhatsAppCloudViewSet
from rest_framework.exceptions import ValidationError


User = get_user_model()


FACEBOOK_CONVERSATION_API_PATH = (
    "marketplace.core.types.channels.whatsapp_base."
    + "requests.facebook.FacebookConversationAPI.conversations"
)


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

    # WhatsApp applications cannot be deleted.
    def test_preventing_destroy_app(self):
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

    @patch("marketplace.clients.flows.client.FlowsClient.detail_channel")
    @patch("marketplace.clients.flows.client.FlowsClient.update_config")
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

    @patch("marketplace.clients.flows.client.FlowsClient.get_sent_messagers")
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

    @patch(FACEBOOK_CONVERSATION_API_PATH)
    def test_get_conversations(self, mock_conversations):
        mock_conversations.return_value = MockConversation()

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(FACEBOOK_CONVERSATION_API_PATH)
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


class WhatsAppCloudConversationsPermissionTestCase(
    PermissionTestCaseMixin, APIBaseTestCase
):
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
        self.start_date = "6-1-2023"
        self.end_date = "6-30-2023"
        self.url = reverse(
            "wpp-cloud-app-conversations", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view({"get": "conversations"})

    @patch(FACEBOOK_CONVERSATION_API_PATH)
    @override_settings(
        ALLOW_CRM_ACCESS=True, CRM_EMAILS_LIST=["otheremail@marketplace.ai"]
    )
    def test_get_conversations_allow_crm_access_true_email_not_in_list(
        self, mock_conversations
    ):
        mock_conversations.return_value = MockConversation()

        # Use PermissionTestCaseMixin to revoke permission
        self.revoke_permission(self.user, "can_communicate_internally")

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(FACEBOOK_CONVERSATION_API_PATH)
    def test_get_conversations_without_authorization(self, mock_conversations):
        mock_conversations.return_value = MockConversation()

        # Use PermissionTestCaseMixin to revoke permission
        self.revoke_permission(self.user, "can_communicate_internally")

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(FACEBOOK_CONVERSATION_API_PATH)
    def test_get_conversations_with_internal_communication_permission(
        self, mock_conversations
    ):
        mock_conversations.return_value = MockConversation()

        # Use PermissionTestCaseMixin to grant permission
        self.grant_permission(self.user, "can_communicate_internally")

        params = {
            "start": self.start_date,
            "end": self.end_date,
        }
        response = self.request.get(self.url, params=params, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MockBusinessMetaService:
    def configure_whatsapp_cloud(
        self, auth_code, waba_id, phone_number_id, waba_currency
    ):
        return {
            "user_access_token": "mock_user_access_token",
            "business_id": "mock_business_id",
            "message_template_namespace": "mock_message_template_namespace",
            "allocation_config_id": "mock_allocation_config_id",
        }

    def register_phone_number(self, phone_number_id, user_access_token, data):
        pass


class MockPhoneNumbersService:
    def get_phone_number(self, phone_number_id):
        return {
            "display_phone_number": "mock_display_phone_number",
            "verified_name": "mock_verified_name",
        }


class MockFlowsService:
    def create_wac_channel(self, email, project_uuid, phone_number_id, config):
        return {"uuid": str(uuid.uuid4())}


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

        # Mock usecases
        self.mock_waba_sync = Mock()
        self.mock_waba_sync.sync_whatsapp_cloud_waba.return_value = {}

        self.mock_phone_sync = Mock()
        self.mock_phone_sync.sync_whatsapp_cloud_phone_number.return_value = {
            "status": "success"
        }

        self.mock_insights_sync = Mock()
        self.mock_insights_sync.sync_whatsapp_cloud_insights.return_value = {
            "status": "success"
        }

        # Mock services
        self.mock_business_meta_service = MockBusinessMetaService()
        self.mock_phone_numbers_service = MockPhoneNumbersService()
        self.mock_flows_service = MockFlowsService()

        patcher_waba_sync = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.WABASyncUseCase",
            new=Mock(return_value=self.mock_waba_sync),
        )

        patcher_phone_sync = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.PhoneNumberSyncUseCase",
            new=Mock(return_value=self.mock_phone_sync),
        )

        patcher_insights_sync = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.WhatsAppInsightsSyncUseCase",
            new=Mock(return_value=self.mock_insights_sync),
        )

        patcher_biz_meta = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.BusinessMetaService",
            new=Mock(return_value=self.mock_business_meta_service),
        )
        patcher_phone = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.PhoneNumbersService",
            new=Mock(return_value=self.mock_phone_numbers_service),
        )
        patcher_flows = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.FlowsService",
            new=Mock(return_value=self.mock_flows_service),
        )
        patcher_celery = patch("marketplace.celery.app.send_task", new=Mock())

        patcher_waba_sync.start()
        patcher_phone_sync.start()
        patcher_insights_sync.start()
        patcher_biz_meta.start()
        patcher_phone.start()
        patcher_flows.start()
        patcher_celery.start()

        self.addCleanup(patcher_waba_sync.stop)
        self.addCleanup(patcher_phone_sync.stop)
        self.addCleanup(patcher_insights_sync.stop)
        self.addCleanup(patcher_biz_meta.stop)
        self.addCleanup(patcher_phone.stop)
        self.addCleanup(patcher_flows.stop)
        self.addCleanup(patcher_celery.stop)

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_whatsapp_cloud_success(self):
        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            App.objects.filter(project_uuid=self.payload["project_uuid"]).exists()
        )
        app = App.objects.get(project_uuid=self.payload["project_uuid"])
        self.assertEqual(app.config["wa_number"], "mock_display_phone_number")
        self.assertEqual(app.config["wa_verified_name"], "mock_verified_name")
        self.assertEqual(app.config["wa_waba_id"], self.payload["waba_id"])
        self.assertEqual(app.config["wa_currency"], "USD")
        self.assertEqual(app.config["wa_business_id"], "mock_business_id")
        self.assertEqual(
            app.config["wa_message_template_namespace"],
            "mock_message_template_namespace",
        )
        self.assertEqual(len(app.config["wa_pin"]), 6)
        self.assertEqual(app.config["wa_user_token"], "mock_user_access_token")

    def test_create_whatsapp_cloud_failure_on_exchange_auth_code(self):
        self.mock_business_meta_service.configure_whatsapp_cloud = Mock(
            side_effect=ValidationError("Invalid auth code")
        )

        response = self.request.post(self.url, body=self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid auth code"])

    def test_create_whatsapp_cloud_failure_on_get_phone_number(self):
        self.mock_phone_numbers_service.get_phone_number = Mock(
            side_effect=ValidationError("Invalid phone number ID")
        )

        response = self.request.post(self.url, body=self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid phone number ID"])

    def test_create_whatsapp_cloud_failure_on_register_phone_number(self):
        self.mock_business_meta_service.register_phone_number = Mock(
            side_effect=ValidationError("Registration failed")
        )

        response = self.request.post(self.url, body=self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Registration failed"])


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


class UpdateMmliteStatusTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            config={"existing_key": "existing_value"},
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
            "wpp-cloud-app-update-mmlite-status", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view({"patch": "update_mmlite_status"})

    def test_update_mmlite_status_to_active_success(self):
        data = {"status": "active"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the app was updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertEqual(app.config["mmlite_status"], "active")

        # Verify existing config is preserved
        self.assertEqual(app.config["existing_key"], "existing_value")

        # Verify response contains the updated app data
        self.assertIn("uuid", response.json)
        self.assertIn("config", response.json)
        self.assertEqual(response.json["config"]["mmlite_status"], "active")

    def test_update_mmlite_status_to_in_progress_success(self):
        data = {"status": "in_progress"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the app was updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertEqual(app.config["mmlite_status"], "in_progress")

        # Verify existing config is preserved
        self.assertEqual(app.config["existing_key"], "existing_value")

        # Verify response contains the updated app data
        self.assertIn("uuid", response.json)
        self.assertIn("config", response.json)
        self.assertEqual(response.json["config"]["mmlite_status"], "in_progress")

    def test_update_mmlite_status_invalid_status(self):
        data = {"status": "invalid_status"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_missing_status_field(self):
        data = {"other_field": "value"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_empty_status(self):
        data = {"status": ""}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_null_status(self):
        data = {"status": None}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_empty_request_body(self):
        data = {}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_case_sensitive(self):
        # Test that status validation is case sensitive
        data = {"status": "ACTIVE"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json, ["Invalid status"])

        # Verify the app was not updated
        app = App.objects.get(uuid=self.app.uuid)
        self.assertNotIn("mmlite_status", app.config)

    def test_update_mmlite_status_overwrites_existing_status(self):
        # Set an initial status
        self.app.config["mmlite_status"] = "in_progress"
        self.app.save()

        # Update to a different status
        data = {"status": "active"}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the status was overwritten
        app = App.objects.get(uuid=self.app.uuid)
        self.assertEqual(app.config["mmlite_status"], "active")

    def test_update_mmlite_status_nonexistent_app(self):
        nonexistent_uuid = str(uuid.uuid4())
        url = reverse(
            "wpp-cloud-app-update-mmlite-status", kwargs={"uuid": nonexistent_uuid}
        )
        data = {"status": "active"}

        response = self.request.patch(url, data, uuid=nonexistent_uuid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_mmlite_status_without_authorization(self):
        # Create app without user authorization
        app_without_auth = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        url = reverse(
            "wpp-cloud-app-update-mmlite-status", kwargs={"uuid": app_without_auth.uuid}
        )
        data = {"status": "active"}

        response = self.request.patch(url, data, uuid=app_without_auth.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
