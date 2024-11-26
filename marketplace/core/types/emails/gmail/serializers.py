import requests
import logging

from django.conf import settings
from rest_framework import serializers

from marketplace.core.types.emails.base_serializer import BaseEmailSerializer

logger = logging.getLogger(__name__)


class GmailSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=True)
    refresh_token = serializers.CharField(required=True)

    def to_channel_data(self):
        """
        Prepares the data for channel creation from the validated data.
        Extends the base data with Gmail-specific fields.
        """
        # base_data = super().to_channel_data()
        url = "https://www.googleapis.com/userinfo/v2/me?"
        url += f"access_token={self.validated_data['access_token']}&alt=json&prettyPrint=true"
        response = requests.get(url=url)
        base_data = {
            "username": response.json().get("email"),
            "password": "",
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT,
            "imap_host": settings.IMAP_HOST,
            "imap_port": settings.IMAP_PORT,
        }
        base_data.update(
            {
                "access_token": self.validated_data["access_token"],
                "refresh_token": self.validated_data["refresh_token"],
            }
        )
        logger.info(f"user_data: {base_data}")
        print(f"user_data: {base_data}")

        return base_data
