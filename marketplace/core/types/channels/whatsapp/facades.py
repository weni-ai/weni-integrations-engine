from typing import TYPE_CHECKING

from marketplace.onpremise.facades import OnPremiseQueueFacade, OnPremiseFacade
from .apis import (
    CreditLineAttachAPI,
    CreditLineAllocationConfigAPI,
    CreditLineValidatorAPI,
    AssignedUsersAPI,
    PhoneNumbersAPI,
)
from marketplace.onpremise.apis import PhoneNumber

if TYPE_CHECKING:
    from .type import WhatsAppType


class WhatsApp(object):
    def __init__(self, url:str, password: str, token: str, phone_number: PhoneNumber) -> None:
        self.url = url
        self.password = password
        self.token = token
        self.phone_number = phone_number

    def __str__(self) -> str:
        return self.phone_number.complete_number


class CreditLineFacade(object):

    allocation_config_id: str = None

    def __init__(self, app_type: "WhatsAppType"):
        self._attach_api = CreditLineAttachAPI(app_type)
        self._allocation_config_api = CreditLineAllocationConfigAPI(app_type)
        self._validator_api = CreditLineValidatorAPI(app_type)

    def attach(self, target_id: str):
        self.allocation_config_id = self._attach_api.attach(target_id)  # TODO: Ver o que fazer com essa variável
        config_credential_id = self._allocation_config_api.get_allocation_config_credential_id(
            self.allocation_config_id
        )
        self._validator_api.validate_config_credential_id(config_credential_id, target_id)


class FacebookAPIFacade(object):
    def __init__(self, app_type: "WhatsAppType"):
        self._assigned_users_api = AssignedUsersAPI(app_type)
        self._credit_line_facade = CreditLineFacade(app_type)
        self._phone_numbers_api = PhoneNumbersAPI(app_type)

    def create(self, waba_id) -> PhoneNumber:
        self._assigned_users_api.add_system_user_waba(waba_id)
        self._assigned_users_api.validate_system_user_waba(waba_id)
        self._credit_line_facade.attach(waba_id)
        return self._phone_numbers_api.get_phone_number(waba_id)


class WhatsAppFacade(object):
    def __init__(self, waba_id: str, app_type: "WhatsAppType"):
        self._waba_id = waba_id

        self._onpremise_queue_facade = OnPremiseQueueFacade()
        self._onpremise_facade = OnPremiseFacade()
        self._facebook_api_facade = FacebookAPIFacade(app_type)

    def create(self) -> WhatsApp:

        phone_number = self._facebook_api_facade.create(self._waba_id)

        onpremise_url = self._onpremise_queue_facade.book_whatsapp()
        # onpremise_password = self._onpremisse_facade.change_password(onpremise_url)
        onpremise_password = "8TT_B-TUrVAszCyrzpwM"
        onpremise_token = self._onpremise_facade.register_whatsapp(onpremise_url, onpremise_password, phone_number)

        return WhatsApp(onpremise_url, onpremise_password, onpremise_token, phone_number)
