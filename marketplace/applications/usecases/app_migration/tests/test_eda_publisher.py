from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import TestCase, override_settings

from marketplace.applications.usecases.app_migration.eda_publisher import (
    AppMigrationEDAPublisher,
)


@override_settings(TESTING=True)
class AppMigrationEDAPublisherDisabledTestCase(TestCase):
    def test_publish_is_noop_when_testing(self):
        publisher = AppMigrationEDAPublisher()
        self.assertIsNone(publisher.eda_publisher)

        publisher.publish_channel_migrated(
            event_id=uuid4(),
            channel_uuid=uuid4(),
            app_uuid=uuid4(),
            project_from=uuid4(),
            project_to=uuid4(),
        )


@override_settings(TESTING=False)
class AppMigrationEDAPublisherEnabledTestCase(TestCase):
    @patch("marketplace.applications.usecases.app_migration.eda_publisher.EDAPublisher")
    def test_publish_sends_expected_message(self, mock_eda_publisher_cls):
        mock_eda = MagicMock()
        mock_eda_publisher_cls.return_value = mock_eda

        publisher = AppMigrationEDAPublisher()
        event_id = uuid4()
        channel_uuid = uuid4()
        app_uuid = uuid4()
        project_from = uuid4()
        project_to = uuid4()

        publisher.publish_channel_migrated(
            event_id=event_id,
            channel_uuid=channel_uuid,
            app_uuid=app_uuid,
            project_from=project_from,
            project_to=project_to,
        )

        mock_eda.send_message.assert_called_once()
        body, kwargs = (
            mock_eda.send_message.call_args.args[0],
            mock_eda.send_message.call_args.kwargs,
        )
        self.assertEqual(kwargs["exchange"], "channels.topic")
        self.assertEqual(kwargs["routing_key"], "channel.migrated")
        self.assertEqual(body["event_id"], str(event_id))
        self.assertEqual(body["event_type"], "integrations.channel.migrated")
        self.assertEqual(body["producer"], "weni-integrations")
        self.assertEqual(body["data"]["uuid"], str(channel_uuid))
        self.assertEqual(body["data"]["app_uuid"], str(app_uuid))
        self.assertEqual(body["data"]["project"]["from"], str(project_from))
        self.assertEqual(body["data"]["project"]["to"], str(project_to))
