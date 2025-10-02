from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserPermissionViewSet, UserViewSet, UserAPITokenAPIView


router = DefaultRouter()

router.register("user", UserViewSet, basename="user")
router.register("user-permission", UserPermissionViewSet, basename="user_permission")


urlpatterns = [
    path("", include(router.urls)),
    path("user-api-token", UserAPITokenAPIView.as_view(), name="user_api_token"),
]
