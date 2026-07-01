# Security & Privacy Review Notes - UVM Project (Copilot Chat)

**Datum:** 2025-10-22
**Projekt:** Universal Vermieter Management (UVM)
**Verantwortlich:** Copilot Chat (kontextbewusst)
**Status:** Nach Codex Performance Audit

---

## 🎯 MEINE AUFGABE (Copilot Chat):

Führe **kontext-basiertes Security- und Privacy-Review** durch.

**Was Codex NICHT kann:**

- ❌ Business-Logic Security (FSM, Payment-Flow)
- ❌ DSGVO-orientierte Privacy Controls (Daten-Löschung, Audit-Logs)
- ❌ Infrastruktur-Security (Docker, Redis, PostgreSQL)
- ❌ Rechtliche Einschätzungen

**Was ICH machen muss:**

- ✅ Django Security Settings Review
- ✅ Authentication & Authorization Audit
- ✅ DSGVO-orientierter Privacy Check
- ✅ API Security (DRF Throttling, Permissions)
- ✅ File Upload Security
- ✅ Session Management

---

## 📋 SECURITY CHECKLIST:

### **1. Django Security Settings** 🔒

**File:** `config/settings/base.py`, `config/settings/prod.py`

```python
# Checklist:
✅ SECRET_KEY aus env-file? (nicht hardcoded)
✅ DEBUG = False in prod?
✅ ALLOWED_HOSTS konfiguriert? (nicht ['*'])
✅ SECURE_SSL_REDIRECT = True in prod?
✅ SECURE_HSTS_SECONDS >= 31536000?
✅ SESSION_COOKIE_SECURE = True?
✅ CSRF_COOKIE_SECURE = True?
✅ SESSION_COOKIE_HTTPONLY = True?
✅ X_FRAME_OPTIONS = 'DENY'?
✅ SECURE_CONTENT_TYPE_NOSNIFF = True?
✅ SECURE_BROWSER_XSS_FILTER = True?
```

**Action:**

- [ ] Prüfe alle Settings
- [ ] Erstelle `docs/SECURITY_SETTINGS_AUDIT.md`

---

### **2. Authentication & Authorization** 🔐

**Files:**

- `landlord/decorators.py` (tenant_login_required)
- `landlord/views_portal.py` (@staff_member_required)
- `landlord/views_tenant.py` (Magic-Link Auth)

```python
# Checklist:
✅ Alle Staff-Views haben @staff_member_required?
✅ Alle Tenant-Views haben @tenant_login_required?
✅ Magic-Link Tokens expirieren? (TimeStampedToken)
✅ Rate-Limiting auf Magic-Link Requests? (3/30min)
✅ Password-Reset funktioniert?
✅ Session-Timeout konfiguriert?
✅ Brute-Force Protection?
```

**Tests:**

- [ ] Test: Unauthenticated user → 403
- [ ] Test: Tenant kann Staff-Portal nicht erreichen
- [ ] Test: Expired Magic-Link → 403
- [ ] Test: Rate-Limit überschritten → 429

---

### **3. DSGVO Compliance** 📜

**Files:**

- `landlord/api/tenants.py` (tenant_erase)
- `landlord/models.py` (Tenant, Issue, Payment)

```python
# Checklist:
✅ Tenant-Daten-Löschung implementiert? (tenant_erase)
✅ Anonymisierung statt Löschung? (Email → anonymized@...)
✅ Audit-Logs für Daten-Zugriff?
✅ Consent Management? (DSGVO-Einwilligung)
✅ Daten-Export (Portabilität)?
✅ Datenschutzerklärung vorhanden?
```

**Tests:**

- [x] Test: tenant_erase anonymisiert korrekt
- [ ] Test: Audit-Log bei Daten-Zugriff
- [ ] Test: Export aller Tenant-Daten (JSON)

**Action:**

- [ ] Prüfe tenant_erase Implementierung
- [ ] Erstelle `docs/DSGVO_COMPLIANCE_AUDIT.md`

---

### **4. API Security (DRF)** 🌐

**Files:**

- `landlord/api/*.py` (DRF Views)
- `config/settings/base.py` (REST_FRAMEWORK)

```python
# Checklist:
✅ Authentication required für alle Endpoints?
✅ Throttling konfiguriert? (AnonRateThrottle, UserRateThrottle)
✅ Permissions korrekt? (IsAdminUser, IsAuthenticated)
✅ CORS Headers korrekt? (nicht allow_all!)
✅ API Versioning?
✅ Input Validation (Serializers)?
```

**Tests:**

- [ ] Test: Unauthenticated API request → 401
- [x] Test: Throttle exceeded → 429 (bereits getestet!)
- [ ] Test: Invalid input → 400 (Serializer validation)

---

### **5. File Upload Security** 📁

**Files:**

- `landlord/models.py` (IssueAttachment, Document)
- `landlord/views_documents.py` (document_upload)

```python
# Checklist:
✅ File-Type Validation? (nur PDF, JPG, PNG)
✅ File-Size Limit? (max 10MB)
✅ Virus-Scanning? (optional, ClamAV)
✅ Storage-Path nicht guessbar? (UUID filenames)
✅ Access Control? (nur Owner kann downloaden)
✅ Content-Type Header korrekt gesetzt?
```

