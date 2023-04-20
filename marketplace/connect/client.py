
import requests

from django.conf import settings

from rest_framework.exceptions import ValidationError


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
    use_connect_v2 = settings.USE_CONNECT_V2

    def _get_url(self, endpoint: str) -> str:
        # TODO: refactor all clients to use this method
        assert endpoint.startswith("/"), "the endpoint needs to start with: /"
        return self.base_url + endpoint

    def list_channels(self, channeltype_code: str) -> list:
        params = {
            "channel_type": channeltype_code
        }
        if self.use_connect_v2:
            url = self.base_url + "/v2/projects/channels"
        else:
            url = self.base_url + "/v1/organization/project/list_channels/"

        response = requests.get(
            url=url,
            params=params,
            headers=self.auth_header(),
            timeout=60
        )
        return response.json().get("channels", None)

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> dict:
        payload = {
            "user": user,
            "project_uuid": str(project_uuid),
            "data": data,
            "channeltype_code": channeltype_code
        }
        if self.use_connect_v2:
            del payload["project_uuid"]
            url = self.base_url + f"/v2/projects/{str(project_uuid)}/channel"
        else:
            url = self.base_url + "/v1/organization/project/create_channel/"

        response = requests.post(
            url=url,
            json=payload,
            headers=self.auth_header(),
            timeout=60
        )

        if response.status_code not in [200, 201]:
            raise ValidationError(f"{response.status_code}: {response.text}")

        return response.json()

    def create_wac_channel(self, user: str, project_uuid: str, phone_number_id: str, config: dict) -> dict:
        payload = {
            "user": user,
            "project_uuid": str(project_uuid),
            "config": config,
            "phone_number_id": phone_number_id,
        }
        if self.use_connect_v2:
            del payload["project_uuid"]
            url = self.base_url + f"/v2/projects/{project_uuid}/create-wac-channel"
        else:
            url = self.base_url + "/v1/organization/project/create_wac_channel/"

        response = requests.post(
            url=url,
            json=payload,
            headers=self.auth_header(),
            timeout=60
        )

        return response.json()

    def release_channel(self, channel_uuid: str, project_uuid: str, user_email: str) -> None:
        payload = {"channel_uuid": channel_uuid, "user": user_email}
        if self.use_connect_v2:
            requests.delete(
                url=self.base_url + f"/v2/projects/{str(project_uuid)}/channel",
                json=payload,
                headers=self.auth_header(),
                timeout=60
            )
        else:
            requests.get(
                url=self.base_url + "/v1/organization/project/release_channel/",
                json=payload,
                headers=self.auth_header(),
                timeout=60
            )
        return None

    def get_user_api_token(self, user: str, project_uuid: str):
        params = dict(user=user, project_uuid=str(project_uuid))
        if self.use_connect_v2:
            url = self.base_url + "/v2/project/user_api_token/"
        else:
            url = self.base_url + "/v1/organization/project/user_api_token/"

        response = requests.get(
            url=url,
            params=params,
            headers=self.auth_header(),
            timeout=60
        )
        return response

    def list_availables_channels(self):
        url = self.base_url + "/v1/channel-types"
        response = requests.get(
            url=url,
            headers=self.auth_header(),
            timeout=60
        )
        return response

    def detail_channel_type(self, channel_code: str):
        params = {"channel_type_code": channel_code}
        url = self.base_url + "/v1/channel-types"
        response = requests.get(
            url=url,
            params=params,
            headers=self.auth_header(),
            timeout=60
        )
        return response

    def create_external_service(self, user: str, project_uuid: str, type_fields: dict, type_code: str):
        payload = {"user": user, "project": str(project_uuid), "type_fields": type_fields, "type_code": type_code}
        response = requests.post(
            self._get_url("/v1/externals"), json=payload, headers=self.auth_header()
        )
        return response

    def release_external_service(self, uuid: str, user_email: str):
        url = self._get_url("/v1/externals")
        params = {
            "uuid": str(uuid),
            "user": user_email
        }

        response = requests.delete(
            url=url,
            params=params,
            headers=self.auth_header()
        )
        return response


class WPPRouterChannelClient(ConnectAuth):
    base_url = settings.ROUTER_BASE_URL

    def get_channel_token(self, uuid: str, name: str) -> str:
        payload = {"uuid": uuid, "name": name}
        response = requests.post(
            url=self.base_url + "/integrations/channel",
            json=payload,
            headers=self.auth_header(),
            timeout=60
        )
        return response.json().get("token", "")
