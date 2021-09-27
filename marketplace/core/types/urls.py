from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types

urlpatterns = []

for type_ in types.get_types():
    router = routers.SimpleRouter()

    if type_.view_class is None:
        continue

    router.register("apps", type_.view_class, basename=f"{type_.code}-app")

    urlpatterns.append(path(f"apptypes/{type_.code}/", include(router.urls)))
