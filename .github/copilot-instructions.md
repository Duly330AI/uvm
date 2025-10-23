# UVM - Universal Vermieter Management: AI Agent Instructions

## 🚀 CURRENT FOCUS: Production-Ready Refactoring (Master Action Plan)

**Phase:** Production-Ready Optimization (40h total)  
**Status:** ✅✅✅ ALL PHASES COMPLETE! 🎉🎉🎉  
**Progress:** 40h / 40h (100%)  
**Goal:** Security ✅ → Performance ✅ → Code quality ✅ → Monitoring ✅

### **Completed Work:**
- ✅ **Phase 1 COMPLETE (6h):** All 8 security tasks done!
- ✅ **Phase 2 COMPLETE (10h):** All performance optimizations done!
  - 2.1 CSV Import O(N×M) → O(N) - 60x speedup ✅
  - 2.2 Payment List Pagination - 100x memory reduction ✅
  - 2.3 Chat Upload Async - 50x response time ✅
- ✅ **Phase 3 COMPLETE (16h):** All code quality improvements done!
  - 3.1 FSM Refactoring CC 46 → 3 ✅
  - 3.2 Chat View CC 40 → <15 ✅
  - 3.3 Test Coverage 79% with 53 new tests ✅
- ✅ **Phase 4 COMPLETE (8h):** Monitoring & operations done!
  - 4.1 Sentry Setup (ready-to-activate) ✅
  - 4.2 Audit Logging (GDPR-compliant) ✅
  - 4.3 Deployment Guide (1000+ lines) ✅
  - 4.4 Operations Runbook (600+ lines) ✅
- 📋 **Master Plan:** `docs/MASTER_ACTION_PLAN.md`
- ✅ **Completed Tasks:** `docs/MASTER_ACTION_PLAN_DONE.md`
- 📊 **Audit Reports:** `docs/codex_executive_summary.md` + 6 detailed reports

### **Workflow:**

1. Pick task from MASTER_ACTION_PLAN.md
2. Implement & test
3. Move completed task to MASTER_ACTION_PLAN_DONE.md
4. Update progress tracker
5. Commit with descriptive message
6. Continue to next task

### **Key Documents:**

- `docs/MASTER_ACTION_PLAN.md` - Remaining tasks (40h plan)
- `docs/MASTER_ACTION_PLAN_DONE.md` - Completed tasks log
- `docs/codex_executive_summary.md` - Codex audit findings (62/100 score)
- `docs/DEPENDENCY_AUDIT_RESULTS.md` - Security vulnerabilities
- `docs/DJANGO_BEST_PRACTICES_REPORT.md` - Config issues
- `docs/DATABASE_QUERY_OPTIMIZATION_REPORT.md` - N+1 queries, indexes
- `docs/CODE_COMPLEXITY_ANALYSIS_REPORT.md` - FSM (CC 46), Chat View (CC 40)
- `docs/TEST_COVERAGE_GAPS_REPORT.md` - auth.py 0%, fsm.py 7%, coverage 69%
- `docs/PERFORMANCE_BOTTLENECKS_REPORT.md` - CSV import O(N×M), unbounded lists

---

## Project Overview

**UVM** is a Django-based property management system with chat-based tenant issue reporting, staff portals, vendor integration, utility billing, and document management. It uses Docker Compose with PostgreSQL, Redis, Celery, and supports both development and production deployments.

**Tech Stack:** Django 5.1 + Python 3.12, HTMX + TailwindCSS + Alpine.js, PostgreSQL 16, Redis 7, Celery, Docker

**Original Status:** 44% feature-complete (M1-M16 done)
**Current Focus:** Production-ready hardening (Security + Performance + Quality + Monitoring)

## Architecture & Key Patterns

### Multi-Settings Configuration

- **Settings:** Split into `config/settings/{base,dev,prod}.py` - select via `DJANGO_SETTINGS_MODULE` env var
- **Development:** Always use `config.settings.dev` (set in docker-compose, pytest.ini)
- **Security:** Production enforces SSL, HSTS, secure cookies; dev disables these for local work
- **Never modify** `__init__.py` in settings - it's intentionally empty

