from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog


class FacebookService:
    def __init__(self):
        self.client = FacebookClient()

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

    def catalog_creation(self, validated_data, app, user):
        business_id = self.get_app_facebook_credentials(app=app).get("wa_business_id")
        response = self.client.create_catalog(
            business_id, validated_data["name"], validated_data["category"]
        )

        if response and response.get("id"):
            catalog = Catalog.objects.create(
                app=app,
                facebook_catalog_id=response.get("id"),
                name=validated_data["name"],
                created_by=user,
            )
            return catalog, response.get("id")

        return None, None

    def catalog_deletion(self, catalog):
        return self.client.destroy_catalog(catalog.facebook_catalog_id)

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
