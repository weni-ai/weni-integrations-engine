import uuid
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from ...models import Project
from ..project_creation import ProjectCreationDTO, ProjectCreationUseCase
from marketplace.accounts.models import ProjectAuthorization


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
            authorizations=[],
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
            authorizations=[],
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
            authorizations=[],
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
            authorizations=[],
        )

        usecase = ProjectCreationUseCase(self.template_type_integration)
        project, created = usecase.get_or_create_project(project_dto, self.user)
        self.assertTrue(created)
        self.assertEqual(project.uuid, project_uuid)

    def test_set_user_project_authorization_role_create_new_project_authorization(self):
        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.set_user_project_authorization_role(self.user, self.project, ProjectAuthorization.ROLE_ADMIN)

        project_auth = ProjectAuthorization.objects.get(project_uuid=self.project.uuid, user=self.user)
        self.assertEquals(project_auth.role, ProjectAuthorization.ROLE_ADMIN)

    def test_project_authorization_already_exists_is_updated_on_set_user_project_authorization_role(self):
        ProjectAuthorization.objects.create(user=self.user, project_uuid=self.project.uuid, role=1)

        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.set_user_project_authorization_role(self.user, self.project, ProjectAuthorization.ROLE_ADMIN)

        project_auth = ProjectAuthorization.objects.get(project_uuid=self.project.uuid, user=self.user)
        self.assertEquals(project_auth.role, ProjectAuthorization.ROLE_ADMIN)

    def test_create_project_sets_created_user_permission_equal_to_admin(self):
        project_uuid = uuid.uuid4()
        project_dto = ProjectCreationDTO(
            uuid=project_uuid,
            name="Fake Project",
            is_template=True,
            date_format="fake",
            timezone="fake",
            template_type_uuid=None,
            authorizations=[],
        )
        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.create_project(project_dto, self.user.email)

        project_auth = ProjectAuthorization.objects.get(project_uuid=project_uuid, user=self.user)
        self.assertEquals(project_auth.role, ProjectAuthorization.ROLE_ADMIN)

    def test_set_users_project_authorizations_creates_object_with_rules(self):

        authorizations = [
            {"user_email": "userrole3@marketplace.ai", "role": 3},
            {"user_email": "userrole2@marketplace.ai", "role": 2},
            {"user_email": "userrole1@marketplace.ai", "role": 1},
        ]

        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.set_users_project_authorizations(self.project, authorizations)

        for authorization in authorizations:
            db_authorization = ProjectAuthorization.objects.get(
                user__email=authorization.get("user_email"), project_uuid=self.project.uuid
            )
            self.assertEquals(db_authorization.role, authorization.get("role"))

    def test_set_users_project_authorizations_ignores_invalid_roles_and_emails(self):
        authorizations = [
            {"user_email": "userrole3@marketplace.ai", "role": 3},
            {"user_email": "userrole2@marketplace.ai", "role": 2},
            {"user_email": "userignore1@marketplace.ai"},
            {"role": 1},
            {"user_email": "userignore2@marketplace.ai", "role": None},
            {"user_email": None, "role": 3},
        ]

        usecase = ProjectCreationUseCase(self.template_type_integration)
        usecase.set_users_project_authorizations(self.project, authorizations)

        project_authorizations = ProjectAuthorization.objects.filter(project_uuid=self.project.uuid)

        self.assertEquals(project_authorizations.count(), 2)

        self.assertTrue(project_authorizations.filter(user__email="userrole3@marketplace.ai").exists())
        self.assertTrue(project_authorizations.filter(user__email="userrole2@marketplace.ai").exists())

        self.assertFalse(project_authorizations.filter(user__email="userignore1@marketplace.ai").exists())
        self.assertFalse(project_authorizations.filter(user__email="userignore2@marketplace.ai").exists())
