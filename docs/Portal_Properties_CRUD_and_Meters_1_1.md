# UVM – Gebäude (Properties) : Portal-CRUD + Zähler (Stammdaten)

Version: **1.2 (Spec + API + Policies + Clarifications)**
Datum: **2025-10-20**
Owner: **Landlord / Property Management**
Scope: **Portal-Modul „Gebäude"** mit Property-CRUD und Zählerverwaltung.
Hinweis: **Units sind out of scope** (separate Spec). Django-Admin bleibt unverändert als „uncut Admin".

---

## 1) Ziel & Nutzen

* Properties im Portal mobilfreundlich **anlegen/anzeigen/bearbeiten/archivieren/löschen**.
* Je Property **beliebig viele Zähler** verwalten (add/edit/remove).
* Zählerdaten dienen der **automatischen Vorbefüllung** im Zählerstands-Formular.

---

## 2) Navigation

* Neuer Top-Nav-Button: **Gebäude** (Pfad: `/portal/properties/`).
* Seiten:

  1. Übersicht `/portal/properties/` (Liste mit Suche/Filter/Sort/Paging)
  2. Anlegen `/portal/properties/new`
  3. Detail & Bearbeiten `/portal/properties/{id}/`
  4. Optionaler Bestätigungsdialog fürs Archivieren/Löschen

---

## 3) Felder (exakt, ohne Spekulation)

### 3.1 Property – Stammdaten

* Name (Pflicht)
* Street
* Postal code
* City
* Country (Dropdown; Default: DE; ISO-3166-1-alpha-2)
  - **Initial Scope:** DE, AT, CH
  - **Storage:** 2-letter code ("DE", "AT", "CH")
  - **Display:** Localized (z.B. "Deutschland", "Österreich", "Schweiz")
  - **Future:** Erweiterbar auf vollständige ISO-Liste ohne Migration
* Geo lat
* Geo lng
* Notes

**Validierungen**

* Name: max. 200 Zeichen.
* Postal code: DE genau 5 Ziffern; sonst alphanumerisch bis 10 (künftige Länderspezifika möglich).
* Geo lat: −90.0 bis +90.0; Geo lng: −180.0 bis +180.0.
* Notes: max. 2000 Zeichen.

### 3.2 Zähler (Stammdaten) – pro Eintrag

* Meter type (Kaltwasser, Warmwasser, Strom, Gas (kWh))
* Serial number (optional; max. 50; Zeichen: A-Z, a-z, 0-9, Bindestrich, Slash)
* Is default (max. 1 pro Property+Medium)
* Is active
* Initial reading value (optional; Decimal ≥ 0; einmalig als „vorheriger Stand“, falls noch kein Reading existiert)
* Installed at (Datum)
* Removed at (Datum; muss ≥ Installed at sein oder leer)
* Notes (max. 1000)
* Aktion: Entfernen (Zeile löschen)

**Regeln**

* Mehrere Zähler pro Medium erlaubt.
* Harte Validierung: pro (Property, Meter type) **genau ein** Default zulässig.
* Gas-Einheit systemweit **kWh**.

---

## 4) UX & Mobile

* Stil wie übriges Portal; mobil einspaltig, ab md zwei Spalten.
* Zählerliste: kompakte Zeilen mit Badges (Default, Aktiv) und Icon je Medium.
* Aktionen unten sticky: **Speichern**, **Abbrechen**, **Archivieren/Löschen**.
* Leere Zustände mit klaren CTAs („+ Zähler hinzufügen“).
* Barrierefreiheit: Labels, Tastaturfokus, ausreichender Kontrast.

---

## 5) Archivieren/Löschen (Policies)

* Soft-Delete: Feld **is_archived** (Bool) + **archived_at**, **archived_by**.
* Standardlisten blenden archivierte Properties aus; Checkbox „Archivierte anzeigen“ blendet sie ein (ausgegraute Zeilen).
* Hard-Delete nur ohne Abhängigkeiten (Units, Verträge, Zahlungen, Dokumente, Zähler, Readings). Bei Abhängigkeiten: Fehlermeldung und Option „Archivieren“.
* Archivierte Properties und deren Zähler werden in Auswahl-Dropdowns (z. B. Zählerstand erfassen) **nicht** angeboten.

---

## 6) API-Spezifikation (MVP, REST; JSON)

Hinweis: „Keine Code-Snippets“ – daher nur Endpunkte, Parameter und Semantik.

### 6.1 Properties

* GET `/portal/api/properties`
  Parameter: query, city, postal_code, country, is_archived (default false), sort (name|city|created_at), order (asc|desc), page, page_size (default 25, max 100).
  Antwort: paginierte Liste mit Summary-Feldern (u. a. meters_count, updated_at).

