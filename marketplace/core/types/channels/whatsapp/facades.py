from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from requests.models import Response
from rest_framework.exceptions import ValidationError

from .queue import QueueItem, QueueItemManager
from .apis import InfrastructureDeployAPI, InfrastructureRemoveAPI
from .exceptions import ItemAlreadyInQueue

if TYPE_CHECKING:
    from .type import WhatsAppType


def request(url: str, method: str = "get", headers: dict = {}, params: dict = {}) -> Response:
    return getattr(requests, method)(url, headers=headers, params=params)


class BaseWhatsAppAPI(ABC):
    def __init__(self, app_type: "WhatsAppType"):
        self._app_type = app_type
        self._headers = {"Authorization": f"Bearer {app_type.SYSTEM_USER_ACCESS_TOKEN}"}

    @abstractmethod
    def _get_url(self):
        pass

    def _validate_response(self, response: Response):
        error = response.json().get("error")
        if error is not None:
            raise ValidationError(error.get("message"))

    def _request(self, url: str, method: str = "get", params: dict = {}) -> Response:
        response = request(url, method, self._headers, params)
        self._validate_response(response)

        return response


class AssignedUsersAPI(BaseWhatsAppAPI):
    def _get_url(self, target_id: str) -> str:
        return f"{self._app_type.API_URL}/{target_id}/assigned_users"

    def _request(self, target_id: str, method: str = "get", params: dict = {}) -> Response:
        url = self._get_url(target_id)
        return super()._request(url, method, params)

    def add_system_user_waba(self, target_id):
        params = dict(
            user=self._app_type.SYSTEM_USER_ID,
            tasks="['MANAGE','MANAGE_TEMPLATES','MANAGE_PHONE','VIEW_COST']",
            access_token=self._app_type.SYSTEM_USER_ACCESS_TOKEN,
            role="FINANCE_EDITOR",
        )
        self._request(target_id, "post", params)

    def validate_system_user_waba(self, target_id):
        params = dict(business=self._app_type.BUSINESS_ID)
        response = self._request(target_id, params=params)
        data = response.json().get("data")

        def validate_user_tasks_and_id(user: dict) -> bool:
            return "MANAGE" in user.get("tasks") and user.get("id") == self._app_type.SYSTEM_USER_ID

        users = list(filter(validate_user_tasks_and_id, data))

        if not users:
            raise ValidationError("User not found")  # TODO: Change to real error


class CreditLineAttachAPI(BaseWhatsAppAPI):
    def _get_url(self) -> str:
        return "{}/{}/whatsapp_credit_sharing_and_attach".format(
            self._app_type.API_URL, self._app_type.BUSINESS_CREDIT_LINE_ID
        )

    def _request(self, params: dict = {}) -> Response:
        url = self._get_url()
        return super()._request(url, "post", params)

    def attach(self, target_id: str):  # TODO: Post return type
        params = dict(waba_id=target_id, waba_currency="USD")
        response = self._request(params=params)
        return response.json().get("allocation_config_id")


class CreditLineAllocationConfigAPI(BaseWhatsAppAPI):
    def _get_url(self, allocation_config_id: str) -> str:
        return f"{self._app_type.API_URL}/{allocation_config_id}"

    def get_allocation_config_credential_id(self, allocation_config_id: str) -> str:
        params = dict(fields="receiving_credential{id}")
        response = self._request(self._get_url(allocation_config_id), params=params)
        receiving_credential = response.json().get("receiving_credential")
        return receiving_credential.get("id")


class CreditLineValidatorAPI(BaseWhatsAppAPI):
    def _get_url(self, target_id: str) -> str:
        return f"{self._app_type.API_URL}/{target_id}"

    def validate_config_credential_id(self, config_credential_id: str, target_id: str):
        params = dict(fields="primary_funding_id")
        response = self._request(self._get_url(target_id), params=params)
        if response.json().get("primary_funding_id") != config_credential_id:
            raise ValidationError("User not found")  # TODO: Change to real error


class CreditLineFacade(object):

    allocation_config_id: str = None

    def __init__(
        self,
        attach_api: CreditLineAttachAPI,
        allocation_config_api: CreditLineAllocationConfigAPI,
        validator_api: CreditLineValidatorAPI,
    ):
        self._attach_api = attach_api
        self._allocation_config_api = allocation_config_api
        self._validator_api = validator_api

    def attach(self, target_id: str):
        self.allocation_config_id = self._attach_api.attach(target_id)  # TODO: Ver o que fazer com essa variável
        config_credential_id = self._allocation_config_api.get_allocation_config_credential_id(
            self.allocation_config_id
        )
        self._validator_api.validate_config_credential_id(config_credential_id, target_id)


class WhatsAppAPIFacade(object):
    def __init__(
        self,
        assigned_users_api: BaseWhatsAppAPI,
        credit_line_facade: BaseWhatsAppAPI,
    ):
        self._assigned_users_api = assigned_users_api
        self._credit_line_facade = credit_line_facade

    def create(self, target_id):
        self._assigned_users_api.add_system_user_waba(target_id)
        self._assigned_users_api.validate_system_user_waba(target_id)
        self._credit_line_facade.attach(target_id)


class InfrastructureQueueFacade(object):
    def __init__(self):
        self.items = QueueItemManager()
        self._deploy_api = InfrastructureDeployAPI()
        self._remove_api = InfrastructureRemoveAPI()

    def deploy_whatsapp(self, item: QueueItem):
        self.items.add(item)
        self._deploy_api.deploy(item)

    def remove_whatsapp(self, item: QueueItem):
        self._remove_api.remove(item)
        self.items.remove(item)  # TODO: Remove only after confirmation

    def book_whatsapp(self) -> str:
        item = self.items.done_items()[-1]
        self.items.remove(item)
        return item.url


class WhatsAppFacade(object):
    def __init__(self, waba_id: str, app_type: "WhatsAppType"):
        self._waba_id = waba_id
        self._app_type = app_type

    def _get_assigned_users_api(self) -> AssignedUsersAPI:
        return AssignedUsersAPI(self._app_type)

    def _get_credit_line_facade(self) -> CreditLineFacade:
        attach_api = CreditLineAttachAPI(self._app_type)
        allocation_config_api = CreditLineAllocationConfigAPI(self._app_type)
        validator_api = CreditLineValidatorAPI(self._app_type)

        return CreditLineFacade(attach_api, allocation_config_api, validator_api)

    def create(self):
        assigned_users_api = self._get_assigned_users_api()
        credit_line_facade = self._get_credit_line_facade()
        whatsapp = WhatsAppAPIFacade(assigned_users_api, credit_line_facade)
        whatsapp.create(self._waba_id)
        return InfrastructureQueueFacade().get_whatsapp_url()
