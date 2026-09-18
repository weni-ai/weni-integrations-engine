"""Project authentication built on top of weni-commons.

``WeniAuthentication`` returns a lightweight ``WeniAuthUser`` for JWT callers,
since a Weni JWT carries only an email, not a Django identity. This project,
however, relies on a real Django user downstream: audit fields such as
``App.created_by`` are foreign keys to ``accounts.User`` and the existing
project-authorization permissions read ``request.user.authorizations``.

``WeniModuleAuthentication`` bridges that gap by resolving (and provisioning,
when absent) the Django user that matches the token email — mirroring what the
OIDC backend already does on first login — so both auth flows expose the same
``request.user`` contract while tenant scope keeps being read exclusively from
``request.auth`` (the immutable token claims).
"""

import logging
from typing import Any, Optional, Tuple

from django.contrib.auth import get_user_model

from weni_commons.auth import WeniAuthContext, WeniAuthentication

logger = logging.getLogger(__name__)

User = get_user_model()


class WeniModuleAuthentication(WeniAuthentication):
    """``WeniAuthentication`` that binds a real Django user for JWT callers."""

    def authenticate(self, request) -> Optional[Tuple[Any, WeniAuthContext]]:
        result = super().authenticate(request)
        if result is None:
            return None

        user, auth_context = result
        if auth_context.is_jwt and auth_context.user_email:
            user = self._resolve_django_user(auth_context.user_email)

        return user, auth_context

    def _resolve_django_user(self, email: str) -> Any:
        """Return the Django user for ``email``, creating it when missing."""
        user, created = User.objects.get_or_create(email=email)
        if created:
            logger.info(f"Provisioned Django user from JWT identity: {email}")
        return user
