# Vermieter‑App – Technische Spezifikation v0.4

# "UVM" Universal Vermieter Management v0.4

**Datum:** 18.10.2025
**Autor:** ChatGPT (Assistenz für Matthias Buchalik)
**Zielgruppe:** Product Owner, Entwicklung, QA, DevOps
**Status:** Implementiert & Testbereit (M1-M10 + PR1-PR2)

---

## 1. Executive Summary

Eine Web‑Anwendung für Vermieter mit ~10 Wohneinheiten (erweiterbar), in der Mieter Störungen/Anliegen über eine dialogorientierte Chat-Oberfläche melden können. Die Eingaben werden strukturiert gespeichert und können im modernen Vermieter-Portal (Staff-only) sowie im Django-Admin verwaltet werden. Fokus auf **deterministisch geführte Datenerhebung** (FSM-basiert), **mobil-optimierte UI**, **Docker‑basierte Bereitstellung** und **GDPR‑konforme** Verarbeitung.

**Neue Features in v0.4:**

- ✅ Vendor-Management mit Auth-Tokens (M10)
- ✅ Mieter-Verwaltung (CRUD) mit Card-Layout (PR2 Phase 1)
- ✅ Tenant-Authentifizierung & Chat-Security (PR2 Phase 2)
- ✅ Willkommens-E-Mail für neue Mieter
- ✅ Dokumenten-Management (M9)
- ✅ Reports & KPI-Dashboard (M9)

---

## 2. Was ist implementiert (M1-M10 + PR1-2)

### M1-M5: Kern-Backend & Admin-API

✅ **Models & Migrations**

- Property, Unit, Tenant, Issue, IssueNote, IssueAttachment, Appointment, Vendor, ChatSession
- Ticket-Sequenz mit race-condition-safe Counter
- Idempotency-Key für Confirm-Endpoint

✅ **Chat FSM (Finite State Machine)**

- Deterministischer Dialog-Flow: GREETING → CAPTURE_SUMMARY → CAPTURE_OCCURRED_AT → CAPTURE_LOCATION → CAPTURE_SEVERITY → CAPTURE_MEDIA → CAPTURE_CONTACT → CONFIRM
- Version-basierte Optimistic Locking für concurrent Updates
- Datei-Upload mit Size/MIME-Type Validation
- Session-Expiry (30min)

✅ **REST API Endpoints**

- `POST /api/chat/sessions/` - Session erstellen
- `POST /api/chat/sessions/<id>/message` - FSM-Step mit Payload
- `POST /api/chat/sessions/<id>/confirm` - Issue finalisieren & Ticket-Nummer vergeben
- `GET /api/admin/issues/` - Issues-Liste mit Filter/Ordering/Pagination
- `POST /api/admin/issues/export/csv` - CSV-Export mit Sanitization
- `POST /api/admin/tenants/<id>/export` - GDPR Export (JSON)
- `POST /api/admin/tenants/<id>/erase` - GDPR Erase (idempotent)

✅ **Background Tasks (Celery)**

- `send_issue_created` - Email an Tenant mit Status-Link
- `send_status_changed` - Statuswechsel-Benachrichtigung
- `send_appointment_invite` - ICS-Datei für Termin
- `send_tenant_magic_link` - Magic-Link für Tenant-Login
- `send_tenant_welcome` - Willkommens-E-Mail für neue Mieter

✅ **Rate Limiting & Security**

- Throttle: Session+IP für Chat-Endpoints (20/min)
- Admin-APIs: IsAdminUser Permission
- CSRF-Protection aktiv
- CSV-Injection-Mitigation

### M6: Mieter-Chat UI & Öffentliche Statusseite

✅ **Mobiles Chat-UI** (`/chat/`)

- Tailwind CSS, HTMX-kompatibel
- Bubble-Konversation (Bot/User)
- Dynamische Eingabefelder je nach FSM-State
- Toast-Benachrichtigungen
- Datei-Upload funktioniert
- Status-Link nach Bestätigung
- **NEU:** Nur für authentifizierte Tenants (Redirect zu `/tenant/` wenn nicht eingeloggt)

✅ **Öffentliche Ticket-Statusseite** (`/t/<token>/`)

- Signierte Token (ohne Migration, `django.core.signing`)
- Read-only View: Ticket-Details, Termine, Mieter-Hinweise
- Responsive Design

### M7: Vermieter-Portal (Staff-only Web-UI)

