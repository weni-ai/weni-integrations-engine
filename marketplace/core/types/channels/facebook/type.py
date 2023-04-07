from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from . import views


class FacebookType(AppType):
    view_class = views.FacebookViewSet

    code = "fba"
    channeltype_code = "FBA"
    name = "Facebook"
    description = "facebook.data.description"
    summary = "facebook.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#039be533"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "sidebar"
