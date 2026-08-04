from typing import Optional, Union
from uuid import UUID

import pendulum
from django.conf import settings
from weni.eda.django.connection_params import AMQConnectionParamsFactory
from weni.eda.eda_publisher import EDAPublisher


class AppMigrationEDAPublisher:
    """
    Publisher for app migration events via AmazonMQ (weni-eda).

    Publishes to exchange 'channels.topic' with routing key 'channel.migrated',
    carrying the Flows channel uuid (App.flow_object_uuid) as data.uuid.
    """

    EXCHANGE = "channels.topic"
    ROUTING_KEY = "channel.migrated"
    EVENT_TYPE = "integrations.channel.migrated"
    PRODUCER = "weni-integrations"

    def __init__(self):
        if not settings.TESTING:
            self.eda_publisher = EDAPublisher(AMQConnectionParamsFactory)
        else:
            self.eda_publisher = None

    def publish_channel_migrated(
        self,
        event_id: Union[UUID, str],
        channel_uuid: Union[UUID, str],
        app_uuid: Union[UUID, str],
        project_from: Union[UUID, str],
        project_to: Union[UUID, str],
        timestamp: Optional[pendulum.DateTime] = None,
    ) -> None:
        """Publish a channel migrated event to AmazonMQ."""
        if not self.eda_publisher:
            return

        if timestamp is None:
            timestamp = pendulum.now("UTC")

        message_body = {
            "event_id": str(event_id),
            "event_type": self.EVENT_TYPE,
            "producer": self.PRODUCER,
            "timestamp": timestamp.to_iso8601_string(),
            "data": {
                "uuid": str(channel_uuid),
                "app_uuid": str(app_uuid),
                "project": {
                    "from": str(project_from),
                    "to": str(project_to),
                },
            },
        }

        self.eda_publisher.send_message(
            message_body,
            exchange=self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
        )
