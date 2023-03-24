import uuid

from django.urls import reverse

from rest_framework import status

from unittest.mock import patch
from unittest.mock import MagicMock

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization

from ..views import WhatsAppCloudViewSet


class RetrieveWhatsAppCloudTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("wpp-cloud-app-detail", kwargs={"uuid": self.app.uuid})

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


class DestroyWhatsAppCloudTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )
        self.url = reverse("wpp-cloud-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def test_destroy_app_ok(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpdateWhatsAppCloudWebHookTestCase(APIBaseTestCase):
    view_class = WhatsAppCloudViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse(
            "wpp-cloud-app-update-webhook", kwargs={"uuid": self.app.uuid}
        )

    @property
    def view(self):
        return self.view_class.as_view({"patch": "update_webhook"})

    @patch("marketplace.flows.client.FlowsClient.detail_channel")
    @patch("marketplace.flows.client.FlowsClient.update_config")
    def test_update_webhook_success(self, mock_flows_client, mock_detail):
        mock = MagicMock()
        mock.raise_for_status.return_value = None
        mock_flows_client.return_value = mock

        webhook = {
            "url": "https://webhook.site/60f72b28-ff2e-4eaa-8655-e9fe76584555",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer 1203alksdalksjd1029alksjda",
                "Content-type": "application/json",
            },
        }
        data = {"config": {"webhook": webhook}}
        config = {
            "tests_key": "test_value",
            "config": {"key1": "value1", "key2": "value2"},
        }
        mock_detail.return_value = config

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        app = App.objects.get(uuid=self.app.uuid)
        app.config["webhook"] = webhook
        app.save()

        self.assertEqual(app.config["webhook"], webhook)

    def test_update_webhook_invalid_key(self):
        data = {"invalid_key": {}}

        response = self.request.patch(self.url, data, uuid=self.app.uuid)
        self.assertEqual(response.json, {"detail": "Missing key: 'config'"})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
