from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


# TODO: Remove unnecessary serializers
class WhatsAppCloudSerializer(AppTypeBaseSerializer):
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
        )
        read_only_fields = ("code", "uuid", "platform")

        # TODO: Validate fields


class WhatsAppCloudConfigureSerializer(serializers.Serializer):
    input_token = serializers.CharField(required=True)
    waba_id = serializers.CharField(required=True)
    phone_number_id = serializers.CharField(required=True)
    business_id = serializers.CharField(required=True)

class WhatsAppCloudDeleteSerializer(serializers.Serializer):
    phone_number_id = serializers.CharField(required=True)
    channel_uuid = serializers.CharField(required=True)
    user_email = serializers.CharField(required=True)