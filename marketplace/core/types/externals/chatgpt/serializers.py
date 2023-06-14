from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class ChatGPTCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    api_key = serializers.CharField(required=True)
    ai_model = serializers.CharField(required=True)


class ChatGPTSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = (
            "code",
            "uuid",
            "project_uuid",
            "flow_object_uuid",
            "platform",
            "config",
            "created_by",
            "created_on",
            "modified_by",
        )
        read_only_fields = ("code", "uuid", "platform")
