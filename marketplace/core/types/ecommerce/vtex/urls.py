from django.urls import path

from .views import (
    VtexIntegrationDetailsView,
    VtexSyncOnDemandInlineView,
    VtexSyncOnDemandView,
)


urlpatterns = [
    path(
        "integration-details/<uuid:project_uuid>",
        VtexIntegrationDetailsView.as_view(),
        name="integration-details",
    ),
    path(
        "sync-on-demand/",
        VtexSyncOnDemandView.as_view(),
        name="sync-on-demand",
    ),
    path(
        "sync-on-demand-inline/",
        VtexSyncOnDemandInlineView.as_view(),
        name="sync-on-demand-inline",
    ),
]
