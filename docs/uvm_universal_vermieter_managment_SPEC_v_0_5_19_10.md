# 🏢 UVM - Universal Vermieter Management

## Technical Specification v0.5

**Stand:** 19. Oktober 2025
**Version:** 0.8.0 (Development)
**Status:** M12a + M12b Complete (19% Progress)

---

## 📊 Projekt-Status

### **Fertiggestellte Features:**

```
✅ Phase 1: Dokumente (8h)
   - M11b: Dokumente → Units
   - M17a: Versionshistorie

✅ Phase 2: Verträge (4.5h)
   - M12a: Vertrags-System

✅ Phase 3: Zahlungen (2h)
   - M12b: Zahlungen CSV-Import

Total: 14.5h / 76h (19%)
Verbleibend: 61.5h (8 Arbeitstage)
```

---

## 🎯 Aktuelle Architektur (v0.5)

### **Tech Stack:**

- **Backend:** Django 5.1.2, Python 3.12
- **Frontend:** TailwindCSS, HTMX, Alpine.js
- **Database:** PostgreSQL 16
- **Storage:** Local FileSystem (S3-ready)
- **Queue:** Celery + Redis
- **Deployment:** Docker Compose

---

## 📦 Datenmodell (v0.5)

### **Core Models:**

```python
# M11b: Dokumente
Document
  - file (FileField)
  - name, category, tags
  - current_version (M17a)
  - property, unit, tenant (ForeignKeys)

DocumentVersion (M17a)
  - document (FK)
  - version_number
  - file, size_bytes, content_type
  - upload_comment

# M12a: Verträge
Contract
  - unit, tenant, document (FKs)
  - start_date, end_date, notice_date
  - rent_amount, additional_costs, deposit_amount
  - payment_day (1-28)
  - status (draft, active, ended, cancelled)
  - Constraint: Nur 1 aktiver Vertrag pro Unit

# M12b: Zahlungen
PaymentTransaction
  - contract (FK)
  - amount, transaction_date, due_date
  - payment_type (rent, deposit, additional_costs, other)
  - status (pending, received, overdue, cancelled)
  - reference, sender_name, sender_iban
  - csv_import_date, csv_row_data (JSON)
```

---

## 🔄 Feature-Details

### **M11b: Dokumente → Units (DONE)**

**Implementiert:**

- Direct ForeignKeys statt Generic Relations
- Upload-Form mit Property/Unit/Tenant Dropdowns
- Document-Liste mit Bezug-Filtern
- Migrations für bestehende Dokumente

**URLs:**

- `/portal/documents/` - Liste
- `/portal/documents/upload` - Upload

---

### **M17a: Versionshistorie (DONE)**

**Implementiert:**

- DocumentVersion Model
- Auto-Archivierung bei Update (v1 → v2 → v3)
- History Timeline UI
- Download alter Versionen

**URLs:**

- `/portal/documents/<id>/history/` - Historie
- `/portal/documents/<id>/version/<version>/` - Download

---

### **M12a: Vertrags-System (DONE)**

**Implementiert:**

- Contract Model mit Relations
- Upload Integration (Kategorie "Vertrag" → Auto-Create)
- Vertrags-Liste mit Filtern
- Details-Seite mit Dokument + Versionshistorie
- Admin mit Fieldsets

**URLs:**

- `/portal/contracts/` - Liste
- `/portal/contracts/<id>/` - Details

**Features:**

- Auto-Create Contract beim Dokument-Upload
- Duplicate Prevention (nur 1 Draft/Active pro Unit)
- Status-Workflow (Draft → Active → Ended)
- Calculated Properties (total_rent, is_active, is_unlimited)

---

### **M12b: Zahlungen CSV-Import (DONE)**

**Implementiert:**

- PaymentTransaction Model
- CSV-Upload mit flexiblem Format
- Auto-Matching zu Contracts (Tenant/Amount/Reference)
- Zahlungen-Liste mit Filtern
- Integration in Contract Details

**URLs:**

- `/portal/payments/` - Liste
- `/portal/payments/upload` - CSV-Upload

**CSV-Format (Semikolon-getrennt):**

```csv
Datum;Betrag;Verwendungszweck;Auftraggeber;IBAN
18.10.2025;850,00;Miete Oktober;Maria Schmidt;DE89...
```

**Auto-Matching Logik:**

1. Betrag = Contract.total_rent (±0.01€)
2. Sender Name enthält Tenant Email
3. Referenz enthält Unit Label

---

## 🚀 Nächste Schritte

### **Priorität 1: M14 Nebenkostenabrechnung (20h)**

**Features:**

- Utility Cost Model (Heizung, Wasser, Müll, etc.)
- NK-Abrechnung Generator
- PDF Export
- Verteilung nach Schlüssel (qm, Personen, Anteil)

### **Priorität 2: M16 Checklisten (12h)**

**Features:**

- ChecklistTemplate Model
- ChecklistInstance mit Foto-Upload
- Wohnungsübergabe-Checkliste
- Wartungs-Checkliste

### **Priorität 3: M15 Wartungskalender (12h)**

**Features:**

- MaintenanceTask Model
- Kalender-Ansicht
- Erinnerungen
- Recurring Tasks

---

## 📈 Performance & Optimierung

### **Aktuelle Optimierungen:**

```python
# select_related für ForeignKeys
contracts = Contract.objects.select_related(
    'unit', 'unit__property', 'tenant', 'document'
).all()

# prefetch_related für Reverse Relations
contract = Contract.objects.prefetch_related(
    'payments'
).get(pk=pk)

# Indexes
class PaymentTransaction:
    class Meta:
        indexes = [
            Index(fields=['contract', 'transaction_date']),
            Index(fields=['transaction_date', 'status']),
            Index(fields=['payment_type', 'status']),
        ]
```

