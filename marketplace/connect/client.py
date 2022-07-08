import json
import requests

from django.conf import settings


class ConnectAuth:
    def get_auth_token(self) -> str:
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

    def auth_header(self, headers: dict = {}) -> dict:
        if "Authorization" not in headers:
            headers["Authorization"] = self.get_auth_token()
        return headers


class ConnectProjectClient(ConnectAuth):

    base_url = settings.CONNECT_ENGINE_BASE_URL

    def list_channels(self, channeltype_code: str):
        channels = []

        payload = {"channel_type": channeltype_code}
        request = requests.get(
            url=self.base_url + "/v1/organization/project/list_channel/", json=payload, headers=self.auth_header()
        )
        response = json.loads(request.text)

        while response.get("next") is not None and request.status_code == 200:
            for channel in response.get("results"):
                channels.append(channel)
            request = requests.get(url=response.get("next"), json=payload, headers=self.auth_header())
            response = json.loads(request.text)

        return channels

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> dict:
        payload = {"user": user, "project_uuid": str(project_uuid), "data": data, "channeltype_code": channeltype_code}
        request = requests.post(
            url=self.base_url + "/v1/organization/project/create_channel/", json=payload, headers=self.auth_header()
        )
        return json.loads(request.text)

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        payload = {"channel_uuid": channel_uuid, "user": user_email}
        requests.get(
            url=self.base_url + "/v1/organization/project/release_channel/", json=payload, headers=self.auth_header()
        )
        return None


class WPPRouterChannelClient(ConnectAuth):
    base_url = settings.ROUTER_BASE_URL

    def get_channel_token(self, uuid: str, name: str) -> str:
        payload = {"uuid": uuid, "name": name}

        response = requests.post(url=self.base_url + "/integrations/channel", json=payload, headers=self.auth_header())

        return response.json().get("token", "")
