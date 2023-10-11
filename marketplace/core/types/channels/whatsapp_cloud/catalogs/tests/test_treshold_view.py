import uuid

from unittest.mock import patch, PropertyMock
from rest_framework import status

from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_cloud.catalogs.views.views import (
    TresholdViewset,
)
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization


class MockFlowsService:
    def __init__(self, *args, **kwargs):
        pass

    def update_treshold(self, app, treshold):
        pass


class SetUpTestBase(APIBaseTestCase):
    view_class = TresholdViewset

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
        return self.view_class.as_view({"patch": "update_treshold"})


class TresholdViewSetTestCase(SetUpTestBase):
    def setUp(self):
        super().setUp()
        # Mock service
        mock_service = MockFlowsService()
        patcher = patch.object(
            self.view_class, "flows_service", PropertyMock(return_value=mock_service)
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_update_treshold(self):
        url = reverse(
            "update-treshold",
            kwargs={"app_uuid": self.app.uuid},
        )
        data = {"treshold": "10.0"}
        response = self.request.patch(url, app_uuid=self.app.uuid, body=data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
