from unittest import TestCase
from unittest.mock import MagicMock, patch

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

    def test_commerce_notified_even_when_scheduler_raises(self):
        self.mock_scheduler.schedule.side_effect = Exception("schedule error")

        with self.assertRaises(Exception):
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
