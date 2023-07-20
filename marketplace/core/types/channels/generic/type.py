from .views import GenericChannelViewSet

from marketplace.core.types.base import AppType, GenericAppType
from marketplace.core.types.channels.generic.views import (
    DetailChannelType,
    GetIcons,
    GenericAppTypes,
)


class GenericChannelAppType(GenericAppType):
    view_class = GenericChannelViewSet
    category = AppType.CATEGORY_CHANNEL
    code = "generic"

    EXTRA_VIEWS = [
        ("detail", DetailChannelType, "channels-detail"),
        ("icons", GetIcons, "channels-icons"),
        ("types", GenericAppTypes, "channels-types"),
    ]

    @classmethod
    def get_extra_urls(cls, router):
        for route, view, basename in cls.EXTRA_VIEWS:
            router.register(route, view, basename=basename)
