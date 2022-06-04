from marketplace.core.types import views
from .serializers import WhatsAppCloudSerializer
from ..whatsapp_base import mixins


class WhatsAppCloudViewSet(views.BaseAppTypeViewSet, mixins.WhatsAppConversationsMixin):

    serializer_class = WhatsAppCloudSerializer
    profile_api_class = None  # TODO: Make a OnPremiseBusinessProfileAPI
