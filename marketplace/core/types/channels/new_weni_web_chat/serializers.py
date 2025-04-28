from rest_framework import serializers

from marketplace.core.fields import Base64ImageField
from marketplace.applications.models import App
from marketplace.core.serializers import AppTypeBaseSerializer


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


class NewWeniWebChatSerializer(AppTypeBaseSerializer):
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


class NewWeniWebChatConfigureSerializer(AppTypeBaseSerializer):
    config = ConfigSerializer(write_only=True)
    script = serializers.SerializerMethodField()

    def get_script(self, obj):
        return obj.config.get("script")

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by", "script")
