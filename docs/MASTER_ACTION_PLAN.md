# 🎯 UVM Production-Ready Master Action Plan

**Created:** 2025-10-22  
**Based on:** Codex Performance Audit (6 Reports + Executive Summary)  
**Overall Score:** 62/100 → **Target: 85/100** (Production-Ready)  
**Total Effort:** ~48h → **Realistic: 32h** (fokussiert)

---

## 📊 **CODEX AUDIT ZUSAMMENFASSUNG:**

### **✅ Was ist GUT:**
- ✅ **Solide Architektur:** Django 5.1, Clean Code, 69% Test Coverage
- ✅ **Keine SQL Injection:** Nur Django ORM, keine Raw Queries
- ✅ **Gute Patterns:** Services-Layer, FSM, Celery Tasks
- ✅ **DSGVO-Basis:** Tenant Erase implementiert

### **❌ Was ist KRITISCH:**
- 🔴 **Security:** Gunicorn CVE, SECRET_KEY exposed, Dev-Settings in Prod
- 🔴 **Performance:** CSV-Import O(N×M), Payment-Listen unbegrenzt
- 🔴 **Code Quality:** Chat FSM zu komplex (CC 46), keine Tests
- 🔴 **Coverage:** Kritische Module <20% (auth, FSM, chat_session)

---

## 🚀 **PHASE 1: CRITICAL SECURITY FIXES (SOFORT!)** ⏰ 6h

### **1.1 Gunicorn Request-Smuggling Fix** 🔴 (0.5h)

**Problem:** CVE-2024-6827 - HTTP Request Smuggling  
**Impact:** Proxy-Bypass, Cache-Poisoning, Daten-Leak  
**File:** `pyproject.toml`

```diff
# pyproject.toml
dependencies = [
-  "gunicorn==22.0.0",
+  "gunicorn==23.0.0",
]
```

**Verification:**
```bash
docker compose build web
docker compose exec web pytest backend/app/landlord -q
```

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

## 🚀 **PHASE 2: PERFORMANCE CRITICAL FIXES** ⏰ 8h

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

## 🚀 **PHASE 3: CODE QUALITY & TESTS** ⏰ 12h

### **3.1 Chat FSM Refactoring** 🔴 (6h)

**Problem:** CC 46, keine Tests, Monolith  
**File:** `landlord/fsm.py:24`

**Strategy:**
```python
# landlord/fsm_handlers.py (NEW FILE)

def handle_greeting(message: str, payload: dict) -> tuple[str, str, dict]:
    """Handle GREETING state."""
    # Extract logic from FSM.next()
    return ("CAPTURE_SUMMARY", "prompt", {})

def handle_capture_summary(message: str, payload: dict) -> tuple[str, str, dict]:
    """Handle CAPTURE_SUMMARY state."""
    # Validation + Category detection
    return ("CAPTURE_OCCURRED_AT", "prompt", {"summary": message})

# ... one handler per state

# landlord/fsm.py (REFACTORED)
from .fsm_handlers import *

class ChatFSM:
    HANDLERS = {
        "GREETING": handle_greeting,
        "CAPTURE_SUMMARY": handle_capture_summary,
        # ...
    }
    
    @staticmethod
    def next(state: str, message: str, payload: dict) -> tuple:
        handler = ChatFSM.HANDLERS.get(state)
        if not handler:
            raise ValueError(f"Invalid state: {state}")
        return handler(message, payload)
```

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
```

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

## 📊 **TIMELINE & PRIORISIERUNG:**

### **WOCHE 1 (CRITICAL - 14h):**
```
Tag 1-2: Phase 1 - Security Fixes (6h)
Tag 3-4: Phase 2 - Performance (8h)
```

### **WOCHE 2 (HIGH - 12h):**
```
Tag 1-2: Phase 3.1 - FSM Refactor (6h)
Tag 3: Phase 3.2 - Chat View (3h)
Tag 4: Phase 3.3 - Tests (3h)
```

### **WOCHE 3 (MEDIUM - 6h):**
```
Tag 1: Phase 4.1 - Sentry (2h)
Tag 2-3: Phase 4.2 - Audit Logging (3h)
Tag 4: Phase 4.3 - Final Review (1h)
```

**TOTAL: 32h über 3 Wochen**

---

## 🎯 **SUCCESS CRITERIA:**

### **After Phase 1:**
- ✅ 0 Security vulnerabilities
- ✅ `manage.py check --deploy` → 0 warnings
- ✅ Production settings default

### **After Phase 2:**
- ✅ CSV Import <5s für 1000 Zeilen
- ✅ Payment List paginiert
- ✅ N+1 Queries eliminiert

### **After Phase 3:**
- ✅ FSM CC <20
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
