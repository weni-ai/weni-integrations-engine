from rest_framework import serializers

from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App


class VtexDomainSerializer(serializers.Serializer):
    domain = serializers.CharField(required=True)


class VtexSerializer(AppTypeBaseSerializer):
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
