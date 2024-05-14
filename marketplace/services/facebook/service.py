import time
from marketplace.services.facebook.exceptions import FileNotSendValidationError
from marketplace.wpp_products.models import Catalog


class FacebookService:
    def __init__(self, client):
        self.client = client

    # ================================
    # Public Methods
    # ================================

    def create_vtex_catalog(self, validated_data, app, vtex_app, user):
        business_id = self._get_app_facebook_credentials(app=app).get("wa_business_id")
        response = self.client.create_catalog(business_id, validated_data["name"])

        if response and response.get("id"):
            data = {
                "app": app,
                "facebook_catalog_id": response.get("id"),
                "vtex_app": vtex_app,
                "name": validated_data["name"],
                "created_by": user,
            }
            catalog = self._create_catalog_object(data)
            self._update_connected_catalog_flag(vtex_app)
            return catalog, response.get("id")

        return None, None

    def catalog_deletion(self, catalog):
        return self.client.destroy_catalog(catalog.facebook_catalog_id)

    def enable_catalog(self, catalog):
        waba_id = self._get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
        response = self.client.enable_catalog(
            waba_id=waba_id, catalog_id=catalog.facebook_catalog_id
        )
        success = response.get("success") is True
        return success, response

    def disable_catalog(self, catalog):
        waba_id = self._get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
        response = self.client.disable_catalog(
            waba_id=waba_id, catalog_id=catalog.facebook_catalog_id
        )
        success = response.get("success") is True
        return success, response

    def get_connected_catalog(self, app):
        waba_id = self._get_app_facebook_credentials(app=app).get("wa_waba_id")
        response = self.client.get_connected_catalog(waba_id=waba_id)

        if len(response.get("data")) > 0:
            return response.get("data")[0].get("id")

        return []

    def toggle_cart(self, app, enable=True):
        business_phone_number_id = self._get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.toggle_cart(business_phone_number_id, enable)

    def toggle_catalog_visibility(self, app, visible=True):
        business_phone_number_id = self._get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.toggle_catalog_visibility(business_phone_number_id, visible)

    def wpp_commerce_settings(self, app):
        business_phone_number_id = self._get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.get_wpp_commerce_settings(business_phone_number_id)

    def create_product_feed(self, product_catalog_id, name):
        return self.client.create_product_feed(product_catalog_id, name)

    def upload_product_feed(
        self, feed_id, file, file_name, file_content_type, update_only=False
    ):
        return self.client.upload_product_feed(
            feed_id, file, file_name, file_content_type, update_only
        )

    def get_upload_status_by_feed(self, feed_id, upload_id) -> bool:
        return self.client.get_upload_status_by_feed(feed_id, upload_id)

    def get_in_process_uploads_by_feed(self, feed_id) -> str:
        return self.client.get_uploads_in_progress_by_feed(feed_id)

    def update_product_feed(self, feed_id, csv_file, file_name):
        response = self.upload_product_feed(
            feed_id, csv_file, file_name, "text/csv", update_only=True
        )
        if "id" not in response:
            raise FileNotSendValidationError()
        return response["id"]

    def uploads_in_progress(self, feed_id):
        upload_id = self.get_in_process_uploads_by_feed(feed_id)
        return upload_id if upload_id else False

    # ================================
    # Private Methods
    # ================================

    def _get_app_facebook_credentials(self, app):
        wa_business_id = app.config.get("wa_business_id")
        wa_waba_id = app.config.get("wa_waba_id")
        wa_phone_number_id = app.config.get("wa_phone_number_id")

        if not wa_business_id or not wa_waba_id or not wa_phone_number_id:
            raise ValueError(
                "Not found 'wa_waba_id', 'wa_business_id' or wa_phone_number_id in app.config "
            )
        return {
            "wa_business_id": wa_business_id,
            "wa_waba_id": wa_waba_id,
            "wa_phone_number_id": wa_phone_number_id,
        }

    def _create_catalog_object(self, data):
        return Catalog.objects.create(
            app=data.get("app"),
            facebook_catalog_id=data.get("facebook_catalog_id"),
            vtex_app=data.get("vtex_app"),
            name=data.get("name"),
            created_by=data.get("created_by"),
        )

    def _update_connected_catalog_flag(self, app) -> None:
        app.config["connected_catalog"] = True
        app.save()

    def _wait_for_upload_completion(self, feed_id, upload_id):
        wait_time = 5
        max_wait_time = 20 * 60
        total_wait_time = 0
        attempt = 1

        while total_wait_time < max_wait_time:
            upload_complete = self.get_upload_status_by_feed(feed_id, upload_id)
            if upload_complete:
                return True

            print(
                f"Attempt {attempt}: Waiting {wait_time} seconds "
                f"to get feed: {feed_id} upload {upload_id} status."
            )
            time.sleep(wait_time)
            total_wait_time += wait_time
            wait_time = min(wait_time * 2, 160)
            attempt += 1

        return False
