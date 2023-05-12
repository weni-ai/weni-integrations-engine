from marketplace.core.types.externals.base import ExternalAppType
from .views import GenericExternalsViewSet


class GenericType(ExternalAppType):
    view_class = GenericExternalsViewSet
    code = "generic-ext"
    channeltype_code = None
    name = "Generic External"
    description = "generic.data.description"
    summary = "generic.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = ""
