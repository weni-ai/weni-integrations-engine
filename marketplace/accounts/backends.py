from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):  # pragma: no cover
    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email).exclude(first_name="", last_name="")

    def create_user(self, claims):
        email = claims.get("email")

        user, _ = self.UserModel.objects.get_or_create(email=email)
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", "")
        user.save()

        return user
