from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.conf import settings
import requests

if TYPE_CHECKING:
    from .queue import InfrastructureQueueItem


class BaseInfrastructureAPI(ABC):

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"token {settings.WHATSAPP_GITHUB_ACCESS_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    @property
    def _url(self) -> str:
        return settings.WHATSAPP_DISPATCHES_URL

    def _get_payload(self, item: "InfrastructureQueueItem") -> dict:
        return {
            "event_type": self._get_event_type(),
            "client_payload": {
                "uid": item.get_uid(),
                "webhook_url": settings.WHATSAPP_DISPATCHES_WEBHOOK_URL,
                "webhook_id": item.get_uid(),
                "dry_run": "enable",
            }
        }

    @abstractmethod
    def _get_event_type(self) -> str:
        pass


class InfrastructureDeployAPI(BaseInfrastructureAPI):
    def _get_event_type(self) -> str:
        return "deploy-whatsapp"

    def deploy(self, item: "InfrastructureQueueItem"):
        # TODO: Validate status
        response = requests.post(self._url,  json=self._get_payload(item), headers=self._headers)


class InfrastructureRemoveAPI(BaseInfrastructureAPI):
    def _get_event_type(self) -> str:
        return "remove-whatsapp"

    def remove(self, item: "InfrastructureQueueItem"):
        # TODO: Validate status
        response = requests.post(self._url,  json=self._get_payload(item), headers=self._headers)
