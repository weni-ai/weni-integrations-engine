from rest_framework import serializers

from marketplace.core.types.channels.whatsapp_base.mixins import QueryParamsParser


class AnalyticsSerializer(serializers.Serializer):
    start = serializers.CharField(required=True)
    end = serializers.CharField(required=True)
    fba_template_ids = serializers.ListField(required=True)

    def validate(self, data):
        parse_data = QueryParamsParser(data)

        data["start"] = parse_data.start
        data["end"] = parse_data.end

        if data["start"] >= data["end"]:
            raise serializers.ValidationError(
                "End date must occur after the start date"
            )

        return data
