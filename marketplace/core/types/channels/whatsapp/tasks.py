import logging
from uuid import UUID

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from phonenumbers.phonenumberutil import NumberParseException

from marketplace.applications.models import App
from marketplace.celery import app as celery_app
from marketplace.clients.flows.client import FlowsClient
from marketplace.core.pacing.constants import (
    QUEUE_WHATSAPP_CLOUD_PHONE_NUMBERS,
    QUEUE_WHATSAPP_CLOUD_WABAS,
    TTL_WHATSAPP_CLOUD_WABAS,
)
from marketplace.core.pacing.queue import enqueue_item
from marketplace.core.pacing.ttl import is_recently_synced
from marketplace.core.types import APPTYPES
from marketplace.core.types.channels.whatsapp.usecases.phone_number_sync import (
    PhoneNumberSyncUseCase,
    SYNC_WHATSAPP_PHONE_NUMBER_LOCK_KEY as CLOUD_PHONE_TTL_KEY,
)
from marketplace.core.types.channels.whatsapp.usecases.waba_sync import WABASyncUseCase
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
    client = FlowsClient()
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
    enqueued = 0
    skipped_ttl = 0
    seen_waba_ids = set()
    apps = App.objects.filter(code="wpp-cloud", configured=True)

    for app in apps:
        config = app.config or {}
        waba_id = config.get("wa_waba_id")
        if not waba_id or "ignores_meta_sync" in config:
            continue
        if waba_id in seen_waba_ids:
            continue
        seen_waba_ids.add(waba_id)

        ttl_key = TTL_WHATSAPP_CLOUD_WABAS.format(waba_id=waba_id)
        if is_recently_synced(ttl_key):
            skipped_ttl += 1
            continue
        if enqueue_item(QUEUE_WHATSAPP_CLOUD_WABAS, waba_id):
            enqueued += 1

    logger.info(
        f"WABA sync dispatch: enqueued={enqueued} skipped_ttl={skipped_ttl} "
        f"unique_wabas={len(seen_waba_ids)}"
    )


def _resolve_waba_id_from_queue_item(item_id: str):
    """Map an in-flight app UUID to wa_waba_id; pass through already-enqueued waba ids."""
    try:
        UUID(str(item_id))
    except (ValueError, TypeError, AttributeError):
        return item_id

    try:
        app = App.objects.get(uuid=item_id, code="wpp-cloud")
    except App.DoesNotExist:
        logger.error(f"WABA sync item skipped, app not found: {item_id}")
        return None

    waba_id = (app.config or {}).get("wa_waba_id")
    if not waba_id:
        logger.error(f"WABA sync item skipped, app has no wa_waba_id: {item_id}")
        return None

    logger.info(f"Resolved in-flight app uuid {item_id} to waba {waba_id}")
    return waba_id


@celery_app.task(name="task_sync_whatsapp_cloud_waba_item")
def task_sync_whatsapp_cloud_waba_item(item_id: str):
    waba_id = _resolve_waba_id_from_queue_item(item_id)
    if not waba_id:
        return

    try:
        result = WABASyncUseCase().sync_waba(waba_id)
        status_result = result.get("status")
        if status_result == "error":
            logger.error(
                f"sync_whatsapp_cloud_wabas: {result.get('error', 'unknown error')} "
                f"for waba {waba_id}"
            )
            return
        logger.info(f"WABA {waba_id} sync result: {status_result}")
    except Exception as e:
        logger.error(f"Error processing WABA sync for waba {waba_id}: {e}")


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
    enqueued = 0
    skipped_ttl = 0
    apps = App.objects.filter(code="wpp-cloud", configured=True)
    total_apps = apps.count()

    for app in apps:
        ttl_key = CLOUD_PHONE_TTL_KEY.format(app_uuid=str(app.uuid))
        if is_recently_synced(ttl_key):
            skipped_ttl += 1
            continue
        if enqueue_item(QUEUE_WHATSAPP_CLOUD_PHONE_NUMBERS, str(app.uuid)):
            enqueued += 1

    logger.info(
        f"Phone number sync dispatch: enqueued={enqueued} skipped_ttl={skipped_ttl} "
        f"total_apps={total_apps}"
    )


@celery_app.task(name="task_sync_whatsapp_cloud_phone_number_item")
def task_sync_whatsapp_cloud_phone_number_item(app_uuid: str):
    try:
        app = App.objects.get(uuid=app_uuid, code="wpp-cloud")
        result = PhoneNumberSyncUseCase(app).sync_whatsapp_cloud_phone_number()
        status_result = result.get("status")
        if status_result == "error":
            logger.error(
                f"sync_whatsapp_cloud_phone_numbers: "
                f"{result.get('error', 'unknown error')} for app {app.uuid}"
            )
            return
        logger.info(f"App {app.uuid} sync result: {status_result}")
    except App.DoesNotExist:
        logger.error(f"Phone number sync item skipped, app not found: {app_uuid}")
    except Exception as e:
        logger.error(f"Error processing phone number sync for app {app_uuid}: {e}")


def delete_inactive_apps(apps, flow_object_uuid):
    for app in apps:
        try:
            # Ensures that it will only delete the app linked to the uuid of the flow
            if str(app.flow_object_uuid) == flow_object_uuid:
                templates = app.templates.all()
                if templates:
                    app.templates.all().delete()

                app.delete()
                logger.info(f"Inactive app: [{app.uuid}] deleted successfully")
        except Exception as e:
            logger.error(f"An error occurred while delete the app {app.uuid}: {e}")
            continue
