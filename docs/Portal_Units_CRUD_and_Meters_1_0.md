# UVM – **Wohnungen (Units)** : Portal-CRUD + **Zähler (Stammdaten)**

**Version:** 1.0 (Spec)  
**Datum:** 2025-10-21  
**Owner:** Landlord / Unit Management  
**Scope:** Neues Portal-Modul **„Wohnungen"** (Units) mit **CRUD** und **Zählerverwaltung** **auf Unit-Ebene**.  
**Hinweis:** Properties werden separat in _Portal_Properties_CRUD_and_Meters_1_1.md_ spezifiziert. Django-Admin bleibt unverändert als „uncut Admin".

**Implementierungs-Status:** 🚧 **IN PROGRESS**

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

### 🚧 Phase 3: Unit-Meter CRUD Views (TODO)
### ⏳ Phase 4: Unit API Endpoints (TODO)
### ⏳ Phase 5: Unit-Meter API Endpoints (TODO)
### ⏳ Phase 6: Tests (TODO)
### ⏳ Phase 7: Navigation & Finalisierung (TODO)

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

- **GET** `/portal/api/units`
  **Params:** `query` (label/property name), `property_id`, `is_active`, `is_archived` (default false), `sort` (label|floor|created_at), `order` (asc|desc), `page`, `page_size` (default 25, max 100).
  **Antwort:** paginierte Liste (inkl. `property_summary`, `meters_count`, `updated_at`).

- **GET** `/portal/api/units/{id}`
  **Antwort:** Unit-Detail inkl. **Zählerliste**.

- **POST** `/portal/api/units`
  **Body:** Felder aus **3.1**.
  **Antwort:** **201** + Objekt (id).
  **Hinweis:** Zähler werden **nicht** im selben Call angelegt (2-Step-Flow: erst Unit speichern, dann Zähler anlegen).

- **PATCH** `/portal/api/units/{id}` → Teilupdates (3.1). **200**.

- **POST** `/portal/api/units/{id}/archive` → **200** (archiviert).

- **DELETE** `/portal/api/units/{id}` → **204** oder **409** (Abhängigkeiten).

### 6.2 Unit-Meters

- **POST** `/portal/api/units/{id}/meters` → Zähler anlegen.
- **PATCH** `/portal/api/units/{id}/meters/{meter_id}` → Zähler ändern.
- **DELETE** `/portal/api/units/{id}/meters/{meter_id}` → s. Policy (204/409).

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

  - **Mutating (POST/PATCH/DELETE):** **60/min** pro **User** und **IP**
  - **GET:** **240/min** pro **User** und **IP**
  - 429 mit `Retry-After`.

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
