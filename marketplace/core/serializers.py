from typing import TYPE_CHECKING

from rest_framework import serializers
from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from marketplace.core.types.base import AppType

User = get_user_model()


class AppTypeBaseSerializer(serializers.ModelSerializer):
    type_class: "AppType" = None

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        view = self.context.get("view")
        if hasattr(view, "type_class"):
            self.type_class = self.context.get("view").type_class

    def create(self, validated_data):
        validated_data.pop("modified_by", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("created_by", None)
        return super().update(instance, validated_data)
