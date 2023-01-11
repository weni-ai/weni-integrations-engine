from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from . import views


class InstagramType(AppType):
    view_class = views.InstagramViewSet

    code = "ig"
    channeltype_code = "IG"
    name = "Instagram"
    description = "instagram.data.description"
    summary = "instagram.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#039be533"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "sidebar"
    channels_available = None
