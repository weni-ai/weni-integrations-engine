from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions


view = get_schema_view(
    openapi.Info(
        title="Integrations API Documentation",
        default_version="v2.0.7",
        desccription="Documentation of the Integrations APIs",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
).with_ui("swagger")
