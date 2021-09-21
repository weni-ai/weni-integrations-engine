from django.contrib.auth import get_user_model
from rest_framework import serializers
from django_grpc_framework import proto_serializers

from .models import ProjectAuthorization
from weni.protobuf.integrations import user_pb2


User = get_user_model()


class ProjectAuthorizationSerializer(proto_serializers.ModelProtoSerializer):

    user = serializers.SlugRelatedField(slug_field="email", queryset=User.objects.all())

    class Meta:
        model = ProjectAuthorization
        proto_class = user_pb2.Permission
        fields = ("project_uuid", "role", "user")
