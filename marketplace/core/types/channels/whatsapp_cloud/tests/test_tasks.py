from uuid import uuid4
import copy

from unittest.mock import patch
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types import APPTYPES
from ..tasks import (
    sync_whatsapp_cloud_apps,
    check_apps_uncreated_on_flow,
    update_account_info_by_webhook,
)
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync import (
    SyncWhatsAppCloudAppsUseCase,
)


User = get_user_model()


class SyncWhatsAppCloudAppsTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.redis_mock = MagicMock()
        self.redis_mock.get.return_value = None

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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    def test_sync_already_in_progress(self, mock_redis):
        self.redis_mock.get.return_value = True
        mock_redis.return_value = self.redis_mock

        result = sync_whatsapp_cloud_apps()

        self.assertIsNone(result)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
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

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.get_redis_connection"
    )
    @patch("marketplace.clients.flows.client.FlowsClient.list_channels")
    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_cloud_sync.logger"
    )
    def test_app_cloud_creation_error(
        self, logger_mock, list_channel_mock: "MagicMock", mock_redis
    ) -> None:
        project_uuid = str(uuid4())
        flow_object_uuid = str(uuid4())

        channel_value = self._get_mock_value(project_uuid, flow_object_uuid)
        channel_value[0]["is_active"] = True

        list_channel_mock.return_value = channel_value

        # Mock the _create_new_app method to raise an exception
        with patch.object(
            SyncWhatsAppCloudAppsUseCase,
            "_create_new_app",
            side_effect=Exception("Test exception"),
        ):
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
    def test_wa_phone_number_id_missing(self, FlowsClientMock):
        self.app.config = {}
        self.app.save()
        check_apps_uncreated_on_flow()

        FlowsClientMock.assert_not_called()

    @patch("marketplace.clients.flows.client.FlowsClient")
    def test_user_no_project_access(self, FlowsClientMock):
        self.app.config = {"wa_phone_number_id": "123456789"}
        self.app.save()

        check_apps_uncreated_on_flow()

        FlowsClientMock.assert_not_called()

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_created_successfully(self, FlowsClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "123456789"}
        self.app.save()

        data = {"uuid": uuid4()}

        client_mock = FlowsClientMock.return_value
        client_mock.create_wac_channel.return_value = data

        check_apps_uncreated_on_flow()

        app = App.objects.get(id=self.app.id)
        self.assertEqual(app.flow_object_uuid, data["uuid"])

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_creation_exception(self, FlowsClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "0123456789"}
        self.app.save()

        client_mock = FlowsClientMock.return_value
        client_mock.create_wac_channel.side_effect = Exception(
            "Channel creation failed"
        )

        check_apps_uncreated_on_flow()

        app = App.objects.get(uuid=self.app.uuid)
        self.assertIsNone(app.flow_object_uuid)

    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.FlowsClient")
    def test_channel_without_uuid(self, FlowsClientMock):
        self.create_project_authorization()
        self.app.config = {"wa_phone_number_id": "0123456789"}
        self.app.save()

        client_mock = FlowsClientMock.return_value
        client_mock.create_wac_channel.return_value = {}

        check_apps_uncreated_on_flow()

        app = App.objects.get(uuid=self.app.uuid)
        self.assertIsNone(app.flow_object_uuid)


class UpdateAccountInfoByWebhookTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.mock_processor = MagicMock()
        return super().setUp()

    def _get_webhook_data(self, waba_id="123456789", field="account_update"):
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "field": field,
                            "value": {
                                "waba_info": {
                                    "waba_id": waba_id,
                                    "ad_account_id": "ad_account_123",
                                }
                            },
                        }
                    ]
                }
            ]
        }

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_successful_webhook_processing(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = self._get_webhook_data()
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)

        # The value should have reason set to empty string after processing
        expected_value = webhook_data["entry"][0]["changes"][0]["value"]
        self.assertEqual(expected_value["reason"], "")

        self.mock_processor.process_event.assert_called_once_with(
            "123456789", expected_value, "account_update", webhook_data
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_webhook_data_missing(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor

        # The function will raise AttributeError when webhook_data is None
        with self.assertRaises(AttributeError):
            update_account_info_by_webhook()

        mock_logger.info.assert_any_call(
            "Update mmlite status by webhook data received: None"
        )
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_empty_webhook_data(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {}
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_missing_waba_id(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {
            "entry": [
                {"changes": [{"field": "account_update", "value": {"waba_info": {}}}]}
            ]
        }
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call(
            f"Whatsapp business account id not found in webhook data: {webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_event_type_not_allowed(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = self._get_webhook_data(field="other_event")
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("Event: other_event, not mapped to usage")
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_multiple_entries_and_changes(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {
            "entry": [
                {
                    "changes": [
                        {
                            "field": "account_update",
                            "value": {
                                "waba_info": {
                                    "waba_id": "123456789",
                                    "ad_account_id": "ad_account_123",
                                }
                            },
                        },
                        {
                            "field": "account_update",
                            "value": {
                                "waba_info": {
                                    "waba_id": "987654321",
                                    "ad_account_id": "ad_account_456",
                                }
                            },
                        },
                    ]
                },
                {
                    "changes": [
                        {
                            "field": "account_update",
                            "value": {
                                "waba_info": {
                                    "waba_id": "555666777",
                                    "ad_account_id": "ad_account_789",
                                }
                            },
                        }
                    ]
                },
            ]
        }
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.assertEqual(self.mock_processor.process_event.call_count, 3)

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_missing_entry_field(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {"other_field": "value"}
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_missing_field_in_change(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "waba_info": {
                                    "waba_id": "123456789",
                                    "ad_account_id": "ad_account_123",
                                }
                            }
                        }
                    ]
                }
            ]
        }
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_missing_value_in_change(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {"entry": [{"changes": [{"field": "account_update"}]}]}

        # The function will raise AttributeError when value is None
        with self.assertRaises(AttributeError):
            update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {webhook_data}"
        )
        self.mock_processor.process_event.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_reason_handling_when_none(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {
            "entry": [
                {
                    "changes": [
                        {
                            "field": "account_update",
                            "value": {
                                "waba_info": {
                                    "waba_id": "123456789",
                                    "ad_account_id": "ad_account_123",
                                },
                                "reason": None,
                            },
                        }
                    ]
                }
            ]
        }
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        # The value should have reason set to empty string
        expected_value = webhook_data["entry"][0]["changes"][0]["value"]
        self.assertEqual(expected_value["reason"], "")

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_called_once_with(
            "123456789", expected_value, "account_update", webhook_data
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_reason_handling_when_missing(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {
            "entry": [
                {
                    "changes": [
                        {
                            "field": "account_update",
                            "value": {
                                "waba_info": {
                                    "waba_id": "123456789",
                                    "ad_account_id": "ad_account_123",
                                }
                            },
                        }
                    ]
                }
            ]
        }
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        # The value should have reason set to empty string
        expected_value = webhook_data["entry"][0]["changes"][0]["value"]
        self.assertEqual(expected_value["reason"], "")

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_called_once_with(
            "123456789", expected_value, "account_update", webhook_data
        )

    @patch(
        "marketplace.core.types.channels.whatsapp_cloud.tasks.create_account_update_webhook_event_processor"
    )
    @patch("marketplace.core.types.channels.whatsapp_cloud.tasks.logger")
    def test_missing_changes_field(self, mock_logger, mock_factory):
        mock_factory.return_value = self.mock_processor
        webhook_data = {"entry": [{"other_field": "value"}]}
        original_webhook_data = copy.deepcopy(webhook_data)

        update_account_info_by_webhook(webhook_data=webhook_data)

        mock_logger.info.assert_any_call(
            f"Update mmlite status by webhook data received: {original_webhook_data}"
        )
        mock_logger.info.assert_any_call("-" * 50)
        self.mock_processor.process_event.assert_not_called()
