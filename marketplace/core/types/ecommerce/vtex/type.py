from ..base import EcommerceAppType
from .views import VtexViewSet


class VtexType(EcommerceAppType):
    view_class = VtexViewSet
    code = "vtex"
    flows_type_code = None
    name = "Vtex"
    description = "vtex.data.description"
    summary = "vtex.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = "pre-popup"
