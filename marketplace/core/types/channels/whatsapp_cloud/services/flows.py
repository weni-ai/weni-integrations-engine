class FlowsService:
    def __init__(self, client):
        self.client = client

    def _update_flows_config(self, app, key):
        """
        synchronize Flows channel configuration.
        """
        detail_channel = self.client.detail_channel(app.flow_object_uuid)
        flows_config = detail_channel["config"]
        flows_config[key] = app.config[key]

        self.client.update_config(
            data=flows_config, flow_object_uuid=app.flow_object_uuid
        )

        return True

    def update_treshold(self, app, treshold):
        app.config["treshold"] = treshold
        app.save()

        return self._update_flows_config(app, "treshold")

    def update_active_catalog(self, app, fba_catalog_id):
        app.config["catalog_id"] = fba_catalog_id
        app.save()

        return self._update_flows_config(app, "catalog_id")
