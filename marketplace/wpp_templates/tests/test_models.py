import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db.utils import IntegrityError

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader

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
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message, status="APPROVED", language="pt_br", variable_count=1
        )
        super().setUp()

    def test_create_template_button_url(self):
        TemplateButton.objects.create(translation=self.template_translation, button_type="URL", url="https://weni.ai/")

    def test_create_template_button_phone_number(self):
        TemplateButton.objects.create(
            translation=self.template_translation,
            button_type="PHONE_NUMBER",
            country_code=55,
            phone_number="738123242",
        )

    def test_create_template_button_url_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateButton.objects.create(translation=self.template_translation, button_type="URL", country_code=55)

    def test_create_template_button_phone_number_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateButton.objects.create(
                translation=self.template_translation, button_type="PHONE_NUMBER", country_code=55
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
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )

        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message, status="APPROVED", language="pt_br", variable_count=1
        )
        super().setUp()

    def test_create_template_header_text(self):
        header = TemplateHeader.objects.create(translation=self.template_translation, header_type="TEXT", text="teste")

        created_templates = TemplateHeader.objects.filter(uuid=header.uuid)

        self.assertEqual(created_templates.count(), 1)
        self.assertEqual(created_templates.first().header_type, header.header_type)
        self.assertEqual(created_templates.first().text, header.text)
        self.assertEqual(created_templates.first().media, None)

    def test_create_template_header_image(self):
        header = TemplateHeader.objects.create(
            translation=self.template_translation, header_type="IMAGE", media="fdas432432432342_dsdsa"
        )

        created_templates = TemplateHeader.objects.filter(uuid=header.uuid)

        self.assertEqual(created_templates.count(), 1)
        self.assertEqual(created_templates.first().header_type, header.header_type)
        self.assertEqual(created_templates.first().media, header.media)
        self.assertEqual(created_templates.first().text, None)

    def test_create_template_header_document(self):
        header = TemplateHeader.objects.create(
            translation=self.template_translation, header_type="DOCUMENT", media="fdas432432432342_dsdsa"
        )

        created_templates = TemplateHeader.objects.filter(uuid=header.uuid)

        self.assertEqual(created_templates.count(), 1)
        self.assertEqual(created_templates.first().header_type, header.header_type)
        self.assertEqual(created_templates.first().media, header.media)
        self.assertEqual(created_templates.first().text, None)

    def test_create_template_video_document(self):
        header = TemplateHeader.objects.create(
            translation=self.template_translation, header_type="VIDEO", media="fdas432432432342_dsdsa"
        )

        created_templates = TemplateHeader.objects.filter(uuid=header.uuid)

        self.assertEqual(created_templates.count(), 1)
        self.assertEqual(created_templates.first().header_type, header.header_type)
        self.assertEqual(created_templates.first().media, header.media)
        self.assertEqual(created_templates.first().text, None)

    def test_create_template_header_text_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateHeader.objects.create(translation=self.template_translation, header_type="TEXT")

    def test_create_template_header_image_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateHeader.objects.create(translation=self.template_translation, header_type="IMAGE")

    def test_create_template_header_document_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateHeader.objects.create(translation=self.template_translation, header_type="DOCUMENT")

    def test_create_template_header_video_required_fail(self):
        with self.assertRaises(IntegrityError):
            TemplateHeader.objects.create(translation=self.template_translation, header_type="VIDEO")
