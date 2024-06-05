from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ProfileHandlerInterface(ABC):
    @abstractmethod
    def get_profile(self):
        pass

    @abstractmethod
    def set_profile(self):
        pass

    @abstractmethod
    def delete_profile_photo(self):
        pass


class BusinessProfileHandlerInterface(ABC):
    @abstractmethod
    def get_profile(self):
        pass

    @abstractmethod
    def set_profile(self):
        pass


class TemplatesRequestsInterface(ABC):
    @abstractmethod
    def create_template_message(
        self, waba_id: str, name: str, category: str, components: list, language: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_template_analytics(
        self, waba_id: str, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def enable_template_insights(self, waba_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_template_messages(self, waba_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_template_namespace(self, waba_id: str) -> str:
        pass

    @abstractmethod
    def update_template_message(
        self, message_template_id: str, name: str, components: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_template_message(self, waba_id: str, name: str) -> Dict[str, Any]:
        pass


class PhotoAPIRequestsInterface(ABC):
    @abstractmethod
    def create_upload_session(self, file_length: int, file_type: str) -> str:
        pass

    @abstractmethod
    def upload_photo(
        self, upload_session_id: str, photo: Any, is_uploading: bool = False
    ) -> str:
        pass

    @abstractmethod
    def set_photo(self, photo: Any, phone_number_id: str) -> Any:
        pass

    @abstractmethod
    def upload_session(
        self, upload_session_id: str, file_type: str, data: bytes
    ) -> str:
        pass


class PhoneNumbersRequestsInterface(ABC):
    @abstractmethod
    def get_phone_numbers(self, waba_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_phone_number(self, phone_number_id: str) -> Dict[str, Any]:
        pass


class CloudProfileRequestsInterface(ABC):
    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_profile(self, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_profile_photo(self) -> None:
        pass


class BusinessMetaRequestsInterface(ABC):
    @abstractmethod
    def exchange_auth_code_to_token(self, auth_code: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_waba_info(
        self, fields: str, user_access_token: str, waba_id: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def assign_system_user(self, waba_id: str, permission: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def share_credit_line(self, waba_id: str, waba_currency: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def subscribe_app(self, waba_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def register_phone_number(
        self, phone_number_id: str, user_access_token: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass
