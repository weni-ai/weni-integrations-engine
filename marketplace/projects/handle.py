from amqp.channel import Channel

from .consumers import TemplateTypeConsumer, ProjectConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume(
        "integrations.template-types", callback=TemplateTypeConsumer().handle
    )
    channel.basic_consume("integrations.projects", callback=ProjectConsumer().handle)
