from weni.protobuf.integrations import user_pb2_grpc

from .services import UserPermissionService


def grpc_handlers(server):
    user_pb2_grpc.add_UserPermissionControllerServicer_to_server(UserPermissionService.as_servicer(), server)
