from datetime import date
from uuid import uuid4

from django.test import SimpleTestCase
from rest_framework import serializers

from marketplace.wpp_templates.metrics.serializers import TemplateVersionDataSerializer


class TestTemplateVersionDataSerializer(SimpleTestCase):
    """Unit tests for TemplateVersionDataSerializer validation rules."""

    def test_validate_success(self):
        """Valid payload should pass is_valid() and return validated data."""
        payload = {
            "start": date(2024, 1, 1),
            "end": date(2024, 1, 2),
            "template_versions": [str(uuid4())],
        }
        ser = TemplateVersionDataSerializer(data=payload)
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data["start"], payload["start"])
        self.assertEqual(ser.validated_data["end"], payload["end"])
        self.assertEqual(len(ser.validated_data["template_versions"]), 1)

    def test_validate_end_before_start_raises(self):
        """When end < start, serializer must raise ValidationError."""
        payload = {
            "start": date(2024, 1, 2),
            "end": date(2024, 1, 1),
            "template_versions": [str(uuid4())],
        }
        ser = TemplateVersionDataSerializer(data=payload)
        self.assertFalse(ser.is_valid())
        self.assertIn("End datetime must be after start datetime.", str(ser.errors))

    def test_validate_empty_template_versions_branch(self):
        """
        Cover the custom branch that checks for empty template_versions.

        Note: ListField has allow_empty=False, which would normally fail field-level
        validation before reaching .validate(). To cover our custom message,
        call .validate() directly.
        """
        payload = {
            "start": date(2024, 1, 1),
            "end": date(2024, 1, 2),
            "template_versions": [],
        }
        ser = TemplateVersionDataSerializer()
        with self.assertRaises(serializers.ValidationError):
            ser.validate(payload)