### Docker-First Development

- **All commands run in containers:** Use `docker compose exec web <command>` for Django management, tests, shell
- **Test task available:** Run `docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.dev -e SECURE_SSL_REDIRECT=0 web pytest -q` or use VS Code task "pytest (dev settings)"
- **Live reload:** Source code mounted at `./backend/app:/app` for hot-reload during development
- **Services:** web (Django), worker (Celery), beat (scheduler), db (Postgres), redis, mailhog (dev email), minio (S3-compatible storage)

### Model Layer Architecture

- **Single app:** All models in `landlord/models.py` (1400+ lines) - Property, Unit, Tenant, Issue, Contract, Payment, Document, etc.
- **TimeStampedModel:** Abstract base for `created_at`/`updated_at` on most models
- **Soft deletes:** Property model uses `is_archived`/`archived_at`/`archived_by` pattern (not Django's native deletion)
- **Validation:** Custom validators in `landlord/validators.py` (e.g., `validate_country_whitelist`, `validate_serial_number_format`)
- **Constraints:** Heavy use of DB-level `CheckConstraint` and unique constraints - check model Meta before adding logic

### View Layer Conventions

- **Split by domain:** `views_portal.py` (staff), `views_tenant.py` (tenant portal), `views_vendor.py`, `views_contracts.py`, `views_payments.py`, `views_utility.py`, etc.
- **HTMX integration:** Check `request.headers.get('HX-Request')` to return partial HTML vs full page (see `views_utility.py:193`, `views_checklist.py:199`)
- **Template base:** All portal views extend `portal/base.html` with TailwindCSS classes
- **Auth decorators:** `@staff_member_required` for staff views, `@tenant_login_required` (custom) for tenant portal, magic-link auth for tenants/vendors

### Service Layer Pattern

- **Location:** Business logic in `landlord/services/` (issues.py, chat_session.py, utility_calculator.py, etc.)
- **Transaction safety:** Wrap state changes in `transaction.atomic()` (see `services/issues.py:update_status`)
- **Example:** Issue status updates call `services.issues.update_status()` which handles DB update + async task dispatch

### FSM-Driven Chat Flow

- **FSM:** `landlord/fsm.py` - ChatFSM with states: GREETING → CAPTURE_SUMMARY → CAPTURE_OCCURRED_AT → CAPTURE_LOCATION → CAPTURE_SEVERITY → CAPTURE_MEDIA → CAPTURE_CONTACT → CONFIRM → CREATE_ISSUE → DONE
- **Validation:** FSM raises `ValueError("VALIDATION:field:error_type")` for errors - caught in serializers/views
- **Heuristic categorization:** FSM auto-detects category (water/heating/electricity/structural) from German keywords in user text
- **State machine:** `ChatFSM.next(state, message, payload)` returns `(next_state, prompt, delta_dict, warnings)`

### Async Task Patterns

- **Celery setup:** `config/celery_app.py` - autodiscovers tasks from installed apps
- **Task routing:** Email tasks go to "emails" queue (see `config/settings/base.py:CELERY_TASK_ROUTES`)
- **Task definition:** Use `@shared_task(autoretry_for=(Exception,), retry_backoff=2, max_retries=5, acks_late=True, time_limit=30)` for robustness
- **Fire-and-forget:** Tasks dispatched with `.delay()` often wrapped in try/except to not block request (see `services/issues.py:20`)

### Testing Standards

- **Fixture:** `tests/conftest.py` auto-relaxes throttles for non-throttle tests (via `@pytest.mark.throttle` marker)
- **Coverage:** Target ~72%, run with `pytest --cov=landlord --cov-report=html`
- **Naming:** `test_*.py` files, `test_*` functions, use pytest fixtures (not unittest classes)
- **Django fixtures:** Use `client` fixture for requests, `settings` for config overrides
- **Database:** Tests use transactional DB (pytest-django), no need for manual cleanup

## Development Workflows

### Running Tests

```bash
# Inside container (preferred)
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.dev -e SECURE_SSL_REDIRECT=0 web pytest -q

# With coverage
docker compose exec web pytest --cov=landlord --cov-report=html
# View: backend/app/htmlcov/index.html
```

### Database Migrations

```bash
# Create migration
docker compose exec web python manage.py makemigrations

# Apply migrations (auto-runs on container start via entrypoint.sh)
docker compose exec web python manage.py migrate

# Check migration status
docker compose exec web python manage.py showmigrations
```

### Adding a New Feature

1. **Model changes:** Add to `landlord/models.py`, create migration
2. **Service logic:** Extract complex logic to `landlord/services/<domain>.py`
3. **Views:** Add to appropriate `views_<domain>.py`, use `@staff_member_required` or custom auth decorator
4. **URLs:** Register in `config/urls.py` (main) or `landlord/api/urls.py` (API)
5. **Templates:** Place in `backend/app/templates/portal/` or `landlord/templates/`
6. **Tests:** Create `tests/test_<feature>.py` with minimum ~3 test cases covering happy/error paths

### Common Pitfalls

- **Settings confusion:** Tests MUST use `config.settings.dev` - set via env var or pytest.ini
- **HTMX responses:** Return partial HTML (single `<div>`) when `HX-Request` header present, not full page
- **Throttling in tests:** Use `@pytest.mark.throttle` for throttle tests; conftest auto-disables for others
- **Container exec:** Always use `docker compose exec web` for Django commands, NOT local Python
- **Migrations:** Existing migrations have complex ForeignKey changes (see `0010_document_fk_relations_m11b.py`) - study before creating new ones

## Key Files Reference

- **Main settings:** `backend/app/config/settings/base.py` - shared config, security, DRF, Celery
- **URL routing:** `config/urls.py` - all app routes (portal, tenant, vendor, admin, API)
- **Models:** `landlord/models.py` - single file, 1400+ lines
- **FSM:** `landlord/fsm.py` - chat state machine logic
- **Tasks:** `landlord/tasks.py` - Celery tasks for emails, reminders
- **Conftest:** `tests/conftest.py` - pytest fixtures, throttle relaxation
- **Docker compose:** `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod overlay)
- **Roadmap:** `ROADMAP.md` - feature status, M1-M16 milestone tracking
- **Spec:** `docs/uvm_universal_vermieter_managment_SPEC_v_0_5_19_10.md` - technical specification

## Project-Specific Conventions

### Code Style

- **Line length:** 100 chars (Black + Ruff configured in `pyproject.toml`)
- **Imports:** Ruff enforces sorted imports with isort-compatible rules
- **Type hints:** Use `from __future__ import annotations` for forward refs (see all model files)
- **Docstrings:** Minimal - only for complex logic, not for obvious CRUD functions

### Naming Patterns

- **Ticket numbers:** Auto-generated as `TCK-YYYY-XXXXX` (5-digit counter per year)
- **Models:** PascalCase (Property, Unit, Tenant, Issue, Contract)
- **Views:** `<noun>_<action>` (e.g., `issue_detail`, `payment_csv_upload`, `checklist_create`)
- **Templates:** Match view function names (e.g., `portal/issue_detail.html`)
- **Services:** `<domain>_service.py` or `<domain>.py` in services/ folder

### Database Patterns

- **ForeignKeys:** Always specify `on_delete` explicitly (PROTECT for critical refs, CASCADE for owned data, SET_NULL for optional)
- **Indexes:** Use `Meta.indexes` for query optimization (see Property model for examples)
- **Constraints:** Prefer DB-level `CheckConstraint` over Python validation when possible
- **Migrations:** Named descriptively (e.g., `0010_document_fk_relations_m11b.py`, `0012b_add_utilityreading_m14.py`)

### Frontend Patterns

- **HTMX:** Used for partial updates (status changes, notes, attachments) - no Alpine.js reactivity needed
- **TailwindCSS:** Utility-first classes, no custom CSS files
- **Alpine.js:** Only for local UI state (dropdowns, modals) - minimal usage
- **Forms:** Django forms rendered with Tailwind classes in templates, CSRF tokens required

## Integration Points

### Email (Mailhog in Dev)

- **Dev:** SMTP via Mailhog on port 1025, web UI at http://localhost:8025
- **Tasks:** `send_issue_created`, `send_status_changed`, `send_appointment_invite` (with ICS attachment)
- **Templates:** `backend/app/templates/emails/` - HTML + plaintext fallback

### S3/MinIO (Optional)

- **Activation:** Set `USE_S3=true` in .env to enable django-storages backend
- **Dev setup:** MinIO runs on port 9000 (API) and 9001 (console)
- **Default:** Local filesystem (`MEDIA_ROOT = backend/app/media/`) in dev

### External APIs

- **None currently** - all functionality is internal to Django
- **Future:** Potential integrations for payment providers, accounting systems (see ROADMAP.md M13)

## Debugging & Troubleshooting

### Common Issues

1. **CSRF errors in tests:** Ensure `SECURE_SSL_REDIRECT=0` and `CSRF_COOKIE_SECURE=False` in test settings
2. **Throttle 429s in tests:** Missing `@pytest.mark.throttle` when testing throttled endpoint
3. **Migration conflicts:** Check `ROADMAP.md` for merge migration history (e.g., `0012_merge_20251019.py`)
4. **Static files 404:** Run `docker compose exec web python manage.py collectstatic` (auto-runs in prod via entrypoint)

### Useful Commands

```bash
# Django shell
docker compose exec web python manage.py shell

# Check logs
docker compose logs -f web
docker compose logs -f worker

# Health check
curl http://localhost:8000/healthz

# Coverage with specific test
docker compose exec web pytest tests/test_chat_api.py::test_chat_flow_confirm_idempotent -v
```

## Current Development Focus

**Production-Ready Refactoring (Master Action Plan)**

**Phase 1: Security Fixes (6h total)**

- ✅ 1.1 Gunicorn CVE Fix (0.5h) - DONE 2025-10-22
- 🔄 1.2 Production Settings Default (1h) - IN PROGRESS
- ⏳ 1.3 SECRET_KEY Hardening (0.5h)
- ⏳ 1.4 Password Validators (0.5h)
- ⏳ 1.5 Cookie Hardening (0.5h)
- ⏳ 1.6 DRF Permissions (1h)
- ⏳ 1.7 ALLOWED_HOSTS Validation (0.5h)
- ⏳ 1.8 Deploy Check in CI (0.5h)

**Phase 2: Performance (10h total)**

- CSV Import O(N×M) → O(N)
- Payment List Pagination
- Chat Upload Async
- N+1 Query Elimination

**Phase 3: Code Quality (16h total)**

- FSM Refactoring (CC 46 → <20)
- Chat View Decomposition
- Test Coverage 69% → 80%

**Phase 4: Monitoring (8h total)**

- Sentry.io Setup
- Audit Logging
- Final Security Review

**Next priorities:**

- Security audit + performance testing (12h)
- See `docs/MASTER_ACTION_PLAN.md` for full milestone tracking

**Recent changes:**

- 2025-10-22: Gunicorn 23.0.0 (CVE-2024-6827 patched), Master Action Plan created
- 2025-10-20: Security fixes (SSL redirect via env var, test dependencies isolated)
- M15 Wartungskalender: Complete with 6 views, 11 tests passing
- M16 Checklisten: Complete with PDF export, inline editing via AJAX
- M14 Nebenkostenabrechnung: HeizkostenV-compliant utility billing with CSV export

When working on new features, consult `docs/MASTER_ACTION_PLAN.md` for current task and `docs/codex_executive_summary.md` for audit findings.

**Critical:** Always keep this document up to date with current focus and progress!
**Critical:** Always keep `docs\MASTER_ACTION_PLAN.md` synchronized with actual work and completed tasks!
**Critical:** After completing a task, immediately log it in `docs/MASTER_ACTION_PLAN_DONE.md` with time spent and verification steps!