* GET `/portal/api/properties/{id}`
  Antwort: Property-Detail inkl. Zählerliste (siehe Felder).

* POST `/portal/api/properties`
  Body: Stammdaten aus 3.1.
  Antwort: 201 mit Objekt (id).
  Hinweis: Zähler werden **nicht** im selben Call angelegt; UI speichert erst Property, danach Zähler (klarer 2-Step-Flow).

* PATCH `/portal/api/properties/{id}`
  Body: Teilupdates der Stammdaten.
  Antwort: 200 mit Objekt.

* POST `/portal/api/properties/{id}/archive` → 200 (archiviert).

* DELETE `/portal/api/properties/{id}` → 204 (nur ohne Abhängigkeiten, sonst 409 mit Fehlertext).

### 6.2 Utility Meters (Property-Scope)

* POST `/portal/api/properties/{id}/meters` → neuen Zähler anlegen.
* PATCH `/portal/api/properties/{id}/meters/{meter_id}` → Felder ändern (inkl. Deaktivierung via `is_active=false`).
* DELETE `/portal/api/properties/{id}/meters/{meter_id}` → Zähler entfernen.

**Meter-Delete Policy (CLARIFIED):**
- **Ohne Readings:** Hard-Delete erlaubt → 204 No Content
- **Mit Readings:** Hard-Delete verboten → 409 Conflict
  - Fehlermeldung: "Zähler kann nicht gelöscht werden, da bereits Zählerstände existieren. Bitte deaktivieren."
  - **Alternative Aktion:** Deaktivieren via `PATCH` mit `is_active=false` und `removed_at=today`
  - **UI-Hinweis:** Bei 409 automatisch Option "Zähler deaktivieren" anbieten

**HTTP-Status/Fehlertexte (Auszug)**

* 400: ungültige Felder/Validierung
* 401/403: fehlende/fehlende Rechte
* 404: nicht gefunden
* 409: Konflikt (z. B. doppelter Default, Abhängigkeiten beim Löschen)
* 422: semantischer Fehler (Removed at vor Installed at)

**Auth/RBAC**

* Session-basiert wie übriges Portal; Rollen: View = Landlord/Staff, CRUD = Admin/Property-Manager.

---

## 7) Performance & Daten

* Paging default 25; sortierbar nach name (Default asc), city, created_at.
* DB-Indizes: (name), (city), (postal_code), (is_archived), (property_id, meter_type, is_default), (property_id, meter_type, is_active).
* Vermeidung N+1: Property-Detail lädt Zähler in einem Query (prefetch/join).
* Optionales Cache-Fragment für Property-Detail; Invalidation bei Save/Archive/Meter-Änderung.
* Ziel: P95 API-Antwort < 300 ms bei 10k Properties.

---

## 8) Sicherheit

* CSRF-Schutz für mutierende Requests.
* Serverseitige Validierung aller Felder; Whitelist für Country (DE, AT, CH); Normalize/Trim.
* **Rate-Limiting (Portal-API):**
  - **Mutierende Endpoints (POST/PATCH/DELETE):** 60 Requests/Minute pro User + IP (sliding window/token bucket)
  - **Lese-Endpoints (GET):** 240 Requests/Minute pro User + IP
  - **Burst:** Bis zu 10 Requests sofort, danach gleichmäßig geglättet
  - **Fehlercode:** 429 Too Many Requests mit `Retry-After` Header
* XSS-Schutz: alle Freitextfelder HTML-escapen; Länge begrenzen.
* Autorisierung pro Route gem. RBAC.

---

## 9) Audit & Monitoring

* Audit-Events für Property/Meter Create/Update/Archive/Delete mit changed_by, changed_at, Feld-Diff.
* Fehler-Logging und optionales Error-Tracking (z. B. Sentry).
* Metriken: Requests/Sek, P95 Latenz, Fehlerquote, Archivierungsrate.

---

## 10) Tests & Qualität

* Backend-Unit-Tests: Modelle, Validatoren, Policies (Ziel ≥ 85% Coverage).
* API-Tests: alle Endpunkte inkl. Fehlerpfade (Ziel ≥ 90% der Routen).
* E2E-Tests (Portal):

  1. Property anlegen (nur Name) → OK
  2. Zähler hinzufügen/ändern/löschen, inkl. doppelter Default → Fehlertext
  3. Archivieren → aus Liste weg; Filter zeigt es
  4. Hard-Delete ohne Abhängigkeiten → 204
  5. Mobile Smoke (iPhone/Pixel) → Sticky-Bar, Add/Remove
* Performance-Smoke: Liste 1k Properties → P95 < 300 ms.

---

## 11) Abhängigkeiten & Deployment

