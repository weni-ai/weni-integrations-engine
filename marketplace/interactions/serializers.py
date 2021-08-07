from rest_framework import serializers
from django.contrib.auth import get_user_model

from marketplace.interactions.models import Comment
from marketplace.core.validators import validate_app_code_exists


User = get_user_model()


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("app_code", "uuid", "content", "created_by", "created_on", "modified_by", "edited", "owned")

    app_code = serializers.CharField(validators=[validate_app_code_exists], required=True)
    uuid = serializers.CharField(read_only=True)
    content = serializers.CharField(required=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault(), write_only=True
    )
    modified_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault(), write_only=True
    )
    created_on = serializers.DateTimeField(read_only=True)
    edited = serializers.BooleanField(read_only=True)
    owned = serializers.SerializerMethodField()

    def create(self, validated_data):
        validated_data.pop("modified_by")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        print(validated_data)
        return super().update(instance, validated_data)

    def get_owned(self, obj) -> bool:
        request = self.context["request"]
        print(self.context)
        if request:
            return obj.created_by == request.user

        return False
