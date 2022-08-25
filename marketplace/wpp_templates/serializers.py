import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from .models import TemplateMessage, TemplateTranslation
from .requests import TemplateMessageRequest

User = get_user_model()


class TemplateTranslationSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    status = serializers.CharField()
    language = serializers.CharField()
    country = serializers.CharField()


class TemplateTranslationCreateSerializer(serializers.Serializer):
    translations = TemplateTranslationSerializer(many=True)
    template_uuid = serializers.CharField()
    template = SlugRelatedField(slug_field="uuid", queryset=TemplateMessage.objects.all())

    def create(self, validated_data: dict) -> object:
        translations = list()

        for translaction in validated_data.get("translations", []):
            translations.append(TemplateTranslation(
                template=validated_data.get("template"),
                status=translaction.get("status"),
                language=translaction.get("language"),
                country=translaction.get("country"),
                variable_count=0,
            ))

        TemplateTranslation.objects.bulk_create(translations)
        return dict(success=True)


class TemplateQuerySetSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    created_on = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    template_type = serializers.CharField(required=False)


class TemplateMessageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    waba_id = serializers.CharField(write_only=True)
    name = serializers.CharField()
    created_on = serializers.CharField(read_only=True)
    category = serializers.CharField()
    template_type = serializers.CharField()
    namespace = serializers.CharField()

    text_preview = serializers.CharField(required=False)

    translations = TemplateTranslationSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.translations.first():
            data['text_preview'] = instance.translations.first().body
        return data

    def create(self, validated_data: dict) -> TemplateMessage:
        template_message_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        template_message_request.create_template_message(
            waba_id=validated_data.get("waba_id"),
            name=validated_data.get("name"),
            category=validated_data.get("category"),
            components=list(),
            language="pt_br",
        )

        return TemplateMessage.objects.create(
            name=validated_data.get("name"),
            category=validated_data.get("category"),
            created_on=datetime.now(),
            template_type=validated_data.get("template_type"),
            namespace=validated_data.get("namespace"),
            code="wwc",
            project_uuid=uuid.uuid4(),
            created_by_id=User.objects.get_admin_user().id,
        )
