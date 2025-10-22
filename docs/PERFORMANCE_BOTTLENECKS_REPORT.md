# Performance Bottlenecks Report

**Scan Date:** 2025-10-22  
**Scope:** `backend/app/landlord`, `backend/app/config`  
**Input Sources:** Static code review, `python manage.py check --deploy`, existing celery/view implementations

## 🔴 Critical (fix immediately)

- **CSV import matches contracts with O(N×M) database lookups** — `backend/app/landlord/views_payments.py:118` (`_match_contract`) is called for every CSV row and executes `Contract.objects.filter(...).select_related(...)` each time. For a 2 000-row bank export with 1 000 active contracts, this becomes millions of ORM iterations, hammering the DB and blocking the request thread for minutes.  
  - *Fix (6 h):* Resolve all candidate contracts once per upload (e.g., `contracts = list(Contract.objects.filter(...).select_related(...))`) and build lookup dictionaries keyed by normalized email, IBAN, and unit label. Move the matching logic outside the loop so each row is matched in-memory.  
  - *Validation:* Add a benchmark test uploading a fixture with 1 000 rows and assert the view completes in <2 s locally.

- **Payment list renders unbounded queryset** — `backend/app/landlord/views_payments.py:24` pulls every `PaymentTransaction` into memory, then computes totals via `sum(p.amount for p in payments)`. Once transaction history grows beyond a few thousand rows, list requests will choke memory and make template rendering unusable.  
  - *Fix (3 h):* Introduce pagination (`Paginator(payments, 50)`), switch totals to `aggregate(Sum("amount"))`, and add index-friendly ordering (`order_by("-transaction_date", "-id")`). Cache aggregate totals per contract if the UI needs full sums.

## 🟡 Medium (address during next optimization sprint)

- **Chat confirmation copies uploads synchronously** — `backend/app/landlord/services/chat_session.py:95` copies each staged file chunk-by-chunk within the HTTP request, performing storage I/O inside the transaction. A user uploading three 10 MB videos ties up the worker thread for seconds and blocks concurrent chat submissions.  
  - *Fix (5 h):* Offload the file move to a Celery task (`finalise_chat_attachments.delay(...)`) and respond immediately with a “processing” state. Alternatively, switch to `FileResponse` streaming or use Django’s `FileSystemStorage` `save`/`copy` outside the transaction.

- **Tenant portal lists lack pagination/caching** — `backend/app/landlord/views_portal.py:157` (`tenants_list`) and `backend/app/landlord/views_portal.py:235` render the entire tenant/unit collections in a single response. Data sets of >1 000 tenants will strain the template and browser.  
  - *Fix (4 h):* Reuse Django’s `Paginator`, add `PageNumberPagination` style query parameters, and memoize `Property.objects.all().values("id","name")` in Redis for the filter dropdown.

- **Reports recompute aggregates on every request** — `backend/app/landlord/views_reports.py:16` recalculates 30-day KPIs without caching. Each dashboard refresh performs multiple `COUNT`/`AVG` scans over the issues table.  
  - *Fix (3 h):* Cache the computed KPI payload for 5–10 minutes (`cache.get_or_set("reports:kpi", ...)`) and invalidate on ticket status changes (hook into `landlord.services.issues.update_status` and Celery completion handlers).

- **Celery queues share Redis broker without rate limiting** — `backend/app/config/settings/base.py:70` routes all `landlord.tasks.send_*` emails to the same `emails` queue but lacks concurrency caps. A spike of ticket notifications can overwhelm the SMTP backend.  
  - *Fix (2 h):* Configure dedicated worker pool size via `CELERY_TASK_ROUTES`/`CELERY_WORKER_CONCURRENCY`, and add exponential backoff or circuit-breaker around `EmailMultiAlternatives.send`.

## 🟢 Low (opportunistic improvements)

- **Dashboard counts recompute for every staff visit** (`backend/app/landlord/views_portal.py:23`): cache the open ticket count/recent list for 30 s to smooth bursts.
- **Utility meter contract lookup** (`backend/app/landlord/services/utility_meter_service.py:39`): cache results per `(scope_type, scope_id, meter_type)` longer than 5 minutes when usage patterns allow.
- **REST API timeouts:** Ensure gunicorn/uvicorn worker timeouts account for the longest Celery-backed view; consider async views where appropriate.

## Measurement & Verification Plan

1. **Profile CSV import** with Django’s `queryset.explain()` and `django-silk` to confirm DB queries drop after refactor.  
2. **Load-test payment pages** via Locust (`locust -f perf/payment_list.py --headless -u 20 -r 2`) to ensure latency stays <250 ms at 20 concurrent staff users.  
3. **Monitor Celery throughput** by enabling `CELERY_SEND_EVENTS` and inspecting Flower to validate task queue lengths after concurrency tuning.  
4. **Log slow queries** (set `CONN_MAX_AGE`, `django.db.backends.utils.CursorWrapper.debug_sql`) and integrate with Prometheus/Grafana for ongoing alerts.

## Follow-Up

- Prioritise implementing contract lookup caching and payment pagination, then re-run the load test suite.  
- Add regression tests preventing reintroduction of unbounded querysets (`pytest --ds=config.settings.dev tests/test_performance_view_limits.py`).  
- Update `docs/SECURITY_COMPLIANCE_AUDIT.md` with caching and worker configuration changes once deployed.
