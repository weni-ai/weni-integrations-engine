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
        url = "https://www.googleapis.com/userinfo/v2/me?"
        url += f"access_token={self.validated_data['access_token']}&alt=json&prettyPrint=true"
        response = requests.get(url=url)
        if response.status_code != 200:
            print(f"error in first try: {response.json()}")
            url = "https://www.googleapis.com/oauth2/v2/userinfo?"
            url += f"access_token={self.validated_data['access_token']}"
            url += f"&oauth_token={self.validated_data['access_token']}"
            url += "&alt=json&prettyPrint=true"
            response = requests.get(url=url)
            if response.status == 200:
                print(f"successfull using: {url}")
            else:
                print(f"error in second try: {response.json()}")
                url = "https://www.googleapis.com/oauth2/v1/userinfo?access_token="
                url += {self.validated_data['access_token']}
                response = requests.get(url=url)
                if response == 200:
                    print(f"sucess using: {url}")
                else:
                    print(f"error in third try: {response.json}")
        else:
            print(f"sucessfull using: {url}")

        base_data = {
            "username": response.json().get("email"),
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
        print(f"user_data: {base_data}")

        return base_data
