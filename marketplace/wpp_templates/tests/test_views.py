import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse

from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.base import FakeRequestsResponse
from ..views import TemplateMessageViewSet

User = get_user_model()


class FakeFacebookResponse(FakeRequestsResponse):
    status_code = 200


class WhatsappTemplateListTestCase(APIBaseTestCase):
    url = reverse("templates-list")
    view_class = TemplateMessageViewSet

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
            template=self.template_message,
            status="APPROVED",
            language="pt_br",
            country="Brasil",
            variable_count=1,
            body="Teste",
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    def test_list_whatsapp_templates(self):
        response = self.request.get(self.url)

        self.assertEqual(response.json.get("results")[0].get("uuid"), str(self.template_message.uuid))
        self.assertEqual(
            response.json.get("results")[0].get("translations")[0].get("uuid"), str(self.template_translation.uuid)
        )


class WhatsappTemplateCreateTestCase(APIBaseTestCase):
    url = reverse("templates-list")
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.body = dict(
            waba_id="324234234432",
            name="teste",
            category="ACCOUNT_UPDATE",
            template_type="TEXT",
            namespace="teste-namespace",
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    @patch("requests.post")
    def test_create_whatsapp_templates(self, mock: MagicMock):
        mock.return_value = FakeFacebookResponse({"success": True})

        before_template_messages = TemplateMessage.objects.all()
        self.request.post(self.url, body=self.body)
        total_template_messages = TemplateMessage.objects.all()

        self.assertNotEqual(before_template_messages, total_template_messages)


class WhatsappTemplateDestroyTestCase(APIBaseTestCase):
    url = reverse("templates-list")
    view_class = TemplateMessageViewSet

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
            config=dict(waba_id="1312321321"),
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
        self.request.delete(self.url, uuid=self.template_message.uuid)
        total_users_after = TemplateMessage.objects.count()

        self.assertNotEqual(total_users_before, total_users_after)


class WhatsappTemplateRetrieveTestCase(APIBaseTestCase):
    url = reverse("templates-list")
    view_class = TemplateMessageViewSet

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

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    @property
    def query_parameter(self):
        return f"?uuid={self.template_message.uuid}"

    def test_retrieve_whatsapp_template(self):
        response = self.request.get(self.url + self.query_parameter, uuid=self.template_message.uuid)

        self.assertEqual(response.json.get("uuid"), str(self.template_message.uuid))


class WhatsappTemplateLanguagesTestCase(APIBaseTestCase):
    url = reverse("templates-languages")
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(get="languages"))

    def test_list_whatsapp_template_languages(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, 200)


class WhatsappTranslactionCreateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

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

        self.url = reverse("templates-translations", kwargs={"uuid": self.template_message.uuid})

        self.body = dict(translations=list(), template=str(self.template_message.uuid))

        self.body.get("translations").append(
            dict(
                status="APPROVED",
                language="pt_br",
                country="Brasil",
            )
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(post="translations"))

    def test_create_whatsapp_translaction(self):
        before_template_messages = TemplateTranslation.objects.all().count()
        self.request.post(self.url, body=self.body, uuid=str(self.template_message.uuid))
        total_template_messages = TemplateTranslation.objects.all().count()

        self.assertNotEqual(before_template_messages, total_template_messages)
