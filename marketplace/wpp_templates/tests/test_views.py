import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation, TemplateHeader
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.base import FakeRequestsResponse
from ..views import TemplateMessageViewSet
from unittest.mock import patch

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
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )

        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            variable_count=1,
            body="Teste",
        )

        TemplateHeader.objects.create(translation=self.template_translation, header_type="TEXT", text="teste")
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    def test_list_whatsapp_templates(self):
        response = self.request.get(self.url, app_uuid=str(self.app.uuid))
        self.assertEqual(response.json.get("results")[0].get("uuid"), str(self.template_message.uuid))
        self.assertEqual(
            response.json.get("results")[0].get("translations")[0].get("uuid"), str(self.template_translation.uuid)
        )


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
            name="teste",
            category="ACCOUNT_UPDATE",
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_whatsapp_templates(self):
        before_template_messages = TemplateMessage.objects.all().count()
        self.request.post(self.url, app_uuid=str(self.app.uuid), body=self.body)
        total_template_messages = TemplateMessage.objects.all().count()

        self.assertNotEqual(before_template_messages, total_template_messages)


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
            created_on=datetime.now(),
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
        mock.side_effect = [fake_response]

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
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
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
        response = self.request.get(self.url, app_uuid=self.app.uuid, uuid=self.template_message.uuid)
        self.assertEqual(response.json.get("uuid"), str(self.template_message.uuid))


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
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.url = reverse(
            "app-template-translations", kwargs={"app_uuid": self.app.uuid, "uuid": self.template_message.uuid}
        )

        self.body = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            header={"header_type": "VIDEO", "example": "data:application/pdf;base64,test=="},
            footer={"type": "FOOTER", "text": "Not interested? Tap Stop promotions"},
            buttons=[{"button_type": "URL", "text": "phone-button-text", "url": "https://weni.ai"}],
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(post="translations"))

    def test_create_whatsapp_translation(self):
        before_template_messages = TemplateTranslation.objects.all().count()
        self.request.post(self.url, body=self.body, uuid=str(self.template_message.uuid))
        total_template_messages = TemplateTranslation.objects.all().count()
        self.assertNotEqual(before_template_messages, total_template_messages)


class WhatsappTemplateUpdateTestCase(APIBaseTestCase):
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
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )

        self.body = dict(
            body={"text": "test2", "type": "BODY"},
            header={"header_type": "VIDEO", "example": "data:application/pdf;base64,test=="},
            footer={"type": "FOOTER", "text": "Not interested? Tap Stop promotions"},
            buttons=[{"button_type": "URL", "text": "phone-button-text", "url": "https://weni.ai"}],
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_UPDATE)

    @patch("requests.update")
    def test_update_whatsapp_template(self, mock):
        fake_response = FakeRequestsResponse(data={"success": True})
        fake_response.status_code = 200
        mock.side_effect = [fake_response]

        object = TemplateMessage.objects.get(uuid=self.template_message.uuid)
        response = self.request.put(self.url, app_uuid=self.app.uuid, uuid=self.template_message.uuid, body=self.body)


        self.assertNotEqual(object.name, response.name)