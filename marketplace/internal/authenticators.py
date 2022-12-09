import requests

from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from django.conf import settings

from marketplace.internal.backends import InternalOIDCAuthenticationBackend


class InternalOIDCAuthentication(OIDCAuthentication):
    def __init__(self, backend=None):
        super().__init__(backend or InternalOIDCAuthenticationBackend())


class InternalAuthentication:

    def __get_module_token(self):
        request = requests.post(
            url=settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                "client_id": settings.OIDC_RP_CLIENT_ID,
                "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )

        token = request.json().get("access_token")
        return f"Bearer {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }
