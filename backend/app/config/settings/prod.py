from .base import *  # noqa
from . import base as _base
import os

DEBUG = False

# Set your production hosts via env DJANGO_ALLOWED_HOSTS (comma separated) or configure here
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if os.getenv("DJANGO_ALLOWED_HOSTS") else []

# Security hardening placeholders
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() in {"1","true","yes"}
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# During pytest runs, avoid HTTPS redirect to keep test client simple
if os.getenv("PYTEST_CURRENT_TEST"):
	SECURE_SSL_REDIRECT = False

# Reverse proxy/SSL settings (when behind a proxy)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv("SECURE_PROXY_SSL_HEADER", "true").lower() in {"1","true","yes"} else None

# CSRF trusted origins (comma separated), e.g. https://app.example.com,https://admin.example.com
_csrf = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _csrf:
	CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()]

# DRF: in prod nur JSON Renderer
REST_FRAMEWORK = {
	**_base.REST_FRAMEWORK,
	"DEFAULT_RENDERER_CLASSES": [
		"rest_framework.renderers.JSONRenderer",
	],
}

# Default cache uses Redis in production
CACHES = {
	"default": {
		"BACKEND": "django_redis.cache.RedisCache",
		"LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
		"OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
		"TIMEOUT": 300,
	}
}

# Static files via WhiteNoise (prod)
MIDDLEWARE = list(MIDDLEWARE)
try:
    sec_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
except ValueError:
    sec_idx = 0
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(sec_idx + 1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Enable hashed/compressed static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Additional Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Content Security Policy (basic - adjust for your needs)
# Uncomment and customize if you want CSP
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com", "https://unpkg.com")
# CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com")

# S3/MinIO for file storage (activate in production)
USE_S3 = os.getenv("USE_S3", "false").lower() in {"1", "true", "yes"}
if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minio")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minio123")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "uvm-uploads")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "http://minio:9000")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_CUSTOM_DOMAIN = None

    # Use S3 for default file storage
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # Cache-Control for media files
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",  # 24 hours
    }
