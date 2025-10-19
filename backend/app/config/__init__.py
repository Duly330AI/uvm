
from .celery_app import celery_app as app  # noqa: F401

# Make celery discoverable as both 'app' and 'celery'
celery = app  # noqa: F401
