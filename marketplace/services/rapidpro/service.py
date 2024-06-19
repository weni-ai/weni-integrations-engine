from marketplace.interfaces.rapidpro.protocol import RapidproClientProtocol


class RapidproService:
    def __init__(self, client: RapidproClientProtocol):
        self.client = client

    def create_notification(self, catalog, incident_name, exception):
        details = {
            "catalog_name": catalog.name,
            "catalog_id": catalog.facebook_catalog_id,
            "app_vtex_uuid": str(catalog.vtex_app.uuid),
            "error": str(exception),
        }
        return self.client.send_alert(incident_name, "integrations", details)
