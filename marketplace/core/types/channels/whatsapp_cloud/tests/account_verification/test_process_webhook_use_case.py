"""Tests for ProcessCertificationWebhookUseCase."""

import uuid
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    CONFIG_KEY,
    VerificationStatus,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.usecases import (
    ProcessCertificationWebhookUseCase,
)


User = get_user_model()


class ProcessCertificationWebhookUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@marketplace.ai")
        self.app = App.objects.create(
            code="wpp-cloud",
            config={"wa_business_id": "client_456", "wa_waba_id": "waba_999"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.connect_service = MagicMock()
        self.use_case = ProcessCertificationWebhookUseCase(
            connect_service=self.connect_service
        )

    def _value(self, status=VerificationStatus.APPROVED, reasons=None):
        return {
            "event": "PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE",
            "partner_client_certification_info": {
                "client_business_id": "client_456",
                "status": status,
                "rejection_reasons": reasons or [],
            },
        }

    def test_approved_event_persists_and_notifies_connect(self):
        self.use_case.execute(waba_id="waba_999", value=self._value())

        self.app.refresh_from_db()
        persisted = self.app.config[CONFIG_KEY]
        self.assertEqual(persisted["status"], VerificationStatus.APPROVED)
        self.assertEqual(persisted["rejection_reasons"], [])

        self.connect_service.notify_business_verification.assert_called_once_with(
            user_email="owner@marketplace.ai",
            status=VerificationStatus.APPROVED,
            rejection_reasons=[],
            verification_attempts=0,
        )

    def test_failed_event_keeps_rejection_reasons(self):
        self.use_case.execute(
            waba_id="waba_999",
            value=self._value(
                status=VerificationStatus.FAILED,
                reasons=["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS", "NONE"],
            ),
        )

        self.app.refresh_from_db()
        persisted = self.app.config[CONFIG_KEY]
        self.assertEqual(persisted["status"], VerificationStatus.FAILED)
        self.assertEqual(
            persisted["rejection_reasons"], ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"]
        )

        self.connect_service.notify_business_verification.assert_called_once_with(
            user_email="owner@marketplace.ai",
            status=VerificationStatus.FAILED,
            rejection_reasons=["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"],
            verification_attempts=0,
        )

    def test_ignores_event_without_client_business_id(self):
        value = self._value()
        value["partner_client_certification_info"].pop("client_business_id")

        self.use_case.execute(waba_id="waba_999", value=value)

        self.app.refresh_from_db()
        self.assertNotIn(CONFIG_KEY, self.app.config)
        self.connect_service.notify_business_verification.assert_not_called()

    def test_ignores_unmatched_app(self):
        self.use_case.execute(
            waba_id="waba_other",
            value={
                "event": "PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE",
                "partner_client_certification_info": {
                    "client_business_id": "client_unmapped",
                    "status": VerificationStatus.APPROVED,
                },
            },
        )
        self.connect_service.notify_business_verification.assert_not_called()

    def test_ignores_unsupported_status(self):
        self.use_case.execute(
            waba_id="waba_999",
            value=self._value(status=VerificationStatus.PENDING),
        )
        self.app.refresh_from_db()
        self.assertNotIn(CONFIG_KEY, self.app.config)
        self.connect_service.notify_business_verification.assert_not_called()

    def test_duplicate_event_does_not_notify_again(self):
        self.use_case.execute(waba_id="waba_999", value=self._value())
        self.connect_service.reset_mock()

        self.use_case.execute(waba_id="waba_999", value=self._value())
        self.connect_service.notify_business_verification.assert_not_called()

    def test_falls_back_to_waba_id_when_no_business_id_match(self):
        other_app = App.objects.create(
            code="wpp-cloud",
            config={"wa_waba_id": "waba_other", "wa_business_id": "client_other"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        value = {
            "event": "PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE",
            "partner_client_certification_info": {
                "client_business_id": "client_unmatched",
                "status": VerificationStatus.APPROVED,
            },
        }
        self.use_case.execute(waba_id="waba_other", value=value)

        other_app.refresh_from_db()
        self.assertEqual(
            other_app.config[CONFIG_KEY]["status"], VerificationStatus.APPROVED
        )

    def test_connect_failure_does_not_crash(self):
        self.connect_service.notify_business_verification.side_effect = Exception(
            "boom"
        )
        self.use_case.execute(waba_id="waba_999", value=self._value())
        self.app.refresh_from_db()
        self.assertEqual(
            self.app.config[CONFIG_KEY]["status"], VerificationStatus.APPROVED
        )
