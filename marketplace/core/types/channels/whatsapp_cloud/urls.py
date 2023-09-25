from django.urls import path

from .views import CatalogViewSet


urlpatterns = [
    path(
        "<uuid:app_uuid>/catalogs/",
        CatalogViewSet.as_view({"post": "create", "get": "list"}),
        name="catalog-list-create",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/",
        CatalogViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="catalog-detail-destroy",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/products/",
        CatalogViewSet.as_view({"get": "list_products"}),
        name="catalog-products-list",
    ),
    path(
        "<uuid:app_uuid>/catalogs/active/",
        CatalogViewSet.as_view({"get": "get_active_catalog"}),
        name="catalog-active",
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
    path(
        "<uuid:app_uuid>/commerce-settings/",
        CatalogViewSet.as_view({"get": "commerce_settings_status"}),
        name="commerce-settings-status",
    ),
    path(
        "<uuid:app_uuid>/toggle-catalog-visibility/",
        CatalogViewSet.as_view({"post": "toggle_catalog_visibility"}),
        name="toggle-catalog-visibility",
    ),
    path(
        "<uuid:app_uuid>/toggle-cart-visibility/",
        CatalogViewSet.as_view({"post": "toggle_cart_visibility"}),
        name="toggle-cart-visibility",
    ),
]
