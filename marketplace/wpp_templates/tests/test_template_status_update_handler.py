import uuid
from copy import deepcopy
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase

from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    PARAMETER_FORMAT_NAMED,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.utils import TemplateStatusUpdateHandler


class TestTemplateStatusUpdateHandler(TestCase):
    def setUp(self):
        self.mock_flows = MagicMock()
        self.mock_commerce = MagicMock()
        self.mock_use_case = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_scheduler = MagicMock()

        self.app = MagicMock()
        self.app.uuid = "app-uuid-123"
        self.template = MagicMock()
        self.template.name = "order_confirmation"
        self.template.gallery_version = "v1"

        self.translation = MagicMock()
        self.translation.status = "PENDING"
        self.translation.language = "en"
        self.translation.message_template_id = "123"
        self.translation.template = self.template
        self.translation.headers.all.return_value = []
        self.translation.buttons.all.return_value = []

        self.handler = TemplateStatusUpdateHandler(
            flows_service=self.mock_flows,
            commerce_service=self.mock_commerce,
            status_use_case_factory=lambda app: self.mock_use_case,
            sync_scheduler=self.mock_scheduler,
            logger=self.mock_logger,
        )

    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_handle_status_change_triggers_all_services(self, mock_extract):
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.translation.save.assert_called_once()
        self.mock_commerce.send_gallery_template_version.assert_called_once()
        self.mock_scheduler.schedule.assert_called_once_with("app-uuid-123")
        self.mock_flows.update_facebook_templates_webhook.assert_not_called()
        self.mock_use_case.update_template_status.assert_called_once()
        self.mock_use_case.synchronize_all_stored_templates.assert_called_once()

    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_handle_status_unchanged_triggers_external_services(self, mock_extract):
        self.translation.status = "APPROVED"
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.translation.save.assert_not_called()
        self.mock_commerce.send_gallery_template_version.assert_called_once()
        self.mock_scheduler.schedule.assert_called_once_with("app-uuid-123")
        self.mock_flows.update_facebook_templates_webhook.assert_not_called()
        self.mock_use_case.update_template_status.assert_called_once()

    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_commerce_fails_but_others_continue(self, mock_extract):
        self.mock_commerce.send_gallery_template_version.side_effect = Exception(
            "Commerce error"
        )
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.mock_logger.error.assert_any_call(
            "[Commerce] Failed to send gallery version for template: order_confirmation, "
            "translation: en, status: APPROVED, error: Commerce error"
        )
        self.mock_scheduler.schedule.assert_called_once_with("app-uuid-123")

    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_flows_fails_but_others_continue(self, mock_extract):
        self.template.gallery_version = None
        self.mock_flows.update_facebook_templates_webhook.side_effect = Exception(
            "Flows error"
        )
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.mock_logger.error.assert_any_call(
            f"[Flows] Failed to send template update: {self.template.name}, "
            f"translation: {self.translation.language}, error: Flows error"
        )
        self.mock_scheduler.schedule.assert_not_called()

    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_status_sync_fails(self, mock_extract):
        self.mock_use_case.update_template_status.side_effect = Exception("Sync error")
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.mock_logger.error.assert_any_call(
            f"[StatusSync] Failed to update template library status for: {self.template.name}. Error: Sync error"
        )

    def test_scheduler_failure_does_not_block_status_sync(self):
        self.mock_scheduler.schedule.side_effect = Exception("schedule error")

        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )

        self.mock_commerce.send_gallery_template_version.assert_called_once_with(
            gallery_version_uuid="v1", status="APPROVED"
        )
        self.mock_logger.error.assert_any_call(
            "[Scheduler] Failed to schedule sync for app app-uuid-123: schedule error"
        )
        self.mock_use_case.update_template_status.assert_called_once_with(
            template_name="order_confirmation",
            new_status="APPROVED",
        )
        self.mock_use_case.synchronize_all_stored_templates.assert_called_once()


User = get_user_model()

GALLERY_NAMED_BODY = "Olá {{nome}}, sua cota {{cota}}"
GALLERY_NAMED_PARAMS = [
    {"param_name": "nome", "example": "João"},
    {"param_name": "cota", "example": "3/12"},
]


class TemplateStatusUpdateGalleryPreservationTestCase(DjangoTestCase):
    def setUp(self):
        self.mock_flows = MagicMock()
        self.mock_commerce = MagicMock()
        self.mock_use_case = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_scheduler = MagicMock()

        self.app = App.objects.create(
            config={"wa_waba_id": "waba-gallery", "wa_user_token": "test-token"},
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=User.objects.get_admin_user(),
            flow_object_uuid=uuid.uuid4(),
        )
        self.template = TemplateMessage.objects.create(
            name="cota_aviso",
            app=self.app,
            category="UTILITY",
            template_type="TEXT",
            created_by=User.objects.get_admin_user(),
            gallery_version=uuid.uuid4(),
        )
        self.translation = TemplateTranslation.objects.create(
            template=self.template,
            status="PENDING",
            body=GALLERY_NAMED_BODY,
            language="pt_BR",
            country="BR",
            variable_count=2,
            message_template_id="1001",
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=list(GALLERY_NAMED_PARAMS),
            parameter_anomaly=None,
        )
        self.handler = TemplateStatusUpdateHandler(
            flows_service=self.mock_flows,
            commerce_service=self.mock_commerce,
            status_use_case_factory=lambda app: self.mock_use_case,
            sync_scheduler=self.mock_scheduler,
            logger=self.mock_logger,
        )

    @patch("marketplace.wpp_templates.usecases.template_sync.FlowsClient")
    @patch("marketplace.wpp_templates.usecases.template_sync.FacebookClient")
    @patch(
        "marketplace.wpp_templates.usecases.template_sync.TemplateService."
        "list_template_messages"
    )
    def test_gallery_resync_preserves_named_params(
        self, mock_list_templates, _mock_facebook, _mock_flows_client
    ):
        mock_list_templates.return_value = {
            "data": [
                {
                    "id": "1001",
                    "name": "cota_aviso",
                    "language": "pt_BR",
                    "status": "APPROVED",
                    "category": "UTILITY",
                    "parameter_format": "NAMED",
                    "components": [
                        {
                            "type": "BODY",
                            "text": GALLERY_NAMED_BODY,
                            "example": {"body_text_named_params": GALLERY_NAMED_PARAMS},
                        }
                    ],
                }
            ]
        }
        before = (
            self.translation.parameter_format,
            deepcopy(self.translation.body_named_params),
            deepcopy(self.translation.parameter_anomaly),
        )

        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )

        self.translation.refresh_from_db()
        self.assertEqual(
            (
                self.translation.parameter_format,
                self.translation.body_named_params,
                self.translation.parameter_anomaly,
            ),
            before,
        )
        self.assertEqual(
            [entry["param_name"] for entry in self.translation.body_named_params],
            ["nome", "cota"],
        )
        self.mock_flows.update_facebook_templates_webhook.assert_not_called()
        self.mock_commerce.send_gallery_template_version.assert_called_once()
        self.mock_scheduler.schedule.assert_called_once_with(str(self.app.uuid))
