"""Tests for SubmitAccountVerificationUseCase."""

import uuid
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    CONFIG_KEY,
    VerificationStatus,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.dto import (
    SubmitAccountVerificationDTO,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.usecases.submit_account_verification import (
    SubmitAccountVerificationUseCase,
)


User = get_user_model()


@override_settings(WHATSAPP_BSP_BUSINESS_ID="partner_123")
class SubmitAccountVerificationUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.app = App.objects.create(
            code="wpp-cloud",
            config={"wa_business_id": "client_456", "wa_waba_id": "waba_999"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.service = MagicMock()
        self.service.submit.return_value = {
            "success": True,
            "verification_attempts": 1,
            "message": "ok",
        }

        document = MagicMock()
        document.name = "doc.pdf"
        document.read.return_value = b"%PDF-1.4"
        document.content_type = "application/pdf"
        self.documents = [document]

        self.use_case = SubmitAccountVerificationUseCase(
            verification_service=self.service,
            partner_business_id="partner_123",
        )

    def _dto(self):
        return SubmitAccountVerificationDTO(
            app_uuid=str(self.app.uuid),
            documents=self.documents,
        )

    def test_submit_persists_pending_state(self):
        state_dto = self.use_case.execute(self._dto())

        self.app.refresh_from_db()
        persisted = self.app.config[CONFIG_KEY]

        self.assertEqual(state_dto.status, VerificationStatus.PENDING)
        self.assertEqual(persisted["status"], VerificationStatus.PENDING)
        self.assertEqual(persisted["verification_attempts"], 1)
        self.assertEqual(persisted["rejection_reasons"], [])
        self.assertIsNotNone(persisted["submitted_at"])
        self.service.submit.assert_called_once_with(
            partner_business_id="partner_123",
            end_business_id="client_456",
            documents=self.documents,
        )

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="")
    def test_raises_when_partner_business_id_missing(self):
        use_case = SubmitAccountVerificationUseCase(
            verification_service=self.service,
            partner_business_id="",
        )
        with self.assertRaises(ValidationError):
            use_case.execute(self._dto())
        self.service.submit.assert_not_called()

    def test_raises_when_app_is_not_wpp_cloud(self):
        self.app.code = "wpp"
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(self._dto())

    def test_raises_when_business_id_is_missing(self):
        self.app.config = {"wa_waba_id": "waba_999"}
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(self._dto())

    def test_raises_when_already_approved(self):
        self.app.config[CONFIG_KEY] = {
            "status": VerificationStatus.APPROVED,
            "verification_attempts": 1,
        }
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(self._dto())

    def test_raises_when_a_submission_is_pending(self):
        self.app.config[CONFIG_KEY] = {
            "status": VerificationStatus.PENDING,
            "verification_attempts": 1,
        }
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(self._dto())

    def test_raises_when_max_attempts_reached(self):
        self.app.config[CONFIG_KEY] = {
            "status": VerificationStatus.FAILED,
            "verification_attempts": 3,
        }
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(self._dto())

    def test_raises_when_app_does_not_exist(self):
        dto = SubmitAccountVerificationDTO(
            app_uuid=str(uuid.uuid4()), documents=self.documents
        )
        with self.assertRaises(ValidationError):
            self.use_case.execute(dto)
