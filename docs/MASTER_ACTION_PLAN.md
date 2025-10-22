# 🎯 UVM Production-Ready Master Action Plan

**Created:** 2025-10-22
**Updated:** 2025-10-22 (nach vollständiger Codex-Report-Review)
**Based on:** Codex Performance Audit (7 Reports + Executive Summary)
**Overall Score:** 62/100 → **Target: 85/100** (Production-Ready)
**Total Effort:** ~48h (Codex) → **Realistic: 38h** (fokussiert + detailliert)

---

## 📊 **CODEX AUDIT ZUSAMMENFASSUNG:**

### **✅ Was ist GUT:**

- ✅ **Solide Architektur:** Django 5.1, Clean Code, 69% Test Coverage
- ✅ **Keine SQL Injection:** Nur Django ORM, keine Raw Queries
- ✅ **Gute Patterns:** Services-Layer, FSM, Celery Tasks
- ✅ **DSGVO-Basis:** Tenant Erase implementiert
- ✅ **Maintainability Index:** Alle Module scored **A**

### **❌ Was ist KRITISCH:**

- 🔴 **Security:** Gunicorn CVE, SECRET_KEY exposed, Dev-Settings in Prod
- 🔴 **Performance:** CSV-Import O(N×M), Payment-Listen unbegrenzt
- 🔴 **Code Quality:** Chat FSM zu komplex (CC 46), Chat View (CC 40)
- 🔴 **Coverage:** Kritische Module <20% (auth 0%, FSM 7%, chat_session 16%)
- 🔴 **Async Tasks:** Email-Queue ohne Concurrency-Limit (22% Coverage)

### **🟡 Was ist MEDIUM:**

- 🟡 **Query Optimization:** Tenant Erase N+1, Unit Delete 7 queries
- 🟡 **Caching:** Dashboard KPIs, Utility Meter Lookups
- 🟡 **Validation:** Duplicated Unit-Meter Logic
- 🟡 **API Filters:** IssuesAdminListView CC 20 (nested branches)

---

## 🚀 **PHASE 1: CRITICAL SECURITY FIXES (SOFORT!)** ⏰ 6h

### **1.1 Gunicorn Request-Smuggling Fix** ✅ DONE (0.5h)

**Status:** ✅ Completed 2025-10-22 20:45
**Details:** See `MASTER_ACTION_PLAN_DONE.md`

---

### **1.2 Production Settings Default** 🔴 (1h)

**Problem:** WSGI/ASGI/Celery laden Dev-Settings (DEBUG=True, ALLOWED_HOSTS=['*'])
**Impact:** Production läuft unsicher!
**Files:** `config/wsgi.py:5`, `config/asgi.py:5`, `config/celery_app.py:5`

```diff
# backend/app/config/wsgi.py
-os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
+os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# backend/app/config/asgi.py
-os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
+os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# backend/app/config/celery_app.py
-os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
+os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
```

**Update README.md:**

```markdown
## Local Development:

export DJANGO_SETTINGS_MODULE=config.settings.dev
```

**Verification:**

```bash
docker compose exec web python manage.py check --deploy --settings=config.settings.prod
# Expected: 0 warnings!
```

---

### **1.3 SECRET_KEY Hardening** 🔴 (0.5h)

**Problem:** Fallback "change-me" exposed
**Impact:** Session-Hijacking, CSRF-Bypass
**File:** `config/settings/base.py:20`

```diff
# backend/app/config/settings/base.py
-SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
+SECRET_KEY = os.getenv("SECRET_KEY")
+if not SECRET_KEY:
+    raise ImproperlyConfigured("SECRET_KEY environment variable is required.")
```

**Generate new key:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Add to .env: SECRET_KEY=<generated-key>
```

---

### **1.4 Password Validators** 🟡 (0.5h)

**Problem:** Keine Password-Strength-Validierung
**File:** `config/settings/base.py`

```python
# backend/app/config/settings/base.py
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

---

### **1.5 Cookie Hardening** 🟡 (0.5h)

**Problem:** SESSION_COOKIE_HTTPONLY, CSRF_COOKIE_HTTPONLY fehlen
**File:** `config/settings/prod.py`

```python
# backend/app/config/settings/prod.py
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
```

---

### **1.6 DRF Default Permissions** 🟡 (1h)

**Problem:** REST API erlaubt Anonymous Access per Default
**File:** `config/settings/base.py`

```python
# backend/app/config/settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # ... existing settings
}
```

**Dann explizit AllowAny wo nötig:**

```python
# landlord/api/chat.py (Magic-Link endpoints)
class ChatSessionCreateView(CreateAPIView):
    permission_classes = [AllowAny]  # Explizit!
```

---

### **1.7 ALLOWED_HOSTS Validation** 🟡 (0.5h)

**Problem:** ALLOWED_HOSTS=[] mit DEBUG=False erlaubt
**File:** `config/settings/prod.py`

```python
# backend/app/config/settings/prod.py
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production!")
```

---

### **1.8 Deploy Check in CI** 🟡 (0.5h)

**Update GitHub Actions / CI:**

```yaml
# .github/workflows/test.yml
- name: Django Deploy Check
  run: |
    docker compose exec web python manage.py check --deploy --settings=config.settings.prod
```

---

## 🚀 **PHASE 2: PERFORMANCE CRITICAL FIXES** ⏰ 10h

### **2.1 CSV-Import Payment Matching** 🔴 (6h)

**Problem:** O(N×M) Contract.objects.filter pro CSV-Zeile
**Impact:** 2000 Zeilen × 1000 Contracts = Millionen ORM-Iterationen, Minuten blockiert
**File:** `landlord/views_payments.py:118`

**Refactor:**

```python
# landlord/views_payments.py
def upload_csv(request):
    # ... existing file parsing ...

    # OLD: O(N×M)
    # for row in csv_reader:
    #     contract = Contract.objects.filter(...).first()  # ❌

    # NEW: Cache contracts upfront - O(N)
    active_contracts = list(
        Contract.objects.filter(
            status__in=["active", "expiring"]
        ).select_related("tenant", "unit")
    )

    # Build in-memory lookup dictionaries
    contract_by_email = {c.tenant.email.lower(): c for c in active_contracts if c.tenant.email}
    contract_by_iban = {c.tenant.iban: c for c in active_contracts if c.tenant.iban}
    contract_by_unit = {c.unit.label: c for c in active_contracts if c.unit}

    for row in csv_reader:
        # In-memory lookup - O(1)
        contract = (
            contract_by_email.get(row['email'].lower()) or
            contract_by_iban.get(row['iban']) or
            contract_by_unit.get(row['unit_label'])
        )
        if contract:
            # ... create payment
```

