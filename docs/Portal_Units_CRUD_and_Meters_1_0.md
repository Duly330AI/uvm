# UVM – **Wohnungen (Units)** : Portal-CRUD + **Zähler (Stammdaten)**

**Version:** 1.0 (Spec)
**Datum:** 2025-10-21
**Owner:** Landlord / Unit Management
**Scope:** Neues Portal-Modul **„Wohnungen"** (Units) mit **CRUD** und **Zählerverwaltung** **auf Unit-Ebene**.
**Hinweis:** Properties werden separat in _Portal_Properties_CRUD_and_Meters_1_1.md_ spezifiziert. Django-Admin bleibt unverändert als „uncut Admin".

**Implementierungs-Status:** ✅ **COMPLETED (2025-10-21)**

---

## 📊 Implementierungs-Progress

### ✅ Phase 1: Model-Migration (COMPLETED - 2025-10-21)

- ✅ Unit-Model erweitert mit `is_archived`, `archived_at`, `archived_by`
- ✅ `archive(user)` Methode hinzugefügt
- ✅ `area_sqm` Validator `MinValueValidator(0)` hinzugefügt
- ✅ Index auf `is_archived` erstellt
- ✅ Migration `0024_unit_archive_fields_phase1.py` erstellt & angewendet

### ✅ Phase 2: Unit-Views & Templates (COMPLETED - 2025-10-21)

- ✅ `UnitListView` erstellt (mit Filter, Search, Sort, Pagination)
- ✅ `UnitDetailView` erstellt (mit Meters & Tenants)
- ✅ `UnitCreateView` erstellt (nur nicht-archivierte Properties)
- ✅ `UnitUpdateView` erstellt
- ✅ Templates: `units_list.html` (Desktop Table + Mobile Cards)
- ✅ Templates: `unit_form.html` (Responsive Form)
- ✅ Templates: `unit_detail.html` (mit Meter-Liste Placeholder)
- ✅ URLs registriert: `/portal/units/`, `/portal/units/new`, `/portal/units/{id}/`, `/portal/units/{id}/edit`
- ✅ Import von Unit in views.py hinzugefügt
- ✅ **Tests:** 229 passed ✅

### ✅ Phase 3: Unit-Meter CRUD Views (COMPLETED - 2025-10-21)

- ✅ `UnitMeterCreateView` erstellt mit `scope_type='unit'` Setzung
- ✅ `UnitMeterUpdateView` erstellt
- ✅ **Validation:** Max 1 Default pro (Unit, Meter-Type) implementiert
- ✅ Template: `unit_meter_form.html` (Responsive, Info-Box mit Hinweisen)
- ✅ `unit_detail.html` aktualisiert: Meter-Buttons aktiviert, Empty-State mit CTA
- ✅ URLs registriert: `/portal/units/{id}/meters/new`, `/portal/units/{id}/meters/{meter_id}/edit`
- ✅ Import: `UnitMeterCreateView`, `UnitMeterUpdateView` in urls.py
- ✅ **Tests:** 229 passed ✅

### ✅ Phase 4: Unit API Endpoints (COMPLETED - 2025-10-21)

- ✅ **Serializers:** `units_serializers.py` erstellt
  - `UnitListSerializer`: property_name, meters_count (annotated)
  - `UnitDetailSerializer`: Mit meters (nested), archived fields
  - `UnitCreateSerializer`: Property-Archive-Validierung
  - `UnitUpdateSerializer`: Property-Archive-Validierung
- ✅ **API Views:** `units.py` erstellt (7 Endpoints)
  - `UnitListAPIView`: Filter (is_archived, property_id, is_active, query), Sort, Pagination (25/page)
  - `UnitDetailAPIView`: Mit prefetch (property, utility_meters)
  - `UnitCreateAPIView`: Admin-only
  - `UnitUpdateAPIView`: Admin-only, PATCH support
  - `UnitDeleteAPIView`: Dependency-Check (Tenants, Meters, Issues, Contracts) → 409 Conflict
  - `UnitArchiveAPIView`: Soft-delete via archive(user)
  - `UnitUnarchiveAPIView`: Check Property-Archive-Status
