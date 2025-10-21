# Portal Units CRUD - Code-Analyse & Bewertung

**Datum:** 2025-10-21
**Reviewer:** AI Code-Analyst
**Dokument:** `Portal_Units_CRUD_and_Meters_1_0.md`
**Status:** ✅ **APPROVED mit kleinen Anpassungen**

---

## 📊 Executive Summary

**Bewertung:** ⭐⭐⭐⭐⭐ **9/10 - Exzellent mit minimalen Anpassungen nötig**

Die Spezifikation ist **sehr gut durchdacht** und passt **hervorragend** zur bestehenden Property-Implementierung. Der unbekannte Agent hat eine strukturierte, umsetzbare Spec erstellt, die nur **minimale Anpassungen** benötigt.

---

## ✅ Stärken der Spezifikation

### 1. **Konsistenz mit Property-Pattern**

✅ Folgt exakt der Property-Implementierung:

- Gleiche View-Struktur (ListView, DetailView, CreateView, UpdateView)
- Gleiche API-Endpoints-Muster
- Gleiche Archive/Delete-Policies
- Gleiche Permissions & Throttling

### 2. **Model-Alignment perfekt**

✅ Alle Felder in Spec stimmen mit `landlord/models.py` überein:

```python
# Aus models.py (Zeilen 111-126)
class Unit(TimeStampedModel):
    property = models.ForeignKey(Property, ...)     # ✅ Spec: Property (Pflicht)
    unit_label = models.CharField(max_length=100)   # ✅ Spec: max 100 Zeichen
    floor = models.CharField(max_length=50, blank=True)  # ✅ Spec: optional
    rooms = models.PositiveSmallIntegerField(null=True, blank=True)  # ✅ Spec: Ganzzahl optional
    area_sqm = models.DecimalField(..., null=True, blank=True)  # ✅ Spec: Decimal ≥ 0
    notes = models.TextField(blank=True)  # ✅ Spec: max 2000 (passt)
    is_active = models.BooleanField(default=True)  # ✅ Spec: Bool
```

### 3. **Zähler-Scope korrekt identifiziert**

✅ Unit-Meter vs Property-Meter Unterscheidung:

- Property-Meter: `scope_type='property'` (Gebäudezähler)
- Unit-Meter: `scope_type='unit'` (Wohnungszähler)
- **Spec kennt die Unterscheidung!**

### 4. **Realistische Aufwandsschätzung**

✅ **2.9–4.7 PT** ist realistisch basierend auf Property-Implementierung:

- Property-Phase 2 dauerte ~4–5 PT
- Units haben weniger Komplexität (keine Geo-Koordinaten)
- Zählerliste kann von Property-Pattern kopiert werden

### 5. **UX/Mobile-Anforderungen klar**

✅ Spezifiziert mobil-optimiertes Design (einspaltig, sticky action bar)
✅ Konsistent mit aktuellem Tailwind-Design-System

---

## ⚠️ Notwendige Anpassungen

### 1. **KRITISCH: Archive-Felder fehlen bei Unit**

**Problem:**

```python
# models.py Unit (Zeile 111-126) hat KEINE Archive-Felder!
class Unit(TimeStampedModel):
    property = models.ForeignKey(...)
    # ... andere Felder ...
    is_active = models.BooleanField(default=True)  # ← Nur is_active!
    # ❌ FEHLT: is_archived, archived_at, archived_by
```

**Spec fordert (Kap. 5):**

> Felder **is_archived**, **archived_at**, **archived_by** an Unit.

**Lösung:**

```python
# Migration nötig!
class Unit(TimeStampedModel):
    # ... bestehende Felder ...

    # Archive fields (soft-delete) - NEU!
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-delete flag for archived units"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when unit was archived"
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='archived_units',
        help_text="User who archived this unit"
    )

    def archive(self, user):
        """Archive this unit (soft-delete)"""
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
```

**Aufwand:** +0.2 PT (Migration + Tests)

---

### 2. **Floor-Feld: String vs Integer**

