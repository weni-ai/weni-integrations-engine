"""Unit tests for state helpers (no DB / no network)."""

from django.test import TestCase

from marketplace.core.types.channels.whatsapp_cloud.account_verification.constants import (
    UIState,
    VerificationStatus,
)
from marketplace.core.types.channels.whatsapp_cloud.account_verification.state import (
    apply_submit_response,
    apply_webhook_event,
    merge_from_meta_submissions,
    read_state,
    to_dto,
)


class ReadStateTestCase(TestCase):
    def test_returns_copy_when_present(self):
        config = {"account_verification": {"status": VerificationStatus.PENDING}}
        state = read_state(config)
        state["status"] = "MUTATED"
        self.assertEqual(
            config["account_verification"]["status"], VerificationStatus.PENDING
        )

    def test_returns_empty_dict_when_missing(self):
        self.assertEqual(read_state({}), {})


class DeriveUIStateTestCase(TestCase):
    def test_not_started_when_state_is_empty(self):
        dto = to_dto({})
        self.assertEqual(dto.ui_state, UIState.NOT_STARTED)
        self.assertTrue(dto.can_submit)

    def test_pending(self):
        dto = to_dto(
            {
                "submission_id": "1",
                "status": VerificationStatus.PENDING,
                "verification_attempts": 1,
            }
        )
        self.assertEqual(dto.ui_state, UIState.PENDING)
        self.assertFalse(dto.can_submit)

    def test_approved(self):
        dto = to_dto(
            {
                "submission_id": "1",
                "status": VerificationStatus.APPROVED,
                "verification_attempts": 1,
            }
        )
        self.assertEqual(dto.ui_state, UIState.APPROVED)
        self.assertFalse(dto.can_submit)

    def test_failed_with_attempts_remaining(self):
        dto = to_dto(
            {
                "submission_id": "1",
                "status": VerificationStatus.FAILED,
                "verification_attempts": 1,
                "rejection_reasons": ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"],
            }
        )
        self.assertEqual(dto.ui_state, UIState.FAILED)
        self.assertTrue(dto.can_submit)
        self.assertEqual(dto.rejection_reasons, ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"])

    def test_blocked_when_attempts_reach_three(self):
        dto = to_dto(
            {
                "submission_id": "1",
                "status": VerificationStatus.FAILED,
                "verification_attempts": 3,
            }
        )
        self.assertEqual(dto.ui_state, UIState.BLOCKED)
        self.assertFalse(dto.can_submit)

    def test_drops_none_rejection_reason_sentinel(self):
        dto = to_dto(
            {
                "submission_id": "1",
                "status": VerificationStatus.APPROVED,
                "rejection_reasons": ["NONE"],
            }
        )
        self.assertEqual(dto.rejection_reasons, [])


class ApplySubmitResponseTestCase(TestCase):
    def test_sets_pending_and_attempts(self):
        state = {}
        apply_submit_response(state, {"success": True, "verification_attempts": 2})

        self.assertEqual(state["status"], VerificationStatus.PENDING)
        self.assertEqual(state["verification_attempts"], 2)
        self.assertEqual(state["rejection_reasons"], [])
        self.assertIsNotNone(state["submitted_at"])

    def test_preserves_highest_attempts(self):
        state = {"verification_attempts": 3}
        apply_submit_response(state, {"verification_attempts": 1})
        self.assertEqual(state["verification_attempts"], 3)


class MergeFromMetaSubmissionsTestCase(TestCase):
    def test_no_submissions_keeps_state_untouched(self):
        state = {"status": VerificationStatus.PENDING}
        merge_from_meta_submissions(state, [])
        self.assertEqual(state, {"status": VerificationStatus.PENDING})

    def test_picks_latest_submission(self):
        state = {}
        submissions = [
            {
                "id": "old",
                "verification_status": "FAILED",
                "submitted_time": "2026-05-01T00:00:00Z",
                "update_time": "2026-05-01T00:00:00Z",
                "rejection_reasons": ["NONE"],
            },
            {
                "id": "new",
                "verification_status": "APPROVED",
                "submitted_time": "2026-05-20T00:00:00Z",
                "update_time": "2026-05-21T00:00:00Z",
                "rejection_reasons": [],
            },
        ]
        merge_from_meta_submissions(state, submissions)
        self.assertEqual(state["submission_id"], "new")
        self.assertEqual(state["status"], VerificationStatus.APPROVED)
        self.assertEqual(state["updated_at_meta"], "2026-05-21T00:00:00Z")
        self.assertEqual(state["verification_attempts"], 2)


class ApplyWebhookEventTestCase(TestCase):
    def test_updates_status_and_reasons(self):
        state = {"status": VerificationStatus.PENDING}
        apply_webhook_event(
            state,
            {
                "status": VerificationStatus.FAILED,
                "rejection_reasons": ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS", "NONE"],
            },
        )
        self.assertEqual(state["status"], VerificationStatus.FAILED)
        self.assertEqual(
            state["rejection_reasons"], ["LEGAL_NAME_NOT_FOUND_IN_DOCUMENTS"]
        )
        self.assertIsNotNone(state["updated_at_meta"])
