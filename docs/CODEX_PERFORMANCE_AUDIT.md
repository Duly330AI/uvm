# 🚀 Codex Performance Audit - UVM Project

**Datum:** 2025-10-22  
**Projekt:** Universal Vermieter Management (UVM)  
**Status:** 44% fertig (M1-M16 done)  
**Tech-Stack:** Django 5.1, Python 3.12, PostgreSQL 16, Redis 7, Celery

---

## 🎯 DEINE AUFGABE (Codex):

Führe ein **automatisiertes Performance & Code-Quality Audit** durch für das UVM-Projekt.

**Ziel:** Produktionsreife erreichen für Exit (Verkauf an PropTech-Firma)

---

## 📋 TASKS (in dieser Reihenfolge):

### **TASK 1: Dependency Security Scan** 🔒

**Was:**
- Prüfe alle Dependencies auf bekannte Sicherheitslücken
- Finde veraltete Packages
- Empfehle Updates

**Wie:**
```bash
# In Docker-Container ausführen:
docker compose exec web pip install safety pip-audit
docker compose exec web safety check --json > docs/safety_report.json
docker compose exec web pip-audit --format json > docs/pip_audit_report.json

# Dann analysiere die Reports und erstelle:
docs/DEPENDENCY_AUDIT_RESULTS.md
```

**Output Format:**
```markdown
# Dependency Audit Results

## 🔴 CRITICAL (fix sofort):
- package==version: CVE-XXXX - Beschreibung - Fix: upgrade to X.Y.Z

## 🟡 MEDIUM (fix vor Exit):
- package==version: Issue - Fix

## 🟢 LOW (optional):
- package==version: Minor issue
```

---

### **TASK 2: Database Query Optimization** ⚡

**Was:**
- Finde N+1 Query-Probleme
- Identifiziere fehlende Indexes
- Prüfe select_related/prefetch_related Nutzung

**Wie:**
```python
# Analysiere folgende Files:
backend/app/landlord/views.py
backend/app/landlord/views_portal.py
backend/app/landlord/views_tenant.py
backend/app/landlord/api/*.py

# Suche nach Patterns:
- .all() ohne select_related()
- Loops mit ORM-Queries (N+1)
- QuerySet.count() statt .exists()
- Missing indexes in models.py
```

**Output Format:**
```markdown
# Database Query Optimization Report

## 🔴 N+1 Queries gefunden:
### File: views_portal.py:74
**Problem:**
```python
for issue in Issue.objects.all():  # N queries!
    print(issue.tenant.name)
```
**Fix:**
```python
for issue in Issue.objects.select_related('tenant').all():
    print(issue.tenant.name)
```

## 🟡 Missing Indexes:
### Model: Issue
- Empfehle Index auf: ['status', 'created_at'] (häufig gefiltert)

## ✅ Gut gemacht:
- views_utility.py:193 - korrekt prefetch_related('readings')
```

---

### **TASK 3: Code Complexity Analysis** 📊

**Was:**
- Finde zu komplexe Funktionen (>15 Zeilen, >3 Nested Loops)
- Identifiziere Duplikate (Copy-Paste-Code)
- Prüfe Code-Style Violations

**Tools:**
```bash
docker compose exec web pip install radon mccabe
docker compose exec web radon cc backend/app/landlord -a -s > docs/complexity_report.txt
docker compose exec web radon mi backend/app/landlord > docs/maintainability_report.txt
```

**Output Format:**
```markdown
# Code Complexity Report

## 🔴 Zu komplex (Refactoring empfohlen):
### landlord/views.py:191-220 (Complexity: 12)
**Problem:** Nested if-statements, zu viele Branches
**Empfehlung:** Extrahiere zu `landlord/services/chat_validation.py`

## 🟡 Duplikate gefunden:
### views_portal.py:127 vs views_tenant.py:67
**Duplikat:** Appointment.send_invite() Logic
**Empfehlung:** Extrahiere zu `services/appointments.py`
```

---

### **TASK 4: Test Coverage Gaps** 🧪

**Was:**
- Finde ungetestete Funktionen
- Identifiziere kritische Paths ohne Tests
- Empfehle neue Tests

**Wie:**
```bash
docker compose exec web pytest --cov=landlord --cov-report=json > docs/coverage.json
# Dann analysiere coverage.json und finde <80% Coverage
```

**Output Format:**
```markdown
# Test Coverage Gaps

## 🔴 Kritische Funktionen ohne Tests:
### landlord/services/utility_calculator.py
- `calculate_heating_costs()` - 0% Coverage ❌
- **Risiko:** HeizkostenV-Compliance!
- **Empfehlung:** Schreibe `test_heating_costs_calculation.py`

## 🟡 Views mit <50% Coverage:
### views_documents.py:247-280
- Document version comparison - 30% Coverage
```

---

### **TASK 5: Django Best Practices Check** ✅

