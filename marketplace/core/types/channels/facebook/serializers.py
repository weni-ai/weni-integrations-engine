from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class FacebookSerializer(AppTypeBaseSerializer):
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

    def create(self, validated_data):
        validated_data["platform"] = self.type_class.platform
        return super().create(validated_data)


class ConfigSerializer(serializers.Serializer):
    user_access_token = serializers.CharField(required=True)
    fb_user_id = serializers.CharField(required=True)
    page_name = serializers.CharField(required=True)
    page_id = serializers.CharField(required=True)


class FacebookConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")


class FacebookSearchProductsSerializer(serializers.Serializer):
    catalog_id = serializers.CharField(required=True)
    product_ids = serializers.ListField(child=serializers.CharField(), required=True)
    fields = serializers.ListField(child=serializers.CharField(), required=False)
    summary = serializers.BooleanField(default=False, required=False)
    limit = serializers.IntegerField(default=100, required=False)
