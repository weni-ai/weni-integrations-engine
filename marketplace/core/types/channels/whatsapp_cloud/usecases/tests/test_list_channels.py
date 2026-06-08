import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_cloud.usecases.list_channels import (
    ListWhatsAppCloudChannelsUseCase,
)


User = get_user_model()


class ListWhatsAppCloudChannelsUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.project_uuid = str(uuid.uuid4())
        self.other_project_uuid = str(uuid.uuid4())
        self.use_case = ListWhatsAppCloudChannelsUseCase()

    def _create_app(self, project_uuid, code="wpp-cloud"):
        return App.objects.create(
            code=code,
            created_by=self.user,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            flow_object_uuid=str(uuid.uuid4()),
        )

    def test_execute_returns_channels_of_the_project(self):
        self._create_app(self.project_uuid)
        self._create_app(self.project_uuid)

        apps = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertEqual(apps.count(), 2)

    def test_execute_returns_empty_queryset_when_project_has_no_channels(self):
        apps = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertEqual(apps.count(), 0)

    def test_execute_does_not_return_channels_of_other_projects(self):
        app = self._create_app(self.project_uuid)
        self._create_app(self.other_project_uuid)

        apps = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertEqual(list(apps), [app])

    def test_execute_only_returns_wpp_cloud_apps(self):
        wpp_cloud_app = self._create_app(self.project_uuid)
        self._create_app(self.project_uuid, code="wpp")

        apps = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertEqual(list(apps), [wpp_cloud_app])
