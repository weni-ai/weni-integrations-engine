"""
Responsible for speeding up the generation of a local '.env' configuration file.
OBS: Run in development environment only
"""

import os
from string import ascii_letters, digits, punctuation

from django.utils.crypto import get_random_string


chars = ascii_letters + digits + punctuation

# TODO: Remove escapes

CONFIG_STRING = f"""
DEBUG=True
ALLOWED_HOSTS=\"*\"
SECRET_KEY=\"{get_random_string(50, chars)}\"
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
USE_OIDC=False
OIDC_RP_CLIENT_ID=""
OIDC_RP_CLIENT_SECRET=""
OIDC_OP_AUTHORIZATION_ENDPOINT=""
OIDC_OP_TOKEN_ENDPOINT=""
OIDC_OP_USER_ENDPOINT=""
OIDC_OP_JWKS_ENDPOINT=""
OIDC_RP_SIGN_ALGO=""
""".strip()

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# TODO: Validate if file already exists

with open(env_path, "w") as configfile:
    configfile.write(CONFIG_STRING)
