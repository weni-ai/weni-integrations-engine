import json
import logging

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from phonenumbers.phonenumberutil import NumberParseException

from marketplace.celery import app as celery_app
from marketplace.grpc.client import ConnectGRPCClient
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App
from .apis import FacebookWABAApi, FacebookPhoneNumbersAPI
from .exceptions import FacebookApiException


User = get_user_model()
logger = logging.getLogger(__name__)


SYNC_WHATSAPP_LOCK_KEY = "sync-whatsapp-lock"
SYNC_WHATSAPP_WABA_LOCK_KEY = "sync-whatsapp-waba-lock-app:{app_uuid}"
SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY = "sync-whatsapp-phone-number-lock-app:{app_uuid}"


@celery_app.task(name="sync_whatsapp_apps")
def sync_whatsapp_apps():
    apptype = APPTYPES.get("wpp")
    response = ConnectGRPCClient().list_channels(apptype.channeltype_code)

    redis = get_redis_connection()

    if redis.get(SYNC_WHATSAPP_LOCK_KEY):
        logger.info("The apps are already syncing by another task!")
        return None

    else:
        with redis.lock(SYNC_WHATSAPP_LOCK_KEY):
            for channel in response:
                channel_config = json.loads(channel.config)

                # Skipping WhatsApp demo channels, change to environment variable later
                if "558231420933" in channel.address:
                    continue

                config = {"title": channel.address}
                config.update(channel_config)

                app, created = App.objects.get_or_create(
                    code=apptype.code,
                    platform=apptype.platform,
                    project_uuid=channel.project_uuid,
                    flow_object_uuid=channel.uuid,
                    defaults=dict(config=config, created_by=User.objects.get_admin_user()),
                )

                if created:
                    logger.info(f"A new whatsapp app was created automatically. UUID: {app.uuid}")

                if app.config.get("auth_token") != config.get("auth_token"):
                    app.config["auth_token"] = config.get("auth_token")
                    app.modified_by = User.objects.get_admin_user()
                    app.save()


@celery_app.task(name="sync_whatsapp_wabas")
def sync_whatsapp_wabas():
    apptype = APPTYPES.get("wpp")
    redis = get_redis_connection()

    for app in apptype.apps:
        key = SYNC_WHATSAPP_WABA_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            config = app.config
            access_token = config.get("fb_access_token", None)
            business_id = config.get("fb_business_id", None)

            if access_token is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_access_token`. UUID: {app.uuid}")
                continue

            if business_id is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_business_id`. UUID: {app.uuid}")
                continue

            logger.info(f"Syncing app WABA. UUID: {app.uuid}")

            api = FacebookWABAApi(access_token)

            try:
                waba = api.get_waba(business_id)
                app.config["waba"] = waba
                app.modified_by = User.objects.get_admin_user()
                app.save()

                redis.set(key, "synced", settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS)
            except FacebookApiException as error:
                logger.error(f"An error occurred while trying to sync the app. UUID: {app.uuid}. Error: {error}")
                continue

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )


@celery_app.task(name="sync_whatsapp_phone_numbers")
def sync_whatsapp_phone_numbers():
    apptype = APPTYPES.get("wpp")
    redis = get_redis_connection()

    def config_app_phone_number(app: App, phone_number: dict):
        phone_number_id = phone_number.get("id", None)
        display_phone_number = phone_number.get("display_phone_number", None)
        verified_name = phone_number.get("verified_name", None)
        consent_status = phone_number.get("cert_status", None)
        certificate = phone_number.get("certificate", None)

        app.config["phone_number"] = dict(
            id=phone_number_id,
            display_phone_number=display_phone_number,
            display_name=verified_name,
        )

        if consent_status is not None:
            app.config["phone_number"]["cert_status"] = consent_status

        if certificate is not None:
            app.config["phone_number"]["certificate"] = certificate

        app.save()

    for app in apptype.apps:
        key = SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            config = app.config
            access_token = config.get("fb_access_token", None)
            business_id = config.get("fb_business_id", None)

            if access_token is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_access_token`. UUID: {app.uuid}")
                continue

            if business_id is None:
                logger.info(f"Skipping the app because it doesn't contain `fb_business_id`. UUID: {app.uuid}")
                continue

            logger.info(f"Syncing app phone number. UUID: {app.uuid}")

            api = FacebookPhoneNumbersAPI(access_token)

            phone_number_id = config.get("phone_number", {}).get("id", None)

            try:
                if phone_number_id is not None:
                    phone_number = api.get_phone_number(phone_number_id)
                    config_app_phone_number(app, phone_number)

                else:
                    try:
                        app_phone_number = phonenumbers.parse(config.get("title", None))
                    except NumberParseException:
                        logger.info(f"Skipping the app because it doesn't contain `title`. UUID: {app.uuid}")
                        continue

                    phone_numbers = api.get_phone_numbers(business_id)

                    for phone_number in phone_numbers:
                        display_phone_number = phone_number.get("display_phone_number")

                        if phonenumbers.parse(display_phone_number) == app_phone_number:
                            config_app_phone_number(app, phone_number)

                redis.set(key, "synced", settings.WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS)
            except FacebookApiException as error:
                logger.error(
                    f"An error occurred while trying to sync the app phone number. UUID: {app.uuid}. Error: {error}"
                )

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )
