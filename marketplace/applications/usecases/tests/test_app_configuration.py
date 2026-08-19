from unittest.mock import MagicMock

from django.test import SimpleTestCase

from marketplace.applications.usecases.app_configuration import AppConfigurationUseCase


class AppConfigurationUseCaseTestCase(SimpleTestCase):
    def setUp(self):
        self.channel_token_client = MagicMock()
        self.use_case = AppConfigurationUseCase(self.channel_token_client)
        self.app = MagicMock()
        self.apptype = MagicMock()
        self.user = MagicMock()

    def test_configure_app_delegates_to_apptype_with_channel_token_client(self):
        self.use_case.configure_app(self.app, self.apptype, self.user)

        self.apptype.configure_app.assert_called_once_with(
            self.app, self.user, self.channel_token_client
        )
