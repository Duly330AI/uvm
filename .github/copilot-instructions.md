# UVM – AI Agent Playbook

**Project:** Property Management Platform (Django 5.1, Python 3.12)  
**Status:** Advanced MVP / portfolio prototype (M1–M16 implemented) · Internal review 90/100 · Tests 384 passed · Coverage 79–80%

---

## 🏗️ Architecture Overview

**Monolith Structure:** Single `landlord` app with layered architecture
- **Models:** `landlord/models.py` (1400+ lines, all domain models)
- **Services:** `landlord/services/*.py` (business logic, transactions)
- **Views:** Split by domain (`views_portal.py`, `views_tenant.py`, `views_contracts.py`, etc.)
- **FSM:** State Handler Pattern (`fsm.py` dispatcher → `fsm_handlers.py` registry)

**Key Components:**
- **Chat System:** Multi-step FSM (`GREETING` → `CAPTURE_SUMMARY` → ... → `CREATE_ISSUE`)
- **Async Jobs:** Celery (`finalize_chat_attachments`, email tasks)
- **Auth:** Magic-Link (tenant/vendor), Django Admin (staff)
- **Audit:** Immutable logs (`models_audit.py`) with HMAC signatures

---

## 🔧 Critical Development Patterns

### 1. Settings Management (CRITICAL!)
```python
# Production is DEFAULT (wsgi.py, asgi.py, celery_app.py)
# Override for local dev:
export DJANGO_SETTINGS_MODULE=config.settings.dev
# OR add to .env: DJANGO_SETTINGS_MODULE=config.settings.dev
```
**Why:** Security hardening (Phase 1.2) moved prod to default. Always override locally!

### 2. State Handler Pattern (FSM)
```python
# fsm_handlers.py - Each state = one function
def handle_capture_summary(message, payload):
    # Validate, detect category, return (next_state, prompt, delta, warnings)
    return ("CAPTURE_OCCURRED_AT", prompt, {"summary": text}, [])

# Register in STATE_HANDLERS dict at bottom of file
STATE_HANDLERS = {
    "CAPTURE_SUMMARY": handle_capture_summary,
    # ...
}
```
**Why:** Reduced CC from 46 → 3. Add new states by adding handler + registry entry.

### 3. Service Layer Transactions
```python
# services/chat_session.py
def message(session_id, version, state, message, files=None):
    # 1. Validate FSM transition OUTSIDE transaction
    fsm = ChatFSM()
    new_state, prompt, delta, warnings = fsm.next(state, message, {})
    
    # 2. Optimistic locking with version check
    with transaction.atomic():
        rows = ChatSession.objects.filter(id=session_id, version=version).update(...)
        if rows == 0:
            raise RuntimeError("STATE_VERSION_CONFLICT")
        # 3. Merge payload in Python (prevents lost updates)
```
**Why:** Prevents race conditions in concurrent chat sessions. Always check `version`.

### 4. Async File Processing
```python
# Chat uploads staged to temp/, moved async after Issue creation
payload.setdefault("temp_files", []).extend(staged)  # During chat
# Later: finalize_chat_attachments.delay(issue_id)  # Celery task
```
**Why:** 50x response time improvement (10s → 200ms). Never block HTTP thread for file I/O.

---

## 🧪 Testing Essentials

### Running Tests
```bash
# Full suite (384 tests)
docker compose exec web pytest -q

# With coverage report
docker compose exec web pytest --cov=landlord --cov=config --cov-report=html

# Specific module
docker compose exec web pytest tests/test_fsm_handlers.py -v

# Skip infrastructure tests locally
docker compose exec -e SECURE_SSL_REDIRECT=0 web pytest -q
```

### Test Markers
```python
@pytest.mark.throttle  # For rate-limit tests (others auto-skip throttle)
@pytest.mark.skip(reason="Infra dependency")  # Document skipped tests
```

### Coverage Targets
- Overall: 79–80% (validators/public_link 100%)
- New modules: Aim for 90%+ before merging
- Critical paths: FSM handlers, service transactions, auth flows

---

## 🔐 Security Conventions

### 1. No Default Secrets
```python
# config/settings/base.py
SECRET_KEY = os.getenv("SECRET_KEY")  # NO fallback!
if not SECRET_KEY:
    raise ImproperlyConfigured("Generate with: python -c '...'")
```

### 2. Audit Logging (Immutable)
```python
from landlord.services.audit import log_audit

log_audit(
    action="tenant_erased",
    actor=request.user,
    target_object=tenant,
    metadata={"reason": "GDPR request"},
    request=request  # Captures IP, User-Agent
)
```
**Why:** privacy/audit accountability. Logs cannot be edited/deleted after creation.

### 3. Tenant Data (§ 550 BGB)
```python
# Tenant model requires first_name/last_name for legal contracts
# Migration 0026_add_tenant_names added these fields
# Always validate in forms/serializers before saving
```

---

## 📦 Docker & Local Dev

### Start Development Stack
```powershell
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Mailhog for magic-link testing: http://localhost:8025
# Admin: http://localhost:8000/admin/
# Portal: http://localhost:8000/portal/
```

### Live Reload
Source code mounted at `./backend/app:/app` – changes auto-reload Django dev server.

### Worker Logs
```bash
docker compose logs -f worker  # Watch Celery tasks
docker compose logs -f beat    # Watch scheduled jobs
```

---

## 🚀 Deployment Checklist

Before deploying:
1. `docker compose exec web python manage.py check --deploy` (0 warnings required)
2. `docker compose exec web pytest -q` (384 tests passing)
3. Update `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` in prod env
4. Rotate `SECRET_KEY` (generate new, never reuse dev keys)
5. Run `collectstatic` (WhiteNoise serves in prod)
6. Check migration `0026_add_tenant_names` applied

**Prod Settings:** `config.settings.prod` (default since Phase 1.2)  
**Health Check:** `curl https://yourdomain.com/healthz`

---

## 📚 Key Documentation

- `README.md` – Feature matrix, quick start, deployment overview
- `ROADMAP.md` – M1–M16 status, M17–M20 planned features
- `docs/DEPLOYMENT.md` – Full production deployment guide
- `docs/MASTER_ACTION_PLAN_DONE.md` – Refactoring changelog (40h sprint)
- `docs/codex_executive_summary.md` – Security audit results (90/100)

---

## ✅ Change Workflow

1. Check `docs/MASTER_ACTION_PLAN.md` for current priorities
2. Create feature branch: `git checkout -b feature/M17-ocr`
3. Implement with tests (maintain 80%+ coverage)
4. Update docs (README, ROADMAP if adding features)
5. Run full test suite + linting (`ruff check .`, `black .`)
6. Document in `MASTER_ACTION_PLAN_DONE.md` if completing planned task
7. PR with reference to milestone/issue

**DSGVO Note:** Tenant data changes require audit log + documentation update.
