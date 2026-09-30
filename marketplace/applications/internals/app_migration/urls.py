from django.urls import path

from marketplace.applications.internals.app_migration import views

urlpatterns = [
    path(
        "app-migrations",
        views.AppMigrationCreateView.as_view(),
        name="internal-app-migration-create",
    ),
    path(
        "app-migrations/<uuid:event_id>",
        views.AppMigrationDetailView.as_view(),
        name="internal-app-migration-detail",
    ),
    path(
        "app-migrations/<uuid:event_id>/status",
        views.AppMigrationStatusView.as_view(),
        name="internal-app-migration-status",
    ),
    path(
        "app-migrations/<uuid:event_id>/republish",
        views.AppMigrationRepublishView.as_view(),
        name="internal-app-migration-republish",
    ),
]
