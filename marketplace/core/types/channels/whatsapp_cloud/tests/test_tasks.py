from uuid import uuid4

from unittest.mock import patch
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from ..tasks import sync_whatsapp_cloud_apps, check_apps_uncreated_on_flow
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization


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
            config={"have_to_stay": True},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        self.wpp_cloud_app = wpp_cloud_type.create_app(
            config={"have_to_stay": True},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        return super().setUp()

    def _get_mock_value(self, project_uuid, flow_object_uuid):
        return [
            {
                "project_uuid": project_uuid,
                "uuid": flow_object_uuid,
                "address": "wa_phone_number_id",
                "config": {
                    "wa_number": "wa_number_value",
                    "have_to_stay": "some_value",
                },
                "is_active": True,
            }
        ]

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_whatsapp_app_that_already_exists_is_migrated_correctly(
        self, list_channel_mock: MagicMock, mock_redis: MagicMock
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
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_sync_for_non_migrated_channels(
        self, list_channel_mock: MagicMock, mock_redis: MagicMock
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
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
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

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_sync_already_in_progress(self, list_channel_mock, mock_redis):
        self.redis_mock.get.return_value = True
        mock_redis.return_value = self.redis_mock

        result = sync_whatsapp_cloud_apps()

        self.assertIsNone(result)
        list_channel_mock.assert_called_once()

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_sync_with_missing_project_uuid(
        self, list_channel_mock, mock_redis
    ) -> None:
        # Simulate a channel with missing project_uuid
        channels = self._get_mock_value(
            str(self.wpp_cloud_app.project_uuid),
            str(self.wpp_cloud_app.flow_object_uuid),
        )
        channels[0]["project_uuid"] = None

        list_channel_mock.return_value = channels
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_cloud_apps()

        app = App.objects.get(id=self.wpp_cloud_app.id)
        self.assertEqual(app.code, "wpp-cloud")
        self.assertIn("have_to_stay", app.config)

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.get_redis_connection")
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.APPTYPES.get")
    def test_app_cloud_creation_error(
        self, apptype_mock, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = True

        list_channel_mock.return_value = channel_value

        apptype_mock.return_value.create_app.side_effect = Exception("Test exception")
        mock_redis.return_value = self.redis_mock

        sync_whatsapp_cloud_apps()

        logger_mock.error.assert_called_with(
            f"Error on processing sync_whatsapp_cloud_apps for channel {flow_object_uuid}: Test exception"
        )


class CheckAppsUncreatedOnFlowTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.user_creation = User.objects.get_admin_user()
        self.project_uuid = uuid4()

        self.app = App.objects.create(
            code="wpp-cloud",
            config={"some_key": "some_value"},
            created_by=self.user_creation,
            project_uuid=self.project_uuid,
        )
        return super().setUp()

    def create_project_authorization(self):
        ProjectAuthorization.objects.create(
            user=self.user_creation,
            project_uuid=self.project_uuid,
        )

    @patch("marketplace.clients.flows.client.FlowsClient")
    def test_wa_phone_number_id_missing(self, ConnectProjectClientMock):
        self.app.config = {}
        self.app.save()
        check_apps_uncreated_on_flow()

        ConnectProjectClientMock.assert_not_called()

    @patch("marketplace.clients.flows.client.FlowsClient")
    def test_user_no_project_access(self, ConnectProjectClientMock):
        self.app.config = {"wa_phone_number_id": "123456789"}
        self.app.save()

        check_apps_uncreated_on_flow()

        ConnectProjectClientMock.assert_not_called()

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_created_successfully(self, ConnectProjectClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "123456789"}
        self.app.save()

        data = {"uuid": uuid4()}

        client_mock = ConnectProjectClientMock.return_value
        client_mock.create_wac_channel.return_value = data

        check_apps_uncreated_on_flow()

        app = App.objects.get(id=self.app.id)
        self.assertEqual(app.flow_object_uuid, data["uuid"])

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_creation_exception(self, ConnectProjectClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "0123456789"}
        self.app.save()

        client_mock = ConnectProjectClientMock.return_value
        client_mock.create_wac_channel.side_effect = Exception(
            "Channel creation failed"
        )

        check_apps_uncreated_on_flow()

        app = App.objects.get(uuid=self.app.uuid)
        self.assertIsNone(app.flow_object_uuid)

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_without_uuid(self, ConnectProjectClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "0123456789"}
        self.app.save()

        client_mock = ConnectProjectClientMock.return_value
        client_mock.create_wac_channel.return_value = {}

        check_apps_uncreated_on_flow()

        app = App.objects.get(uuid=self.app.uuid)
        self.assertIsNone(app.flow_object_uuid)
