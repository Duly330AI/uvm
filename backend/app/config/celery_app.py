import os

from celery import Celery

# Production Settings Default (Phase 1.2 - 2025-10-22)
# For local development: export DJANGO_SETTINGS_MODULE=config.settings.dev
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

celery_app = Celery("config")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()
