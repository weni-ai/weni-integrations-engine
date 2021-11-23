import json

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

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> str:
        response = self.project_stub.CreateChannel(
            project_pb2.CreateChannelRequest(
                user=user, project_uuid=project_uuid, data=json.dumps(data), channeltype_code=channeltype_code
            )
        )
        return response

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        response = self.project_stub.ReleaseChannel(
            project_pb2.ReleaseChannelRequest(channel_uuid=channel_uuid, user=user_email)
        )
        return response


@celery_app.task(name="create_channel")
def create_channel(user: str, project_uuid: str, data: dict, channeltype_code: str) -> str:
    client = ConnectGRPCClient()
    return client.create_channel(user, project_uuid, data, channeltype_code).uuid


@celery_app.task(name="release_channel")
def release_channel(channel_uuid: str, user_email: str) -> None:
    client = ConnectGRPCClient()
    client.release_channel(channel_uuid, user_email)
    return None
