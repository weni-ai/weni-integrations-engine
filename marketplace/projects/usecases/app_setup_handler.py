from django.contrib.auth import get_user_model

from ..models import Project, TemplateType
from .exceptions import InvalidTemplateTypeData
from marketplace.core.types import APPTYPES


User = get_user_model()


class AppSetupHandlerUseCase:
    def __init__(self, app_configuration):
        self.__app_configuration = app_configuration

    def setup_apps_in_project(
        self, project: Project, template_type: TemplateType, user: User
    ):
        setup = template_type.setup

        if setup == {}:
            raise InvalidTemplateTypeData(
                f"The `setup` of TemplateType {template_type.uuid} is empty!"
            )

        for setup_app in setup.get("apps"):
            code = setup_app.get("code")

            if not code:
                raise InvalidTemplateTypeData(
                    f"The TemplateType {template_type.uuid} has an invalid setup!"
                )

            try:
                apptype = APPTYPES.get(code)
            except KeyError:
                raise InvalidTemplateTypeData(
                    f"TemplateType {template_type.uuid} has invalid app code!"
                )

            app = apptype.create_app(project_uuid=str(project.uuid), created_by=user)
            self.__app_configuration.configure_app(app, apptype, user)
