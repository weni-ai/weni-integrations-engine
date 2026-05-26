"""Helpers to derive AccountVerificationStateDTO from app.config and to mutate it."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    CONFIG_KEY,
    MAX_DOCUMENTS,
    NONE_REJECTION_REASON,
    UIState,
    VerificationStatus,
)
from .dto import AccountVerificationStateDTO


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_state(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the persisted dict (or an empty dict if missing)."""
    return dict(config.get(CONFIG_KEY) or {})


def _filter_reasons(reasons: Optional[List[str]]) -> List[str]:
    """Drop Meta's NONE sentinel and ignore non-string entries."""
    if not reasons:
        return []
    return [
        reason
        for reason in reasons
        if isinstance(reason, str) and reason != NONE_REJECTION_REASON
    ]


def _derive_ui_state(state: Dict[str, Any]) -> str:
    if not state.get("submission_id") and not state.get("status"):
        return UIState.NOT_STARTED

    attempts = int(state.get("verification_attempts") or 0)
    status = state.get("status")

    if attempts >= MAX_DOCUMENTS and status != VerificationStatus.APPROVED:
        return UIState.BLOCKED
    if status == VerificationStatus.APPROVED:
        return UIState.APPROVED
    if status == VerificationStatus.FAILED:
        return UIState.FAILED
    if status == VerificationStatus.PENDING:
        return UIState.PENDING
    return UIState.NOT_STARTED


def _derive_can_submit(state: Dict[str, Any]) -> bool:
    attempts = int(state.get("verification_attempts") or 0)
    status = state.get("status")
    if status == VerificationStatus.APPROVED:
        return False
    if status == VerificationStatus.PENDING:
        return False
    return attempts < MAX_DOCUMENTS


def to_dto(state: Dict[str, Any]) -> AccountVerificationStateDTO:
    return AccountVerificationStateDTO(
        ui_state=_derive_ui_state(state),
        status=state.get("status"),
        submission_id=state.get("submission_id"),
        verification_attempts=int(state.get("verification_attempts") or 0),
        rejection_reasons=_filter_reasons(state.get("rejection_reasons")),
        submitted_at=state.get("submitted_at"),
        updated_at_meta=state.get("updated_at_meta"),
        last_synced_at=state.get("last_synced_at"),
        can_submit=_derive_can_submit(state),
    )


def merge_from_meta_submissions(
    state: Dict[str, Any], submissions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Update local state with the freshest submission returned by Meta.

    Meta returns the list of submissions for the client; the most recent one
    drives the UI state. ``verification_attempts`` is kept as the maximum
    between any value Meta reports and the length of the list, protecting
    against drift if a submission was created before the local config existed.
    """
    if not submissions:
        return state

    sorted_submissions = sorted(
        submissions,
        key=lambda submission: submission.get("update_time")
        or submission.get("submitted_time")
        or "",
        reverse=True,
    )
    latest = sorted_submissions[0]

    state["submission_id"] = latest.get("id") or state.get("submission_id")
    state["status"] = latest.get("verification_status") or state.get("status")
    state["rejection_reasons"] = _filter_reasons(latest.get("rejection_reasons"))
    state["updated_at_meta"] = (
        latest.get("update_time")
        or latest.get("submitted_time")
        or state.get("updated_at_meta")
    )
    state["submitted_at"] = state.get("submitted_at") or latest.get("submitted_time")
    state["verification_attempts"] = max(
        int(state.get("verification_attempts") or 0),
        len(submissions),
    )
    return state


def apply_submit_response(
    state: Dict[str, Any], response: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply Meta's response to a fresh self_certify_whatsapp_business POST."""
    state["status"] = VerificationStatus.PENDING
    state["verification_attempts"] = max(
        int(state.get("verification_attempts") or 0),
        int(response.get("verification_attempts") or 0),
    )
    state["rejection_reasons"] = []
    state["submitted_at"] = now_iso()
    state["updated_at_meta"] = None
    state["last_synced_at"] = None
    return state


def apply_webhook_event(
    state: Dict[str, Any], partner_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply a PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE webhook payload."""
    state["status"] = partner_info.get("status") or state.get("status")
    state["rejection_reasons"] = _filter_reasons(partner_info.get("rejection_reasons"))
    state["updated_at_meta"] = now_iso()
    return state
