from django.urls import path
from marketplace.wpp_templates.metrics.views import TemplateMetricsView

urlpatterns = [
    path(
        "<uuid:app_uuid>/template-metrics/",
        TemplateMetricsView.as_view(),
        name="template-metrics",
    )
]
