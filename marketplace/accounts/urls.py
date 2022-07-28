from django.urls import path, include
from rest_framework.routers import DefaultRouter

from weni.protobuf.integrations import user_pb2_grpc

from .services import UserPermissionService, UserService

from .views import UserPermissionViewSet, UserViewSet


def grpc_handlers(server):
    user_pb2_grpc.add_UserPermissionControllerServicer_to_server(UserPermissionService.as_servicer(), server)
    user_pb2_grpc.add_UserControllerServicer_to_server(UserService.as_servicer(), server)


router = DefaultRouter()

router.register("user", UserViewSet, basename="user")
router.register("user-permission", UserPermissionViewSet, basename="user_permission")

urlpatterns = [
    path("", include(router.urls)),
]