**Benchmark Test:**

```python
# tests/test_payment_csv_performance.py
def test_csv_upload_1000_rows_under_2s():
    """CSV import must complete in <2s for 1000 rows."""
    start = time.time()
    upload_csv_file_with_1000_rows()
    duration = time.time() - start
    assert duration < 2.0, f"Took {duration}s, expected <2s"
```

**Verification:**

```bash
# Profile with django-silk
docker compose exec web python manage.py silk --profile
# Upload CSV, check silk dashboard for query count
```

---

### **2.2 Payment List Pagination + Aggregates** 🔴 (3h)

**Problem:** Unbounded QuerySet + Python sum() im Memory
**Impact:** >1000 Payments → OOM, Template-Rendering blockiert
**File:** `landlord/views_payments.py:24`

```python
# landlord/views_payments.py
from django.core.paginator import Paginator
from django.db.models import Sum

def payments_list(request):
    # OLD: Unbounded
    # payments = Payment.objects.select_related(...).all()
    # total = sum(p.amount for p in payments)  # ❌ Python sum!

    # NEW: Paginated + DB Aggregates
    payments_qs = Payment.objects.select_related(
        "contract__tenant", "contract__unit"
    ).order_by("-transaction_date", "-id")

    # Pagination
    paginator = Paginator(payments_qs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # DB-side aggregates
    totals = payments_qs.aggregate(
        total_amount=Sum("amount"),
        total_count=Count("id")
    )

    return render(request, "portal/payments_list.html", {
        "page_obj": page_obj,
        "totals": totals,
    })
```

**Load Test:**

```python
# tests/test_performance_payment_list.py
@pytest.mark.django_db
def test_payment_list_with_5000_records():
    """Payment list must render in <250ms for 5000 records."""
    # Create 5000 payments
    Payment.objects.bulk_create([...])

    start = time.time()
    response = client.get("/portal/payments/")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 0.25, f"Took {duration}s, expected <250ms"
```

---

### **2.3 Chat File Upload Async** 🟡 (5h)

**Problem:** Synchrones File-Copying blockiert HTTP-Thread
**Impact:** 3×10MB Videos = 10s+ Request-Time, Worker blockiert
**File:** `landlord/services/chat_session.py:95`

**Refactor:**

```python
# landlord/tasks.py (NEW TASK)
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def finalise_chat_attachments(self, issue_id, temp_file_paths):
    """Move staged files from temp to issue storage (async)."""
    issue = Issue.objects.get(pk=issue_id)

    for temp_path in temp_file_paths:
        try:
            # Move file to issue storage
            with open(temp_path, 'rb') as f:
                issue.attachments.create(
                    file=File(f, name=Path(temp_path).name),
                    uploaded_by=issue.tenant,
                )
            # Clean up temp
            os.remove(temp_path)
        except Exception as exc:
            self.retry(exc=exc, countdown=60)

# landlord/services/chat_session.py (UPDATED)
def confirm(session_id, idempotency_key):
    with transaction.atomic():
        # Create issue immediately
        issue = Issue.objects.create(...)

        # Stage file paths (don't move yet!)
        temp_paths = [f.path for f in session.temp_files]

        # Return issue immediately
        ticket = issue.ticket_number

    # Move files ASYNC (outside transaction!)
    if temp_paths:
        finalise_chat_attachments.delay(issue.id, temp_paths)

    return issue.id, ticket
```

**Tests:**

```python
# tests/test_chat_async_upload.py
@pytest.mark.django_db
def test_confirm_returns_immediately_with_large_files():
    """confirm() must return in <1s even with 30MB files."""
    session = create_chat_session_with_30mb_files()

    start = time.time()
    issue_id, ticket = confirm(session.id, uuid.uuid4())
    duration = time.time() - start

    assert duration < 1.0
    assert Issue.objects.get(pk=issue_id).ticket_number == ticket

    # Files are processed async (check in background)
```

---

### **2.4 Tenant/Unit Portal Pagination** 🟡 (2h)

**Problem:** Unbounded tenant/unit lists
**Files:** `landlord/views_portal.py:157`, `:235`

```python
# landlord/views_portal.py
from django.core.paginator import Paginator

def tenants_list(request):
    tenants_qs = Tenant.objects.select_related("unit").order_by("name")

    # Pagination
    paginator = Paginator(tenants_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/tenants_list.html", {"page_obj": page_obj})

def units_list(request):
    units_qs = Unit.objects.select_related("property").order_by("label")

    # Pagination
    paginator = Paginator(units_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/units_list.html", {"page_obj": page_obj})
```

---

### **2.5 Dashboard KPI Caching** 🟡 (2h)

**Problem:** Dashboard re-computes KPIs bei jedem Request
**File:** `landlord/views_reports.py:16`

```python
# landlord/views_reports.py
from django.core.cache import cache

def dashboard(request):
    cache_key = "dashboard:kpis:30d"
    kpis = cache.get(cache_key)

    if not kpis:
        # Expensive aggregates
        kpis = {
            "open_issues": Issue.objects.filter(status__in=["new", "in_progress"]).count(),
            "avg_response_time": Issue.objects.aggregate(Avg("response_time"))["response_time__avg"],
            "total_tenants": Tenant.objects.count(),
            # ...
        }
        cache.set(cache_key, kpis, 300)  # 5 minutes TTL

    return render(request, "portal/dashboard.html", {"kpis": kpis})

# Invalidate on issue status change
# landlord/services/issues.py
def update_status(issue_id, new_status):
    with transaction.atomic():
        issue = Issue.objects.select_for_update().get(pk=issue_id)
        issue.status = new_status
        issue.save()

    # Invalidate cache
    cache.delete("dashboard:kpis:30d")
```

---

### **2.6 Celery Email Queue Concurrency** 🟡 (1h)

**Problem:** Email-Queue ohne Rate-Limit
**File:** `config/settings/base.py:70`

