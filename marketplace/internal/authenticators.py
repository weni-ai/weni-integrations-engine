from mozilla_django_oidc.contrib.drf import OIDCAuthentication

from marketplace.internal.backends import InternalOIDCAuthenticationBackend


class InternalOIDCAuthentication(OIDCAuthentication):
    def __init__(self, backend=None):
        super().__init__(backend or InternalOIDCAuthenticationBackend())
