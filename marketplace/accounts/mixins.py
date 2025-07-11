"""
Mixin to provide easy access to JWT project_uuid and payload for DRF views.
"""

from marketplace.accounts.permissions import JWTProjectPermission, NoAuthentication


class JWTProjectAuthMixin:
    """
    Mixin to provide easy access to JWT project_uuid and payload for DRF views.
    Usage: Inherit this in your APIView.
    """

    authentication_classes = [NoAuthentication]
    permission_classes = [JWTProjectPermission]

    @property
    def project_uuid(self):
        return getattr(self.request, "project_uuid", None)

    @property
    def jwt_payload(self):
        return getattr(self.request, "jwt_payload", None)
