"""Client for connection with flows"""
import requests
import json

from django.conf import settings


class FlowsClient:
    def __init__(self):
        self.base_url = settings.FLOWS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def list_channel_types(self, channel_code):
        if channel_code:
            request_url = (
                f"{self.base_url}/api/v2/internals/channels/{str(channel_code)}"
            )
        else:
            request_url = f"{self.base_url}/api/v2/internals/channels"

        response = requests.get(
            url=request_url, headers=self.authentication_instance.headers, timeout=60
        )
        return response

    def partial_config_update(self, key, data, flow_object_uuid):
        payload = {"config": {key: data}}

        if data:
            request_url = (
                f"{self.base_url}/api/v2/internals/channel/{flow_object_uuid}/"
            )

        headers = self.authentication_instance.headers_patch_json

        response = requests.patch(
            url=request_url, headers=headers, data=json.dumps(payload), timeout=60
        )
        return response


class InternalAuthentication:
    def __get_module_token(self):
        request = requests.post(
            url=settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                "client_id": settings.OIDC_RP_CLIENT_ID,
                "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            timeout=60,
        )
        token = request.json().get("access_token")
        if token is None:
            return ("Access token is missing in the request", 401)

        return f"Bearer {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }

    @property
    def headers_patch_json(self):
        return {
            "Content-Type": "application/json-patch+json",
            "Authorization": self.__get_module_token(),
        }
