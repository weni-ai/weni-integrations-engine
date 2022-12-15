import json
import requests

from django.conf import settings

from marketplace.applications.models import AppTypeAsset


class ConnectAuth:
    def __get_auth_token(self) -> str:
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

    def auth_header(self) -> dict:
        return {"Authorization": self.__get_auth_token()}


class ConnectProjectClient(ConnectAuth):

    base_url = settings.CONNECT_ENGINE_BASE_URL

    def list_channels(self, channeltype_code: str) -> list:

        params = {"channel_type": channeltype_code}
        response = requests.get(
            url=self.base_url + "/v1/organization/project/list_channels/", params=params, headers=self.auth_header()
        )
        return response.json().get("channels", None)

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> dict:
        payload = {"user": user, "project_uuid": str(project_uuid), "data": data, "channeltype_code": channeltype_code}
        response = requests.post(
            url=self.base_url + "/v1/organization/project/create_channel/", json=payload, headers=self.auth_header()
        )
        return response.json()

    def create_wac_channel(self, user: str, project_uuid: str, phone_number_id: str, config: dict) -> dict:
        payload = {
            "user": user,
            "project_uuid": str(project_uuid),
            "config": json.dumps(config),
            "phone_number_id": phone_number_id,
        }
        response = requests.post(
            url=self.base_url + "/v1/organization/project/create_wac_channel/",
            json=payload,
            headers=self.auth_header(),
        )
        return response.json()

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        payload = {"channel_uuid": channel_uuid, "user": user_email}
        requests.get(
            url=self.base_url + "/v1/organization/project/release_channel/", json=payload, headers=self.auth_header()
        )
        return None

    def get_user_api_token(self, user: str, project_uuid: str):
        params = dict(user=user, project_uuid=str(project_uuid))
        response = requests.get(
            self.base_url + "/v1/organization/project/user_api_token/", params=params, headers=self.auth_header()
        )
        return response

    def list_availables_channels(self):
        response = requests.get(
            url=self.base_url + "/v1/channel-types",
            headers=self.auth_header(),
            timeout=60
        )
        return response

    def detail_channel_type(self, channel_code: str):
        params = {"channel_type_code": channel_code}
        response = requests.get(
            url=self.base_url + "/v1/channel-types",
            params=params, headers=self.auth_header(),
            timeout=60
        )
        return response


class WPPRouterChannelClient(ConnectAuth):
    base_url = settings.ROUTER_BASE_URL

    def get_channel_token(self, uuid: str, name: str) -> str:
        payload = {"uuid": uuid, "name": name}
        
        response = requests.post(url=self.base_url + "/integrations/channel", json=payload, headers=self.auth_header())
        
        return response.json().get("token", "")
