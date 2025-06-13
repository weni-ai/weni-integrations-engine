from django.urls import path
from marketplace.wpp_templates.insights.views import TemplateVersionDataView

urlpatterns = [
    path(
        "<uuid:app_uuid>/template-version-insights/",
        TemplateVersionDataView.as_view(),
        name="template-version-insights",
    )
]
