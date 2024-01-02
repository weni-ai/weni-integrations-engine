from django.core.exceptions import MultipleObjectsReturned

from marketplace.services.vtex.exceptions import (
    NoVTEXAppConfiguredException,
    MultipleVTEXAppsConfiguredException,
)
from marketplace.applications.models import App


class AppVtexManager:
    def get_vtex_app_or_error(self, project_uuid):
        try:
            app_vtex = App.objects.get(
                code="vtex", project_uuid=str(project_uuid), configured=True
            )
            return app_vtex
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()
        except MultipleObjectsReturned:
            raise MultipleVTEXAppsConfiguredException()

    def initial_sync_products_completed(self, app: App):
        try:
            app.config["initial_sync_completed"] = True
            app.save()
            return True
        except Exception as e:
            raise e
