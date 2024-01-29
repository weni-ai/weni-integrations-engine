import time

import requests
from rest_framework import status

from django.conf import settings

from ..whatsapp_base.interfaces import ProfileHandlerInterface
from ..whatsapp_base.exceptions import FacebookApiException


class CloudProfileRequest(ProfileHandlerInterface):
    # TODO: Validate response status
    _endpoint = "/whatsapp_business_profile"
    _fields = dict(
        fields="about,address,description,email,profile_picture_url,websites,vertical"
    )

    def __init__(self, access_token: str, phone_number_id: "str") -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id

    @property
    def _url(self) -> str:
        return settings.WHATSAPP_API_URL + f"/{self._phone_number_id}" + self._endpoint

    @property
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }

    def get_profile(self):
        response = requests.get(self._url, params=self._fields, headers=self._headers)
        content = response.json().get("data", [{}])[0]

        return dict(
            status=content.get("about"),
            email=content.get("email"),
            websites=content.get("websites"),
            address=content.get("address"),
            photo_url=content.get("profile_picture_url"),
            business=dict(
                description=content.get("description"), vertical=content.get("vertical")
            ),
        )

    def set_profile(self, **kwargs) -> None:
        # TODO: Validate photo change
        data = dict(messaging_product="whatsapp")
        data.update(kwargs)

        response = requests.post(self._url, headers=self._headers, json=data)
        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

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

        for i in range(2):
            if response.status_code != status.HTTP_200_OK:
                time.sleep(10)
                response = requests.get(url, headers=self._headers)

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

        return response.json().get("data", [])

    def get_phone_number(self, phone_number_id: str):
        url = self._get_url(phone_number_id)
        print('URL PHONE NUMBER', url, 'HEADER', self._headers)
        response = requests.get(url, headers=self._headers)

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

        return response.json()


class PhotoAPIRequest(object):
    def __init__(self, phone_number_id: str, access_token: str) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get_url(self, endpoint: str) -> str:
        return f"{settings.WHATSAPP_API_URL}/{endpoint}"

    def create_upload_session(
        self, access_token: str, file_length: int, file_type: str
    ) -> str:
        url = self._get_url(
            f"app/uploads?access_token={self._access_token}&file_length={file_length}&file_type={file_type}"
        )
        response = requests.post(url, headers=self._headers)

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

        return response.json().get("id", "")

    def upload_photo(
        self, upload_session_id: str, photo: str, is_uploading: bool = False
    ) -> str:
        url = self._get_url(upload_session_id)

        headers = {
            "Content-Type": photo.content_type,
            "Authorization": f"OAuth {self._access_token}",
        }

        if not is_uploading:
            headers["file_offset"] = "0"

        response = requests.post(url, headers=headers, data=photo.file.getvalue())

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())

        return response.json().get("h", "")

    def set_photo(self, photo):
        url = self._get_url(f"{self._phone_number_id}/whatsapp_business_profile")

        upload_session_id = self.create_upload_session(
            self._access_token, len(photo.file.getvalue()), file_type=photo.content_type
        )

        upload_handle = self.upload_photo(upload_session_id, photo)

        payload = {
            "messaging_product": "whatsapp",
            "profile_picture_handle": upload_handle,
        }

        response = requests.post(url, headers=self._headers, json=payload)

        if response.status_code != status.HTTP_200_OK:
            raise FacebookApiException(response.json())
