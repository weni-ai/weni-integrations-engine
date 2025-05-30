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
        self,
        flow_object_uuid: str,
        template_data: dict,
        template_name: str,
        webhook: dict = None,
    ):
        return self.client.update_facebook_templates_webhook(
            flow_object_uuid, template_data, template_name, webhook
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

    def create_channel(
        self, user_email: str, project_uuid: str, data: dict, channeltype_code: str
    ) -> dict:
        return self.client.create_channel(
            user_email, project_uuid, data, channeltype_code
        )

    def update_config(self, config: dict, flow_object_uuid: str):
        return self.client.update_config(config, flow_object_uuid)
