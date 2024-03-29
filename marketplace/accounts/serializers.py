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


class ProjectAuthorizationSerializer(serializers.Serializer):
    project_uuid = serializers.CharField(read_only=True)
    user = serializers.CharField(required=True, allow_blank=False)
    role = serializers.IntegerField(required=True, min_value=0, max_value=3)


class UserPermissionSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, allow_blank=False)
    photo_url = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
