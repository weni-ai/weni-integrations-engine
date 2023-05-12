import uuid

from unittest.mock import Mock, patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from marketplace.applications.models import AppTypeAsset

from ..type import GenericExternalAppType
from marketplace.core.types.externals.generic.views import (
    GenericExternalsViewSet,
    ExternalsAppTypes,
    DetailGenericExternals,
    ExternalsIcons,
    search_icon,
)

from typing import Any
from marketplace.interfaces.flows import FlowsInterface
from marketplace.interfaces.connect import ConnectInterface

apptype = GenericExternalAppType()


class MockFlowsClient(FlowsInterface):
    def __init__(self):
        self.base_url = "test"
        self.authentication_instance = object

    def list_external_types(self, flows_type_code=None) -> Any:
        if flows_type_code:
            return {
                "attributes": {"name": "Omie", "slug": "omie"},
                "form": [
                    {
                        "name": "name",
                        "type": "text",
                        "help_text": "Name",
                        "label": "Name",
                    },
                    {
                        "name": "app_key",
                        "type": "text",
                        "help_text": "Omie App Key",
                        "label": "Omie App Key",
                    },
                    {
                        "name": "app_secret",
                        "type": "text",
                        "help_text": "Omie App Secret",
                        "label": "Omie App Secret",
                    },
                ],
            }
        else:
            return {
                "external_types": {
                    "omie": {"attributes": {"name": "Omie", "slug": "omie"}}
                }
            }

    def release_external_service(self, uuid: str, user_email: str) -> Any:
        response = Mock()
        response.status_code = 200
        return response


class MockConnectClient(ConnectInterface):
    base_url = "connect test"
    use_connect_v2 = "test"

    def create_external_service(
        self, user: str, project_uuid: str, type_fields: dict, type_code: str
    ):
        response = Mock()
        response.status_code = 201
        response.json.return_value = {
            "uuid": str(uuid.uuid4()),
            "external_service_type": "omie",
            "name": "Omie test",
            "config": {"app_key": "123456789", "app_secret": "987654321"},
        }
        return response