* Neue Felder: is_archived, archived_at, archived_by an Property.
* Indizes gemäß Kap. 7.
* Feature-Flag „properties_portal“ möglich (schrittweise Freigabe).
* Rollback: Deaktivieren des Menüpunktes + Revert Migration.

---

## 12) Akzeptanzkriterien (Checkliste)

* Menüpunkt **Gebäude** vorhanden; öffnet Übersicht mit Suche/Filter/Sort.
* Property-Anlegen speichert Felder aus 3.1; Redirect auf Detail.
* Property-Bearbeiten zeigt vorbefüllte Felder; **Zählerliste** unterstützt Add/Edit/Remove.
* Validierung verhindert doppelten Default je Medium.
* Archivierte Properties sind standardmäßig ausgeblendet; Filter „Archivierte anzeigen“ funktioniert.
* Hard-Delete verhält sich gemäß Policy und liefert sinnvolle Fehlermeldungen bei Abhängigkeiten.
* API-Statuscodes und Fehlermeldungen wie spezifiziert.
* Mobile-UX konsistent mit Portal.

---

## 13) Nicht-Ziele

* Units (eigenes Menü/Feature).
* Bulk-Import/Export, Kartenansicht, QR/OCR.
* Externe Provider-Sync.

---

## 14) Aufwand (aktualisiert)

* Views/Routes + Übersicht + Detail: 0.8–1.2 PT
* Zählerliste (dyn. Add/Remove, Validierungen): 0.8–1.5 PT
* Archiv/Hard-Delete + Abhängigkeitsprüfung: 0.5–0.8 PT
* API + Tests (Unit/API/E2E): 0.8–1.2 PT
  **Gesamt:** **2.9–4.7 PT** (inkl. Puffer)

---

## 15) Implementation Progress Tracker

**Status:** 🟡 In Progress  
**Started:** 2025-10-20  
**Target Completion:** TBD

### Phase 1: Core Models & Migrations (1.0 PT)
- [ ] 1.1 Add `is_archived`, `archived_at`, `archived_by` to Property model
- [ ] 1.2 Add Country choices (DE, AT, CH)
- [ ] 1.3 Update field validations (max lengths, constraints)
- [ ] 1.4 Create migrations
- [ ] 1.5 Add DB indexes (name, city, postal_code, is_archived)
- [ ] 1.6 Model unit tests (≥85% coverage)

**Progress:** 0/6 ⬜⬜⬜⬜⬜⬜

### Phase 2: API Endpoints - Properties (1.2 PT)
- [ ] 2.1 GET `/portal/api/properties/` (List with pagination)
- [ ] 2.2 GET `/portal/api/properties/{id}/` (Detail)
- [ ] 2.3 POST `/portal/api/properties/` (Create)
- [ ] 2.4 PATCH `/portal/api/properties/{id}/` (Update)
- [ ] 2.5 POST `/portal/api/properties/{id}/archive` (Archive)
- [ ] 2.6 DELETE `/portal/api/properties/{id}/` (Hard-Delete)
- [ ] 2.7 Serializers with validations
- [ ] 2.8 API unit tests (≥90% routes)

**Progress:** 0/8 ⬜⬜⬜⬜⬜⬜⬜⬜

### Phase 3: API Endpoints - Meters (0.8 PT)
- [ ] 3.1 POST `/portal/api/properties/{id}/meters/` (Create)
- [ ] 3.2 PATCH `/portal/api/properties/{id}/meters/{meter_id}/` (Update)
- [ ] 3.3 DELETE `/portal/api/properties/{id}/meters/{meter_id}/` (Delete with Reading check)
- [ ] 3.4 Default-constraint validation (max 1 per Property+Medium)
- [ ] 3.5 Meter serializers
- [ ] 3.6 API tests for meters

**Progress:** 0/6 ⬜⬜⬜⬜⬜⬜

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

**Overall Progress:** 0/70 Tasks (0%)

**Phase Summary:**
- ⬜ Phase 1: Not Started (1.0 PT)
- ⬜ Phase 2: Not Started (1.2 PT)
- ⬜ Phase 3: Not Started (0.8 PT)
- ⬜ Phase 4: Not Started (0.9 PT)
- ⬜ Phase 5: Not Started (1.0 PT)
- ⬜ Phase 6: Not Started (0.6 PT)
- ⬜ Phase 7: Not Started (0.5 PT)
- ⬜ Phase 8: Not Started (1.0 PT)
- ⬜ Phase 9: Not Started (0.4 PT)
- ⬜ Phase 10: Not Started (0.3 PT)

**Total Estimated Effort:** 7.7 PT

---

## 16) Changelog

### v1.2 (2025-10-20) - Clarifications Added
- ✅ **Country-Liste:** Initial scope DE, AT, CH; ISO-3166-1-alpha-2; erweiterbar
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
