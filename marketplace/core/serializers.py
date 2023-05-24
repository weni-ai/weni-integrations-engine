from rest_framework import serializers
from django.contrib.auth import get_user_model


User = get_user_model()


class AppTypeBaseSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault(),
        write_only=True,
    )
    modified_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault(),
        write_only=True,
    )

    def create(self, validated_data):
        validated_data.pop("modified_by", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("created_by", None)
        return super().update(instance, validated_data)
