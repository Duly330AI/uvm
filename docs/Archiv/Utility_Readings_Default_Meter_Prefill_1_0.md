# UVM – Utility Readings: Default Meter Prefill

**Version:** 1.0 (Spec)
**Date:** 2025-10-20
**Owner:** Landlord / Utility Domain
**Scope:** Portal `…/portal/utility/readings/create` („📊 Neuen Zählerstand erfassen“) + Django-Admin (Property/Unit)

---

## 1) Ziel & Nutzen

Beim Erfassen eines neuen Zählerstands wird die **Zählernummer (Seriennummer)** automatisch vorbefüllt, sobald im Dropdown _Wohneinheit / Gebäude_ eine Property (Gebäudezähler) oder Unit (Wohnungszähler) **und** der **Zählertyp** gewählt wurden.
Die Standard-Zähler werden **optional** bereits im **Django-Admin** an Property/Unit gepflegt.
**Medien:** Warmwasser, Kaltwasser, Strom, Gas (Gas in **kWh**).

**Business-Mehrwert**

- Schnellere, fehlerärmere Erfassung (keine manuelle Seriennummer).
- Konsistente Stammdatenbasis je Objekt/Wohnung.
- Erweiterbar für Zählerwechsel & Historie.

---

## 2) Ist-Zustand (heute)

- Formular `…/portal/utility/readings/create`

  - _Wohneinheit / Gebäude_ (Gruppierung: **Gebäudenzähler** vs. **Wohnungszähler**).
  - Zählernummer wird **manuell** eingetragen.
  - Hinweis im UI: „Der **vorherige Zählerstand** wird automatisch vom letzten Eintrag übernommen.“

- Im Django-Admin existiert **keine** strukturierte Pflege von Standard-Zählern pro Medium/Objekt.

---

## 3) Soll-Zustand (Zielbild)

### 3.1 Datenmodell (logisch, ohne Code)

**Entity: UtilityMeter** _(Zähler-Stammdatensatz)_

- **scope_type**: `property` | `unit`
- **scope_id**: FK → Property bzw. Unit
- **meter_type**: Enum {`hot_water`, `cold_water`, `electricity`, `gas`}
- **serial_number**: String (Seriennummer des Versorgers)
- **reading_unit** _(implizit aus meter_type; Gas = kWh)_
- **is_default**: Bool — genau **ein** Default pro `(scope_type, scope_id, meter_type)`
- **is_active**: Bool — aktiver Zähler (Inventarstatus)
- **initial_reading_value** _(optional)_: Decimal — Startwert (nur intern für erste Berechnung)
- **installed_at**, **removed_at** _(optional)_: Datumsfelder für Wechsel/Historie

**Kardinalität & Regeln**

- **Mehrere Zähler pro Medium sind zulässig** (z. B. komplexe Heizsysteme).
- **Konflikt-Policy:** Im Admin ist **genau ein Default** je `(scope, meter_type)` zulässig. Doppelte Defaults werden **verhindert**.
- Mehrere **aktive** Zähler ohne Default sind erlaubt, aber führen im Portal zur **Auswahl**.

### 3.2 Admin-UX

- **Property-Admin** und **Unit-Admin**: Inline „Zähler (Stammdaten)“.

  - Felder pro Datensatz: _Medium, Seriennummer, Default, Aktiv, Startwert (optional), Installiert am, Entfernt am_.
  - **Validation:**

    - Max. **ein** `is_default = true` pro `(scope, meter_type)` → sonst Speichern verhindern.
    - Seriennummer kann leer sein (wenn z. B. nur Inventar angelegt wird), wird dann nicht vorbefüllt.

- **Pflegeprinzip:** „**Frei anlegbare Datensätze**“. Optionale Shortcuts zum schnellen Anlegen der vier Standardmedien (nicht verpflichtend).

### 3.3 Portal-Formular: Verhalten (Prefill + Auswahl)

1. Nutzer wählt **Wohneinheit/Gebäude** _(Scope)_ und **Zählertyp** _(Medium)_.

2. System sucht **UtilityMeter** nach Priorität:

   1. **Default-Zähler** → **Zählernummer** wird **automatisch** vorbefüllt.
   2. Kein Default, aber **genau ein aktiver** Zähler → dessen Seriennummer vorbefüllen.
   3. **Mehrere aktive** Zähler und **kein Default** → **zusätzliches Dropdown „Zähler auswählen“** anzeigen; nach Auswahl wird Seriennummer übernommen.
   4. **Kein Zähler** gefunden → Feld bleibt leer + Hinweis „Kein Standardzähler hinterlegt“.

3. **Vorheriger Zählerstand**

   - Wird automatisch aus dem **letzten Reading des ausgewählten Zählers** übernommen.
   - Gibt es noch **kein Reading**, aber `initial_reading_value` ist gesetzt → dieser Startwert dient **einmalig** als „vorheriger Zählerstand“ (Info-Hinweis).
   - UI bleibt wie gehabt: „Der vorherige Zählerstand wird automatisch vom letzten Eintrag übernommen.“

### 3.4 Dropdown-Gruppierung (Scope-Auswahl)

- **Dynamisch**:

  - Gruppe **„Gebäudenzähler“** nur, wenn für die gewählte Property relevante Default/Aktive vorhanden sind.
  - Gruppe **„Wohnungszähler“** je Unit, analog.
  - Bezeichnungen/Listen passen sich dem vorhandenen Bestand an.

### 3.5 Service/Datenaustausch (logisch)

- **getDefaultMeter(scope_type, scope_id, meter_type)**

  - Liefert: `{meter_id, serial_number, has_multiple, initial_reading_value?}`

