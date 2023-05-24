from ..base import ExternalAppType
from .views import OmieViewSet


class OmieType(ExternalAppType):
    view_class = OmieViewSet
    code = "omie"
    flows_type_code = "omie"
    name = "Omie"
    description = "omie.data.description"
    summary = "omie.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = ""