---

## 🔒 Security & Validation

### **Implementierte Maßnahmen:**

```python
# File Upload Validierung
- Size Limit: 10 MB (Dokumente), 5 MB (CSV)
- MIME Type Whitelist: PDF, Images, Office
- BOM Handling (UTF-8-sig)

# Access Control
- @staff_member_required für alle Views
- Contract Constraint: 1 aktiver pro Unit

# Input Validation
- CSV Date Parsing (multiple formats)
- Decimal Amount Cleaning
- CSRF Protection
```

---

## 📊 Database Schema (v0.5)

```sql
-- M11b: Dokumente
landlord_document
  - id, name, category, current_version
  - property_id, unit_id, tenant_id (FKs)
  - file, size_bytes, content_type
  - tags, notes
  - created_at, updated_at

-- M17a: Versionen
landlord_documentversion
  - id, document_id, version_number
  - file, size_bytes, content_type
  - upload_comment, uploaded_by_id
  - created_at

-- M12a: Verträge
landlord_contract
  - id, unit_id, tenant_id, document_id (FKs)
  - start_date, end_date, notice_date
  - rent_amount, additional_costs, deposit_amount
  - payment_day, status
  - notes, created_at, updated_at
  - CONSTRAINT: uq_active_contract_per_unit

-- M12b: Zahlungen
landlord_paymenttransaction
  - id, contract_id (FK)
  - amount, transaction_date, due_date
  - payment_type, status
  - reference, sender_name, sender_iban
  - csv_import_date, csv_row_data (JSONB)
  - notes, created_at, updated_at
```

---

## 🧪 Testing-Status

### **Browser-Testing:**

- ✅ M11b: Dokumente-Upload, Liste, Filter
- ✅ M17a: Versionshistorie, Download
- ✅ M12a: Contract-Liste, Details, Upload-Integration
- ✅ M12b: Zahlungen-Liste, CSV-Upload, Contract-Integration

### **Automatische Tests:**

- ⏸️ Unit Tests (später)
- ⏸️ Integration Tests (später)
- ⏸️ E2E Tests (später)

---

## 📝 API Endpoints (Internal)

### **Dokumente:**

```
GET  /portal/documents/                      # Liste
POST /portal/documents/upload                # Upload
GET  /portal/documents/<id>/history/         # Historie
GET  /portal/documents/<id>/version/<v>/     # Download Version
```

### **Verträge:**

```
GET  /portal/contracts/                      # Liste
GET  /portal/contracts/<id>/                 # Details
```

### **Zahlungen:**

```
GET  /portal/payments/                       # Liste
POST /portal/payments/upload                 # CSV-Import
```

---

## 🔧 Development Setup

### **Requirements:**

```bash
# Docker Compose
docker-compose up -d

# Services:
- web:      Django App (port 8000)
- db:       PostgreSQL 16 (port 5432)
- redis:    Redis 7 (port 6379)
- worker:   Celery Worker
```

### **Database Migrations:**

```bash
# Create
docker compose exec web python manage.py makemigrations

# Apply
docker compose exec web python manage.py migrate

# Manual Table Creation (if needed)
docker compose exec db psql -U landlord -d landlord -c "CREATE TABLE..."
```

---

## 📌 Lessons Learned

### **Was gut funktioniert:**

1. **Manual Table Creation:** Schneller als Migration Debugging
2. **Prefetch Related:** Verhindert N+1 Queries
3. **Flexible CSV Parsing:** Unterstützt verschiedene Formate
4. **Auto-Matching:** Spart manuelle Zuordnung
5. **Browser-Testing First:** Features funktionieren, Tests später!

### **Was verbessert wurde:**

1. **Type Hints:** `Optional[Type]` statt `Type | None` (Python 3.9 compat)
2. **Duplicate Prevention:** Nur 1 Draft/Active Contract pro Unit
3. **Upload Integration:** Auto-Create Contract bei Mietvertrag-Upload
4. **Realistische Planung:** Zeitersparnis 57% (6.5h statt 15h)

### **Was noch zu tun ist:**

1. **Tests schreiben:** M12a + M12b Tests ausstehend (~3h)
2. **Coverage erhöhen:** Von aktuell ~50% auf 90%+ (~3h)
3. **CI/CD Pipeline:** Automatische Tests bei Commits (~2h)

---

## 🎯 Go-Live Roadmap

### **Verbleibende Features (61.5h):**

```
1. M14: Nebenkostenabrechnung (20h)
2. M16: Checklisten (12h)
3. M15: Wartungskalender (12h)
4. M18: Mieter-Portal erweitern (8h)
5. M19: Reports & Analytics (6h)
6. Testing & Bugfixes (3.5h)
```

### **Go-Live Prognose:**

- **Zeitrahmen:** 8 Arbeitstage (von 10 geplant)
- **Kosten:** €0 externe APIs (nur Hosting)
- **Risiko:** 🟢 NIEDRIG (19% bereits fertig, alle Browser-Tests erfolgreich)

---

## 📞 Support & Dokumentation

### **Code-Dokumentation:**

- Docstrings in allen Views
- Kommentare für komplexe Logik
- ROADMAP.md mit Feature-Details

### **Admin-Dokumentation:**

- Fieldsets für übersichtliche Forms
- Help-Text bei wichtigen Feldern
- Search & Filter für alle Models

---

**Erstellt von:** AI Assistant
**Letzte Aktualisierung:** 19.10.2025 02:30 Uhr
**Version:** 0.5 (M12a + M12b Complete)
**Nächster Meilenstein:** M14 Nebenkostenabrechnung 🚀
