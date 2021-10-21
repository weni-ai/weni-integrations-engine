import os
import json

from django.conf import settings
from rest_framework import serializers

from marketplace.core.fields import Base64ImageField
from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.core.storage import AppStorage
from marketplace.celery import app as celery_app
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
    timeBetweenMessages = serializers.IntegerField(default=1)

    def to_internal_value(self, data):
        self.app = self.parent.instance

        data = super().to_internal_value(data)
        storage = AppStorage(self.app)

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
        attrs["selector"] = f"#{type_.WeniWebChatType.code}"

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

        channel_uuid = self.app.config.get("channelUuid", None)
        attrs["channelUuid"] = channel_uuid if channel_uuid is not None else self._create_channel()

        attrs["socketUrl"] = settings.SOCKET_BASE_URL

        attrs.pop("keepHistory")

        attrs["script"] = self.generate_script(attrs.copy())

        return super().validate(attrs)

    def _create_channel(self) -> str:
        user = self.context.get("request").user
        name = f"{type_.WeniWebChatType.name} - #{self.app.id}"

        task = celery_app.send_task(name="create_weni_web_chat", args=[name, user.email])
        task.wait()

        return task.result

    def generate_script(self, attrs):
        """
        Generate a script with serializer validated attrs, upload it to S3 and get url
        """
        header_path = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(header_path, "header.script"), "r") as script_header:
            header = script_header.read().replace("<APPTYPE_CODE>", type_.WeniWebChatType.code)
            header = header.replace("<CUSTOM-MESSAGE-DELAY>", str(attrs.get("timeBetweenMessages")))

            custom_css = str(attrs.get("customCss", ""))
            header = header.replace("<CUSTOM_CSS>", custom_css)

            attrs.pop("timeBetweenMessages")

            if custom_css:
                attrs.pop("customCss")

        script = header.replace("<FIELDS>", json.dumps(attrs, indent=2))

        storage = AppStorage(self.app)

        with storage.open("script.js", "w") as up_file:
            up_file.write(script)
            return storage.url(up_file.name)


class WeniWebChatConfigureSerializer(AppTypeBaseSerializer):

    config = ConfigSerializer(write_only=True)
    script = serializers.SerializerMethodField()

    def get_script(self, obj):
        return obj.config.get("script")

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by", "script")
