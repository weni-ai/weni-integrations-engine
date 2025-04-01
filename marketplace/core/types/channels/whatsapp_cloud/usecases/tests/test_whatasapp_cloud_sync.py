from uuid import uuid4
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync import (
    SyncWhatsAppCloudAppsUseCase,
    SYNC_WHATSAPP_CLOUD_LOCK_KEY,
)

User = get_user_model()


class SyncWhatsAppCloudAppsUseCaseTestCase(TestCase):
    def setUp(self) -> None:
        wpp_cloud_type = APPTYPES.get("wpp-cloud")

        self.wpp_cloud_app = wpp_cloud_type.create_app(
            config={"have_to_stay": True},
            project_uuid=uuid4(),
            flow_object_uuid=uuid4(),
            created_by=User.objects.get_admin_user(),
        )

        return super().setUp()

    def _get_mock_channel(self, project_uuid, flow_object_uuid, is_active=True):
        return {
            "project_uuid": project_uuid,
            "uuid": flow_object_uuid,
            "address": "wa_phone_number_id",
            "config": {
                "wa_number": "wa_number_value",
                "have_to_stay": "some_value",
            },
            "is_active": is_active,
        }

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_execute_success(self, mock_list_channels, mock_redis):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        mock_redis.return_value = redis_mock

        mock_list_channels.return_value = [
            self._get_mock_channel(
                str(self.wpp_cloud_app.project_uuid),
                str(self.wpp_cloud_app.flow_object_uuid),
            )
        ]

        use_case = SyncWhatsAppCloudAppsUseCase()
        result = use_case.execute()

        self.assertTrue(result)
        redis_mock.set.assert_called_once_with(
            SYNC_WHATSAPP_CLOUD_LOCK_KEY, "1", ex=600
        )
        redis_mock.delete.assert_called_once_with(SYNC_WHATSAPP_CLOUD_LOCK_KEY)
        mock_list_channels.assert_called_once()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    def test_is_locked_returns_true(self, mock_redis):
        redis_mock = MagicMock()
        redis_mock.get.return_value = "1"
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        result = use_case._is_locked()

        self.assertTrue(result)
        redis_mock.get.assert_called_once_with(SYNC_WHATSAPP_CLOUD_LOCK_KEY)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    def test_is_locked_returns_false(self, mock_redis):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        result = use_case._is_locked()

        self.assertFalse(result)
        redis_mock.get.assert_called_once_with(SYNC_WHATSAPP_CLOUD_LOCK_KEY)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    def test_acquire_lock(self, mock_redis):
        redis_mock = MagicMock()
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        use_case._acquire_lock()

        redis_mock.set.assert_called_once_with(
            SYNC_WHATSAPP_CLOUD_LOCK_KEY, "1", ex=600
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    def test_release_lock(self, mock_redis):
        redis_mock = MagicMock()
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        use_case._release_lock()

        redis_mock.delete.assert_called_once_with(SYNC_WHATSAPP_CLOUD_LOCK_KEY)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    def test_fetch_channels(self, mock_list_channels, mock_redis):
        expected_channels = [
            self._get_mock_channel(
                str(self.wpp_cloud_app.project_uuid),
                str(self.wpp_cloud_app.flow_object_uuid),
            )
        ]
        mock_list_channels.return_value = expected_channels

        redis_mock = MagicMock()
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        result = use_case._fetch_channels()

        self.assertEqual(result, expected_channels)
        mock_list_channels.assert_called_once_with(use_case.app_type.flows_type_code)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.logger"
    )
    def test_process_channels_with_exception(self, mock_logger, mock_redis):
        redis_mock = MagicMock()
        mock_redis.return_value = redis_mock

        channels = [
            self._get_mock_channel(
                str(self.wpp_cloud_app.project_uuid),
                str(self.wpp_cloud_app.flow_object_uuid),
            )
        ]

        use_case = SyncWhatsAppCloudAppsUseCase()
        with patch.object(
            use_case,
            "_process_single_channel",
            side_effect=Exception("Test error"),
        ):
            use_case._process_channels(channels)

        mock_logger.error.assert_called_once_with(
            f"Error on processing sync_whatsapp_cloud_apps for channel {channels[0].get('uuid')}: Test error"
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.logger"
    )
    def test_process_single_channel_without_project_uuid(self, mock_logger, mock_redis):
        redis_mock = MagicMock()
        mock_redis.return_value = redis_mock

        use_case = SyncWhatsAppCloudAppsUseCase()
        channel = self._get_mock_channel(None, str(uuid4()))
        use_case._process_single_channel(channel)

        mock_logger.info.assert_called_once_with(
            f"The channel {channel['uuid']} does not have a project_uuid."
        )
