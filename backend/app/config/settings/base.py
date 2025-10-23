from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


# SECRET_KEY Hardening (Phase 1.3 - 2025-10-22)
# No default fallback - must be explicitly set in environment
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY environment variable is required but not set. "
        "Generate a secure key with: "
        "python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # Domain app
    "landlord.apps.LandlordConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://landlord:landlord@localhost:5432/landlord")
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
}


# Redis / Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Europe/Berlin"
# Worker/task defaults
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 30
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))


# Password hashing (Argon2 preferred)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Password validation (Phase 1.4 - 2025-10-22)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True


# Static & media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Email (Mailhog in dev via env)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")


# DRF defaults
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        # Browsable API bleibt in dev an; in prod wird sie überschrieben
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.api.exception_handler.custom_exception_handler",
    # DRF Permission Classes (Phase 1.6 - 2025-10-22)
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Authentication Classes
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# Upload memory caps
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# Throttling for chat API
REST_FRAMEWORK.update({
    "DEFAULT_THROTTLE_CLASSES": [
        "landlord.throttles.ChatRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "chat": "20/min",
    },
})


# Optional S3 storage via django-storages when USE_S3=true
USE_S3 = os.getenv("USE_S3", "false").lower() in {"1", "true", "yes"}
if USE_S3:
    INSTALLED_APPS.append("storages")
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("S3_BUCKET")
    AWS_QUERYSTRING_AUTH = True


# Logging (simple structured-ish JSON)
DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"}
    },
    "root": {"handlers": ["console"], "level": DJANGO_LOG_LEVEL},
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Site domain for emails and links
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "localhost:8000")

# Celery task routes (optional emails queue)
CELERY_TASK_ROUTES = {
    "landlord.tasks.send_*": {"queue": "emails"},
}

# ---------------------------------------------------------------------------
# Security settings (sensible defaults for production, keep dev friendly)
# ---------------------------------------------------------------------------
# ALLOWED_HOSTS can be provided as a comma-separated env var, default empty (dev)
_hosts = os.getenv("ALLOWED_HOSTS", "")
if _hosts:
    ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()]

# If DEBUG is False, enable stricter security defaults. These can be overridden
# via environment variables when needed for staging/prod.
if not DEBUG:
    # Cookie Security (Phase 1.5 - 2025-10-22)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = "Lax"  # Prevent CSRF attacks via cross-site requests
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access to CSRF token cookie
    CSRF_COOKIE_SAMESITE = "Lax"  # Additional CSRF protection
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    # HSTS: default to 1 year; can be tuned via env
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() in {"1","true","yes"}
    SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "true").lower() in {"1","true","yes"}
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() in {"1","true","yes"}
else:
    # Development-safe defaults
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True  # Still protect in dev (doesn't break local testing)
    SESSION_COOKIE_SAMESITE = "Lax"  # Still set SameSite in dev for consistency
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access in dev for easier debugging
    CSRF_COOKIE_SAMESITE = "Lax"


# ============================================================================
# PHASE 4.1: SENTRY ERROR TRACKING & PERFORMANCE MONITORING (2025-10-23)
# ============================================================================
# Sentry.io integration for production error tracking and APM.
# Activated by setting SENTRY_DSN environment variable.
#
# To activate:
#   1. Sign up at sentry.io and create project
#   2. Get DSN from project settings
#   3. Set SENTRY_DSN in .env or environment
#   4. Optionally set SENTRY_ENVIRONMENT (default: "production")
#   5. Optionally set SENTRY_TRACES_SAMPLE_RATE (default: 0.1 = 10%)
#
# Example .env:
#   SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
#   SENTRY_ENVIRONMENT=production
#   SENTRY_TRACES_SAMPLE_RATE=0.1

SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        
        # Determine environment
        sentry_environment = os.getenv("SENTRY_ENVIRONMENT", "production")
        
        # Traces sample rate (0.0 to 1.0)
        # Default 0.1 = 10% of transactions for performance monitoring
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            environment=sentry_environment,
            
            # Performance Monitoring
            traces_sample_rate=traces_sample_rate,
            
            # Send default PII (user IDs, emails) for better error context
            send_default_pii=True,
            
            # Release tracking (use git commit hash in production)
            release=os.getenv("SENTRY_RELEASE", "uvm@dev"),
            
            # Before-send hook to scrub sensitive data if needed
            # before_send=lambda event, hint: event,  # Customize as needed
        )
        
        # Log successful initialization (only in non-DEBUG mode to avoid noise)
        if not DEBUG:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Sentry initialized for environment: {sentry_environment}")
            
    except ImportError:
        # Sentry SDK not installed - log warning
        import warnings
        warnings.warn(
            "SENTRY_DSN is set but sentry-sdk is not installed. "
            "Install with: pip install sentry-sdk",
            stacklevel=2
        )
