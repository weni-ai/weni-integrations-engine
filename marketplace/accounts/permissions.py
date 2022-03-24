from rest_framework import permissions
from django.contrib.auth.models import AnonymousUser

from .models import ProjectAuthorization


WRITE_METHODS = ["POST"]
OBJECT_METHODS = ["DELETE", "PATCH", "PUT"]


class ProjectManagePermission(permissions.BasePermission):
    def has_permission(self, request, view):
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
        if request.method in OBJECT_METHODS:
            if isinstance(request.user, AnonymousUser):
                return False
            try:
                authorization = request.user.authorizations.get(project_uuid=obj.project_uuid)
            except ProjectAuthorization.DoesNotExist:
                return False
            return authorization.can_contribute(obj) or authorization.is_admin

        return True
