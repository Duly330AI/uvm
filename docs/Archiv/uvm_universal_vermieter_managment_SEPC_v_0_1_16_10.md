# Vermieter‑App – Technische Spezifikation v0.1
# "UVM" Universal Vermieter Managment v0.1

**Datum:** 16.10.2025  
**Autor:** ChatGPT-assisted draft
**Zielgruppe:** Product Owner, Entwicklung, QA, DevOps  
**Status:** Entwurf (reviewfähig)

---

## 1. Executive Summary
Eine Web‑Anwendung für Vermieter mit ~10 Wohneinheiten (erweiterbar), in der Mieter Störungen/Anliegen über eine dialogorientierte Oberfläche („Chat‑Formular“) melden. Die Eingaben werden strukturiert gespeichert, im Admin‑Bereich verwaltet (Status, Notizen, Termine, Dienstleister‑Zuweisung) und per Benachrichtigungen verfolgt. Fokus auf **deterministisch geführte Datenerhebung** (keine LLM‑Pflicht), **schnell nutzbarer Admin**, **Docker‑basierte Bereitstellung** und **GDPR‑konforme** Verarbeitung.

---

## 2. Review & Verbesserungen gegenüber der Ausgangsidee
Die Gemini‑Antwort skizziert Django/Flask, Chatbot‑Libs und NLP. Das Grundprinzip ist korrekt. Für ein produktionsnahes MVP empfehlen wir:

1. **Geführtes Chat‑Formular mit Zustandsmaschine (FSM) statt „intelligentem Chatbot“**:  
   ‑ deterministische Schritte (Begrüßung → Problem → Zeitpunkt → Ort → Dringlichkeit → Kontakt/Erreichbarkeit → Medien → Bestätigung).  
   ‑ robust, testbar, barrierearm; keine Halluzinationen.

2. **Django‑Stack (Admin inklusive) + DRF + Channels**:  
   ‑ minimaler Setup‑Aufwand für den Admin‑Bereich, Permissions out‑of‑the‑box.  
   ‑ REST API für das Chat‑Frontend und Admin‑UI‑Erweiterungen.  
   ‑ Channels/WebSocket optional (Live‑Status/Live‑Chat, späteres Upgrade).

3. **Optionale „leichte KI“** nur für Klassifikation/Normalisierung (z. B. Schlüsselwörter → Kategorie), **nicht** für den Primärfluss.  
   ‑ einfache Keyword‑/Regel‑Engine, später ersetzbar durch spaCy oder Cloud‑NLU.

4. **Strukturierte Datenmodelle & klare Status**:  
   ‑ `Issue` mit `status`, `severity`, `category`, `notes`, `appointments`.  
   ‑ `Tenant`, `Unit`, `Property`, `Vendor` (Dienstleister).  
   ‑ Datei‑Uploads (Fotos/Videos) für Beweissicherung.

5. **DevOps & Qualität**: Docker Compose, Mailhog/SMTP‑Dev, MinIO (S3‑kompatibel) für Medien, Sentry (optional), Playwright‑E2E für Chat‑Flow.

6. **Datenschutz/Security** von Anfang an: DSGVO‑Checkliste, Rollenmodell, Audit‑Log, Aufbewahrung & Löschung.

---

## 3. Ziele, Nicht‑Ziele, Erfolgskriterien
**Ziele**
- Mieter können Anliegen schnell und niederschwellig melden (mobilfähig).  
- Admin kann Anliegen strukturiert einsehen, priorisieren, kommentieren, Dienstleister beauftragen, Termine planen.  
- Vollständige Nachverfolgbarkeit (Historie, Notizen, Statuswechsel).  
- Einfache Bereitstellung via Docker Compose.

**Nicht‑Ziele (v1/MVP)**
- Kein komplexes Multi‑Vermieter‑SaaS mit Abrechnung.  
- Kein vollwertiges Ticketsystem mit SLAs/Workflows für Großbetriebe.  
- Keine LLM‑gestützte Dialogsteuerung im Primary Flow (nur optional zur Kategorisierung).

