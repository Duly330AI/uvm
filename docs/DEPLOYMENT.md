# 🚀 UVM Production Deployment Guide (2025-10-23)

This guide reflects the post-refactoring state (Security Score 90/100, 384 Tests, Tenant name fields, async pipelines). Follow the checklist to promote a stable release.

---

## ✅ Preflight Checklist
1. `docker compose exec web python manage.py check --deploy` → 0 warnings
2. `docker compose exec web pytest -q` → **384 passed**, 7 skipped
3. Coverage report (`pytest --cov`) ≥ 79 %
4. Confirm migration `0026_add_tenant_names.py` applied
5. Update `.env` with prod secrets (see [docs/SECURITY_ENV_VARS.md](./SECURITY_ENV_VARS.md))

---

## 🧱 Prerequisites
- Docker ≥ 24 · Docker Compose ≥ 2.20
- Domain + TLS (Let’s Encrypt or managed)
- PostgreSQL 16, Redis 7
- SMTP provider (SendGrid/Mailgun) or on-prem relay
- Optional: S3-compatible storage (AWS S3, MinIO)
- Sentry project (optional but recommended)

---

## 🛠️ Environment (.env)
```
# Django
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<generated>
ALLOWED_HOSTS=app.example.com
SECURE_SSL_REDIRECT=1

# Database
DATABASE_URL=postgres://uvm_user:password@db:5432/uvm_prod

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<user>
EMAIL_HOST_PASSWORD=<password>
DEFAULT_FROM_EMAIL=noreply@example.com

# Monitoring (optional)
SENTRY_DSN=https://public@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## 🧾 Tenant Model Update
- Migration `0026_add_tenant_names.py` adds `first_name`, `last_name`, `date_of_birth`, `emergency_contact_*`, `notes`
- Forms/Admin wurden aktualisiert; bestehende Datensätze können zunächst leere Strings haben
- Vertragsvorlagen müssen Vor- und Nachname referenzieren (BGB § 550)

---

## 🐳 Deployment Steps
```bash
# 1. Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. Start stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Run migrations
docker compose exec web python manage.py migrate

# 4. Create superuser (once)
docker compose exec web python manage.py createsuperuser

# 5. Collect static files
docker compose exec web python manage.py collectstatic --noinput

# 6. Warm up caches / health check
curl -I https://app.example.com/healthz
```

### Workers & Scheduler
```bash
docker compose ps worker
# Logs
docker compose logs -f worker
```
Ensure `finalize_chat_attachments` queue is processed (async chat uploads).

---

## 🔐 Security Hardening
- HTTPS enforced via `SECURE_SSL_REDIRECT=1`
- Cookies: Secure, HttpOnly, SameSite=Lax (prod defaults)
- SECRET_KEY rotation documented in `docs/SECURITY_ENV_VARS.md`
- Audit log immutable; ensure read-only DB role for analytics exports

---

## 📈 Monitoring & Logging
- Activate Sentry (`SENTRY_DSN`) – includes Django, Celery, Redis integrations
- Health endpoint: `/healthz` (DB, Redis, Celery status)
- Access logs via `docker compose logs -f web` (Gunicorn JSON format)
- Mailhog only in dev; configure SMTP credentials in prod

---

## 🧪 Post-Deployment Verification
1. Admin login + Tenant search (check new name fields)
2. Create chat issue with attachment → Verify Celery finalizes file
3. Run payment CSV upload smoke test (uses cached O(N) matcher)
4. Generate KPI dashboard (cache warm)
5. Trigger audit events (GDPR erase, property archive) → Validate immutable logs

---

## 🔁 Rollback Strategy
- Keep last successful compose bundle/tag
- Database backups (pg_dump) + media snapshots (tar) with 30‑T retention
- To roll back:
  1. `docker compose down`
  2. Restore DB + media
  3. Checkout previous tag
  4. Re-run migrate (if necessary `python manage.py migrate <app> <previous_migration>`)

---

## 🆘 Troubleshooting Quick Reference
| Symptom | Check | Fix |
| --- | --- | --- |
| 502 Bad Gateway | `docker compose logs web nginx` | Restart services, verify Gunicorn port 8000 |
| Celery pending | `docker compose logs worker` | Scale workers, verify Redis URL |
| Static 404 | `collectstatic` executed? volumes mounted? | Re-run collectstatic, restart nginx |
| Email fails | SMTP creds / TLS | Update `.env`, restart web |

---

## 📚 Weitere Ressourcen
- [docs/OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)
- [docs/SENTRY_SETUP.md](./SENTRY_SETUP.md)
- [docs/SECURITY_ENV_VARS.md](./SECURITY_ENV_VARS.md)
- [README.md](../README.md) für Projektüberblick

Deployment fertig? Aktualisiere ROADMAP & Master Action Plan und dokumentiere Go-Live-Checks.
