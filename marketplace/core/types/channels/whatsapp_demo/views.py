from rest_framework import viewsets
from marketplace.applications.models import App

from marketplace.core.types.views import BaseAppTypeViewSet


class WhatsAppDemoViewSet(BaseAppTypeViewSet):

    serializer_class = None
