import uuid

from django.test import TestCase
from django.db.utils import IntegrityError

from marketplace.accounts.models import User, ProjectAuthorization


class TestUserCreate(TestCase):
    def setUp(self):
        self.user_info = dict(email="fake@email.com", password="fake123pass")

    def test_create_user(self):
        user = User.objects.create_user(**self.user_info)

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.user_info["email"], user.email)

    def test_create_super_user(self):
        user = User.objects.create_superuser(**self.user_info)

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(self.user_info["email"], user.email)

    def test_create_super_user_without_is_staff(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True."):
            User.objects.create_superuser(**self.user_info, is_staff=False)

    def test_create_super_user_without_is_superuser(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_superuser=True."):
            User.objects.create_superuser(**self.user_info, is_superuser=False)

    def test_empty_email(self):
        user_info = self.user_info
        user_info.update(email="")

        with self.assertRaises(ValueError):
            User.objects.create_superuser(**self.user_info)


class ProjectAuthorizationTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")

    def test_related_user_authorizations(self):
        authorization = ProjectAuthorization.objects.create(user=self.user, project_uuid=uuid.uuid4())
        self.assertIn(authorization, self.user.authorizations.all())

    def test_project_authorization_role(self):
        authorization = ProjectAuthorization.objects.create(user=self.user, project_uuid=uuid.uuid4())
        self.assertEqual(authorization.role, ProjectAuthorization.ROLE_NOT_SETTED)

    def test_user_project_uuid_unique_together(self):
        project_uuid = uuid.uuid4()
        ProjectAuthorization.objects.create(user=self.user, project_uuid=project_uuid)

        with self.assertRaises(IntegrityError):
            ProjectAuthorization.objects.create(user=self.user, project_uuid=project_uuid)


class ProjectAuthorizationMethodsTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.project_uuid = uuid.uuid4()
        self.user = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")
        self.authorization = ProjectAuthorization.objects.create(user=self.user, project_uuid=self.project_uuid)

    def test_str_method(self):
        self.assertEqual(str(self.authorization), f"{self.user} - {self.project_uuid}")
