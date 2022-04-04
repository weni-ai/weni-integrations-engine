from __future__ import absolute_import
import os

from celery import Celery

from marketplace import settings


def get_extra_task_paths() -> list:
    types_path = "marketplace.core.types."
    extra_task_paths = ["marketplace.grpc.client"]
    for apptype in settings.APPTYPES_CLASSES:
        extra_task_paths.append(types_path + ".".join(apptype.split(".")[:2]))
    return extra_task_paths


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")

app = Celery("marketplace")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = settings.CELERY_BEAT_SCHEDULE
app.autodiscover_tasks(settings.INSTALLED_APPS + get_extra_task_paths())
