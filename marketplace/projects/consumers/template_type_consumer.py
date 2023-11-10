import amqp
from sentry_sdk import capture_exception

from marketplace.event_driven.parsers import JSONParser
from marketplace.event_driven.consumers import EDAConsumer
from ..usecases import create_template_type


class TemplateTypeConsumer(EDAConsumer):  # pragma: no cover
    def consume(self, message: amqp.Message):
        print(f"[TemplateTypeConsumer] - Consuming a message. Body: {message.body}")

        try:
            body = JSONParser.parse(message.body)

            create_template_type(
                uuid=body.get("uuid"),
                project_uuid=body.get("project_uuid"),
                name=body.get("name"),
            )

            message.channel.basic_ack(message.delivery_tag)

        except Exception as exception:
            capture_exception(exception)
            message.channel.basic_reject(message.delivery_tag, requeue=False)
            print(f"[ProjectConsumer] - Message rejected by: {exception}")
