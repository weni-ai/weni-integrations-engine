"""Constants for the Partner-led WhatsApp Business Account Verification flow."""


CONFIG_KEY = "account_verification"

MAX_DOCUMENTS = 3
MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_DOCUMENT_CONTENT_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
)

CERTIFICATION_EVENT = "PARTNER_CLIENT_CERTIFICATION_STATUS_UPDATE"

NONE_REJECTION_REASON = "NONE"


class VerificationStatus:
    """Meta's verification status values plus our local PENDING marker."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FAILED = "FAILED"

    CHOICES = (PENDING, APPROVED, FAILED)


class UIState:
    """States the frontend renders for the Account verification tab."""

    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    FAILED = "failed"
    BLOCKED = "blocked"


CACHE_KEY_TEMPLATE = "account-verification:meta:{end_business_id}"


def build_cache_key(end_business_id: str) -> str:
    return CACHE_KEY_TEMPLATE.format(end_business_id=end_business_id)
