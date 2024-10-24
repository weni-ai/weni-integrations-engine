import re

from rest_framework import serializers

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class EmailSerializer(AppTypeBaseSerializer):
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


class BaseEmailSerializer(serializers.Serializer):
    username = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)
    smtp_host = serializers.CharField(required=True)
    smtp_port = serializers.IntegerField(required=True)
    imap_host = serializers.CharField(required=True)
    imap_port = serializers.IntegerField(required=True)

    def validate_smtp_port(self, value):
        # Ensure SMTP port is either 465 (SSL) or 587 (TLS)
        if value not in [465, 587]:
            raise serializers.ValidationError(
                "SMTP port must be 465 (SSL) or 587 (TLS)."
            )
        return value

    def validate_imap_port(self, value):
        # Ensure IMAP port is either 993 (SSL/TLS) or 143 (No encryption)
        if value not in [993, 143]:
            raise serializers.ValidationError("IMAP port must be 993 (SSL/TLS) or 143.")
        return value

    def validate_smtp_host(self, value):
        # Basic domain format validation for smtp_host
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            raise serializers.ValidationError("Invalid SMTP host format.")
        return value

    def validate_imap_host(self, value):
        # Basic domain format validation for imap_host
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            raise serializers.ValidationError("Invalid IMAP host format.")
        return value

    def to_channel_data(self):
        """
        Prepares the data for channel creation from the validated config.
        Common to all email configurations.
        """
        return {
            "username": self.validated_data["username"],
            "password": self.validated_data["password"],
            "smtp_host": self.validated_data["smtp_host"],
            "smtp_port": self.validated_data["smtp_port"],
            "imap_host": self.validated_data["imap_host"],
            "imap_port": self.validated_data["imap_port"],
        }
