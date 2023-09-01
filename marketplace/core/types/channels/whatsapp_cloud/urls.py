from django.urls import path

from .views import CatalogViewSet, ProductFeedViewSet


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
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/product_feeds/",
        ProductFeedViewSet.as_view({"post": "create", "get": "list"}),
        name="product-feed-list-create",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/product_feeds/<uuid:feed_uuid>/",
        ProductFeedViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="product-feed-detail-destroy",
    ),
    path(
        "<uuid:app_uuid>/catalogs/<uuid:catalog_uuid>/product_feeds/<uuid:feed_uuid>/products/",
        ProductFeedViewSet.as_view({"get": "list_products"}),
        name="product-feed-products-list",
    ),
]
