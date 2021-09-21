from django.shortcuts import get_object_or_404
from django_grpc_framework import generics, mixins
from django.contrib.auth import get_user_model

from .models import ProjectAuthorization
from .serializers import ProjectAuthorizationSerializer


User = get_user_model()


class UserPermissionService(mixins.UpdateModelMixin, generics.GenericService):

    serializer_class = ProjectAuthorizationSerializer

    def get_object(self):
        user = get_object_or_404(User, email=self.request.user)
        project_uuid = self.request.project_uuid
        return ProjectAuthorization.objects.get_or_create(user=user, project_uuid=project_uuid)[0]
