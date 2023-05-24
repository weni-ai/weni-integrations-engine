from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import GenericChannelViewSet


class GenericType(AppType):
    view_class = GenericChannelViewSet
    code = "generic"
    flows_type_code = None
    name = "Generic Type"
    description = "Generic.data.description"
    summary = "Generic.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"
