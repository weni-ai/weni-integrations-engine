from unittest import TestCase
from unittest.mock import MagicMock, patch

from marketplace.wpp_templates.utils import TemplateStatusUpdateHandler


class TestTemplateStatusUpdateHandler(TestCase):
    def setUp(self):
        # Set up mock services and objects
        self.mock_flows = MagicMock()
        self.mock_commerce = MagicMock()
        self.mock_use_case = MagicMock()
        self.mock_logger = MagicMock()

        # Set up mock app and template
        self.app = MagicMock()
        self.template = MagicMock()
        self.template.name = "order_confirmation"
        self.template.gallery_version = "v1"

        # Set up mock translation
        self.translation = MagicMock()
        self.translation.status = "PENDING"
        self.translation.language = "en"
        self.translation.message_template_id = "123"
        self.translation.template = self.template
        self.translation.headers.all.return_value = []
        self.translation.buttons.all.return_value = []

        # Initialize the handler with mock services
        self.handler = TemplateStatusUpdateHandler(
            flows_service=self.mock_flows,
            commerce_service=self.mock_commerce,
            status_use_case_factory=lambda app: self.mock_use_case,
            logger=self.mock_logger,
        )

    @patch("marketplace.wpp_templates.utils.TemplateSyncUseCase.sync_templates")
    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_handle_status_change_triggers_all_services(self, mock_extract, mock_sync):
        # Test that all services are triggered when status changes
        self.handler.handle(
            app=self.app,
            template=self.template,
            translation=self.translation,
            status="APPROVED",
            webhook={"webhook": "info"},
        )
        self.translation.save.assert_called_once()
        self.mock_commerce.send_gallery_template_version.assert_called_once()
        self.mock_flows.update_facebook_templates_webhook.assert_not_called()
        self.mock_use_case.update_template_status.assert_called_once()
        self.mock_use_case.synchronize_all_stored_templates.assert_called_once()

    @patch("marketplace.wpp_templates.utils.TemplateSyncUseCase.sync_templates")
    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_handle_status_unchanged_triggers_external_services(
        self, mock_extract, mock_sync
    ):
        # Test that external services are triggered when status is unchanged
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
        self.mock_flows.update_facebook_templates_webhook.assert_not_called()
        self.mock_use_case.update_template_status.assert_called_once()

    @patch("marketplace.wpp_templates.utils.TemplateSyncUseCase.sync_templates")
    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_commerce_fails_but_others_continue(self, mock_extract, mock_sync):
        # Test that other services continue when commerce fails
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

    @patch("marketplace.wpp_templates.utils.TemplateSyncUseCase.sync_templates")
    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_flows_fails_but_others_continue(self, mock_extract, mock_sync):
        # Force template without gallery_version to trigger Flows directly
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

    @patch("marketplace.wpp_templates.utils.TemplateSyncUseCase.sync_templates")
    @patch(
        "marketplace.wpp_templates.utils.extract_template_data",
        return_value={"mocked": "data"},
    )
    def test_status_sync_fails(self, mock_extract, mock_sync):
        # Test that other services continue when status sync fails
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
