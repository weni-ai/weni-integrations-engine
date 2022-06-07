from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from marketplace.core.types import views
from .serializers import WhatsAppCloudSerializer
from ..whatsapp_base import mixins
from .facades import CloudProfileFacade, CloudProfileContactFacade


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):

    serializer_class = WhatsAppCloudSerializer

    business_profile_class = CloudProfileContactFacade
    profile_class = CloudProfileFacade

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def destroy(self, request, *args, **kwargs) -> Response:
        return Response("This channel cannot be deleted", status=status.HTTP_403_FORBIDDEN)

    @property
    def profile_config_credentials(self) -> dict:
        config = self.get_object().config
        phone_numbrer_id = config.get("phone_number_id", None)

        if phone_numbrer_id is None:
            raise ValidationError("The phone number is not configured")

        return dict(phone_number_id=phone_numbrer_id)