**Aktuell (models.py):**

```python
floor = models.CharField(max_length=50, blank=True)  # ← String!
```

**Spec sagt (Kap. 3.1):**

> Floor: Ganzzahl (optional)

**Empfehlung:** **Spec anpassen** (String behalten)

- **Grund:** `CharField` erlaubt "EG", "UG", "DG", "1. OG" etc.
- **Vorteil:** Flexibler für deutsche/internationale Stockwerksbezeichnungen
- **Kein Breaking Change** nötig

**Anpassung in Spec:**

```diff
- Floor: Ganzzahl (optional).
+ Floor: Text (max. 50 Zeichen; optional; z.B. "EG", "1. OG", "UG").
```

---

### 3. **API-Routes: Nested vs Flat**

**Property-Pattern (aktuell):**

```python
# config/urls.py (Zeilen 148-149)
path("portal/properties/<int:property_id>/meters/new", ...)  # ← Nested!
path("portal/properties/<int:property_id>/meters/<int:pk>/edit", ...)
```

**Spec fordert (Kap. 6.2):**

```
POST /portal/api/units/{id}/meters
PATCH /portal/api/units/{id}/meters/{meter_id}
DELETE /portal/api/units/{id}/meters/{meter_id}
```

**Konsistenz-Check:** ✅ **Spec ist konsistent!**

- Properties nutzen nested routes
- Units sollen nested routes nutzen
- **Perfekt aligned!**

---

### 4. **Meter-Type Mapping beachten**

**Wichtig:**

```python
# UtilityMeter.MeterType (für Stammdaten)
WATER_COLD = 'cold_water'    # ← Unterstrich!
WATER_HOT = 'hot_water'
ELECTRICITY = 'electricity'
GAS = 'gas'

# UtilityReading.MeterType (für Ablesungen)
WATER_COLD = 'water_cold'    # ← Anderer Name!
WATER_HOT = 'water_hot'
```

**Spec muss klarstellen:**

- Unit-Meter nutzen `UtilityMeter.MeterType` (mit Unterstrich)
- Bei Vorbefüllung: Mapping `cold_water → water_cold` beachten

---

### 5. **Indizes: Spec vs Realität**

**Spec fordert (Kap. 7):**

```
Indizes: (property_id, label), (is_archived),
         (unit_id, meter_type, is_default),
         (unit_id, meter_type, is_active)
```

**Aktuell (models.py Zeile 120-122):**

```python
class Meta:
    indexes = [
        models.Index(fields=["property", "unit_label"]),  # ✅ Vorhanden
        # ❌ FEHLT: is_archived Index (muss mit Migration hinzugefügt werden)
    ]
```

**Meter-Indizes:**

```python
# UtilityMeter.Meta (bereits vorhanden, Zeilen 853-859)
indexes = [
    models.Index(fields=['property', 'scope_type', 'meter_type']),
    models.Index(fields=['unit', 'scope_type', 'meter_type']),
    models.Index(fields=['is_default']),
    models.Index(fields=['is_active']),
]
# ✅ Ausreichend für Unit-Meter Performance!
```

---

## 🔍 Detailprüfung: Validierungen

### Unit-Validierungen (Kap. 3.1)

| Feld       | Spec                      | Code                                 | Status                          |
| ---------- | ------------------------- | ------------------------------------ | ------------------------------- |
| Property   | Pflicht, nicht archiviert | `ForeignKey(..., on_delete=CASCADE)` | ⚠️ Archive-Filter in Form nötig |
| Unit label | max 100                   | `CharField(max_length=100)`          | ✅                              |
| Floor      | Ganzzahl (opt)            | `CharField(max_length=50)`           | ⚠️ Spec anpassen                |
| Rooms      | Ganzzahl (opt)            | `PositiveSmallIntegerField`          | ✅                              |
| Area sqm   | Decimal ≥ 0               | `DecimalField(..., null=True)`       | ⚠️ Validator ≥ 0 fehlt          |
| Notes      | max 2000                  | `TextField(blank=True)`              | ⚠️ MaxLength-Validator fehlt    |

