import uuid

from unittest.mock import patch, PropertyMock
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
        return {
            "data": [
                {
                    "template_id": "1515371305882507",
                    "sent": 3,
                    "delivered": 3,
                    "read": 1,
                    "template": "test1",
                },
                {
                    "template_id": "768404021753348",
                    "sent": 3,
                    "delivered": 3,
                    "read": 1,
                    "template": "test2",
                },
            ],
            "totals": {"sent": 6, "delivered": 6, "read": 2},
        }

    def enable_insights(self, app):
        return True


class MockFacebookServiceFailure(MockFacebookService):
    def enable_insights(self, app):
        return None


class SetUpTestBase(APIBaseTestCase):
    current_view_mapping = {}
    view_class = TemplateAnalyticsViewSet

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            config={"wa_waba_id": "123456789"},
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)


class MockServices(SetUpTestBase):
    def setUp(self):
        super().setUp()

        # Mock Facebook service
        mock_facebook_service = MockFacebookService()
        patcher_fb = patch.object(
            self.view_class,
            "fb_service",
            PropertyMock(return_value=mock_facebook_service),
        )
        self.addCleanup(patcher_fb.stop)
        patcher_fb.start()


class TemplateAnalyticsViewSetTestCase(MockServices):
    current_view_mapping = {"get": "template_analytics"}

    def test_get_template_analytics(self):
        url = reverse(
            "template-analytics",
            kwargs={"app_uuid": self.app.uuid},
        )
        params = {
            "start": "9-27-2023",
            "end": "9-28-2023",
            "fba_template_ids": [831797345020910, 1515371305882507, 768404021753348],
        }
        response = self.request.get(url, app_uuid=self.app.uuid, params=params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json["data"]), 2)


class EnableTemplateAnalyticsViewSetTestCase(MockServices):
    current_view_mapping = {"post": "enable_analytics"}

    def test_enable_analytics(self):
        url = reverse(
            "enable-analytics",
            kwargs={"app_uuid": self.app.uuid},
        )
        response = self.request.post(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_falied_to_enable_analytics(self):
        mock_facebook_service_failure = MockFacebookServiceFailure()
        patcher_fb_failure = patch.object(
            self.view_class,
            "fb_service",
            PropertyMock(return_value=mock_facebook_service_failure),
        )
        patcher_fb_failure.start()
        self.addCleanup(patcher_fb_failure.stop)

        url = reverse(
            "enable-analytics",
            kwargs={"app_uuid": self.app.uuid},
        )
        response = self.request.post(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
