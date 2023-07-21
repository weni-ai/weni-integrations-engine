from amqp.channel import Channel

from .consumers import TemplateTypeConsumer, ProjectConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume("integrations.template-types", callback=TemplateTypeConsumer.consume)
    channel.basic_consume("integrations.projects", callback=ProjectConsumer.consume)
