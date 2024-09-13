from rest_framework import permissions
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from .models import ProjectAuthorization


WRITE_METHODS = ["POST"]
MODIFY_METHODS = ["DELETE", "PATCH", "PUT"]
READ_METHODS = ["GET"]


def is_crm_user(user):
    if not settings.ALLOW_CRM_ACCESS:
        return False

    if user.email not in settings.CRM_EMAILS_LIST:
        return False

    return True


class ProjectManagePermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)

        if not is_authenticated:
            return False

        if request.method in WRITE_METHODS:
            project_uuid = request.data.get("project_uuid")

            if project_uuid is None:
                project_uuid = request.headers.get("Project-Uuid")

            if project_uuid is None:
                return False

            try:
                authorization = request.user.authorizations.get(
                    project_uuid=project_uuid
                )
            except ProjectAuthorization.DoesNotExist:
                return False

            return authorization.is_contributor or authorization.is_admin

        return True

    def has_object_permission(self, request, view, obj):
        if request.method not in WRITE_METHODS:
            try:
                project_uuid = self._get_project_uuid_from_object(obj)
                authorization = request.user.authorizations.get(
                    project_uuid=project_uuid
                )
                is_admin = authorization.is_admin
                is_contributor = authorization.is_contributor
                is_viewer = authorization.is_viewer
            except ProjectAuthorization.DoesNotExist:
                return False

            if request.method in MODIFY_METHODS:
                return is_contributor or is_admin

            if request.method in READ_METHODS:
                return is_viewer or is_contributor or is_admin

        return True

    def _get_project_uuid_from_object(self, obj):
        """
        Helper method to retrieve the project UUID from the object or its related App.
        """
        if hasattr(obj, "project_uuid"):
            return obj.project_uuid
        if hasattr(obj, "app") and hasattr(obj.app, "project_uuid"):
            return obj.app.project_uuid
        return None


class ProjectViewPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = request.user.authorizations.get(
                project_uuid=obj.project_uuid
            )
        except ProjectAuthorization.DoesNotExist:
            return False
        return (
            authorization.is_viewer
            or authorization.is_contributor
            or authorization.is_admin
        )


class IsCRMUser(permissions.IsAuthenticated):
    def has_permission(self, request, view) -> bool:
        is_authenticated = super().has_permission(request, view)

        if not is_authenticated:
            return False

        return is_crm_user(request.user)

    def has_object_permission(self, request, view, obj):
        return is_crm_user(request.user)
