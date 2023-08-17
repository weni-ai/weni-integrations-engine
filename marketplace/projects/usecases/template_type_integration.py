from typing import TYPE_CHECKING

from .interfaces import TemplateTypeIntegrationInterface
from .exceptions import InvalidTemplateTypeData
from ..models import TemplateType


if TYPE_CHECKING:
    from ..models import Project
    from django.contrib.auth import get_user_model

    User = get_user_model()


class TemplateTypeIntegrationUseCase(TemplateTypeIntegrationInterface):
    def __init__(self, app_setup_handler):
        self.__app_setup_handler = app_setup_handler

    def integrate_template_type_in_project(self, project: "Project", template_type_uuid: str, user: "User") -> None:
        if project.template_type is not None:
            raise InvalidTemplateTypeData(f"The project `{project.uuid}` already has an integrated template!")

        if template_type_uuid is None:
            raise InvalidTemplateTypeData("'template_type_uuid' cannot be empty when 'is_template' is True!")

        try:
            template_type = TemplateType.objects.get(uuid=template_type_uuid)
        except TemplateType.DoesNotExist:
            raise InvalidTemplateTypeData(f"Template Type with uuid `{template_type_uuid}` does not exists!")

        self.__app_setup_handler.setup_apps_in_project(project, template_type, user)
        project.template_type = template_type
        project.save()
