import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.applications.usecases.check_webchat_integration import (
    CheckWebChatIntegrationUseCase,
    WEBCHAT_APP_CODE,
)


User = get_user_model()


class CheckWebChatIntegrationUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@marketplace.ai")
        self.project_uuid = uuid.uuid4()
        self.use_case = CheckWebChatIntegrationUseCase()

    def test_execute_returns_has_webchat_false_when_no_app_exists(self):
        result = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertFalse(result["has_webchat"])
        self.assertNotIn("webchat_app_uuid", result)
        self.assertNotIn("flows_channel_uuid", result)

    def test_execute_returns_has_webchat_true_when_app_exists(self):
        app = App.objects.create(
            code=WEBCHAT_APP_CODE,
            config={},
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
            flow_object_uuid=uuid.uuid4(),
        )
        result = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertTrue(result["has_webchat"])
        self.assertEqual(result["webchat_app_uuid"], str(app.uuid))
        self.assertEqual(result["flows_channel_uuid"], str(app.flow_object_uuid))

    def test_execute_returns_false_for_different_project(self):
        App.objects.create(
            code=WEBCHAT_APP_CODE,
            config={},
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )
        result = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertFalse(result["has_webchat"])

    def test_execute_ignores_non_webchat_apps(self):
        App.objects.create(
            code="wpp-cloud",
            config={},
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )
        result = self.use_case.execute(project_uuid=self.project_uuid)

        self.assertFalse(result["has_webchat"])
