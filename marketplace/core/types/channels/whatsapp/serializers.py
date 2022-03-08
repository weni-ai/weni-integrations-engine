from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WhatsAppSerializer(AppTypeBaseSerializer):

    target_id = serializers.CharField(write_only=True, required=True)
    input_token = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = App
        fields = (
            "code",
            "uuid",
            "project_uuid",
            "platform",
            "config",
            "created_by",
            "created_on",
            "modified_by",
            "target_id",
            "input_token",
        )
        read_only_fields = ("code", "uuid", "platform")

        # TODO: Validate fields

    def create(self, validated_data):
        validated_data.pop("target_id")
        validated_data.pop("input_token")
        return super().create(validated_data)