```python
# config/settings/base.py
CELERY_TASK_ROUTES = {
    "landlord.tasks.send_*": {"queue": "emails"},
}

# NEW: Concurrency limits
CELERY_WORKER_CONCURRENCY = {
    "emails": 5,  # Max 5 concurrent email tasks
    "default": 10,
}

# NEW: Exponential backoff
from celery import shared_task

@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def send_issue_created(self, issue_id):
    # ... existing email logic
```

---

### **2.7-2.9: Query Optimization (bereits in Phase 2.1-2.2 erwähnt)**

- ✅ **2.7:** Tenant Erase N+1 → 3 queries (bereits oben)
- ✅ **2.8:** Unit Delete 7→2 queries (bereits oben)
- ✅ **2.9:** Attachment Size Aggregate (bereits oben)
- ✅ **2.10:** Database Indexes (bereits oben)

---

## 🚀 **PHASE 3: CODE QUALITY & TESTS** ⏰ 14h

### **2.1 CSV-Import Payment Matching** 🔴 (3h)

**Problem:** O(N×M) Contract.objects.filter pro CSV-Zeile
**File:** `landlord/views_payments.py:118`

**Refactor:**

```python
# landlord/views_payments.py
def upload_csv(request):
    # ... existing file parsing ...

    # OLD: O(N×M)
    # for row in csv_reader:
    #     contract = Contract.objects.filter(...).first()  # ❌

    # NEW: Cache contracts upfront
    active_contracts = {
        (c.tenant_id, c.unit_id): c
        for c in Contract.objects.filter(
            status__in=["active", "expiring"]
        ).select_related("tenant", "unit")
    }

    for row in csv_reader:
        tenant_key = (tenant_id, unit_id)
        contract = active_contracts.get(tenant_key)
        if contract:
            # ... create payment
```

**Tests:**

```python
# tests/test_payment_csv_performance.py
def test_csv_upload_with_1000_rows():
    # Benchmark: Should complete in <5s
    start = time.time()
    upload_csv_file_with_1000_rows()
    assert time.time() - start < 5.0
```

---

### **2.2 Payment List Pagination** 🔴 (1h)

**Problem:** Alle Payments ohne Limit laden
**File:** `landlord/views_payments.py:24`

```python
# landlord/views_payments.py
from django.core.paginator import Paginator

def payments_list(request):
    payments = Payment.objects.select_related("contract__tenant", "contract__unit").order_by("-created_at")

    # Add pagination
    paginator = Paginator(payments, 50)  # 50 per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "portal/payments_list.html", {"page_obj": page_obj})
```

**Template:**

```django
{# portal/payments_list.html #}
{% for payment in page_obj %}
  {# ... #}
{% endfor %}

{# Pagination controls #}
<div class="pagination">
    {% if page_obj.has_previous %}
        <a href="?page=1">First</a>
        <a href="?page={{ page_obj.previous_page_number }}">Previous</a>
    {% endif %}
    Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
    {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}">Next</a>
        <a href="?page={{ page_obj.paginator.num_pages }}">Last</a>
    {% endif %}
</div>
```

---

### **2.3 Tenant Erase N+1 Fix** 🟡 (2h)

**Problem:** 1+N queries für IssueNote.exists()
**File:** `landlord/api/tenants.py:120`

```python
# landlord/api/tenants.py
from django.db.models import Q

def tenant_erase(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    marker = "[REDACTED by admin]"

    # OLD: N+1
    # for issue in tenant.issues.all():
    #     if not IssueNote.objects.filter(issue=issue, text__icontains=marker).exists():
    #         IssueNote.objects.create(...)  # ❌

    # NEW: Bulk-aware
    issue_ids = list(tenant.issues.values_list("id", flat=True))
    existing_markers = set(
        IssueNote.objects.filter(
            issue_id__in=issue_ids,
            text__icontains=marker
        ).values_list("issue_id", flat=True)
    )

    IssueNote.objects.bulk_create([
        IssueNote(
            issue_id=issue_id,
            text=f"{marker} at {timezone.now().isoformat()}",
            visibility="internal",
        )
        for issue_id in issue_ids
        if issue_id not in existing_markers
    ])

    # ... rest of anonymization
```

---

### **2.4 Unit Delete Annotation** 🟡 (1h)

**Problem:** 7 Queries für Related-Count
**File:** `landlord/api/units.py:203`

```python
# landlord/api/units.py
from django.db.models import Count

class UnitDeleteAPIView(DestroyAPIView):
    queryset = Unit.objects.annotate(
        tenant_count=Count("tenants", distinct=True),
        meter_count=Count("utility_meters", distinct=True),
        issue_count=Count("issues", distinct=True),
        contract_count=Count("contracts", distinct=True),
    )

    def destroy(self, request, *args, **kwargs):
        unit = self.get_object()
        dependencies = []
        if unit.tenant_count:
            dependencies.append(f"{unit.tenant_count} Mieter")
        if unit.meter_count:
            dependencies.append(f"{unit.meter_count} Zähler")
        # ...
```

---

### **2.5 Attachment Size Aggregate** 🟡 (0.5h)

**File:** `landlord/views_tenant.py:193`

```python
from django.db.models import Sum
from django.db.models.functions import Coalesce

total_size = issue.attachments.aggregate(
    total=Coalesce(Sum("size_bytes"), 0)
)["total"]

if total_size + file.size > 40 * 1024 * 1024:
    return JsonResponse({"error": "Quota exceeded"}, status=413)
```

---

### **2.6 Database Indexes** 🟡 (1h + migration)

**File:** `landlord/models.py`

```python
# landlord/models.py
class IssueNote(TimeStampedModel):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=["issue", "-created_at"], name="issue_note_recent_idx"),
        ]

class Appointment(TimeStampedModel):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=["issue", "-created_at"], name="appointment_recent_idx"),
        ]

class VendorAttachment(TimeStampedModel):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=["issue", "-created_at"], name="vendor_attach_recent_idx"),
        ]
```

**Create migration:**

```bash
docker compose exec web python manage.py makemigrations -n add_query_indexes
docker compose exec web python manage.py migrate
```

---

## 🚀 **PHASE 3: CODE QUALITY & TESTS** ⏰ 16h

### **3.1 Chat FSM Refactoring** 🔴 (6h)

