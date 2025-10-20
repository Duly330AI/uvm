# UVM – Gebäude (Properties) : Portal-CRUD + Zähler (Stammdaten)

Version: **1.3 (Final Spec - Production Ready)**
Datum: **2025-10-20**
Owner: **Landlord / Property Management**
Scope: **Portal-Modul „Gebäude"** mit Property-CRUD und Zählerverwaltung.
Hinweis: **Units sind out of scope** (separate Spec). Django-Admin bleibt unverändert als „uncut Admin".

---

## 1) Ziel & Nutzen

- Properties im Portal mobilfreundlich **anlegen/anzeigen/bearbeiten/archivieren/löschen**.
- Je Property **beliebig viele Zähler** verwalten (add/edit/remove).
- Zählerdaten dienen der **automatischen Vorbefüllung** im Zählerstands-Formular.

**Scope-Klarstellung:**

- Diese Spec behandelt **Building-Level Meters** (Haus-Hauptzähler).
- Unit-Level Meters (Wohnungszähler) folgen in separater Spec („Units CRUD").
- Mapping zwischen Building-Meters und Unit-Readings erfolgt später (derzeit: Readings direkt an Unit).
- **Future:** UtilityMeter mit `scope` (building|unit) für konsistente Hierarchie.

---

## 2) Navigation

- Neuer Top-Nav-Button: **Gebäude** (Pfad: `/portal/properties/`).
- Seiten:

  1. Übersicht `/portal/properties/` (Liste mit Suche/Filter/Sort/Paging)
  2. Anlegen `/portal/properties/new`
  3. Detail & Bearbeiten `/portal/properties/{id}/`
  4. Optionaler Bestätigungsdialog fürs Archivieren/Löschen

---

## 3) Felder (exakt, ohne Spekulation)

### 3.1 Property – Stammdaten

- Name (Pflicht)
- Street
- Postal code
- City
- Country (Dropdown; Default: DE; ISO-3166-1-alpha-2)
  - **Initial Scope:** DE, AT, CH
  - **Storage:** 2-letter code ("DE", "AT", "CH")
  - **Display:** Localized (z.B. "Deutschland", "Österreich", "Schweiz")
  - **Future:** Erweiterbar auf vollständige ISO-Liste ohne Migration
- Geo lat
- Geo lng
- Notes

**Validierungen**

- Name: max. 200 Zeichen.
- Postal code: DE genau 5 Ziffern; sonst alphanumerisch bis 10 (künftige Länderspezifika möglich).
- Geo lat: **DecimalField(9,6)**, Range −90.0 bis +90.0 (DB Check-Constraint)
- Geo lng: **DecimalField(9,6)**, Range −180.0 bis +180.0 (DB Check-Constraint)
- Notes: max. 2000 Zeichen.

### 3.2 Zähler (Stammdaten) – pro Eintrag

- Meter type (Kaltwasser, Warmwasser, Strom, Gas (kWh))
- Serial number (optional; max. 50; Zeichen: A-Z, a-z, 0-9, Bindestrich, Slash)
  - **Storage:** Normalized uppercase (z.B. "ABC-123")
  - **Optional Future:** Unique-Index (property, meter_type, serial_number) für Duplicate-Prevention
- Is default (max. 1 pro Property+Medium)
- Is active
- Initial reading value (optional; Decimal ≥ 0; einmalig als „vorheriger Stand", falls noch kein Reading existiert)
- Installed at (Datum)
- Removed at (Datum; muss ≥ Installed at sein oder leer)
- Notes (max. 1000)
- Aktion: Entfernen (Zeile löschen)

**Regeln**

- Mehrere Zähler pro Medium erlaubt.
- **Harte Validierung (DB-Constraint):** Postgres Partial Unique Constraint:
  ```sql
  UNIQUE (property_id, meter_type) WHERE is_default = TRUE
  ```
- **Transaktionale Default-Setzung:** Beim Setzen `is_default=true` werden alle anderen Defaults desselben Mediums auf `false` gesetzt.
- **Default-Meter Löschung:** Beim Löschen eines Default-Zählers wird **kein** neuer Default automatisch gesetzt. Property bleibt ohne Default für dieses Medium, bis User explizit einen anderen Meter als Default markiert.
- Gas-Einheit systemweit **kWh**.

---

## 4) UX & Mobile

- Stil wie übriges Portal; mobil einspaltig, ab md zwei Spalten.
- Zählerliste: kompakte Zeilen mit Badges (Default, Aktiv) und Icon je Medium.
- Aktionen unten sticky: **Speichern**, **Abbrechen**, **Archivieren/Löschen**.
- Leere Zustände mit klaren CTAs („+ Zähler hinzufügen“).
- Barrierefreiheit: Labels, Tastaturfokus, ausreichender Kontrast.

---

## 5) Archivieren/Löschen (Policies)

- Soft-Delete: Feld **is_archived** (Bool) + **archived_at**, **archived_by**.
- Standardlisten blenden archivierte Properties aus; Checkbox „Archivierte anzeigen" blendet sie ein (ausgegraute Zeilen).
- Hard-Delete nur ohne Abhängigkeiten (Units, Verträge, Zahlungen, Dokumente, Zähler, Readings). Bei Abhängigkeiten: Fehlermeldung und Option „Archivieren".
- **Archiv-Propagation:** Archivierte Properties und deren Zähler werden in **allen** Auswahl-Dropdowns ausgefiltert:
  - Zählerstands-Formular (Readings)
  - Dokument-Zuweisung
  - Vertrags-Assistenten
  - **Implementierung:** Alle QuerySets filtern `.filter(is_archived=False)` bzw. `.exclude(property__is_archived=True)`

---

## 6) API-Spezifikation (MVP, REST; JSON)

**API-Pfad-Konvention:** `/api/portal/properties/...`

- Grund: Konsistenz mit bestehendem API-Layout (`/api/...` für JSON, `/portal/...` für HTML)
- Permissions: `portal`-scoped (Session-based Auth wie übriges Portal)

Hinweis: „Keine Code-Snippets" – daher nur Endpunkte, Parameter und Semantik.

### 6.1 Properties

- GET `/api/portal/properties/`
  Parameter: query, city, postal_code, country, is_archived (default false), sort (name|city|created_at), order (asc|desc), page, page_size (default 25, max 100).
  Antwort: paginierte Liste mit Summary-Feldern (u. a. meters_count, updated_at).

- GET `/api/portal/properties/{id}/`
  Antwort: Property-Detail inkl. Zählerliste (siehe Felder).

- POST `/api/portal/properties/`
  Body: Stammdaten aus 3.1.
  Antwort: 201 mit Objekt (id).
  Hinweis: Zähler werden **nicht** im selben Call angelegt; UI speichert erst Property, danach Zähler (klarer 2-Step-Flow).

- PATCH `/api/portal/properties/{id}/`
  Body: Teilupdates der Stammdaten.
  Antwort: 200 mit Objekt.

- POST `/api/portal/properties/{id}/archive/` → 200 (archiviert).

- DELETE `/api/portal/properties/{id}/` → 204 (nur ohne Abhängigkeiten, sonst 409 mit Fehlertext).

### 6.2 Utility Meters (Property-Scope)

- POST `/api/portal/properties/{id}/meters/` → neuen Zähler anlegen.
- PATCH `/api/portal/properties/{id}/meters/{meter_id}/` → Felder ändern (inkl. Deaktivierung via `is_active=false`).
- DELETE `/api/portal/properties/{id}/meters/{meter_id}/` → Zähler entfernen.

**Meter-Delete Policy (CLARIFIED):**

- **Ohne Readings:** Hard-Delete erlaubt → 204 No Content
- **Mit Readings:** Hard-Delete verboten → 409 Conflict
  - Fehlermeldung: "Zähler kann nicht gelöscht werden, da bereits Zählerstände existieren. Bitte deaktivieren."
  - **Alternative Aktion:** Deaktivieren via `PATCH` mit `is_active=false` und `removed_at=today`
  - **UI-Hinweis:** Bei 409 automatisch Option "Zähler deaktivieren" anbieten

**HTTP-Status/Fehlertexte (Auszug)**

- 400: ungültige Felder/Validierung
- 401/403: fehlende/fehlende Rechte
- 404: nicht gefunden
- 409: Konflikt (z. B. doppelter Default, Abhängigkeiten beim Löschen)
- **422: semantischer Fehler** (Removed at vor Installed at)
  - **Implementierung:** Durch `custom_exception_handler` in `config.api.exception_handler` gemappt (DRF Default = 400)

**Auth/RBAC**

- Session-basiert wie übriges Portal.
- **Rollen & Endpoints:**
  - **View (GET):** Landlord, Staff, Property-Manager, Admin
  - **Create (POST):** Property-Manager, Admin
  - **Update (PATCH):** Property-Manager, Admin
  - **Archive (POST /archive/):** Property-Manager, Admin
  - **Delete (DELETE):** Admin only (aufgrund Dependency-Check)
  - **Implementierung:** `@permission_classes([IsAuthenticated, IsAdminOrPropertyManager])`

---

## 7) Performance & Daten

- Paging default 25; sortierbar nach name (Default asc), city, created_at.
- **DB-Indizes:**
  - `(name)` - für Sortierung
  - `(city)` - für Filter
  - `(postal_code)` - für Filter
  - `(is_archived)` - für Standard-Filter (exclude archived)
  - `(property_id, meter_type, is_default)` - für Default-Lookup
  - `(property_id, meter_type, is_active)` - für Active-Meter-Lookup
  - **Optional (Performance-Boost):** `GIN(name gin_trgm_ops)` - Trigram-Index für Fuzzy-Search via `pg_trgm` (bei großen Beständen >10k)
- **N+1 Prevention:** Property-Detail lädt Zähler in einem Query (`prefetch_related('utilitymeter_set')`).
- **Caching:**
  - Fragment-Cache für Property-Detail (Key: `property_detail_{id}`)
  - **Invalidierung:** Bei `Property.save()`, `.archive()`, `UtilityMeter.create()/.update()/.delete()`
  - TTL: 15 Minuten (900s)
- Ziel: P95 API-Antwort < 300 ms bei 10k Properties.

---

## 8) Sicherheit

- CSRF-Schutz für mutierende Requests.
- Serverseitige Validierung aller Felder; Whitelist für Country (DE, AT, CH); Normalize/Trim.
- **Rate-Limiting (Portal-API):**
  - **Mutierende Endpoints (POST/PATCH/DELETE):** 60 Requests/Minute pro User + IP (sliding window/token bucket)
  - **Lese-Endpoints (GET):** 240 Requests/Minute pro User + IP
  - **Burst:** Bis zu 10 Requests sofort, danach gleichmäßig geglättet
  - **Fehlercode:** 429 Too Many Requests mit `Retry-After` Header
  - **Staff-Ausnahme:** Erhöhtes Limit für `is_staff=True` (600/min mutating) für Bulk-Operationen, Migrations, Load-Tests
  - **IP-Erkennung:** Bei Reverse-Proxy/Load-Balancer muss `X-Forwarded-For` korrekt terminiert werden:
    - Nginx: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
    - Django: Custom Throttle mit `get_ident()` nutzt `X-Forwarded-For` Header
    - Fallback: `REMOTE_ADDR` wenn kein Proxy
  - **DRF-Implementierung:**
    ```python
    # settings.py
    REST_FRAMEWORK = {
        'DEFAULT_THROTTLE_CLASSES': [
            'landlord.throttles.PortalMutatingThrottle',  # 60/min (600/min für Staff)
            'landlord.throttles.PortalReadThrottle',      # 240/min
        ],
        'DEFAULT_THROTTLE_RATES': {
            'portal_mutating': '60/min',
            'portal_mutating_staff': '600/min',
            'portal_read': '240/min',
        }
    }
    # Views: throttle_classes = [PortalMutatingThrottle] oder [PortalReadThrottle]
    ```
- XSS-Schutz: alle Freitextfelder HTML-escapen; Länge begrenzen.
- Autorisierung pro Route gem. RBAC (siehe Kap. 6.2).

---

## 9) Audit & Monitoring

- Audit-Events für Property/Meter Create/Update/Archive/Delete mit changed_by, changed_at, Feld-Diff.
- Fehler-Logging und optionales Error-Tracking (z. B. Sentry).
- Metriken: Requests/Sek, P95 Latenz, Fehlerquote, Archivierungsrate.

---

## 10) Tests & Qualität

- Backend-Unit-Tests: Modelle, Validatoren, Policies (Ziel ≥ 85% Coverage).
- API-Tests: alle Endpunkte inkl. Fehlerpfade (Ziel ≥ 90% der Routen).
- E2E-Tests (Portal):

  1. Property anlegen (nur Name) → OK
  2. Zähler hinzufügen/ändern/löschen, inkl. doppelter Default → Fehlertext
  3. Archivieren → aus Liste weg; Filter zeigt es
  4. Hard-Delete ohne Abhängigkeiten → 204
  5. Mobile Smoke (iPhone/Pixel) → Sticky-Bar, Add/Remove

- Performance-Smoke: Liste 1k Properties → P95 < 300 ms.

---

## 11) Abhängigkeiten & Deployment

- Neue Felder: is_archived, archived_at, archived_by an Property.
- Indizes gemäß Kap. 7.
- Feature-Flag „properties_portal“ möglich (schrittweise Freigabe).
- Rollback: Deaktivieren des Menüpunktes + Revert Migration.

---

## 12) Akzeptanzkriterien (Checkliste)

- Menüpunkt **Gebäude** vorhanden; öffnet Übersicht mit Suche/Filter/Sort.
- Property-Anlegen speichert Felder aus 3.1; Redirect auf Detail.
- Property-Bearbeiten zeigt vorbefüllte Felder; **Zählerliste** unterstützt Add/Edit/Remove.
- Validierung verhindert doppelten Default je Medium.
- Archivierte Properties sind standardmäßig ausgeblendet; Filter „Archivierte anzeigen“ funktioniert.
- Hard-Delete verhält sich gemäß Policy und liefert sinnvolle Fehlermeldungen bei Abhängigkeiten.
- API-Statuscodes und Fehlermeldungen wie spezifiziert.
- Mobile-UX konsistent mit Portal.

---

## 13) Nicht-Ziele

- Units (eigenes Menü/Feature).
- Bulk-Import/Export, Kartenansicht, QR/OCR.
- Externe Provider-Sync.

---

## 14) Aufwand (aktualisiert)

- Views/Routes + Übersicht + Detail: 0.8–1.2 PT
- Zählerliste (dyn. Add/Remove, Validierungen): 0.8–1.5 PT
- Archiv/Hard-Delete + Abhängigkeitsprüfung: 0.5–0.8 PT
- API + Tests (Unit/API/E2E): 0.8–1.2 PT
  **Gesamt:** **2.9–4.7 PT** (inkl. Puffer)

---

## 15) Implementation Progress Tracker

**Status:** 🟡 In Progress
**Started:** 2025-10-20
**Target Completion:** TBD

### Phase 1: Core Models & Migrations (1.2 PT)

- [ ] 1.1 Add `is_archived`, `archived_at`, `archived_by` to Property model
- [ ] 1.2 Add `geo_lat`, `geo_lng` as DecimalField(9,6) with DB Check-Constraints (-90/+90, -180/+180)
- [ ] 1.3 Add Country choices (DE, AT, CH) with localization
- [ ] 1.4 Update all field validations (max lengths, constraints per Kap. 3.1/3.2)
- [ ] 1.5 Add Postgres Partial Unique Constraint: `UNIQUE (property_id, meter_type) WHERE is_default = TRUE`
- [ ] 1.6 Normalize `serial_number` to uppercase on save
- [ ] 1.7 Create migrations
- [ ] 1.8 Add DB indexes: (name), (city), (postal_code), (is_archived)
- [ ] 1.9 Add meter indexes: (property_id, meter_type, is_default), (property_id, meter_type, is_active)
- [ ] 1.10 Optional: Add Trigram index `GIN(name gin_trgm_ops)` via pg_trgm extension
- [ ] 1.11 Model unit tests (≥85% coverage)

**Progress:** 0/11 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 2: API Endpoints - Properties (1.3 PT)

- [ ] 2.1 GET `/api/portal/properties/` (List with pagination, filters, sort)
- [ ] 2.2 GET `/api/portal/properties/{id}/` (Detail with prefetch meters)
- [ ] 2.3 POST `/api/portal/properties/` (Create)
- [ ] 2.4 PATCH `/api/portal/properties/{id}/` (Update)
- [ ] 2.5 POST `/api/portal/properties/{id}/archive/` (Archive action)
- [ ] 2.6 DELETE `/api/portal/properties/{id}/` (Hard-Delete with dependency check)
- [ ] 2.7 Serializers with all validations (Country whitelist, Geo ranges, etc.)
- [ ] 2.8 RBAC permissions: `IsAdminOrPropertyManager` per endpoint
- [ ] 2.9 Throttling: `PortalMutatingThrottle` (60/min) & `PortalReadThrottle` (240/min)
- [ ] 2.10 API unit tests (≥90% routes, all HTTP status codes)

**Progress:** 0/10 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 3: API Endpoints - Meters (0.9 PT)

- [ ] 3.1 POST `/api/portal/properties/{id}/meters/` (Create meter)
- [ ] 3.2 PATCH `/api/portal/properties/{id}/meters/{meter_id}/` (Update meter)
- [ ] 3.3 DELETE `/api/portal/properties/{id}/meters/{meter_id}/` (Delete with Reading dependency check → 409)
- [ ] 3.4 Default-constraint validation (transactional: set others to false when setting new default)
- [ ] 3.5 Deactivate-instead-of-delete logic (UI hint on 409)
- [ ] 3.6 Meter serializers with all validations
- [ ] 3.7 API tests for all meter endpoints (create, update, delete, conflict cases)

**Progress:** 0/7 ⬜⬜⬜⬜⬜⬜⬜

### Phase 4: Portal Views - List & Create (0.9 PT)

- [ ] 4.1 Route `/portal/properties/` (List view)
- [ ] 4.2 Route `/portal/properties/new` (Create form)
- [ ] 4.3 Search/Filter UI (query, city, postal_code, country, is_archived)
- [ ] 4.4 Sort UI (name, city, created_at)
- [ ] 4.5 Pagination UI (25 per page)
- [ ] 4.6 "Archivierte anzeigen" checkbox
- [ ] 4.7 Mobile-responsive layout
- [ ] 4.8 Empty states

**Progress:** 0/8 ⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 5: Portal Views - Detail & Edit (1.0 PT)

- [ ] 5.1 Route `/portal/properties/{id}/` (Detail/Edit view)
- [ ] 5.2 Property form (all fields from 3.1)
- [ ] 5.3 Meter list inline (dynamic add/edit/remove)
- [ ] 5.4 Meter form fields (all from 3.2)
- [ ] 5.5 Default-badge UI
- [ ] 5.6 Active/Inactive badge UI
- [ ] 5.7 Sticky action bar (Save, Cancel, Archive, Delete)
- [ ] 5.8 Client-side validations
- [ ] 5.9 Unsaved changes warning

**Progress:** 0/9 ⬜⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 6: Archive & Delete Logic (0.6 PT)

- [ ] 6.1 Archive action (soft-delete)
- [ ] 6.2 Dependency check for hard-delete (Units, Contracts, Payments, Documents, Readings)
- [ ] 6.3 409 Conflict handling with user-friendly messages
- [ ] 6.4 UI confirmation dialogs
- [ ] 6.5 Meter delete with Reading check
- [ ] 6.6 "Deaktivieren statt Löschen" option

**Progress:** 0/6 ⬜⬜⬜⬜⬜⬜

### Phase 7: Security & Performance (0.5 PT)

- [ ] 7.1 CSRF protection
- [ ] 7.2 Rate limiting (60/min mutating, 240/min read)
- [ ] 7.3 XSS protection (HTML escape)
- [ ] 7.4 RBAC authorization checks
- [ ] 7.5 N+1 query prevention (prefetch meters)
- [ ] 7.6 Cache strategy (fragment cache + invalidation)
- [ ] 7.7 DB indexes applied

**Progress:** 0/7 ⬜⬜⬜⬜⬜⬜⬜

### Phase 8: Testing & QA (1.0 PT)

- [ ] 8.1 Backend unit tests (models, validators, services) → ≥85%
- [ ] 8.2 API tests (all endpoints, error cases) → ≥90%
- [ ] 8.3 E2E Test 1: Create Property (name only) + Add meter
- [ ] 8.4 E2E Test 2: Double-default validation
- [ ] 8.5 E2E Test 3: Archive + Filter
- [ ] 8.6 E2E Test 4: Hard-delete without dependencies
- [ ] 8.7 E2E Test 5: Mobile smoke (iPhone/Pixel)
- [ ] 8.8 Performance smoke (1k Properties < 300ms P95)
- [ ] 8.9 Coverage report generation
- [ ] 8.10 Fix all failing tests

**Progress:** 0/10 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 9: Audit & Monitoring (0.4 PT)

- [ ] 9.1 Audit trail: Property create/update/archive/delete
- [ ] 9.2 Audit trail: Meter create/update/delete
- [ ] 9.3 Field-diff logging (JSON format)
- [ ] 9.4 Error logging setup
- [ ] 9.5 Metrics collection (requests, latency, errors)

**Progress:** 0/5 ⬜⬜⬜⬜⬜

### Phase 10: Documentation & Deployment (0.3 PT)

- [ ] 10.1 Migration guide
- [ ] 10.2 Rollback plan
- [ ] 10.3 Feature flag setup (optional)
- [ ] 10.4 User documentation (README/Wiki)
- [ ] 10.5 Code review & merge

**Progress:** 0/5 ⬜⬜⬜⬜⬜

---

**Overall Progress:** 0/75 Tasks (0%)

**Phase Summary:**

- ⬜ Phase 1: Not Started (1.2 PT) - 11 tasks
- ⬜ Phase 2: Not Started (1.3 PT) - 10 tasks
- ⬜ Phase 3: Not Started (0.9 PT) - 7 tasks
- ⬜ Phase 4: Not Started (0.9 PT) - 8 tasks
- ⬜ Phase 5: Not Started (1.0 PT) - 9 tasks
- ⬜ Phase 6: Not Started (0.6 PT) - 6 tasks
- ⬜ Phase 7: Not Started (0.5 PT) - 7 tasks
- ⬜ Phase 8: Not Started (1.0 PT) - 10 tasks
- ⬜ Phase 9: Not Started (0.4 PT) - 5 tasks
- ⬜ Phase 10: Not Started (0.3 PT) - 5 tasks

**Total Estimated Effort:** 8.1 PT (+0.4 PT vs. v1.2 due to clarifications)

**Implementation Strategy:**

1. **Backend-First:** Phases 1-3 (Models + API) = 3.4 PT
2. **Frontend:** Phases 4-5 (Views + UI) = 1.9 PT
3. **Polish:** Phases 6-7 (Business Logic + Security) = 1.1 PT
4. **Quality:** Phases 8-10 (Testing + Deployment) = 1.7 PT

---

## 16) Changelog

### v1.3.1 (2025-10-20) - GPT-5 Review Clarifications ✅

**Ergänzungen nach GPT-5 Code-Review:**

- ✅ **Default-Meter Löschung:** Explizit dokumentiert, dass beim Löschen eines Default-Zählers KEIN automatisches Reassignment erfolgt (Kap. 3.2)
- ✅ **X-Forwarded-For:** Throttling-Implementation nutzt `X-Forwarded-For` Header für korrekte IP-Erkennung hinter Reverse-Proxy/Load-Balancer (Kap. 8)
- ✅ **Staff Throttle-Ausnahme:** Erhöhtes Limit (600/min) für `is_staff=True` User für Bulk-Operationen, Migrations, Load-Tests (Kap. 8)
- ✅ **Nginx-Konfiguration:** Beispiel für `proxy_set_header X-Forwarded-For` dokumentiert (Kap. 8)
- ✅ **TODO-Updates:** Implementation-Details für Custom Throttle `get_ident()` und Default-Delete-Tests ergänzt

**Technische Details:**
- Custom `get_ident()` in Throttle-Klassen für X-Forwarded-For Support
- Nginx-Config: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
- Test: `test_meter_delete_default_no_auto_reassign()` für explizites Verhalten

---

### v1.3 (2025-10-20) - Final Spec - Production Ready ✅

**Technical Clarifications:**

- ✅ **Scope-Klarstellung:** Building-Level Meters only; Unit-Meters folgen in separater Spec
- ✅ **Geo-Felder:** DecimalField(9,6) mit DB Check-Constraints (-90/+90, -180/+180)
- ✅ **Serial Number:** Normalized uppercase storage; optional Unique-Index für Duplicate-Prevention
- ✅ **Default-Constraint:** Postgres Partial Unique Constraint `WHERE is_default = TRUE`
- ✅ **Default-Setzung:** Transaktional (set others to false when setting new default)

**API-Konvention:**

- ✅ **Pfade:** `/api/portal/properties/...` (statt `/portal/api/...`)
- ✅ **Begründung:** Konsistenz mit `/api/...` = JSON, `/portal/...` = HTML
- ✅ **RBAC Details:** Endpoints pro Rolle dokumentiert (View/Create/Update/Archive/Delete)
- ✅ **422 Status Code:** Durch `custom_exception_handler` gemappt (DRF Default = 400)

**Performance & Security:**

- ✅ **Trigram-Index:** Optional `GIN(name gin_trgm_ops)` für Fuzzy-Search bei >10k Properties
- ✅ **Cache-Invalidierung:** Explizit bei Property.save(), .archive() und Meter CRUD
- ✅ **N+1 Prevention:** `prefetch_related('utilitymeter_set')` dokumentiert
- ✅ **Rate-Limiting DRF:** Code-Snippet für `PortalMutatingThrottle` & `PortalReadThrottle`
- ✅ **Archiv-Propagation:** Alle QuerySets filtern `is_archived=False` in Dropdowns

**Implementation Tracker:**

- ✅ **Phase 1:** 11 tasks (statt 6) - +5 für Geo, Constraints, Normalization
- ✅ **Phase 2:** 10 tasks (statt 8) - +2 für RBAC, Throttling
- ✅ **Phase 3:** 7 tasks (statt 6) - +1 für Deactivate-Logic
- ✅ **Total:** 75 tasks, 8.1 PT (statt 70 tasks, 7.7 PT)
- ✅ **Strategy:** Backend-First (3.4 PT), Frontend (1.9 PT), Polish (1.1 PT), Quality (1.7 PT)

**Recommendations Integrated:**

1. ✅ Zähler-Ebene vs. Readings-Modell geklärt (Building-Level first)
2. ✅ API-Pfadkonvention korrigiert (`/api/portal/...`)
3. ✅ 422-Rückgaben technisch verankert (custom_exception_handler)
4. ✅ Default-Einzigkeit "hart" gemacht (Postgres Constraint + Transaction)
5. ✅ Indices & Trigram-Suche dokumentiert
6. ✅ Lösch-/Archiv-Propagation explizit (alle Dropdowns filtern)
7. ✅ RBAC konkretisiert (Endpoints je Rolle)
8. ✅ Rate-Limits DRF-Konfiguration hinzugefügt
9. ✅ Caching-Invalidierung klar notiert
10. ✅ Geo-Felder mit DecimalField(9,6) + DB-Constraints
11. ✅ Serial-Number Normalization (uppercase)
12. ✅ Progress-Schätzung realistisch (8.1 PT, Backend-First)

### v1.2 (2025-10-20) - Clarifications Added

- ✅ **Country-Liste:** Initial scope DE, AT, CH; ISO-3166-1-alpha-2; erweiterbar
- ✅ **Meter-Delete Policy:** Hard-Delete nur ohne Readings; sonst 409 mit Deaktivierungs-Option
- ✅ **Rate Limiting:** 60/min mutating, 240/min read; Burst 10; 429 + Retry-After
- ✅ **Implementation Progress Tracker:** 10 Phasen, 70 Tasks, 7.7 PT
- ✅ **Meter-Delete Policy:** Hard-Delete nur ohne Readings; sonst 409 mit Deaktivierungs-Option
- ✅ **Rate Limiting:** 60/min mutating, 240/min read; Burst 10; 429 + Retry-After
- ✅ **Implementation Progress Tracker:** 10 Phasen, 70 Tasks, 7.7 PT

### v1.1 (2025-10-20) - API + Policies

- ✅ API-Spezifikation hinzugefügt (Kap. 6)
- ✅ Performance-Details (Kap. 7)
- ✅ Security-Kapitel (Kap. 8)
- ✅ Tests erweitert (Kap. 10)
- ✅ Aufwand aktualisiert: 2.9-4.7 PT

### v1.0 (2025-10-20) - Initial Spec

- ✅ Scope, Ziele, Felder definiert
- ✅ UX/Mobile beschrieben
- ✅ Policies skizziert

---