✅ **Dashboard** (`/portal/`)

- Anzahl offener Tickets
- Neueste 10 Tickets
- Navigation: Dashboard | Tickets | Dokumente | Reports | **Mieter** | Admin

✅ **Tickets-Liste** (`/portal/issues/`)

- Filter: Status, Objekt, Suche (Ticket/Betreff)
- 🔥 Dringend-Filter (Severity ≥4)
- Pagination (20 pro Seite)
- Klickbare Zeilen → Detail

✅ **Ticket-Detail** (`/portal/issues/<id>/`)

- Status ändern (HTMX, ohne Page-Reload)
- Notizen hinzufügen (intern/öffentlich) mit Autor-Anzeige
- Vendor zuweisen → automatischer Termin
- Termine manuell anlegen
- Farbcodierte Status-Badges

### M9: Dokumenten-Management & Reports (NEU)

✅ **Dokumenten-Speicher** (`/portal/documents/`)

- Upload von PDFs, Bildern
- Kategorien: lease (Mietverträge), invoice (Rechnungen), protocol (Protokolle), certificate (Bescheinigungen), other
- Max 10MB/Datei, 40MB gesamt
- Download & Bulk-Delete

✅ **Reports & KPIs** (`/portal/reports/`)

- SLA-Tracking (First Response, Resolution Time)
- SLA-Verstöße (>24h ohne Reaktion)
- Reaktionszeit nach Kategorie
- Lösungszeit nach Priorität
- CSV-Export für alle KPIs

### M10: Vendor-Management (PR 1)

✅ **Vendor Model**

- Name, Trade (Handwerkstyp), Kontakt (E-Mail, Telefon)
- Notizen, is_active Flag
- Auth-Token für Vendor-Portal (UUID, expires_at)

✅ **Vendor Admin**

- Django Admin Integration
- Token-Generierung per Button
- Token-Link in Admin-View

✅ **Tests**

- 20 Tests passed (pytest)
- Vendor Token Generation
- Vendor Assignment Workflow

### PR2 Phase 1: Mieter-Verwaltung (NEU)

✅ **Mieter-Liste** (`/portal/tenants/`)

- **Card-Based Layout** (statt Tabelle)
- Gruppierte Infos: Kontakt, Wohnung, Eingezogen, Status
- Icons für Aktionen (Bearbeiten, Deaktivieren, Löschen)
- Responsive Design (Mobile-ready)

✅ **Mieter CRUD**

- **Create** (`/portal/tenants/new`): Unit, E-Mail, Telefon, Einzugsdatum
- **Edit** (`/portal/tenants/<id>/edit`): Alle Felder editierbar
- **Deactivate** (Soft Delete): `is_active=False`, `moved_out_at` setzen
- **Delete** (Hard Delete): Nur wenn keine Tickets vorhanden

✅ **Willkommens-E-Mail**

- Checkbox beim Anlegen: "Willkommens-E-Mail senden"
- Task `send_tenant_welcome` mit Magic-Link
- Tenant kann Portal aktivieren

### PR2 Phase 2: Tenant-Authentifizierung (NEU)

✅ **Auth Module** (`landlord/auth.py`)

- `@tenant_login_required` Decorator
- `get_tenant_from_session(request)` Utility
- Session-basierte Authentifizierung

✅ **Chat Security**

- Chat-Zugriff nur für eingeloggte Tenants
- Redirect zu `/tenant/` wenn nicht authentifiziert
- **WICHTIG:** Login-Seite (`/tenant/`) bleibt öffentlich!

✅ **Tenant-Portal** (`/tenant/`)

- Magic-Link Login (15min, single-use)
- Rate-Limiting: Max 3 Links pro 30min pro E-Mail
- Ticket-Historie (`/tenant/issues/`)
- Ticket-Details (`/tenant/issues/<id>/`)

✅ **Issue-Tenant Assignment**

- Chat erstellt Issues mit `tenant=request.tenant`
- Service `confirm()` akzeptiert Tenant-Parameter
- Tickets sind Tenant zugeordnet ✅

---

## 3. Technischer Stack (wie implementiert)

### Backend

- **Django 5.1** (Python 3.12)
- **Django REST Framework** (API)
- **PostgreSQL 16** (Datenbank)
- **Redis** (Cache, Celery Broker)
- **Celery** (Background Tasks)

### Frontend

