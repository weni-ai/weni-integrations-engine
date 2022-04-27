from django_grpc_framework import generics, mixins
from django.contrib.auth import get_user_model

from .models import ProjectAuthorization
from .serializers import ProjectAuthorizationProtoSerializer, UserProtoSerializer


User = get_user_model()


class UserPermissionService(mixins.UpdateModelMixin, generics.GenericService):

    serializer_class = ProjectAuthorizationProtoSerializer

    def get_object(self):
        user, _ = User.objects.get_or_create(email=self.request.user)
        project_uuid = self.request.project_uuid
        return ProjectAuthorization.objects.get_or_create(user=user, project_uuid=project_uuid)[0]


class UserService(mixins.UpdateModelMixin, generics.GenericService):

    serializer_class = UserProtoSerializer

    def get_object(self):
        return User.objects.get_or_create(email=self.request.user)[0]
