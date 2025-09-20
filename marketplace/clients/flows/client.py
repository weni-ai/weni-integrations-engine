"""Client for connection with flows"""

from django.conf import settings

from marketplace.clients.base import RequestClient, InternalAuthentication


class FlowsClient(RequestClient):
    def __init__(self):
        self.base_url = settings.FLOWS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def detail_channel(self, flow_object_uuid):
        url = f"{self.base_url}/api/v2/internals/channel/{str(flow_object_uuid)}"

        response = self.make_request(
            url, method="GET", headers=self.authentication_instance.headers
        )
        return response.json()

    def update_config(self, data, flow_object_uuid):
        payload = {"config": data}
        url = f"{self.base_url}/api/v2/internals/channel/{flow_object_uuid}/"

        response = self.make_request(
            url,
            method="PATCH",
            headers=self.authentication_instance.headers,
            json=payload,
        )
        return response

    def update_vtex_integration_status(self, project_uuid, user_email, action):
        url = f"{self.base_url}/api/v2/internals/orgs/{project_uuid}/update-vtex/"
        payload = {"user_email": user_email}
        self.make_request(
            url=url,
            method=action,
            headers=self.authentication_instance.headers,
            json=payload,
        )
        return True

    def update_vtex_ads_status(self, project_uuid, user_email, action, vtex_ads):
        url = f"{self.base_url}/api/v2/internals/orgs/{project_uuid}/update-vtex/"
        payload = {"user_email": user_email, "vtex_ads": vtex_ads}
        self.make_request(
            url=url,
            method=action,
            headers=self.authentication_instance.headers,
            json=payload,
        )
        return True

    def update_catalogs(self, flow_object_uuid, catalogs_data, active_catalog):
        data = {"data": catalogs_data, "active_catalog": active_catalog}
        url = f"{self.base_url}/catalogs/{flow_object_uuid}/update-catalog/"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def update_status_catalog(self, flow_object_uuid, fba_catalog_id, is_active: bool):
        data = {
            "facebook_catalog_id": fba_catalog_id,
            "is_active": is_active,
        }
        url = f"{self.base_url}/catalogs/{flow_object_uuid}/update-status-catalog/"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def update_vtex_products(self, products, flow_object_uuid, dict_catalog):
        data = {
            "catalog": dict_catalog,
            "channel_uuid": flow_object_uuid,
            "products": products,
        }
        url = f"{self.base_url}/products/update-products/"
        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def update_facebook_templates(self, flow_object_uuid, fba_templates):
        data = {"data": fba_templates}
        url = f"{self.base_url}/template/{flow_object_uuid}/"

        response = self.make_request(
            url,
            method="PATCH",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def update_facebook_templates_webhook(
        self, flow_object_uuid, template_data, template_name, webhook=None
    ):
        data = {
            "template_name": template_name,
            "template_data": template_data,
        }
        if webhook:
            data["webhook"] = webhook

        url = f"{self.base_url}/template/{flow_object_uuid}/template-sync/"
        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def create_wac_channel(
        self, user: str, project_uuid: str, phone_number_id: str, config: dict
    ) -> dict:
        url = f"{self.base_url}/api/v2/internals/channel/create_wac/"
        payload = {
            "user": user,
            "org": str(project_uuid),
            "config": config,
            "phone_number_id": phone_number_id,
        }
        response = self.make_request(
            method="POST",
            url=url,
            json=payload,
            headers=self.authentication_instance.headers,
        )
        return response.json()

    def get_sent_messagers(
        self, project_uuid: str, start_date: str, end_date: str, user: str
    ):
        url = f"{self.base_url}/api/v2/internals/template-messages/"
        params = {
            "project_uuid": project_uuid,
            "start_date": start_date,
            "end_date": end_date,
            "user": user,
        }
        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
            params=params,
        )
        return response

    def create_channel(
        self, user_email: str, project_uuid: str, data: dict, channeltype_code: str
    ) -> dict:
        payload = {
            "user": user_email,
            "org": str(project_uuid),
            "data": data,
            "channeltype_code": channeltype_code,
        }
        url = f"{self.base_url}/api/v2/internals/channel/"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=payload,
        )

        return response.json()

    def list_channels(self, channeltype_code: str, exclude_wpp_demo=None) -> list:
        params = {"channel_type": channeltype_code}
        if exclude_wpp_demo:
            params["exclude_wpp_demo"] = "true"

        url = f"{self.base_url}/api/v2/internals/channel/"

        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
            params=params,
        )

        def map_org_to_project_uuid(channel: dict) -> dict:
            channel["project_uuid"] = channel.pop("org")
            return channel

        return list(map(map_org_to_project_uuid, response.json()))

    def list_channel_types(self, channel_code):
        if channel_code:
            url = f"{self.base_url}/api/v2/internals/channels/{str(channel_code)}"
        else:
            url = f"{self.base_url}/api/v2/internals/channels"

        response = self.make_request(
            url, method="GET", headers=self.authentication_instance.headers
        )

        return response

    def detail_external(self, flow_object_uuid):
        url = f"{self.base_url}/api/v2/internals/externals/{str(flow_object_uuid)}"

        response = self.make_request(
            url, method="GET", headers=self.authentication_instance.headers
        )
        return response.json()

    def update_external_config(self, data, flow_object_uuid):
        payload = {"config": data}
        url = f"{self.base_url}/api/v2/internals/externals/{flow_object_uuid}/"

        response = self.make_request(
            url,
            method="PATCH",
            headers=self.authentication_instance.headers,
            json=payload,
        )
        return response

    def release_external_service(self, uuid: str, user_email: str):
        url = f"{self.base_url}/api/v2/internals/externals/{uuid}/"
        params = {"user": user_email}

        response = self.make_request(
            url,
            method="DELETE",
            headers=self.authentication_instance.headers,
            params=params,
        )
        return response

    def create_external_service(
        self, user: str, project: str, type_fields: dict, type_code: str
    ):
        body = dict(
            user=user, project=project, type_fields=type_fields, type_code=type_code
        )
        url = f"{self.base_url}/api/v2/internals/externals"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=body,
        )

        return response

    def create_prompts(self, user: str, text: str, external_uuid: str):
        body = dict(
            user=user,
            text=text,
        )
        url = f"{self.base_url}/api/v2/internals/externals/{external_uuid}/prompts/"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=body,
        )
        return response

    def detail_prompts(self, external_uuid: str, prompt_uuid: str):
        url = f"{self.base_url}/api/v2/internals/externals/{external_uuid}/prompts/{prompt_uuid}"

        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
        )
        return response

    def list_prompts(self, external_uuid: str):
        url = f"{self.base_url}/api/v2/internals/externals/{external_uuid}/prompts/"

        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
        )
        return response

    def delete_prompts(self, external_uuid: str, prompt_uuid: str):
        url = f"{self.base_url}/api/v2/internals/externals/{external_uuid}/prompts/{prompt_uuid}"

        response = self.make_request(
            url,
            method="DELETE",
            headers=self.authentication_instance.headers,
        )
        return response

    def get_user_api_token(self, user: str, project_uuid: str):
        params = dict(user=user, project=str(project_uuid))
        url = f"{self.base_url}/api/v2/internals/users/api-token/"
        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
            params=params,
        )
        return response

    def list_availables_channels(self):
        url = f"{self.base_url}/v1/channel-types"
        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
        )
        return response

    def detail_channel_type(self, channel_code: str):
        params = {"channel_type_code": channel_code}
        url = f"{self.base_url}/v1/channel-types"
        response = self.make_request(
            url,
            method="GET",
            headers=self.authentication_instance.headers,
            params=params,
        )
        return response

    def release_channel(
        self, channel_uuid: str, project_uuid: str, user_email: str
    ) -> None:
        params = {"user": user_email}
        url = f"{self.base_url}/api/v2/internals/channel/{channel_uuid}"
        self.make_request(
            url,
            method="DELETE",
            headers=self.authentication_instance.headers,
            params=params,
        )
        return None