- ✅ **URLs:** `/api/portal/units/` + CRUD + archive/unarchive
- ✅ **Throttling:** PortalReadThrottle (100/h), PortalWriteThrottle (50/h)
- ✅ **Permissions:** IsAuthenticated (List/Detail), IsAdminUser (Create/Update/Delete)
- ✅ **Tests:** 229 passed ✅

### ✅ Phase 5: Unit-Meter API Endpoints (COMPLETED - 2025-10-21)

- ✅ **API Views:** `unit_meters.py` erstellt (5 Endpoints)
  - `UnitMeterListAPIView`: Filter scope_type='unit', Sort by meter_type, is_default, is_active
  - `UnitMeterCreateAPIView`: scope_type='unit' auto-set, unit_id from URL
  - `UnitMeterDetailAPIView`: Single meter detail
  - `UnitMeterUpdateAPIView`: Transactional default-handling, auto-set removed_at
  - `UnitMeterDeleteAPIView`: Reading-Check (UtilityReading-Dependency) → 409 ValidationError
- ✅ **Default-Constraint:** Transactional clearance of other defaults before save
- ✅ **Reading-Dependency:** Meter-Type-Mapping (cold_water → water_cold) für Reading-Check
- ✅ **URLs:** `/api/portal/units/{unit_id}/meters/` + CRUD
- ✅ **Reuse:** Nutzt `UtilityMeterSerializer`, `UtilityMeterCreateSerializer`, `UtilityMeterUpdateSerializer` von properties
- ✅ **Tests:** 229 passed ✅

### ⏳ Phase 5: Unit-Meter API Endpoints (TODO)

### ✅ Phase 6: Tests (COMPLETED - 2025-10-21)

**Model-Tests (test_unit_model.py - 11 Tests):**

- ✅ Create with all fields
- ✅ Archive sets all fields (is_archived, archived_at, archived_by)
- ✅ Archive idempotent (can be called multiple times)
- ✅ area_sqm validation: positive, zero, negative
- ✅ **str** representation
- ✅ Property relationship & CASCADE delete
- ✅ Optional fields (floor, rooms, area_sqm, notes)
- ✅ is_archived index in DB

**API-Tests (test_unit_api.py - 25 Tests):**

- ✅ List: Authentication, Pagination (25/page), Filter (property_id, is_active, archived), Search (unit_label), Sort
- ✅ Detail: Authentication, All fields, Nested meters
- ✅ Create: Admin-only, Required fields, Archived-property validation
- ✅ Update: Admin-only, Success
- ✅ Archive: Success, Idempotent (already archived)
- ✅ Unarchive: Success, Archived-property check
- ✅ Delete: Success (no dependencies), Dependency-check (meters)

**Test-Ergebnisse:**
✅ **265 Tests passed (+36 neue Unit-Tests)**
✅ 11 Model-Tests
✅ 25 API-Tests
✅ Keine Regressions

**Bugfixes während Tests:**

- Archive/Unarchive Views: `http_method_names = ['post']` + `post()` statt `update()` (405 → 200)

### ✅ Phase 7: Navigation & Finalisierung (COMPLETED - 2025-10-21)

**Navigation (portal/base.html):**

- ✅ "Wohnungen"-Button zur Top-Nav hinzugefügt (zwischen "Gebäude" und "Reports")
- ✅ Mobile-responsive (whitespace-nowrap, flex-wrap)

**Dokumentation:**

- ✅ Portal_Units_CRUD_and_Meters_1_0.md vollständig aktualisiert
- ✅ Alle 7 Phasen dokumentiert
- ✅ Test-Ergebnisse & Bugfixes dokumentiert

**Implementierungs-Status:**
✅ **7/7 Phasen abgeschlossen (100%)**

---

## 1) Ziel & Nutzen

- **Wohnungen** direkt im **Portal** mobilfreundlich **anlegen/anzeigen/bearbeiten/archivieren/löschen**.
- Je Unit **beliebig viele Zähler** (Kaltwasser, Warmwasser, Strom, Gas in kWh) **hinzufügen/ändern/entfernen**.
- Unit-Zähler dienen der **automatischen Vorbefüllung** im Formular „Zählerstand erfassen“ (Wohnungszähler-Gruppe).