**Tests:**

- [ ] Test: Upload .exe file → 400 (rejected)
- [ ] Test: Upload 50MB file → 413 (too large)
- [ ] Test: Tenant A kann Tenant B's File nicht downloaden

**Action:**

- [ ] Prüfe File-Validation in views_documents.py
- [ ] Teste Upload-Security

---

### **6. Session Management** 🍪

**Files:**

- `config/settings/base.py` (SESSION\_\*)
- `landlord/views.py` (Magic-Link Session)

```python
# Checklist:
✅ Session Backend = Redis? (scalable)
✅ SESSION_COOKIE_AGE sinnvoll? (2 Wochen)
✅ SESSION_EXPIRE_AT_BROWSER_CLOSE?
✅ Session Fixation Protection?
✅ CSRF Protection aktiv?
```

**Tests:**

- [ ] Test: Session expired → Login required
- [ ] Test: CSRF Token missing → 403

---

### **7. SQL Injection Prevention** 💉

**Files:** Alle Files mit DB-Queries

```python
# Checklist:
✅ Keine Raw SQL queries?
✅ Wenn Raw SQL: Parameterized queries?
✅ Django ORM korrekt verwendet?
✅ .extra() vermieden?
```

**Scan:**

```bash
# Suche nach gefährlichen Patterns:
grep -r "cursor.execute" backend/app/landlord/
grep -r ".raw(" backend/app/landlord/
grep -r ".extra(" backend/app/landlord/
```

**Expected:** Keine Treffer! (Django ORM only)

---

### **8. XSS Prevention** 🕷️

**Files:** Alle Templates (`templates/`)

```python
# Checklist:
✅ Auto-Escaping aktiv? (Django default)
✅ Keine {{ var|safe }} ohne Grund?
✅ JavaScript in Templates escaped?
✅ User-Input niemals unescaped?
```

**Scan:**

```bash
# Suche nach |safe usage:
grep -r "|safe" backend/app/templates/
```

**Action:**

- [ ] Prüfe jeden |safe Treffer
- [ ] Rechtfertige oder entferne

---

### **9. Password Security** 🔑

**Files:**

- `config/settings/base.py` (PASSWORD_HASHERS)
- User-Model (Django default)

```python
# Checklist:
✅ PBKDF2 oder Argon2 als Hasher?
✅ Min. Password Length = 8?
✅ Password Complexity Rules?
✅ Password History (keine Wiederholung)?
```

**Django Default:** ✅ Gut (PBKDF2 with SHA256)

---

### **10. Celery Task Security** ⚙️

**Files:**

- `landlord/tasks.py` (Celery Tasks)
- `config/celery_app.py`

```python
# Checklist:
✅ Tasks validieren Input?
✅ Retry-Logic sicher? (kein infinite loop)
✅ Task-Results nicht sensibel? (PII logged?)
✅ Celery-Backend sicher? (Redis password?)
```

**Tests:**

- [ ] Test: Task mit invalid input → logged error, nicht crashed

---

## 🚀 MONITORING & LOGGING SETUP:

### **Task: Setup Sentry.io (Error Tracking)**

**File:** `config/settings/prod.py`

```python
# 1. Install:
pip install sentry-sdk

# 2. Configure:
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # 10% Performance Monitoring
    send_default_pii=False,  # DSGVO!
    environment="production",
)
```

**Tests:**

- [ ] Test: Exception wird zu Sentry gesendet
- [ ] Test: PII wird NICHT geloggt

---

### **Task: Audit Logging**

**File:** `landlord/middleware.py` (neu erstellen)

```python
# Log alle Admin-Aktionen:
- Tenant created/updated/deleted
- Document accessed
- Payment modified
- Issue status changed

# Format:
{
  "timestamp": "2025-10-22T10:30:00Z",
  "user": "admin@example.com",
  "action": "tenant_deleted",
  "object_id": 123,
  "ip_address": "192.168.1.1"
}
```

**Storage:** PostgreSQL Table `AuditLog`

---

## 📊 FINALE DELIVERABLES:

1. **`docs/SECURITY_SETTINGS_AUDIT.md`**
2. **`docs/DSGVO_COMPLIANCE_AUDIT.md`**
3. **`docs/MONITORING_SETUP.md`** (Sentry + Logging)
4. **`docs/SECURITY_AUDIT_SUMMARY.md`** (Executive Summary)

---

## 🎯 ERFOLGSKRITERIEN:

✅ **Keine Critical Security Issues**
✅ **DSGVO-orientierte Controls geprüft** (Tenant-Löschung, Audit-Logs)
✅ **Monitoring vorbereitet** (Sentry.io)
✅ **Alle Tests grün** (Security-Tests hinzugefügt)
✅ **Dokumentation vollständig**

**Dann:** bereit für manuelle Security-/Privacy-Prüfung.

---

**WICHTIG:** Diese Arbeit muss **ICH (Copilot Chat)** machen - Codex hat nicht den Business-Kontext!
