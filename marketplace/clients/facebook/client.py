import time
import json

from django.conf import settings

from marketplace.clients.base import RequestClient
from marketplace.clients.decorators import retry_on_exception
from marketplace.interfaces.facebook.interfaces import (
    ProfileHandlerInterface,
    BusinessProfileHandlerInterface,
)


class FacebookAuthorization:
    BASE_URL = f"{settings.WHATSAPP_API_URL}/"

    def __init__(self, access_token):
        self.access_token = access_token

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    @property
    def get_url(self):
        return self.BASE_URL


class CatalogsRequests(FacebookAuthorization, RequestClient):
    def create_catalog(self, business_id, name, category="commerce"):
        url = self.get_url + f"{business_id}/owned_product_catalogs"
        data = {"name": name}
        if category:
            data["vertical"] = category

        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)

        return response.json()

    def destroy_catalog(self, catalog_id):
        url = self.get_url + f"{catalog_id}"

        headers = self._get_headers()
        response = self.make_request(url, method="DELETE", headers=headers)

        return response.json().get("success")

    @retry_on_exception()
    def create_product_feed(self, product_catalog_id, name):
        url = self.get_url + f"{product_catalog_id}/product_feeds"

        data = {"name": name}
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)

        return response.json()

    @retry_on_exception()
    def upload_product_feed(
        self, feed_id, file, file_name, file_content_type, update_only=False
    ):
        url = self.get_url + f"{feed_id}/uploads"

        headers = self._get_headers()
        files = {
            "file": (
                file_name,
                file,
                file_content_type,
            )
        }
        params = {"update_only": update_only}
        response = self.make_request(
            url, method="POST", headers=headers, params=params, files=files
        )
        return response.json()

    def create_product_feed_by_url(
        self, product_catalog_id, name, feed_url, file_type, interval, hour
    ):  # TODO: adjust this method
        url = self.get_url + f"{product_catalog_id}/product_feeds"

        schedule = {"interval": interval, "url": feed_url, "hour": str(hour)}

        data = {"name": name, "schedule": json.dumps(schedule), "file_type": file_type}

        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def get_all_upload_status(self, feed_id, max_attempts=10, wait_time=30):
        """
        Checks the upload status using long polling.

        Args:
            upload_id (str): The ID of the upload.
            max_attempts (int): Maximum number of polling attempts. Default is 10.
            wait_time (int): Wait time in seconds between polling attempts. Default is 30 seconds.

        Returns:
            bool or str: True if 'end_time' is found, otherwise a formatted error message.
        """
        url = self.get_url + f"{feed_id}/uploads"
        headers = self._get_headers()

        attempts = 0
        while attempts < max_attempts:
            response = self.make_request(url, method="GET", headers=headers)
            data = response.json()

            if data.get("data") and data["data"][0].get("end_time"):
                return True

            time.sleep(wait_time)
            attempts += 1

        total_wait_time = wait_time * max_attempts
        return (
            f"Unable to retrieve the upload completion status for feed {feed_id}. "
            f"Waited for a total of {total_wait_time} seconds."
        )

    def list_products_by_feed(self, feed_id):
        url = self.get_url + f"{feed_id}/products"

        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)

        return response.json()

    def list_all_products_by_feed(self, feed_id):
        url = self.get_url + f"{feed_id}/products"
        headers = self._get_headers()
        all_products = []

        while url:
            response = self.make_request(url, method="GET", headers=headers).json()
            all_products.extend(response.get("data", []))
            url = response.get("paging", {}).get("next")

        return all_products

    def list_all_catalogs(self, wa_business_id):
        url = self.get_url + f"{wa_business_id}/owned_product_catalogs"
        headers = self._get_headers()
        all_catalog_ids = []
        all_catalogs = []
        params = dict(limit=999)

        response = self.make_request(
            url, method="GET", headers=headers, params=params
        ).json()
        catalog_data = response.get("data", [])
        for item in catalog_data:
            all_catalog_ids.append(item["id"])
            all_catalogs.append(item)

        return all_catalog_ids, all_catalogs

    def destroy_feed(self, feed_id):
        url = self.get_url + f"{feed_id}"

        headers = self._get_headers()
        response = self.make_request(url, method="DELETE", headers=headers)

        return response.json().get("success")

    def get_connected_catalog(self, waba_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    def enable_catalog(self, waba_id, catalog_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        data = {"catalog_id": catalog_id}
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def disable_catalog(self, waba_id, catalog_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        data = {"catalog_id": catalog_id, "method": "delete"}
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def get_catalog_details(self, catalog_id):
        url = self.get_url + f"{catalog_id}"
        params = {"fields": "name,vertical"}
        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers, params=params)

        return response.json()

    def _update_commerce_settings(self, wa_phone_number_id, **settings):
        url = self.BASE_URL + f"{wa_phone_number_id}/whatsapp_commerce_settings"
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=settings)
        return response.json()

    def toggle_cart(self, wa_phone_number_id, enable=True):
        return self._update_commerce_settings(
            wa_phone_number_id, is_cart_enabled=enable
        )

    def toggle_catalog_visibility(self, wa_phone_number_id, make_visible=True):
        return self._update_commerce_settings(
            wa_phone_number_id, is_catalog_visible=make_visible
        )

    def get_wpp_commerce_settings(self, wa_phone_number_id):
        """
        Returns:
            "data": [
                {
                    "is_cart_enabled": true,
                    "is_catalog_visible": true,
                    "id": "270925148880242"
                }
            ]
        Or:
            "data": []
        """
        url = self.BASE_URL + f"{wa_phone_number_id}/whatsapp_commerce_settings"

        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    def get_upload_status_by_feed(self, feed_id, upload_id):
        url = self.get_url + f"{feed_id}/uploads"

        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        data = response.json()

        upload = next(
            (
                upload
                for upload in data.get("data", [])
                if upload.get("id") == upload_id
            ),
            None,
        )

        if upload:
            return "end_time" in upload

        return False

    def get_uploads_in_progress_by_feed(self, feed_id):
        url = self.get_url + f"{feed_id}/uploads"

        headers = self._get_headers()
        response = self.make_request(url, method="GET", headers=headers)
        data = response.json()
        upload = next(
            (
                upload
                for upload in data.get("data", [])
                if upload.get("end_time") is None
            ),
            None,
        )
        if upload:
            if "end_time" not in upload:
                return upload.get("id")


class TemplatesRequests(FacebookAuthorization, RequestClient):
    def create_template_message(
        self, waba_id: str, name: str, category: str, components: list, language: str
    ) -> dict:
        params = dict(
            name=name,
            category=category,
            components=str(components),
            language=language,
        )
        url = self.get_url + f"{waba_id}/message_templates"
        response = self.make_request(
            url, method="POST", params=params, headers=self._get_headers()
        )

        return response.json()

    def get_template_analytics(self, waba_id, fields):
        url = self.BASE_URL + f"{waba_id}/template_analytics"
        headers = self._get_headers()
        combined_data = {"data": {"data_points": []}}

        response = self.make_request(
            url, method="GET", headers=headers, params=fields
        ).json()

        data = response.get("data", [])
        data_points = data[0].get("data_points", [])
        combined_data["data"]["data_points"].extend(data_points)

        return combined_data

    def enable_template_insights(self, waba_id):
        url = self.BASE_URL + f"{waba_id}"
        params = {"is_enabled_for_insights": "true"}
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, params=params)
        return response.json()


