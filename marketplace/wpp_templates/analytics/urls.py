from django.urls import path

from marketplace.wpp_templates.analytics.views.views import TemplateAnalyticsViewSet


template_analytics = [
    path(
        "<uuid:app_uuid>/template-analytics/",
        TemplateAnalyticsViewSet.as_view({"get": "template_analytics"}),
        name="template-analytics",
    ),
    path(
        "<uuid:app_uuid>/enable-analytics/",
        TemplateAnalyticsViewSet.as_view({"post": "enable_analytics"}),
        name="enable-analytics",
    ),
]

urlpatterns = template_analytics