**Problem:** CC 46 (Grade F!), 11 sequential branches, keine Tests
**Impact:** Unmaintainable, Regressions undetected
**File:** `landlord/fsm.py:24`

**Strategy - State Handler Pattern:**

```python
# landlord/fsm_handlers.py (NEW FILE)

def handle_greeting(message: str, payload: dict) -> tuple[str, str, dict, list]:
    """Handle GREETING state."""
    if not message.strip():
        raise ValueError("VALIDATION:text:empty")

    # Category detection
    category = detect_category(message)
    return ("CAPTURE_SUMMARY", get_prompt("CAPTURE_SUMMARY"), {"category": category}, [])

def handle_capture_summary(message: str, payload: dict) -> tuple[str, str, dict, list]:
    """Handle CAPTURE_SUMMARY state."""
    if len(message) < 10:
        raise ValueError("VALIDATION:summary:too_short")

    category = payload.get("category") or detect_category(message)
    return ("CAPTURE_OCCURRED_AT", get_prompt("CAPTURE_OCCURRED_AT"), {"summary": message, "category": category}, [])

def handle_capture_occurred_at(message: str, payload: dict) -> tuple[str, str, dict, list]:
    """Handle CAPTURE_OCCURRED_AT state."""
    try:
        dt = parse_datetime(message)
        if not dt:
            raise ValueError("VALIDATION:occurred_at:invalid_format")
        if dt > timezone.now():
            raise ValueError("VALIDATION:occurred_at:future")

        return ("CAPTURE_LOCATION", get_prompt("CAPTURE_LOCATION"), {"occurred_at": dt}, [])
    except Exception:
        raise ValueError("VALIDATION:occurred_at:parse_error")

# ... handlers for all 11 states

def detect_category(text: str) -> str:
    """Shared category detection logic."""
    text_lower = text.lower()

    # Heating keywords
    if any(kw in text_lower for kw in ["heizung", "warm", "temperatur", "kalt"]):
        return "heating"

    # Water keywords
    if any(kw in text_lower for kw in ["wasser", "dusche", "bad", "waschbecken", "leck"]):
        return "water"

    # Electricity keywords
    if any(kw in text_lower for kw in ["strom", "licht", "elektrik", "sicherung"]):
        return "electricity"

    # Structural keywords
    if any(kw in text_lower for kw in ["wand", "dach", "fenster", "tür", "schimmel"]):
        return "structural"

    return "other"

# landlord/fsm.py (REFACTORED)
from .fsm_handlers import *

class ChatFSM:
    STATE_HANDLERS = {
        "GREETING": handle_greeting,
        "CAPTURE_SUMMARY": handle_capture_summary,
        "CAPTURE_OCCURRED_AT": handle_capture_occurred_at,
        "CAPTURE_LOCATION": handle_capture_location,
        "CAPTURE_SEVERITY": handle_capture_severity,
        "CAPTURE_MEDIA": handle_capture_media,
        "CAPTURE_CONTACT": handle_capture_contact,
        "CONFIRM": handle_confirm,
        "CREATE_ISSUE": handle_create_issue,
        "DONE": handle_done,
    }

    @staticmethod
    def next(state: str, message: str, payload: dict) -> tuple:
        """
        Transition to next state.
        Returns: (next_state, prompt, delta, warnings)
        """
        handler = ChatFSM.STATE_HANDLERS.get(state)
        if not handler:
            raise ValueError(f"VALIDATION:state:unknown ({state})")

        return handler(message, payload)
```

**Comprehensive Tests:**

```python
# tests/test_fsm_handlers.py
import pytest
from landlord.fsm_handlers import *

class TestGreetingHandler:
    def test_greeting_with_heating_keyword(self):
        next_state, prompt, delta, warnings = handle_greeting("Die Heizung ist kaputt", {})
        assert next_state == "CAPTURE_SUMMARY"
        assert delta["category"] == "heating"

    def test_greeting_empty_text_raises(self):
        with pytest.raises(ValueError, match="VALIDATION:text:empty"):
            handle_greeting("", {})

class TestCaptureOccurredAt:
    def test_future_date_rejected(self):
        tomorrow = (timezone.now() + timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="VALIDATION:occurred_at:future"):
            handle_capture_occurred_at(tomorrow, {})

    def test_valid_past_date(self):
        yesterday = (timezone.now() - timedelta(days=1)).isoformat()
        next_state, _, delta, _ = handle_capture_occurred_at(yesterday, {})
        assert next_state == "CAPTURE_LOCATION"
        assert "occurred_at" in delta

class TestCaptureSeverity:
    def test_hazard_keywords_bump_severity(self):
        """Hazard keywords should escalate severity to HIGH."""
        next_state, _, delta, warnings = handle_capture_severity(
            "Es gibt Schimmel und Asbest!",
            {"severity": "low"}
        )
        assert delta["severity"] == "high"
        assert any("hazard" in w.lower() for w in warnings)

class TestCategoryDetection:
    @pytest.mark.parametrize("text,expected", [
        ("Die Heizung funktioniert nicht", "heating"),
        ("Wasser läuft aus dem Bad", "water"),
        ("Strom ist ausgefallen", "electricity"),
        ("Schimmel an der Wand", "structural"),
        ("Müll nicht abgeholt", "other"),
    ])
    def test_category_detection(self, text, expected):
        assert detect_category(text) == expected
```

**Estimated Effort:**

- Refactoring: 3h
- Tests (11 states × 3 test cases): 3h
- **Total: 6h**

---

### **3.2 Chat View Decomposition** 🔴 (3h)

**Problem:** CC 40 (Grade E!), 120+ lines, 4 nested if-ladders
**File:** `landlord/views.py:163`

**Extract Helpers:**

