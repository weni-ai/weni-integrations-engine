import amqp
from sentry_sdk import capture_exception

from ..usecases import update_permission
from marketplace.event_driven.parsers import JSONParser
from marketplace.event_driven.consumers import EDAConsumer


class UpdatePermissionConsumer(EDAConsumer):
    def consume(self, message: amqp.Message):  # pragma: no cover
        print(f"[UpdatePermission] - Consuming a message. Body: {message.body}")
        try:
            body = JSONParser.parse(message.body)

            update_permission(
                project_uuid=body.get("project"),
                action=body.get("action"),
                user_email=body.get("user"),
                role=body.get("role"),
            )

            message.channel.basic_ack(message.delivery_tag)

        except Exception as exception:
            capture_exception(exception)
            message.channel.basic_reject(message.delivery_tag, requeue=False)
            print(f"[UpdatePermission] - Message rejected by: {exception}")
