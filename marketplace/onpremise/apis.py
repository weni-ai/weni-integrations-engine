from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from django.urls import reverse
from rest_framework import status

if TYPE_CHECKING:
    from .queue import QueueItem


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


class OnPremisePasswordAPI(object):
    @property
    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def change(self, onpremise_url: str, new_password: str) -> None:
        data = {"new_password": new_password}

        response = requests.post(
            f"{onpremise_url}/v1/users/login", json=data, headers=self._headers, auth=HTTPBasicAuth("admin", "secret")
        )

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise Exception("the password of this on premise has already been changed!")
