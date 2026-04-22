import copy
import os
import json

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

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
            "flow_object_uuid",
        )
        read_only_fields = ("code", "uuid", "platform", "flow_object_uuid")

    def create(self, validated_data):
        validated_data["platform"] = self.type_class.platform
        return super().create(validated_data)


class AvatarBase64ImageField(Base64ImageField):
    def get_file_name(self, extencion: str) -> str:
        return f"avatar.{extencion}"


class OpenLauncherBase64ImageField(Base64ImageField):
    def get_file_name(self, extencion: str) -> str:
        return f"launcher.{extencion}"


class AvatarImageField(serializers.Field):
    """Accepts a base64-encoded image, a direct URL, or an empty string to clear it."""

    def to_internal_value(self, data):
        if data == "":
            return ""

        if isinstance(data, str) and data.startswith("data:"):
            base64_field = AvatarBase64ImageField()
            return base64_field.to_internal_value(data)

        if isinstance(data, str):
            url_validator = URLValidator()
            try:
                url_validator(data)
            except DjangoValidationError:
                raise ValidationError("Invalid URL or base64 image.")
            return data

        raise ValidationError("Expected a base64 image string or a URL.")


class OpenLauncherImageField(serializers.Field):
    """Accepts a base64-encoded image, a direct URL, or an empty string to clear it."""

    def to_internal_value(self, data):
        if data == "":
            return ""

        if isinstance(data, str) and data.startswith("data:"):
            base64_field = OpenLauncherBase64ImageField()
            return base64_field.to_internal_value(data)

        if isinstance(data, str):
            url_validator = URLValidator()
            try:
                url_validator(data)
            except DjangoValidationError:
                raise ValidationError("Invalid URL or base64 image.")
            return data

        raise ValidationError("Expected a base64 image string or a URL.")


class ConfigSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    subtitle = serializers.CharField(required=False)
    inputTextFieldHint = serializers.CharField(default="Type a message...")
    showFullScreenButton = serializers.BooleanField(default=True)
    displayUnreadCount = serializers.BooleanField(default=False)
    keepHistory = serializers.BooleanField(default=False)
    initPayload = serializers.CharField(required=False)
    mainColor = serializers.CharField(default="#00DED3")
    profileAvatar = AvatarImageField(required=False)
    openLauncherImage = OpenLauncherImageField(required=False)
    customCss = serializers.CharField(required=False, allow_blank=True)
    timeBetweenMessages = serializers.IntegerField(default=1)
    tooltipMessage = serializers.CharField(required=False)
    startFullScreen = serializers.BooleanField(default=False)
    showVoiceRecordingButton = serializers.BooleanField(default=False)
    showCameraButton = serializers.BooleanField(default=False)
    navigateIfSameDomain = serializers.BooleanField(default=False)
    embedded = serializers.BooleanField(default=False)
    contactTimeout = serializers.IntegerField(default=0)
    version = serializers.CharField(default="1")
    useConnectionOptimization = serializers.BooleanField(default=False)
    conversationStartersPDP = serializers.BooleanField(default=False)
    renderPercentage = serializers.IntegerField(
        required=False, min_value=0, max_value=100
    )
    voiceMode = serializers.JSONField(required=False)
    addToCart = serializers.BooleanField(default=False)

    @staticmethod
    def _is_stored_url(value):
        return isinstance(value, str) and value.startswith(("http://", "https://"))

    def _merge_with_existing_config(self, incoming_data):
        """Merge incoming PATCH data with existing config to preserve unset fields."""
        existing_config = self.app.config
        merged = {}
        for field_name in self.fields:
            if field_name in incoming_data:
                merged[field_name] = incoming_data[field_name]
            elif field_name in existing_config:
                merged[field_name] = existing_config[field_name]
        return merged

    def to_internal_value(self, data):
        self.app = self.parent.instance

        if self.app and self.app.config:
            data = self._merge_with_existing_config(data)

        data = super().to_internal_value(data)
        storage = AppStorage(self.app)

        # An empty string on these fields means "clear the value" — drop the
        # key so the stored config no longer keeps the previous URL.
        for clearable_field in ("profileAvatar", "openLauncherImage", "customCss"):
            if data.get(clearable_field) == "":
                data.pop(clearable_field)

        if data.get("profileAvatar"):
            avatar = data["profileAvatar"]
            if not isinstance(avatar, str):
                with storage.open(avatar.name, "w") as up_file:
                    up_file.write(avatar.file.read())
                    data["profileAvatar"] = storage.url(up_file.name)

        if data.get("openLauncherImage"):
            launcher = data["openLauncherImage"]
            if not isinstance(launcher, str):
                with storage.open(launcher.name, "w") as up_file:
                    up_file.write(launcher.file.read())
                    data["openLauncherImage"] = storage.url(up_file.name)

        if data.get("customCss"):
            custom_css = data["customCss"]
            if not self._is_stored_url(custom_css):
                with storage.open("custom.css", "w") as up_file:
                    up_file.write(custom_css)
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

        version = attrs.get("version", "2")
        if self.app.flow_object_uuid is None:
            self.app.flow_object_uuid = self._create_channel(version).get("uuid")

        flows_config = {
            "base_url": settings.SOCKET_BASE_URL,
            "version": version,
            "voice_mode": attrs.get("voiceMode", {}),
        }
        self._update_config(flows_config)
        self.app.configured = True

        attrs["socketUrl"] = settings.SOCKET_BASE_URL
        attrs["host"] = settings.FLOWS_HOST_URL
        attrs.pop("keepHistory")

        conversation_starters_pdp = attrs.pop("conversationStartersPDP")
        attrs["conversationStarters"] = {"pdp": conversation_starters_pdp}

        # Remove the apiKey from the generated script but keep it in attrs for storage
        script_attrs = copy.deepcopy(attrs)
        voice_mode = script_attrs.get("voiceMode", None)
        if voice_mode:
            eleven_labs = voice_mode.get("elevenLabs", None)
            if eleven_labs:
                eleven_labs.pop("apiKey", None)

        attrs["script"] = self.generate_script(script_attrs)

        return super().validate(attrs)

    def _create_channel(self, version: str) -> str:
        user = self.context.get("request").user
        name = f"{type_.WeniWebChatType.name} - #{self.app.id}"
        data = {"name": name, "base_url": settings.SOCKET_BASE_URL}
        client = FlowsClient()
        return client.create_channel(
            user.email, self.app.project_uuid, data, self.app.flows_type_code
        )

    def _update_config(self, config: dict):
        client = FlowsClient()
        response = client.update_config(config, self.app.flow_object_uuid)
        response.raise_for_status()

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
