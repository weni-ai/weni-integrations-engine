from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from ..tasks import sync_whatsapp_cloud_apps
from marketplace.applications.models import App

from unittest.mock import MagicMock

User = get_user_model()


class SyncWhatsAppCloudAppsTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

        lock_mock = MagicMock()
        lock_mock.__enter__.return_value = None
        lock_mock.__exit__.return_value = False
        self.redis_mock.lock.return_value = lock_mock

        wpp_type = APPTYPES.get("wpp")
        wpp_cloud_type = APPTYPES.get("wpp-cloud")

        self.wpp_app = wpp_type.create_app(
            config={"have_to_stay": "fake"},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        self.wpp_cloud_app = wpp_cloud_type.create_app(
            config={"have_to_stay": "fake"},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        return super().setUp()

    def _get_mock_value(self, project_uuid: str, flow_object_uuid: str) -> list:
        return [
            {
                "uuid": flow_object_uuid,
                "name": "teste",
                "config": {},
                "address": "f234234",
                "project_uuid": project_uuid,
                "is_active": True,
            }
        ]

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.flows.client.FlowsClient.list_channels")
    def test_whatsapp_app_that_already_exists_is_migrated_correctly(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            str(self.wpp_app.project_uuid), str(self.wpp_app.flow_object_uuid)
        )

        mock_redis.return_value = self.redis_mock

        sync_whatsapp_cloud_apps()

        app = App.objects.get(id=self.wpp_app.id)
        self.assertEqual(app.code, "wpp-cloud")
        self.assertIn("config_before_migration", app.config)
        self.assertIn("have_to_stay", app.config.get("config_before_migration"))

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.flows.client.FlowsClient.list_channels")
    def test_sync_for_non_migrated_channels(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        list_channel_mock.return_value = self._get_mock_value(
            str(self.wpp_cloud_app.project_uuid),
            str(self.wpp_cloud_app.flow_object_uuid),
        )

        mock_redis.return_value = self.redis_mock

        sync_whatsapp_cloud_apps()

        app = App.objects.get(id=self.wpp_cloud_app.id)
        self.assertEqual(app.code, "wpp-cloud")
        self.assertIn("have_to_stay", app.config)

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.flows.client.FlowsClient.list_channels")
    def test_create_new_whatsapp_cloud(
        self, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        list_channel_mock.return_value = self._get_mock_value(
            project_uuid, flow_object_uuid
        )

        mock_redis.return_value = self.redis_mock

        sync_whatsapp_cloud_apps()

        self.assertTrue(App.objects.filter(flow_object_uuid=flow_object_uuid).exists())
        self.assertTrue(App.objects.filter(project_uuid=project_uuid).exists())
