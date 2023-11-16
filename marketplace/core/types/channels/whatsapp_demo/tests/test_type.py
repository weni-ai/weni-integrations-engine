import uuid
from unittest.mock import MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..type import WhatsAppDemoType


User = get_user_model()


class SetupWhatsAppDemoTypeTestCase(TestCase):
    def setUp(self) -> None:
        self.apptype = WhatsAppDemoType()

    def test_template_type_setup_returns_app_code(self):
        app_setup = self.apptype.template_type_setup()
        self.assertEqual(app_setup.get("code"), self.apptype.code)


class ConfigureWhatsAppDemoTypeTestCase(TestCase):
    def setUp(self) -> None:
        self.apptype_class = WhatsAppDemoType

        self.user = User.objects.create_superuser(
            email="admin@marketplace.ai", password="fake@pass#$"
        )
        self.app = self.apptype_class().create_app(
            created_by=self.user, project_uuid=uuid.uuid4()
        )

        self.channel_client = self._get_channel_client_mock("Test App Name", "1234")
        self.channel_token_client = self._get_channel_token_client_mock(
            "Test App Name", "1234"
        )

    def _get_channel_client_mock(self, name: str, uuid: str) -> MagicMock:
        channel_client_mock = MagicMock()
        channel_client_mock.create_channel.return_value = {"name": name, "uuid": uuid}

        return channel_client_mock

    def _get_channel_token_client_mock(self, name: str, uuid: str) -> MagicMock:
        channel_client_mock = MagicMock()
        channel_client_mock.get_channel_token.return_value = "fake-token"

        return channel_client_mock

    def test_app_config_title_equals_channel_name(self):
        app = self.apptype_class.configure_app(
            self.app, self.user, self.channel_client, self.channel_token_client
        )
        self.assertEqual(app.config.get("title"), "Test App Name")

    def test_app_config_router_token_equals_channel_token(self):
        app = self.apptype_class.configure_app(
            self.app, self.user, self.channel_client, self.channel_token_client
        )
        self.assertEqual(app.config.get("routerToken"), "fake-token")

    def test_app_config_redirect_url_has_channel_token(self):
        redirect_url = f"https://wa.me/{self.apptype_class.NUMBER}?text=fake-token"
        app = self.apptype_class.configure_app(
            self.app, self.user, self.channel_client, self.channel_token_client
        )
        self.assertEqual(app.config.get("redirect_url"), redirect_url)
