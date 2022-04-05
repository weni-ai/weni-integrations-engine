import uuid

from django.test import TestCase
from django.db import connection
from django.db.utils import IntegrityError, ProgrammingError
from django.db.models.base import ModelBase
from django.conf import settings

from marketplace.accounts.models import User, ProjectAuthorization
from marketplace.core.models import BaseModel


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

    def test_get_admin_user_method(self):
        user_count = User.objects.count()
        user = User.objects.get_admin_user()

        self.assertNotEqual(user_count, User.objects.count())
        self.assertEqual(user.email, settings.ADMIN_USER_EMAIL)


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

        self.fakemodel = self.__class__._base_model
        self.fakemodel_instance = self.fakemodel.objects.create(created_by=self.user)

    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, "_base_model"):
            cls._base_model = ModelBase(
                "AuthorizationTestFakeModel", (BaseModel,), {"__module__": BaseModel.__module__}
            )

        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(cls._base_model)
        except ProgrammingError:
            pass
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(cls._base_model)
        except ProgrammingError:
            pass

        super().tearDownClass()

    def test_str_method(self):
        self.assertEqual(str(self.authorization), f"{self.user} - {self.project_uuid}")

    def test_set_role_method_with_invalid_role(self):
        invalid_role = 4
        with self.assertRaisesMessage(AssertionError, f"Role: {invalid_role} isn't valid!"):
            self.authorization.set_role(invalid_role)

    def test_is_viewer_method(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        self.assertTrue(self.authorization.is_viewer)

    def test_is_contributor_method(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.assertTrue(self.authorization.is_contributor)

    def test_is_admin_method(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.assertTrue(self.authorization.is_admin)

    def test_can_write_method_with_authorization_role_not_set_can_write(self):
        self.assertFalse(self.authorization.can_write)

    def test_can_write_method_with_authorization_role_viewer_can_write(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        self.assertFalse(self.authorization.can_write)

    def test_can_write_method_with_authorization_role_contributor_can_write(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.assertTrue(self.authorization.can_write)

    def test_can_write_method_with_authorization_role_admin_can_write(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.assertTrue(self.authorization.can_write)

    def test_can_contribute_method_return_true(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.assertTrue(self.authorization.can_contribute(self.fakemodel_instance))

    def test_can_contribute_method_with_invalid_user(self):
        user = User.objects.create(email="user2@marketplace.ai", password="fake@pass#$")
        fakemodel_instance = self.fakemodel.objects.create(created_by=user)

        self.authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.assertFalse(self.authorization.can_contribute(fakemodel_instance))

    def test_can_destroy_method_with_admin_authorization(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.assertTrue(self.authorization.can_destroy(self.fakemodel_instance))

    def test_can_destroy_method_with_contributor_authorization(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.assertTrue(self.authorization.can_destroy(self.fakemodel_instance))

    def test_can_destroy_method_with_viewer_authorization(self):
        self.authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        self.assertFalse(self.authorization.can_destroy(self.fakemodel_instance))
