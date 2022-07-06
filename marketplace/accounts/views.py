from rest_framework import viewsets
from marketplace.accounts.serializers import ProjectAuthorizationSerializer, UserPermissionSerializer

from .models import ProjectAuthorization

from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class UserViewSet(viewsets.ViewSet):
    def get_serializer(self, *args, **kwargs):
        return UserPermissionSerializer()

    def create(self, request):

        if not request.user.has_perm("accounts.can_communicate_internally"):
            return Response({"error": "Not Allowed"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserPermissionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"error": "invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get_or_create(email=serializer.data.get("email"))[0]

        if "photo_url" in serializer.data:
            user.photo_url = serializer.data.get("photo_url")

        if "first_name" in serializer.data:
            user.first_name = serializer.data.get("first_name")

        if "last_name" in serializer.data:
            user.last_name = serializer.data.get("last_name")

        user.save()

        serializer = UserPermissionSerializer(user)

        return Response(serializer.data)


class UserPermissionViewSet(viewsets.ViewSet):
    lookup_field = "project_uuid"

    def get_serializer(self, *args, **kwargs):
        return ProjectAuthorizationSerializer()

    def partial_update(self, request, project_uuid):

        if not request.user.has_perm("accounts.can_communicate_internally"):
            return Response({"error": "Not Allowed"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProjectAuthorizationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({"error": "invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get_or_create(email=serializer.data.get("user"))[0]

        project_authorization = ProjectAuthorization.objects.get_or_create(user=user, project_uuid=project_uuid)[0]

        project_authorization.role = serializer.data.get("role")
        project_authorization.save()

        serializer = ProjectAuthorizationSerializer(project_authorization)

        return Response(serializer.data)
