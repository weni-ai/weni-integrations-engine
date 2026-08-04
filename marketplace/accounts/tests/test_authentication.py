import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from weni_commons.auth import WeniAuthContext

from marketplace.accounts.authentication import WeniModuleAuthentication


User = get_user_model()


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


class WeniModuleAuthenticationTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_pem, cls.public_pem = _generate_rsa_keypair()

    def setUp(self):
        self.factory = APIRequestFactory()
        self.authentication = WeniModuleAuthentication()

    def _build_request(self, payload):
        token = jwt.encode(payload, self.private_pem, algorithm="RS256")
        return self.factory.get("/", HTTP_X_WENI_AUTH=token)

    def _default_payload(self, **overrides):
        payload = {
            "project_uuid": "5f3b2c10-0000-0000-0000-000000000000",
            "user_email": "jwt-user@weni.ai",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        payload.update(overrides)
        return payload

    def test_returns_none_when_no_token(self):
        with override_settings(JWT_PUBLIC_KEY=self.public_pem):
            result = self.authentication.authenticate(self.factory.get("/"))

        self.assertIsNone(result)

    def test_jwt_resolves_and_provisions_django_user(self):
        request = self._build_request(self._default_payload())

        with override_settings(JWT_PUBLIC_KEY=self.public_pem):
            user, auth = self.authentication.authenticate(request)

        self.assertIsInstance(auth, WeniAuthContext)
        self.assertTrue(auth.is_jwt)
        self.assertEqual(auth.project_uuid, "5f3b2c10-0000-0000-0000-000000000000")
        self.assertIsInstance(user, User)
        self.assertEqual(user.email, "jwt-user@weni.ai")
        self.assertTrue(User.objects.filter(email="jwt-user@weni.ai").exists())

    def test_jwt_reuses_existing_django_user(self):
        existing = User.objects.create_user(email="jwt-user@weni.ai")
        request = self._build_request(self._default_payload())

        with override_settings(JWT_PUBLIC_KEY=self.public_pem):
            user, _ = self.authentication.authenticate(request)

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(User.objects.filter(email="jwt-user@weni.ai").count(), 1)

    def test_expired_token_is_rejected(self):
        payload = self._default_payload(
            exp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        request = self._build_request(payload)

        with override_settings(JWT_PUBLIC_KEY=self.public_pem):
            with self.assertRaises(AuthenticationFailed):
                self.authentication.authenticate(request)

    def test_keycloak_caller_keeps_the_user_resolved_by_oidc(self):
        oidc_user = User.objects.create_user(email="keycloak-user@weni.ai")
        backend = MagicMock()
        backend.get_or_create_user.return_value = oidc_user
        backend.verify_token.return_value = {"email": oidc_user.email}
        authentication = WeniModuleAuthentication(oidc_backend=backend)
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer not-a-weni-jwt")

        with override_settings(JWT_PUBLIC_KEY=self.public_pem):
            user, auth = authentication.authenticate(request)

        self.assertTrue(auth.is_keycloak)
        self.assertEqual(user.pk, oidc_user.pk)
        self.assertEqual(User.objects.count(), 1)
