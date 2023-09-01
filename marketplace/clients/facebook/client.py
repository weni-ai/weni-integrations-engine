import time

from django.conf import settings

from marketplace.clients.base import RequestClient

WHATSAPP_VERSION = settings.WHATSAPP_VERSION
ACCESS_TOKEN = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN


class FacebookAuthorization:
    BASE_URL = f"https://graph.facebook.com/{WHATSAPP_VERSION}/"

    def __init__(self):
        self.access_token = ACCESS_TOKEN

    def _get_headers(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        return headers

    @property
    def get_url(self):
        return self.BASE_URL


class FacebookClient(FacebookAuthorization, RequestClient):
    def create_catalog(self, business_id, name, category=None):
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

    def create_product_feed(self, product_catalog_id, name):
        url = self.get_url + f"{product_catalog_id}/product_feeds"

        data = {"name": name}
        headers = self._get_headers()
        response = self.make_request(url, method="POST", headers=headers, data=data)

        return response.json()

    def upload_product_feed(self, feed_id, file):
        url = self.get_url + f"{feed_id}/uploads"

        headers = self._get_headers()
        files = {
            "file": (
                file.name,
                file,
                file.content_type,
            )
        }
        response = self.make_request(url, method="POST", headers=headers, files=files)
        return response.json()

    def get_upload_status(self, feed_id, max_attempts=10, wait_time=30):
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

    def destroy_feed(self, feed_id):
        url = self.get_url + f"{feed_id}"

        headers = self._get_headers()
        response = self.make_request(url, method="DELETE", headers=headers)

        return response.json().get("success")