```python
# landlord/views_helpers.py (NEW FILE)

def validate_chat_state(session, expected_states):
    """Guard: Ensure session is in expected state(s)."""
    if isinstance(expected_states, str):
        expected_states = [expected_states]

    if session.state not in expected_states:
        raise ValidationError({
            "code": "STATE_MISMATCH",
            "expected": expected_states,
            "actual": session.state,
        })

def parse_chat_files(request):
    """Extract uploaded files from request."""
    if not hasattr(request, "FILES"):
        return None
    return request.FILES.getlist("files")

def build_chat_payload(validated_data, raw_data):
    """Merge validated data with raw text fields."""
    payload = dict(validated_data)

    # Ensure 'text' is forwarded if present but omitted in validation
    raw_text = (raw_data.get("text") or "").strip()
    if raw_text:
        payload["text"] = raw_text

        # Map text → summary for GREETING/CAPTURE_SUMMARY
        if "summary" not in payload:
            payload["summary"] = raw_text

    return payload

def apply_fsm_transition(session, message, payload):
    """Apply FSM transition and update session."""
    from .fsm import ChatFSM

    try:
        next_state, prompt, delta, warnings = ChatFSM.next(
            session.state, message, payload
        )
    except ValueError as e:
        # FSM validation errors
        if str(e).startswith("VALIDATION:"):
            raise ValidationError({"detail": str(e)})
        raise

    return next_state, prompt, delta, warnings

# landlord/views.py (REFACTORED)
from .views_helpers import *

class ChatMessageView(CreateAPIView):
    def post(self, request, session_id):
        # 1. Throttle check
        enforce_burst_throttle(session_id=session_id)

        # 2. Load session with locking
        session = get_object_or_404(
            ChatSession.objects.select_for_update(),
            pk=session_id
        )

        # 3. Validate version (optimistic locking)
        data = request.data
        if session.version != data.get("version"):
            return Response(
                {"code": "STATE_VERSION_CONFLICT"},
                status=status.HTTP_409_CONFLICT
            )

        # 4. Serialize & validate
        serializer = ChatMessageSerializer(
            data=data,
            context={"state": session.state}
        )
        if not serializer.is_valid():
            return Response(
                {"code": "VALIDATION_ERROR", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Build payload
        payload = build_chat_payload(serializer.validated_data, data)
        files = parse_chat_files(request)

        # 6. Apply FSM transition
        next_state, prompt, delta, warnings = apply_fsm_transition(
            session, payload.get("text", ""), payload
        )

        # 7. Call message service
        try:
            updated_session = message(
                session_id=session.id,
                message=payload.get("text", ""),
                payload=delta,
                files=files,
                version=session.version,
            )
        except RuntimeError as e:
            if "STATE_VERSION_CONFLICT" in str(e):
                return Response(
                    {"code": "STATE_VERSION_CONFLICT"},
                    status=status.HTTP_409_CONFLICT
                )
            raise

        # 8. Return response
        return Response({
            "state": updated_session.state,
            "prompt": prompt,
            "version": updated_session.version,
            "warnings": warnings,
        })
```

**Tests:**

```python
# tests/test_chat_view_helpers.py

def test_validate_chat_state_raises_on_mismatch():
    session = ChatSession(state="GREETING")
    with pytest.raises(ValidationError, match="STATE_MISMATCH"):
        validate_chat_state(session, "CAPTURE_SUMMARY")

def test_build_chat_payload_maps_text_to_summary():
    payload = build_chat_payload(
        validated_data={},
        raw_data={"text": "Heizung kaputt"}
    )
    assert payload["text"] == "Heizung kaputt"
    assert payload["summary"] == "Heizung kaputt"
```

---

### **3.3 Critical Test Coverage Gaps** 🔴 (5h)

**Gap 1: Session Auth (0% Coverage!)**
**File:** `landlord/auth.py`

```python
# tests/test_auth_session.py
import pytest
from django.test import RequestFactory
from landlord.auth import tenant_login_required, get_tenant_from_session

@pytest.mark.django_db
def test_tenant_login_required_redirects_unauthenticated():
    """Unauthenticated requests should redirect to tenant login."""
    @tenant_login_required
    def protected_view(request):
        return HttpResponse("OK")

    rf = RequestFactory()
    request = rf.get("/portal/")
    request.session = {}

    response = protected_view(request)
    assert response.status_code == 302
    assert "/tenant/login/" in response.url

@pytest.mark.django_db
def test_get_tenant_from_session_clears_stale_session():
    """Stale tenant_id should be removed from session."""
    rf = RequestFactory()
    request = rf.get("/")
    request.session = {"tenant_id": 99999}  # Non-existent

    tenant = get_tenant_from_session(request)
    assert tenant is None
    assert "tenant_id" not in request.session

@pytest.mark.django_db
def test_get_tenant_from_session_returns_valid_tenant():
    """Valid tenant_id should return Tenant object."""
    tenant = Tenant.objects.create(name="Test", email="test@example.com")

    rf = RequestFactory()
    request = rf.get("/")
    request.session = {"tenant_id": tenant.id}

    result = get_tenant_from_session(request)
    assert result == tenant
```

**Gap 2: Chat Session Service (16% Coverage!)**
**File:** `landlord/services/chat_session.py`

```python
# tests/test_chat_session_service.py

@pytest.mark.django_db
def test_stage_files_rejects_oversized_upload():
    """Files >10MB should raise ValueError."""
    session = ChatSession.objects.create(state="CAPTURE_MEDIA")
    large_file = SimpleUploadedFile(
        "huge.jpg",
        b"x" * (11 * 1024 * 1024),  # 11MB
        content_type="image/jpeg"
    )

    with pytest.raises(ValueError, match="File too large"):
        _stage_files(session, [large_file])

@pytest.mark.django_db
def test_stage_files_rejects_invalid_mime_type():
    """Non-allowed MIME types should raise ValueError."""
    session = ChatSession.objects.create(state="CAPTURE_MEDIA")
    exe_file = SimpleUploadedFile(
        "virus.exe",
        b"MZ",  # EXE header
        content_type="application/x-msdownload"
    )

    with pytest.raises(ValueError, match="Invalid file type"):
        _stage_files(session, [exe_file])

@pytest.mark.django_db
def test_message_raises_on_version_conflict():
    """Concurrent updates should raise RuntimeError."""
    session = ChatSession.objects.create(state="GREETING", version=1)

    with pytest.raises(RuntimeError, match="STATE_VERSION_CONFLICT"):
        message(
            session_id=session.id,
            message="Hello",
            payload={},
            files=None,
            version=0,  # Wrong version!
        )

@pytest.mark.django_db
def test_confirm_is_idempotent():
    """Multiple confirm() calls with same key should return same issue."""
    session = ChatSession.objects.create(
        state="CONFIRM",
        payload={"summary": "Heizung kaputt", "category": "heating"}
    )
    idempotency_key = uuid.uuid4()

    # First call
    issue_id_1, ticket_1 = confirm(session.id, idempotency_key)

    # Second call (idempotent)
    issue_id_2, ticket_2 = confirm(session.id, idempotency_key)

    assert issue_id_1 == issue_id_2
    assert ticket_1 == ticket_2
    assert Issue.objects.filter(id=issue_id_1).count() == 1

@pytest.mark.django_db
def test_confirm_moves_temp_files_to_issue_storage():
    """Staged files should be attached to created issue."""
    session = ChatSession.objects.create(
        state="CONFIRM",
        payload={"summary": "Wasser", "category": "water"}
    )

    # Stage temp files
    temp_file = SimpleUploadedFile("test.jpg", b"fake image", content_type="image/jpeg")
    _stage_files(session, [temp_file])

    # Confirm
    issue_id, ticket = confirm(session.id, uuid.uuid4())

    # Assert files are attached
    issue = Issue.objects.get(pk=issue_id)
    assert issue.attachments.count() == 1
    assert issue.attachments.first().file.name.endswith("test.jpg")
```

