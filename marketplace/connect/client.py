import json
import requests

from django.conf import settings
from rest_framework import serializers
from collections import namedtuple

from marketplace.celery import app as celery_app

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
        if 'Authorization' not in headers:
            headers['Authorization'] = self.get_auth_token()
        return headers

class ConnectProjectClient(ConnectAuth):

    base_url = settings.CONNECT_ENGINE_BASE_URL

    def list_channels(self, channeltype_code: str):
        channels = []

        payload = {
            "channel_type": channeltype_code
        }
        request = requests.get(url=self.base_url + '/organization/project/list_channel/', json=payload, headers=self.auth_header())
        response = json.loads(request.text)

        """
        limit = 20
        offset = 20
        pages = round(response.get("count")/limit)+1

        for i in range(1, pages):
            if not response.get("results"):
                continue

            for channel in response.get("results"):
                channels.append(channel)

            request = requests.get(url=self.base_url + f'/organization/project/list_channel/?limit={limit}&offset={offset*i}', json=payload, headers=self.auth_header())
            response = json.loads(request.text)

        return channels
        """

        while response.get("next") != None and request.status_code == 200:
            for channel in response.get("results"):
                channels.append(channel)
            request = requests.get(url=response.get("next"), json=payload, headers=self.auth_header())
            response = json.loads(request.text)

        return channels
        

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> dict:
        payload = {
            "user": user,
            "project_uuid": project_uuid,
            "data": data,
            "channeltype_code": channeltype_code
        }
        request = requests.post(url=self.base_url + '/organization/project/create_channel/', json=payload, headers=self.auth_header())
        return json.loads(request.text)

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        payload = {
            "channel_uuid": channel_uuid,
            "user": user_email
        }
        request = requests.get(url=self.base_url + '/organization/project/release_channel/', json=payload, headers=self.auth_header())
        return None


class WPPRouterChannelClient(ConnectAuth):
    base_url = settings.ROUTER_BASE_URL
    
    def get_channel_token(self, uuid: str, name: str) -> str:
        payload = {
            "channel_uuid": uuid,
            "user": name
        }

        request = requests.post(url=self.base_url + '/integrations/channel', json=payload, headers=self.auth_header())
        return json.loads(request.text)['token']