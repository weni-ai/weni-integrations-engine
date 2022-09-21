import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from marketplace.applications.models import App

from .models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader
from .requests import TemplateMessageRequest

User = get_user_model()


class HeaderSerializer(serializers.Serializer):
    class Meta:
        model = TemplateHeader
        fields = '__all__'

class ButtonSerializer(serializers.Serializer):
    class Meta:
        model = TemplateButton
        fields = '__all__'

class TemplateTranslationSerializer(serializers.Serializer):
    template_uuid = serializers.CharField(write_only=True)
    #template = SlugRelatedField(slug_field="uuid", queryset=TemplateMessage.objects.all(), write_only=True)

    uuid = serializers.UUIDField(read_only=True)
    #status = serializers.CharField()
    language = serializers.CharField()
    country = serializers.CharField()
    header = HeaderSerializer(required=False)
    body = serializers.JSONField(required=False)
    footer = serializers.CharField(required=False)
    buttons = ButtonSerializer(many=True, required=False)
    variable_count = serializers.IntegerField(read_only=True)


    def create(self, validated_data: dict) -> None:
        template_message_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        template = TemplateMessage.objects.get(uuid=validated_data.get("template_uuid"))
        
        print(validated_data.get("buttons"))

        template_message_request.create_template_message(
            waba_id=template.app.config.get("waba_id"),
            name=template.name,
            category=template.category,
            components=list(),
            language=validated_data.get("language"),
        )

        template = TemplateTranslation.objects.create(
            template=template,
            status="PENDING",
            language=validated_data.get("language"),
            country=validated_data.get("country"),
            variable_count=0,
        )

        return template


class ButtonSerializer(serializers.Serializer):
    ...


class TemplateTranslationCreateSerializer(serializers.Serializer):
    #translations = TemplateTranslationSerializer(many=True)
    template_uuid = serializers.CharField()
    template = SlugRelatedField(slug_field="uuid", queryset=TemplateMessage.objects.all())

    def create(self, validated_data: dict) -> object:
        #translations = list()
        #print(validated_data)

        """
        for translaction in validated_data.get("translations", []):
            translations.append(TemplateTranslation(
                template=validated_data.get("template"),
                status=translaction.get("status"),
                language=translaction.get("language"),
                #country=translaction.get("country"),
                variable_count=0,
            ))
        """
        """
        TemplateTranslation.objects.create(
            template=validated_data.get("template"),
            status=validated_data.get("status"),
            language=validated_data.get("language"),
            #country=translaction.get("country"),
            variable_count=0,
        )
        """

        #print(validated_data.get("template"))

        #emplateTranslation.objects.bulk_create(translations)
        return dict(success=True)


class TemplateQuerySetSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    created_on = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    template_type = serializers.CharField(required=False)


class TemplateMessageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    #waba_id = serializers.CharField(write_only=True)
    name = serializers.CharField()
    created_on = serializers.CharField(read_only=True)
    category = serializers.CharField()
    #template_type = serializers.CharField()
    #namespace = serializers.CharField()

    app_uuid = serializers.CharField(write_only=True)

    text_preview = serializers.CharField(required=False, read_only=True)

    translations = TemplateTranslationSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.translations.first():
            data['text_preview'] = instance.translations.first().body
        return data

    def create(self, validated_data: dict) -> TemplateMessage:
        app = App.objects.get(uuid=validated_data.get("app_uuid"))

        return TemplateMessage.objects.create(
            name=validated_data.get("name"),
            app=app,
            category=validated_data.get("category"),
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )