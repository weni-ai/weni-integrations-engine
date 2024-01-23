import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from ..template_type_creation import create_template_type
from ...models import TemplateType


User = get_user_model()


class TemplateTypeCreationTestCase(TestCase):
    def setUp(self) -> None:
        self.project_uuid = uuid.uuid4()
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

    def tests_template_type_is_created_with_the_correct_setup(self):
        template_type_uuid = uuid.uuid4()
        apptype = APPTYPES.get("wpp-demo")
        apptype.create_app(created_by=self.user, project_uuid=self.project_uuid)

        create_template_type(
            template_type_uuid, self.project_uuid, "Fake Template Type"
        )

        template_type = TemplateType.objects.get(uuid=template_type_uuid)
        self.assertEqual(template_type.setup, {"apps": [{"code": "wpp-demo"}]})

    def test_renamed_when_passing_existing_template_type_uuid(self):
        template_type_uuid = uuid.uuid4()
        TemplateType.objects.create(
            uuid=template_type_uuid, name="Fake Template Type", setup={"fake": "test"}
        )

        create_template_type(template_type_uuid, self.project_uuid, "New Name")

        template_type = TemplateType.objects.get(uuid=template_type_uuid)
        self.assertEqual(template_type.name, "New Name")

    def test_ignore_apps_that_cannot_be_turned_into_template_type(self):
        apptype = APPTYPES.get("wpp-demo")
        apptype.create_app(created_by=self.user, project_uuid=self.project_uuid)

        apptype = APPTYPES.get("wpp-cloud")
        apptype.create_app(created_by=self.user, project_uuid=self.project_uuid)

        template_type_uuid = uuid.uuid4()
        create_template_type(
            template_type_uuid, self.project_uuid, "Fake Template Type"
        )
