from django.urls import path

from .views import VtexIntegrationDetailsView


urlpatterns = [
    path(
        "integration-details/<uuid:project_uuid>",
        VtexIntegrationDetailsView.as_view(),
        name="integration-details",
    ),
]
