import json

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from django.conf import settings
from django.core.cache import cache

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


User = get_user_model()


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):  # pragma: no cover
    cache_token = settings.OIDC_CACHE_TOKEN
    cache_ttl = settings.OIDC_CACHE_TTL

    def get_userinfo(self, access_token, *args):
        """
        Cache userinfo in Redis by access_token.

        Args:
            access_token: OIDC access token

        Returns:
            dict: User information from OIDC provider
        """
        if not self.cache_token:
            return super().get_userinfo(access_token, *args)

        redis_connection = get_redis_connection()
        userinfo = redis_connection.get(access_token)

        if userinfo is not None:
            return json.loads(userinfo)

        userinfo = super().get_userinfo(access_token, *args)
        redis_connection.set(access_token, json.dumps(userinfo), self.cache_ttl)

        return userinfo

    def check_module_permission(self, claims, user) -> None:
        """
        Check and grant module permission for internal communication.

        Args:
            claims: OIDC claims dictionary
            user: User instance to grant permission
        """
        if claims.get("can_communicate_internally", False):
            content_type = ContentType.objects.get_for_model(User)
            permission, _ = Permission.objects.get_or_create(
                codename="can_communicate_internally",
                name="can communicate internally",
                content_type=content_type,
            )
            if not user.has_perm("authentication.can_communicate_internally"):
                user.user_permissions.add(permission)

    def _get_cache_key(self, email: str) -> str:
        """
        Generate cache key for user lookup by email.

        Args:
            email: User email address

        Returns:
            str: Cache key in format 'oidc_user_by_email:{email}'
        """
        return f"oidc_user_by_email:{email.strip().lower()}"

    def filter_users_by_claims(self, claims):
        """
        Return all users matching the specified email with cache support.

        Args:
            claims: OIDC claims dictionary containing email

        Returns:
            QuerySet or list: Users matching the email criteria
        """
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()

        cache_key = self._get_cache_key(email)
        cached_user = cache.get(cache_key)
        if cached_user:
            return [cached_user]

        qs = self.UserModel.objects.filter(email__iexact=email).exclude(
            first_name="", last_name=""
        )
        user = qs.first()
        if user:
            cache.set(cache_key, user, self.cache_ttl)
            return [user]

        return self.UserModel.objects.none()

    def create_user(self, claims):
        """
        Create or update user from OIDC claims with cache invalidation.

        Args:
            claims: OIDC claims dictionary

        Returns:
            User: Created or updated user instance
        """
        email = claims.get("email")
        user, created = self.UserModel.objects.get_or_create(email=email)

        # Only update fields if user was just created or if fields have values
        if created or claims.get("given_name") or claims.get("family_name"):
            user.first_name = claims.get("given_name", "")
            user.last_name = claims.get("family_name", "")
            user.save()

        # Only invalidate cache if user was updated (not created)
        if not created:
            cache.delete(self._get_cache_key(email))

        self.check_module_permission(claims, user)

        return user

    def update_user(self, user, claims):
        """
        Update user from OIDC claims with cache invalidation.

        Args:
            user: User instance to update
            claims: OIDC claims dictionary

        Returns:
            User: Updated user instance
        """
        old_email = user.email
        new_email = claims.get("email", "")
        old_first_name = user.first_name
        old_last_name = user.last_name
        new_first_name = claims.get("given_name", "")
        new_last_name = claims.get("family_name", "")

        # Track if any changes were made
        has_changes = False

        # Only update fields if they have values and are different
        if new_email and old_email != new_email:
            user.email = new_email
            has_changes = True

        if new_first_name and old_first_name != new_first_name:
            user.first_name = new_first_name
            has_changes = True

        if new_last_name and old_last_name != new_last_name:
            user.last_name = new_last_name
            has_changes = True

        # Only save if there were actual changes
        if has_changes:
            user.save()

        # Only invalidate cache if email actually changed
        if old_email != new_email:
            cache.delete(self._get_cache_key(old_email))
            cache.delete(self._get_cache_key(new_email))

        self.check_module_permission(claims, user)

        return user
