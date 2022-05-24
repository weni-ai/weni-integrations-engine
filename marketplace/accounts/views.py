from rest_framework import viewsets
from rest_framework.views import APIView
from marketplace.accounts.serializers import ProjectAuthorizationSerializer, UserPermissionSerializer

from .models import ProjectAuthorization

from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.decorators import action
from django.contrib.auth import get_user_model

User = get_user_model()


class UserViewSet(viewsets.ViewSet):
    
    def get_serializer(self, *args, **kwargs):
        return UserPermissionSerializer()

    def create(self, request):

        if not request.user.has_perm("accounts.can_communicate_internally"):
            return Response({"error": "Not Allowed"}, status=status.HTTP_400_BAD_REQUEST)

        user_email = request.data.get("email", None)
        photo_url = request.data.get("photo_url", "")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        if "email" not in request.data:
            return Response({"error": "email not found in request"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get_or_create(email=user_email)[0]
    
        if "photo_url" in request.data:
            user.photo_url = photo_url

        if "first_name" in request.data:
            user.first_name = first_name

        if "last_name" in request.data:
            user.last_name = last_name

        user.save()

        serializer = UserPermissionSerializer(user)

        return Response(serializer.data)


class UserPermissionViewSet(viewsets.ViewSet):
    lookup_field = "project_uuid"

    def get_serializer(self, *args, **kwargs):
        return ProjectAuthorizationSerializer()

    def partial_update(self, request, project_uuid):

        if not request.user.has_perm("authentication.can_communicate_internally"):
            return Response({"error": "Not Allowed"}, status=status.HTTP_400_BAD_REQUEST)

        user_email = request.data.get("user", "")
        role = request.data.get("role", 1)

        if "user" not in request.data:
            return Response({"error": "user not found in request"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get_or_create(email=user_email)[0]

        project_authorization = ProjectAuthorization.objects.get_or_create(user=user, project_uuid=project_uuid)[0]

        project_authorization.role = role
        project_authorization.save()

        serializer = ProjectAuthorizationSerializer(project_authorization)

        return Response(serializer.data)