import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from marketplace.wpp_templates.serializers import (
    TemplateTranslationSerializer,
    TemplateMessageSerializer,
)

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

    def test_template_header_to_dict(self):
        header = TemplateHeader.objects.create(
            translation=self.template_translation, header_type="TEXT", text="teste"
        )
        expected_dict = dict(header_type="TEXT", text="teste")
        self.assertEqual(header.to_dict(), expected_dict)


class TemplateMessageModelTestCase(TestCase):
    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=User.objects.get_admin_user(),
        )

    def test_name_validation(self):
        # Trying to create a TemplateMessage with an invalid name
        with self.assertRaises(ValidationError):
            invalid_name = "Invalid Name With Spaces And UpperCase"
            template_message = TemplateMessage(
                name=invalid_name,
                category="ACCOUNT_UPDATE",
                app=self.app,
                created_by=User.objects.get_admin_user(),
                template_type="TEXT",
            )
            template_message.clean_fields()

        # Trying to create a TemplateMessage without a name
        with self.assertRaises(ValidationError):
            template_message_without_name = TemplateMessage(
                category="ACCOUNT_UPDATE",
                app=self.app,
                created_by=User.objects.get_admin_user(),
                template_type="TEXT",
            )
            template_message_without_name.clean_fields()

        # Checking if a valid name passes validation
        try:
            valid_name = "valid_name_without_spaces"
            valid_template_message = TemplateMessage(
                name=valid_name,
                category="ACCOUNT_UPDATE",
                app=self.app,
                created_by=User.objects.get_admin_user(),
                template_type="TEXT",
            )
            valid_template_message.clean_fields()
        except ValidationError:
            self.fail("A ValidationError was raised, but it shouldn't have been.")


class TemplateTranslationSerializerTestCase(TestCase):
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
        self.header = TemplateHeader.objects.create(
            translation=self.template_translation, header_type="TEXT", text="teste"
        )

        self.template_translation_with_body = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            body="Sample Body Text",
        )

        super().setUp()

    def test_template_message_serializer_to_representation(self):
        template_message = TemplateMessage.objects.create(
            name="new teste",
            app=self.app,
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        template_translation = TemplateTranslation.objects.create(
            template=template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
        )
        TemplateHeader.objects.create(
            translation=template_translation, header_type="TEXT", text="new teste"
        )

        serializer = TemplateMessageSerializer(template_message)

        expected_data = {
            "uuid": str(template_message.uuid),
            "name": template_message.name,
            "created_on": template_message.created_on.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "category": template_message.category,
            "gallery_version": None,
            "translations": [
                {
                    "uuid": str(template_translation.uuid),
                    "message_template_id": None,
                    "status": "APPROVED",
                    "language": "pt_br",
                    "country": None,
                    "body": None,
                    "footer": None,
                    "buttons": [],
                    "variable_count": 1,
                    "header": {"header_type": "TEXT", "text": "new teste"},
                }
            ],
            "text_preview": None,
        }
        serialized_data = serializer.data
        serialized_data["translations"] = [
            dict(item) for item in serialized_data["translations"]
        ]
        self.assertEqual(serialized_data, expected_data)

    def test_to_representation_method_with_text_preview(self):
        template_message = TemplateMessage.objects.create(
            name="new test",
            app=self.app,
            category="ACCOUNT_UPDATE",
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        template_translation_1 = TemplateTranslation.objects.create(
            template=template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
        )
        template_translation_2 = TemplateTranslation.objects.create(
            template=template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
        )
        serializer = TemplateMessageSerializer(template_message)

        expected_data = {
            "uuid": str(template_message.uuid),
            "name": template_message.name,
            "created_on": template_message.created_on.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "category": template_message.category,
            "gallery_version": None,
            "translations": [
                TemplateTranslationSerializer(template_translation_1).data,
                TemplateTranslationSerializer(template_translation_2).data,
            ],
            "text_preview": None,
        }
        self.assertEqual(serializer.data, expected_data)
