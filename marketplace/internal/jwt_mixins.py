"""
Mixin to provide easy access to JWT project_uuid and payload for inter-module communication.
"""

from marketplace.internal.jwt_authenticators import JWTModuleAuthentication


class JWTModuleAuthMixin:
    """
    Mixin to provide easy access to JWT project_uuid and payload for inter-module communication.

    This mixin is designed for secure communication between modules where:
    - An intelligent agent needs information from this marketplace module
    - An intermediate module captures information and validates it
    - Generates a JWT token with project_uuid and other data
    - This module receives and validates the token using the public key

    Usage: Inherit this in your APIView for inter-module communication.
    """

    authentication_classes = [JWTModuleAuthentication]
    permission_classes = (
        []
    )  # No permission classes needed since we're just validating JWT

    @property
    def project_uuid(self):
        """Get the project_uuid from the validated JWT token."""
        return getattr(self.request, "project_uuid", None)

    @property
    def jwt_payload(self):
        """Get the full JWT payload from the validated token."""
        return getattr(self.request, "jwt_payload", None)
