import re
import base64

from collections import Counter
from datetime import datetime
from typing import Any, List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework import serializers
from rest_framework.exceptions import APIException

from marketplace.applications.models import App
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import PhotoAPIService, TemplateService
from marketplace.wpp_templates.models import (
    TemplateButton,
    TemplateHeader,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.parameters import (
    PARAMETER_FORMAT_NAMED,
    build_named_example_payload,
    detect_authoring_format,
    extract_named_placeholders,
    extract_positional_placeholders,
    validate_parameter_name,
)
from marketplace.wpp_templates.template_helpers import extract_body_example

User = get_user_model()

_UNSUPPORTED_PARAMETER_FORMAT_MARKERS = (
    "unsupported",
    "not supported",
    "unknown field",
    "does not exist",
    "not a valid field",
    "unrecognized",
    "unrecognised",
)


def _authoring_named_example_map(body):
    example = (body or {}).get("example") or {}
    if not isinstance(example, dict):
        return {}
    entries = example.get("body_text_named_params") or []
    if not isinstance(entries, list):
        return {}
    lookup = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("param_name")
        if not name:
            continue
        lookup[name] = entry.get("example")
    return lookup


def _meta_error_text(detail) -> str:
    if isinstance(detail, dict):
        return " ".join(_meta_error_text(value) for value in detail.values())
    if isinstance(detail, (list, tuple)):
        return " ".join(_meta_error_text(item) for item in detail)
    return str(detail)


def _is_unsupported_parameter_format_error(exc: CustomAPIException) -> bool:
    text = _meta_error_text(exc.detail).lower()
    if "parameter_format" not in text:
        return False
    return any(marker in text for marker in _UNSUPPORTED_PARAMETER_FORMAT_MARKERS)


class HeaderSerializer(serializers.ModelSerializer):
    text = serializers.CharField(required=False)
    example = serializers.CharField(required=False)

    class Meta:
        model = TemplateHeader
        fields = ["header_type", "text", "example"]


class ButtonSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    url = serializers.CharField(required=False)
    example = serializers.ListField(required=False)
    payment_setting = serializers.JSONField(required=False)

    class Meta:
        model = TemplateButton
        fields = [
            "button_type",
            "text",
            "country_code",
            "phone_number",
            "url",
            "example",
            "payment_setting",
        ]


class TemplateTranslationSerializer(serializers.Serializer):
    template_uuid = serializers.CharField(write_only=True)
    uuid = serializers.UUIDField(read_only=True)
    message_template_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    language = serializers.CharField()
    country = serializers.CharField(required=False)
    header = HeaderSerializer(required=False)
    body = serializers.JSONField(required=False)
    body_example = serializers.ListField(read_only=True)
    footer = serializers.JSONField(required=False)
    buttons = ButtonSerializer(many=True, required=False)
    variable_count = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.headers.first():
            data["header"] = instance.headers.first().to_dict()

        return data

    def append_to_components(self, components: List[Any], component=None):
        if component:
            components.append(dict(component))

        return components

    def validate_body(self, body):
        if not isinstance(body, dict):
            return body
        text = body.get("text") or ""
        named = extract_named_placeholders(text)
        positional = extract_positional_placeholders(text)
        self._reject_mixed_parameter_formats(named, positional)
        if detect_authoring_format(text) != PARAMETER_FORMAT_NAMED:
            return body
        self._reject_named_when_flag_disabled()
        self._reject_duplicate_parameter_names(named)
        self._reject_invalid_parameter_names(named)
        self._reject_missing_named_examples(named, body)
        return body

    def _reject_mixed_parameter_formats(self, named, positional):
        if not (named and positional):
            return
        if len(named) <= len(positional):
            minority = named
        else:
            minority = positional
        joined = ", ".join(minority)
        raise serializers.ValidationError(
            f"A template uses one parameter format. Minority-format variables: {joined}."
        )

    def _reject_named_when_flag_disabled(self):
        if settings.WHATSAPP_NAMED_TEMPLATES_ENABLED:
            return
        raise serializers.ValidationError("Named templates are not enabled.")

    def _reject_duplicate_parameter_names(self, names):
        duplicated = sorted(name for name, count in Counter(names).items() if count > 1)
        if not duplicated:
            return
        joined = ", ".join(duplicated)
        raise serializers.ValidationError(
            f"Parameter name '{joined}' is duplicated. Each named parameter may appear only once."
        )

    def _reject_invalid_parameter_names(self, names):
        invalid = [name for name in names if not validate_parameter_name(name)]
        if not invalid:
            return
        raise serializers.ValidationError(
            f"Parameter name '{invalid[0]}' is invalid. Named parameters must match "
            "^[a-z_][a-z0-9_]*$ (start with a letter or underscore, then lowercase "
            "letters, digits or underscores)."
        )

    def _reject_missing_named_examples(self, names, body):
        example_map = _authoring_named_example_map(body)
        missing = [
            name
            for name in names
            if example_map.get(name) is None or example_map.get(name) == ""
        ]
        if not missing:
            return
        joined = ", ".join(missing)
        raise serializers.ValidationError(
            f"Named parameter '{joined}' has no example value."
        )

    def _reraise_meta_create_error(self, exc: CustomAPIException):
        if getattr(exc, "status_code", None) != 400:
            raise exc
        if _is_unsupported_parameter_format_error(exc):
            raise APIException(
                detail=(
                    "Named template authoring is not available: the configured Graph API "
                    "version does not support the parameter_format capability."
                )
            ) from exc
        raise serializers.ValidationError({"body": exc.detail}) from exc

    def create(self, validated_data: dict) -> None:
        template = TemplateMessage.objects.get(uuid=validated_data.get("template_uuid"))

        access_token = template.app.apptype.get_access_token(template.app)
        template_service = TemplateService(client=FacebookClient(access_token))

        body = validated_data.get("body") or {}
        body_text = body.get("text") or ""
        named_params = None
        if detect_authoring_format(body_text) == PARAMETER_FORMAT_NAMED:
            names = extract_named_placeholders(body_text)
            named_params = build_named_example_payload(
                names, _authoring_named_example_map(body)
            )
            example = dict(body.get("example") or {})
            example["body_text_named_params"] = named_params
            body = dict(body)
            body["example"] = example

        components = [body]
        header = validated_data.get("header")

        # Process Header
        if header:
            header = dict(header)
            header["type"] = "HEADER"
            header["format"] = header.get("header_type", "TEXT")
            header.pop("header_type")

            # Handle Media Uploads
            if header.get("format") in ["IMAGE", "DOCUMENT", "VIDEO"]:
                photo_api_request = PhotoAPIService(client=FacebookClient(access_token))
                photo = header.get("example")
                file_type = re.search("(?<=data:)(.*)(?=;base64)", photo).group(0)
                photo = photo.split(";base64,")[1]
                upload_session_id = photo_api_request.create_upload_session(
                    len(base64.b64decode(photo)),
                    file_type=file_type,
                )
                dict_response = photo_api_request.upload_session(
                    upload_session_id=upload_session_id,
                    file_type=file_type,
                    data=base64.b64decode(photo),
                )
                upload_handle = dict_response.get("h", "")
                header.pop("example")
                header["example"] = dict(header_handle=upload_handle)

        components = self.append_to_components(components, header)
        components = self.append_to_components(components, validated_data.get("footer"))
        buttons = validated_data.get("buttons", {})

        # Process Buttons
        buttons_component = {
            "type": "BUTTONS",
            "buttons": [],
        }

        for button in buttons:
            button = dict(button)
            button["type"] = button.get("button_type")

            if button.get("phone_number"):
                button[
                    "phone_number"
                ] = f'+{button.get("country_code")} {button.get("phone_number")}'

            button_component = button
            button_component.pop("button_type")

            if button_component.get("country_code"):
                button_component.pop("country_code")

            if button_component["type"] == "PAYMENT_REQUEST":
                meta_button = {
                    "type": "PAYMENT_REQUEST",
                    "text": button_component.get("text"),
                }
                if button_component.get("payment_setting"):
                    meta_button["payment_setting"] = button_component["payment_setting"]
                buttons_component.get("buttons").append(meta_button)
            else:
                buttons_component.get("buttons").append(button_component)

        if buttons_component.get("buttons"):
            components = self.append_to_components(components, buttons_component)

        waba_id = (
            template.app.config.get("wa_waba_id")
            if template.app.config.get("wa_waba_id")
            else template.app.config.get("waba").get("id")
        )

        create_kwargs = dict(
            waba_id=waba_id,
            name=template.name,
            category=template.category,
            components=components,
            language=validated_data.get("language"),
        )
        if named_params is not None:
            create_kwargs["parameter_format"] = "named"

        try:
            new_template = template_service.create_template_message(**create_kwargs)
        except CustomAPIException as exc:
            self._reraise_meta_create_error(exc)

        # Extract body example from body if available
        body_example = []
        if validated_data.get("body", {}).get("example"):
            body_example = extract_body_example(validated_data["body"]["example"])

        translation_fields = dict(
            template=template,
            status="PENDING",
            body=validated_data.get("body", {}).get("text", ""),
            body_example=body_example,
            footer=validated_data.get("footer", {}).get("text", ""),
            language=validated_data.get("language"),
            country=validated_data.get("country", "Brasil"),
            variable_count=0,
            message_template_id=new_template["id"],
        )
        if named_params is not None:
            translation_fields["parameter_format"] = PARAMETER_FORMAT_NAMED
            translation_fields["body_named_params"] = named_params
            translation_fields["variable_count"] = len(named_params)

        translation = TemplateTranslation.objects.create(**translation_fields)

        for button in buttons:
            button = dict(button)
            TemplateButton.objects.create(translation=translation, **button)

        if validated_data.get("header"):
            hh = dict(validated_data.get("header"))
            if hh.get("example"):
                hh.pop("example")
            TemplateHeader.objects.create(translation=translation, **hh)

        return translation


class TemplateMessageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    created_on = serializers.CharField(read_only=True)
    category = serializers.CharField()
    app_uuid = serializers.CharField(write_only=True)
    text_preview = serializers.CharField(required=False, read_only=True)
    translations = TemplateTranslationSerializer(many=True, read_only=True)
    gallery_version = serializers.UUIDField(required=False, allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.translations.first():
            data["text_preview"] = instance.translations.first().body
        return data

    def create(self, validated_data: dict) -> TemplateMessage:
        app = App.objects.get(uuid=validated_data.get("app_uuid"))

        template_message = TemplateMessage(
            name=validated_data.get("name"),
            app=app,
            category=validated_data.get("category"),
            created_on=datetime.now(),
            template_type="TEXT",
            created_by_id=User.objects.get_admin_user().id,
            gallery_version=validated_data.get("gallery_version"),
        )
        try:
            template_message.full_clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        template_message.save()
        return template_message
