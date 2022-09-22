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


class HeaderSerializer(serializers.ModelSerializer):
    media = serializers.CharField(required=False)

    class Meta:
        model = TemplateHeader
        fields = ["header_type", "text", "media"]

class ButtonSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    url = serializers.CharField(required=False)

    class Meta:
        model = TemplateButton
        fields = ["button_type", "text", "country_code", "phone_number", "url"]

class TemplateTranslationSerializer(serializers.Serializer):
    template_uuid = serializers.CharField(write_only=True)
    #template = SlugRelatedField(slug_field="uuid", queryset=TemplateMessage.objects.all(), write_only=True)

    uuid = serializers.UUIDField(read_only=True)
    #status = serializers.CharField()
    language = serializers.CharField()
    country = serializers.CharField(required=False)
    header = HeaderSerializer(required=False)
    body = serializers.JSONField(required=False)
    footer = serializers.JSONField(required=False)
    buttons = ButtonSerializer(many=True, required=False)
    variable_count = serializers.IntegerField(read_only=True)

    def append_to_components(self, components: list() = [], component = None):
        if component:
            components.append(dict(component))

        return components
        

    def create(self, validated_data: dict) -> None:
        template_message_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        template = TemplateMessage.objects.get(uuid=validated_data.get("template_uuid"))

        components = [validated_data.get("body", {})]
        components = self.append_to_components(components, validated_data.get("header"))
        components = self.append_to_components(components, validated_data.get("footer"))
        #components.update(validated_data.get("buttons", dict()))

        buttons = validated_data.get("buttons", {})

        buttons_component = {
            "type": "BUTTONS",
            "buttons": [],
        }

        for button in buttons:
            button = dict(button)
            button["type"] = button.get("button_type")
            if button.get("phone_number"):
                button["phone_number"] = f'+{button.get("country_code")} {button.get("phone_number")}'
            
            if button.get("button_type") != "URL":
                buttons_component.get("buttons").append(button)


        if buttons_component.get("buttons"):
            components = self.append_to_components(components, buttons_component)

        #print(type(components))

        template_message_request.create_template_message(
            waba_id=template.app.config.get("wa_waba_id"),
            #waba_id="109552365187427",
            name=template.name,
            category=template.category,
            components=components,
            language=validated_data.get("language"),
        )

        translation = TemplateTranslation.objects.create(
            template=template,
            status="PENDING",
            body=validated_data.get("body"),
            language=validated_data.get("language"),
            country=validated_data.get("country", "Brasil"),
            variable_count=0,
        )

        for button in buttons:
            button = dict(button)
            TemplateButton.objects.create(translation=translation, **button)

        if validated_data.get("header"):
            TemplateHeader.objects.create(translation=translation, **dict(validated_data.get("header")))

        return translation



class TemplateTranslationCreateSerializer(serializers.Serializer):
    #translations = TemplateTranslationSerializer(many=True)
    template_uuid = serializers.CharField()
    template = SlugRelatedField(slug_field="uuid", queryset=TemplateMessage.objects.all())

    def create(self, validated_data: dict) -> object:
        return dict(success=True)


class TemplateQuerySetSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    created_on = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    template_type = serializers.CharField(required=False)


class TemplateMessageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    created_on = serializers.CharField(read_only=True)
    category = serializers.CharField()

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