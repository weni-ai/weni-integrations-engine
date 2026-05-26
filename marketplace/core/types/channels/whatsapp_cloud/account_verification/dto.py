"""DTOs for the Account Verification flow."""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(frozen=True)
class SubmitAccountVerificationDTO:
    """Input DTO carrying the validated payload to the submit use case."""

    app_uuid: str
    documents: List[Any]


@dataclass(frozen=True)
class AccountVerificationStateDTO:
    """Output DTO representing the persisted state for the frontend."""

    ui_state: str
    status: Optional[str] = None
    submission_id: Optional[str] = None
    verification_attempts: int = 0
    rejection_reasons: List[str] = field(default_factory=list)
    submitted_at: Optional[str] = None
    updated_at_meta: Optional[str] = None
    last_synced_at: Optional[str] = None
    can_submit: bool = True

    def to_dict(self) -> dict:
        return {
            "ui_state": self.ui_state,
            "status": self.status,
            "submission_id": self.submission_id,
            "verification_attempts": self.verification_attempts,
            "rejection_reasons": list(self.rejection_reasons),
            "submitted_at": self.submitted_at,
            "updated_at_meta": self.updated_at_meta,
            "last_synced_at": self.last_synced_at,
            "can_submit": self.can_submit,
        }