**Gap 3: Async Tasks (22% Coverage!)**
**File:** `landlord/tasks.py`

```python
# tests/test_tasks_email.py
from django.core import mail

@pytest.mark.django_db
def test_send_issue_created_includes_ics_attachment():
    """Email should include ICS calendar invite."""
    issue = Issue.objects.create(
        summary="Heizung kaputt",
        tenant=tenant,
        category="heating"
    )

    send_issue_created.delay(issue.id)

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == f"Neues Ticket: {issue.ticket_number}"
    assert email.to == [issue.tenant.email]

    # Check ICS attachment
    assert len(email.attachments) == 1
    filename, content, mime = email.attachments[0]
    assert filename.endswith(".ics")
    assert mime == "text/calendar"

@pytest.mark.django_db
def test_send_issue_created_skips_if_no_tenant_email():
    """Task should short-circuit if tenant has no email."""
    tenant_no_email = Tenant.objects.create(name="No Email")
    issue = Issue.objects.create(
        summary="Test",
        tenant=tenant_no_email,
    )

    send_issue_created.delay(issue.id)

    # No email sent
    assert len(mail.outbox) == 0

@pytest.mark.django_db
def test_send_status_changed_retries_on_smtp_error():
    """SMTP errors should trigger retry with backoff."""
    with patch("smtplib.SMTP.sendmail", side_effect=smtplib.SMTPException("Server error")):
        issue = Issue.objects.create(summary="Test", tenant=tenant)

        with pytest.raises(smtplib.SMTPException):
            send_status_changed.apply(args=[issue.id, "in_progress"], throw=True)

        # Assert retry was scheduled
        # (Check Celery task state or mock retry())
```

---

### **3.4 Medium Complexity Refactoring** 🟡 (2h)

**IssuesAdminListView (CC 20)**
**File:** `landlord/api/issues.py:30`

```python
# landlord/api/issues.py
from django_filters import rest_framework as filters

class IssueFilter(filters.FilterSet):
    """Django-filter based filtering for cleaner code."""

    status = filters.MultipleChoiceFilter(choices=Issue.STATUS_CHOICES)
    severity = filters.NumberFilter()
    severity_min = filters.NumberFilter(field_name="severity", lookup_expr="gte")
    severity_max = filters.NumberFilter(field_name="severity", lookup_expr="lte")
    category = filters.ChoiceFilter(choices=Issue.CATEGORY_CHOICES)
    created_from = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_to = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    search = filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(summary__icontains=value) |
            Q(ticket_number__icontains=value) |
            Q(tenant__name__icontains=value)
        )

    class Meta:
        model = Issue
        fields = ["status", "severity", "category", "created_from", "created_to", "search"]

class IssuesAdminListView(ListAPIView):
    queryset = Issue.objects.select_related("tenant", "unit").all()
    serializer_class = IssueListSerializer
    filterset_class = IssueFilter  # ← Use django-filter!

    # Removed 60 lines of manual filtering! 🎉
```

---

### **3.5 Test Coverage Extension** 🟡 (2h)

**Extend coverage.run.source to include config:**

```toml
# pyproject.toml
[tool.coverage.run]
source = ["landlord", "config"]  # ← Add config!
omit = ["*/migrations/*", "*/tests/*"]
```

**Add config smoke tests:**

```python
# tests/test_config_smoke.py

def test_base_settings_imports_without_error():
    """Ensure base settings can be imported."""
    from config.settings import base
    assert base.SECRET_KEY  # Should exist or raise

def test_celery_app_imports_without_error():
    """Ensure Celery app can be imported."""
    from config import celery_app
    assert celery_app.app is not None

def test_wsgi_application_imports():
    """WSGI app should be importable."""
    from config import wsgi
    assert wsgi.application is not None
```

---

## 🚀 **PHASE 4: MONITORING & FINAL HARDENING** ⏰ 8h```python

# landlord/fsm_handlers.py (NEW FILE)

def handle_greeting(message: str, payload: dict) -> tuple[str, str, dict]:
"""Handle GREETING state.""" # Extract logic from FSM.next()
return ("CAPTURE_SUMMARY", "prompt", {})

def handle_capture_summary(message: str, payload: dict) -> tuple[str, str, dict]:
"""Handle CAPTURE_SUMMARY state.""" # Validation + Category detection
return ("CAPTURE_OCCURRED_AT", "prompt", {"summary": message})

# ... one handler per state

# landlord/fsm.py (REFACTORED)

from .fsm_handlers import \*

class ChatFSM:
HANDLERS = {
"GREETING": handle_greeting,
"CAPTURE_SUMMARY": handle_capture_summary, # ...
}

    @staticmethod
    def next(state: str, message: str, payload: dict) -> tuple:
        handler = ChatFSM.HANDLERS.get(state)
        if not handler:
            raise ValueError(f"Invalid state: {state}")
        return handler(message, payload)

````

**Tests:**

