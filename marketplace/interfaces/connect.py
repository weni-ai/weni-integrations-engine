from abc import ABC, abstractmethod
from typing import Any


class ConnectInterface(ABC):
    @abstractmethod
    def create_external_service(
        self, user: str, project_uuid: str, type_fields: dict, type_code: str
    ) -> Any:
        pass
