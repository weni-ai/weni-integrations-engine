from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from marketplace.connect.client import ConnectProjectClient


class FlowsOIDCAuthentication(OIDCAuthentication):  # pragma: no cover
    def is_flows_token(self, token):
        """
        Check if the token is likely a Flows token based on its length.
        """
        return len(token) == 40

    def authenticate(self, request):
        access_token = self.get_access_token(request)
        if not access_token:
            return None

        if self.is_flows_token(access_token):
            client = ConnectProjectClient()
            response = client.get_user_api_token(
                request.data["user_email"], access_token
            )

            if response:
                return (request.user, access_token)

        return super().authenticate(request)
