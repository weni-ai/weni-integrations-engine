from rest_framework import serializers
from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WeniWebChatSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("app_code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("app_code", "uuid")


class WeniWebChatConfigureSerializer(AppTypeBaseSerializer):

    config = ConfigSerializer()

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
