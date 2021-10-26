import grpc
from django.conf import settings

from marketplace.celery import app as celery_app
from weni.protobuf.connect import project_pb2, project_pb2_grpc


class ConnectGRPCClient:

    base_url = settings.SOCKET_BASE_URL

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

    def create_weni_web_chat(self, project_uuid: str, name: str, user_email: str) -> str:
        response = self.project_stub.CreateChannel(
            project_pb2.CreateChannelRequest(
                project_uuid=project_uuid, name=name, user=user_email, base_url=self.base_url
            )
        )
        return response


@celery_app.task(name="create_weni_web_chat")
def create_weni_web_chat(project_uuid: str, name: str, user_email: str) -> str:
    client = ConnectGRPCClient()
    return client.create_weni_web_chat(project_uuid, name, user_email).uuid
