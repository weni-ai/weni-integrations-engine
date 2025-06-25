from django.urls import path

from marketplace.core.types.channels.facebook.views import FacebookSearchProductsView


urlpatterns = [
    path(
        "facebook/products/search/",
        FacebookSearchProductsView.as_view(),
        name="facebook-search-products",
    ),
]
