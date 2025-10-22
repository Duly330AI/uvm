# Dependency Audit Results

**Scan Date:** 2025-10-22  
**Tooling:** Safety 3.6.2 (`docs/safety_report.json`), pip-audit 2.9.0 (`docs/pip_audit_report.json`)

## 🔴 Critical (fix sofort)

- **gunicorn==22.0.0** - CVE-2024-6827 & Safety advisory 72809 (HTTP request smuggling via `Transfer-Encoding` header confusion)  
  - *Impact:* A crafted request can bypass upstream proxies and poison caches, exposing tenant/vendor data served by `backend/app/config/wsgi.py` when deployed behind load balancers.  
  - *Fix (0.5h):* Upgrade to `gunicorn==23.0.0`, rebuild the `web` container, and run the regression test suite.  
  - *Code update:*
    ```diff
    # pyproject.toml
    -  "gunicorn==22.0.0",
    +  "gunicorn==23.0.0",
    ```
  - *Verification:* `docker compose build web && docker compose exec web pytest backend/app/landlord`  
  - *Notes:* `23.0.0` drops the deprecated `TOLERATE_DANGEROUS_FRAMING` flag; no changes needed because the project does not override it.

## 🟡 Medium (fix vor Exit)

- **pip==25.2** - CVE-2025-8869 (arbitrary file overwrite while unpacking sdist archives)  
  - *Impact:* The build pipeline inside the `web` container can be compromised if a malicious sdist is installed during CI/CD. Runtime risk is low, but supply-chain exposure remains.  
  - *Fix (0.5h):* Adopt the patched release (`pip==25.3` once available) and restrict installs to wheels in the interim.  
  - *Hardening example:*
    ```dockerfile
    # backend/app/Dockerfile
    -RUN pip install --upgrade pip
    +RUN pip install --upgrade "pip==25.3" && \
    +    pip config set global.only-binary :all: && \
    +    pip config set install.use-feature fast-deps false
    ```
  - *Operational workaround:* Mirror trusted wheels or pin hashes in `requirements.lock` until the official release lands.

## 🟢 Low (optional)

- **Framework & worker stack refresh (4h):**  
  Upgrade `Django 5.1.13 -> 5.2.7`, `djangorestframework 3.15.2 -> 3.16.1`, and `celery 5.4.0 -> 5.5.3` to stay on supported branches and pick up ORM and task scheduler performance fixes.  
  ```diff
  # pyproject.toml
  -  "Django==5.1.13",
  -  "djangorestframework==3.15.2",
  -  "celery==5.4.0",
  +  "Django==5.2.7",
  +  "djangorestframework==3.16.1",
  +  "celery==5.5.3",
  ```
  Run `python manage.py check --deploy` after the upgrades to catch deprecated settings.

- **Data services alignment (3h):**  
  Bump `redis 5.0.8 -> 6.4.0` and `psycopg[binary,pool] 3.2.3 -> 3.2.11` for improved cluster support and pool leak fixes. Validate connection handling in `backend/app/config/settings/base.py` by exercising Celery and tenant onboarding flows.

- **Storage client maintenance (1h):**  
  Update `boto3/botocore` and `django-storages` to their latest patch releases to keep S3 uploads compatible with AWS signature changes.

- **Dev-tool hygiene (1h):**  
  Refresh `pytest`, `pytest-django`, and `pytest-cov` to maintain compatibility with Python 3.12. Pin wheel hashes in your lockfile to avoid drift in CI.

## Follow-Up

- Replace the deprecated `safety check` invocation with `safety scan --full-report --output docs/safety_report.json` before integrating into CI.  
- Monitor the pip advisory feed and update once 25.3 is published; record the mitigation status in `SECURITY.md`.  
- Schedule dependency retests after each upgrade: `docker compose exec web python manage.py test landlord`.
