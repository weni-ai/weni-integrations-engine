from marketplace.core.types import views
from .serializers import WhatsAppCloudSerializer
from ..whatsapp_base import mixins


class WhatsAppCloudViewSet(
    views.BaseAppTypeViewSet,
    mixins.WhatsAppConversationsMixin,
    mixins.WhatsAppContactMixin,
    mixins.WhatsAppProfileMixin,
):

    serializer_class = WhatsAppCloudSerializer
    business_profile_class = None
    profile_class = None
