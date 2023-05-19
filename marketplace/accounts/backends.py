from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

User = get_user_model()


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):  # pragma: no cover
    def check_module_permission(self, claims, user) -> None:
        if claims.get("can_communicate_internally", False):
            content_type = ContentType.objects.get_for_model(User)
            permission, created = Permission.objects.get_or_create(
                codename="can_communicate_internally",
                name="can communicate internally",
                content_type=content_type,
            )
            if not user.has_perm("authentication.can_communicate_internally"):
                user.user_permissions.add(permission)

    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email).exclude(
            first_name="", last_name=""
        )

    def create_user(self, claims):
        email = claims.get("email")

        user, _ = self.UserModel.objects.get_or_create(email=email)
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        self.check_module_permission(claims, user)

        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", "")
        user.save()

        self.check_module_permission(claims, user)

        return user
