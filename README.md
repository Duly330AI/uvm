# UVM — Universal Vermieter Management (Property Management MVP)

**Status:** Advanced MVP / portfolio prototype
**Scope:** Django-based property-management MVP for landlord operations
**Review snapshot:** Internal Codex-assisted review notes from 2025-10-23; not externally audited
**Test snapshot:** 384 passing (7 skipped, documented) · coverage around 79–80% at the time of the internal review
**Repository:** https://github.com/Duly330AI/uvm

> This project is a portfolio prototype. It is not a certified legal, tax, accounting, or property-management product. It must not be used in production without a full security, privacy, and legal review.

---

## 🗺️ Überblick
UVM ist ein Django-basiertes Property-Management-MVP für Vermieter-Workflows. Der Prototyp deckt Immobilien, Einheiten, Mieter:innen, Tickets, Dokumente, Zählerstände, Nebenkosten-Workflows und Portalansichten ab. Optionale Automatisierungen und Integrationen sind als mögliche spätere Erweiterungen dokumentiert.

---

## ✅ Feature-Matrix (MVP-Umfang)
| Modul | Status | Highlights |
| --- | --- | --- |
| M1–M4 Ticketing & Kommunikation | ✅ | Chat-FSM v2, Status-Workflow, SLA-Metriken, Audit-Log |
| M5–M8 Portale | ✅ | Mieter-Magic-Link, Vendor-Auftragsportal, Terminplanung |
| M9–M11 Dokumente | ✅ | Versionierung (M17a integriert), Property/Unit-Zuordnung, Rollenrechte |
| M12 Verträge & Zahlungen | ✅ | Vertragsverwaltung, HMAC-signierter CSV-Import (O(N)), Zahlungsjournal |
| M14 Nebenkosten | ✅ | Utility Calculator (HeizkostenV), Verbrauchserfassung, CSV-Export |
| M15 Wartungskalender | ✅ | Overdue Detection, Staff Assignment, Celery-Reminder |
| M16 Checklisten | ✅ | Ein-/Auszug, Wartung, PDF-Export, Inline-Editing |

**Kernfunktionen:** MVP-Umfang implementiert · **Audit Logging:** immutable Design für Nachvollziehbarkeit · **Async Pipelines:** Chat-Anhänge, E-Mail-Tasks · **Monitoring:** Health Checks, Sentry (opt-in)

---

## 📋 Roadmap (M17–M20 geplant)
- M17b OCR & Dokument-Automation (optional)
- M18 Finanz-Schnittstellen (Bank-API, FiBu)
- M19 Analytics & Self-Service Dashboards
- M20 optionale Integrationen

> Fortschritt: fortgeschrittener MVP-Snapshot · Rest: optionale Erweiterungen mit fachlicher Prüfung

---

## 🧪 Qualität & Tests
- Interner Test-Snapshot: `pytest -q` → **384 passed, 7 skipped** (siehe `tests/` README)
- Coverage-Snapshot: `htmlcov/index.html` ≈ **79–80 %** zum Zeitpunkt der internen Prüfung
- Wichtige Testdateien: `test_validators.py`, `test_public_link.py`, `test_checklist_integration.py`
- Linting: `ruff check .` · Format: `black .`

### Schnellstart Tests
```bash
docker compose exec web pytest -q
docker compose exec web pytest tests/test_chat_api.py::test_chat_flow_confirm_idempotent -v
```

---

## ⚙️ Systemarchitektur
- **Backend:** Django 5.1, Python 3.12 (Services-Layer, FSM, Celery)
- **Frontend:** HTMX, TailwindCSS, Alpine.js
- **Storage:** PostgreSQL 16, Redis 7, optional S3/MinIO
- **Async:** Celery worker + beat, HMAC-signierte Payloads
- **Security:** sicherheitsbewusste Settings, SECRET_KEY per Env, Cookie-/Permission-Hardening

### Tenant-Modell (Änderung 2025-10-23)
- Felder: `first_name`, `last_name`, `date_of_birth`, `emergency_contact_*`, `notes`
- Zweck: strukturierte Vertragsparteien- und Kontaktdaten im Prototyp
- Migration: `0026_add_tenant_names.py` (bereits angewendet)

---

## 🚀 Demo-/Entwicklungssetup (Kurzfassung)
1. `.env` aus `.env.prod.example` erstellen (SECRET_KEY, DATABASE_URL, SENTRY_DSN optional)
2. `docker compose -f docker-compose.yml -f docker-compose.prod.yml build`
3. `docker compose ... up -d` (web, worker, beat, nginx, redis, db)
4. `docker compose exec web python manage.py migrate`
5. `docker compose exec web python manage.py check --deploy`
6. `docker compose exec web pytest -q`

Details: [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md). Vor echter Nutzung sind Security-, Privacy- und Rechtsprüfung erforderlich.

---

## 🧑‍💻 Entwicklung & Tooling
```powershell
# Dev-Settings aktivieren
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"

# Datenbank migrieren
python manage.py migrate

# Server & Worker starten
python manage.py runserver 0.0.0.0:8000
celery -A config.celery_app worker -l info
```
- Mailhog: http://localhost:8025
- Tenant/Vendor Magic-Link Tests via Mailhog UI

---

## 📚 Dokumentation
- [ROADMAP.md](./ROADMAP.md) – M1–M20 Status & Timeline
- [docs/MASTER_ACTION_PLAN.md](./docs/MASTER_ACTION_PLAN.md) – 40 h Refactoring-Plan (100 % abgeschlossen)
- [docs/MASTER_ACTION_PLAN_DONE.md](./docs/MASTER_ACTION_PLAN_DONE.md) – Detaillog abgeschlossen
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) – Deployment-Notizen
- [docs/SENTRY_SETUP.md](./docs/SENTRY_SETUP.md) – Monitoring aktivieren
- [docs/SECURITY_ENV_VARS.md](./docs/SECURITY_ENV_VARS.md) – Hardening & Secrets

---

## 📈 Kennzahlen & Review-Notizen
- Interner Codex-Review-Snapshot: **90/100** (Security, Performance, Code Quality, Monitoring)
- CSV-Import O(N) · Payment-Views paginiert · Chat-Anhänge async
- Audit-Log & HMAC-Signaturen unterstützen nachvollziehbare Änderungen

---

## 🤝 Mitwirken
1. Repo forken & Branch erstellen (`git checkout -b feature/<name>`)
2. Tests & Lints ausführen
3. Änderungen dokumentieren (`README`, `ROADMAP`, relevante docs)
4. Pull Request mit Kontext (Link zu Master Action Plan / Issue)

---

## © Lizenz & Kontakt
MIT License · Maintained by Duly330AI
