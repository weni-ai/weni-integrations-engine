"""
Responsible for speeding up the generation of a local '.env' configuration file.
OBS: Run in development environment only
"""

import os

from django.core.management.utils import get_random_secret_key


# TODO: Remove escapes

CONFIG_STRING = f"""
DEBUG=True
ALLOWED_HOSTS=\"*\"
SECRET_KEY=\"{get_random_secret_key()}\"
DATABASE_URL=\"postgresql://marketplace:marketplace@localhost:5432/marketplace\"
LANGUAGE_CODE=\"en-us\"
TIME_ZONE=\"America/Maceio\"
MEDIA_ROOT=\"media/\"

# if USE_S3 is True uses AWS S3 to store static files
USE_S3=False
AWS_ACCESS_KEY_ID=\"\"
AWS_SECRET_ACCESS_KEY=\"\"
AWS_STORAGE_BUCKET_NAME=\"\"

# if USE_OIDC is True uses OpenID Connect (OIDC) to authenticate the users
USE_OIDC=True
OIDC_RP_CLIENT_ID=""
OIDC_RP_CLIENT_SECRET=""
OIDC_OP_AUTHORIZATION_ENDPOINT=""
OIDC_OP_TOKEN_ENDPOINT=""
OIDC_OP_USER_ENDPOINT=""
OIDC_OP_JWKS_ENDPOINT=""
OIDC_RP_SIGN_ALGO=""

ROUTER_NUMBER="+559999998888"
ROUTER_COUNTRY="BR"
ROUTER_BASE_URL=""
ROUTER_USERNAME=""
ROUTER_PASSWORD=""
ROUTER_FACEBOOK_NAMESPACE=""
ROUTER_WABA_ID=""
ROUTER_BUSINESS_ID=""
ROUTER_VERIFIED_NAME=""
ROUTER_PHONE_NUMBER_ID=""

# WhatsApp App
WHATSAPP_SYSTEM_USER_ACCESS_TOKEN=""
WHATSAPP_VERSION=""
WHATSAPP_API_URL="https://graph.facebook.com/"
WHATSAPP_CLOUD_SYSTEM_USER_ID=""
WHATSAPP_CLOUD_EXTENDED_CREDIT_ID=""

CORS_ALLOWED_ORIGINS=""

USE_SENTRY=False
SENTRY_DSN=""


FLOWS_REST_ENDPOINT=""
""".strip()

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)

# TODO: Validate if file already exists

with open(env_path, "w") as configfile:
    configfile.write(CONFIG_STRING)
