""" Tests for the wpp_templates module """
import uuid
import textwrap

from datetime import datetime

from rest_framework import status

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from marketplace.applications.models import App
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation
from marketplace.wpp_templates.views import TemplateMessageViewSet
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_base.exceptions import (
    FacebookApiException,
)

from unittest.mock import patch
from unittest.mock import MagicMock

User = get_user_model()


class WhatsappTemplateCreateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=User.objects.get_admin_user(),
        )
        self.body = dict(
            name="teste", category="ACCOUNT_UPDATE", text_preview="Preview Test"
        )
        self.url = reverse("app-template-list", kwargs={"app_uuid": str(self.app.uuid)})
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_whatsapp_template_with_valid_data(self):
        response = self.request.post(
            self.url, app_uuid=str(self.app.uuid), body=self.body
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", response.data)

    def test_create_whatsapp_template_with_invalid_name(self):
        message = _(
            """
                Invalid name format.
                The name must not contain spaces and must start with a lowercase letter
                followed by one or more uppercase or lowercase letters,
                digits, or underscores.
            """
        )
        error_message = textwrap.dedent(str(message))
        error_message = {"name": [error_message]}
        invalid_body = self.body.copy()
        invalid_body["name"] = "Test Invalid N4M3"

        response = self.request.post(
            self.url, app_uuid=str(self.app.uuid), body=invalid_body
        )

        self.assertEqual(error_message, response.json)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WhatsappTemplateDestroyTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=User.objects.get_admin_user(),
        )
        self.template_message = TemplateMessage.objects.create(
            name="teste",
            category="ACCOUNT_UPDATE",
            app=self.app,
        )
        self.url = reverse(
            "app-template-detail",
            kwargs={
                "app_uuid": str(self.app.uuid),
                "uuid": str(self.template_message.uuid),
            },
        )
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    @patch(
        "marketplace.wpp_templates.requests.TemplateMessageRequest.delete_template_message"
    )
    def test_destroy_template_message_successfully(self, mock_delete_template_message):
        mock_delete_template_message.return_value.status_code = status.HTTP_200_OK

        response = self.request.delete(
            self.url, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            TemplateMessage.objects.filter(uuid=self.template_message.uuid).exists()
        )

    @patch(
        "marketplace.wpp_templates.requests.TemplateMessageRequest.delete_template_message"
    )
    def test_destroy_template_message_with_subcode_error(
        self, mock_delete_template_message
    ):
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_response.json.return_value = {"error": {"error_subcode": 2388094}}
        mock_delete_template_message.return_value = mock_response

        response = self.request.delete(
            self.url, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"error": "WhatsApp.templates.error.delete_sample"}
        )
        self.assertTrue(
            TemplateMessage.objects.filter(uuid=self.template_message.uuid).exists()
        )

    @patch(
        "marketplace.wpp_templates.requests.TemplateMessageRequest.delete_template_message"
    )
    def test_destroy_template_message_requestapi_error(
        self, mock_delete_template_message
    ):
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_delete_template_message.return_value = mock_response

        response = self.request.delete(
            self.url, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            TemplateMessage.objects.filter(uuid=self.template_message.uuid).exists()
        )


