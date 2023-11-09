from ..base import ExternalAppType
from .views import VtexViewSet


class VtexType(ExternalAppType):
    view_class = VtexViewSet
    code = "vtex"
    flows_type_code = None
    name = "Vtex"
    description = "vtex.data.description"
    summary = "vtex.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = ""
