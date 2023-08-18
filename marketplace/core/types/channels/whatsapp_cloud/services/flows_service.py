from marketplace.flows.client import FlowsClient


class FlowsService:
    def __init__(self):
        self.client = FlowsClient()

    def _update_flows_config(self, app):
        """
        synchronize Flows channel configuration.
        """
        detail_channel = self.client.detail_channel(app.flow_object_uuid)
        flows_config = detail_channel["config"]
        flows_config["catalogs"] = app.config["catalogs"]
        self.client.update_config(
            data=flows_config, flow_object_uuid=app.flow_object_uuid
        )

    def update_app_and_flows_with_catalog(self, app, catalog, catalog_id):
        if "catalogs" not in app.config:
            app.config["catalogs"] = []

        app.config["catalogs"].append({"facebook_catalog_id": catalog_id})
        app.save()

        self._update_flows_config(app)

        return catalog

    def remove_catalog_from_app(self, catalog):
        if "catalogs" in catalog.app.config:
            catalogs_to_remove = [
                idx
                for idx, catalog_entry in enumerate(catalog.app.config["catalogs"])
                if catalog_entry.get("facebook_catalog_id")
                == catalog.facebook_catalog_id
            ]

            for idx in reversed(catalogs_to_remove):
                del catalog.app.config["catalogs"][idx]

            catalog.app.save()

            self._update_flows_config(catalog.app)
