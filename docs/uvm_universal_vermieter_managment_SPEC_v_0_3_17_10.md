# Vermieter‑App – Technische Spezifikation v0.3

# "UVM" Universal Vermieter Management v0.3

**Datum:** 17.10.2025
**Autor:** ChatGPT (Assistenz für Matthias Buchalik)
**Zielgruppe:** Product Owner, Entwicklung, QA, DevOps
**Status:** Implementiert & Testbereit (M1-M7)

---

## 1. Executive Summary

Eine Web‑Anwendung für Vermieter mit ~10 Wohneinheiten (erweiterbar), in der Mieter Störungen/Anliegen über eine dialogorientierte Chat-Oberfläche melden können. Die Eingaben werden strukturiert gespeichert und können im modernen Vermieter-Portal (Staff-only) sowie im Django-Admin verwaltet werden. Fokus auf **deterministisch geführte Datenerhebung** (FSM-basiert), **mobil-optimierte UI**, **Docker‑basierte Bereitstellung** und **GDPR‑konforme** Verarbeitung.

---

## 2. Was ist implementiert (M1-M7)

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
- `POST /api/admin/issues/export/csv` - CSV-Export mit Sanitization (CSV-Injection-Mitigation)
- `POST /api/admin/tenants/<id>/export` - GDPR Export (JSON)
- `POST /api/admin/tenants/<id>/erase` - GDPR Erase (idempotent)

✅ **Background Tasks (Celery)**

- `send_issue_created` - Email an Tenant mit Status-Link
- `send_status_changed` - Statuswechsel-Benachrichtigung
- `send_appointment_invite` - ICS-Datei für Termin

✅ **Rate Limiting & Security**

- Throttle: Session+IP für Chat-Endpoints (20/min)
- Admin-APIs: IsAdminUser Permission
- CSRF-Protection aktiv
- CSV-Injection-Mitigation (führendes `'` bei = + - @)

### M6: Mieter-Chat UI & Öffentliche Statusseite

✅ **Mobiles Chat-UI** (`/chat/`)

- Tailwind CSS, HTMX-kompatibel
- Bubble-Konversation (Bot/User)
- Dynamische Eingabefelder je nach FSM-State
- Toast-Benachrichtigungen
- Datei-Upload funktioniert
- Status-Link nach Bestätigung

✅ **Öffentliche Ticket-Statusseite** (`/t/<token>/`)

- Signierte Token (ohne Migration, `django.core.signing`)
- Read-only View: Ticket-Details, Termine, Mieter-Hinweise
- Responsive Design

### M7: Vermieter-Portal (Staff-only Web-UI)

✅ **Dashboard** (`/portal/`)

- Anzahl offener Tickets
- Neueste 10 Tickets
- Navigation: Dashboard | Tickets | Admin

✅ **Tickets-Liste** (`/portal/issues/`)

- Filter: Status, Objekt, Suche (Ticket/Betreff)
- 🔥 Dringend-Filter (Severity ≥4)
- Pagination (20 pro Seite)
- Klickbare Zeilen → Detail

✅ **Ticket-Detail** (`/portal/issues/<id>/`)

- Status ändern (HTMX, ohne Page-Reload)
- Notizen hinzufügen (intern/öffentlich)
- Vendor zuweisen → automatischer Termin
- Termine manuell anlegen
- Farbcodierte Status-Badges

---

## 3. Technischer Stack (wie implementiert)

### Backend

- **Django 5.1.2** + **Django REST Framework 3.15.2**
- **PostgreSQL 16** (über Docker)
- **Redis 7** (Celery Broker + Cache)
- **Celery 5.4.0** (Background Tasks)
- **Argon2** (Password Hashing)
- **WhiteNoise 6.6.0** (Static Files in Production)

### Frontend

- **Server-rendered Templates** (Django Templates)
- **Tailwind CSS** (via CDN für schnelles Prototyping)
- **HTMX 1.9.10** (für interaktive Actions ohne JS-Framework)
- **Vanilla JavaScript** (für Chat-FSM-Logic)

### Infrastructure

- **Docker Compose** (7 Services)
  - `web` - Django runserver (dev) / Gunicorn+Uvicorn (prod)
  - `worker` - Celery worker (2 Queues: default, emails)
  - `beat` - Celery beat scheduler
  - `db` - PostgreSQL 16
  - `redis` - Redis 7
  - `minio` - MinIO (S3-kompatibel für Uploads)
  - `mailhog` - Mail-Testing (Port 8025)

### Storage

- **Local FileSystem** (dev: `/app/media`)
- **MinIO** (S3-kompatibel, optional via `USE_S3=true`)

---

## 4. URLs & Endpunkte

### Öffentlich (keine Auth)

- `GET /healthz` - Healthcheck (DB + Redis Status)
- `GET /chat/` - Mieter-Chat-UI
- `POST /api/chat/sessions/` - Chat-Session erstellen
- `POST /api/chat/sessions/<uuid>/message` - FSM-Step
- `POST /api/chat/sessions/<uuid>/confirm` - Ticket finalisieren
- `GET /t/<token>/` - Öffentliche Ticket-Statusseite (signiert)

### Staff-only (Django `@staff_member_required`)

- `GET /portal/` - Vermieter-Dashboard
- `GET /portal/issues/` - Tickets-Liste mit Filtern
- `GET /portal/issues/<int:pk>/` - Ticket-Detail
- `POST /portal/issues/<int:pk>/status` - Status ändern (HTMX)
- `POST /portal/issues/<int:pk>/notes` - Notiz hinzufügen (HTMX)
- `POST /portal/issues/<int:pk>/assign-vendor` - Vendor zuweisen (HTMX)
- `POST /portal/issues/<int:pk>/appointment` - Termin anlegen (HTMX)

