# Test Coverage Gaps Report

**Scan Date:** 2025-10-22  
**Coverage Artifact:** `backend/app/coverage.xml` (coverage.py 7.11.0, line-rate **69.0 %**)  
**Scope Reminder:** landlord + config; migrations/tests excluded

## Coverage Snapshot (lowest modules)

| Module | Covered / Total | Coverage |
| --- | --- | --- |
| `backend/app/landlord/auth.py` | 0 / 20 | 0 % |
| `backend/app/landlord/fsm.py` | 8 / 114 | 7 % |
| `backend/app/landlord/services/chat_session.py` | 16 / 103 | 16 % |
| `backend/app/landlord/tasks.py` | 23 / 106 | 22 % |
| `backend/app/landlord/views_portal.py` | 42 / 181 | 23 % |
| `backend/app/landlord/views.py` | 46 / 186 | 25 % |
| `backend/app/landlord/api/tenants.py` | 16 / 59 | 27 % |

## 🔴 Critical (close gaps immediately)

- **Session auth helpers are untested** — `backend/app/landlord/auth.py:1` (0 % coverage)  
  - *Risk:* Tenant login flows can silently break (wrong redirect, stale session leakage) without any test failure.  
  - *Add:* Lightweight unit tests that call the decorator and `get_tenant_from_session` using `rf = RequestFactory()`.  
    ```python
    @pytest.mark.django_db
    def test_tenant_login_required_redirects_unauthenticated(rf):
        @tenant_login_required
        def view(request): return HttpResponse("ok")
        resp = view(rf.get("/portal/"))
        assert resp.status_code == 302 and resp.url.endswith("/tenant/login/")

    def test_get_tenant_from_session_clears_stale_session(rf):
        request = rf.get("/")
        request.session = {"tenant_id": 999}
        assert get_tenant_from_session(request) is None
        assert "tenant_id" not in request.session
    ```
  - *Effort:* 1 h.

- **Chat state machine lacks regression safety nets** — `backend/app/landlord/fsm.py:24` (CC **46**, 7 % coverage)  
  - *Risk:* State regressions (e.g. invalid severity, hazardous keyword escalation) reach production undetected.  
  - *Add:* Focused unit tests covering every state branch, including negative paths (`occurred_at` in future, overlong location, hazard keywords bumping severity). Build a parametrised test table to ensure each `STATE -> state_handler` contract is verified.  
  - *Effort:* 4 h to author fixtures + tests; reuse them later during FSM refactor.

- **chat_session service happy-path only** — `backend/app/landlord/services/chat_session.py:38` & `:66` (16 % coverage)  
  - *Risk:* Optimistic locking, file staging limits, and idempotency semantics are largely untested; regressions would surface as duplicate issues or lost attachments.  
  - *Add:* Isolate `_stage_files` via `SimpleUploadedFile`, asserting that >10 MB or invalid MIME raises the documented `ValueError`. Exercise `message()` with conflicting versions and ensure `RuntimeError("STATE_VERSION_CONFLICT")` propagates. For `confirm()`, assert that a second call with the same idempotency key reuses the original issue and that temp files are moved to `issue` storage.  
  - *Snippet:*
    ```python
    @pytest.mark.django_db
    def test_chat_confirm_idempotent_moves_files(tmp_path, chat_session_factory):
        session = chat_session_factory(payload={"summary": "Wasser"}, temp_files=[...])
        issue_id_1, ticket_1 = confirm(session.id, idempotency_key=uuid.uuid4())
        issue_id_2, ticket_2 = confirm(session.id, idempotency_key=uuid.uuid4())
        assert issue_id_1 == issue_id_2 and ticket_1 == ticket_2
    ```
  - *Effort:* 5 h (includes storage fixture plumbing).

## 🟡 Medium (cover before release)

- **Async notification tasks barely exercised** — `backend/app/landlord/tasks.py:28` (22 % coverage)  
  - *Gap:* No test validates that ICS attachments, retry configuration, or missing email addresses behave as expected.  
  - *Add:* Use Django’s `mail.outbox` to assert generated subjects and ICS payloads; mock `build_ics` for deterministic bytes. Include failure-path tests to confirm tasks short-circuit when no tenant email is present.  
  - *Effort:* 3 h.

- **GDPR export/erase edge cases** — `backend/app/landlord/api/tenants.py:20` (27 % coverage)  
  - *Gap:* Current test only asserts the happy path; duplicate-note suppression, optional phone fields, and timezone stamping remain untested.  
  - *Add:* Extend `tests/test_admin_tenants_gdpr.py` to hit the idempotent erase path twice, verifying that a second call neither re-creates notes nor mutates already-redacted fields.  
  - *Effort:* 2 h.

- **CSV exports & vendor flows** — `backend/app/landlord/api/issues_export.py:11`, `backend/app/landlord/views_vendor.py:1` (≤28 % coverage)  
  - *Gap:* Export sanitisation and vendor-session guards (magic-link login, unauthorized access) rely on manual QA.  
  - *Add:* Request-level tests mocking vendor auth tokens to assert 403 responses for unassigned issues and to confirm CSV sanitises line breaks.  
  - *Effort:* 3 h.

- **Settings/configuration not measured** — `pyproject.toml:56` restricts coverage sources to `["landlord"]`; `backend/app/config/*.py` (ASGI/WSGI, Celery) never execute under tests.  
  - *Action:* Broaden `coverage.run.source` to `["landlord", "config"]`, then add smoke tests that import `config.settings.base` and `config.celery_app` to catch missing environment keys.  
  - *Effort:* 1 h to adjust config + 2 h for smoke tests.

## 🟢 Low (opportunistic)

- **Portal CRUD views (`backend/app/landlord/views_portal.py:39`, `:204`)**  
  - Add Selenium-free view tests with staff user fixture to assert pagination, search filters, and flashing messages render expected templates.
- **Utility meter validators duplicated in views (`backend/app/landlord/views.py:604`, `:649`)**  
  - Cover the “only one default meter” guard by hitting create/update endpoints; this also increases confidence before extracting shared validation logic.

## Follow-Up

1. Expand coverage source to include `config` and fail CI below 80 % line coverage once critical gaps close.  
2. Automate nightly `pytest --cov=landlord --cov=config --cov-report=xml` and publish the XML artifact so the audit trail stays current.  
3. After adding tests, re-run `radon cc -s landlord config --exclude '*/migrations/*,*/tests/*'` to ensure complexity reductions are reflected alongside coverage gains.