**Erfolgskriterien (MVP)**
- Ein Anliegen lässt sich vom Mieter vollständig erfassen inkl. Fotos.  
- Das Anliegen erscheint im Admin, kann auf **„in Arbeit“** gesetzt und mit Notizen/Termin versehen werden.  
- Benachrichtigung an Mieter beim Statuswechsel.  
- End‑to‑End‑Test (Playwright) deckt Standard‑Flow ab.

---

## 4. Nutzer & Rollen
- **Tenant (Mieter)**: Meldet Anliegen zu seiner **Unit** (Wohnung).  
- **Staff (Mitarbeiter/Vermieter)**: Sichtet, bearbeitet, notiert, ändert Status.  
- **Admin**: Alle Rechte, Stammdatenpflege (Properties/Units/Vendors/Users).  
- **Vendor (Dienstleister, optionales Portal in v2)**: Sieht ihm zugewiesene Vorgänge/Termine.

---

## 5. Use‑Cases & User Stories (Auszug)
1. **Meldung absetzen** (Tenant):  
   *Als Mieter möchte ich per Chat‑Formular mein Problem schildern, Bilder hochladen und meine Erreichbarkeit angeben, damit der Vermieter effizient helfen kann.*

2. **Sichten & Priorisieren** (Staff/Admin):  
   *Als Vermieter möchte ich eine Liste neuer Anliegen mit Ort, Kategorie, Dringlichkeit sehen, um sie in Arbeit zu nehmen.*

3. **Status setzen & notieren** (Staff):  
   *Als Vermieter möchte ich ein Ticket auf „in Arbeit“ setzen und Notizen sowie Beauftragungen dokumentieren.*

4. **Terminierung** (Staff):  
   *Als Vermieter möchte ich einen Termin (z. B. mit Installateur) planen und den Mieter benachrichtigen.*

5. **Kommunikation** (Tenant/Staff):  
   *Als Mieter möchte ich Benachrichtigungen (Mail) über Statusänderungen erhalten.*

6. **Anhänge** (Tenant/Staff):  
   *Als Nutzer möchte ich Fotos/Videos anhängen, damit die Lage besser eingeschätzt werden kann.*

---

## 6. Systemarchitektur (MVP)
**Empfohlener Stack**
- **Backend**: Django 5.x, Django REST Framework (DRF), Django Channels (optional), Celery + Redis (Background‑Jobs/Benachrichtigungen).  
- **Datenbank**: PostgreSQL 16.  
- **Storage**: S3‑kompatibel (MinIO in Dev), lokal möglich.  
- **Frontend**: Server‑rendered Django Templates *oder* schlankes SPA‑Frontend (HTMX/AlpineJS) für den Chat‑Flow; Admin primär via Django Admin (+ Custom Views).  
- **Auth**: Django Auth (E‑Mail + Passwort), optional Magic‑Link für Mieter‑Aktivierung.  
- **Container/Orchestration**: Docker Compose (web, worker, redis, db, minio, mailhog).

**Kontextdiagramm (ASCII)**
```
[ Mieter-Browser ] --(HTTPS)--> [ Django/DRF Web ] --(ORM)--> [ PostgreSQL ]
                                     |   |\
                                     |   +-> [ MinIO (S3) ]
                                     |   +-> [ Redis ] <--- Celery Worker (Mails/Jobs)
[ Admin-Browser ] --(HTTPS)----------+
```

**Skalierung**: Single‑Node Compose für Start; später separierbar (Web/Worker/DB/Storage) und mit Caddy/Nginx als Reverse Proxy.

---

## 7. Datenmodell
**Kern‑Entitäten**
- **Property** (Liegenschaft/Adresse)  
  Felder: `id`, `name` (optional), `street`, `postal_code`, `city`, `country`, `geo_lat`, `geo_lng`, `notes`.

- **Unit** (Wohnung)  
  Felder: `id`, `property` (FK), `unit_label` (z. B. „WE 1. OG links“), `floor`, `rooms`, `area_sqm`, `notes`, `is_active`.

- **Tenant** (Mieter)  
  Felder: `id`, `user` (FK auth_user), `primary_email`, `phone`, `unit` (FK), `moved_in_at`, `moved_out_at`, `is_active`.

- **Vendor** (Dienstleister)  
  Felder: `id`, `name`, `email`, `phone`, `trade` (z. B. Sanitär, Elektro), `address_text`, `notes`.

