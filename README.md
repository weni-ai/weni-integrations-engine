# weni-marketplace-engine
This project provides so many API endpoints to manage Weni Platform marketplace.

## Running project for development

### Requirements
- Python ^3.8
- Poetry ^1.0

### Installation
To run this project, we will need [Poetry](https://python-poetry.org/docs/) installed on your machine.  
After installing poetry, install all dependencies using (on project root path):
```sh
$ poetry install
```

To enter on Poetry virtual environment, we use:
```sh
$ poetry shell
```

### Environment setting

In this project we use environment variables to make most of the configurations.
To speed up the project installation process we use a script to generate our `.env` file, it can be found in `contrib/gen_env.py`. To use type:

```sh
$ python contrib/gen_env.py
```
Ready, an `.env` file should be appars on root of project, and from it we can configure our environment variables.

**OBS**: The use of this script is recommended in development environment only.

### Setting up the local database

To get the database up and running, docker-compose can be handy:
```sh
$ docker-compose up -d database
```

Run the necessary migrations with:
```sh
$ python manage.py migrate
```

### Executing the application

To run the application, you can use:
```sh
$ python manage.py runserver 8001
```


## Environment Variables list:


| Name                           	|  Type  	| Required 	|         Default        	| Description                                                                                                                                                                          	|
|--------------------------------	|:------:	|:--------:	|:----------------------:	|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| DEBUG                          	|  Bool  	|   False  	|          True          	| If True, debug actions are made and shown in stdout.                                                                                                                                 	|
| SECRET_KEY                     	| String 	|   True   	|          None          	| [Django's required SECRET_KEY.](https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts)                                                                                   	|
| ALLOWED_HOSTS                  	|  List  	|   False  	|          None          	| [Django's ALLOWED_HOSTS variable](https://docs.djangoproject.com/en/3.2/ref/settings/#allowed-hosts)                                                                                 	|
| DATABASE_URL                   	| String 	|   True   	|          None          	| Postgres database URL.                                                                                                                                                               	|
| LANGUAGE_CODE                  	| String 	|   False  	|        "en-us"         	| Language code used in i18n.                                                                                                                                                          	|
| TIME_ZONE                      	| String 	|   False  	|    "America/Maceio"    	| Application time zone.                                                                                                                                                               	|
| MEDIA_ROOT                     	| String 	|   False  	|        "media/"        	| The default medias folder if S3 is not provided.                                                                                                                                     	|
| USE_S3                         	|  Bool  	|   False  	|          False         	| Boolean that defines if S3 should be used.                                                                                                                                           	|
| AWS_ACCESS_KEY_ID              	| String 	|   False  	|          None          	| Amazon S3 bucket Access Key.                                                                                                                                                         	|
| AWS_SECRET_ACCESS_KEY          	| String 	|   False  	|          None          	| Amazon S3 bucket Secret Key.                                                                                                                                                         	|
| AWS_STORAGE_BUCKET_NAME        	| String 	|   False  	|          None          	| Amazon S3 bucket name.                                                                                                                                                               	|
| USE_OIDC                       	|  Bool  	|   False  	|          False         	| Boolean that defines if OIDC should be used.                                                                                                                                         	|
| OIDC_RP_CLIENT_ID              	| String 	|   False  	|          None          	| [OpenID Connect client ID provided by your OP.](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_RP_CLIENT_ID)                                                	|
| OIDC_RP_CLIENT_SECRET          	| String 	|   False  	|          None          	| [OpenID Connect client secret provided by your OP](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_RP_CLIENT_SECRET)                                         	|
| OIDC_OP_AUTHORIZATION_ENDPOINT 	| String 	|   False  	|          None          	| [URL of your OpenID Connect provider authorization endpoint.](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_OP_AUTHORIZATION_ENDPOINT)                     	|
| OIDC_OP_TOKEN_ENDPOINT         	| String 	|   False  	|          None          	| [URL of your OpenID Connect provider token endpoint](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_OP_TOKEN_ENDPOINT)                                      	|
| OIDC_OP_USER_ENDPOINT          	| String 	|   False  	|          None          	| [URL of your OpenID Connect provider userinfo endpoint](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_OP_USER_ENDPOINT)                                    	|
| OIDC_OP_JWKS_ENDPOINT          	| String 	|   False  	|          None          	| [URL of the OIDC OP jwks endpoint](https://mozilla-django-oidc.readthedocs.io/en/stable/installation.html?highlight=JWKS#choose-the-appropriate-algorithm)                           	|
| OIDC_RP_SIGN_ALGO              	| String 	|   False  	|          HS256         	| [Sets the algorithm the IdP uses to sign ID tokens.](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_RP_SIGN_ALGO)                                           	|
| OIDC_DRF_AUTH_BACKEND          	| String 	|   False  	|          None          	| [Sets the default rest framework integration of OIDC with Django](https://mozilla-django-oidc.readthedocs.io/en/stable/drf.html?highlight=DRF#drf-django-rest-framework-integration) 	|
| OIDC_RP_SCOPES                 	| String 	|   False  	|      openid email      	| [The OpenID Connect scopes to request during login.](https://mozilla-django-oidc.readthedocs.io/en/stable/settings.html#OIDC_RP_SCOPES)                                              	|
| CORS_ALLOWED_ORIGINS           	|  List  	|   False  	|           [ ]          	| Allowed Origins at CORS configuration.                                                                                                                                               	|
| CONNECT_GRPC_SERVER_URL        	| String 	|   False  	|          None          	| URL of gRPC Connect client.                                                                                                                                                          	|
| CONNECT_CERTIFICATE_GRPC_CRT   	| String 	|   False  	|          None          	| Certificate of gRPC Connect client.                                                                                                                                                  	|
| SOCKET_BASE_URL                	| String 	|   False  	|          None          	| Base URL of a [Weni Web Chat Socket](https://github.com/Ilhasoft/weni-webchat-socket) application                                                                                    	|
| FLOWS_HOST_URL                 	| String 	|   False  	|          None          	| Base URL of a  [Weni Flows](https://github.com/Ilhasoft/rapidpro)  application.                                                                                                      	|
| CELERY_BROKER_URL              	| String 	|   False  	| redis://localhost:6379 	| [Default broker URL.](https://docs.celeryproject.org/en/stable/userguide/configuration.html#std-setting-broker_url)                                                                  	|
| CELERY_RESULT_BACKEND          	| String 	|   False  	| redis://localhost:6379 	| [The backend used to store task results](https://docs.celeryproject.org/en/stable/userguide/configuration.html#result-backend)                                                       	|
| USE_SENTRY                     	|  Bool  	|   False  	|          False         	| Boolean that defines if Sentry should be initialized.                                                                                                                                	|
| SENTRY_DSN                     	| String 	|   False  	|          None          	| Sentry's DSN URL.                                                                                                                                                                    	|
| USE_GRPC                       	|  Bool  	|   False  	|          False         	| Boolean that defines if GRPC should be used.                                                                                                                                         	|