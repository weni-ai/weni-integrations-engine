import os
import json

from django.conf import settings
from rest_framework import serializers

from marketplace.core.fields import Base64ImageField
from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.core.storage import AppStorage
from . import type as type_

from marketplace.clients.flows.client import FlowsClient


class WeniWebChatSerializer(AppTypeBaseSerializer):
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
    initPayload = serializers.CharField(required=False)
    mainColor = serializers.CharField(default="#00DED3")
    profileAvatar = AvatarBase64ImageField(required=False)
    customCss = serializers.CharField(required=False)
    timeBetweenMessages = serializers.IntegerField(default=1)
    tooltipMessage = serializers.CharField(required=False)
    startFullScreen = serializers.BooleanField(default=False)
    embedded = serializers.BooleanField(default=False)
    contactTimeout = serializers.IntegerField(default=0)
    version = serializers.CharField(default="1")
    useConnectionOptimization = serializers.BooleanField(default=False)

    def to_internal_value(self, data):
        self.app = self.parent.instance

        data = super().to_internal_value(data)
        storage = AppStorage(self.app)

        if data.get("profileAvatar"):
            content_file = data["profileAvatar"]

            with storage.open(content_file.name, "w") as up_file:
                up_file.write(content_file.file.read())
                file_url = storage.url(up_file.name)
                data["profileAvatar"] = file_url
                data["openLauncherImage"] = file_url

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

        if self.app.flow_object_uuid is None:
            version = attrs.get("version", "2")
            self.app.flow_object_uuid = self._create_channel(version).get("uuid")
            self.app.configured = True

        attrs["socketUrl"] = settings.SOCKET_BASE_URL
        attrs["host"] = settings.FLOWS_HOST_URL
        attrs.pop("keepHistory")
        attrs["script"] = self.generate_script(attrs.copy())

        return super().validate(attrs)

    def _create_channel(self, version: str) -> str:
        user = self.context.get("request").user
        name = f"{type_.WeniWebChatType.name} - #{self.app.id}"
        data = {"name": name, "base_url": settings.SOCKET_BASE_URL, "version": version}
        client = FlowsClient()
        return client.create_channel(
            user.email, self.app.project_uuid, data, self.app.flows_type_code
        )

    def generate_script(self, attrs):
        """
        Generate a script with serializer validated attrs, upload it to S3 and get url
        """
        header_path = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(header_path, "header.script"), "r") as script_header:
            header = script_header.read().replace(
                "<APPTYPE_CODE>", type_.WeniWebChatType.code
            )
            header = header.replace(
                "<CUSTOM-MESSAGE-DELAY>", str(attrs.get("timeBetweenMessages"))
            )

            custom_css = str(attrs.get("customCss", ""))
            header = header.replace("<CUSTOM_CSS>", custom_css)

            attrs.pop("timeBetweenMessages")

            attrs["channelUuid"] = str(self.app.flow_object_uuid)

            if custom_css:
                attrs.pop("customCss")

            # For WWC version 2, enforce connectOn rule based on useConnectionOptimization
            version_value = str(attrs.pop("version", "1"))
            if version_value == "2":
                use_conn_opt = bool(attrs.get("useConnectionOptimization", False))
                attrs["connectOn"] = "demand" if use_conn_opt else "mount"

            # Do not include version in the generated script (already popped above)

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