- **Issue** (Ticket/Anliegen)  
  Felder:  
  `id`, `tenant` (FK), `unit` (FK), `category` (Enum: water, heating, electricity, structural, other), `severity` (Enum 1–5),  
  `status` (Enum: `NEW`, `IN_PROGRESS`, `WAITING_TENANT`, `WAITING_VENDOR`, `SCHEDULED`, `RESOLVED`, `CANCELLED`),  
  `summary` (Kurztext), `description_raw` (Freitext vom Mieter), `description_struct` (JSON mit extrahierten Feldern),  
  `occurred_at` (Zeitpunkt), `location_hint` (z. B. „Badezimmer“), `contact_times` (z. B. „Mo–Fr 12–16“),  
  `sla_due_at` (optional), `created_at`, `updated_at`, `created_via` (chat/form/api).

- **IssueAttachment**  
  Felder: `id`, `issue` (FK), `uploader_role` (Enum: tenant, staff), `file`, `mime`, `size_bytes`, `uploaded_at`.

- **IssueNote**  
  Felder: `id`, `issue` (FK), `author` (FK user), `visibility` (Enum: internal/public), `text`, `created_at`.

- **Appointment** (Termin)  
  Felder: `id`, `issue` (FK), `vendor` (FK), `start`, `end`, `status` (Enum: invited, confirmed, done, cancelled), `notes`.

- **ChatSession** (Dialog‑FSM)  
  Felder: `id`, `tenant` (nullable, falls Gast/Activation‑Flow), `unit` (nullable bis Identifikation), `state` (Enum siehe FSM),  
  `payload` (JSON Zwischenstände), `transcript` (JSON), `expires_at`, `created_at`, `updated_at`.

**ERD (vereinfacht, ASCII)**
```
Property 1---* Unit 1---* Tenant 1---* Issue *---* IssueAttachment
                                   \            \---* IssueNote
                                    \            \---* Appointment *---1 Vendor
                                     \---0..1 ChatSession
```

**Validierungen (Auszug)**
- `Issue`: `tenant` ODER `unit` muss bekannt sein (mind. eine Zuordnung).  
- `occurred_at` ≤ `now`.  
- `severity` ∈ {1,2,3,4,5}.  
- Uploads: Max. Größe (z. B. 10 MB), erlaubte MIME‑Typen (jpeg/png/mp4/pdf).

---

## 8. Dialog‑Spezifikation (FSM)
**Ziel:** vollständige, strukturierte Erfassung ohne LLM.

**Zustände**
- `GREETING` → Begrüßung + kurze Erklärung.  
- `CAPTURE_SUMMARY` → Freitext „Worum geht es?“ (z. B. „Seit Montag kein Wasser im Bad“).  
- `CAPTURE_OCCURRED_AT` → „Seit wann?“ (Datum/Uhrzeit).  
- `CAPTURE_LOCATION` → „Wo genau?“ (Raum/Ort).  
- `CAPTURE_SEVERITY` → Skala 1–5 + ggf. Hinweise (Sicherheitsrisiko?).  
- `CAPTURE_MEDIA` → Upload von Fotos/Videos (optional).  
- `CAPTURE_CONTACT` → Erreichbarkeit/Telefon.  
- `CONFIRM` → Zusammenfassung zur Bestätigung.  
- `CREATE_ISSUE` → Ticket anlegen, Ticket‑Nr. anzeigen, E‑Mail‑Bestätigung senden.  
- `DONE` → Link zur Statusseite.

**Verzweigungen & Regeln**
- Schlüsselwort‑Heuristik zur `category`‑Vorauswahl (z. B. „Wasser“, „Heizung“, „Strom“).  
- Bei **kritischen Mustern** (Gasgeruch, Elektrik‑Gefahr): sofortiger Hinweis + Priorität erhöhen + optional Hotline anzeigen.  
- Abbruch/Zurück möglich (Back‑Steps).  
- Timeout/Expiry von Sessions (z. B. 60 min Inaktivität).

**Beispiel‑Bestätigung (CONFIRM)**
> *Zusammenfassung*: „Kein Wasser im Badezimmer“;  
> *Seit*: Mo, 14.10.2025, 07:00;  
> *Ort*: Bad; *Dringlichkeit*: 4/5;  
> *Kontakt*: 0151… Mo–Fr 12–16;  
> *Anhänge*: 2 Fotos.  
> **Erzeugen?** [Ja] [Bearbeiten]

