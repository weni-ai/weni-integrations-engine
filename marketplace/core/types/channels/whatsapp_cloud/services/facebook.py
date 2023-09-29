"""
Service for interfacing with Facebook APIs.

This service facilitates the communication with Facebook's APIs, specifically focusing on
WhatsApp Business features and their configurations. The service provides functions for
enabling and disabling catalogs, toggling cart settings, and managing the visibility of
catalogs, among other actions.

Attributes:
    client (ClientType): An instance of a client responsible for making requests to Facebook's API.

Methods:
    get_app_facebook_credentials(app): Retrieves the Facebook credentials from the app's configuration.

    enable_catalog(catalog): Enables a catalog for a given app.

    disable_catalog(catalog): Disables a catalog for a given app.

    get_connected_catalog(app): Gets the currently connected catalog ID for a given app.

    toggle_cart(app, enable=True): Toggles the cart setting for WhatsApp Business.

    toggle_catalog_visibility(app, visible=True): Toggles the visibility of the catalog on WhatsApp Business.

    wpp_commerce_settings(app): Retrieves the WhatsApp commerce settings associated with a business phone number.

Raises:
    ValueError: If required Facebook credentials are missing from the app's configuration.
"""


class FacebookService:
    def __init__(self, client):
        self.client = client

    def get_app_facebook_credentials(self, app):
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

    def enable_catalog(self, catalog):
        waba_id = self.get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
        return self.client.enable_catalog(
            waba_id=waba_id, catalog_id=catalog.facebook_catalog_id
        )

    def disable_catalog(self, catalog):
        waba_id = self.get_app_facebook_credentials(app=catalog.app).get("wa_waba_id")
        return self.client.disable_catalog(
            waba_id=waba_id, catalog_id=catalog.facebook_catalog_id
        )

    def get_connected_catalog(self, app):
        waba_id = self.get_app_facebook_credentials(app=app).get("wa_waba_id")
        response = self.client.get_connected_catalog(waba_id=waba_id)
        return response.get("data")[0].get("id") if response else []

    def toggle_cart(self, app, enable=True):
        business_phone_number_id = self.get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.toggle_cart(business_phone_number_id, enable)

    def toggle_catalog_visibility(self, app, visible=True):
        business_phone_number_id = self.get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.toggle_catalog_visibility(business_phone_number_id, visible)

    def wpp_commerce_settings(self, app):
        business_phone_number_id = self.get_app_facebook_credentials(app=app).get(
            "wa_phone_number_id"
        )
        return self.client.get_wpp_commerce_settings(business_phone_number_id)