---

## 2) Navigation & Seiten

- **Neuer Top-Nav-Button:** **Wohnungen** (Alternative: „Units“)
- **Pfad:** `/portal/units/`
- **Seiten:**

  1. **Übersicht** `/portal/units/` – Liste mit Suche/Filter/Sort/Paging
  2. **Anlegen** `/portal/units/new`
  3. **Detail & Bearbeiten** `/portal/units/{id}/`
  4. Optionaler **Archivieren/Löschen**-Dialog

> **Auswahl „Property“**: In Create/Edit nur **nicht archivierte** Properties auswählbar (analog Property-Spec; archivierte werden in Portaldropdowns nicht angeboten).

---

## 3) Felder (exakt, ohne Spekulation)

### 3.1 Unit – Stammdaten

**⚠️ Hinweis:** Die Felder `is_archived`, `archived_at`, `archived_by` sind aktuell **NICHT** im Model und müssen per **Migration hinzugefügt** werden (analog zu Property).

- **Property** _(Pflicht; Auswahl)_
- **Unit label**
- **Floor** _(Text; max. 50 Zeichen; optional; z.B. "EG", "1. OG", "UG")_
- **Rooms**
- **Area sqm**
- **Notes**
- **Is active** _(Bool)_
- **Is archived** _(Bool; default=False; **NEU per Migration**)_
- **Archived at** _(DateTime; nullable; **NEU per Migration**)_
- **Archived by** _(FK User; nullable; **NEU per Migration**)_

**Validierungen**

- Property: muss existieren & nicht archiviert sein.
- Unit label: max. 100 Zeichen.
- Floor: Text, max. 50 Zeichen (optional; erlaubt "EG", "1. OG", "UG", etc.).
- Rooms: Ganzzahl (optional).
- Area sqm: Decimal ≥ 0 (optional). **⚠️ Validator `MinValueValidator(0)` muss zum Model hinzugefügt werden.**
- Notes: max. 2000 Zeichen. **⚠️ MaxLengthValidator in Form (TextField hat keine max_length).**

> **Nicht gefordert / kein Zwang:** keine globale Eindeutigkeit des _Unit label_ (Unique-Regel kann später ergänzt werden).

### 3.2 Zähler (Stammdaten) – **Unit-Scope**

- **Meter type** _(Medium)_: **Kaltwasser**, **Warmwasser**, **Strom**, **Gas (kWh)**

**Technische Werte (UtilityMeter.MeterType):**

- `cold_water` (Kaltwasser)
- `hot_water` (Warmwasser)
- `electricity` (Strom)
- `gas` (Gas in kWh)

**⚠️ Wichtig:** Bei Vorbefüllung in "Zählerstand erfassen" muss Mapping zu `UtilityReading.MeterType` beachtet werden:

- `cold_water → water_cold`
- `hot_water → water_hot`
- `electricity → electricity`
- `gas → gas`