---

## 9. API‑Design (Auszug, DRF)
**Authentifizierung**: Session‑Auth für Admin/Staff (Django), token‑basierte Endpunkte (JWT/knox) optional. Tenant‑Flow kann auch ohne Login starten (E‑Mail‑Verifizierung im Verlauf, optional).

- `POST /api/chat/sessions/`  
  **Body**: `{ unit_id?, tenant_token? }` → **201** `{ id, state }`

- `POST /api/chat/sessions/{id}/message`  
  **Body**: `{ text?, occurred_at?, location?, severity?, contact?, files? }` → **200** `{ state, next_prompt, payload_partial }`

- `POST /api/chat/sessions/{id}/confirm`  
  **200** `{ issue_id, ticket_no }`

- `GET /api/issues?status=NEW|IN_PROGRESS|...&search=...`  
  **200** `[{ id, ticket_no, unit, tenant, category, severity, status, created_at }]`

- `GET /api/issues/{id}`  
  Detail inkl. Notizen/Anhänge/Historie.

- `PATCH /api/issues/{id}`  
  Felder: `status`, `category`, `severity`, `vendor_id`...

- `POST /api/issues/{id}/notes`  
  **Body**: `{ text, visibility }`

- `POST /api/issues/{id}/appointments`  
  **Body**: `{ vendor_id, start, end, notes }`

- `POST /api/issues/{id}/attachments`  
  Multipart Upload.

---

## 10. Admin‑Bereich (Django Admin + Custom Views)
**Listen**: Issues (Filter: Status, Kategorie, Property/Unit, Severity, Zeitraum).  
**Detail**: Kopf (Ticket‑Nr., Mieter, Unit), Status‑Buttons, Kategorie/Severity, Notizen (intern/öffentlich), Anhänge, Termin‑Widget (Kalender), Vendor‑Zuweisung.  
**Stammdaten**: Properties, Units, Tenants, Vendors.  
**Auditing**: History‑Log (Statuswechsel/Notizen/Assignee/Terminänderungen).  
**Suchen**: globaler Suchbalken (Ticket‑Nr., Namen, Adresse, Keywords).

---

## 11. Benachrichtigungen
- **E‑Mail**: Bestätigung nach Ticket‑Erstellung, Statuswechsel, Termin‑Einladung (ICS‑Anhang).  
- **Optional SMS** (später): Twilio/Provider via Celery‑Task.  
- **Vorlagen**: Jinja/Django‑Templates mit Variablen (Ticket‑Nr., Datum, Ansprechpartner).  
- **Zustellbarkeit Dev**: Mailhog in Compose.

---

## 12. Nicht‑funktionale Anforderungen
- **Sicherheit**: CSRF/HTTPS, Passwort‑Hashing (Argon2), Rate‑Limiting (DRF Throttling), Upload‑Scanning (ClamAV optional), rollenbasierte Rechte.  
- **Datenschutz**: Einwilligungstexte, Datenschutzerklärung, Löschkonzept (Ticket/Anhänge nach X Jahren), Auskunft/Export (DSGVO Art. 15), Datenminimierung.  
- **Performance**: P95 API < 300 ms bei 50 RPS (MVP‑Skala), Bild‑Resizing/Thumbnail‑Generation asynchron.  
- **Observability**: strukturiertes Logging, Request‑IDs, Health‑Endpoint, Sentry (optional).  
- **Internationalisierung**: Deutsch (v1), i18n‑fähig.

---

## 13. DevOps & Deploy
**Docker Compose Services (MVP)**
- `web`: Django + DRF + Gunicorn/Daphne.  
- `worker`: Celery (async tasks), `beat` für periodische Aufgaben.  
- `db`: Postgres 16.  
- `redis`: Broker/Cache.  
- `minio`: S3‑Storage; `minio‑mc` (Setup).  
- `mailhog`: SMTP Dev + Web UI.

**Konfiguration (Beispiele)**
- `.env`: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `DEFAULT_FROM_EMAIL`.  
- Medienpfade/Retention, Upload‑Limits (Nginx/ASGI‑Server berücksichtigen).  
- Backups: pg_dump nightly, MinIO Versioning optional.

