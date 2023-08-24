import uuid
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from ...models import Project, TemplateType
from ..template_type_integration import TemplateTypeIntegrationUseCase
from ..exceptions import InvalidTemplateTypeData


User = get_user_model()


class TemplateTypeIntegrationTestCase(TestCase):
    def setUp(self) -> None:
        self.app_setup_handler = MagicMock()
        self.user = User.objects.create_superuser(email="user@marketplace.ai")
        self.project = Project.objects.create(uuid=uuid.uuid4(), name="Test Project", created_by=self.user)

    def test_project_already_has_template_raises_invalid_template_type_data(self):
        template_type_uuid = uuid.uuid4()
        template_type = TemplateType.objects.create(uuid=template_type_uuid, name="Fake Template Type")
        self.project.template_type = template_type
        self.project.save()

        usecase = TemplateTypeIntegrationUseCase(self.app_setup_handler)
        with self.assertRaisesMessage(
            InvalidTemplateTypeData, f"The project `{self.project.uuid}` already has an integrated template!"
        ):
            usecase.integrate_template_type_in_project(self.project, template_type_uuid, self.user)

    def test_send_template_type_uuid_equal_to_none_raises_invalid_template_type_data(self):
        usecase = TemplateTypeIntegrationUseCase(self.app_setup_handler)
        with self.assertRaisesMessage(
            InvalidTemplateTypeData, "'template_type_uuid' cannot be empty when 'is_template' is True!"
        ):
            usecase.integrate_template_type_in_project(self.project, None, self.user)

    def test_sending_uuid_template_type_does_not_exist_raises_invalid_template_type_data(self):
        template_type_uuid = uuid.uuid4()
        usecase = TemplateTypeIntegrationUseCase(self.app_setup_handler)
        with self.assertRaisesMessage(
            InvalidTemplateTypeData, f"Template Type with uuid `{template_type_uuid}` does not exists!"
        ):
            usecase.integrate_template_type_in_project(self.project, template_type_uuid, self.user)

    def test_setup_apps_in_project_called_once(self):
        template_type = TemplateType.objects.create(uuid=uuid.uuid4(), name="Fake Template Type")

        usecase = TemplateTypeIntegrationUseCase(self.app_setup_handler)
        usecase.integrate_template_type_in_project(self.project, template_type.uuid, self.user)
        self.app_setup_handler.setup_apps_in_project.assert_called_once()

    def test_integrate_template_type_in_project_assigns_template_type_in_project(self):
        template_type_uuid = uuid.uuid4()
        template_type = TemplateType.objects.create(uuid=template_type_uuid, name="Fake Template Type")

        usecase = TemplateTypeIntegrationUseCase(self.app_setup_handler)
        usecase.integrate_template_type_in_project(self.project, template_type_uuid, self.user)
        self.assertEqual(self.project.template_type, template_type)
