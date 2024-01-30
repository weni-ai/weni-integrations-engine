import uuid

from unittest.mock import Mock, patch
from rest_framework import status

from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.wpp_templates.analytics.views.views import TemplateAnalyticsViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization


class MockFacebookService:
    def __init__(self, *args, **kwargs):
        pass

    def template_analytics(self, app, data):
        pass


class SetUpTestBase(APIBaseTestCase):
    view_class = TemplateAnalyticsViewSet

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

    @property
    def view(self):
        return self.view_class.as_view({"get": "template_analytics"})


class TemplateAnalyticsViewSetSerializerTestCase(SetUpTestBase):
    def setUp(self):
        super().setUp()
        # Mock service
        mock_service = MockFacebookService()
        patcher = patch.object(
            self.view_class, "fb_service", Mock(return_value=mock_service)
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_start_date_after_end_date_whatsapp_cloud(self):
        url = reverse(
            "template-analytics",
            kwargs={"app_uuid": self.app.uuid},
        )
        params = {
            "start": "12-31-2023",
            "end": "01-01-2023",
            "fba_template_ids": ["831797345020910"],
        }
        response = self.client.get(url, params, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["End date must occur after the start date"]},
        )

    def test_start_date_after_end_date_whatsapp(self):
        app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        url = reverse(
            "template-analytics",
            kwargs={"app_uuid": app.uuid},
        )
        params = {
            "start": "12-31-2023",
            "end": "01-01-2023",
            "fba_template_ids": ["831797345020910"],
        }
        response = self.client.get(url, params, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"non_field_errors": ["End date must occur after the start date"]},
        )
