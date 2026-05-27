"""Integration test: AccountUpdateWebhookEventProcessor dispatches the certification event."""

import uuid
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    CERTIFICATION_EVENT,
)
from marketplace.core.types.channels.whatsapp_cloud.processors import (
    AccountUpdateWebhookEventProcessor,
)


User = get_user_model()


class AccountUpdateWebhookEventProcessorDispatchTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.app = App.objects.create(
            code="wpp-cloud",
            config={"wa_business_id": "client_456", "wa_waba_id": "waba_999"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.use_case = MagicMock()
        self.processor = AccountUpdateWebhookEventProcessor(
            certification_use_case=self.use_case
        )

    def test_dispatches_certification_event_to_use_case(self):
        value = {
            "event": CERTIFICATION_EVENT,
            "partner_client_certification_info": {
                "client_business_id": "client_456",
                "status": "APPROVED",
            },
        }
        self.processor.process_account_update("waba_999", value, {"raw": True})
        self.use_case.execute.assert_called_once_with(waba_id="waba_999", value=value)

    def test_mmlite_event_still_works(self):
        value = {"event": "MM_LITE_TERMS_SIGNED"}
        self.processor.process_account_update("waba_999", value, {})
        self.app.refresh_from_db()
        self.assertEqual(self.app.config["mmlite_status"], "active")
        self.use_case.execute.assert_not_called()

    def test_unknown_event_is_ignored(self):
        value = {"event": "SOMETHING_ELSE"}
        self.processor.process_account_update("waba_999", value, {})
        self.use_case.execute.assert_not_called()
