"""Tests for the wpp_templates module"""

import uuid

import textwrap
import pytz

from datetime import datetime

from rest_framework import status
from rest_framework.test import APIClient

from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.urls import reverse

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import PhotoAPIService, TemplateService
from marketplace.wpp_templates.models import TemplateMessage, TemplateTranslation
from marketplace.wpp_templates.views import TemplateMessageViewSet
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.wpp_templates.usecases import TemplateDetailUseCase


User = get_user_model()


class WhatsappTemplateCreateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_on=datetime.now(pytz.UTC),
            created_by=self.user,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.body = dict(
            name="teste",
            category="ACCOUNT_UPDATE",
            text_preview="Preview Test",
            project_uuid=str(self.app.project_uuid),
        )
        self.url = reverse("app-template-list", kwargs={"app_uuid": str(self.app.uuid)})

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


# TODO: Replace decorator path with service class instance
class WhatsappTemplateDestroyTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            config={"waba": {"id": "432321321"}, "fb_access_token": "token"},
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp",
            created_by=self.user,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
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

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_wpp_template_message_successfully(
        self, mock_delete_template_message
    ):
        mock_delete_template_message.return_value = None

        response = self.request.delete(
            self.url, app_uuid=str(self.app.uuid), uuid=str(self.template_message.uuid)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            TemplateMessage.objects.filter(uuid=self.template_message.uuid).exists()
        )

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_template_message_missing_waba(self, mock_delete_template_message):
        self.app.config.pop("waba")
        self.app.save()

        with self.assertRaises(ValidationError):
            self.request.delete(
                self.url,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
            )

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_template_message_missing_fb_access_token(
        self, mock_delete_template_message
    ):
        self.app.config.pop("fb_access_token")
        self.app.save()

        with self.assertRaises(ValidationError):
            self.request.delete(
                self.url,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
            )

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_template_message_wpp_cloud(self, mock_delete_template_message):
        self.app.code = "wpp-cloud"
        self.app.config = {"wa_waba_id": "wa_waba_id_value"}
        self.app.save()

        response = self.request.delete(
            self.url,
            app_uuid=str(self.app.uuid),
            uuid=str(self.template_message.uuid),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            TemplateMessage.objects.filter(uuid=self.template_message.uuid).exists()
        )

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_template_message_missing_waba_id(
        self, mock_delete_template_message
    ):
        self.app.config["waba"]["id"] = None
        self.app.save()

        with self.assertRaises(ValidationError):
            self.request.delete(
                self.url,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
            )

    @patch(
        "marketplace.services.facebook.service.TemplateService.delete_template_message"
    )
    def test_destroy_template_message_missing_wpp_cloud_waba_id(
        self, mock_delete_template_message
    ):
        self.app.code = "wpp-cloud"
        self.app.config.pop("wa_waba_id", None)
        self.app.save()

        with self.assertRaises(ValidationError):
            self.request.delete(
                self.url,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
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


class TemplateMessageViewSetTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        self.client = APIClient()
        self.app = App.objects.create(
            config=dict(),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=User.objects.get_admin_user(),
        )

        self.template_message_1 = TemplateMessage.objects.create(
            name="Template 1",
            app=self.app,
            category="MARKETING",
            created_on=datetime.now(pytz.UTC),  # Ensuring timezone-aware datetime
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_message_2 = TemplateMessage.objects.create(
            name="Template 2",
            app=self.app,
            category="Category 2",
            created_on=datetime.now(pytz.UTC),  # Ensuring timezone-aware datetime
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
        self.template_message_3 = TemplateMessage.objects.create(
            name="Template 3",
            app=self.app,
            category="MARKETING",
            created_on=datetime.now(pytz.UTC),  # Ensuring timezone-aware datetime
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )

        super().setUp()

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_LIST)

    def test_filter_queryset_with_parameters(self):
        date = datetime.now(pytz.UTC)  # Ensuring timezone-aware datetime
        formatted_date = date.strftime("%-m-%-d-%Y")
        url = reverse("app-template-list", kwargs={"app_uuid": str(self.app.uuid)})
        params = {
            "name": "Template 1",
            "category": "MARKETING",
            "start": formatted_date,
            "end": formatted_date,
            "sort": "name",
        }
        response = self.request.get(url, params, app_uuid=str(self.app.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json
        self.assertEqual(len(data["results"]), 1)


class MockPhotoAPIRequests:
    def create_upload_session(self, file_length: int, file_type: str) -> str:
        return "mock_upload_session_id"

    def upload_session(
        self, upload_session_id: str, file_type: str, data: bytes
    ) -> dict:
        return {"h": "mock_upload_handle"}

    def get_url(self) -> str:
        return "http://mock.url"


class MockTemplateService:
    def create_template_message(self, *args, **kwargs):
        return {"id": "0123456789", "status": "PENDING"}

    def get_url(self) -> str:
        return "http://mock.url"


# TODO: Replace decorator path with service class instance
class WhatsappTemplateTranslationsTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            config=dict(wa_waba_id="109552365187427"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=self.user,
        )

        self.template_message = TemplateMessage.objects.create(
            name="teste",
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.url = reverse(
            "app-template-translations",
            kwargs={"app_uuid": self.app.uuid, "uuid": self.template_message.uuid},
        )

        self.body = dict(
            project_uuid=str(self.app.project_uuid),
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

        self.mock_facebook_client = Mock(spec=FacebookClient)
        self.mock_template_service = MockTemplateService()
        self.mock_photo_api_requests = MockPhotoAPIRequests()

        with patch(
            "marketplace.clients.facebook.client.FacebookClient",
            return_value=self.mock_facebook_client,
        ):
            with patch.object(
                FacebookClient,
                "get_url",
                return_value="mocked_url",
            ):
                self.template_service = TemplateService(
                    client=self.mock_facebook_client
                )
                self.photo_api_service = PhotoAPIService(
                    client=self.mock_photo_api_requests
                )

    @property
    def view(self):
        return self.view_class.as_view(dict(post="translations"))

    def test_create_template_translation(self):
        with patch.object(
            TemplateService,
            "create_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ):
            with patch.object(
                PhotoAPIService, "upload_session", return_value={"h": "upload_handle"}
            ):
                with patch.object(
                    PhotoAPIService, "create_upload_session", return_value="0123456789"
                ):
                    response = self.request.post(
                        self.url, body=self.body, uuid=str(self.template_message.uuid)
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertTrue(
                        TemplateTranslation.objects.filter(
                            template=self.template_message
                        ).exists()
                    )

    def test_create_template_translation_error(self):
        with patch.object(
            TemplateService,
            "create_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ):
            with patch.object(
                PhotoAPIService,
                "upload_session",
                side_effect=Exception("Upload session failed"),
            ):
                with patch.object(
                    PhotoAPIService,
                    "create_upload_session",
                    side_effect=Exception("Create upload session failed"),
                ):
                    with self.assertRaises(Exception):
                        self.request.post(
                            self.url,
                            body=self.body,
                            uuid=str(self.template_message.uuid),
                        )

    def test_wpp_template_translation_without_token(self):
        self.app.code = "wpp"
        self.app.config = {"waba": {"id": "432321321"}}
        self.app.save()

        with self.assertRaises(ValueError):
            self.request.post(
                self.url, body=self.body, uuid=str(self.template_message.uuid)
            )

        self.app.config = {"waba": {"id": "432321321"}, "fb_access_token": "token"}
        self.app.code = "wpp-cloud"
        self.app.save()


# TODO: Replace decorator path with service class instance
class WhatsappTemplateUpdateTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

        self.validated_data = dict(
            language="pt_br",
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

        self.app = App.objects.create(
            config={"wa_waba_id": "432321321"},
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=self.user,
        )

        self.template_message = TemplateMessage.objects.create(
            name="teste",
            app=self.app,
            category="TRANSACTIONAL",
            created_on=datetime.now(pytz.UTC),  # Ensuring timezone-aware datetime
            template_type="TEXT",
            created_by=self.user,
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
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.headers = {"Project-Uuid": str(self.app.project_uuid)}
        self.body = {
            "message_template_id": "0123456789",
            "header": {
                "header_type": "VIDEO",
                "example": "data:application/pdf;base64,test==",
            },
            "body": {"type": "BODY", "text": "txt body"},
            "footer": {"type": "FOOTER", "text": "txt footer"},
            "buttons": [
                {
                    "button_type": "URL",
                    "text": "phone-button-text",
                    "url": "https://weni.ai",
                    "phone_number": "84999999999",
                    "country_code": "+55",
                }
            ],
        }

        self.url = reverse(
            "app-template-detail",
            kwargs={
                "app_uuid": str(self.app.uuid),
                "uuid": str(self.template_message.uuid),
            },
        )

        self.mock_facebook_client = Mock(spec=FacebookClient)
        self.mock_template_service = MockTemplateService()
        self.mock_photo_api_requests = MockPhotoAPIRequests()

        with patch(
            "marketplace.clients.facebook.client.FacebookClient",
            return_value=self.mock_facebook_client,
        ):
            with patch.object(
                FacebookClient,
                "get_url",
                return_value="mocked_url",
            ):
                self.template_service = TemplateService(
                    client=self.mock_facebook_client
                )
                self.photo_api_service = PhotoAPIService(
                    client=self.mock_photo_api_requests
                )

    @property
    def view(self):
        return self.view_class.as_view({"patch": "partial_update"})

    def test_partial_update_template(self):
        with patch.object(
            TemplateService,
            "update_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ):
            with patch.object(
                PhotoAPIService, "upload_session", return_value={"h": "upload_handle"}
            ):
                with patch.object(
                    PhotoAPIService, "create_upload_session", return_value="0123456789"
                ):
                    response = self.request.patch(
                        self.url,
                        body=self.body,
                        app_uuid=str(self.app.uuid),
                        uuid=str(self.template_message.uuid),
                        headers=self.headers,
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertTrue(
                        TemplateTranslation.objects.filter(
                            template=self.template_message
                        ).exists()
                    )

    def test_partial_update_without_token(self):
        self.app.code = "wpp"
        self.app.config = {"waba": {"id": "432321321"}}
        self.app.save()

        with self.assertRaises(ValidationError):
            self.request.patch(
                self.url,
                body=self.body,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
                headers=self.headers,
            )

        self.app.config = {"waba": {"id": "432321321"}, "fb_access_token": "token"}
        self.app.code = "wpp-cloud"
        self.app.save()

    def test_partial_update_template_error(self):
        with patch.object(
            TemplateService,
            "update_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ):
            with patch.object(
                PhotoAPIService,
                "upload_session",
                side_effect=Exception("Upload session failed"),
            ):
                with patch.object(
                    PhotoAPIService, "create_upload_session", return_value="0123456789"
                ):
                    with self.assertRaises(Exception):
                        self.request.patch(
                            self.url,
                            body=self.body,
                            app_uuid=str(self.app.uuid),
                            uuid=str(self.template_message.uuid),
                            headers=self.headers,
                        )


class WhatsappTemplateDetailsTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            configured=True,
            created_by=self.user,
        )

        self.template_message = TemplateMessage.objects.create(
            name="test_template",
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )

        self.template_translation = TemplateTranslation.objects.create(
            template=self.template_message,
            status="APPROVED",
            body="Test body",
            language="en_US",
            country="US",
            variable_count=0,
            message_template_id="test_template_id",
        )

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.url = reverse("app-template-details")

    @property
    def view(self):
        return self.view_class.as_view({"get": "template_detail"})

    @patch(
        "marketplace.wpp_templates.usecases.TemplateDetailUseCase.get_whatsapp_cloud_data_from_integrations"
    )
    def test_whatsapp_template_details_endpoint_success(self, mock_get_data):
        mock_dto = TemplateDetailUseCase.WhatsappCloudDTO(
            app_uuid=str(self.app.uuid),
            templates_uuid=[str(self.template_message.uuid)],
        )
        mock_get_data.return_value = [mock_dto]

        response = self.request.get(
            self.url,
            {
                "project_uuid": str(self.app.project_uuid),
                "template_id": "test_template_id",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["app_uuid"], str(self.app.uuid))
        self.assertEqual(
            response.data[0]["templates_uuid"], [str(self.template_message.uuid)]
        )

        mock_get_data.assert_called_once_with(
            project_uuid=str(self.app.project_uuid), template_id="test_template_id"
        )

    def test_whatsapp_template_details_missing_project_uuid(self):
        with self.assertRaises(ValidationError) as cm:
            self.request.get(self.url, {"template_id": "test_template_id"})

        self.assertEqual(
            cm.exception.message, "Missing required parameter: project_uuid"
        )

    def test_whatsapp_template_details_missing_template_id(self):
        with self.assertRaises(ValidationError) as cm:
            self.request.get(self.url, {"project_uuid": str(self.app.project_uuid)})

        self.assertEqual(
            cm.exception.message, "Missing required parameter: template_id"
        )