- **Tailwind CSS 3** (Styling)
- **HTMX 1.9** (Interaktivität ohne JS-Framework)
- **Alpine.js** (Leichte Client-Interaktionen)
- **Django Templates** (Server-side Rendering)

### Infrastructure

- **Docker Compose** (Local Dev)
- **Gunicorn** (WSGI Server)
- **WhiteNoise** (Static Files)
- **Mailhog** (E-Mail Testing, Dev)

---

## 4. Architektur-Übersicht

### Request Flow (Mieter-Chat)

```
Browser → Nginx/Gunicorn → Django View
  ↓
ChatPageView (protected by tenant_login_required)
  ↓
POST /api/chat/sessions/<id>/message
  ↓
FSM State Machine
  ↓
Celery Task (Email)
  ↓
PostgreSQL + Redis
```

### Request Flow (Vermieter-Portal)

```
Browser → Django View (@staff_member_required)
  ↓
Portal Dashboard/Issues/Tenants
  ↓
HTMX Partials (Status-Update, Notes)
  ↓
PostgreSQL
```

### Authentication Flows

**Tenant (Mieter):**

```
1. GET /tenant/ → Login-Seite
2. POST /tenant/request-link → send_tenant_magic_link Task
3. GET /tenant/magic/<token>/ → Session erstellt
4. Redirect to /tenant/issues/ (eingeloggt)
5. GET /chat/ → Chat zugänglich ✅
```

**Staff (Vermieter):**

```
1. GET /admin/login/ → Django Admin Login
2. Username + Password
3. GET /portal/ → Dashboard ✅
```

**Vendor (Handwerker):**

```
1. Admin generiert Token
2. GET /vendor/auth/<token>/ → Session erstellt
3. Redirect to /vendor/issues/ (geplant für M11)
```

---

## 5. Datenmodell (erweitert)

### Tenant (Mieter)

- `unit` (FK to Unit)
- `primary_email` (EmailField, unique per unit)
- `phone` (optional)
- `moved_in_at` (DateField, optional)
- `moved_out_at` (DateTimeField, optional) - **NEU**
- `is_active` (Boolean, default=True)

### TenantAuthToken

- `id` (UUID, primary key)
- `tenant` (FK to Tenant, **nullable**) - **FIX in v0.4**
- `email` (EmailField, indexed)
- `expires_at` (DateTimeField)
- `used_at` (DateTimeField, nullable)
- `ip_hash`, `ua_hash` (Privacy)

### Issue

- `tenant` (FK to Tenant, **nullable** → wird durch Chat gesetzt)
- `unit` (FK to Unit)
- `category`, `severity`, `status`
- `summary`, `description_struct` (JSON)
- `ticket_no` (unique, generated)
- `occurred_at`, `created_at`
- `created_via` (chat/portal/api)

### Vendor (NEU in M10)

- `name`, `trade` (Handwerkstyp)
- `email`, `phone`
- `notes` (TextField)
- `is_active` (Boolean)
- `auth_token` (UUID, nullable)
- `token_expires_at` (DateTimeField, nullable)

### Document (NEU in M9)

- `category` (lease/invoice/protocol/certificate/other)
- `file` (FileField)
- `uploaded_by` (FK to User)
- `uploaded_at` (DateTimeField)

---

## 6. API Endpoints (Übersicht)

### Public (Tenant)

- `GET /tenant/` - Login-Seite
- `POST /tenant/request-link` - Magic-Link anfordern
- `GET /tenant/magic/<token>/` - Magic-Link validieren & Login
- `GET /tenant/issues/` - Eigene Tickets (authenticated)
- `GET /tenant/issues/<id>/` - Ticket-Details (authenticated)
- `GET /t/<token>/` - Öffentlicher Ticket-Status (signierter Token)

### Chat (Authenticated Tenant)

- `GET /chat/` - Chat-UI (tenant_login_required)
- `POST /api/chat/sessions/` - Session erstellen
- `POST /api/chat/sessions/<id>/message` - Message senden
- `POST /api/chat/sessions/<id>/confirm` - Ticket finalisieren

### Portal (Staff)

