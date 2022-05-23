from django.conf import settings
from .client import ConnectProjectClient, ConnectChannelClient
from marketplace.celery import app as celery_app

@celery_app.task(name="create_channel")
def create_channel(user: str, project_uuid: str, data: dict, channeltype_code: str):
    client = ConnectProjectClient()
    channel = client.create_channel(user, project_uuid, data, channeltype_code)
    return dict(uuid=channel.uuid, name=channel.name, config=channel.config, address=channel.address)


@celery_app.task(name="release_channel")
def release_channel(channel_uuid: str, user_email: str) -> None:
    client = ConnectProjectClient()
    client.release_channel(channel_uuid, user_email)
    return None


@celery_app.task(name="get_channel_token")
def get_channel_token(uuid: str, name: str) -> str:
    client = ConnectChannelClient()
    return client.get_channel_token(uuid, name).token