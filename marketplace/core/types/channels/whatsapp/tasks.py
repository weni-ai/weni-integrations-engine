import logging

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from phonenumbers.phonenumberutil import NumberParseException

from marketplace.celery import app as celery_app
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App
from marketplace.connect.client import ConnectProjectClient
from .apis import FacebookWABAApi, FacebookPhoneNumbersAPI
from ..whatsapp_base.exceptions import FacebookApiException


User = get_user_model()
logger = logging.getLogger(__name__)


SYNC_WHATSAPP_LOCK_KEY = "sync-whatsapp-lock"
SYNC_WHATSAPP_WABA_LOCK_KEY = "sync-whatsapp-waba-lock-app:{app_uuid}"
SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY = "sync-whatsapp-phone-number-lock-app:{app_uuid}"


@celery_app.task(name="sync_whatsapp_apps")
def sync_whatsapp_apps():
    apptype = APPTYPES.get("wpp")
    client = ConnectProjectClient()
    channels = client.list_channels(apptype.flows_type_code, exclude_wpp_demo=True)

    redis = get_redis_connection()

    if redis.get(SYNC_WHATSAPP_LOCK_KEY):
        logger.info("The apps are already syncing by another task!")
        return None

    else:
        with redis.lock(SYNC_WHATSAPP_LOCK_KEY):
            for channel in channels:
                channel_config = channel.get("config")

                if channel.get("project_uuid") is None:
                    uuid = channel.get("uuid")
                    logger.info(f"The channel {uuid} does not have a project_uuid.")
                    continue

                if channel.get("uuid") is None:
                    logger.info("Skipping channel with None UUID.")
                    continue

                if channel.get("is_active") is False:
                    flow_channel_uuid = channel.get("uuid")
                    apps_to_delete = App.objects.filter(
                        flow_object_uuid=flow_channel_uuid
                    )
                    if apps_to_delete:
                        delete_inactive_apps(apps_to_delete, flow_channel_uuid)

                    logger.info(f"Skipping channel {flow_channel_uuid} is inactive.")
                    continue

                # Skipping WhatsApp demo channels, change to environment variable later
                if "558231420933" in channel.get("address"):
                    continue

                config = {"title": channel.get("address")}
                config.update(channel_config)

                apps = App.objects.filter(flow_object_uuid=channel.get("uuid"))

                if apps.exists():
                    app = apps.first()

                    if app.code != apptype.code:
                        logger.error(
                            f"This app: {app.uuid} has been migrated from {app.code} to wpp "
                            "we don't support it so it will be ignored"
                        )
                        continue

                    sync_fields = [
                        "base_url",
                        "username",
                        "password",
                        "auth_token",
                        "fb_access_token",
                    ]
                    has_changes = False

                    for field in sync_fields:
                        if app.config.get(field) != config.get(field):
                            app.config[field] = config.get(field)
                            has_changes = True

                    if has_changes:
                        app.modified_by = User.objects.get_admin_user()
                        app.save()

                else:
                    try:
                        app = apptype.create_app(
                            project_uuid=channel.get("project_uuid"),
                            flow_object_uuid=channel.get("uuid"),
                            config=config,
                            created_by=User.objects.get_admin_user(),
                        )

                        logger.info(
                            f"A new whatsapp app was created automatically. UUID: {app.uuid}"
                        )
                    except Exception as e:
                        logger.error(f"An error occurred while creating the app: {e}")
                        continue


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
                logger.info(
                    f"Skipping the app because it doesn't contain `fb_access_token`. UUID: {app.uuid}"
                )
                continue

            if business_id is None:
                logger.info(
                    f"Skipping the app because it doesn't contain `fb_business_id`. UUID: {app.uuid}"
                )
                continue

            logger.info(f"Syncing app WABA. UUID: {app.uuid}")

            api = FacebookWABAApi(access_token)

            try:
                waba = api.get_waba(business_id)
                app.config["waba"] = waba
                app.modified_by = User.objects.get_admin_user()
                app.save()

                redis.set(
                    key, "synced", settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS
                )
            except FacebookApiException as error:
                logger.error(
                    f"An error occurred while trying to sync the app. UUID: {app.uuid}. Error: {error}"
                )
                continue

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )


