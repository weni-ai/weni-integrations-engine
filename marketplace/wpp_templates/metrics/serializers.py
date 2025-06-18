from rest_framework import serializers


class TemplateVersionDataSerializer(serializers.Serializer):
    end = serializers.DateField(required=True)
    start = serializers.DateField(required=True)
    template_versions = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )

    def validate(self, data):
        if data["end"] <= data["start"]:
            raise serializers.ValidationError(
                "End datetime must be after start datetime."
            )
        if not data["template_versions"]:
            raise serializers.ValidationError(
                "At least one template version is required."
            )
        return data
