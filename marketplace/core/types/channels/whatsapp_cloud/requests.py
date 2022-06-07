import json

import requests

from django.conf import settings
from ..whatsapp_base.interfaces import ProfileHandlerInterface


class CloudProfileRequest(ProfileHandlerInterface):

    _endpoint = "/whatsapp_business_profile"
    _fields = dict(fields="about,address,description,email,profile_picture_url,websites,vertical")

    def __init__(self, phone_number_id: "str") -> None:  # TODO: VAlidate if phone_number_id is str
        self._phone_number_id = phone_number_id

    @property
    def _url(self) -> str:
        return settings.WHATSAPP_API_URL + f"/{self._phone_number_id}" + self._endpoint

    @property
    def _headers(self) -> dict:
        access_token = settings.WHATSAPP_CLOUD_ACCESS_TOKEN
        return {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}

    def get_profile(self):
        response = requests.get(self._url, params=self._fields, headers=self._headers)
        content = response.json().get("data", [])[0]

        return dict(
            status=content.get("about"),
            email=content.get("email"),
            websites=content.get("websites"),
            address=content.get("address"),
            business=dict(description=content.get("description"), vertical=content.get("vertical")),
        )

    def set_profile(self, **kwargs) -> None:
        # TODO: Validate photo change
        data = dict(messaging_product="whatsapp")
        data.update(kwargs)

        response = requests.post(self._url, headers=self._headers, data=json.dumps(data))

    def delete_profile_photo(self):
        ...
