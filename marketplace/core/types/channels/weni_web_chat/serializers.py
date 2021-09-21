import os
import uuid
import json

from rest_framework import serializers
from marketplace.core.fields import Base64ImageField

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.core.storage import AppStorage
from . import type as type_


class WeniWebChatSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("code", "uuid", "platform")

    def create(self, validated_data):
        from .type import WeniWebChatType

        validated_data["platform"] = WeniWebChatType.platform
        return super().create(validated_data)


class AvatarBase64ImageField(Base64ImageField):
    def get_file_name(self, extencion: str) -> str:
        return f"avatar.{extencion}"


class ConfigSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    subtitle = serializers.CharField(required=False)
    inputTextFieldHint = serializers.CharField(default="Type a message...")
    showFullScreenButton = serializers.BooleanField(default=True)
    displayUnreadCount = serializers.BooleanField(default=False)
    keepHistory = serializers.BooleanField(default=False)
    initPayload = serializers.CharField(default="start")
    mainColor = serializers.CharField(default="#00DED3")
    avatarImage = AvatarBase64ImageField(required=False)
    customCss = serializers.CharField(required=False)

    # TODO: Implements `timeBetweenMessages` field

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        storage = AppStorage(self.parent.instance)

        if data.get("avatarImage"):
            content_file = data["avatarImage"]

            with storage.open(content_file.name, "w") as up_file:
                up_file.write(content_file.file.read())
                data["avatarImage"] = storage.url(up_file.name)

        if data.get("customCss"):
            with storage.open("custom.css", "w") as up_file:
                up_file.write(data["customCss"])
                data["customCss"] = storage.url(up_file.name)

        return data

    def validate(self, attrs):
        from .type import WeniWebChatType

        attrs["selector"] = f"#{WeniWebChatType.code}"

        attrs["customizeWidget"] = {
            "headerBackgroundColor": attrs["mainColor"],
            "launcherColor": attrs["mainColor"],
            "userMessageBubbleColor": attrs["mainColor"],
            "quickRepliesFontColor": attrs["mainColor"],
            "quickRepliesBackgroundColor": attrs["mainColor"] + "33",
            "quickRepliesBorderColor": attrs["mainColor"],
        }

        attrs["params"] = {
            "images": {
                "dims": {
                    "width": 300,
                    "height": 200,
                },
            },
            "storage": "local" if attrs["keepHistory"] else "session",
        }

        # channel_uuid = ConnectGRPCClient.create_weni_web_chat(request.user.email) # TODO: Implement real connectio
        channel_uuid = str(uuid.uuid4())  # Fake UUID, only to test
        attrs["channelUuid"] = channel_uuid

        attrs.pop("keepHistory")

        self.generate_script(attrs)

        return super().validate(attrs)

    def generate_script(self, attrs):
        """
        Generate a script with serializer validated attrs, upload it to S3 and get url
        """
        header_path = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(header_path, "header.script"), "r") as script_header:
            header = script_header.read().replace("<APPTYPE_CODE>", type_.WeniWebChatType.code)

        script = header.replace("<FIELDS>", json.dumps(attrs, indent=2))

        storage = AppStorage(self.parent.instance)

        with storage.open("script.js", "w") as up_file:
            up_file.write(script)
            attrs["script"] = storage.url(up_file.name)


class WeniWebChatConfigureSerializer(AppTypeBaseSerializer):

    config = ConfigSerializer(write_only=True)
    script = serializers.SerializerMethodField()

    def get_script(self, obj):
        return obj.config.get("script")

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by", "script")
