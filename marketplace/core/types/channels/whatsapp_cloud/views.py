from marketplace.core.types import views
from .serializers import WhatsAppCloudSerializer


class WhatsAppCloudViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppCloudSerializer
