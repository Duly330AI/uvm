# UVM – AI Agent Playbook (Stand 2025-10-23)

## 🎯 Aktueller Fokus
- Production-harter Refactoring-Plan (40 h) **abgeschlossen**
- Security Score 90/100 · Coverage ~80 %
- Kernfeatures (M1–M16) produktionsreif; M17–M20 optional
- Primary workstreams jetzt: Dokumentation, Release-Readiness, optionale Integrationen

## 📌 Projekt-Snapshot
- **Feature Status:** 80 % gesamt · Core 100 %
- **Tests:** 384 passed / 7 skipped (siehe `pytest -q`)
- **Coverage:** 79–80 % (validators/public_link 100 %)
- **Tenant-Modell:** `first_name`, `last_name`, `date_of_birth`, `emergency_contact_*`, `notes` seit Migration `0026_add_tenant_names`
- **Master Action Plan:** Phasen 1–4 erledigt → siehe `docs/MASTER_ACTION_PLAN_DONE.md`

## 🛠️ Arbeitsablauf für neue Tasks
1. Prüfe `docs/MASTER_ACTION_PLAN.md` für offene To-dos/M17–M20 Vorbereitungen
2. Aktualisiere bei Start eines Tasks diese Datei mit Status & Fokus
3. Implementiere Änderungen (`backend/app/...`), ergänze Tests bei Bedarf
4. Führe `pytest -q` sowie zielgerichtete Tests aus
5. Dokumentiere Anpassungen (README, ROADMAP, relevante Docs)
6. Verschiebe abgeschlossene Tasks nach `docs/MASTER_ACTION_PLAN_DONE.md`
7. Stelle sicher, dass Security-/Performance-Guides aktuell bleiben

## 🧩 Architektur & Konventionen
- **Backend:** Django 5.1, Python 3.12, Service-Layer (`landlord/services`)
- **FSM:** Ausgelagert nach `landlord/fsm_handlers.py`, Zustände per Registry, Tests in `tests/test_fsm_*`
- **Async:** Celery (`config/celery_app.py`), Chat-Anhänge → `finalize_chat_attachments`
- **Audit Logging:** `landlord/models_audit.py`, `landlord/services/audit.py` – keine Mutationen, HMAC für sensitive Aktionen
- **Security Defaults:** Prod-Settings (`config.settings.prod`) per WSGI/ASGI; Secrets ausschließlich via Env (`docs/SECURITY_ENV_VARS.md`)

### Coding Standards
- Line length 100, Ruff + Black (siehe `pyproject.toml`)
- Typisierung mit `from __future__ import annotations`
- Tests unter `backend/app/tests/` (Pytest + Django fixtures)
- Neue Dienste im passenden `services/` Modul kapseln

## 🔍 Test & Qualität
```bash
# Dev-Mode aktivieren
export DJANGO_SETTINGS_MODULE=config.settings.dev

# Vollsuite
docker compose exec web pytest -q

# Coverage Bericht
docker compose exec web pytest --cov=landlord --cov=config --cov-report=html
```
- Skipped Tests dokumentieren (pytest markers + README Hinweis)
- PRs sollen rote Tests verhindern; bei Infrastrukturtests `$SECURE_SSL_REDIRECT=0`

## 🚀 Deployment Hinweise
- Produktionsleitfaden: `docs/DEPLOYMENT.md`
- Nach Schema: migrate → check --deploy → pytest → collectstatic → healthz
- Tenant-Felder erfordern aktualisierte Admin-Formulare & Vertragsvorlagen
- Sentry optional: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`

## 📚 Schlüssel-Dokumente
- `README.md` · `ROADMAP.md`
- `docs/MASTER_ACTION_PLAN.md` / `_DONE.md`
- `docs/codex_executive_summary.md` (Score 90/100)
- `docs/TEST_COVERAGE_GAPS_REPORT.md` (aktualisiert, jetzt grüne Bereiche)
- `docs/DEPLOYMENT.md`, `docs/OPERATIONS_RUNBOOK.md`

## ✅ Merkliste nach Änderungen
- [ ] Code + Tests aktualisiert
- [ ] Dokumentation synchronisiert (README/ROADMAP/copilot instructions)
- [ ] Master Action Plan gepflegt
- [ ] Security & Performance Reports bei relevanten Änderungen notiert

Bleibe bei Änderungen konsistent, dokumentiere Tenant-bezogene Daten sorgfältig (Art. 6 DSGVO), und halte den Exit-ready Status (80 %) stets sichtbar.
