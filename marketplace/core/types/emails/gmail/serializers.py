from rest_framework import serializers

from marketplace.core.types.emails.base_serializer import BaseEmailSerializer


class GmailSerializer(BaseEmailSerializer):
    access_token = serializers.CharField(required=True)
    refresh_token = serializers.CharField(required=True)

    def to_channel_data(self):
        """
        Prepares the data for channel creation from the validated data.
        Extends the base data with Gmail-specific fields.
        """
        base_data = super().to_channel_data()
        base_data.update(
            {
                "access_token": self.validated_data["access_token"],
                "refresh_token": self.validated_data["refresh_token"],
            }
        )
        return base_data


class GmailOAuth(serializers.Serializer):
    code = serializers.CharField(required=True)
