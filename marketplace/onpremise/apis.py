from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from requests.auth import HTTPBasicAuth
from requests.models import Response
from django.conf import settings
from django.urls import reverse
from rest_framework import status

if TYPE_CHECKING:
    from .queue import QueueItem


class PhoneNumber(object):
    def __init__(self, number_data: dict):
        self._number_data = number_data

        self.display_number = self._get_display_number()

        self.id = self._get_certificate()
        self.certificate = self._get_certificate()
        self.country_code, self.ddd, self.number = self.display_number
        self.complete_number = self.ddd + self.number

    def _get_display_number(self) -> list:
        display_phone_number = self._number_data.get("display_phone_number")
        return display_phone_number.replace("-", "").replace("+", "").split()

    def _get_certificate(self):
        return self._number_data.get("certificate")

    def _get_id(self):
        return self._number_data.get("id")

    def __str__(self) -> str:
        return self.complete_number


class BaseOnPremiseManifestAPI(ABC):
    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"token {settings.WHATSAPP_GITHUB_ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    @property
    def _url(self) -> str:
        return settings.WHATSAPP_DISPATCHES_URL

    def _get_payload(self, item: "QueueItem") -> dict:
        return {
            "event_type": self._get_event_type(),
            "client_payload": {
                "uid": item.uid,
                "webhook_url": settings.EXTERNAL_URL + reverse("wpp-app-webhook"),
                "webhook_id": item.uid,
                "dry_run": "enable",
            },
        }

    @abstractmethod
    def _get_event_type(self) -> str:
        pass


class BaseOnPremiseUserAPI(ABC):
    @property
    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _request(self, onpremise_url: str, password: str, json: dict = None) -> Response:
        response = requests.post(
            f"{onpremise_url}/v1/users/login", json=json, headers=self._headers, auth=HTTPBasicAuth("admin", password)
        )

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise Exception("the password of this on premise has already been changed!")

        return response


class OnPremiseDeployManifestAPI(BaseOnPremiseManifestAPI):
    def _get_event_type(self) -> str:
        return "deploy-whatsapp"

    def deploy(self, item: "QueueItem") -> None:
        # TODO: Validate status
        requests.post(self._url, json=self._get_payload(item), headers=self._headers)


class OnPremiseRemoveManifestAPI(BaseOnPremiseManifestAPI):
    def _get_event_type(self) -> str:
        return "remove-whatsapp"

    def remove(self, item: "QueueItem") -> None:
        # TODO: Validate status
        requests.post(self._url, json=self._get_payload(item), headers=self._headers)


class OnPremisePasswordAPI(BaseOnPremiseUserAPI):
    def change(self, onpremise_url: str, new_password: str) -> None:
        data = {"new_password": new_password}
        self._request(onpremise_url, new_password, data)


class OnPremiseLoginAPI(BaseOnPremiseUserAPI):
    def get_access_token(self, onpremise_url: str, password: str) -> str:
        response = self._request(onpremise_url, password)
        users = response.json().get("users", None)

        if users is not None:
            return users[0].get("token")


class OnPremiseRegistrationAPI(object):
    def _get_url(self, onpremise_url):
        return onpremise_url + "/v1/account"

    def _get_headers(self, token: str):
        return {"Content-Type": "application/json", "Authorization": "Bearer " + token}

    def register_account(self, onpremise_url: str, token: str, phone_number: PhoneNumber) -> None:
        data = dict(
            cc=phone_number.country_code,
            phone_number=str(phone_number),
            cert=phone_number.certificate,
            method="sms",
        )
        requests.post(self._get_url(onpremise_url), json=data, headers=self._get_headers(token))
