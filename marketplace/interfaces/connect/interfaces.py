"""Interfaces for the Connect (weni-engine) HTTP client."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional


class ConnectClientInterface(ABC):
    """Contract for interacting with the Connect internal REST API."""

    @abstractmethod
    def notify_business_verification(
        self,
        user_email: str,
        status: str,
        rejection_reasons: Optional[Iterable[str]] = None,
        verification_attempts: int = 0,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger the business verification result email for the given user."""
        pass
