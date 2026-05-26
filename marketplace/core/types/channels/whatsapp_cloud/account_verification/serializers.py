"""Serializers for the Account Verification API."""

from rest_framework import serializers

from .constants import (
    ALLOWED_DOCUMENT_CONTENT_TYPES,
    MAX_DOCUMENT_SIZE_BYTES,
    MAX_DOCUMENTS,
)


class AccountVerificationDocumentField(serializers.FileField):
    """File field that enforces Meta's size and content-type constraints."""

    def to_internal_value(self, data):
        uploaded = super().to_internal_value(data)
        if uploaded.size > MAX_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError(
                f"Document '{uploaded.name}' exceeds the 5MB size limit."
            )
        if uploaded.content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
            raise serializers.ValidationError(
                f"Document '{uploaded.name}' has an unsupported content type "
                f"'{uploaded.content_type}'. Allowed: PDF, JPEG, JPG, PNG."
            )
        return uploaded


class SubmitAccountVerificationSerializer(serializers.Serializer):
    """Input serializer for the submit endpoint (multipart/form-data)."""

    documents = serializers.ListField(
        child=AccountVerificationDocumentField(),
        min_length=1,
        max_length=MAX_DOCUMENTS,
        allow_empty=False,
    )


class AccountVerificationStateSerializer(serializers.Serializer):
    """Output serializer mirroring AccountVerificationStateDTO."""

    ui_state = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    submission_id = serializers.CharField(allow_null=True)
    verification_attempts = serializers.IntegerField()
    rejection_reasons = serializers.ListField(child=serializers.CharField())
    submitted_at = serializers.CharField(allow_null=True)
    updated_at_meta = serializers.CharField(allow_null=True)
    last_synced_at = serializers.CharField(allow_null=True)
    can_submit = serializers.BooleanField()