class PatchedFlowsClientTestCase(APIBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.patch_flows_client = patch(
            "marketplace.core.types.externals.generic.views.FlowsClient",
            MockFlowsClient,
        )
        cls.patch_connect_client = patch(
            "marketplace.core.types.externals.generic.serializers.ConnectProjectClient",
            MockConnectClient,
        )
        cls.patch_flows_client.start()
        cls.patch_connect_client.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_flows_client.stop()
        cls.patch_connect_client.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()


class CreateOmieAppTestCase(PatchedFlowsClientTestCase):
    url = reverse("generic-external-app-list")
    view_class = GenericExternalsViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    @patch("marketplace.core.types.externals.generic.views.search_icon")
    def test_create_app(self, mock_search_icon):
        mock_search_icon.return_value = "https://url.test.com.br/icon.jpg"
        external_code = "omie"
        self.body["external_code"] = external_code
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_flows_type_code(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveGenericExternalsAppTestCase(APIBaseTestCase):
    view_class = GenericExternalsViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="generic-external",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse(
            "generic-external-app-detail", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_retrieve_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid, code="generic")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid, code="generic")
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class ConfigureGenericAppTestCase(PatchedFlowsClientTestCase):
    view_class = GenericExternalsViewSet

    def setUp(self):
        super().setUp()

        data = {
            "flows_type_code": "omie",
            "name": "Omie",
            "external_icon_url": "/media/omie.png",
        }

        self.app = App.objects.create(
            code="generic-external",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=data,
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse(
            "generic-external-app-configure", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view({"patch": "configure"})

    def test_configure_channel_success(self):
        keys_values = {
            "flows_type_code": "omie",
            "name": "Omie",
            "external_icon_url": "/media/omie.png",
        }
        payload = {
            "user": str(self.user),
            "project_uuid": str(uuid.uuid4()),
            "config": keys_values,
        }
        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_configure_channel_without_config(self):
        """Request without config field"""
        response_data = {"config": ["This field is required."]}

        payload = {
            "user": str(self.user),
            "project_uuid": str(uuid.uuid4()),
        }
        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response_data, response.json)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DeleteGenericExternalsAppTestCase(PatchedFlowsClientTestCase):
    view_class = GenericExternalsViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse(
            "generic-external-app-detail", kwargs={"uuid": self.app.uuid}
        )

    def test_delete_app_plataform(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())

    def test_delete_app_with_wrong_project_uuid(self):
        response = self.request.delete(self.url, uuid=str(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_app_without_autorization(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_release_external_service(self):
        self.app.config = {"channelUuid": str(uuid.uuid4())}
        self.app.save()

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())


class DetailExternalAppTypesTestCase(PatchedFlowsClientTestCase):
    view_class = DetailGenericExternals

    def setUp(self):
        super().setUp()
        self.url = reverse(
            "externals-detail-detail", kwargs={"flows_type_code": "omie"}
        )

    @property
    def view(self):
        return self.view_class.as_view({"get": "retrieve"})

    def test_retrieve_success(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ExternalsIconsTestCase(PatchedFlowsClientTestCase):
    view_class = ExternalsIcons

    def setUp(self):
        super().setUp()
        self.url = reverse("externals-icons-list")

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    @patch("marketplace.core.types.externals.generic.views.search_icon")
    def test_get_icons_success(self, mock_search_icon):
        response_data = {
            "external_types": {
                "omie": "http://example.com/icon.png",
            }
        }
        mock_search_icon.return_value = "http://example.com/icon.png"
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, response_data["external_types"])


class ExternalsAppTypesTestCase(PatchedFlowsClientTestCase):
    view_class = ExternalsAppTypes

    def setUp(self):
        super().setUp()
        self.url = reverse("externals-types-list")

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    def test_list_genericapptypes_success(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SearchIconTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.flows_type_code = "omie"
        self.icon_url = "example.com/icon.png"
        self.path = "/media/"
        user = get_user_model()
        self.user = user.objects.create_superuser(email="user@marketplace.ai")
        self.apptype_asset = AppTypeAsset.objects.create(
            code=self.flows_type_code.lower(),
            attachment=self.icon_url,
            created_by=self.user,
        )
        self.generic_apptype_asset = AppTypeAsset.objects.create(
            code="generic-external", attachment=self.icon_url, created_by=self.user
        )

    def test_search_icon_with_existing_code(self):
        result = search_icon(self.flows_type_code)
        self.assertEqual(result, f"{self.path}{self.icon_url}")

    def test_search_icon_with_non_existing_code(self):
        non_existing_code = "non_existing_code"
        result = search_icon(non_existing_code)
        generic_apptype_asset = AppTypeAsset.objects.filter(
            code="generic-external"
        ).first()
        expected_url = (
            generic_apptype_asset.attachment.url if generic_apptype_asset else None
        )
        self.assertEqual(result, expected_url)

    def test_search_icon_with_generic_code(self):
        generic_code = "generic-external"
        result = search_icon(generic_code)
        generic_apptype_asset = AppTypeAsset.objects.filter(
            code="generic-external"
        ).first()
        expected_url = (
            generic_apptype_asset.attachment.url if generic_apptype_asset else None
        )
        self.assertEqual(result, expected_url)

    def test_search_icon_with_invalid_code_and_missing_generic_asset(self):
        AppTypeAsset.objects.all().delete()
        invalid_code = "invalid_code"
        icon_url = search_icon(invalid_code)
        self.assertIsNone(icon_url)
        # Recreates the apptype_asset objects
        self.apptype_asset = AppTypeAsset.objects.create(
            code=self.flows_type_code.lower(),
            attachment=self.icon_url,
            created_by=self.user,
        )
        self.generic_apptype_asset = AppTypeAsset.objects.create(
            code="external-external", attachment=self.icon_url, created_by=self.user
        )
