import time
import json

from django.conf import settings

from marketplace.clients.base import RequestClient

WHATSAPP_VERSION = settings.WHATSAPP_VERSION
ACCESS_TOKEN = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN


class FacebookAuthorization:
    BASE_URL = f"https://graph.facebook.com/{WHATSAPP_VERSION}/"

    def __init__(self):
        self.access_token = ACCESS_TOKEN

    def _get_user_token(self, app):
        if app.config.get("wa_user_token"):
            return app.config.get("wa_user_token")
        return None

    def _get_headers(self, user_token):
        if user_token:
            headers = {"Authorization": f"Bearer {user_token}"}
        else:
            headers = {"Authorization": f"Bearer {self.access_token}"}
        return headers

    @property
    def get_url(self):
        return self.BASE_URL


class FacebookClient(FacebookAuthorization, RequestClient):
    # Product Catalog
    def create_catalog(self, app, business_id, name, category=None):
        url = self.get_url + f"{business_id}/owned_product_catalogs"
        data = {"name": name}
        if category:
            data["vertical"] = category

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="POST", headers=headers, data=data)

        return response.json()

    def destroy_catalog(self, app, catalog_id):
        url = self.get_url + f"{catalog_id}"

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="DELETE", headers=headers)

        return response.json().get("success")

    def create_product_feed(self, app, product_catalog_id, name):
        url = self.get_url + f"{product_catalog_id}/product_feeds"

        data = {"name": name}
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="POST", headers=headers, data=data)

        return response.json()

    def upload_product_feed(self, app, feed_id, file):
        url = self.get_url + f"{feed_id}/uploads"

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        files = {
            "file": (
                file.name,
                file,
                file.content_type,
            )
        }
        response = self.make_request(url, method="POST", headers=headers, files=files)
        return response.json()

    def create_product_feed_via_url(
        self, app, product_catalog_id, name, feed_url, file_type, interval, hour
    ):  # TODO: adjust this method
        url = self.get_url + f"{product_catalog_id}/product_feeds"

        schedule = {"interval": interval, "url": feed_url, "hour": str(hour)}

        data = {"name": name, "schedule": json.dumps(schedule), "file_type": file_type}

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def get_upload_status(self, app, feed_id, max_attempts=10, wait_time=30):
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
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)

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

    def list_products_by_feed(self, app, feed_id):
        url = self.get_url + f"{feed_id}/products"

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="GET", headers=headers)

        return response.json()

    def list_all_products_by_feed(self, app, feed_id):
        url = self.get_url + f"{feed_id}/products"
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        all_products = []

        while url:
            response = self.make_request(url, method="GET", headers=headers).json()
            all_products.extend(response.get("data", []))
            url = response.get("paging", {}).get("next")

        return all_products

    def list_all_catalogs(self, app, wa_business_id):
        url = self.get_url + f"{wa_business_id}/owned_product_catalogs"
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        all_catalog_ids = []
        all_catalogs = []

        while url:
            response = self.make_request(url, method="GET", headers=headers).json()
            catalog_data = response.get("data", [])
            for item in catalog_data:
                all_catalog_ids.append(item["id"])
                all_catalogs.append(item)

            url = response.get("paging", {}).get("next")

        return all_catalog_ids, all_catalogs

    def destroy_feed(self, app, feed_id):
        url = self.get_url + f"{feed_id}"

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="DELETE", headers=headers)

        return response.json().get("success")

    def get_connected_catalog(self, app, waba_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    def enable_catalog(self, app, waba_id, catalog_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        data = {"catalog_id": catalog_id}
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def disable_catalog(self, app, waba_id, catalog_id):
        url = self.get_url + f"{waba_id}/product_catalogs"
        data = {"catalog_id": catalog_id, "method": "delete"}
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="POST", headers=headers, data=data)
        return response.json()

    def get_catalog_details(self, app, catalog_id):
        url = self.get_url + f"{catalog_id}"
        params = {"fields": "name,vertical"}
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="GET", headers=headers, params=params)

        return response.json()

    def _update_commerce_settings(self, app, wa_phone_number_id, **settings):
        url = self.BASE_URL + f"{wa_phone_number_id}/whatsapp_commerce_settings"
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
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

    def get_wpp_commerce_settings(self, app, wa_phone_number_id):
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

        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="GET", headers=headers)
        return response.json()

    # Whatsapp Templates
    def get_template_analytics(self, app, waba_id, fields):
        url = self.BASE_URL + f"{waba_id}/template_analytics"
        user_token = self._get_user_token(app)
        headers = self._get_headers(user_token)
        response = self.make_request(url, method="GET", headers=headers, params=fields)
        return response.json()
