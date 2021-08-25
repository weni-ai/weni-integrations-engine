import grpc
from django.conf import settings

from marketplace.celery import app as celery_app


class ConnectGRPCClient:
    def __init__(self):
        self.channel = self._get_channel()

    def _get_channel(self):
        if settings.CONNECT_CERTIFICATE_GRPC_CRT:
            with open(settings.CONNECT_CERTIFICATE_GRPC_CRT, "rb") as crt:
                credentials = grpc.ssl_channel_credentials(crt.read())
            return grpc.secure_channel(settings.CONNECT_GRPC_SERVER_URL, credentials)
        return grpc.insecure_channel(settings.CONNECT_GRPC_SERVER_URL)
    
    @classmethod
    def create_weni_web_chat(cls, **kwargs):
        task = celery_app.send_task(name="create_weni_web_chat", kwargs=dict(client=cls(), **kwargs))


@celery_app.task(name="create_weni_web_chat")
def create_weni_web_chat(client, project_uuid: str, config: dict):
    ...
