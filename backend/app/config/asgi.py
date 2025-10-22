import os

from django.core.asgi import get_asgi_application

# Production Settings Default (Phase 1.2 - 2025-10-22)
# For local development: export DJANGO_SETTINGS_MODULE=config.settings.dev
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_asgi_application()
