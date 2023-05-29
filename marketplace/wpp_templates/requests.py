import requests

from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)

from django.conf import settings

WHATSAPP_VERSION = settings.WHATSAPP_VERSION

from django.conf import settings

WHATSAPP_VERSION = settings.WHATSAPP_VERSION


class TemplateMessageRequest(object):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def list_template_messages(self, waba_id: str) -> dict:
        params = dict(
            limit=999,
            access_token=self._access_token,
        )
        response = requests.get(
            url=f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates",
            params=params,
        )
        return response.json()

    def get_template_namespace(self, waba_id: str) -> dict:
        params = dict(
            fields="message_template_namespace",
            access_token=self._access_token,
        )
        response = requests.get(
            url=f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}",
            params=params,
        )
        return response.json().get("message_template_namespace")

    def create_template_message(
        self, waba_id: str, name: str, category: str, components: list, language: str
    ) -> dict:
        params = dict(
            name=name,
            category=category,
            components=str(components),
            language=language,
            access_token=self._access_token,
        )
        response = requests.post(
            url=f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates",
            params=params,
        )
        if response.status_code != 200:
            raise FacebookApiException(response.json())

        return response.json()
    
    def update_template_message(self, message_template_id: str, name: str, components: str) -> dict:
        params = dict(
            name=name,
            components=str(components),
            access_token=self._access_token
        )
        response = requests.post(url=f"https://graph.facebook.com/{WHATSAPP_VERSION}/{message_template_id}", params=params)
        if response.status_code != 200:
            raise FacebookApiException(response.json())

        return response.json()

    def delete_template_message(self, waba_id: str, name: str) -> bool:
        params = dict(name=name, access_token=self._access_token)
        return requests.delete(
            url=f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}/message_templates",
            params=params,
        )
