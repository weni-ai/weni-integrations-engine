import uuid
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from ...models import Project
from ..project_creation import ProjectCreationDTO, ProjectCreationUseCase


User = get_user_model()


class ProjectCreationTestCase(TestCase):
    def setUp(self) -> None:
        self.template_type_integration = MagicMock()
        self.user = User.objects.create_superuser(email="user@marketplace.ai")
        self.project = Project.objects.create(uuid=uuid.uuid4(), name="Test Project", created_by=self.user)

    def test_get_or_create_user_by_email(self):
        usecase = ProjectCreationUseCase(self.template_type_integration)
        user, _ = usecase.get_or_create_user_by_email("user@marketplace.ai")

        self.assertEqual(user, self.user)

    def test_get_or_create_user_by_email_creates_new_user(self):
        new_user_email = "newuser@marketplace.ai"
        usecase = ProjectCreationUseCase(self.template_type_integration)
        user, _ = usecase.get_or_create_user_by_email(new_user_email)

        self.assertEqual(user.email, new_user_email)

    def test_creating_template_project_integrate_template_type_in_project_is_called(self):
        project_uuid = uuid.uuid4()
        project_dto = ProjectCreationDTO(
            uuid=project_uuid,
            name="Fake Project",
            is_template=True,
            date_format="fake",
            timezone="fake",
            template_type_uuid=None,
        )
        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.create_project(project_dto, "user@marketplace.ai")

        self.template_type_integration.integrate_template_type_in_project.assert_called_once()
        self.assertTrue(Project.objects.filter(uuid=project_uuid).exists())

    def test_create_non_template_project(self):
        project_uuid = uuid.uuid4()
        project_dto = ProjectCreationDTO(
            uuid=project_uuid,
            name="Fake Project",
            is_template=False,
            date_format="fake",
            timezone="fake",
            template_type_uuid=None,
        )
        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.create_project(project_dto, "user@marketplace.ai")

        self.assertTrue(Project.objects.filter(uuid=project_uuid).exists())
        self.template_type_integration.integrate_template_type_in_project.assert_not_called()

    def test_get_or_create_project_returns_existing_project(self):
        project_dto = ProjectCreationDTO(
            uuid=self.project.uuid,
            name="Fake Project",
            is_template=False,
            date_format="fake",
            timezone="fake",
            template_type_uuid=None,
        )

        usecase = ProjectCreationUseCase(self.template_type_integration)
        project, created = usecase.get_or_create_project(project_dto, self.user)
        self.assertEqual(project, self.project)
        self.assertFalse(created)

    def test_get_or_create_project_with_non_existent_uuid(self):
        project_uuid = uuid.uuid4()
        project_dto = ProjectCreationDTO(
            uuid=project_uuid,
            name="Fake Project",
            is_template=False,
            date_format="fake",
            timezone="fake",
            template_type_uuid=None,
        )

        usecase = ProjectCreationUseCase(self.template_type_integration)
        project, created = usecase.get_or_create_project(project_dto, self.user)
        self.assertTrue(created)
        self.assertEqual(project.uuid, project_uuid)