- `GET /portal/` - Dashboard
- `GET /portal/issues/` - Tickets-Liste
- `GET /portal/issues/<id>/` - Ticket-Detail
- `POST /portal/issues/<id>/status` - Status ändern
- `POST /portal/issues/<id>/notes` - Notiz hinzufügen
- `GET /portal/documents/` - Dokumenten-Liste
- `POST /portal/documents/upload` - Dokument hochladen
- `GET /portal/reports/` - KPI-Dashboard
- `GET /portal/reports/export` - CSV-Export
- `GET /portal/tenants/` - Mieter-Liste (NEU)
- `GET /portal/tenants/new` - Mieter anlegen (NEU)
- `GET /portal/tenants/<id>/edit` - Mieter bearbeiten (NEU)
- `POST /portal/tenants/<id>/deactivate` - Mieter deaktivieren (NEU)
- `DELETE /portal/tenants/<id>/delete` - Mieter löschen (NEU)

### Admin (Django)

- `GET /admin/` - Django Admin Interface
- Vendor Token-Generierung

---

## 7. Deployment

### Lokales Dev-Setup

```bash
# 1. Container starten
docker compose up -d

# 2. Migrations
docker compose exec web python manage.py migrate

# 3. Superuser
docker compose exec web python manage.py createsuperuser

# 4. Testdaten (optional)
docker compose exec web python manage.py shell -c "
from landlord.models import Property, Unit, Tenant
from datetime import date

prop = Property.objects.create(name='Demo Objekt', address='Teststr. 1')
Unit.objects.bulk_create([
    Unit(property=prop, unit_label='A', floor='1. OG', rooms=3),
    Unit(property=prop, unit_label='B', floor='1. OG', rooms=2),
    Unit(property=prop, unit_label='C', floor='2. OG', rooms=3),
])
print('✓ Testdaten erstellt')
"

# URLs:
# - Chat: http://localhost:8000/chat/ (erfordert Login)
# - Tenant Login: http://localhost:8000/tenant/
# - Portal: http://localhost:8000/portal/
# - Admin: http://localhost:8000/admin/
# - Mailhog: http://localhost:8025
```

### Prod-Settings

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DJANGO_ALLOWED_HOSTS` setzen (Komma-separiert)
- `DJANGO_CSRF_TRUSTED_ORIGINS` mit Schema+Port
- `SECURE_SSL_REDIRECT=0` für lokales Testing
- WhiteNoise für Static Files aktiv

---

## 8. Security & GDPR

### Implementierte Sicherheitsmaßnahmen

✅ CSRF-Protection (Django + HTMX-kompatibel)
✅ Rate-Limiting:

- Chat: 20/min (Session+IP)
- Tenant Magic-Link: 3/30min pro E-Mail
  ✅ CSV-Injection-Mitigation (Export)
  ✅ Password-Hashing (Argon2)
  ✅ Idempotency-Keys (Confirm-Endpoint)
  ✅ Session-Expiry:
- Chat: 30min
- Tenant Magic-Link: 15min (single-use)
  ✅ Signierte Token für öffentliche Status-Links
  ✅ **Tenant-Auth:** Session-basiert, keine Passwörter
  ✅ **Chat-Protection:** Nur authentifizierte Tenants

### GDPR-Features

✅ **Export**: JSON-Bundle mit Tenant, Issues, Notes, Attachments-Metadaten
✅ **Erase**: Idempotente PII-Anonymisierung, Audit-Note
✅ **Aufbewahrung**: Keine automatische Löschung (manuell via Admin)

### Security-Matrix

| Endpoint          | Öffentlich | Tenant | Staff | Vendor |
| ----------------- | ---------- | ------ | ----- | ------ |
| `/tenant/`        | ✅         | ✅     | ✅    | ✅     |
| `/chat/`          | ❌         | ✅     | ✅    | ❌     |
| `/tenant/issues/` | ❌         | ✅     | ❌    | ❌     |
| `/portal/`        | ❌         | ❌     | ✅    | ❌     |
| `/admin/`         | ❌         | ❌     | ✅    | ❌     |
| `/t/<token>/`     | ✅         | ✅     | ✅    | ✅     |

---

## 9. Testing

### Testabdeckung (aktuell)

✅ **20+ Tests passed** (pytest)

- Chat FSM States & Transitions
- Idempotency (Confirm)
- CSV Export (Filter, Header, Sanitization)
- GDPR Export/Erase (inkl. Idempotenz)
- Vendor Token Generation
- **NEU:** Tenant Assignment Integration Test

### Test-Commands

```bash
# Alle Tests
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.dev web pytest -q

# Einzelner Test
docker compose exec web pytest landlord/tests/test_tenant_auth.py -v

