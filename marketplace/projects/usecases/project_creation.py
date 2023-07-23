from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import Project, TemplateType
from .exceptions import InvalidProjectData


User = get_user_model()


@dataclass
class ProjectCreationDTO:
    uuid: str
    name: str
    is_template: bool
    user_email: str
    date_format: str
    timezone: str
    template_type_uuid: str


class ProjectCreationUseCase:
    def __init__(self, app_setup_handler):
        self.__app_setup_handler = app_setup_handler

    def create_project(self, project_dto: ProjectCreationDTO):
        project: Project = None
        template_type: TemplateType = None
        user: User = None

        if project_dto.is_template and project_dto.template_type_uuid is None:
            raise InvalidProjectData("'template_type_uuid' cannot be empty when 'is_template' is True!")

        try:
            template_type = TemplateType.objects.get(uuid=project_dto.template_type_uuid)
        except TemplateType.DoesNotExist:
            raise InvalidProjectData(f"Template Type with uuid `{project_dto.template_type_uuid}` does not exists!")

        try:
            user = User.objects.get(email=project_dto.user_email)
        except User.DoesNotExist:
            raise InvalidProjectData(f"User with email `{project_dto.user_email}` does not exist!")

        project = Project.objects.filter(uuid=project_dto.uuid).first()

        if project:
            if project_dto.is_template and project.template_type is not None:
                raise InvalidProjectData(f"The project `{project.uuid}` already has an integrated template!")

        else:
            project = Project.objects.create(
                uuid=project_dto.uuid,
                name=project_dto.name,
                is_template=project_dto.is_template,
                date_format=project_dto.date_format,
                timezone=project_dto.timezone,
                created_by=user,
            )

        if project_dto.is_template:
            self.__app_setup_handler.setup_apps_in_project(project, template_type, user)
            project.template_type = template_type
            project.save()