### Admin-only (`IsAdminUser` Permission)

- `GET /admin/` - Django Admin
- `GET /api/admin/issues/` - Issues-API (Filter/Ordering/Pagination)
- `POST /api/admin/issues/export/csv` - CSV-Export
- `POST /api/admin/tenants/<id>/export` - GDPR Export
- `POST /api/admin/tenants/<id>/erase` - GDPR Erase

---

## 5. Rollen & Berechtigungen

| Rolle         | Zugriff                                                           |
| ------------- | ----------------------------------------------------------------- |
| **Anonymous** | Chat-UI (`/chat/`), Status-Seite (`/t/<token>/`)                  |
| **Staff**     | Portal (`/portal/`), Ticket-Management, Notizen, Vendor-Zuweisung |
| **Admin**     | Alles + Django Admin + API-Endpunkte + GDPR-Tools                 |

---

## 6. Datenmodell (Kern)

### Property

- `name`, `street`, `postal_code`, `city`, `notes`

### Unit

- `property` (FK), `unit_label`, `floor`, `size_sqm`

### Tenant

- `unit` (FK), `primary_email`, `phone`, `notes`

### Issue

- `ticket_no` (unique, auto-generated: TCK-YYYY-XXXXX)
- `status` (NEW, IN_PROGRESS, WAITING_VENDOR, WAITING_TENANT, DONE)
- `severity` (1-5)
- `category` (z.B. "heating", "water", "electric")
- `summary`, `location_hint`, `occurred_at`
- `unit` (FK), `tenant` (FK optional)
- `created_at`, `updated_at`

### IssueNote

- `issue` (FK), `text`, `visibility` (tenant/internal)
- `created_at`

### IssueAttachment

- `issue` (FK), `file` (FileField), `mime`, `size_bytes`

### Appointment

- `issue` (FK), `vendor` (FK optional)
- `start`, `end`

### ChatSession

- `id` (UUID), `state`, `version`, `payload` (JSON)
- `issue` (FK optional), `expires_at`

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

# 4. Collectstatic (nur für prod-Settings)
docker compose exec web python manage.py collectstatic --noinput

# URLs:
# - Chat: http://localhost:8000/chat/
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
✅ Rate-Limiting (Session+IP, 20/min für Chat)
✅ CSV-Injection-Mitigation (Export)
✅ Password-Hashing (Argon2)
✅ Idempotency-Keys (Confirm-Endpoint)
✅ Session-Expiry (30min für Chat)
✅ Signierte Token für öffentliche Status-Links

### GDPR-Features

✅ **Export**: JSON-Bundle mit Tenant, Issues, Notes, Attachments-Metadaten
✅ **Erase**: Idempotente PII-Anonymisierung, Audit-Note (nur einmal)
✅ **Aufbewahrung**: Keine automatische Löschung (manuell via Admin)

### Noch zu implementieren (Optional)

- Legal Hold Flag (verhindert Erase bei aktiven Verfahren)
- Structured Logging (event, user_id, duration_ms)
- Cache-Control: no-store für Admin-Exports
- X-Content-Type-Options: nosniff Header

---

## 9. Testing

### Testabdeckung (aktuell)

✅ 20 Tests passed (pytest)

- Chat FSM States & Transitions
- Idempotency (Confirm)
- CSV Export (Filter, Header, Sanitization)
- GDPR Export/Erase (inkl. Idempotenz)

### Test-Infrastruktur

- `pytest` + `pytest-django`
- Dev-Settings für Tests (`config.settings.dev`)
- Docker-basiert: `docker compose exec web pytest`

### E2E-Tests (geplant)

- Playwright für kompletten Chat-Flow
- Vendor-Zuweisung mit Email-Check (Mailhog)

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

## 11. Roadmap (Post-MVP)

### M8: Mieter-Portal (optional)

- Login für Tenants (Magic-Link oder Email+Passwort)
- Eigene Ticket-Historie
- Notiz-Antworten auf Tenant-Seite

### M9: Reports & Analytics

- Open Tickets per Property
- Ageing by Status (Ø Tage)
- Top Categories (30 Tage)
- CSV-Export für Reports

### M10: Vendor-Portal (optional)

- Login für Vendors
- Zugewiesene Tickets & Termine
- Status-Updates von Vendor-Seite

### M11: Production-Hardening

- Sentry für Error-Tracking
- Structured Logging (JSON)
- Prometheus Metrics
- Automated Backups (DB + Media)

---

## 12. Änderungshistorie

| Version | Datum      | Änderungen                                          |
| ------- | ---------- | --------------------------------------------------- |
| v0.1    | 16.10.2025 | Initial Draft (Planung)                             |
| v0.2    | 17.10.2025 | M1-M5 implementiert (Backend, API, CSV/GDPR)        |
| v0.3    | 17.10.2025 | M6-M7 implementiert (Chat-UI, Status-Seite, Portal) |

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
```

### Docker

```bash
# Logs anzeigen
docker compose logs -f web
docker compose logs -f worker

# Container neustarten
docker compose restart web

# Alles neu bauen
docker compose build && docker compose up -d
```

### Datenbank

```bash
# Direkter DB-Zugriff
docker compose exec db psql -U landlord landlord

# Backup
docker compose exec db pg_dump -U landlord landlord > backup.sql
```

---

## 14. Support & Kontakt

**Development Contact**: Matthias Buchalik
**Assistant**: ChatGPT (Code-Generation & Architecture)
**Repository**: (Internal)
**Issues**: (Django Admin oder GitHub Issues)

---

**Status**: ✅ Implementiert & Testbereit für Produktion (mit lokalen Docker-Setup)
