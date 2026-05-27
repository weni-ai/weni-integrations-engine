"""Tests for GetAccountVerificationStatusUseCase."""

import uuid
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from marketplace.applications.models import App
from marketplace.clients.exceptions import CustomAPIException
from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    CONFIG_KEY,
    UIState,
    VerificationStatus,
    build_cache_key,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.usecases import (
    GetAccountVerificationStatusUseCase,
)


User = get_user_model()


@override_settings(
    WHATSAPP_BSP_BUSINESS_ID="partner_123",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "get-account-verification-tests",
        }
    },
)
class GetAccountVerificationStatusUseCaseTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.app = App.objects.create(
            code="wpp-cloud",
            config={"wa_business_id": "client_456", "wa_waba_id": "waba_999"},
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.service = MagicMock()
        self.use_case = GetAccountVerificationStatusUseCase(
            verification_service=self.service,
            partner_business_id="partner_123",
            ttl=60,
        )

    def tearDown(self):
        cache.clear()

    def test_returns_not_started_when_no_submissions_and_no_local_state(self):
        self.service.list_submissions.return_value = {"data": []}

        state = self.use_case.execute(str(self.app.uuid))

        self.assertEqual(state.ui_state, UIState.NOT_STARTED)
        self.assertEqual(state.verification_attempts, 0)

    def test_caches_meta_response_to_avoid_repeated_calls(self):
        self.service.list_submissions.return_value = {
            "data": [
                {
                    "id": "sub_1",
                    "verification_status": "APPROVED",
                    "submitted_time": "2026-05-20T00:00:00Z",
                    "update_time": "2026-05-21T00:00:00Z",
                    "rejection_reasons": [],
                }
            ]
        }

        first = self.use_case.execute(str(self.app.uuid))
        second = self.use_case.execute(str(self.app.uuid))

        self.assertEqual(first.status, VerificationStatus.APPROVED)
        self.assertEqual(second.status, VerificationStatus.APPROVED)
        self.service.list_submissions.assert_called_once()

    def test_persists_state_into_app_config(self):
        self.service.list_submissions.return_value = {
            "data": [
                {
                    "id": "sub_1",
                    "verification_status": "FAILED",
                    "submitted_time": "2026-05-20T00:00:00Z",
                    "update_time": "2026-05-21T00:00:00Z",
                    "rejection_reasons": ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"],
                }
            ]
        }

        state = self.use_case.execute(str(self.app.uuid))

        self.app.refresh_from_db()
        persisted = self.app.config[CONFIG_KEY]
        self.assertEqual(state.ui_state, UIState.FAILED)
        self.assertEqual(persisted["status"], VerificationStatus.FAILED)
        self.assertEqual(persisted["submission_id"], "sub_1")
        self.assertEqual(
            persisted["rejection_reasons"], ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"]
        )

    def test_meta_failure_falls_back_to_local_state(self):
        self.app.config[CONFIG_KEY] = {
            "status": VerificationStatus.PENDING,
            "verification_attempts": 1,
            "submission_id": "sub_local",
        }
        self.app.save()
        self.service.list_submissions.side_effect = CustomAPIException(
            detail="boom", status_code=500
        )

        state = self.use_case.execute(str(self.app.uuid))

        self.assertEqual(state.status, VerificationStatus.PENDING)
        self.assertFalse(cache.get(build_cache_key("client_456")))

    def test_serves_from_cache_without_calling_meta(self):
        cache.set(
            build_cache_key("client_456"),
            [
                {
                    "id": "sub_cached",
                    "verification_status": "APPROVED",
                    "submitted_time": "2026-05-20T00:00:00Z",
                    "update_time": "2026-05-21T00:00:00Z",
                    "rejection_reasons": [],
                }
            ],
            60,
        )

        state = self.use_case.execute(str(self.app.uuid))

        self.assertEqual(state.status, VerificationStatus.APPROVED)
        self.service.list_submissions.assert_not_called()

    def test_raises_when_app_does_not_exist(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.use_case.execute(str(uuid.uuid4()))

    def test_raises_when_app_is_not_wpp_cloud(self):
        from rest_framework.exceptions import ValidationError

        self.app.code = "wpp"
        self.app.save()
        with self.assertRaises(ValidationError):
            self.use_case.execute(str(self.app.uuid))

    def test_returns_local_state_when_business_id_missing(self):
        self.app.config = {}
        self.app.save()

        state = self.use_case.execute(str(self.app.uuid))

        self.assertEqual(state.ui_state, "not_started")
        self.service.list_submissions.assert_not_called()
