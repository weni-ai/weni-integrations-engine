from django.urls import path

from marketplace.core.types.channels.whatsapp_cloud.catalogs.views.view import (
    CatalogViewSet,
    CommerceSettingsViewSet,
)


catalog_patterns = [
    path(
        "<uuid:app_uuid>/catalogs/",
        CatalogViewSet.as_view({"get": "list"}),
        name="catalog-list",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/",
        CatalogViewSet.as_view({"get": "retrieve"}),
        name="catalog-detail",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/enable/",
        CatalogViewSet.as_view({"post": "enable_catalog"}),
        name="catalog-enable",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/disable/",
        CatalogViewSet.as_view({"post": "disable_catalog"}),
        name="catalog-disable",
    ),
]

commerce_settings_patterns = [
    path(
        "<uuid:app_uuid>/commerce-settings/",
        CommerceSettingsViewSet.as_view({"get": "commerce_settings_status"}),
        name="commerce-settings-status",
    ),
    path(
        "<uuid:app_uuid>/toggle-catalog-visibility/",
        CommerceSettingsViewSet.as_view({"post": "toggle_catalog_visibility"}),
        name="toggle-catalog-visibility",
    ),
    path(
        "<uuid:app_uuid>/toggle-cart-visibility/",
        CommerceSettingsViewSet.as_view({"post": "toggle_cart_visibility"}),
        name="toggle-cart-visibility",
    ),
    path(
        "<uuid:app_uuid>/catalogs/active/",
        CommerceSettingsViewSet.as_view({"get": "get_active_catalog"}),
        name="catalog-active",
    ),
]

urlpatterns = catalog_patterns + commerce_settings_patterns
