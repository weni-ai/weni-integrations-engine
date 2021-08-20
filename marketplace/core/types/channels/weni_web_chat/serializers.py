from django.db.models import fields
from marketplace.applications.models import App
from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer


class WeniWebChatSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("app_code", "uuid", "org_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("app_code", "uuid")


class WeniWebChatConfigureSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
