import re

from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.contrib.auth.models import Group
from django.urls.conf import include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from marketplace.swagger import view as swagger_view
from marketplace.applications import urls as applications_urls
from marketplace.interactions import urls as interactions_urls
from marketplace.webhooks import urls as webhooks_urls


def index(request):
    return HttpResponse()


admin.site.unregister(Group)


api_urls = [
    path("", include(applications_urls)),
    path("", include(interactions_urls)),
    path("", include(webhooks_urls)),
]


urlpatterns = [
    path("", index),
    path("docs", swagger_view),
    path("admin", admin.site.urls),
    path("api/v1/", include(api_urls)),
]

# Static files

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

else:
    regex_path = "^{}(?P<path>.*)$".format(re.escape(settings.STATIC_URL.lstrip("/")))
    urlpatterns.append(
        re_path(regex_path, serve, {"document_root": settings.STATIC_ROOT})
    )


# Django Admin

admin.site.site_header = "Weni Integrations Admin"
