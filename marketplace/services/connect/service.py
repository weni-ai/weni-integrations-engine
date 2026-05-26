"""Service layer for Connect interactions."""

from typing import Any, Dict, Iterable, Optional

from marketplace.interfaces.connect.interfaces import ConnectClientInterface


class ConnectService:
    """Thin wrapper around `ConnectClientInterface`."""

    def __init__(self, client: ConnectClientInterface):
        self.client = client

    def notify_business_verification(
        self,
        user_email: str,
        status: str,
        rejection_reasons: Optional[Iterable[str]] = None,
        verification_attempts: int = 0,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.client.notify_business_verification(
            user_email=user_email,
            status=status,
            rejection_reasons=rejection_reasons,
            verification_attempts=verification_attempts,
            language=language,
        )
