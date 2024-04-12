"""Client for connection with flows"""

from django.conf import settings

from marketplace.clients.base import RequestClient


class InternalAuthentication(RequestClient):
    def __get_module_token(self):
        data = {
            "client_id": settings.OIDC_RP_CLIENT_ID,
            "client_secret": settings.OIDC_RP_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        request = self.make_request(
            url=settings.OIDC_OP_TOKEN_ENDPOINT, method="POST", data=data
        )

        token = request.json().get("access_token")

        return f"Bearer {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }


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

    def update_catalogs(
        self, flow_object_uuid, catalogs_data, requests_data, response_data, urls_data
    ):
        data = {
            "data": catalogs_data,
            "requests": requests_data,
            "responses": response_data,
            "urls": urls_data,
        }
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

    def update_facebook_templates(
        self, flow_object_uuid, fba_templates, request, response_data, url_request
    ):
        data = {
            "data": fba_templates,
            "request": request,
            "response": response_data,
            "url": url_request,
        }
        url = f"{self.base_url}/template/{flow_object_uuid}/"

        response = self.make_request(
            url,
            method="PATCH",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response

    def update_facebook_templates_webhook(
        self, flow_object_uuid, webhook, template_data, template_name
    ):
        data = {
            "template_name": template_name,
            "webhook": webhook,
            "template_data": template_data,
        }
        url = f"{self.base_url}/template/{flow_object_uuid}/template-sync/"
        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response
