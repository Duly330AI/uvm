# Django Best Practices Report

**Scan Date:** 2025-10-22  
**Diagnostics:** `python manage.py check --deploy` (3 warnings)  
**Scope:** `backend/app/config`, `backend/app/landlord`

## 🔴 Critical (fix before go-live)

- **Prod entrypoints boot the dev settings module** — `backend/app/config/wsgi.py:5`, `backend/app/config/asgi.py:5`, `backend/app/config/celery_app.py:5` call `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")`.  
  *Impact:* Unless the environment overrides this variable, uWSGI/ASGI servers and the Celery worker will run with `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, unsecured cookies, and non-SSL redirects. The deployment check warnings stem directly from this default.  
  *Fix (0.5h):* Default to the production settings and let developers override locally:  
  ```python
  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
  ```  
  Document the override in `README.md` (`export DJANGO_SETTINGS_MODULE=config.settings.dev` for local shells).

- **Insecure SECRET_KEY fallback** — `backend/app/config/settings/base.py:20` sets `SECRET_KEY = os.getenv("SECRET_KEY", "change-me")`. `manage.py check --deploy` flags the short key, and an unset env leaks an easily guessable value.  
  *Fix (0.5h):* Remove the hardcoded fallback and fail fast when missing:  
  ```python
  SECRET_KEY = os.getenv("SECRET_KEY")
  if not SECRET_KEY:
      raise ImproperlyConfigured("SECRET_KEY environment variable is required.")
  ```  
  Rotate existing keys (50+ chars) and store them in the secrets manager used by the deployment pipeline.

- **HTTPS enforcement off by default** — `manage.py check --deploy` reports `SECURE_SSL_REDIRECT` is False because the dev settings are active.  
  *Fix (0.2h):* After switching the default settings module to `config.settings.prod`, keep `SECURE_SSL_REDIRECT=True` (already defined in prod). For local development, disable via `DJANGO_SETTINGS_MODULE=config.settings.dev` or `SECURE_SSL_REDIRECT=0` in `.env`.

## 🟡 Medium (prioritise for the hardening sprint)

- **Password strength validation missing** — `backend/app/config/settings/base.py` defines custom hashers but omits `AUTH_PASSWORD_VALIDATORS`. New superusers/admins can set weak passwords.  
  *Fix (0.5h):* Add Django’s default validators or a tailored list:
  ```python
  AUTH_PASSWORD_VALIDATORS = [
      {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
      {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
      {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
      {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
  ]
  ```

- **Cookies not fully hardened** — `SESSION_COOKIE_HTTPONLY` / `CSRF_COOKIE_HTTPONLY` are unset in both dev/prod profiles, leaving session and CSRF tokens readable by JavaScript.  
  *Fix (0.2h):* Set both attributes to `True` (while keeping SameSite as configured) and ensure any front-end code does not rely on reading those cookies.

- **OPEN ALLOWED_HOSTS defaults** — `backend/app/config/settings/base.py:40` starts with `ALLOWED_HOSTS: list[str] = []` and only populates from `ALLOWED_HOSTS` env. Combined with the dev default settings, the system accepts all hosts.  
  *Fix (0.2h):* Fail fast when the env var is missing in production (e.g., raise `ImproperlyConfigured` if `DEBUG` is False and `ALLOWED_HOSTS` is empty).

- **REST framework defaults rely on implicit authentication** — `REST_FRAMEWORK` omits `DEFAULT_AUTHENTICATION_CLASSES` and `DEFAULT_PERMISSION_CLASSES`, meaning anonymous access is allowed unless each view sets permissions manually.  
  *Fix (1h):* Define conservative defaults (`IsAuthenticated`, `SessionAuthentication`/`TokenAuthentication`) and override only where public access is required.

- **Deployment check coverage** — Current automation runs `python manage.py check --deploy` against the dev settings, hiding production misconfigurations.  
  *Fix (0.2h):* Update CI to execute `manage.py check --deploy --settings=config.settings.prod` so the hardened configuration is validated on every pipeline run.

- **Celery email tasks lack test mode safeguards** — `backend/app/landlord/tasks.py:28` sends emails directly via SMTP, relying on environment. Configure `EMAIL_BACKEND`/`ANYMAIL` per environment and use `CELERY_TASK_ALWAYS_EAGER` in tests to avoid accidental deliveries.

## 🟢 Low (opportunistic improvements)

- **Set `ADMINS` & `SERVER_EMAIL`** in production to capture crash reports via email.  
- **Enable CSP and COOP headers** once the front-end asset origins are known (`config/settings/prod.py` already provides placeholders).  
- **Document SITE_DOMAIN** — defaulting to `localhost:8000` leaks into emails (`backend/app/config/settings/base.py:153`). Ensure staging/prod override this via env.

## Follow-Up

1. Update WSGI/ASGI/Celery entrypoints and rerun `python manage.py check --deploy --settings=config.settings.prod` to confirm warnings disappear.  
2. Add password validators and cookie hardening settings; verify login flows still pass integration tests.  
3. Lock down DRF defaults and run the API regression suite to ensure expected endpoints expose `AllowAny` explicitly where needed.  
4. Capture the final configuration baseline in `docs/SECURITY_COMPLIANCE_AUDIT.md` and link this report for traceability.
