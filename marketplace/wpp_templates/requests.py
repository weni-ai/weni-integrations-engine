import requests
import urllib.parse
import json

from marketplace.core.types.channels.whatsapp_base.exceptions import FacebookApiException


class TemplateMessageRequest(object):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def create_template_message(self, waba_id: str, name: str, category: str, components: list, language: str) -> dict:
        params = dict(
            name=name, category=category, components=str(components), language=language, access_token=self._access_token
        )
        
        #print(urlencode(params))
        #print(f"https://graph.facebook.com/v14.0/{waba_id}/message_templates?components={str(components)}")

        #payload_str = urllib.parse.urlencode(params, safe=':+')

        response = requests.post(url=f"https://graph.facebook.com/v14.0/{waba_id}/message_templates", params=params)

        print("AAAAAAAAAA")
        #print(response.url)
        print("AAAAAAAAAA")

        if response.status_code != 200:
            raise FacebookApiException(response.json())

        return response.json()

    def delete_template_message(self, waba_id: str, name: str) -> bool:
        params = dict(name=name, access_token=self._access_token)
        response = requests.delete(url=f"https://graph.facebook.com/v14.0/{waba_id}/message_templates", params=params)

        
        if response.status_code != 200:
            raise FacebookApiException(response.json())

        return response.json().get("success", False)
