import jwt

from typing import Optional, Tuple, Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request
from django.conf import settings


class JWTModuleAuthentication(BaseAuthentication):
    """
    DRF authentication class for inter-module communication using JWT tokens.

    This class handles JWT authentication for secure communication between modules:
    - Validates the JWT signature using the public key from settings
    - Extracts 'project_uuid' from the payload and attaches it to the request object
    - Raises AuthenticationFailed for any missing/invalid cases

    Usage:
        authentication_classes = [JWTModuleAuthentication]
    """

    def authenticate(self, request: Request) -> Optional[Tuple[Any, None]]:
        """
        Authenticate the request using JWT token for inter-module communication.

        Returns:
            Tuple of (user, auth) where user is None (no user model needed)
            and auth is None (no auth object needed)
        """
        public_key: Optional[bytes] = getattr(settings, "JWT_PUBLIC_KEY", None)
        if not public_key:
            raise AuthenticationFailed(
                "JWT_PUBLIC_KEY not configured in Django settings. "
                "Please add the public key for JWT validation."
            )

        auth_header: str = request.headers.get("Authorization", "")
        if not isinstance(auth_header, str) or not auth_header.startswith("Bearer "):
            raise AuthenticationFailed("Missing or invalid Authorization header.")

        token: str = auth_header.split(" ", 1)[1]
        try:
            payload: dict = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token.")

        project_uuid: Optional[str] = payload.get("project_uuid")
        if not project_uuid:
            raise AuthenticationFailed("project_uuid not found in token payload.")

        # Inject project_uuid and payload for use in the view/mixin
        request.project_uuid = project_uuid
        request.jwt_payload = payload

        # Return None for user since we don't need a user model for JWT auth
        return (None, None)
