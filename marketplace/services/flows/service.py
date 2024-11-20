class FlowsService:
    def __init__(self, client):
        self.client = client

    def update_vtex_integration_status(self, project_uuid, user_email, action):
        return self.client.update_vtex_integration_status(
            project_uuid, user_email, action
        )

    def update_vtex_ads_status(self, app, vtex_ads, action):
        return self.client.update_vtex_ads_status(
            app.project_uuid, app.created_by.email, action, vtex_ads
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

    def update_facebook_templates_webhook(
        self, flow_object_uuid, webhook, template_data, template_name
    ):
        return self.client.update_facebook_templates_webhook(
            flow_object_uuid, webhook, template_data, template_name
        )

    def _update_flows_config(self, app):
        """
        synchronize Flows channel configuration.
        """
        detail_channel = self.client.detail_channel(app.flow_object_uuid)
        flows_config = detail_channel["config"]
        flows_config["treshold"] = app.config["treshold"]

        self.client.update_config(
            data=flows_config, flow_object_uuid=app.flow_object_uuid
        )

        return True

    def update_treshold(self, app, treshold):
        app.config["treshold"] = treshold
        app.save()
        return self._update_flows_config(app)

    def update_catalog_to_active(self, app, fba_catalog_id):
        return self.client.update_status_catalog(
            str(app.flow_object_uuid), fba_catalog_id, is_active=True
        )

    def update_catalog_to_inactive(self, app, fba_catalog_id):
        return self.client.update_status_catalog(
            str(app.flow_object_uuid), fba_catalog_id, is_active=False
        )

    def create_wac_channel(
        self, user: str, project_uuid: str, phone_number_id: str, config: dict
    ) -> dict:
        return self.client.create_wac_channel(
            user, project_uuid, phone_number_id, config
        )

    # TODO: need implement methods on client
    def create_facebook_template(self, flow_object_uuid, template_data, template_name):
        return self.client.create_facebook_template(
            flow_object_uuid, template_data, template_name
        )

    # TODO: need implement methods on client
    def delete_facebook_template(self, flow_object_uuid, template_data, template_name):
        return self.client.delete_facebook_template(
            flow_object_uuid, template_data, template_name
        )