# Coverage
docker compose exec web pytest --cov=landlord --cov-report=html
```

### Manueller Workflow-Test

**1. Mieter anlegen mit Willkommens-E-Mail:**

```
1. GET /portal/tenants/new
2. Fill: Unit=A, Email=test@example.com, ✅ Willkommens-E-Mail
3. POST → Task queued
4. Check Mailhog: http://localhost:8025
5. Click Magic-Link
6. Verify: Session created, Redirect to /tenant/issues/
```

**2. Chat-Security:**

```
1. Inkognito: GET /chat/ → Redirect to /tenant/ ✅
2. Nach Login: GET /chat/ → Chat öffnet sich ✅
3. Ticket erstellen → tenant=<logged_in_user> ✅
```

**3. Tenant-Assignment:**

```bash
# Check if ticket has tenant
docker compose exec web python manage.py shell -c "
from landlord.models import Issue
i = Issue.objects.latest('created_at')
print(f'Tenant: {i.tenant.primary_email if i.tenant else \"NONE\"}')
"
```

---

## 10. Performance & Skalierung

### Aktuelle Limits (MVP)

- ~10 Wohneinheiten
- ~100 Tickets/Monat
- Single-Server Docker Compose

### Optimierungspotenzial

- Indices: (status, created_at), (severity, created_at), unit_id, tenant_id
- Redis-Cache für Dashboard-Statistiken
- S3 für Attachments (statt lokales Filesystem)
- Load Balancer + Multi-Worker für höheren Traffic

---

## 11. Roadmap (Post-v0.4)

### M11: Vendor Portal Frontend (Nächste 1-2 Wochen)

**Priorität:** 🔥 HOCH

- Vendor Magic-Link E-Mail Task (Auto-Versand)
- Vendor Portal Frontend (Issue-Liste, Details)
- Kostenvoranschlag Upload (PDF durch Vendor)
- Rechnung Upload (PDF durch Vendor)
- ICS-Terminzusagen (Optional)

**Aufwand:** ~12h (1.5 Tage)

### M12-M14: Finanzen (4-6 Wochen)

**Priorität:** 🔥 HOCH

**M12: Mieteingänge & Mahnwesen**

- Zahlungen erfassen (manuell + CSV-Import)
- Soll/Ist-Vergleich
- Mahnwesen Stufe 1-3
- Mahnungen als PDF

**M13: Bankkonto-Integration**

- HBCI/FinTS Setup (fints library)
- Kontoumsätze abrufen
- Auto-Match Zahlungen → Mieter
- SEPA-Export für Lastschriften

**M14: Nebenkostenabrechnung**

- Zählerstände erfassen
- Umlage-Schlüssel (Fläche/Personen/Verbrauch)
- Berechnung & Vorschau
- PDF-Export & E-Mail-Versand

### M15-M16: Wartung & Compliance (2-3 Wochen)

**Priorität:** 🟡 MITTEL

**M15: Wartungskalender**

- Rauchmelder-Verwaltung
- Rauchmelder-Prüftermine (Recurring)
- Heizungswartung-Termine
- E-Mail-Erinnerungen

**M16: Checklisten**

- Checklisten-Templates
- Wohnungsübergabe-Checkliste
- Wartungs-Checkliste
- Foto-Upload pro Checkpunkt
- PDF-Export (Übergabeprotokoll)

### M17+: Advanced Features (8+ Wochen)

**Priorität:** 🟢 NIEDRIG

- **M17:** OCR für Rechnungen (Tesseract/Google Vision)
- **M18:** Digitale Signaturen (DocuSign/eIDAS)
- **M19:** Smart-Home Integration (Philips Hue, Homematic)
- **M20:** KI-Analysen (Kostentreiber, Predictive Maintenance)

---

## 12. Änderungshistorie

| Version | Datum      | Änderungen                                                            |
| ------- | ---------- | --------------------------------------------------------------------- |
| v0.1    | 16.10.2025 | Initial Draft (Planung)                                               |
| v0.2    | 17.10.2025 | M1-M5 implementiert (Backend, API, CSV/GDPR)                          |
| v0.3    | 17.10.2025 | M6-M7 implementiert (Chat-UI, Status-Seite, Portal)                   |
| v0.4    | 18.10.2025 | M9-M10 + PR1-2 (Dokumente, Reports, Vendor, Mieter-CRUD, Tenant-Auth) |

---

## 13. Anhang: Nützliche Commands

### Django Management

```bash
# Migrations erstellen
docker compose exec web python manage.py makemigrations

