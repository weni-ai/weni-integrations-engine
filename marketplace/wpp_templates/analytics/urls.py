from django.urls import path

from marketplace.wpp_templates.analytics.views.views import TemplateAnalyticsViewSet


template_analytics = [
    path(
        "<uuid:app_uuid>/template-analytics/",
        TemplateAnalyticsViewSet.as_view({"post": "template_analytics"}),
        name="template-analytics",
    )
]

urlpatterns = template_analytics
