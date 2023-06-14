import uuid

from unittest.mock import Mock, patch
from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from ..views import ChatGPTViewSet
from ..type import ChatGPTType


APPTYPE = ChatGPTType()
PROMPTS = str(uuid.uuid4())


class CreateChatGPTAppTestCase(APIBaseTestCase):
    url = reverse("chatgpt-app-list")
    view_class = ChatGPTViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def setUp(self):
        super().setUp()
        self.project_uuid = str(uuid.uuid4())
        self.body = {"project_uuid": self.project_uuid}

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "marketplace.core.types.externals.chatgpt.views.FlowsClient.create_external_service"
    )
    def test_create_chatgpt(self, mock_create_external_service):
        data = {
            "channelUuid": str(uuid.uuid4()),
            "title": "ChatGPT Test",
        }
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_response.status_code = 200
        mock_create_external_service.return_value = mock_response

        payload = {
            "user": str(self.user),
            "project_uuid": self.project_uuid,
            "name": "ChatGPT Test",
            "api_key": str(uuid.uuid4()),
            "ai_model": "gpt-3.5-turbo",
        }
        response = self.request.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_app_without_permission(self):
        self.user_authorization.delete()
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveChatGPTAppTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    def setUp(self):
        super().setUp()

        self.app = APPTYPE.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("chatgpt-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class PatchChatGPTAppTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    def setUp(self):
        super().setUp()
        self.data = {
            "name": "gpt_test",
            "app_key": str(uuid.uuid4()),
            "app_secret": str(uuid.uuid4()),
            "ai_model": "gpt-3.5-turbo",
        }
        self.app = APPTYPE.create_app(
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=self.data,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = f"api/v1/apptypes/chatgpt/apps/{str(self.app.uuid)}"
        # reverse("chatgpt-app-list", kwargs={"uuid": str(self.app.uuid)})
        self.body = {"config": {"name": "new_name"}}

    @property
    def view(self):
        return self.view_class.as_view({"patch": "update"})

    @patch("marketplace.core.types.externals.chatgpt.views.FlowsClient.detail_external")
    @patch(
        "marketplace.core.types.externals.chatgpt.views.FlowsClient.update_external_config"
    )
    def test_patch_chatgpt_success(self, mock_update, mock_detail):
        mock_detail.return_value = {"config": self.data}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_update.return_value = mock_response

        payload = {"config": self.data}

        response = self.request.patch(self.url, payload, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreatePromptsTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    def setUp(self):
        super().setUp()
        self.data = {
            "name": "gpt_test",
            "app_key": str(uuid.uuid4()),
            "app_secret": str(uuid.uuid4()),
            "ai_model": "gpt-3.5-turbo",
        }
        self.app = APPTYPE.create_app(
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=self.data,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("chatgpt-app-prompts", kwargs={"uuid": str(self.app.uuid)})

    @property
    def view(self):
        return self.view_class.as_view({"post": "prompts"})

    @patch("marketplace.core.types.externals.chatgpt.views.FlowsClient.create_prompts")
    def test_create_prompts(self, mock_create_prompts):
        data = {"uuid": PROMPTS}
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_response.status_code = 200
        mock_create_prompts.return_value = mock_response

        payload = {
            "project_uuid": str(self.app.project_uuid),
            "prompts": [
                {"text": "test_1"},
            ],
        }
        response = self.request.post(self.url, payload, uuid=str(self.app.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ListPromptsTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    def setUp(self):
        super().setUp()
        self.data = {
            "name": "gpt_test",
            "app_key": str(uuid.uuid4()),
            "app_secret": str(uuid.uuid4()),
            "ai_model": "gpt-3.5-turbo",
        }
        self.app = APPTYPE.create_app(
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=self.data,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("chatgpt-app-prompts", kwargs={"uuid": str(self.app.uuid)})

    @property
    def view(self):
        return self.view_class.as_view({"get": "prompts"})

    @patch("marketplace.core.types.externals.chatgpt.views.FlowsClient.list_prompts")
    def test_list_prompts(self, mock_create_prompts):
        data = [
            {"uuid": str(uuid.uuid4()), "text": "123456"},
            {"uuid": str(uuid.uuid4()), "text": "654321"},
        ]
        mock_response = Mock()
        mock_response.json.return_value = data
        mock_response.status_code = 200
        mock_create_prompts.return_value = mock_response

        response = self.request.get(self.url, uuid=str(self.app.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeletePromptsTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    def setUp(self):
        super().setUp()
        self.data = {
            "name": "gpt_test",
            "app_key": str(uuid.uuid4()),
            "app_secret": str(uuid.uuid4()),
            "ai_model": "gpt-3.5-turbo",
        }
        self.app = APPTYPE.create_app(
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            config=self.data,
            flow_object_uuid=str(uuid.uuid4()),
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("chatgpt-app-prompts", kwargs={"uuid": str(self.app.uuid)})

    @property
    def view(self):
        return self.view_class.as_view({"delete": "prompts"})

    @patch("marketplace.core.types.externals.chatgpt.views.FlowsClient.delete_prompts")
    def test_delete_prompts(self, mock_delete_prompts):
        mock_delete_prompts.return_value.status_code = status.HTTP_204_NO_CONTENT
        payload = {
            "project_uuid": str(self.app.project_uuid),
            "prompts": [
                PROMPTS,
            ],
        }
        response = self.request.delete(self.url, payload, uuid=str(self.app.uuid))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class DeleteChatGPTAppTestCase(APIBaseTestCase):
    view_class = ChatGPTViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def setUp(self):
        super().setUp()
        self.app = APPTYPE.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("chatgpt-app-detail", kwargs={"uuid": self.app.uuid})

    def test_delete_app_plataform(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())

    def test_delete_app_with_wrong_project_uuid(self):
        response = self.request.delete(self.url, uuid=str(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_app_without_autorization(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("marketplace.flows.client.FlowsClient.release_external_service")
    def test_release_external_service(self, mock_release):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_release.return_value = mock_response

        self.app.flow_object_uuid = uuid.uuid4()
        self.app.save()

        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())
