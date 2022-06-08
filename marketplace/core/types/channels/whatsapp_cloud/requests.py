import json

import requests
from rest_framework import status

from django.conf import settings
from ..whatsapp_base.interfaces import ProfileHandlerInterface
from ..whatsapp_base.exceptions import FacebookApiException


class CloudProfileRequest(ProfileHandlerInterface):
    # TODO: Validate response status
    _endpoint = "/whatsapp_business_profile"
    _fields = dict(fields="about,address,description,email,profile_picture_url,websites,vertical")

    def __init__(self, phone_number_id: "str") -> None:
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

        requests.post(self._url, headers=self._headers, data=json.dumps(data))

    def delete_profile_photo(self):
        ...


class PhoneNumbersRequest(object):
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get_url(self, endpoint: str) -> str:
        return f"{settings.WHATSAPP_API_URL}/{endpoint}"

    def get_phone_numbers(self, waba_id: str) -> list:
        url = self._get_url(f"{waba_id}/phone_numbers")
        response = requests.get(url, headers=self._headers)

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

        return response.json().get("data", [])