```python
# tests/test_fsm_handlers.py
def test_greeting_state():
    next_state, prompt, delta = handle_greeting("Hallo", {})
    assert next_state == "CAPTURE_SUMMARY"

def test_summary_validation():
    with pytest.raises(ValueError, match="VALIDATION:summary:too_short"):
        handle_capture_summary("abc", {})

def test_category_detection():
    _, _, delta = handle_capture_summary("Die Heizung ist kaputt", {})
    assert delta["category"] == "heating"
````

---

### **3.2 Chat View Decomposition** 🔴 (3h)

**Problem:** CC 40, Monolith
**File:** `landlord/views.py:163`

**Extract helpers:**

```python
# landlord/views_helpers.py (NEW)

def validate_chat_state(session, expected_state):
    """Helper for state validation."""
    if session.state != expected_state:
        raise ValidationError(f"Expected {expected_state}, got {session.state}")

def parse_chat_files(request):
    """Helper for file parsing."""
    if not hasattr(request, "FILES"):
        return None
    return request.FILES.getlist("files")

def apply_fsm_transition(session, message, payload):
    """Helper for FSM logic."""
    from .fsm import ChatFSM
    next_state, prompt, delta = ChatFSM.next(session.state, message, payload)
    # ... update session
    return next_state, prompt, delta
```

---

### **3.3 Test Coverage → 80%** 🔴 (3h)

**Priority Tests:**

```python
# tests/test_auth_redirects.py
def test_unauthenticated_portal_redirect():
    """Staff-Portal requires login."""
    response = client.get("/portal/")
    assert response.status_code == 302
    assert "/admin/login/" in response.url

# tests/test_fsm_edge_cases.py
def test_fsm_invalid_state_transition():
    with pytest.raises(ValueError):
        ChatFSM.next("INVALID_STATE", "text", {})

def test_fsm_validation_errors():
    with pytest.raises(ValueError, match="VALIDATION:"):
        ChatFSM.next("CAPTURE_SUMMARY", "", {})

# tests/test_chat_session_limits.py
def test_file_upload_quota():
    # Test 40MB limit
    with pytest.raises(ValidationError):
        upload_file_exceeding_quota()

# tests/test_tenant_erase_idempotent.py (already exists - extend!)
def test_erase_with_250_issues():
    # Performance test
    tenant = create_tenant_with_250_issues()
    erase_tenant(tenant.id)
    # Assert: <3 queries
```

**Update coverage config:**

```toml
# pyproject.toml
[tool.coverage.run]
source = ["landlord", "config"]  # Add config!
```

---

## 🚀 **PHASE 4: MONITORING & FINAL HARDENING** ⏰ 6h

### **4.1 Sentry.io Setup** (2h)

```bash
pip install sentry-sdk
```

```python
# config/settings/prod.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,  # DSGVO!
    environment="production",
)
```

---

### **4.2 Audit Logging** (3h)

```python
# landlord/models.py
class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=50)
    object_id = models.IntegerField()
    ip_address = models.GenericIPAddressField()

    class Meta:
        indexes = [
            models.Index(fields=["-timestamp", "user"]),
        ]

# landlord/middleware.py
class AuditMiddleware:
    def __call__(self, request):
        response = self.get_response(request)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Log action
            AuditLog.objects.create(...)
        return response
```

---

### **4.3 Final Security Review** (1h)

**Checklist:**

- ✅ `python manage.py check --deploy` → 0 warnings
- ✅ All SECRET_KEY rotated
- ✅ HTTPS enforced
- ✅ Cookies hardened
- ✅ DRF permissions locked
- ✅ Test coverage ≥80%
- ✅ Sentry active
- ✅ Audit logging enabled

---

## 📊 **UPDATED TIMELINE & PRIORISIERUNG:**

### **ZUSAMMENFASSUNG (38h total):**

```
Phase 1: Security          6h  (Critical - Sofort!)
Phase 2: Performance      10h  (Critical - Woche 1)
Phase 3: Code Quality     16h  (High - Woche 2)
Phase 4: Monitoring        8h  (Medium - Woche 3)
─────────────────────────────
TOTAL:                    40h  über 3 Wochen
```

---

### **WOCHE 1 (CRITICAL - 16h):**

```
Tag 1 (4h):
  ✅ 1.1 Gunicorn CVE Fix (0.5h)
  ✅ 1.2 Prod Settings Default (1h)
  ✅ 1.3 SECRET_KEY Hardening (0.5h)
  ✅ 1.4 Password Validators (0.5h)
  ✅ 1.5 Cookie Hardening (0.5h)
  ✅ 1.6 DRF Permissions (1h)

Tag 2 (6h):
  ✅ 2.1 CSV-Import Refactor (6h)

Tag 3 (3h):
  ✅ 2.2 Payment Pagination + Aggregates (3h)

Tag 4 (3h):
  ✅ 2.3 Chat Upload Async (Teil 1: 3h)

Ende Woche 1: Security ✅, Performance 60% ✅
```

---

### **WOCHE 2 (HIGH - 16h):**

```
Tag 1 (5h):
  ✅ 2.3 Chat Upload Async (Teil 2: 2h)
  ✅ 2.4 Portal Pagination (2h)
  ✅ 2.5 KPI Caching (1h)

Tag 2 (6h):
  ✅ 3.1 FSM Refactoring (6h)

Tag 3 (3h):
  ✅ 3.2 Chat View Decomposition (3h)

Tag 4 (2h):
  ✅ 3.3 Critical Test Gaps (Teil 1: 2h)

Ende Woche 2: Performance ✅, FSM/Chat View ✅
```

---

### **WOCHE 3 (MEDIUM - 8h):**

```
Tag 1 (3h):
  ✅ 3.3 Critical Test Gaps (Teil 2: 3h)

Tag 2 (2h):
  ✅ 3.4 Medium Complexity Refactor (2h)
  ✅ 4.1 Sentry Setup (Teil 1: 1h)

Tag 3 (3h):
  ✅ 4.1 Sentry Setup (Teil 2: 1h)
  ✅ 4.2 Audit Logging (2h)

Tag 4 (2h):
  ✅ 4.2 Audit Logging (Teil 2: 1h)
  ✅ 4.3 Final Review (1h)

