import uuid
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from ..app_setup_handler import AppSetupHandlerUseCase
from ...models import Project, TemplateType
from ..exceptions import InvalidTemplateTypeData


User = get_user_model()


class AppSetupHandlerTestCase(TestCase):
    def setUp(self):
        self.app_configuration = MagicMock()
        self.uescase = AppSetupHandlerUseCase(self.app_configuration)

        self.user = User.objects.create_superuser(email="user@marketplace.ai")
        self.project = Project.objects.create(uuid=uuid.uuid4(), name="Test Project", created_by=self.user)

    def test_empty_setup_raises_invalid_template_type_data(self):
        template_type = TemplateType.objects.create(uuid=uuid.uuid4(), name="Fake TT", setup={})

        error_message = f"The `setup` of TemplateType {template_type.uuid} is empty!"
        with self.assertRaisesMessage(InvalidTemplateTypeData, error_message):
            self.uescase.setup_apps_in_project(self.project, template_type, self.user)

    def test_setup_without_code_raises_invalid_template_type_data(self):
        template_type = TemplateType.objects.create(uuid=uuid.uuid4(), name="Fake TT", setup={"apps": [{}]})

        error_message = f"The TemplateType {template_type.uuid} has an invalid setup!"
        with self.assertRaisesMessage(InvalidTemplateTypeData, error_message):
            self.uescase.setup_apps_in_project(self.project, template_type, self.user)

    def test_setup_without_invalid_code_raises_invalid_template_type_data(self):
        template_type = TemplateType.objects.create(
            uuid=uuid.uuid4(), name="Fake TT", setup={"apps": [{"code": "fake-code"}]}
        )

        error_message = f"TemplateType {template_type.uuid} has invalid app code!"
        with self.assertRaisesMessage(InvalidTemplateTypeData, error_message):
            self.uescase.setup_apps_in_project(self.project, template_type, self.user)

    def test_configure_app_called_once_with_valid_template_type(self):
        template_type = TemplateType.objects.create(
            uuid=uuid.uuid4(), name="Fake TT", setup={"apps": [{"code": "wpp-demo"}]}
        )

        self.uescase.setup_apps_in_project(self.project, template_type, self.user)
        self.app_configuration.configure_app.assert_called_once()
