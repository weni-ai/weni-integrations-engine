import requests
import logging

from rest_framework import serializers


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
        url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        headers = {"Authorization": f"Bearer {self.validated_data['access_token']}"}
        response = requests.get(url=url, headers=headers)
        base_data = {
            "username": response.json().get("emailAddress"),
            "password": "",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "imap_host": "imap.gmail.com",
            "imap_port": 993
        }
        base_data.update(
            {
                "access_token": self.validated_data["access_token"],
                "refresh_token": self.validated_data["refresh_token"],
            }
        )
        logger.info(f"user_data: {base_data}")

        return base_data
