"""
Service for interfacing with Facebook APIs.

This service facilitates the communication with Facebook's APIs, specifically focusing on
WhatsApp Business features and their configurations. The service provides functions for
enabling and disabling catalogs, toggling cart settings, and managing the visibility of
catalogs, among other actions.

Attributes:
    client (ClientType): An instance of a client responsible for making requests to Facebook's API.

Methods:
    catalog_creation(validated_data, app, vtex_app, user): Creates a new catalog associated
    with an app and returns the created,

    Catalog object along with the Facebook catalog ID.

    catalog_deletion(catalog): Deletes a catalog from Facebook and the local database.

    enable_catalog(catalog): Enables a catalog for use with WhatsApp Business.

    disable_catalog(catalog): Disables a catalog for use with WhatsApp Business.

    get_connected_catalog(app): Retrieves the ID of the catalog currently connected to a WhatsApp Business account.

    toggle_cart(app, enable=True): Toggles the shopping cart feature for WhatsApp Business.

    toggle_catalog_visibility(app, visible=True): Toggles the visibility of the catalog for WhatsApp Business.

    wpp_commerce_settings(app): Retrieves the WhatsApp commerce settings associated with a business phone number.

Private Methods:
    _get_app_facebook_credentials(app): Retrieves the Facebook credentials from the app's configuration.

    _create_catalog_object(data): Creates a Catalog object in the local database using provided data.

Raises:
    ValueError: If required Facebook credentials are missing from the app's configuration.
"""
from marketplace.wpp_products.models import Catalog


class FacebookService:
    def __init__(self, client):
        self.client = client

    # ================================
    # Public Methods
    # ================================

    def catalog_creation(self, validated_data, app, vtex_app, user):
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
            return catalog, response.get("id")

        return None, None

    def catalog_deletion(self, catalog):
        return self.client.destroy_catalog(catalog.facebook_catalog_id)

    def enable_catalog(self, catalog):
        waba_id = self.get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
        response = self.client.enable_catalog(
            waba_id=waba_id, catalog_id=catalog.facebook_catalog_id
        )
        success = response.get("success") is True
        return success, response

    def disable_catalog(self, catalog):
        waba_id = self.get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
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
