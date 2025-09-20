import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin
from ..views import WhatsAppDemoViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types import APPTYPES


class CeleryResponse:
    def __init__(self, response):
        self.result = response

    def wait(self):
        ...


class CreateWhatsAppDemoAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    url = reverse("wpp-demo-app-list")
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()
        self.project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": self.project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

        # Patch for FlowsService.create_wac_channel
        self.create_wac_channel_patcher = patch(
            "marketplace.services.flows.service.FlowsService.create_wac_channel"
        )
        self.mock_create_wac_channel = self.create_wac_channel_patcher.start()

        # Patch for FlowsService.update_config
        self.update_config_patcher = patch(
            "marketplace.services.flows.service.FlowsService.update_config"
        )
        self.mock_update_config = self.update_config_patcher.start()

        # Patch for WPPRouterChannelClient.get_channel_token
        self.get_channel_token_patcher = patch(
            "marketplace.clients.router.client.WPPRouterChannelClient.get_channel_token"
        )
        self.mock_get_channel_token = self.get_channel_token_patcher.start()

        # Add cleanup for all patches
        self.addCleanup(self.create_wac_channel_patcher.stop)
        self.addCleanup(self.update_config_patcher.stop)
        self.addCleanup(self.get_channel_token_patcher.stop)

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_request_ok(self):
        channel_uuid = str(uuid.uuid4())

        self.mock_create_wac_channel.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]
        self.mock_get_channel_token.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        app = App.objects.get(uuid=response.json.get("uuid"))
        self.assertEqual(str(app.uuid), response.json["uuid"])
        self.assertEqual(app.config["title"], "WhatsApp: +559999998888")
        self.assertEqual(
            app.config["router_token"],
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te",
        )
        self.assertEqual(
            app.config["redirect_url"],
            "https://wa.me/+559999998888?text=WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te",
        )

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        self.mock_create_wac_channel.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]
        self.mock_get_channel_token.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_get_app_with_respective_project_uuid(self):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        self.mock_create_wac_channel.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]
        self.mock_get_channel_token.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        self.request.post(self.url, self.body)
        App.objects.get(project_uuid=self.body.get("project_uuid"))

    def test_create_app_without_permission(self):
        """Should return 403 if only project authorization is missing"""
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_with_internal_permission_only(self):
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        self.mock_create_wac_channel.return_value = dict(
            name="WhatsApp: +559999998888", uuid=str(uuid.uuid4())
        )
        self.mock_get_channel_token.return_value = (
            "WhatsApp:+559999998888-whatsapp-demo-token"
        )

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_permission_and_authorization(self):
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveWhatsAppDemoAppTestCase(APIBaseTestCase):
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-demo",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-demo-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class DestroyWhatsAppDemoAppTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-demo",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("wpp-demo-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def test_destroy_app_ok(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_with_authorization_contributor(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_with_authorization_viewer(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_not_setted(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_internal_permission_only(self):
        """Should allow deletion if the user only has internal permission"""
        self.user_authorization.delete()
        self.grant_permission(self.user, "can_communicate_internally")

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_without_permission_and_authorization(self):
        """Should return 403 if the user has neither internal permission nor project authorization"""
        self.user_authorization.delete()
        self.clear_permissions(self.user)

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class URLWhatsAppDemoAppTestCase(APIBaseTestCase):
    url = reverse("wpp-demo-app-url")
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()
        self.project_uuid = str(uuid.uuid4())

    @property
    def view(self):
        return self.view_class.as_view({"get": "url"})

    def test_blank_project_uuid_returns_400(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json.get("detail"), "“project“ is a required parameter"
        )

    def test_not_valid_uuid_returns_400(self):
        response = self.request.get(self.url + "?project=123")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json.get("detail"), "“123” is not a valid UUID.")

    def test_user_without_having_permission_returns_403(self):
        response = self.request.get(self.url + f"?project={uuid.uuid4()}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json.get("detail"),
            "You do not have permission to access this project",
        )

    def test_user_not_setted_permission_returns_403(self):
        self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_NOT_SETTED
        )
        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json.get("detail"),
            "You do not have permission to access this project",
        )

    def tests_app_does_not_exist_returns_404(self):
        self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json.get("detail"),
            "This project does not have an integrated WhatsApp Demo",
        )

    def test_request_ok(self):
        self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )

        redirect_url = "https://wa.me/1234?text=weni-demo-pi68n_q5A"
        apptype = APPTYPES.get("wpp-demo")
        apptype.create_app(
            project_uuid=self.project_uuid,
            created_by=self.user,
            config={"redirect_url": redirect_url},
        )

        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, dict(url=redirect_url))
