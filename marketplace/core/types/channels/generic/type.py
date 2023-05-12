from marketplace.applications.models import App
from .views import GenericChannelViewSet

from marketplace.core.types.base import AppType, GenericAppType


class GenericType(GenericAppType):
    view_class = GenericChannelViewSet
    category = AppType.CATEGORY_CHANNEL
    platform = App.PLATFORM_WENI_FLOWS
