from .views import GenericChannelViewSet

from marketplace.core.types.base import AppType, GenericAppType


class GenericChannelAppType(GenericAppType):
    view_class = GenericChannelViewSet
    category = AppType.CATEGORY_CHANNEL
    code = "generic"
