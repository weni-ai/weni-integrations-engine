from typing import Type

from django.db.models import QuerySet

from marketplace.applications.models import App


class ListWhatsAppCloudChannelsUseCase:
    """Return every WhatsApp Cloud channel (App) of a project.

    The slug is referenced by literal (instead of importing
    `WhatsAppCloudType`) to avoid the `type -> views -> usecases` import cycle,
    matching how other modules query these apps.
    """

    CODE = "wpp-cloud"

    def __init__(self, app_model: Type[App] = App):
        self._app_model = app_model

    def execute(self, project_uuid) -> "QuerySet[App]":
        return self._app_model.objects.filter(code=self.CODE, project_uuid=project_uuid)
