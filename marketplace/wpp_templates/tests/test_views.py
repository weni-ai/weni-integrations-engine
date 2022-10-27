import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.base import FakeRequestsResponse
from ..views import TemplateMessageViewSet
from ..languages import LANGUAGES

User = get_user_model()


class FakeFacebookResponse(FakeRequestsResponse):
    status_code = 200


class WhatsappTemplateListTestCase(APIBaseTestCase):
    url = reverse("app-template-list", kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"})
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
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
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    def _create_translation(self):
        return TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            body="Teste",
            footer="footer-teste",
        )

    def test_list_whatsapp_templates(self):
        response = self.request.get(self.url, app_uuid=str(self.app.uuid)).json.get("results", [{}])[0]

        self.assertEqual(response.get("uuid"), str(self.template_message.uuid))
        self.assertEqual(response.get("name"), self.template_message.name)
        self.assertEqual(response.get("category"), self.template_message.category)

    def test_list_whatsapp_template_with_translation(self):
        template_translation = self._create_translation()

        response = self.request.get(self.url, app_uuid=str(self.app.uuid),).json.get(
            "results", [{}]
        )[0]

        translation = response.get("translations", [{}])[0]

        self.assertEqual(translation.get("uuid"), str(template_translation.uuid))
        self.assertEqual(translation.get("status"), template_translation.status)
        self.assertEqual(translation.get("language"), template_translation.language)
        self.assertEqual(translation.get("body"), template_translation.body)
        self.assertEqual(translation.get("footer"), template_translation.footer)

    def test_list_whatsapp_translation_with_header_text(self):
        template_translation = self._create_translation()

        header = TemplateHeader.objects.create(translation=template_translation, header_type="TEXT", text="teste")

        response = self.request.get(self.url, app_uuid=str(self.app.uuid),).json.get(
            "results", [{}]
        )[0]

        translation = response.get("translations", [{}])[0]

        self.assertEqual(translation.get("header").get("header_type"), header.header_type)
        self.assertEqual(translation.get("header").get("text"), header.text)

    def test_list_whatsapp_translation_with_button_url(self):
        template_translation = self._create_translation()

        button = TemplateButton.objects.create(
            translation=template_translation, button_type="URL", url="https://weni.ai/"
        )

        response = self.request.get(self.url, app_uuid=str(self.app.uuid),).json.get(
            "results", [{}]
        )[0]

        translation = response.get("translations", [{}])[0]

        self.assertEqual(translation.get("buttons")[0].get("button_type"), button.button_type)
        self.assertEqual(translation.get("buttons")[0].get("url"), button.url)

    def test_list_whatsapp_translation_with_button_phone(self):
        template_translation = self._create_translation()

        button = TemplateButton.objects.create(
            translation=template_translation, button_type="PHONE_NUMBER", country_code=55, phone_number="8434920432"
        )

        response = self.request.get(self.url, app_uuid=str(self.app.uuid),).json.get(
            "results", [{}]
        )[0]

        translation = response.get("translations", [{}])[0]

        self.assertEqual(translation.get("buttons")[0].get("button_type"), button.button_type)
        self.assertEqual(translation.get("buttons")[0].get("country_code"), str(button.country_code))
        self.assertEqual(translation.get("buttons")[0].get("phone_number"), button.phone_number)


