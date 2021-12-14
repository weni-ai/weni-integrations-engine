from marketplace.core.types.base import AppType
from marketplace.applications.models import App

from .views import WhatsAppDemoViewSet


class WhatsAppDemoType(AppType):
    view_class = WhatsAppDemoViewSet

    code = "wpp-demo"
    channeltype_code = None
    name = "WhatsApp Demo"
    description = "WhatsAppDemo.data.description"
    summary = "WhatsAppDemo.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#00DED333"
    platform = App.PLATFORM_WENI_FLOWS
