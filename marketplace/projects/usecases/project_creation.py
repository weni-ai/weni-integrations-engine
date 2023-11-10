from dataclasses import dataclass
from django.contrib.auth import get_user_model

from ..models import Project
from .interfaces import TemplateTypeIntegrationInterface
from marketplace.accounts.models import ProjectAuthorization


User = get_user_model()


@dataclass
class ProjectCreationDTO:
    uuid: str
    name: str
    is_template: bool
    date_format: str
    timezone: str
    template_type_uuid: str
    authorizations: list


class ProjectCreationUseCase:
    def __init__(self, template_type_integration: TemplateTypeIntegrationInterface):
        self.__template_type_integration = template_type_integration

    def set_user_project_authorization_role(
        self, user: User, project: Project, role: int
    ):
        project_authorization, created = ProjectAuthorization.objects.get_or_create(
            user=user, project_uuid=project.uuid, defaults={"role": role}
        )

        if not created:
            project_authorization.role = role
            project_authorization.save()

    def get_or_create_user_by_email(self, email: str) -> tuple:
        return User.objects.get_or_create(email=email)

    def get_or_create_project(
        self, project_dto: ProjectCreationDTO, user: User
    ) -> tuple:
        return Project.objects.get_or_create(
            uuid=project_dto.uuid,
            defaults=dict(
                name=project_dto.name,
                date_format=project_dto.date_format,
                timezone=project_dto.timezone,
                created_by=user,
                is_template=project_dto.is_template,
            ),
        )

    def set_users_project_authorizations(self, project: Project, authorizations: list):
        for authorization in authorizations:
            user_email = authorization.get("user_email")
            role = authorization.get("role")

            if not user_email or not role:
                continue

            user, _ = self.get_or_create_user_by_email(user_email)

            self.set_user_project_authorization_role(
                user=user, project=project, role=role
            )

    def create_project(self, project_dto: ProjectCreationDTO, user_email: str) -> None:
        user, _ = self.get_or_create_user_by_email(user_email)
        project, _ = self.get_or_create_project(project_dto, user)

        self.set_user_project_authorization_role(
            user=user, project=project, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.set_users_project_authorizations(project, project_dto.authorizations)

        if project_dto.is_template:
            self.__template_type_integration.integrate_template_type_in_project(
                project, project_dto.template_type_uuid, user
            )
