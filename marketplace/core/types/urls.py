from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types

urlpatterns = []


for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()
    if apptype.view_class is None:
        continue

    router.register("apps", apptype.view_class, basename=f"{apptype.code}-app")
    urlpatterns.append(path(f"apptypes/{apptype.code}/", include(router.urls)))

urlpatterns.append(
    path("apptypes/generic/", include("marketplace.core.types.channels.generic.urls")),
)
urlpatterns.append(
    path(
        "apptypes/wpp-cloud/",
        include("marketplace.core.types.channels.whatsapp_cloud.urls"),
    ),
)
