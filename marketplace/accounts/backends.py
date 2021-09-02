from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):  # pragma: no cover
    def create_user(self, claims):
        email = claims.get("email")

        user = self.UserModel.objects.create_user(email)
        user.save()

        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", "")
        user.save()

        return user