- **getLastReading(meter_id)**

  - Liefert letzten Zählerstand; fehlt er, wird `initial_reading_value` verwendet (falls vorhanden).

- Beide Aufrufe werden **onChange** von Scope/Medium (und ggf. „Zähler auswählen“) verwendet.

---

## 4) Validierungen & Regeln (Erfassung)

- **Aktueller Zählerstand** muss ≥ **vorheriger Zählerstand** (harte Validierung).
- **Ein Reading pro `(Tag, Zählertyp, Zähler/Meter)`**.
- **Einheiten**:

  - Kalt-/Warmwasser → m³
  - Strom → kWh
  - **Gas → kWh** (Projektstandard)

- Bei Meter-Wechsel (neuer Default) wird automatisch auf den **gewählten Meter** bezogen; „vorheriger Zählerstand“ stammt immer vom **gleichen Meter**.

---

## 5) Einführungs- & Migrationsplan

1. **Entity UtilityMeter** inkl. `is_default`-Constraint (1 Default je `(scope, type)`).
2. **Admin-Inlines** bei Property & Unit; Validierungen gem. Konflikt-Policy.
3. **Services** `getDefaultMeter`, `getLastReading`.
4. **Portal-Form**: Prefill-Flows + optionales „Zähler auswählen“ bei Mehrfachtreffern.
5. **Datenübernahme (optional)**: vorhandene Seriennummern aus Notizen/Listen migrieren.
6. **Hinweise/Tooltips** im Admin & Portal zur Funktionsweise (Startwert, Default, Auswahl).

---

## 6) Akzeptanzkriterien

- [ ] Auswahl **Property + Strom** mit gepflegtem Default → **Seriennummer** wird **vorbefüllt**.
- [ ] Auswahl **Unit + Kaltwasser**, **kein Default**, **ein aktiver** → Seriennummer vorbefüllt.
- [ ] Auswahl **Unit + Warmwasser**, **kein Default**, **zwei aktive** → UI zeigt **„Zähler auswählen“**; nach Wahl wird vorbefüllt.
- [ ] **Vorheriger Zählerstand** kommt aus letztem Reading desselben **Meter**; wenn keines existiert, einmalig aus `initial_reading_value`.
- [ ] **Admin** verhindert zweite Default-Markierung pro `(scope, type)`.
- [ ] **Gas**-Readings werden in **kWh** geführt und berechnet.
- [ ] **Dynamische Gruppierung** im Dropdown: Gruppen erscheinen nur, wenn es relevante Zähler gibt.
- [ ] Prefill aktualisiert sich bei Wechsel von Scope/Medium/Zähler **ohne Seitenreload**.
- [ ] Performance lokal: Prefill-Abruf < 200 ms.

---

## 7) Testfälle (manuell/E2E, ohne Code)

1. **Happy Path Default**: Property „Mehrfamilienhaus – Allgemein“, Typ **Strom**, Default vorhanden → Seriennummer sichtbar; Vorheriger Stand = letzter Reading-Wert.
2. **Ein aktiver, kein Default**: Unit „1a“, Typ **Kaltwasser** → Seriennummer vorbefüllt; Vorheriger Stand korrekt.
3. **Mehrere aktive, kein Default**: Unit „1b“, Typ **Warmwasser** → „Zähler auswählen“ erscheint; nach Auswahl stimmen Serien- & Vorheriger Stand.
4. **Kein Zähler**: Unit „1c“, Typ **Gas** → Seriennummer leer + Hinweis; Gas-Einheit wird als **kWh** verarbeitet.
5. **Startwert-Fall**: Neuer Zähler mit `initial_reading_value=14155`, erstes Reading → Vorheriger Stand = 14155 (einmalig), danach regulär.
6. **Admin-Validation**: Zweiten Default für `(Unit 1a, Strom)` markieren → Speichern wird verhindert.
7. **Dynamische Gruppierung**: Entferne alle Unit-Zähler → nur „Gebäudenzähler“ wird gelistet.

---

## 8) Nicht-Ziele (vorerst)

- Kein Foto-/Scan-OCR für Zählerstände.
- Kein externer Provider-Sync.
- Kein automatischer Zähler-Abgleich via Seriennummern-Register.

---

## 9) Offene Punkte / Risiken

- **Mehrzähler-Sicht:** UI-Komplexität bei sehr vielen Zählern pro Medium (Filter/Suche ggf. später).
- **Startwert-Transparenz:** `initial_reading_value` wird nicht prominent angezeigt (derzeit **nur** beim ersten Reading wirksam).
- **Einheiten-Mix Gas:** Falls historische m³-Werte existieren, braucht es eine Migrationsstrategie (Konversion/Kennzeichnung).

---

## 10) Umsetzungs-Checkliste (ohne Code)

- [ ] Entity **UtilityMeter** + Constraints `one default per scope+type`.
- [ ] Admin-Inlines Property/Unit; Validierungen & Hilfetexte.
- [ ] Services **getDefaultMeter**, **getLastReading**.
- [ ] Portal-Form: Prefill + „Zähler auswählen“ bei Mehrfachtreffern.
- [ ] Automatik **„Vorheriger Zählerstand“** wie beschrieben.
- [ ] Gas = **kWh** end-to-end.
- [ ] E2E-Flows & Performance Smoke-Tests.
- [ ] Kurz-Doku für Anwender & Release-Note.

---

**Status:** **Freigegeben** (alle 7 Rückfragen beantwortet). Bereit für Umsetzung & E2E-Tests.
