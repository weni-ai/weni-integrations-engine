import grpc
from django.conf import settings

from marketplace.celery import app as celery_app
from marketplace.grpc.protos import project_pb2, project_pb2_grpc


class ConnectGRPCClient:
    def __init__(self):
        self.channel = self._get_channel()
        self.project_stub = self._get_project_stub()

    def _get_channel(self):
        if settings.CONNECT_CERTIFICATE_GRPC_CRT:
            with open(settings.CONNECT_CERTIFICATE_GRPC_CRT, "rb") as crt:
                credentials = grpc.ssl_channel_credentials(crt.read())
            return grpc.secure_channel(settings.CONNECT_GRPC_SERVER_URL, credentials)
        return grpc.insecure_channel(settings.CONNECT_GRPC_SERVER_URL)

    def _get_project_stub(self):
        return project_pb2_grpc.ProjectControllerStub(self.channel)

    @classmethod
    def create_weni_web_chat(cls, name: str, user_email: str, base_url: str) -> str:
        task = celery_app.send_task(name="create_weni_web_chat", args=[name, user_email, base_url])
        task.wait()
        return task.result


@celery_app.task(name="create_weni_web_chat")
def create_weni_web_chat(name: str, user_email: str, base_url: str) -> str:
    client = ConnectGRPCClient()
    response = client.project_stub.CreateChannel(
        project_pb2.CreateChannelRequest(name=name, user=user_email, base_url=base_url)
    )

    # TODO: Call connect end get response

    return "fake-channe-uuid"
