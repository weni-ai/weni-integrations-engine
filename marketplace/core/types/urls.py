from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types
from marketplace.core.types.channels.generic.views import DetailChannelType
from marketplace.core.types.channels.generic.views import GetIcons
from marketplace.core.types.channels.generic.views import GenericAppTypes

urlpatterns = []


for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()
    if apptype.view_class is None:
        continue

    router.register("apps", apptype.view_class, basename=f"{apptype.code}-app")
    urlpatterns.append(path(f"apptypes/{apptype.code}/", include(router.urls)))

generic_router = routers.SimpleRouter()
generic_router.register("channel-type", DetailChannelType, basename="channel-type")
generic_router.register("get-icons", GetIcons, basename="get-icons")
generic_router.register("apptypes", GenericAppTypes, basename="my-apps")

urlpatterns.append(path("apptypes/generic/", include(generic_router.urls)))
