from django.urls import path

from marketplace.wpp_templates.analytics.views.views import TemplateAnalytics


template_analytics = [
    path(
        "<uuid:app_uuid>/template-analytics/",
        TemplateAnalytics.as_view({"get": "template_analytics"}),
        name="template-analytics",
    )
]

urlpatterns = template_analytics
