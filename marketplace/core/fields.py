import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class Base64ImageField(serializers.ImageField):
    def get_file_name(self, extencion: str) -> str:
        return f"{uuid.uuid4()}.{extencion}"

    def _decode(self, data):
        if not isinstance(data, str) or not data.startswith("data:"):
            raise ValidationError

        # base64 encoded file - decode
        try:
            header, b64_encoded = data.split(";base64,")
        except ValueError:
            raise ValidationError

        extencion = header.split("/")[-1]

        try:
            return ContentFile(
                base64.b64decode(b64_encoded), name=self.get_file_name(extencion)
            )
        except binascii.Error:
            raise ValidationError

    def to_internal_value(self, data):
        return super().to_internal_value(self._decode(data))
