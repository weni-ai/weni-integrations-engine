import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db.utils import IntegrityError

from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader

User = get_user_model()


class TemplateButtonModelTestCase(TestCase):
    def setUp(self):
        self.template_message = TemplateMessage.objects.create(
            name="teste",
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            namespace="teste-namespace",
            code="wwc",
            project_uuid=uuid.uuid4(),
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message, status="APPROVED", language="pt_br", country="Brasil", variable_count=1
        )
        super().setUp()

    def test_create_template_button_url_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateButton.objects.create(
                translation=self.template_translation, button_type="URL", country_code=55
            )

    def test_create_template_button_phone_number_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateButton.objects.create(
                translation=self.template_translation, button_type="PHONE_NUMBER", country_code=55
            )


class TemplateHeaderModelTestCase(TestCase):
    def setUp(self):
        self.template_message = TemplateMessage.objects.create(
            name="teste",
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            namespace="teste-namespace",
            code="wwc",
            project_uuid=uuid.uuid4(),
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message, status="APPROVED", language="pt_br", country="Brasil", variable_count=1
        )
        super().setUp()

    def test_create_template_header_text_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateHeader.objects.create(translation=self.template_translation, header_type="TEXT")