**To-Do:**

```python
# Validatoren hinzufügen
area_sqm = models.DecimalField(
    ...,
    validators=[MinValueValidator(0)],  # ← Hinzufügen!
)

# Notes: MaxLengthValidator in Form, nicht Model (TextField hat keine max_length)
```

---

## 🚀 Implementierungs-Roadmap

### Phase 1: Model-Migration (0.3 PT)

1. ✅ Archive-Felder zu Unit hinzufügen
2. ✅ Index auf `is_archived` erstellen
3. ✅ Validator `MinValueValidator(0)` für `area_sqm`
4. ✅ Migration erstellen & testen

### Phase 2: Views & Templates (1.0 PT)

1. ✅ `UnitListView` (analog PropertyListView)
2. ✅ `UnitDetailView` (analog PropertyDetailView)
3. ✅ `UnitCreateView` (analog PropertyCreateView)
4. ✅ `UnitUpdateView` (analog PropertyUpdateView)
5. ✅ Templates: `units_list.html`, `unit_detail.html`, `unit_form.html`

### Phase 3: Unit-Meter CRUD (1.2 PT)

1. ✅ Views: `UnitMeterCreateView`, `UnitMeterUpdateView`
2. ✅ Template: `unit_meter_form.html` (analog meter_form.html)
3. ✅ Unit-Detail zeigt Meter-Liste mit Add/Edit/Delete
4. ✅ Validation: Max 1 Default pro (Unit, Meter-Type)

### Phase 4: API Endpoints (0.8 PT)

1. ✅ `UnitListAPIView` (mit Pagination & Filtering)
2. ✅ `UnitDetailAPIView`
3. ✅ `UnitCreateAPIView`, `UnitUpdateAPIView`
4. ✅ `UnitArchiveAPIView`, `UnitUnarchiveAPIView`, `UnitDeleteAPIView`
5. ✅ Serializers: `UnitListSerializer`, `UnitDetailSerializer`, etc.

### Phase 5: Unit-Meter API (0.5 PT)

1. ✅ `UnitMeterCreateAPIView`
2. ✅ `UnitMeterUpdateAPIView`
3. ✅ `UnitMeterDeleteAPIView` (mit Reading-Check)

### Phase 6: Tests (1.0 PT)

1. ✅ Model-Tests (Validierungen, Archive-Methode)
2. ✅ View-Tests (CRUD-Flows)
3. ✅ API-Tests (alle Endpoints + Error-Cases)
4. ✅ E2E-Tests (Create Unit → Add Meter → Archive)

---

## 📋 Änderungsempfehlungen für Spec

### Änderung 1: Archive-Felder explizit als "TO BE ADDED"

```diff
### 3.1 Unit – Stammdaten

+ **⚠️ Hinweis:** Die Felder `is_archived`, `archived_at`, `archived_by`
+ sind aktuell NICHT im Model und müssen per Migration hinzugefügt werden.

* **Property** *(Pflicht; Auswahl)*
...
* **Is active** *(Bool)*
+ * **Is archived** *(Bool; default=False; NEU per Migration)*
+ * **Archived at** *(DateTime; nullable; NEU)*
+ * **Archived by** *(FK User; nullable; NEU)*
```

### Änderung 2: Floor-Typ korrigieren

```diff
### 3.1 Unit – Stammdaten

- * **Floor** *(Ganzzahl; optional)*
+ * **Floor** *(Text; max 50 Zeichen; optional; z.B. "EG", "1. OG")*
```

### Änderung 3: Validator-Notizen hinzufügen

```diff
**Validierungen**

* Area sqm: Decimal ≥ 0 (optional).
+ ⚠️ **Hinweis:** Validator `MinValueValidator(0)` muss zum Model hinzugefügt werden.
* Notes: max. 2000 Zeichen.
+ ⚠️ **Hinweis:** MaxLengthValidator in Form (TextField hat keine max_length).
```

