from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model


class PermissionTestCaseMixin:
    """
    Mixin that provides utility methods to manage user permissions in test cases.
    """

    def grant_permission(self, user, codename, name=None, app_label="accounts"):
        """
        Grants a specific permission to a user.
        """
        content_type = ContentType.objects.get_for_model(get_user_model())
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            name=name or codename.replace("_", " ").capitalize(),
            content_type=content_type,
        )
        user.user_permissions.add(permission)

    def revoke_permission(self, user, codename):
        """
        Removes a specific permission from a user.
        """
        try:
            permission = Permission.objects.get(codename=codename)
            user.user_permissions.remove(permission)
        except Permission.DoesNotExist:
            pass

    def clear_permissions(self, user):
        """
        Clears all permissions from a user.
        """
        user.user_permissions.clear()
