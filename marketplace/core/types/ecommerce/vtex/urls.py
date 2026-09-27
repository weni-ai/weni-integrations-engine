from django.urls import path

from .views import (
    VtexIntegrationDetailsView,
    VtexSyncOnDemandInlineView,
    VtexSyncOnDemandView,
    VtexUploadInlineProductsView,
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
    path(
        "upload-inline-products/",
        VtexUploadInlineProductsView.as_view(),
        name="upload-inline-products",
    ),
]
