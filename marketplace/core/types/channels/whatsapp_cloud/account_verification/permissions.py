"""Permission resolving project authorization from the App in the URL kwargs."""

from rest_framework import permissions

from marketplace.accounts.models import ProjectAuthorization
from marketplace.accounts.permissions import (
    MODIFY_METHODS,
    READ_METHODS,
    WRITE_METHODS,
)
from marketplace.applications.models import App


class AppProjectManagePermission(permissions.IsAuthenticated):
    """Authorize app-scoped endpoints by reading the App referenced in the URL.

    Unlike ``ProjectManagePermission``, this class does not require the caller
    to pass ``project_uuid`` in the request body for POST: it derives the project
    from ``view.kwargs['app_uuid']`` and validates the user authorization there.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        app_uuid = view.kwargs.get("app_uuid")
        if app_uuid is None:
            return False

        app = App.objects.filter(uuid=app_uuid).only("project_uuid").first()
        if app is None:
            return False

        try:
            authorization = request.user.authorizations.get(
                project_uuid=app.project_uuid
            )
        except ProjectAuthorization.DoesNotExist:
            return request.user.has_perm("accounts.can_communicate_internally")

        if request.method in WRITE_METHODS or request.method in MODIFY_METHODS:
            return authorization.is_contributor or authorization.is_admin
        if request.method in READ_METHODS:
            return (
                authorization.is_viewer
                or authorization.is_contributor
                or authorization.is_admin
            )
        return False  # pragma: no cover