---

## 14. Teststrategie
- **Unit‑Tests**: Modelle, Serializer, Permissions, FSM‑Übergänge.  
- **Integration**: API‑Flows (Chat‑Session → Issue), Upload‑Handling, E‑Mail‑Dispatch.  
- **E2E (Playwright)**:
  1) Mieter startet Chat, meldet „kein Wasser“, lädt 2 Fotos hoch, bestätigt → Ticket erstellt.  
  2) Admin setzt Status auf „in Arbeit“, fügt Notiz hinzu → Mieter erhält Mail.  
  3) Admin legt Termin an → Mieter erhält ICS.

- **Performance‑Smoke**: einfache Locust/ab‑Tests (optional).  
- **Security**: grundlegende OWASP‑Checks (AuthZ, Upload‑Typen, Rate‑Limit).

---

## 15. Roadmap & Meilensteine
- **M1 – Projektgerüst (1–2 Tage)**: Django + DRF, Modelle/Migrationen, Admin registriert, Compose up, Mailhog/MinIO ok.  
- **M2 – Chat‑FSM & API (2–4 Tage)**: Chat‑Session Endpunkte, Templates/HTMX, Validierungen, Tests.  
- **M3 – Issues & Admin (2–4 Tage)**: Issue‑Listen, Detail, Statuswechsel, Notizen, Anhänge.  
- **M4 – Benachrichtigung & Termine (1–3 Tage)**: E‑Mail‑Templates, ICS, Vendor‑Stammdaten.  
- **M5 – Feinschliff & E2E (1–2 Tage)**: Playwright, Doku, Backup‑Skripte, Logging.

*(Tage = Netto‑Entwicklungszeit; realistisch gepuffert je nach Umfang.)*

---

## 16. Offene Punkte / Entscheidungsbedarf
- Tenant‑Login vs. Gast‑Flow mit E‑Mail‑Verifikation? (MVP Empfehlung: Gast‑Flow + Bestätigungs‑Mail)  
- SMS‑Benachrichtigungen in v1 oder v2?  
- Vendor‑Portal (Leserechte/Termin‑Bestätigung) in v2?  
- Obligatorische i18n (DE/EN) oder nur DE in v1?

---

## 17. Beispiel‑Payloads
**Issue Detail (GET /api/issues/{id})**
```json
{
  "id": 123,
  "ticket_no": "TCK-2025-00123",
  "tenant": { "name": "Max Mustermann", "email": "max@example.com" },
  "unit": { "id": 9, "label": "WE 1. OG links", "property": "Hauptstr. 12, 46485 Wesel" },
  "category": "water",
  "severity": 4,
  "status": "IN_PROGRESS",
  "summary": "Kein Wasser im Badezimmer",
  "description_raw": "Seit Montagmorgen kommt kein Wasser im Bad.",
  "description_struct": {
    "room": "Badezimmer",
    "occurred_at": "2025-10-14T07:00:00Z",
    "keywords": ["wasser", "bad"]
  },
  "attachments": [
    { "id": 55, "mime": "image/jpeg", "url": "/media/issues/123/1.jpg" },
    { "id": 56, "mime": "image/jpeg", "url": "/media/issues/123/2.jpg" }
  ],
  "notes": [
    { "id": 77, "author": "Admin", "visibility": "internal", "text": "Sanitär Felix Krach beauftragt", "created_at": "2025-10-16T09:20:00Z" }
  ],
  "appointments": [
    { "id": 11, "vendor": "Sanitär Krach", "start": "2025-10-20T10:00:00Z", "end": "2025-10-20T11:00:00Z", "status": "invited" }
  ],
  "created_at": "2025-10-16T08:00:00Z",
  "updated_at": "2025-10-16T09:25:00Z"
}
```

---

## 18. Minimaler Compose‑Ausschnitt (Beispiel)
```yaml
services:
  web:
    build: ./app
    env_file: .env
    depends_on: [db, redis, minio]
    ports: ["8000:8000"]
    command: gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

  worker:
    build: ./app
    env_file: .env
    depends_on: [web, redis]
    command: celery -A config.celery_app worker -l info

  beat:
    build: ./app
    env_file: .env
    depends_on: [worker]
    command: celery -A config.celery_app beat -l info

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: landlord
      POSTGRES_USER: landlord
      POSTGRES_PASSWORD: landlord
    volumes:
      - dbdata:/var/lib/postgresql/data

  redis:
    image: redis:7

  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio123
    command: server /data --console-address :9001
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio:/data

  mailhog:
    image: mailhog/mailhog
    ports: ["8025:8025"]

volumes:
  dbdata: {}
  minio: {}
```

