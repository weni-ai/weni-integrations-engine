from marketplace.core.serializers import AppTypeBaseSerializer
from marketplace.applications.models import App
from marketplace.core.types.emails.base_serializer import BaseEmailSerializer


class GenericEmailSerializer(BaseEmailSerializer):
    pass


class EmailConfigureSerializer(AppTypeBaseSerializer):
    config = GenericEmailSerializer(write_only=True)

    class Meta:
        model = App
        fields = ("uuid", "config", "modified_by")
