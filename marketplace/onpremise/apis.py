from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from django.conf import settings
from django.urls import reverse

if TYPE_CHECKING:
    from .queue import QueueItem


class BaseOnPremiseAPI(ABC):
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


class OnPremiseDeployAPI(BaseOnPremiseAPI):
    def _get_event_type(self) -> str:
        return "deploy-whatsapp"

    def deploy(self, item: "QueueItem") -> None:
        # TODO: Validate status
        requests.post(self._url, json=self._get_payload(item), headers=self._headers)


class OnPremiseRemoveAPI(BaseOnPremiseAPI):
    def _get_event_type(self) -> str:
        return "remove-whatsapp"

    def remove(self, item: "QueueItem") -> None:
        # TODO: Validate status
        requests.post(self._url, json=self._get_payload(item), headers=self._headers)
