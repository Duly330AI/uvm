import os

# Ensure dev settings for pytest runs regardless of container env
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import pytest


@pytest.fixture(autouse=True)
def _relax_throttles_for_non_throttle_tests(settings, request):
    """
    Für alle Tests außer denen, die explizit @pytest.mark.throttle haben:
    - drehe die Raten hoch, damit keine zufälligen 429 auftreten
    - erhöhe den Burst (per-Session) auf einen hohen Wert
    """
    if "throttle" in request.keywords:
        return
    rf = settings.REST_FRAMEWORK.copy()
    rf.setdefault("DEFAULT_THROTTLE_RATES", {})
    rf["DEFAULT_THROTTLE_RATES"]["chat"] = "1000/min"
    rf["DEFAULT_THROTTLE_CLASSES"] = []
    settings.REST_FRAMEWORK = rf
    settings.CHAT_BURST_LIMIT = 1000
    settings.CHAT_DISABLE_BURST_THROTTLE = True
    settings.SECURE_SSL_REDIRECT = False
    settings.CSRF_COOKIE_SECURE = False
    # Remove SecurityMiddleware to avoid HTTPS redirects in tests
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"]
    os.environ["CHAT_DISABLE_BURST_THROTTLE"] = "1"
    settings.CHAT_DISABLE_BURST_THROTTLE = True
