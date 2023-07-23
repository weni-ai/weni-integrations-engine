from django.contrib.auth import get_user_model

from ..models import Project, TemplateType
from .exceptions import InvalidTemplateTypeData
from marketplace.core.types import APPTYPES


User = get_user_model()


class AppSetupHandlerUseCase:
    def __init__(self, channel_client, channel_token_client):
        self.__channel_client = channel_client
        self.__channel_token_client = channel_token_client

    def setup_apps_in_project(self, project: Project, template_type: TemplateType, user: User):
        setup = template_type.setup

        if setup == {}:
            raise InvalidTemplateTypeData(f"The `setup` of TemplateType {template_type.uuid} is empty!")

        for setup_app in setup.get("apps"):
            code = setup_app.get("code")

            if not code:
                raise InvalidTemplateTypeData(f"The TemplateType {template_type.uuid} has an invalid setup!")

            try:
                apptype = APPTYPES.get(code)
            except KeyError:
                raise InvalidTemplateTypeData(f"TemplateType {template_type.uuid} has invalid app code!")

            app = apptype.create_app(project_uuid=str(project.uuid), created_by=user)
            apptype.configure_app(app, user, self.__channel_client, self.__channel_token_client)
