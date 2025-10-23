# 🏢 UVM – Universal Vermieter Management

**Version:** 1.0.0 (Production-Ready)
**Status:** 🚀 **80 % complete – Core Features 100 % live (M1–M16)**
**Security Score:** 90/100 (Codex re-audit 2025‑10‑23)
**Test Suite:** 384 passing (7 skipped, documented) · **Coverage:** 79–80 %
**Repository:** https://github.com/Duly330AI/uvm

---

## 🗺️ Überblick
UVM ist eine vollwertige Hausverwaltungsplattform mit Chat-basiertem Ticketing, Vertrags- und Dokumentenverwaltung, Nebenkostenabrechnung, Checklisten, Wartungsplaner und Portalen für Mieter:innen sowie Dienstleister. Der aktuelle Stand deckt alle Kernprozesse für einen Exit-ready MVP ab; optionale Automatisierungen (M17–M20) sind geplant.

---

## ✅ Feature-Matrix (M1–M16 abgeschlossen)
| Modul | Status | Highlights |
| --- | --- | --- |
| M1–M4 Ticketing & Kommunikation | ✅ | Chat-FSM v2, Status-Workflow, SLA-Metriken, Audit-Log |
| M5–M8 Portale | ✅ | Mieter-Magic-Link, Vendor-Auftragsportal, Terminplanung |
| M9–M11 Dokumente | ✅ | Versionierung (M17a integriert), Property/Unit-Zuordnung, Rollenrechte |
| M12 Verträge & Zahlungen | ✅ | Vertragsverwaltung, HMAC-signierter CSV-Import (O(N)), Zahlungsjournal |
| M14 Nebenkosten | ✅ | Utility Calculator (HeizkostenV), Verbrauchserfassung, CSV-Export |
| M15 Wartungskalender | ✅ | Overdue Detection, Staff Assignment, Celery-Reminder |
| M16 Checklisten | ✅ | Ein-/Auszug, Wartung, PDF-Export, Inline-Editing |

**Kernfunktionen:** 100 % produktionsreif · **Audit Logging:** Immutable, GDPR-konform · **Async Pipelines:** Chat-Anhänge, E-Mail-Tasks · **Monitoring:** Health Checks, Sentry (opt-in)

---

## 📋 Roadmap (M17–M20 geplant)
- M17b OCR & Dokument-Automation (optional)
- M18 Finanz-Schnittstellen (Bank-API, FiBu)
- M19 Analytics & Self-Service Dashboards
- M20 Premium-Integrationen für Exit-Verhandlungen

> Fortschritt: **80 % abgeschlossen** · Rest: optionale Erweiterungen mit Business-Abstimmung

---

## 🧪 Qualität & Tests
- `pytest -q` → **384 passed, 7 skipped** (siehe `tests/` README)
- Coverage-Bericht: `htmlcov/index.html` ≈ **79–80 %** (validators & public_link 100 %)
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
- **Security:** Prod-Settings Default (`config.settings.prod`), SECRET_KEY erzwingt Env, sichere Cookies, DRF-Permissions hart

### Tenant-Modell (Änderung 2025-10-23)
- Felder: `first_name`, `last_name`, `date_of_birth`, `emergency_contact_*`, `notes`
- Rechtliche Grundlage: § 550 BGB – Vertragsparteien im Mietvertrag
- Migration: `0026_add_tenant_names.py` (bereits angewendet)

---

## 🚀 Deployment (Kurzfassung)
1. `.env` aus `.env.prod.example` erstellen (SECRET_KEY, DATABASE_URL, SENTRY_DSN optional)
2. `docker compose -f docker-compose.yml -f docker-compose.prod.yml build`
3. `docker compose ... up -d` (web, worker, beat, nginx, redis, db)
4. `docker compose exec web python manage.py migrate`
5. `docker compose exec web python manage.py check --deploy`
6. `docker compose exec web pytest -q` (384 Tests)

Detailleitfaden: [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

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
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) – Produktionsleitfaden
- [docs/SENTRY_SETUP.md](./docs/SENTRY_SETUP.md) – Monitoring aktivieren
- [docs/SECURITY_ENV_VARS.md](./docs/SECURITY_ENV_VARS.md) – Hardening & Secrets

---

## 📈 Kennzahlen & Audits
- Codex Performance Audit Score: **90/100** (Security, Performance, Code Quality, Monitoring)
- CSV-Import O(N) · Payment-Views paginiert · Chat-Anhänge async
- Audit-Log & HMAC-Signaturen verhindern Manipulationen

---

## 🤝 Mitwirken
1. Repo forken & Branch erstellen (`git checkout -b feature/<name>`)
2. Tests & Lints ausführen
3. Änderungen dokumentieren (`README`, `ROADMAP`, relevante docs)
4. Pull Request mit Kontext (Link zu Master Action Plan / Issue)

---

## © Lizenz & Kontakt
Privates Repository · Alle Rechte vorbehalten · Maintained by Duly330AI
