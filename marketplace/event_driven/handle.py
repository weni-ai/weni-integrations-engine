from amqp.channel import Channel

from marketplace.projects.handle import handle_consumers as project_handle_consumers
from marketplace.accounts.handle import handle_consumers as update_permission_consumers


def handle_consumers(channel: Channel) -> None:
    project_handle_consumers(channel)
    update_permission_consumers(channel)
