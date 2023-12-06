from django.urls import path
from .product_updates import VtexProductUpdateWebhook

urlpatterns = [
    path(
        "vtex/<uuid:app_uuid>/products-update/api/notification/",
        VtexProductUpdateWebhook.as_view(),
        name="vtex-product-updates",
    ),
]
