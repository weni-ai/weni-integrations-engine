from django.urls import path

from .views import VtexIntegrationDetailsView, VtexSyncOnDemandView


urlpatterns = [
    path(
        "integration-details/<uuid:project_uuid>",
        VtexIntegrationDetailsView.as_view(),
        name="integration-details",
    ),
    path(
        "sync-on-demand/<uuid:project_uuid>/",
        VtexSyncOnDemandView.as_view(),
        name="sync-on-demand",
    ),
]
