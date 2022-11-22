import json
import requests

from django.conf import settings


class ConnectAuth:
    def __get_auth_token(self) -> str:
        request = requests.post(
            url=settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                "client_id": settings.OIDC_RP_CLIENT_ID,
                "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        token = request.json().get("access_token")
        return f"Bearer {token}"

    def auth_header(self) -> dict:
        return {"Authorization": self.__get_auth_token()}


class ConnectProjectClient(ConnectAuth):

    base_url = settings.CONNECT_ENGINE_BASE_URL

    def list_channels(self, channeltype_code: str) -> list:

        params = {"channel_type": channeltype_code}
        response = requests.get(
            url=self.base_url + "/v1/organization/project/list_channels/", params=params, headers=self.auth_header()
        )
        return response.json().get("channels", None)

    def create_channel(self, user: str, project_uuid: str, data: dict, channeltype_code: str) -> dict:
        payload = {"user": user, "project_uuid": str(project_uuid), "data": data, "channeltype_code": channeltype_code}
        response = requests.post(
            url=self.base_url + "/v1/organization/project/create_channel/", json=payload, headers=self.auth_header()
        )
        return response.json()

    def create_wac_channel(self, user: str, project_uuid: str, phone_number_id: str, config: dict) -> dict:
        payload = {
            "user": user,
            "project_uuid": str(project_uuid),
            "config": json.dumps(config),
            "phone_number_id": phone_number_id,
        }
        response = requests.post(
            url=self.base_url + "/v1/organization/project/create_wac_channel/",
            json=payload,
            headers=self.auth_header(),
        )
        return response.json()

    def release_channel(self, channel_uuid: str, user_email: str) -> None:
        payload = {"channel_uuid": channel_uuid, "user": user_email}
        requests.get(
            url=self.base_url + "/v1/organization/project/release_channel/", json=payload, headers=self.auth_header()
        )
        return None

    def get_user_api_token(self, user: str, project_uuid: str):
        params = dict(user=user, project_uuid=str(project_uuid))
        response = requests.get(
            self.base_url + "/v1/organization/project/user_api_token/", params=params, headers=self.auth_header()
        )
        return response

    def list_availables_channels(self) -> list:
        # response = requests.get(
        #     url=self.base_url + "/v1/organization/project/list_channels_availables/",
        #     headers=self.auth_header(),
        #     timeout=60
        # )
        # return response.json().get("channels", None)
        payload = [
                {
                    "attrs": {
                        "code": "AC",
                        "name": "ArabiaCell",
                        "available_timezones": [
                            "Asia/Amman"
                        ],
                        "recommended_timezones": [
                            "Asia/Amman"
                        ],
                        "category": {
                            "name": "PHONE",
                            "value": 1
                        },
                        "schemes": [
                            "tel"
                        ],
                        "max_length": 1530,
                        "attachment_support": False,
                        "claim_blurb": "If you have an <a href=\"https://www.arabiacell.com/\">ArabiaCell</a> number, you can quickly connect it using their APIs.",
                        "configuration_blurb": "To finish connecting your channel, you need to have ArabiaCell configure the URL below for your short code.",
                        "configuration_urls": [
                            {
                                "label": "Receive URL",
                                "url": "https://{{channel.callback_domain}}/c/ac/{{channel.uuid}}/receive",
                                "description": "This URL should be called by ArabiaCell when new messages are received."
                            }
                        ],
                        "slug": "arabiacell",
                        "num_fields": 12
                    }
                }, 
                {
                    "attrs": {
                        "code": "WWC",
                        "category": {
                            "name": "API",
                            "value": 4
                        },
                        "courier_url": "^wwc/(?P<uuid>[a-z0-9\\-]+)/receive",
                        "name": "Weni Web Chat",
                        "icon": "icon-weniwebchat",
                        "show_config_page": True,
                        "claim_blurb": "With Weni Web Chat, you can integrate your Rapidpro organization as a chat on your website.",
                        "schemes": [
                            "weniwebchat"
                        ],
                        "max_length": 320,
                        "attachment_support": True,
                        "free_sending": True,
                        "slug": "weniwebchat",
                        "num_fields": 12
                    }
                },
                {
                    "attrs": {
                        "code": "TG",
                        "category": {
                            "name": "SOCIAL_MEDIA",
                            "value": 2
                        },
                        "courier_url": "^tg/(?P<uuid>[a-z0-9\\-]+)/receive$",
                        "name": "Telegram",
                        "icon": "icon-telegram",
                        "show_config_page": False,
                        "claim_blurb": "Add a <a href=\"https://telegram.org\">Telegram</a> bot to send and receive messages to Telegram users for free. Your users will need an Android, Windows or iOS device and a Telegram account to send and receive messages.",
                        "schemes": [
                            "telegram"
                        ],
                        "max_length": 1600,
                        "attachment_support": True,
                        "free_sending": True,
                        "slug": "telegram",
                        "num_fields": 12
                    }
                },
                        {
                    "attrs": {
                        "code": "ZVS",
                        "category": {
                            "name": "PHONE",
                            "value": 1
                        },
                        "courier_url": "^zvs/(?P<uuid>[a-z0-9\\-]+)/(?P<action>receive|status)$",
                        "name": "Zenvia SMS",
                        "claim_blurb": "If you have a <a href=\"https://www.zenvia.com/\">Zenvia SMS</a> number, you can connect it to communicate with your contacts.",
                        "schemes": [
                            "tel"
                        ],
                        "max_length": 1600,
                        "slug": "zenvia_sms",
                        "num_fields": 8
                    }
                },
                {
                    "attrs": {
                        "CONFIG_BASE_URL": "base_url",
                        "CONFIG_BOT_USERNAME": "bot_username",
                        "CONFIG_ADMIN_AUTH_TOKEN": "admin_auth_token",
                        "CONFIG_ADMIN_USER_ID": "admin_user_id",
                        "CONFIG_SECRET": "secret",
                        "code": "RC",
                        "slug": "rocketchat",
                        "category": {
                            "name": "SOCIAL_MEDIA",
                            "value": 2
                        },
                        "courier_url": "^rc/(?P<uuid>[a-z0-9\\-]+)/receive$",
                        "name": "Rocket.Chat",
                        "icon": "icon-rocketchat",
                        "show_config_page": False,
                        "claim_blurb": "Add a <a href=\"https://rocket.chat/\">Rocket.Chat</a> bot to send and receive messages to Rocket.Chat users.",
                        "schemes": [
                            "rocketchat"
                        ],
                        "num_fields": 14
                    }
                },
                {
                    "attrs": {
                        "code": "EX",
                        "category": {
                            "name": "PHONE",
                            "value": 1
                        },
                        "courier_url": "^ex/(?P<uuid>[a-z0-9\\-]+)/(?P<action>sent|delivered|failed|received|receive|stopped)$",
                        "name": "External API",
                        "icon": "icon-power-cord",
                        "claim_blurb": "Use our pluggable API to connect an external service you already have.",
                        "schemes": None,
                        "max_length": 160,
                        "attachment_support": False,
                        "CONFIG_SEND_AUTHORIZATION": "send_authorization",
                        "CONFIG_MAX_LENGTH": "max_length",
                        "CONFIG_SEND_METHOD": "method",
                        "CONFIG_SEND_BODY": "body",
                        "CONFIG_MT_RESPONSE_CHECK": "mt_response_check",
                        "CONFIG_CONTENT_TYPE": "content_type",
                        "CONFIG_DEFAULT_SEND_BODY": "id={{id}}&text={{text}}&to={{to}}&to_no_plus={{to_no_plus}}&from={{from}}&from_no_plus={{from_no_plus}}&channel={{channel}}",
                        "slug": "external",
                        "num_fields": 17
                    }
                }
                ]
        return payload


    def get_available_channel(self, channel_code: str) -> list:

        #params = {"channel_code": channel_code}
        # response = requests.get(
        #     url=self.base_url + "/v1/organization/project/channel_available/",
        #     params=params, headers=self.auth_header(),
        #     timeout=60
        # )
        # return response.json().get("channels", None)
        channel_code = channel_code.upper()
        payload = {
            "TG": {
                        "attributes": {
                            "code": "TG",
                            "category": {
                                "name": "SOCIAL_MEDIA",
                                "value": 2
                            },
                            "courier_url": "^tg/(?P<uuid>[a-z0-9\\-]+)/receive$",
                            "name": "Telegram",
                            "icon": "icon-telegram",
                            "show_config_page": False,
                            "claim_blurb": "Add a <a href=\"https://telegram.org\">Telegram</a> bot to send and receive messages to Telegram users for free. Your users will need an Android, Windows or iOS device and a Telegram account to send and receive messages.",
                            "schemes": [
                                "telegram"
                            ],
                            "max_length": 1600,
                            "attachment_support": True,
                            "free_sending": True,
                            "slug": "telegram",
                            "num_fields": 12
                        },
                        "form": [
                            {
                                "name": "auth_token",
                                "type": "text",
                                "help_text": "The Authentication token for your Telegram Bot"
                            }
                        ]
                    }
            ,"WWC":{
                        "attributes": {
                            "code": "WWC",
                            "category": {
                                "name": "API",
                                "value": 4
                            },
                            "courier_url": "^wwc/(?P<uuid>[a-z0-9\\-]+)/receive",
                            "name": "Weni Web Chat",
                            "icon": "icon-weniwebchat",
                            "show_config_page": False,
                            "claim_blurb": "With Weni Web Chat, you can integrate your Rapidpro organization as a chat on your website.",
                            "schemes": [
                                "weniwebchat"
                            ],
                            "max_length": 320,
                            "attachment_support": True,
                            "free_sending": True,
                            "slug": "weniwebchat",
                            "num_fields": 12
                        },
                        "form": [
                            {
                                "name": "name",
                                "type": "text",
                                "help_text": "This field will serve as name for your channel"
                            },
                            {
                                "name": "base_url",
                                "type": "url",
                                "help_text": "URL where socket communication will take place"
                            }
                        ]
                    }
            ,"ZVS":{
                        "attributes": {
                            "code": "ZVS",
                            "category": {
                                "name": "PHONE",
                                "value": 1
                            },
                            "courier_url": "^zvs/(?P<uuid>[a-z0-9\\-]+)/(?P<action>receive|status)$",
                            "name": "Zenvia SMS",
                            "claim_blurb": "If you have a <a href=\"https://www.zenvia.com/\">Zenvia SMS</a> number, you can connect it to communicate with your contacts.",
                            "schemes": [
                                "tel"
                            ],
                            "max_length": 1600,
                            "slug": "zenvia_sms",
                            "num_fields": 8
                        },
                        "form": [
                            {
                                "name": "country",
                                "type": "select",
                                "help_text": "The country this phone number is used in",
                                "choices": [
                                    [
                                        "AF",
                                        "Afghanistan"
                                    ],
                                    [
                                        "AL",
                                        "Albania"
                                    ],
                                    [
                                        "DZ",
                                        "Algeria"
                                    ],
                                    [
                                        "BR",
                                        "Brazil"
                                    ],

                                ]
                            },
                            {
                                "name": "number",
                                "type": "text",
                                "help_text": "The phone number with country code or short code you are connecting. ex: +250788123124 or 15543"
                            },
                            {
                                "name": "token",
                                "type": "text",
                                "help_text": "The API token for your integration as provided by Zenvia"
                            }
                        ]
                    }
            ,"RC":{
                        "attributes": {
                            "CONFIG_BASE_URL": "base_url",
                            "CONFIG_BOT_USERNAME": "bot_username",
                            "CONFIG_ADMIN_AUTH_TOKEN": "admin_auth_token",
                            "CONFIG_ADMIN_USER_ID": "admin_user_id",
                            "CONFIG_SECRET": "secret",
                            "code": "RC",
                            "slug": "rocketchat",
                            "category": {
                                "name": "SOCIAL_MEDIA",
                                "value": 2
                            },
                            "courier_url": "^rc/(?P<uuid>[a-z0-9\\-]+)/receive$",
                            "name": "Rocket.Chat",
                            "icon": "icon-rocketchat",
                            "show_config_page": False,
                            "claim_blurb": "Add a <a href=\"https://rocket.chat/\">Rocket.Chat</a> bot to send and receive messages to Rocket.Chat users.",
                            "schemes": [
                                "rocketchat"
                            ],
                            "num_fields": 14
                        },
                        "form": [
                            {
                                "name": "base_url",
                                "type": "url",
                                "help_text": "URL of the Rocket.Chat Channel app"
                            },
                            {
                                "name": "bot_username",
                                "type": "text",
                                "help_text": "Username of your bot user"
                            },
                            {
                                "name": "admin_user_id",
                                "type": "text",
                                "help_text": "User ID of an administrator user"
                            },
                            {
                                "name": "admin_auth_token",
                                "type": "text",
                                "help_text": "Authentication token of an administrator user"
                            },
                            {
                                "name": "secret",
                                "type": "hidden",
                                "help_text": "Secret to be passed to Rocket.Chat"
                            }
                        ]
                    }
            ,"EX":{
                        "attributes": {
                            "code": "EX",
                            "category": {
                                "name": "PHONE",
                                "value": 1
                            },
                            "courier_url": "^ex/(?P<uuid>[a-z0-9\\-]+)/(?P<action>sent|delivered|failed|received|receive|stopped)$",
                            "name": "External API",
                            "icon": "icon-power-cord",
                            "claim_blurb": "Use our pluggable API to connect an external service you already have.",
                            "schemes": None,
                            "max_length": 160,
                            "attachment_support": False,
                            "CONFIG_SEND_AUTHORIZATION": "send_authorization",
                            "CONFIG_MAX_LENGTH": "max_length",
                            "CONFIG_SEND_METHOD": "method",
                            "CONFIG_SEND_BODY": "body",
                            "CONFIG_MT_RESPONSE_CHECK": "mt_response_check",
                            "CONFIG_CONTENT_TYPE": "content_type",
                            "CONFIG_DEFAULT_SEND_BODY": "id={{id}}&text={{text}}&to={{to}}&to_no_plus={{to_no_plus}}&from={{from}}&from_no_plus={{from_no_plus}}&channel={{channel}}",
                            "slug": "external",
                            "num_fields": 17
                        },
                        "form": None
                    },
        }

        data = payload.keys()
        for value in data:
            if channel_code in (value):
                return payload.get(channel_code)

        return None

class WPPRouterChannelClient(ConnectAuth):
    base_url = settings.ROUTER_BASE_URL

    def get_channel_token(self, uuid: str, name: str) -> str:
        payload = {"uuid": uuid, "name": name}

        response = requests.post(url=self.base_url + "/integrations/channel", json=payload, headers=self.auth_header())

        return response.json().get("token", "")