class CloudProfileRequests(
    FacebookAuthorization, RequestClient, ProfileHandlerInterface
):
    _endpoint = "/whatsapp_business_profile"
    _fields = dict(
        fields="about,address,description,email,profile_picture_url,websites,vertical"
    )

    def __init__(self, phone_number_id: "str") -> None:
        self._phone_number_id = phone_number_id

    @property
    def _url(self) -> str:
        return settings.WHATSAPP_API_URL + f"/{self._phone_number_id}" + self._endpoint

    @property
    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def get_profile(self):
        response = self.make_request(
            method="GET", url=self._url, params=self._fields, headers=self._headers
        )
        content = response.json().get("data", [{}])[0]

        return dict(
            status=content.get("about"),
            email=content.get("email"),
            websites=content.get("websites"),
            address=content.get("address"),
            photo_url=content.get("profile_picture_url"),
            business=dict(
                description=content.get("description"), vertical=content.get("vertical")
            ),
        )

    def set_profile(self, **kwargs) -> None:
        # TODO: Validate photo change
        data = dict(messaging_product="whatsapp")
        data.update(kwargs)

        response = self.make_request(
            method="POST", url=self._url, json=data, headers=self._headers
        )
        return response.json()

    def delete_profile_photo(self):  # pragma: no cover
        ...


