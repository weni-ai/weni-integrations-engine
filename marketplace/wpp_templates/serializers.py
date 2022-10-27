import requests
import uuid
import json
import re
import base64
from datetime import datetime

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from marketplace.applications.models import App

from .models import TemplateMessage, TemplateTranslation, TemplateButton, TemplateHeader
from .requests import TemplateMessageRequest
from marketplace.core.types.channels.whatsapp_cloud.requests import PhotoAPIRequest
from marketplace.core.types.channels.whatsapp_base.exceptions import FacebookApiException

User = get_user_model()


class HeaderSerializer(serializers.ModelSerializer):
    text = serializers.CharField(required=False)
    #example = serializers.CharField(required=False)
    media = serializers.CharField(required=False)

    """
    def to_internal_value(self, data):
        data["media"] = data.get("example")

        if data.get("example"):
            data.pop("example")
        
        return data
    """
    
    def create(self, validated_data: dict) -> None:
        header = validated_data

        if header.get("header_type") in ["IMAGE", "DOCUMENT", "VIDEO"]:
            photo_api_request = PhotoAPIRequest(template.app.config.get("wa_waba_id"))

            photo = header.get("example")

            file_type = re.search('(?<=data:)(.*)(?=;base64)', photo).group(0)

            photo = photo.split(";base64,")[1]

            upload_session_id = photo_api_request.create_upload_session(
                settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN, len(base64.b64decode(photo)), file_type=file_type
            )

            url = f"https://graph.facebook.com/v14.0/{upload_session_id}"
            headers = {"Content-Type": file_type, "Authorization": f"OAuth {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"}
            headers["file_offset"] = "0"
            response = requests.post(url, headers=headers, data=base64.b64decode(photo))

            if response.status_code != 200:
                raise FacebookApiException(response.json())

            upload_handle = response.json().get("h", "")


            header.pop("example")

            header["example"] = dict(header_handle=upload_handle)

        #header["format"] = header.get("header_type", "TEXT")

        return object()
    #print("=====================")

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

    uuid = serializers.UUIDField(read_only=True)
    status = serializers.CharField(required=False)
    language = serializers.CharField()
    country = serializers.CharField(required=False)
    header = HeaderSerializer(required=False)
    body = serializers.JSONField(required=False)
    footer = serializers.JSONField(required=False)
    buttons = ButtonSerializer(many=True, required=False)
    variable_count = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.headers.first():
            data['header'] = instance.headers.first().to_dict()
        return data

    def append_to_components(self, components: list() = [], component = None):
        if component:
            components.append(dict(component))

        return components

    def create(self, validated_data: dict) -> None:
        template_message_request = TemplateMessageRequest(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        template = TemplateMessage.objects.get(uuid=validated_data.get("template_uuid"))

        components = [validated_data.get("body", {})]

        if validated_data.get("header"):
            header = HeaderSerializer(data=validated_data.get("header"))
            header.is_valid()
            header.save()
            #print(header)


        #return object()

        """
        if header:
            header = dict(header)
            header["type"] = "HEADER"
            header["format"] = header.get("header_type", "TEXT")
            header.pop("header_type")

            if header.get("format") == "IMAGE" or header.get("format") == "DOCUMENT" or header.get("format") == "VIDEO":
                photo_api_request = PhotoAPIRequest(template.app.config.get("wa_waba_id"))

                photo = header.get("example")

                file_type = re.search('(?<=data:)(.*)(?=;base64)', photo).group(0)

                photo = photo.split(";base64,")[1]
                
                upload_session_id = photo_api_request.create_upload_session(
                    settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN, len(base64.b64decode(photo)), file_type=file_type
                )
                
                url = f"https://graph.facebook.com/v14.0/{upload_session_id}"
                headers = {"Content-Type": file_type, "Authorization": f"OAuth {settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN}"}
                headers["file_offset"] = "0"
                response = requests.post(url, headers=headers, data=base64.b64decode(photo))

                if response.status_code != 200:
                    raise FacebookApiException(response.json())

                upload_handle = response.json().get("h", "")


                header.pop("example")

                header["example"] = dict(header_handle=upload_handle)
        """
        #print(header)

        #components = self.append_to_components(components, header)
        components = self.append_to_components(components, validated_data.get("footer"))

        buttons = validated_data.get("buttons", {})

        buttons_component = {
            "type": "BUTTONS",
            "buttons": [],
        }

        url_component = {
            "type": "URL",
        }

        for button in buttons:
            button = dict(button)
            button["type"] = button.get("button_type")
            if button.get("phone_number"):
                button["phone_number"] = f'+{button.get("country_code")} {button.get("phone_number")}'
            
            button_component = button
            button_component.pop("button_type")

            if button_component.get("country_code"):
                button_component.pop("country_code")

            buttons_component.get("buttons").append(button_component)

        if buttons_component.get("buttons"):
            components = self.append_to_components(components, buttons_component)

        template_message_request.create_template_message(
            waba_id=template.app.config.get("wa_waba_id"),
            name=template.name,
            category=template.category,
            components=components,
            language=validated_data.get("language"),
        )

        translation = TemplateTranslation.objects.create(
            template=template,
            status="PENDING",
            body=validated_data.get("body", {}).get("text", ""),
            footer=validated_data.get("footer", {}).get("text", ""),
            language=validated_data.get("language"),
            country=validated_data.get("country", "Brasil"),
            variable_count=0,
        )

        for button in buttons:
            button = dict(button)
            TemplateButton.objects.create(translation=translation, **button)

        if validated_data.get("header"):
            hh = dict(validated_data.get("header"))
            if hh.get("example"):
                hh.pop("media")
                hh.pop("example")
            
            #TemplateHeader.objects.create(translation=translation, **hh)

        return translation
        


class TemplateTranslationCreateSerializer(serializers.Serializer):
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

    def validate_name(self, name):
        if bool(re.match("\w*[A-Z]\w*", name)) or " " in name:
            raise serializers.ValidationError("WhatsApp.templates.error.invalid_name_format")

        return name

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
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
        )
