import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import WhatsAppDemoViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization


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

    @patch("marketplace.celery.app.send_task")
    def test_request_ok(self, task):

        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        task.side_effect = [
            CeleryResponse(dict(name="WhatsApp: +559999998888", uuid=channel_uuid)),
            CeleryResponse("WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"),
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = App.objects.get(uuid=response.json.get("uuid"))
        self.assertEqual(str(app.uuid), response.json["uuid"])
        self.assertEqual(app.config["title"], "WhatsApp: +559999998888")
        self.assertEqual(app.config["channelUuid"], channel_uuid)
        self.assertEqual(app.config["routerToken"], "WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te")
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

    @patch("marketplace.celery.app.send_task")
    def test_create_app_platform(self, task):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        task.side_effect = [
            CeleryResponse(dict(name="WhatsApp: +559999998888", uuid=channel_uuid)),
            CeleryResponse("WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"),
        ]

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    @patch("marketplace.celery.app.send_task")
    def test_get_app_with_respective_project_uuid(self, task):
        self.view_class.type_class.NUMBER = "+559999998888"
        channel_uuid = str(uuid.uuid4())

        task.side_effect = [
            CeleryResponse(dict(name="WhatsApp: +559999998888", uuid=channel_uuid)),
            CeleryResponse("WhatsApp:+559999998888-whatsapp-demo-v5ciobe7te"),
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
            code="wpp-demo", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
        )
        self.user_authorization = self.user.authorizations.create(project_uuid=self.app.project_uuid)
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
            code="wpp-demo", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
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

    def test_destroy_with_authorization_contributor_and_another_user(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_CONTRIBUTOR)
        self.request.set_user(self.super_user)
        self.super_user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_viewer(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_VIEWER)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_with_authorization_not_setted(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
