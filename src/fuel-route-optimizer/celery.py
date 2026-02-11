import os

from celery.app.base import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "fuel-route-optimizer.settings.development"
)

app = Celery("fuel-route-optimizer")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
