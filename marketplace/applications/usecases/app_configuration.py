from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover
    from django.contrib.auth import get_user_model

    from marketplace.core.types import AppType
    from ..models import App

    User = get_user_model()


class AppConfigurationUseCase:  # pragma: no cover
    def __init__(self, channel_client, channel_token_client):
        self.__channel_client = channel_client
        self.__channel_token_client = channel_token_client

    def configure_app(self, app: "App", apptype: "AppType", user: "User") -> None:
        apptype.configure_app(app, user, self.__channel_client, self.__channel_token_client)
