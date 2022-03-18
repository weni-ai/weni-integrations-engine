from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from requests.models import Response
from rest_framework.exceptions import ValidationError

from marketplace.onpremise.apis import PhoneNumber

if TYPE_CHECKING:
    from .type import WhatsAppType


def request(url: str, method: str = "get", headers: dict = {}, params: dict = {}) -> Response:
    return getattr(requests, method)(url, headers=headers, params=params)


class BaseFacebookAPI(ABC):
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


class AssignedUsersAPI(BaseFacebookAPI):
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


class CreditLineAttachAPI(BaseFacebookAPI):
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


class CreditLineAllocationConfigAPI(BaseFacebookAPI):
    def _get_url(self, allocation_config_id: str) -> str:
        return f"{self._app_type.API_URL}/{allocation_config_id}"

    def get_allocation_config_credential_id(self, allocation_config_id: str) -> str:
        params = dict(fields="receiving_credential{id}")
        response = self._request(self._get_url(allocation_config_id), params=params)
        receiving_credential = response.json().get("receiving_credential")
        return receiving_credential.get("id")


class CreditLineValidatorAPI(BaseFacebookAPI):
    def _get_url(self, target_id: str) -> str:
        return f"{self._app_type.API_URL}/{target_id}"

    def validate_config_credential_id(self, config_credential_id: str, target_id: str):
        params = dict(fields="primary_funding_id")
        response = self._request(self._get_url(target_id), params=params)
        if response.json().get("primary_funding_id") != config_credential_id:
            raise ValidationError("User not found")  # TODO: Change to real error


class PhoneNumbersAPI(BaseFacebookAPI):
    def _get_url(self, waba_id: str) -> str:
        return f"{self._app_type.API_URL}/{waba_id}/phone_numbers"

    def _get_params(self) -> dict:
        return {
            "fields": "display_phone_number,certificate,name_status,new_name_status,new_certificate",
            "access_token": self._app_type.SYSTEM_USER_ACCESS_TOKEN,
        }

    def get_phone_number(self, waba_id: str) -> PhoneNumber:
        response = self._request(self._get_url(waba_id), params=self._get_params())
        data = response.json().get("data")[0]

        return PhoneNumber(data)