@celery_app.task(name="sync_whatsapp_cloud_wabas")
def sync_whatsapp_cloud_wabas():
    apptype = APPTYPES.get("wpp-cloud")
    redis = get_redis_connection()

    for app in apptype.apps:
        key = SYNC_WHATSAPP_WABA_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            config = app.config
            wa_waba_id = config.get("wa_waba_id", None)

            if wa_waba_id is None:
                logger.info(
                    f"Skipping the app because it doesn't contain `wa_waba_id`. UUID: {app.uuid}"
                )
                continue

            logger.info(f"Syncing app WABA. UUID: {app.uuid}")

            api = FacebookWABAApi(apptype.get_access_token(app))

            try:
                waba = api.get_waba(wa_waba_id)
                app.config["waba"] = waba
                app.modified_by = User.objects.get_admin_user()
                app.save()

                redis.set(
                    key, "synced", settings.WHATSAPP_TIME_BETWEEN_SYNC_WABA_IN_HOURS
                )
            except FacebookApiException as error:
                logger.error(
                    f"An error occurred while trying to sync the app. UUID: {app.uuid}. Error: {error}"
                )
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

    error_counts = {}

    for app in apptype.apps:
        key = SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            config = app.config
            access_token = config.get("fb_access_token", None)
            business_id = config.get("fb_business_id", None)

            if access_token is None:
                logger.info(
                    f"Skipping the app because it doesn't contain `fb_access_token`. UUID: {app.uuid}"
                )
                continue

            if business_id is None:
                logger.info(
                    f"Skipping the app because it doesn't contain `fb_business_id`. UUID: {app.uuid}"
                )
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
                        logger.info(
                            f"Skipping the app because it doesn't contain `title`. UUID: {app.uuid}"
                        )
                        continue

                    phone_numbers = api.get_phone_numbers(business_id)

                    for phone_number in phone_numbers:
                        display_phone_number = phone_number.get("display_phone_number")

                        if phonenumbers.parse(display_phone_number) == app_phone_number:
                            config_app_phone_number(app, phone_number)

                redis.set(
                    key,
                    "synced",
                    settings.WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS,
                )
            except FacebookApiException as error:
                error_message = str(error)
                if error_message in error_counts:
                    error_counts[error_message] += 1
                else:
                    error_counts[error_message] = 1
                logger.info(
                    f"An error occurred while trying to sync the app phone number. UUID: {app.uuid}. Error: {error}"
                )

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )

    if error_counts:
        total_errors = sum(error_counts.values())
        logger.error(
            f"Sync phone numbers task failed with {total_errors}",
            extra={"erros": error_counts},
        )


@celery_app.task(name="sync_whatsapp_cloud_phone_numbers")
def sync_whatsapp_cloud_phone_numbers():
    apptype = APPTYPES.get("wpp-cloud")
    redis = get_redis_connection()

    error_counts = {}

    for app in apptype.apps:
        key = SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY.format(app_uuid=str(app.uuid))

        if redis.get(key) is None:
            phone_number_id = app.config.get("wa_phone_number_id", None)

            if phone_number_id is None:
                logger.info(
                    f"Skipping the app because it doesn't contain `wa_phone_number_id`. UUID: {app.uuid}"
                )
                continue

            try:
                api = FacebookPhoneNumbersAPI(apptype.get_access_token(app))
                phone_number = api.get_phone_number(phone_number_id)

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

                app.modified_by = User.objects.get_admin_user()

                app.save()
                redis.set(
                    key,
                    "synced",
                    settings.WHATSAPP_TIME_BETWEEN_SYNC_PHONE_NUMBERS_IN_HOURS,
                )

            except Exception as e:
                error_message = str(e)
                if error_message in error_counts:
                    error_counts[error_message] += 1
                else:
                    error_counts[error_message] = 1
                logger.info(f"sync_whatsapp_cloud_phone_numbers:{e}")
                continue

        else:
            logger.info(
                f"Skipping the app because it was recently synced. {redis.ttl(key)} seconds left. UUID: {app.uuid}"
            )

    if error_counts:
        total_errors = sum(error_counts.values())
        logger.error(
            f"Sync phone numbers task failed with {total_errors}.",
            extra={"erros": error_counts},
        )


def delete_inactive_apps(apps, flow_object_uuid):
    for app in apps:
        try:
            # Ensures that it will only delete the app linked to the uuid of the flow
            if str(app.flow_object_uuid) == flow_object_uuid:
                templates = app.template.all()
                if templates:
                    app.template.all().delete()

                app.delete()
                logger.info(f"Inactive app: [{app.uuid}] deleted successfully")
        except Exception as e:
            logger.error(f"An error occurred while delete the app {app.uuid}: {e}")
            continue
