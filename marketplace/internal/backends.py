from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class InternalOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def check_module_permission(self, claims, user) -> None:
        if claims.get("can_communicate_internally", False):
            content_type = ContentType.objects.get_for_model(self.UserModel)
            permission, _ = Permission.objects.get_or_create(
                codename="can_communicate_internally",
                name="can communicate internally",
                content_type=content_type,
            )
            if not user.has_perm("auth.can_communicate_internally"):
                user.user_permissions.add(permission)

    def get_username(self, claims):
        username = claims.get("email")
        if username:
            return username
        return super().get_username(claims=claims)

    def create_user(self, claims):
        email = claims.get("email")
        username = self.get_username(claims)

        user, _ = self.UserModel.objects.get_or_create(email=email, username=username)

        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")

        user.save()

        self.check_module_permission(claims, user)

        return user
