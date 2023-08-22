import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import WhatsAppDemoViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types import APPTYPES


class CeleryResponse:
    def __init__(self, response):
        self.result = response

    def wait(self):
        ...


class CreateWhatsAppDemoAppTestCase(APIBaseTestCase):
    url = reverse("wpp-demo-app-list")
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()
        project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    @patch("marketplace.connect.client.WPPRouterChannelClient.get_channel_token")
    @patch("marketplace.connect.client.ConnectProjectClient.create_channel")
    def test_request_ok(self, create_channel_request, get_channel_token_request):
        channel_uuid = str(uuid.uuid4())

        create_channel_request.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]

        get_channel_token_request.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = App.objects.get(uuid=response.json.get("uuid"))
        self.assertEqual(str(app.uuid), response.json["uuid"])
        self.assertEqual(app.config["title"], "WhatsApp: +559999998888")
        self.assertEqual(
            app.config["routerToken"], "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
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

    @patch("marketplace.connect.client.WPPRouterChannelClient.get_channel_token")
    @patch("marketplace.connect.client.ConnectProjectClient.create_channel")
    def test_create_app_platform(
        self, create_channel_request, get_channel_token_request
    ):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        create_channel_request.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]

        get_channel_token_request.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    @patch("marketplace.connect.client.WPPRouterChannelClient.get_channel_token")
    @patch("marketplace.connect.client.ConnectProjectClient.create_channel")
    def test_get_app_with_respective_project_uuid(
        self, create_channel_request, get_channel_token_request
    ):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        create_channel_request.side_effect = [
            dict(name="WhatsApp: +559999998888", uuid=channel_uuid)
        ]

        get_channel_token_request.side_effect = [
            "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"
        ]

        self.request.post(self.url, self.body)
        App.objects.get(project_uuid=self.body.get("project_uuid"))

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
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


class DestroyWhatsAppDemoAppTestCase(APIBaseTestCase):
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
        self.assertEqual(response.json.get("detail"), "“project“ is a required parameter")

    def test_not_valid_uuid_returns_400(self):
        response = self.request.get(self.url + "?project=123")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json.get("detail"), "“123” is not a valid UUID.")

    def test_user_without_having_permission_returns_403(self):
        response = self.request.get(self.url + f"?project={uuid.uuid4()}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json.get("detail"), "You do not have permission to access this project")

    def test_user_not_setted_permission_returns_403(self):
        self.user.authorizations.create(project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json.get("detail"), "You do not have permission to access this project")

    def tests_app_does_not_exist_returns_404(self):
        self.user.authorizations.create(project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_ADMIN)
        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json.get("detail"), "This project does not have an integrated WhatsApp Demo")

    def test_request_ok(self):
        self.user.authorizations.create(project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_ADMIN)

        redirect_url = "https://wa.me/1234?text=weni-demo-pi68n_q5A"
        apptype = APPTYPES.get("wpp-demo")
        apptype.create_app(project_uuid=self.project_uuid, created_by=self.user, config={"redirect_url": redirect_url})

        response = self.request.get(self.url + f"?project={self.project_uuid}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, dict(url=redirect_url))
