import json

import grpc
from django.conf import settings
from rest_framework import serializers

from marketplace.celery import app as celery_app
from weni.protobuf.connect import project_pb2, project_pb2_grpc
from weni.protobuf.wpp_router import channel_pb2, channel_pb2_grpc


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

    def list_channels(self, channeltype_code: str):
        try:
            response = self.project_stub.Channel(project_pb2.ChannelListRequest(channel_type=channeltype_code))
            return response
        except grpc.RpcError as error:
            raise Exception(error)

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> str:
        try:
            response = self.project_stub.CreateChannel(
                project_pb2.CreateChannelRequest(
                    user=user, project_uuid=project_uuid, data=json.dumps(data), channeltype_code=channeltype_code
                )
            )
        except grpc.RpcError as error:
            if error.code() is grpc.StatusCode.INVALID_ARGUMENT:
                raise serializers.ValidationError()
            raise error

        return response

    def create_wac_channel(self, user: str, project_uuid: str, phone_number_id: str, config: dict):
        try:
            return self.project_stub.CreateWACChannel(
                project_pb2.ChannelWACCreateRequest(
                    user=user, project_uuid=project_uuid, phone_number_id=phone_number_id, config=json.dumps(config)
                )
            )

        except grpc.RpcError as error:
            raise serializers.ValidationError(error)

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        response = self.project_stub.ReleaseChannel(
            project_pb2.ReleaseChannelRequest(channel_uuid=channel_uuid, user=user_email)
        )
        return response


class RouterGRPCClient:
    def __init__(self):
        self.channel = self._get_channel()
        self.stub = self._get_stub()

    def _get_channel(self):
        if settings.ROUTER_CERTIFICATE_GRPC_CRT:
            with open(settings.ROUTER_CERTIFICATE_GRPC_CRT, "rb") as crt:
                credentials = grpc.ssl_channel_credentials(crt.read())
            return grpc.secure_channel(settings.ROUTER_GRPC_SERVER_URL, credentials)
        return grpc.insecure_channel(settings.ROUTER_GRPC_SERVER_URL)

    def _get_stub(self):
        return channel_pb2_grpc.ChannelServiceStub(self.channel)

    def get_channel_token(self, uuid: str, name: str) -> str:
        return self.stub.CreateChannel(channel_pb2.ChannelRequest(uuid=uuid, name=name))


@celery_app.task(name="create_channel")
def create_channel(user: str, project_uuid: str, data: dict, channeltype_code: str):
    client = ConnectGRPCClient()
    channel = client.create_channel(user, project_uuid, data, channeltype_code)
    return dict(uuid=channel.uuid, name=channel.name, config=channel.config, address=channel.address)


@celery_app.task(name="create_wac_channel")
def create_wac_channel(user: str, project_uuid: str, phone_number_id: str, config: dict):
    client = ConnectGRPCClient()
    channel = client.create_wac_channel(user, project_uuid, phone_number_id, config)
    return dict(uuid=channel.uuid, name=channel.name, config=channel.config, address=channel.address)


@celery_app.task(name="release_channel")
def release_channel(channel_uuid: str, user_email: str) -> None:
    client = ConnectGRPCClient()
    client.release_channel(channel_uuid, user_email)
    return None


@celery_app.task(name="get_channel_token")
def get_channel_token(uuid: str, name: str) -> str:
    client = RouterGRPCClient()
    return client.get_channel_token(uuid, name).token
