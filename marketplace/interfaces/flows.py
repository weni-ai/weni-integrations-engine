from abc import ABC, abstractmethod
from typing import Any


class FlowsInterface(ABC):
    @abstractmethod
    def list_external_types(self, flows_type_code=None) -> Any:
        pass

    def release_external_service(self, uuid: str, user_email: str) -> Any:
        pass
