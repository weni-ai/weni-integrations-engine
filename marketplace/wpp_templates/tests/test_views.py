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
from marketplace.wpp_templates.models import (
    PARAMETER_FORMAT_NAMED,
    PARAMETER_FORMAT_POSITIONAL,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.views import TemplateMessageViewSet
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.accounts.permissions import ProjectManagePermission
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
            "language": "pt_br",
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

    def test_partial_update_named_body_rederives_params_in_place(self):
        self.translation.parameter_format = PARAMETER_FORMAT_NAMED
        self.translation.body = "Olá {{nome}}, sua cota {{cota}}"
        self.translation.body_named_params = [
            {"param_name": "nome", "example": "João"},
            {"param_name": "cota", "example": "3/12"},
        ]
        self.translation.variable_count = 2
        self.translation.parameter_anomaly = {
            "type": "BODY_EXAMPLE_NAME_MISMATCH",
            "body_param_names": ["nome", "cota"],
            "example_param_names": ["nome", "quota"],
        }
        self.translation.save()

        body = {
            "message_template_id": "0123456789",
            "language": "pt_br",
            "body": {
                "type": "BODY",
                "text": "Olá {{cliente}}, pedido {{pedido}}",
            },
        }

        with patch.object(
            TemplateService,
            "update_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ) as mock_update:
            response = self.request.patch(
                self.url,
                body=body,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.translation.refresh_from_db()
        self.assertEqual(self.translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            self.translation.body_named_params,
            [
                {"param_name": "cliente", "example": None},
                {"param_name": "pedido", "example": None},
            ],
        )
        self.assertEqual(self.translation.variable_count, 2)
        self.assertIsNone(self.translation.parameter_anomaly)
        self.assertNotIn("parameter_format", mock_update.call_args.kwargs)

    def test_partial_update_positional_body_is_unchanged(self):
        self.translation.parameter_format = PARAMETER_FORMAT_POSITIONAL
        self.translation.body = "Olá {{1}}, seu pedido {{2}} foi enviado."
        self.translation.body_named_params = []
        self.translation.variable_count = 0
        self.translation.parameter_anomaly = None
        self.translation.save()

        body = {
            "message_template_id": "0123456789",
            "language": "pt_br",
            "body": {
                "type": "BODY",
                "text": "Olá {{1}}, seu pedido {{2}} saiu para entrega.",
            },
        }

        with patch.object(
            TemplateService,
            "update_template_message",
            return_value={"id": "0123456789", "status": "PENDING"},
        ) as mock_update:
            response = self.request.patch(
                self.url,
                body=body,
                app_uuid=str(self.app.uuid),
                uuid=str(self.template_message.uuid),
                headers=self.headers,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.translation.refresh_from_db()
        self.assertEqual(self.translation.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(self.translation.body_named_params, [])
        self.assertEqual(self.translation.variable_count, 0)
        self.assertIsNone(self.translation.parameter_anomaly)
        self.assertEqual(
            self.translation.body, "Olá {{1}}, seu pedido {{2}} saiu para entrega."
        )
        self.assertNotIn("parameter_format", mock_update.call_args.kwargs)


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
        response = self.request.get(self.url, {"template_id": "test_template_id"})
        self.assertEqual(response.data[0], "Missing required parameter: project_uuid")
        self.assertEqual(response.status_code, 400)

    def test_whatsapp_template_details_missing_template_id(self):
        response = self.request.get(self.url, {"project_uuid": "test_project_uuid"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data[0], "Missing required parameter: template_id")


class WhatsappTemplateSyncTestCase(APIBaseTestCase):
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
        self.url = reverse("app-template-sync", kwargs={"app_uuid": str(self.app.uuid)})
        self.body = {"project_uuid": str(self.app.project_uuid)}

    @property
    def view(self):
        return self.view_class.as_view({"get": "sync", "post": "sync"})

    def test_get_sync_status_without_previous_sync(self):
        response = self.request.get(self.url, app_uuid=str(self.app.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json["last_synced_at"])

    @patch("marketplace.wpp_templates.views.TemplateSyncUseCase.request_sync")
    def test_post_sync_templates_successfully(self, mock_request_sync):
        last_synced_at = "2026-08-20T15:00:00+00:00"
        mock_request_sync.return_value = {"last_synced_at": last_synced_at}

        response = self.request.post(
            self.url, app_uuid=str(self.app.uuid), body=self.body
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["last_synced_at"], last_synced_at)

    def test_post_sync_templates_within_cooldown(self):
        self.app.config["templates_last_synced_at"] = datetime.now(pytz.UTC).isoformat()
        self.app.save(update_fields=["config"])

        response = self.request.post(
            self.url, app_uuid=str(self.app.uuid), body=self.body
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("retry_after_seconds", response.json)

    def test_post_sync_templates_ignored_meta_sync(self):
        self.app.config["ignores_meta_sync"] = {"code": 100}
        self.app.save(update_fields=["config"])

        response = self.request.post(
            self.url, app_uuid=str(self.app.uuid), body=self.body
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


NAMED_BODY = "Olá {{nome}}, sua cota {{cota}}"
NAMED_PARAMS = [
    {"param_name": "nome", "example": "João"},
    {"param_name": "cota", "example": "3/12"},
]
POSITIONAL_BODY = "Olá {{1}}, seu pedido {{2}} foi enviado."
POSITIONAL_FORMAT_NAMED_BODY_ANOMALY = {
    "type": "POSITIONAL_FORMAT_NAMED_BODY",
    "body_param_names": ["nome"],
}
BODY_EXAMPLE_NAME_MISMATCH_ANOMALY = {
    "type": "BODY_EXAMPLE_NAME_MISMATCH",
    "body_param_names": ["nome", "cota"],
    "example_param_names": ["nome", "quota"],
}


class TemplateReadSurfaceTestCase(APIBaseTestCase):
    view_class = TemplateMessageViewSet

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            config=dict(wa_waba_id="432321321"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=self.user,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.list_url = reverse(
            "app-template-list", kwargs={"app_uuid": str(self.app.uuid)}
        )

        self.named_clean = self._create_template(
            "cota_aviso",
            body=NAMED_BODY,
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=NAMED_PARAMS,
            variable_count=2,
        )
        self.named_zero = self._create_template(
            "named_empty",
            body="Olá, tudo bem?",
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=[],
            variable_count=0,
        )
        self.named_anomalous = self._create_template(
            "named_mismatch",
            body=NAMED_BODY,
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=[
                {"param_name": "nome", "example": "João"},
                {"param_name": "cota", "example": None},
            ],
            variable_count=2,
            parameter_anomaly=BODY_EXAMPLE_NAME_MISMATCH_ANOMALY,
        )
        self.positional = self._create_template(
            "pedido_enviado",
            body=POSITIONAL_BODY,
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
            body_named_params=[],
            variable_count=0,
            body_example=["João", "12345"],
        )
        self.positional_named_body = self._create_template(
            "positional_named_body",
            body="Olá {{nome}}",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
            body_named_params=[],
            variable_count=0,
            parameter_anomaly=POSITIONAL_FORMAT_NAMED_BODY_ANOMALY,
        )
        self.not_yet_known = self._create_template(
            "library_pending",
            body="",
            parameter_format=None,
            body_named_params=[],
            variable_count=0,
        )
        self.legacy = self._create_template(
            "legacy_row",
            body=NAMED_BODY,
            parameter_format=None,
            body_named_params=[],
            variable_count=0,
        )
        self.mixed = TemplateMessage.objects.create(
            name="mixed_langs",
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )
        self._create_translation(
            self.mixed,
            language="pt_BR",
            body=NAMED_BODY,
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=NAMED_PARAMS,
            variable_count=2,
        )
        self._create_translation(
            self.mixed,
            language="en_US",
            body=POSITIONAL_BODY,
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
            body_named_params=[],
            variable_count=0,
        )
        self.named_with_null_sibling = TemplateMessage.objects.create(
            name="named_plus_unknown",
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )
        self._create_translation(
            self.named_with_null_sibling,
            language="pt_BR",
            body=NAMED_BODY,
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=NAMED_PARAMS,
            variable_count=2,
        )
        self._create_translation(
            self.named_with_null_sibling,
            language="es",
            body="",
            parameter_format=None,
            body_named_params=[],
            variable_count=0,
        )
        self.no_translations = TemplateMessage.objects.create(
            name="no_translations",
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_LIST)

    def _create_template(self, name, **translation_kwargs):
        template = TemplateMessage.objects.create(
            name=name,
            app=self.app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )
        self._create_translation(template, **translation_kwargs)
        return template

    def _create_translation(self, template, **kwargs):
        defaults = dict(
            status="APPROVED",
            language="pt_BR",
            country="Brasil",
            body="",
            body_example=[],
            variable_count=0,
            body_named_params=[],
            parameter_anomaly=None,
        )
        defaults.update(kwargs)
        return TemplateTranslation.objects.create(template=template, **defaults)

    def _detail_url(self, template):
        return reverse(
            "app-template-detail",
            kwargs={"app_uuid": str(self.app.uuid), "uuid": str(template.uuid)},
        )

    def _list_payload(self):
        self.request.set_view(self.view_class.as_view(APIBaseTestCase.ACTION_LIST))
        response = self.request.get(
            self.list_url, {"page_size": 100}, app_uuid=str(self.app.uuid)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_no_positional_keys(response.json)
        return response.json

    def _detail_payload(self, template):
        self.request.set_view(self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE))
        response = self.request.get(
            self._detail_url(template),
            app_uuid=str(self.app.uuid),
            uuid=str(template.uuid),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_no_positional_keys(response.json)
        return response.json

    def _list_item(self, name):
        results = self._list_payload()["results"]
        matches = [item for item in results if item["name"] == name]
        self.assertEqual(len(matches), 1, msg=f"expected one list item named {name}")
        return matches[0]

    def assert_no_positional_keys(self, node):
        forbidden = {"index", "position", "slot", "order"}
        if isinstance(node, dict):
            self.assertEqual(forbidden & set(node), set())
            for value in node.values():
                self.assert_no_positional_keys(value)
        elif isinstance(node, list):
            for item in node:
                self.assert_no_positional_keys(item)

    def _assert_translation_shape(
        self,
        translation,
        parameter_format,
        parameter_names,
        variable_count,
        has_parameter_anomaly,
    ):
        self.assertEqual(translation["parameter_format"], parameter_format)
        self.assertEqual(translation["parameter_names"], parameter_names)
        self.assertIsInstance(translation["parameter_names"], list)
        for name in translation["parameter_names"]:
            self.assertIsInstance(name, str)
        self.assertEqual(translation["variable_count"], variable_count)
        self.assertEqual(translation["has_parameter_anomaly"], has_parameter_anomaly)
        self.assertIsInstance(translation["has_parameter_anomaly"], bool)
        self.assertNotIn("parameter_anomaly", translation)
        self.assertNotIn("body_named_params", translation)
        self.assertIn("variable_count", translation)
        self.assertIn("body_example", translation)

    def _assert_template_on_list_and_detail(self, template, expected_format, assert_fn):
        list_item = self._list_item(template.name)
        detail = self._detail_payload(template)
        self.assertEqual(list_item["parameter_format"], expected_format)
        self.assertEqual(detail["parameter_format"], expected_format)
        assert_fn(list_item)
        assert_fn(detail)

    def test_independent_test_named_and_positional_list_and_detail(self):
        def assert_named(payload):
            self.assertEqual(len(payload["translations"]), 1)
            self._assert_translation_shape(
                payload["translations"][0],
                parameter_format=PARAMETER_FORMAT_NAMED,
                parameter_names=["nome", "cota"],
                variable_count=2,
                has_parameter_anomaly=False,
            )

        def assert_positional(payload):
            self.assertEqual(len(payload["translations"]), 1)
            translation = payload["translations"][0]
            self._assert_translation_shape(
                translation,
                parameter_format=PARAMETER_FORMAT_POSITIONAL,
                parameter_names=[],
                variable_count=0,
                has_parameter_anomaly=False,
            )
            self.assertEqual(translation["body_example"], ["João", "12345"])

        self._assert_template_on_list_and_detail(
            self.named_clean, PARAMETER_FORMAT_NAMED, assert_named
        )
        self._assert_template_on_list_and_detail(
            self.positional, PARAMETER_FORMAT_POSITIONAL, assert_positional
        )

    def test_named_zero_placeholders(self):
        def assert_shape(payload):
            self._assert_translation_shape(
                payload["translations"][0],
                parameter_format=PARAMETER_FORMAT_NAMED,
                parameter_names=[],
                variable_count=0,
                has_parameter_anomaly=False,
            )

        self._assert_template_on_list_and_detail(
            self.named_zero, PARAMETER_FORMAT_NAMED, assert_shape
        )

    def test_named_anomalous_publishes_boolean_not_evidence(self):
        def assert_shape(payload):
            translation = payload["translations"][0]
            self._assert_translation_shape(
                translation,
                parameter_format=PARAMETER_FORMAT_NAMED,
                parameter_names=["nome", "cota"],
                variable_count=2,
                has_parameter_anomaly=True,
            )
            self.assertNotIn("João", str(translation.get("parameter_names")))

        self._assert_template_on_list_and_detail(
            self.named_anomalous, PARAMETER_FORMAT_NAMED, assert_shape
        )

    def test_positional_with_named_body(self):
        def assert_shape(payload):
            self._assert_translation_shape(
                payload["translations"][0],
                parameter_format=PARAMETER_FORMAT_POSITIONAL,
                parameter_names=[],
                variable_count=0,
                has_parameter_anomaly=True,
            )

        self._assert_template_on_list_and_detail(
            self.positional_named_body, PARAMETER_FORMAT_POSITIONAL, assert_shape
        )

    def test_not_yet_known_and_legacy_rows(self):
        def assert_unknown(payload):
            self._assert_translation_shape(
                payload["translations"][0],
                parameter_format=None,
                parameter_names=[],
                variable_count=0,
                has_parameter_anomaly=False,
            )

        self._assert_template_on_list_and_detail(
            self.not_yet_known, None, assert_unknown
        )
        self._assert_template_on_list_and_detail(self.legacy, None, assert_unknown)

    def test_mixed_template_level_keeps_per_translation_values(self):
        def assert_shape(payload):
            by_language = {item["language"]: item for item in payload["translations"]}
            self._assert_translation_shape(
                by_language["pt_BR"],
                parameter_format=PARAMETER_FORMAT_NAMED,
                parameter_names=["nome", "cota"],
                variable_count=2,
                has_parameter_anomaly=False,
            )
            self._assert_translation_shape(
                by_language["en_US"],
                parameter_format=PARAMETER_FORMAT_POSITIONAL,
                parameter_names=[],
                variable_count=0,
                has_parameter_anomaly=False,
            )

        self._assert_template_on_list_and_detail(self.mixed, "MIXED", assert_shape)

    def test_null_translation_does_not_force_mixed(self):
        def assert_shape(payload):
            by_language = {item["language"]: item for item in payload["translations"]}
            self.assertEqual(
                by_language["pt_BR"]["parameter_format"], PARAMETER_FORMAT_NAMED
            )
            self.assertIsNone(by_language["es"]["parameter_format"])

        self._assert_template_on_list_and_detail(
            self.named_with_null_sibling, PARAMETER_FORMAT_NAMED, assert_shape
        )

    def test_template_with_no_translations_reads_null_format(self):
        def assert_shape(payload):
            self.assertEqual(payload["translations"], [])

        self._assert_template_on_list_and_detail(
            self.no_translations, None, assert_shape
        )

    def test_tenancy_filters_by_app_behind_project_manage_permission(self):
        other_app = App.objects.create(
            config=dict(wa_waba_id="999"),
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=self.user,
        )
        foreign = TemplateMessage.objects.create(
            name="foreign_template",
            app=other_app,
            category="UTILITY",
            created_on=datetime.now(pytz.UTC),
            template_type="TEXT",
            created_by=self.user,
        )
        self.assertEqual(
            TemplateMessageViewSet.permission_classes, [ProjectManagePermission]
        )
        names = {item["name"] for item in self._list_payload()["results"]}
        self.assertIn("cota_aviso", names)
        self.assertNotIn("foreign_template", names)

        self.request.set_view(self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE))
        response = self.request.get(
            reverse(
                "app-template-detail",
                kwargs={"app_uuid": str(self.app.uuid), "uuid": str(foreign.uuid)},
            ),
            app_uuid=str(self.app.uuid),
            uuid=str(foreign.uuid),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
