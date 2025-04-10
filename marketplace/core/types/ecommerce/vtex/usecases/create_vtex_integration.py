from marketplace.applications.models import App
from typing import TypedDict, Optional


class CreateVtexIntegrationUseCase:
    class CreateVtexData(TypedDict):
        account: str
        store_type = Optional[str]

    @staticmethod
    def configure_app(app: App, data: CreateVtexData) -> App:
        app.config["account"] = data.get("account")
        app.config["store_type"] = data.get("store_type")
        app.config["initial_sync_completed"] = False
        app.config["connected_catalog"] = False
        app.configured = True
        app.save()
        return app
