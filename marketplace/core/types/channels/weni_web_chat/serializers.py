import os

from rest_framework import serializers
from django.core.files.storage import default_storage
from marketplace.core.fields import Base64ImageField

from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


class WeniWebChatSerializer(AppTypeBaseSerializer):
    class Meta:
        model = App
        fields = ("app_code", "uuid", "project_uuid", "platform", "config", "created_by", "created_on", "modified_by")
        read_only_fields = ("app_code", "uuid")


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
    # timeBetweenMessages = serializers.IntegerField(default=1)
    mainColor = serializers.CharField(default="#00DED3")
    avatarImage = AvatarBase64ImageField(required=True)  # TODO: Validate if "required" need be True
    customCss = serializers.CharField(required=False)

    def to_internal_value(self, data):
        from .type import WeniWebChatType

        data = super().to_internal_value(data)

        app = self.context["view"].get_object()
        files_path = f"AppType/{WeniWebChatType.code}/{app.pk}/"

        if data.get("avatarImage"):
            content_file = data["avatarImage"]

            with default_storage.open(os.path.join(files_path, content_file.name), "w") as up_file:
                up_file.write(content_file.file.read())
                data["avatarImage"] = default_storage.url(up_file.name)

        if data.get("customCss"):
            with default_storage.open(os.path.join(files_path, "custom.css"), "w") as up_file:
                up_file.write(data["customCss"])
                data["customCss"] = default_storage.url(up_file.name)

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

        attrs.pop("mainColor")
        attrs.pop("keepHistory")

        return super().validate(attrs)


class WeniWebChatConfigureSerializer(AppTypeBaseSerializer):

    config = ConfigSerializer()

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
