from typing import TYPE_CHECKING

from marketplace.connect.client import ConnectProjectClient
from ..base import ExternalAppType
from .views import OmieViewSet


if TYPE_CHECKING:
    from marketplace.applications.models import App
    from django.contrib.auth import get_user_model
    User = get_user_model()


class OmieType(ExternalAppType):
    view_class = OmieViewSet

    code = "omie"
    channeltype_code = "omie" # TODO: rename this field to flows_type_code
    name = "Omie"
    description = "omie.data.description"
    summary = "omie.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = ""
    channels_available = None # TODO: This field is temporary, it needs to be removed in the future