class WhatsappTemplateTranslationsTestCase(APIBaseTestCase):
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
            category="UTILITY",
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.url = reverse(
            "app-template-translations",
            kwargs={"app_uuid": self.app.uuid, "uuid": self.template_message.uuid},
        )

        self.body = dict(
            language="ja",
            # message_template_id=None,
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            header={
                "header_type": "VIDEO",
                "example": "data:application/pdf;base64,test==",
            },
            footer={"type": "FOOTER", "text": "Not interested? Tap Stop promotions"},
            buttons=[
                {
                    "button_type": "URL",
                    "text": "phone-button-text",
                    "url": "https://weni.ai",
                    "phone_number": "84999999999",
                    "country_code": "+55",
                }
            ],
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(post="translations"))

    @patch("marketplace.wpp_templates.serializers.requests")
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.requests.PhotoAPIRequest.create_upload_session"
    )
    @patch(
        "marketplace.wpp_templates.requests.TemplateMessageRequest.create_template_message"
    )
    def test_create_template_translation(
        self, mock_create_template_message, mock_create_upload_session, mock_requests
    ):
        # create_template_message
        mock_create_template_message.return_value = {"some_key": "some_value", "id": "0123456789"}

        # create_upload_session
        mock_create_upload_session.return_value = MagicMock(
            create_upload_session=lambda x: "0123456789"
        )

        # request
        mock_post = mock_requests.post
        mock_post.return_value.status_code = status.HTTP_200_OK
        mock_post.return_value.json.return_value = {"h": "upload_handle"}

        response = self.request.post(
            self.url, body=self.body, uuid=str(self.template_message.uuid),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("marketplace.wpp_templates.serializers.requests")
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.requests.PhotoAPIRequest.create_upload_session"
    )
    def test_create_template_translation_error(
        self, mock_create_upload_session, mock_requests
    ):
        # create_upload_session
        mock_create_upload_session.return_value = MagicMock(
            create_upload_session=lambda x: "0123456789"
        )

        # request
        mock_post = mock_requests.post
        mock_post.return_value.status_code = status.HTTP_404_NOT_FOUND
        mock_post.return_value.json.return_value = {"error": "error"}

        with self.assertRaises(FacebookApiException):
            self.request.post(
                self.url, body=self.body, uuid=str(self.template_message.uuid)
            )


class WhatsappTemplateUpdateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.validated_data = dict(
            language="ja",
            body={"text": "test", "type": "BODY"},
            country="Brasil",
            header={
                "header_type": "VIDEO",
                "example": "data:application/pdf;base64,test==",
            },
            footer={"type": "FOOTER", "text": "Not interested? Tap Stop promotions"},
            buttons=[
                {
                    "button_type": "URL",
                    "text": "phone-button-text",
                    "url": "https://weni.ai",
                    "phone_number": "84999999999",
                    "country_code": "+55",
                }
            ],
        )
        self.body = {
                "message_template_id": "0123456789",
                "header": {
                    "header_type": "TEXT",
                    "text": "txt",
                    "example": "txt example"
                },
                "body": {
                    "type": "BODY",
                    "text": "txt body"
                },
                "footer": {
                    "type": "FOOTER",
                    "text": "txt footer"
                },
                "buttons": [{
                    "button_type": "URL",
                    "text": "phone-button-text",
                    "url": "https://weni.ai",
                    "phone_number": "84999999999",
                    "country_code": "+55",
                }]
        }

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

        self.translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="PENDING",
            body=self.validated_data.get("body", {}).get("text", ""),
            footer=self.validated_data.get("footer", {}).get("text", ""),
            language=self.validated_data.get("language"),
            country=self.validated_data.get("country", "Brasil"),
            variable_count=0,
            message_template_id="0123456789",
        )

        self.url = reverse(
            "app-template-detail",
            kwargs={
                "app_uuid": str(self.app.uuid),
                "uuid": str(self.template_message.uuid),
            },
        )
        print(self.app.uuid)
        print(self.url)
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view({"patch": "partial_update"})

    @patch(
        "marketplace.wpp_templates.requests.TemplateMessageRequest.update_template_message"
    )
    def test_update_template_translation(
        self, mock_update_template_message
    ):
        mock_update_template_message.return_value = {"success": True}

        response = self.request.patch(
            self.url, body=self.body, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
        )
        print('test', response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_template_translation_error(
        self
    ):

        with self.assertRaises(FacebookApiException):
            self.request.patch(
                self.url, body=self.body, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
            )


class WhatsappTemplateLanguagesTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.url = reverse(
            "app-template-languages",
            kwargs={"app_uuid": "8c2a8e9e-9833-4710-9df0-548bcfeaf596"},
        )
        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(dict(get="languages"))

    def test_list_whatsapp_template_languages(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, 200)