---

## 19. Projektstruktur (Django‑Variante, Vorschlag)
```
app/
  config/
    __init__.py
    settings.py
    urls.py
    asgi.py
    wsgi.py
    celery_app.py
  requirements.txt
  manage.py
  landlord/                # Domain‑App
    models.py              # Property, Unit, Tenant, Vendor, Issue, Attachments, Notes, Appointment, ChatSession
    admin.py               # Admin‑Registrierungen + Custom Admin
    serializers.py         # DRF Serializer
    views.py               # API Views (ViewSets)
    urls.py
    fsm.py                 # Dialog‑Zustandsmaschine
    tasks.py               # Celery Tasks (Mails, Thumbnails, ICS)
    templates/
      chat/
        index.html         # Chat‑UI (HTMX/AlpineJS)
      emails/
        issue_created.html
        status_changed.html
    static/
      css/js/img
  tests/
    test_models.py
    test_api_chat.py
    test_api_issues.py
    e2e/
      playwright.spec.ts
```

---

## 20. Sicherheit & Datenschutz (Kurzleitfaden)
- **Rollen/Permissions**: Staff/Admin getrennt; Tenant sieht nur seine Issues.  
- **Auditing**: Änderungen an Status/Notizen werden geloggt (who/when/what).  
- **Uploads**: Virenscan optional, EXIF‑Stripping (Privacy), Public‑URLs mit zeitlich begrenzten Signed URLs.  
- **Rechtsgrundlagen**: Vertragserfüllung (Art. 6 Abs. 1 lit. b DSGVO) für Anliegenbearbeitung; Aufbewahrung: z. B. 3–6 Jahre (juristisch prüfen).  
- **Betroffenenrechte**: Export (JSON/PDF), Löschung auf Anfrage (sofern keine Aufbewahrungspflichten entgegenstehen).

---

## 21. Erweiterungen (v2+)
- Vendor‑Portal (Login, Termin‑Bestätigung, Upload Befund/Rechnung).  
- Push‑Benachrichtigungen (PWA).  
- Eskalations‑Logik (SLA/Fristen).  
- Mehrmandantenfähigkeit (mehrere Vermieter/Verwaltungen).  
- Optionale NLU‑Klassifikation & Summarization (spaCy/Cloud‑NLU).  
- WebSockets Live‑Status, Chat in Echtzeit (Channels).  
- Kalender‑Sync (ICS‑Feed oder Google/Microsoft‑Integration).

---

## 22. Akzeptanzkriterien (MVP, stichpunktartig)
- [ ] Mieter kann ohne Login ein Anliegen vollständig melden (mit Upload), erhält Ticket‑Nr. + Bestätigungs‑Mail.  
- [ ] Admin sieht Anliegenliste, kann Status→„in Arbeit“ setzen, interne Notiz hinterlegen.  
- [ ] Admin kann Termin mit Vendor anlegen; E‑Mail mit ICS wird versendet.  
- [ ] Anhänge sind abrufbar, Zugang geschützt.  
- [ ] E2E‑Test des Standard‑Flows grün.  
- [ ] Docker Compose „up“ bringt das System reproduzierbar zum Laufen.

---

## 23. Nächste Schritte (konkret)
1. Repo initialisieren, Django/DRF/Compose Grundgerüst anlegen.  
2. Modelle & Migrationen implementieren.  
3. Chat‑FSM + API Endpunkte + einfache Chat‑UI (HTMX) implementieren.  
4. Admin‑Customizations (Filter, Aktionen, Detail‑Layout).  
5. E‑Mail‑Vorlagen + ICS‑Erzeugung (Termine).  
6. Tests (Unit/Integration/E2E) + README/ENV‑Doku.  
7. Review mit Fachseite (Formulierungen, Pflichteingaben, Benachrichtigungen).

---

*Ende der Spezifikation v0.1*

