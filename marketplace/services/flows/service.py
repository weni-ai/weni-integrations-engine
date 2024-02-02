class FlowsService:
    def __init__(self, client):
        self.client = client

    def update_vtex_integration_status(self, project_uuid, user_email, action):
        return self.client.update_vtex_integration_status(
            project_uuid, user_email, action
        )

    def update_vtex_products(self, products: list, flow_object_uuid, dict_catalog):
        return self.client.update_vtex_products(
            products, flow_object_uuid, dict_catalog
        )

    def update_webhook_vtex_products(self, products: list, app):
        for catalog in app.catalogs.all():
            self.update_vtex_products(
                products, str(app.flow_object_uuid), catalog.facebook_catalog_id
            )

        return True
