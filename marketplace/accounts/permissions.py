from rest_framework import permissions
from django.contrib.auth.models import AnonymousUser

from .models import ProjectAuthorization


WRITE_METHODS = ["POST"]
MODIFY_METHODS = ["DELETE", "PATCH", "PUT"]
READ_METHODS = ["GET"]


class ProjectManagePermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)

        if not is_authenticated:
            return False

        if request.method in WRITE_METHODS:
            project_uuid = request.data.get("project_uuid")

            if project_uuid is None:
                return False

            try:
                authorization = request.user.authorizations.get(project_uuid=project_uuid)
            except ProjectAuthorization.DoesNotExist:
                return False

            return authorization.is_contributor or authorization.is_admin

        return True

    def has_object_permission(self, request, view, obj):
        if request.method not in WRITE_METHODS:
            try:
                authorization = request.user.authorizations.get(project_uuid=obj.project_uuid)
                is_admin = authorization.is_admin
                is_contributor = authorization.is_contributor
                is_viewer = authorization.is_viewer
            except ProjectAuthorization.DoesNotExist:
                return False

            if request.method in MODIFY_METHODS:
                return is_contributor or is_admin

            if request.method in READ_METHODS:
                return (is_viewer or is_contributor or is_admin)

        return True


class ProjectViewPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(request.user, AnonymousUser):
            return False
        try:
            authorization = request.user.authorizations.get(project_uuid=obj.project_uuid)
        except ProjectAuthorization.DoesNotExist:
            return False
        return authorization.is_viewer or authorization.is_contributor or authorization.is_admin
