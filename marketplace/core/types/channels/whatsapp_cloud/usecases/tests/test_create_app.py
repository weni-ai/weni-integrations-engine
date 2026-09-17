import uuid
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.usecases.create_app import (
    CreateWhatsAppCloudAppDTO,
    CreateWhatsAppCloudAppUseCase,
    PHONE_NUMBER_FIELDS,
)


User = get_user_model()

CREATE_APP_MODULE = "marketplace.core.types.channels.whatsapp_cloud.usecases.create_app"


class CreateWhatsAppCloudAppUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.project_uuid = str(uuid.uuid4())
        self.channel_uuid = str(uuid.uuid4())
        self.dto = CreateWhatsAppCloudAppDTO(
            project_uuid=self.project_uuid,
            waba_id="waba-id",
            phone_number_id="phone-id",
            auth_code="auth-code",
            created_by=self.user,
            user_email=self.user.email,
        )

        self.business_service = Mock()
        self.business_service.configure_whatsapp_cloud.return_value = {
            "user_access_token": "user-token",
            "business_id": "business-id",
            "message_template_namespace": "namespace",
            "allocation_config_id": "allocation-id",
            "dataset_id": "dataset-id",
        }
        self.phone_numbers_service = Mock()
        self.phone_numbers_service.get_phone_number.return_value = {
            "display_phone_number": "+55 11 99999-0000",
            "verified_name": "Acme",
        }
        self.template_service = Mock()
        self.template_service.setup_insights.return_value = True
        self.flows_service = Mock()
        self.flows_service.create_wac_channel.return_value = {"uuid": self.channel_uuid}

        self.use_case = CreateWhatsAppCloudAppUseCase(
            business_service=self.business_service,
            phone_numbers_service=self.phone_numbers_service,
            template_service=self.template_service,
            flows_service=self.flows_service,
        )

        patcher_waba = patch(
            f"{CREATE_APP_MODULE}.WABASyncUseCase", return_value=Mock()
        )
        patcher_phone = patch(
            f"{CREATE_APP_MODULE}.PhoneNumberSyncUseCase", return_value=Mock()
        )
        patcher_insights = patch(
            f"{CREATE_APP_MODULE}.WhatsAppInsightsSyncUseCase", return_value=Mock()
        )
        patcher_mmlite = patch(
            f"{CREATE_APP_MODULE}.SyncMmliteStatusUseCase", return_value=Mock()
        )
        patcher_waba.start()
        patcher_phone.start()
        patcher_insights.start()
        patcher_mmlite.start()
        self.addCleanup(patcher_waba.stop)
        self.addCleanup(patcher_phone.stop)
        self.addCleanup(patcher_insights.stop)
        self.addCleanup(patcher_mmlite.stop)

    def test_execute_registers_phone_number_when_not_connected(self):
        with patch(f"{CREATE_APP_MODULE}.get_random_string", return_value="123456"):
            app = self.use_case.execute(self.dto)

        self.business_service.configure_whatsapp_cloud.assert_called_once_with(
            self.dto.auth_code, self.dto.waba_id, self.dto.phone_number_id, "BRL"
        )
        self.phone_numbers_service.get_phone_number.assert_called_once_with(
            self.dto.phone_number_id, fields=PHONE_NUMBER_FIELDS
        )
        self.business_service.register_phone_number.assert_called_once_with(
            self.dto.phone_number_id,
            "user-token",
            dict(messaging_product="whatsapp", pin="123456"),
        )
        self.flows_service.create_wac_channel.assert_called_once()
        self.assertEqual(app.config["wa_pin"], "123456")
        self.assertEqual(app.config["wa_phone_number_id"], self.dto.phone_number_id)
        self.assertTrue(
            App.objects.filter(project_uuid=self.project_uuid, uuid=app.uuid).exists()
        )

    def test_execute_skips_register_when_connected_on_cloud_api(self):
        self.phone_numbers_service.get_phone_number.return_value = {
            "display_phone_number": "+55 11 99999-0000",
            "verified_name": "Acme",
            "status": "CONNECTED",
            "platform_type": "CLOUD_API",
        }

        app = self.use_case.execute(self.dto)

        self.business_service.configure_whatsapp_cloud.assert_called_once()
        self.business_service.register_phone_number.assert_not_called()
        self.flows_service.create_wac_channel.assert_called_once()
        self.assertIsNone(app.config["wa_pin"])
        self.assertEqual(str(app.flow_object_uuid), self.channel_uuid)
        self.assertTrue(app.configured)

    def test_execute_registers_when_connected_without_cloud_api_platform(self):
        self.phone_numbers_service.get_phone_number.return_value = {
            "display_phone_number": "+55 11 99999-0000",
            "verified_name": "Acme",
            "status": "CONNECTED",
            "platform_type": "ON_PREMISE",
        }

        with patch(f"{CREATE_APP_MODULE}.get_random_string", return_value="654321"):
            app = self.use_case.execute(self.dto)

        self.business_service.register_phone_number.assert_called_once()
        self.assertEqual(app.config["wa_pin"], "654321")

    def test_execute_registers_when_cloud_api_without_connected_status(self):
        self.phone_numbers_service.get_phone_number.return_value = {
            "display_phone_number": "+55 11 99999-0000",
            "verified_name": "Acme",
            "status": "PENDING",
            "platform_type": "CLOUD_API",
        }

        with patch(f"{CREATE_APP_MODULE}.get_random_string", return_value="111111"):
            app = self.use_case.execute(self.dto)

        self.business_service.register_phone_number.assert_called_once()
        self.assertEqual(app.config["wa_pin"], "111111")

    def test_execute_does_not_create_app_when_register_fails(self):
        self.business_service.register_phone_number.side_effect = Exception(
            "Registration failed"
        )

        with self.assertRaisesMessage(Exception, "Registration failed"):
            self.use_case.execute(self.dto)

        self.assertFalse(App.objects.filter(project_uuid=self.project_uuid).exists())
        self.flows_service.create_wac_channel.assert_not_called()
