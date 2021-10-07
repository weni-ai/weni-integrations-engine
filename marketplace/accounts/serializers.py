from django.contrib.auth import get_user_model
from rest_framework import serializers
from django_grpc_framework import proto_serializers

from .models import ProjectAuthorization
from weni.protobuf.integrations import user_pb2


User = get_user_model()


class ProjectAuthorizationProtoSerializer(proto_serializers.ModelProtoSerializer):

    user = serializers.SlugRelatedField(slug_field="email", queryset=User.objects.all())

    class Meta:
        model = ProjectAuthorization
        proto_class = user_pb2.Permission
        fields = ("project_uuid", "role", "user")


class UserProtoSerializer(proto_serializers.ModelProtoSerializer):

    user = serializers.SlugRelatedField(slug_field="email", queryset=User.objects.all())

    class Meta:
        model = User
        proto_class = user_pb2.User
        fields = ("user", "photo_url", "first_name", "last_name")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "photo_url")