class WhatsappTemplateCreateTestCase(APIBaseTestCase):
    url = reverse("app-template-list", kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"})
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=User.objects.get_admin_user(),
        )

        self.body = dict(
            name="teste-name",
            category="ACCOUNT_UPDATE",
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_whatsapp_templates(self):
        before_template_messages = TemplateMessage.objects.all().count()
        response = self.request.post(self.url, app_uuid=str(self.app.uuid), body=self.body).json
        total_template_messages = TemplateMessage.objects.all().count()

        self.assertNotEqual(before_template_messages, total_template_messages)
        self.assertEqual(response.get("name"), self.body.get("name"))
        self.assertEqual(response.get("category"), self.body.get("category"))


class WhatsappTemplateDestroyTestCase(APIBaseTestCase):
    url = reverse("app-template-list", kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"})
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
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

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    @patch("requests.delete")
    def test_delete_whatsapp_template(self, mock):
        fake_response = FakeRequestsResponse(data={"success": True})
        fake_response.status_code = 200
        mock.return_value = fake_response

        total_users_before = TemplateMessage.objects.count()
        self.request.delete(self.url, app_uuid=self.app.uuid, uuid=self.template_message.uuid)
        total_users_after = TemplateMessage.objects.count()

        self.assertNotEqual(total_users_before, total_users_after)


class WhatsappTemplateRetrieveTestCase(APIBaseTestCase):
    url = reverse("app-template-list", kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"})
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
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
        )

        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            body="Teste",
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    @property
    def query_parameter(self):
        return f"?uuid={self.template_message.uuid}"

    def test_retrieve_whatsapp_template(self):
        response = self.request.get(self.url, app_uuid=self.app.uuid, uuid=self.template_message.uuid).json

        self.assertEqual(response.get("uuid"), str(self.template_message.uuid))
        self.assertEqual(response.get("name"), self.template_message.name)
        self.assertEqual(response.get("category"), self.template_message.category)


class WhatsappTemplateLanguagesTestCase(APIBaseTestCase):
    url = reverse("app-template-languages", kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"})
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(get="languages"))

    def test_list_whatsapp_template_languages(self):
        response = self.request.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, LANGUAGES)


class WhatsappTranslationCreateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="109552365187427"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=User.objects.get_admin_user(),
        )

        self.template_message = TemplateMessage.objects.create(
            name="teste",
            app=self.app,
            category="TRANSACTIONAL",
            template_type="TEXT",
        )

        self.url = reverse(
            "app-template-translations", kwargs={"app_uuid": self.app.uuid, "uuid": self.template_message.uuid}
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(post="translations"))

    @patch("requests.post")
    def test_create_whatsapp_translation(self, mock):
        mock.return_value = FakeFacebookResponse({"success": True})

        body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            footer={"type": "FOOTER", "text": "Testing footer"},
        )

        self.request.post(self.url, body=body, uuid=str(self.template_message.uuid))

        template_message = TemplateTranslation.objects.all().last()

        self.assertEqual(template_message.language, body.get("language"))
        self.assertEqual(template_message.status, "PENDING")
        self.assertEqual(template_message.body, body.get("body").get("text"))
        self.assertEqual(template_message.country, body.get("country"))
        self.assertEqual(template_message.footer, body.get("footer").get("text"))

    @patch("requests.post")
    def test_create_whatsapp_translation_header_text(self, mock):
        mock.return_value = FakeFacebookResponse({"success": True})

        body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            header={"header_type": "TEXT", "text": "teste_header"},
        )

        self.request.post(self.url, body=body, uuid=str(self.template_message.uuid))

        header = TemplateHeader.objects.all().last()

        self.assertEqual(header.header_type, body.get("header").get("header_type"))
        self.assertEqual(header.text, body.get("header").get("text"))

    @patch("requests.post")
    def test_create_whatsapp_translation_header_media(self, mock):
        mock.return_value = FakeFacebookResponse({"success": True})

        image = "data:image/gif;base64,R0w=="

        body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            header={"header_type": "IMAGE", "media": image},
        )

        self.request.post(self.url, body=body, uuid=str(self.template_message.uuid))

        header = TemplateHeader.objects.all().last()

        self.assertEqual(header.header_type, body.get("header").get("header_type"))
        self.assertEqual(header.media, body.get("header").get("text"))

    @patch("requests.post")
    def test_create_whatsapp_translation_button_url(self, mock):
        mock.return_value = FakeFacebookResponse({"success": True})

        body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            buttons=[{"button_type": "URL", "text": "phone-button-text", "url": "https://weni.ai"}],
        )

        self.request.post(self.url, body=body, uuid=str(self.template_message.uuid))

        button = TemplateButton.objects.all().last()

        self.assertEqual(button.button_type, body.get("buttons")[0].get("button_type"))
        self.assertEqual(button.text, body.get("buttons")[0].get("text"))
        self.assertEqual(button.url, body.get("buttons")[0].get("url"))

    @patch("requests.post")
    def test_create_whatsapp_translation_phone_number(self, mock):
        mock.return_value = FakeFacebookResponse({"success": True})

        body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            buttons=[
                {
                    "button_type": "PHONE_NUMBER",
                    "country_code": 55,
                    "phone_number": "61994308420",
                    "text": "phone-button-text",
                }
            ],
        )

        self.request.post(self.url, body=body, uuid=str(self.template_message.uuid))

        button = TemplateButton.objects.all().last()

        self.assertEqual(button.button_type, body.get("buttons")[0].get("button_type"))
        self.assertEqual(button.country_code, body.get("buttons")[0].get("country_code"))
        self.assertEqual(button.text, body.get("buttons")[0].get("text"))
        self.assertEqual(button.phone_number, body.get("buttons")[0].get("phone_number"))