**Was:**
- Prüfe Django-Conventions
- Finde anti-patterns
- Security-Issues (XSS, CSRF, SQL-Injection)

**Prüf-Liste:**
```python
# 1. Models:
- Fehlende __str__ methods?
- Fehlende Meta.ordering?
- Fehlende verbose_name?

# 2. Views:
- Missing @staff_member_required?
- Raw SQL queries? (SQL-Injection Risk!)
- Fehlende CSRF-Protection?

# 3. Templates:
- Unescaped variables {{ var|safe }}? (XSS Risk!)
- Hardcoded URLs statt {% url %}?

# 4. Settings:
- DEBUG = True in prod? ❌
- SECRET_KEY exposed? ❌
- ALLOWED_HOSTS = ['*']? ❌
```

**Output Format:**
```markdown
# Django Best Practices Report

## 🔴 Security Issues:
### views_portal.py:156
**Problem:** Raw SQL query ohne Escaping
```python
cursor.execute(f"SELECT * FROM tenant WHERE name = '{user_input}'")  # ❌
```
**Fix:** Use Django ORM or parameterized queries

## 🟡 Missing Decorators:
### views_documents.py:82
**Problem:** Keine Auth-Check für file download
**Fix:** Add `@staff_member_required`
```

---

### **TASK 6: Performance Bottlenecks** 🐌

**Was:**
- Finde langsame Operationen
- Identifiziere Caching-Opportunities
- Prüfe Celery-Task-Performance

**Analysiere:**
```python
# 1. Views mit >100ms Response Time
# 2. Celery Tasks mit >5s Execution Time
# 3. Template Rendering >50ms
# 4. File-Uploads ohne Streaming
# 5. Fehlende Pagination bei großen QuerySets
```

**Output Format:**
```markdown
# Performance Bottlenecks

## 🔴 Slow Views (>500ms):
### portal/property_list (782ms avg)
**Grund:** Lädt alle Properties ohne Pagination
**Fix:** Add PageNumberPagination(page_size=50)

## 🟡 Caching Opportunities:
### Template: portal/base.html
**Problem:** User-Menü wird bei jedem Request gerendert
**Fix:** Template-Fragment Caching (10min TTL)
```

---

## 📊 FINALE ZUSAMMENFASSUNG:

Erstelle am Ende eine **Executive Summary**:

```markdown
# UVM Performance Audit - Executive Summary

**Audit Datum:** 2025-10-22  
**Geprüfte Codebase:** 37.25h Entwicklungszeit, ~10.000 LOC

## 🎯 OVERALL SCORE: X/100

### 🔴 CRITICAL (fix vor Exit):
1. Issue #1 - Beschreibung (Impact: High, Effort: Medium)
2. Issue #2 - ...

### 🟡 MEDIUM (fix empfohlen):
1. ...

### 🟢 LOW (optional):
1. ...

## 📈 METRIKEN:
- **Security Issues:** X critical, Y medium
- **Performance Issues:** X slow queries, Y missing indexes
- **Code Quality:** X complex functions, Y duplicates
- **Test Coverage:** X% (Target: 80%)

## ✅ POSITIVE:
- Was ist gut gemacht? (Clean Code, Tests, Patterns)

## 🚀 NÄCHSTE SCHRITTE:
1. Fix Critical Issues (Est. Xh)
2. Performance Optimization (Est. Yh)
3. Test Coverage auf 80% (Est. Zh)

**Estimated Total Effort:** ~Xh bis Production-Ready
```

---

## 🎯 WICHTIGE HINWEISE:

### **SCOPE:**
- ✅ **Analysiere nur:** `backend/app/landlord/` und `backend/app/config/`
- ✅ **Ignoriere:** `migrations/`, `__pycache__/`, `htmlcov/`, `tests/` (außer Coverage-Check)
- ✅ **Fokus:** Performance, Security, Code-Quality (NICHT Business-Logic!)

### **OUTPUT:**
- ✅ Erstelle **6 separate Reports** (eine pro Task)
- ✅ **Executive Summary** am Ende
- ✅ Alle Reports in `docs/` speichern
- ✅ **Actionable** (konkrete Fixes, keine Theory!)

### **STYLE:**
- ✅ **Markdown** Format
- ✅ **Code-Snippets** mit Syntax Highlighting
- ✅ **Priorisierung:** 🔴 Critical, 🟡 Medium, 🟢 Low
- ✅ **Geschätzte Aufwände** pro Fix (Xh)

---

## 🚀 START-COMMAND:

```bash
# 1. Stelle sicher, dass Docker läuft
docker compose up -d

# 2. Installiere Audit-Tools
docker compose exec web pip install safety pip-audit radon mccabe

# 3. Starte mit TASK 1
# (Dann der Reihe nach TASK 2-6)
```

---

**VIEL ERFOLG, CODEX!** 🤖

*PS: Bei Fragen zu Business-Logic oder Django-Patterns, frag Copilot Chat!*
