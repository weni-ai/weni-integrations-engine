import requests

from django.conf import settings
from rest_framework import permissions

from marketplace.applications.models import App
from marketplace


class IsProjectAdmin(permissions.BasePermission):

    def __init__(self):
        self.base_url = settings.FLOWS_REST_ENDPOINT
        self.authentication_instance = InternalAuthentication()

    def has_permission(self, request, view):
        app_uuid = request.parser_context.get("kwargs").get("app_uuid")

        app = App.objects.get(uuid=app_uuid)

        org_administrators = requests.get(
            url=f"{self.base_url}/api/v2/internals/orgs/{app.project_uuid}/",
            headers=self.authentication_instance.headers,
        ).json().get("administrators")

        administrators_emails = [admin.get("email") for admin in org_administrators]

        return (request.user in administrators_emails)