# Migrations anwenden
docker compose exec web python manage.py migrate

# Shell
docker compose exec web python manage.py shell

# Tests
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.dev web pytest -q

# Superuser erstellen
docker compose exec web python manage.py createsuperuser
```

### Docker

```bash
# Logs anzeigen
docker compose logs -f web
docker compose logs -f worker

# Container neustarten
docker compose restart web
docker compose restart worker

# Alles neu bauen
docker compose build && docker compose up -d

# Files kopieren (für Dev)
docker cp local/file.py uvm-web-1:/app/path/file.py
docker cp local/file.py uvm-worker-1:/app/path/file.py  # Für Tasks!
```

### Worker Management

```bash
# Worker neu starten (nach Task-Änderungen)
docker compose restart worker

# Worker Logs checken
docker compose logs worker --tail=50

# Task manuell triggern
docker compose exec web python manage.py shell -c "
from landlord.tasks import send_tenant_welcome
from landlord.models import Tenant
t = Tenant.objects.first()
send_tenant_welcome.delay(t.pk)
"
```

### Datenbank

```bash
# Direkter DB-Zugriff
docker compose exec db psql -U landlord landlord

# Backup
docker compose exec db pg_dump -U landlord landlord > backup.sql

# Sequence fix (bei Ticket-Nummer-Konflikten)
docker compose exec web python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()
from django.db import connection
c = connection.cursor()
c.execute('SELECT MAX(id) FROM landlord_issue')
m = c.fetchone()[0] or 0
c.execute('SELECT setval(%s, %s)', ['issue_ticket_seq', m+1])
print(f'Sequence set to {m+1}')
"
```

### Mailhog

```bash
# E-Mails checken (Web-UI)
open http://localhost:8025

# API: Letzte E-Mails
curl -s http://localhost:8025/api/v2/messages | jq '.items[0:3] | .[] | {subject: .Content.Headers.Subject[0], to: .Content.Headers.To[0]}'
```

---

## 14. Known Issues & Workarounds

### Issue 1: Sequence out of sync

**Problem:** `duplicate key value violates unique constraint "landlord_issue_ticket_no_uniq"`
**Ursache:** Sequence wurde manuell zurückgesetzt oder Bulk-Insert
**Fix:** Siehe "Sequence fix" in Anhang

### Issue 2: Task nicht registriert

**Problem:** `Received unregistered task of type 'landlord.tasks.xyz'`
**Ursache:** Worker hat alte Version der tasks.py
**Fix:**

```bash
docker cp backend/app/landlord/tasks.py uvm-worker-1:/app/landlord/tasks.py
docker compose restart worker
```

### Issue 3: Magic-Link "Ungültig"

**Problem:** Token ist valid, aber View sagt "Ungültig"
**Ursache:** Token hat kein `tenant` ForeignKey gesetzt
**Fix:** Task muss `tenant=tenant` setzen beim Token-Create (✅ Fixed in v0.4)

---

## 15. Support & Kontakt

**Development Contact**: Matthias Buchalik
**Assistant**: ChatGPT (Code-Generation & Architecture)
**Repository**: (Internal)
**Issues**: Django Admin oder GitHub Issues
**Documentation**: `docs/` Ordner

---

## 16. Quick Reference: User Roles & Permissions

| Feature                             | Public | Tenant | Staff | Vendor   |
| ----------------------------------- | ------ | ------ | ----- | -------- |
| Ticket-Status sehen (`/t/<token>/`) | ✅     | ✅     | ✅    | ✅       |
| Magic-Link anfordern                | ✅     | ✅     | ❌    | ❌       |
| Chat nutzen                         | ❌     | ✅     | ✅    | ❌       |
| Eigene Tickets sehen                | ❌     | ✅     | ❌    | ❌       |
| Portal Dashboard                    | ❌     | ❌     | ✅    | ❌       |
| Mieter verwalten                    | ❌     | ❌     | ✅    | ❌       |
| Vendor zuweisen                     | ❌     | ❌     | ✅    | ❌       |
| Django Admin                        | ❌     | ❌     | ✅    | ❌       |
| Vendor Portal                       | ❌     | ❌     | ❌    | ✅ (M11) |

---

**Status**: ✅ Implementiert & Testbereit für Produktion (mit lokalem Docker-Setup)

**Next Milestone**: M11 - Vendor Portal Frontend (ETA: 1-2 Wochen)
