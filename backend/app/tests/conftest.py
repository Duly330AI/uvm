import os
import shutil
import tempfile

import pytest
from django.test import override_settings


@pytest.fixture
def use_locmem_email_backend():
    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        yield


@pytest.fixture(autouse=True)
def _relax_throttles_for_non_throttle_tests(settings, request):
    if "throttle" in request.keywords:
        return
    rf = settings.REST_FRAMEWORK.copy()
    rf.setdefault("DEFAULT_THROTTLE_RATES", {})
    rf["DEFAULT_THROTTLE_RATES"]["chat"] = "1000/min"
    rf["DEFAULT_THROTTLE_CLASSES"] = []
    settings.REST_FRAMEWORK = rf
    settings.CHAT_BURST_LIMIT = 1000
    settings.CHAT_DISABLE_BURST_THROTTLE = True
    os.environ["CHAT_DISABLE_BURST_THROTTLE"] = "1"
    settings.SECURE_SSL_REDIRECT = False

@pytest.fixture(autouse=True)
def _temp_media_root(settings):
    tmp = tempfile.mkdtemp(prefix="media-")
    with override_settings(MEDIA_ROOT=tmp):
        yield
    shutil.rmtree(tmp, ignore_errors=True)

