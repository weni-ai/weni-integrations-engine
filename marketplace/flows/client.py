"""Client for connection with flows"""

import requests

from django.conf import settings

from rest_framework.exceptions import APIException


class FlowsClient:  # TODO: Migrate all methods to marketplace.clients.flows.client
    def __init__(self):
        self.base_url = settings.FLOWS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def list_channel_types(self, channel_code):
        if channel_code:
            url = f"{self.base_url}/api/v2/internals/channels/{str(channel_code)}"
        else:
            url = f"{self.base_url}/api/v2/internals/channels"

        response = self.make_request(
            url, method="GET", headers=self.authentication_instance.headers
        )

        return response

    def detail_channel(self, flow_object_uuid):
        url = f"{self.base_url}/api/v2/internals/channel/{str(flow_object_uuid)}"

        response = self.make_request(
            url, method="GET", headers=self.authentication_instance.headers
        )
        return response.json()

    def detail_external(self, flow_object_uuid):
        url = f"{self.base_url}/api/v2/internals/externals/{str(flow_object_uuid)}"

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
            data=payload,
        )
        return response

    def update_external_config(self, data, flow_object_uuid):
        payload = {"config": data}
        url = f"{self.base_url}/api/v2/internals/externals/{flow_object_uuid}/"

        response = self.make_request(
            url,
            method="PATCH",
            headers=self.authentication_instance.headers,
            data=payload,
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
            data=body,
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
            data=body,
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

    def make_request(self, url: str, method: str, headers=None, data=None, params=None):
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=60,
            params=params,
        )
        if response.status_code >= 500:
            raise CustomAPIException(status_code=response.status_code)
        elif response.status_code >= 400:
            raise CustomAPIException(
                detail=response.json() if response.text else response.text,
                status_code=response.status_code,
            )

        return response


class InternalAuthentication:
    def __get_module_token(self):
        try:
            request = requests.post(
                url=settings.OIDC_OP_TOKEN_ENDPOINT,
                data={
                    "client_id": settings.OIDC_RP_CLIENT_ID,
                    "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                },
                timeout=60,
            )
            request.raise_for_status()

        except requests.exceptions.HTTPError as exception:
            # Handles HTTP exceptions
            raise APIException(
                detail=f"HTTPError: {str(exception)}", code=request.status_code
            ) from exception
        except requests.exceptions.RequestException as exception:
            # Handle general network exceptions
            raise APIException(
                detail=f"RequestException: {str(exception)}", code=request.status_code
            ) from exception

        token = request.json().get("access_token")

        return f"Bearer {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }


class CustomAPIException(APIException):
    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail, code)
        self.status_code = status_code or self.status_code
