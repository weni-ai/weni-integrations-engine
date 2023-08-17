from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..models import Project

    User = get_user_model()


class TemplateTypeIntegrationInterface(ABC):
    @abstractmethod
    def integrate_template_type_in_project(self, project: "Project", template_type_uuid: str, user: "User"):
        pass