* **Serial number** _(optional; max. 50; erlaubte Zeichen: A–Z, a–z, 0–9, `-`, `/`)_
* **Is default** _(Standardzähler; **max. 1 pro Unit+Medium**)_
* **Is active**
* **Initial reading value** _(optional; Decimal ≥ 0; wird **einmalig** als „vorheriger Stand" verwendet, falls noch kein Reading existiert)_
* **Installed at** _(Datum)_
* **Removed at** _(Datum; **≥ Installed at** oder leer)_
* **Notes** _(max. 1000)_
* **Aktion:** **Entfernen** (Zeile löschen)

**Regeln**

- Mehrere Zähler je Medium **zulässig**.
- Harte Validierung: pro _(Unit, Meter type)_ **nur ein** `Is default = true`.
- **Gas** wird systemweit in **kWh** geführt.

---

## 4) UX & Mobile

- Gleiches Look & Feel wie `/portal/`: mobil **einspaltig**, ab `md` **zweispaltig**.
- **Zählerliste** als editierbare Zeilen mit Badges `Default`/`Aktiv`, Medium-Icon, Aktionen `Entfernen`.
- **Sticky Action Bar** unten: `Speichern`, `Abbrechen`, `Archivieren/Löschen`.
- Leere Zustände: „Noch keine Zähler angelegt. Jetzt hinzufügen.“
- Barrierefreiheit: Labels/ARIA, Fokus, Kontrast.

---

## 5) Archivieren/Löschen (Policies)

- **Soft-Delete (Archiv):** Felder **is_archived**, **archived_at**, **archived_by** an Unit.
- Übersicht **blendet archivierte Units aus**; Checkbox „Archivierte anzeigen“ zeigt sie (ausgegraut).
- **Hard-Delete** nur ohne Abhängigkeiten (Verträge, Zahlungen, Dokumente, **Zähler**, **Readings**, Mieterzuordnungen). Bei Abhängigkeiten: **409** + Meldung „Bitte archivieren“.
- Archivierte Units (und deren Zähler) werden in Portaldropdowns (z. B. Zählerstand erfassen) **nicht** angeboten.

**Meter-Delete Policy (Unit-Scope)**

- **Ohne Readings:** `DELETE` → **204**, Zähler wird entfernt.
- **Mit Readings:** `DELETE` → **409** (Hard-Delete verboten). UI bietet **„Zähler deaktivieren“** an (setzt `is_active=false`, `removed_at=today`).

---

## 6) API (REST, JSON)

### 6.1 Units

- **GET** `/api/portal/units`
  **Params:** `query` (label/property name), `property_id`, `is_active`, `is_archived` (default false), `sort` (label|floor|created_at), `order` (asc|desc), `page`, `page_size` (default 25, max 100).
  **Antwort:** paginierte Liste (inkl. `property_summary`, `meters_count`, `updated_at`).

- **GET** `/api/portal/units/{id}`
  **Antwort:** Unit-Detail inkl. **Zählerliste**.

- **POST** `/api/portal/units`
  **Body:** Felder aus **3.1**.
  **Antwort:** **201** + Objekt (id).
  **Hinweis:** Zähler werden **nicht** im selben Call angelegt (2-Step-Flow: erst Unit speichern, dann Zähler anlegen).

- **PATCH** `/api/portal/units/{id}` → Teilupdates (3.1). **200**.

- **POST** `/api/portal/units/{id}/archive` → **200** (archiviert).

- **DELETE** `/api/portal/units/{id}` → **204** oder **409** (Abhängigkeiten).

### 6.2 Unit-Meters

- **POST** `/api/portal/units/{id}/meters` → Zähler anlegen.
- **PATCH** `/api/portal/units/{id}/meters/{meter_id}` → Zähler ändern.
- **DELETE** `/api/portal/units/{id}/meters/{meter_id}` → s. Policy (204/409).

**Statuscodes & Fehlertexte (Auszug)**

- **400** ungültige Felder/Validierung
- **401/403** fehlende/fehlende Rechte
- **404** nicht gefunden
- **409** Konflikt (doppelter Default, Abhängigkeiten beim Löschen)
- **422** semantischer Fehler (z. B. `Removed at` < `Installed at`)

**Auth/RBAC**

- Session-basiert wie übriges Portal.
- **View:** Landlord/Staff. **CRUD:** Admin/Property-Manager.

---

## 7) Performance

- Paging 25/Seite; Default-Sort `label ASC`.
- **Indizes:** `(property_id, label)`, `(is_archived)`, `(unit_id, meter_type, is_default)`, `(unit_id, meter_type, is_active)`.
- N+1-Vermeidung: Unit-Detail lädt Zähler gesammelt (prefetch/join).
- Ziel: **P95 < 300 ms** (10k Units).

---

## 8) Sicherheit

- CSRF für mutierende Requests.
- Server-Validierung aller Felder; Normalize/Trim.
- XSS-Schutz (escape, Längenlimits).
- Rate-Limit (wie Properties):

  - **Mutating (POST/PATCH/DELETE):** **50/Stunde** pro **User**
  - **GET:** **100/Stunde** pro **User**
  - Antworten enthalten `Retry-After`, wenn Limits greifen.

---

## 9) Audit & Monitoring

- Events: Create/Update/Archive/Delete für Unit & Unit-Meter; `changed_by`, `changed_at`, Feld-Diff (`{field:{old,new}}`).
- Logging + optional Sentry.
- Metriken: Requests/s, P95, 4xx/5xx-Rate.

---

## 10) Akzeptanzkriterien

- [ ] Top-Nav **Einheiten** führt zu `/portal/units/` (Liste mit Suche/Filter/Sort).
- [ ] **Unit anlegen** (Property gewählt, minimale Pflichtfelder) → 201 + Redirect auf Detail.
- [ ] **Bearbeiten** zeigt vorbefüllte Felder und **Zählerliste**; Add/Edit/Remove funktioniert.
- [ ] **Default-Validierung:** zweiter Default für gleiches Medium → **409/Fehlertext**.
- [ ] **Meter-Delete:** mit Readings → **409** + UI-Option „Deaktivieren“ setzt `is_active=false`, `removed_at=today`.
- [ ] **Archivieren** blendet Unit aus der Standardliste; Filter „Archivierte anzeigen“ zeigt sie (ausgegraut).
- [ ] **Dropdowns im Portal** bieten **keine archivierten Units** zur Auswahl an.
- [ ] **Mobile-UX**: einspaltig, Sticky Action Bar, gute Touch-Targets.
- [ ] **Performance**: P95 < 300 ms (Liste/Detail).

---

## 11) Tests (Auszug)

- Backend-Unit-Tests: Modelle/Validatoren/Policies (Ziel ≥ 85 %).
- API-Tests: alle Endpunkte inkl. Konflikte (doppelter Default, 409 Delete) (Ziel ≥ 90 % Routen).
- E2E (Portal):

  1. Create Unit → OK;
  2. Add Meter (Default) → OK;
  3. Zweiten Default setzen → Fehlertext;
  4. Delete Meter mit Readings → 409 + Deaktivieren-Flow;
  5. Archivieren/Filter-Toggle;
  6. Mobile Smoke (iPhone/Pixel).

---

## 12) Rollout & Abhängigkeiten

- **Migrations erforderlich:**
  1. **Archive-Felder** hinzufügen: `is_archived`, `archived_at`, `archived_by` zu Unit-Model (analog zu Property).
  2. **Validator** `MinValueValidator(0)` für `area_sqm` hinzufügen.
  3. **Index** auf `is_archived` erstellen.
  4. Indizes gemäß Kap. 7 überprüfen/erstellen.
- Feature-Flag `units_portal` optional.
- Rollback: Menüpunkt deaktivieren + Migration revert.

---

## 13) Nicht-Ziele

- Property-Pflege (separates Modul).
- Bulk-Import/Export, Karten-Ansicht, QR/OCR.
- Externer Provider-Sync.

---

## 14) Aufwand (aktualisierte Schätzung)

- **Model-Migration** (Archive-Felder, Validators, Indizes): **0.3 PT**
- Views/Routes + Übersicht + Detail: **0.8–1.2 PT** → **1.0 PT** (Copy-Paste von Property-Pattern)
- Zählerliste (dyn. Add/Remove, Validierungen): **0.8–1.5 PT** → **1.0 PT** (Meter-Pattern vorhanden)
- Archiv/Hard-Delete + Abhängigkeitsprüfung: **0.5–0.8 PT** → **0.5 PT** (wie Property)
- API + Tests (Unit/API/E2E): **0.8–1.2 PT** → **1.2 PT**
  **Gesamt:** **2.9–4.7 PT** → **Aktualisiert: ~4.0 PT**

**Hinweis:** Aufwand reduziert sich durch Wiederverwendung des Property-Patterns (Views, Templates, API-Struktur, Tests).

---

**Status:** **Freigegeben für Umsetzung (v1.0)**
**Empfohlener Dateiname:** `uvm/docs/Portal_Units_CRUD_and_Meters_1_0.md`
