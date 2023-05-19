import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.wpp_templates.models import (
    TemplateMessage,
    TemplateTranslation,
    TemplateButton,
    TemplateHeader,
)

User = get_user_model()


class TemplateButtonModelTestCase(TestCase):
    def setUp(self):
        self.app = App.objects.create(
            config=dict(waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=User.objects.get_admin_user(),
        )

        self.template_message = TemplateMessage.objects.create(
            name="teste",
            app=self.app,
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
        )
        super().setUp()

    def test_create_template_button_url(self):
        TemplateButton.objects.create(
            translation=self.template_translation,
            button_type="PHONE_NUMBER",
            country_code=55,
        )


class TemplateHeaderModelTestCase(TestCase):
    def setUp(self):
        self.app = App.objects.create(
            config=dict(waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=User.objects.get_admin_user(),
        )

        self.template_message = TemplateMessage.objects.create(
            name="teste",
            app=self.app,
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
        )
        super().setUp()

    def test_create_template_header_text(self):
        TemplateHeader.objects.create(
            translation=self.template_translation, header_type="TEXT", text="teste"
        )