### Änderung 4: Meter-Type-Mapping explizit machen

```diff
### 3.2 Zähler (Stammdaten) – **Unit-Scope**

* **Meter type** *(Medium)*: **Kaltwasser**, **Warmwasser**, **Strom**, **Gas (kWh)**
+
+ **Technische Werte (UtilityMeter.MeterType):**
+ - `cold_water` (Kaltwasser)
+ - `hot_water` (Warmwasser)
+ - `electricity` (Strom)
+ - `gas` (Gas in kWh)
+
+ ⚠️ **Wichtig:** Bei Vorbefüllung in "Zählerstand erfassen"
+ muss Mapping zu UtilityReading.MeterType beachtet werden:
+ `cold_water → water_cold`, `hot_water → water_hot`
```

---

## 📊 Finale Bewertung

### Code-Passung: ⭐⭐⭐⭐⭐ (5/5)

- ✅ Model-Felder 95% korrekt identifiziert
- ✅ API-Pattern perfekt aligned
- ✅ View-Struktur konsistent mit Properties
- ✅ Permissions & Throttling übernommen

### Umsetzbarkeit: ⭐⭐⭐⭐☆ (4/5)

- ✅ Klare Strukturierung
- ✅ Realistische Aufwandsschätzung
- ⚠️ Migration für Archive-Felder nötig (nicht erwähnt)
- ✅ Copy-Paste von Property-Pattern möglich

### Vollständigkeit: ⭐⭐⭐⭐⭐ (5/5)

- ✅ Alle CRUD-Operationen spezifiziert
- ✅ API-Endpoints vollständig
- ✅ Error-Handling & Status-Codes definiert
- ✅ Tests & E2E-Szenarien beschrieben
- ✅ Performance-Anforderungen (P95 < 300ms)

### Klarheit: ⭐⭐⭐⭐⭐ (5/5)

- ✅ Keine Spekulationen
- ✅ Exakte Feldnamen & Typen
- ✅ Klar definierte Policies
- ✅ Akzeptanzkriterien testbar

---

## ✅ Empfehlung

**APPROVED für Umsetzung** mit folgenden Maßnahmen:

### Vor Start:

1. ✅ Spec mit 4 Änderungen updaten (siehe oben)
2. ✅ Migration für Archive-Felder erstellen
3. ✅ Validators zu Unit-Model hinzufügen

### Während Implementierung:

1. ✅ Property-Pattern 1:1 kopieren & anpassen
2. ✅ Tests parallel schreiben (TDD)
3. ✅ Mobile-UX testen (iPhone/Pixel)

### Nach Implementierung:

1. ✅ E2E-Tests gegen Akzeptanzkriterien (Kap. 10)
2. ✅ Performance-Test: P95 < 300ms @ 10k Units
3. ✅ Code-Review: Konsistenz mit Property-Pattern

---

## 📈 Geschätzter Aufwand (aktualisiert)

| Phase             | Spec           | Angepasst   | Grund                      |
| ----------------- | -------------- | ----------- | -------------------------- |
| Model-Migration   | -              | **+0.3 PT** | Archive-Felder, Validators |
| Views & Templates | 0.8–1.2 PT     | **1.0 PT**  | Copy-Paste von Property    |
| Zählerliste       | 0.8–1.5 PT     | **1.0 PT**  | Meter-Pattern vorhanden    |
| Archive/Delete    | 0.5–0.8 PT     | **0.5 PT**  | Wie Property               |
| API & Tests       | 0.8–1.2 PT     | **1.2 PT**  | Wie Property               |
| **Gesamt**        | **2.9–4.7 PT** | **4.0 PT**  | Realistisch                |

---

**✅ FREIGABE FÜR UMSETZUNG**

Spec ist **exzellent strukturiert** und kann mit **minimalen Anpassungen** (Archive-Migration + Spec-Updates) direkt implementiert werden.

**Nächster Schritt:** Spec updaten → Migration erstellen → Views implementieren (analog Property-Pattern)
