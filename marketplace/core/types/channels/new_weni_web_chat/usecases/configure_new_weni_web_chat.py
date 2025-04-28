import os
import json

from django.conf import settings

from marketplace.accounts.models import User
from marketplace.applications.models import App
from marketplace.core.storage import AppStorage
from marketplace.core.types.channels.new_weni_web_chat.type import NewWeniWebChatType
from marketplace.clients.flows.client import FlowsClient

from storages.backends.s3boto3 import S3Boto3Storage

from typing import Optional, TypedDict, Any


class ConfigureNewWeniWebChatUseCase:
    class ConfigData(TypedDict):
        title: str
        subtitle: Optional[str]
        inputTextFieldHint: str
        showFullScreenButton: bool
        displayUnreadCount: bool
        keepHistory: bool
        initPayload: Optional[str]
        mainColor: str
        profileAvatar: Optional[Any]
        customCss: Optional[Any]
        timeBetweenMessages: int
        tooltipMessage: Optional[str]
        startFullScreen: bool
        embedded: bool

    def __init__(
        self,
        app: App,
        user: User,
        config_data: ConfigData,
        storage: Optional[S3Boto3Storage] = None,
        flows_client: Optional[FlowsClient] = None,
    ):
        self.app = app
        self.user = user
        self.config_data = config_data
        self.storage = storage or AppStorage(app)
        self.flows_client = flows_client or FlowsClient()

    def _process_avatar(self):
        avatar_file = self.config_data.get("profileAvatar")

        if avatar_file:
            with self.storage.open(avatar_file.name, "w") as up_file:
                up_file.write(avatar_file.file.read())
                file_url = self.storage.url(up_file.name)
                self.config_data["profileAvatar"] = file_url
                self.config_data["openLauncherImage"] = file_url

    def _process_custom_css(self):
        custom_css = self.config_data.get("customCss")

        if custom_css:
            with self.storage.open("custom.css", "w") as up_file:
                up_file.write(custom_css)
                self.config_data["customCss"] = self.storage.url(up_file.name)

    def _create_channel_if_needed(self):
        if self.app.flow_object_uuid is None:
            name = f"{NewWeniWebChatType.name} - #{self.app.id}"
            data = {"name": name, "base_url": settings.SOCKET_BASE_URL}

            result = self.flows_client.create_channel(
                self.user.email, self.app.project_uuid, data, self.app.flows_type_code
            )

            self.app.flow_object_uuid = result.get("uuid")
            self.app.configured = True
            self.app.save(update_fields=["flow_object_uuid", "configured"])

    def _generate_script(self, attrs: ConfigData):
        header_path = os.path.dirname(os.path.abspath(__file__))
        header_file = os.path.join(header_path, "../header.script")

        with open(header_file, "r") as script_header:
            header = (
                script_header.read()
                .replace("<APPTYPE_CODE>", NewWeniWebChatType.code)
                .replace(
                    "<CUSTOM-MESSAGE-DELAY>", str(attrs.get("timeBetweenMessages"))
                )
                .replace("<CUSTOM_CSS>", str(attrs.get("customCss", "")))
            )
            attrs.pop("timeBetweenMessages", None)
            attrs["channelUuid"] = str(self.app.flow_object_uuid)
            attrs.pop("customCss", None)

        script = header.replace("<FIELDS>", json.dumps(attrs, indent=2))

        with self.storage.open("script.js", "w") as up_file:
            up_file.write(script)
            return self.storage.url(up_file.name)

    def _configure(self):
        self.config_data["selector"] = f"#{NewWeniWebChatType.code}"
        main_color = self.config_data.get("mainColor")
        self.config_data["customizeWidget"] = {
            "headerBackgroundColor": main_color,
            "launcherColor": main_color,
            "userMessageBubbleColor": main_color,
            "quickRepliesFontColor": main_color,
            "quickRepliesBackgroundColor": main_color + "33",
            "quickRepliesBorderColor": main_color,
        }
        self.config_data["params"] = {
            "images": {"dims": {"width": 300, "height": 200}},
            "storage": "local" if self.config_data.get("keepHistory") else "session",
        }
        self.config_data["socketUrl"] = settings.SOCKET_BASE_URL
        self.config_data["host"] = settings.FLOWS_HOST_URL
        self.config_data.pop("keepHistory", None)
        self.config_data["script"] = self._generate_script(self.config_data.copy())

    def execute(self):
        self._process_avatar(self.config_data)
        self._process_custom_css(self.config_data)
        self._create_channel_if_needed()
        self._configure(self.config_data)

        return self.config_data
