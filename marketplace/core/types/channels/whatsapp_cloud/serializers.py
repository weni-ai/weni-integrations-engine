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
    waba_id = serializers.CharField(required=True)
    phone_number_id = serializers.CharField(required=True)
    auth_code = serializers.CharField(required=True)
