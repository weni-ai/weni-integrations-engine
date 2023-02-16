from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import WhatsAppCloudViewSet


class WhatsAppCloudType(AppType):

    view_class = WhatsAppCloudViewSet

    code = "wpp-cloud"
    channeltype_code = "WAC"
    name = "WhatsApp"
    description = "WhatsAppCloud.data.description"
    summary = "WhatsAppCloud.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"  # TODO: Change to real color
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"