Ende Woche 3: PRODUCTION-READY! 🚀
```

---

## 🎯 **SUCCESS CRITERIA (detailliert):**

### **After Phase 1 (Security - 6h):**

- ✅ 0 CVEs (Gunicorn 23.0.0)
- ✅ `python manage.py check --deploy --settings=config.settings.prod` → 0 warnings
- ✅ Production settings als Default (wsgi/asgi/celery)
- ✅ SECRET_KEY rotation durchgeführt
- ✅ Password Validators aktiv (12+ chars)
- ✅ Cookies hardened (HttpOnly flags)
- ✅ DRF Default Permissions = IsAuthenticated
- ✅ ALLOWED_HOSTS validation

---

### **After Phase 2 (Performance - 10h):**

- ✅ **CSV Import:** 1000 Zeilen in <2s (vorher: ~60s)
- ✅ **Payment List:** Paginiert (50/page), DB-Aggregates statt Python-Sum
- ✅ **Chat Upload:** Async file-move, Response <1s (vorher: ~10s)
- ✅ **Portal Lists:** Paginiert (Tenants, Units)
- ✅ **Dashboard:** KPIs cached (5min TTL)
- ✅ **Celery:** Email queue concurrency = 5
- ✅ **Tenant Erase:** 1+N → 3 queries
- ✅ **Unit Delete:** 7 → 2 queries
- ✅ **Attachment Check:** DB aggregate statt Python sum

**Load Test Results:**

```bash
# Payment List: 5000 records in <250ms
# CSV Upload: 2000 rows in <2s
# Dashboard: <100ms (cached)
```

---

### **After Phase 3 (Code Quality - 16h):**

- ✅ **FSM Complexity:** CC 46 → <20 (Grade F → B)
- ✅ **Chat View Complexity:** CC 40 → <20 (Grade E → B)
- ✅ **Test Coverage:** 69% → ≥80%
  - `auth.py`: 0% → 100%
  - `fsm.py`: 7% → 85%
  - `chat_session.py`: 16% → 80%
  - `tasks.py`: 22% → 70%
- ✅ **Config Coverage:** Included in coverage.run.source
- ✅ **Regression Tests:** FSM states, Chat concurrency, File limits
- ✅ **API Filters:** django-filter für IssuesAdminListView (CC 20 → 8)

**Radon Metrics:**

```bash
# Before:
Functions ≥ CC C: 24
Highest CC: 46 (FSM.next)

# After:
Functions ≥ CC C: <10
Highest CC: <20
Maintainability Index: All A
```

---

### **After Phase 4 (Monitoring - 8h):**

- ✅ **Sentry.io:** Active error tracking
  - DSN configured in prod settings
  - PII disabled (DSGVO-compliant)
  - 10% performance sampling
- ✅ **Audit Logging:** All admin actions logged
  - Tenant created/deleted
  - Document accessed
  - Payment modified
  - Issue status changed
- ✅ **Health Checks:** `/healthz` endpoint extended
  - Database connectivity
  - Redis connectivity
  - Celery worker status
- ✅ **CI/CD:** Deploy check automated
  - `pytest --cov` → fail if <80%
  - `manage.py check --deploy` → fail if warnings

---

## 🚀 **EXIT-READY CRITERIA (Gesamtbild):**

Nach Abschluss aller 4 Phasen (40h):

### **Security:**

✅ 0 CVEs (Gunicorn, pip)
✅ Django deploy check: 0 warnings
✅ SECRET_KEY rotation
✅ HTTPS enforced
✅ Cookies secured
✅ Password strength validated
✅ DRF permissions locked

### **Performance:**

✅ CSV Import: <2s (1000 rows)
✅ Payment List: <250ms (5000 records)
✅ Chat Upload: <1s response
✅ Dashboard: <100ms (cached)
✅ N+1 Queries: Eliminated
✅ Pagination: All lists

### **Quality:**

✅ Code Complexity: CC <20
✅ Test Coverage: ≥80%
✅ Radon MI: All A
✅ FSM: Fully tested
✅ Async Tasks: Covered

### **Monitoring:**

✅ Sentry.io: Active
✅ Audit Logs: Implemented
✅ Health Checks: Extended
✅ CI/CD: Automated checks

### **Documentation:**

✅ Codex Reports: 7 files
✅ Master Action Plan: This document
✅ Security Audit: Completed
✅ README: Deployment instructions

---

## 💰 **ROI-KALKULATION:**

### **Investment:**

```
Arbeit:           40h
Aufwand:          40h × 80 EUR/h = 3.200 EUR
Codex-Audit:      Bereits erledigt (2h)
```

### **Wertsteigerung:**

```
Vorher:           12.000 EUR (MVP, 62/100 Score)
Nachher:          40.000 EUR (Production-Ready, 85/100 Score)
Steigerung:       +28.000 EUR
```

### **ROI:**

```
ROI = (28.000 - 3.200) / 3.200 × 100
    = 775% 🚀
```

**Oder anders:**

```
Wert pro Arbeitsstunde: 28.000 / 40 = 700 EUR/h! 💰
```

---

## 📝 **NEXT STEPS:**

1. ✅ **Du liest** diesen erweiterten Master Plan durch
2. ✅ **Wir besprechen** den Zeitplan & Prioritäten
3. ✅ **Du entscheidest:** Sofort starten? Morgen? Review first?
4. ✅ **Ich helfe** bei jedem einzelnen Step (Pair-Programming)
5. ✅ **In 3 Wochen:** Production-Ready für Exit! 🎉

---

**BEREIT ZU STARTEN?** 😊

- ✅ Test Coverage ≥80%
- ✅ Alle Critical Module getestet

### **After Phase 4:**

- ✅ Sentry aktiv
- ✅ Audit Logging vorhanden
- ✅ **PRODUCTION-READY! 🚀**

---

## 🚀 **EXIT-READY CRITERIA:**

Nach Abschluss aller 4 Phasen:

✅ **Security:** 0 CVEs, alle Settings gehärtet
✅ **Performance:** <100ms Response-Time (P95)
✅ **Quality:** CC <25, 80% Coverage
✅ **Monitoring:** Sentry + Audit-Logs aktiv
✅ **Documentation:** Security Audit Report komplett

**DANN:** Pitchable an PropTech-Firmen für ~40.000 EUR! 💰

---

## 📝 **NEXT STEPS:**

1. ✅ **Du liest** diesen Plan durch
2. ✅ **Wir starten** mit Phase 1.1 (Gunicorn Fix)
3. ✅ **Ich helfe** bei jedem Step
4. ✅ **In 3 Wochen:** Production-Ready! 🎉

**Bereit zu starten?** 😊
