from amqp.channel import Channel

from .consumers import UpdatePermissionConsumer


def handle_consumers(channel: Channel) -> None:
    channel.basic_consume(
        "integrations.update-permission", callback=UpdatePermissionConsumer().handle
    )