class PhoneNumbersRequests(FacebookAuthorization, RequestClient, object):
    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get_url(self, endpoint: str) -> str:
        return f"{settings.WHATSAPP_API_URL}/{endpoint}"

    def get_phone_numbers(self, waba_id: str) -> list:
        url = self._get_url(f"{waba_id}/phone_numbers")
        response = self._retry_request(
            method="GET", url=url, headers=self._headers, max_retries=6
        )
        return response.json().get("data", [])

    def _retry_request(self, method: str, url: str, headers: dict, max_retries: int):
        attempt = 0
        while attempt <= max_retries:
            try:
                response = self.make_request(method=method, url=url, headers=headers)
                if response.status_code == 200:
                    return response
            except Exception as e:
                print(f"Request failed: {e}, endpoint: [{method}]:{url}")

            wait_time = 2**attempt
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            attempt += 1

    def get_phone_number(self, phone_number_id: str):
        url = self._get_url(phone_number_id)
        response = self.make_request(method="GET", url=url, headers=self._headers)
        return response.json()


class PhotoAPIRequests(FacebookAuthorization, RequestClient, object):
    def _endpoint_url(self, endpoint: str) -> str:
        return f"{self.get_url()}/{endpoint}"

    def create_upload_session(self, file_length: int, file_type: str) -> str:
        url = self._endpoint_url(
            f"app/uploads?access_token={self.access_token}&file_length={file_length}&file_type={file_type}"
        )
        response = self.make_request(
            method="POST", url=url, headers=self._get_headers()
        )
        return response.json().get("id", "")

    def upload_photo(
        self, upload_session_id: str, photo: str, is_uploading: bool = False
    ) -> str:
        url = self._endpoint_url(upload_session_id)

        headers = {
            "Content-Type": photo.content_type,
            "Authorization": f"OAuth {self.access_token}",
        }

        if not is_uploading:
            headers["file_offset"] = "0"

        response = self.make_request(
            method="POST", url=url, headers=headers, data=photo.file.getvalue()
        )
        return response.json().get("h", "")

    def set_photo(self, photo, phone_number_id):
        url = self._endpoint_url(f"{phone_number_id}/whatsapp_business_profile")

        upload_session_id = self.create_upload_session(
            len(photo.file.getvalue()), file_type=photo.content_type
        )

        upload_handle = self.upload_photo(upload_session_id, photo)

        payload = {
            "messaging_product": "whatsapp",
            "profile_picture_handle": upload_handle,
        }

        response = self.make_request(
            method="POST", url=url, headers=self._get_headers(), json=payload
        )
        return response


class FacebookClient(
    CatalogsRequests,
    TemplatesRequests,
    CloudProfileRequests,
    PhoneNumbersRequests,
    PhotoAPIRequests,
):
    def __init__(self, access_token):
        # Initialize FacebookAuthorization with access_token
        FacebookAuthorization.__init__(self, access_token)
