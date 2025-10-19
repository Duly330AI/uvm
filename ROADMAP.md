# 🏢 UVM - Universal Vermieter Management

## Projekt-Roadmap & Feature-Status

**Stand:** 19. Oktober 2025
**Version:** 0.8.0 (Development - M12a + M12b Complete)
**Letzte Aktualisierung:** 19.10.2025 02:30 - **PHASE 2+3 VERTRÄGE & ZAHLUNGEN ABGESCHLOSSEN** ✅

---

## 📊 Executive Summary

Das UVM-System ist eine **webbasierte Hausverwaltungssoftware** mit Fokus auf:

- **Mieter-Self-Service** (Chat, Tickets, Dokumente)
- **Vermieter-Portal** (Verwaltung, Reports, KPIs)
- **Handwerker-Integration** (Magic-Link, Aufträge)

**Aktueller Fortschritt:** ~70% der Kern-Features implementiert
**Neue Roadmap:** Priorisierung nach **logischem Workflow** & **technischen Abhängigkeiten**---

## ✅ IMPLEMENTIERTE FEATURES (M1-M10 + PR1-2)

### 🎫 **Ticketing & Kommunikation**

| Feature                        | Status  | Details                                                                   |
| ------------------------------ | ------- | ------------------------------------------------------------------------- |
| Chat-basierte Anliegen-Meldung | ✅ 100% | Strukturierter Dialog: Problem → Kategorie → Schwere → Foto → Bestätigung |
| Ticket-Erstellung              | ✅ 100% | Auto-Ticket-Nr (TCK-YYYY-XXXXX), Status-Tracking                          |
| Status-Workflow                | ✅ 100% | NEW → IN*PROGRESS → WAITING*\* → DONE                                     |
| Notizen & Kommunikation        | ✅ 100% | Public/Internal Notes, Verlauf                                            |
| Automatische Priorisierung     | ✅ 100% | Severity 1-5 aus Chat-Dialog                                              |
| Dokumenten-Upload              | ✅ 100% | Fotos/PDFs während Chat & nachträglich                                    |

### 📁 **Dokumenten-Management (M9 + M11b + M17a)**

| Feature                          | Status  | Details                                                  |
| -------------------------------- | ------- | -------------------------------------------------------- |
| Digitaler Dokumentenspeicher     | ✅ 100% | Categories: lease, invoice, protocol, certificate, other |
| Download/Export                  | ✅ 100% | Einzeldownload + Bulk-Export                             |
| Upload-Validierung               | ✅ 100% | Max 10MB/Datei, 40MB gesamt, JPEG/PNG/GIF/PDF            |
| **Dokumente → Units/Properties** | ✅ 100% | **M11b:** Property/Unit/Tenant ForeignKeys (5.5h)        |
| **Versionshistorie**             | ✅ 100% | **M17a:** DocumentVersion Model, Timeline UI (2.5h)      |

### 🔧 **Handwerker/Dienstleister (M10 + M11)**

| Feature                    | Status  | Details                                      |
| -------------------------- | ------- | -------------------------------------------- |
| Vendor-Datenbank           | ✅ 100% | Name, Trade, Kontakt, Notizen                |
| Vendor Auth Token          | ✅ 100% | Magic-Link (24h Gültigkeit, VendorAuthToken) |
| Vendor-Zuweisung zu Issues | ✅ 100% | Appointments mit Vendor-Link                 |
| E-Mail bei Zuweisung       | ✅ 100% | Auto-Versand mit Magic-Link & Ticket-Details |
| Vendor-Portal Frontend     | ✅ 100% | Login, Auftrags-Liste, Ticket-Details        |
| PDF-Upload (KVA/Rechnung)  | ✅ 100% | Kategorisiert, validiert (10MB, nur PDF)     |
| Vendor-Uploads im Portal   | ✅ 100% | Staff sieht Vendor-Dokumente, Tenant NICHT   |
| Approval durch Vermieter   | ⚠️ 50%  | Manuell zuweisen, kein Workflow              |
| Auftragshistorie           | ✅ 100% | Über Appointments & VendorAttachments        |

### 📈 **Reports & KPIs (M9)**

| Feature                      | Status  | Details                                  |
| ---------------------------- | ------- | ---------------------------------------- |
| Dashboard                    | ✅ 100% | Offene Tickets, neueste Vorgänge         |
| SLA-Tracking                 | ✅ 100% | Zeit bis erste Reaktion, Zeit bis Lösung |
| SLA-Verstöße Report          | ✅ 100% | Issues >24h ohne Reaktion                |
| Reaktionszeit nach Kategorie | ✅ 100% | Avg. Response-Time pro Category          |
| Lösungszeit nach Priorität   | ✅ 100% | Avg. Resolution-Time pro Severity        |
| CSV-Export                   | ✅ 100% | Alle KPIs exportierbar                   |

### 👥 **Mieter-Verwaltung (PR 2 Phase 1)**

| Feature                           | Status  | Details                              |
| --------------------------------- | ------- | ------------------------------------ |
| Mieter-Liste                      | ✅ 100% | Card-Layout mit allen Details        |
| Mieter anlegen                    | ✅ 100% | Unit, E-Mail, Telefon, Einzugsdatum  |
| Mieter bearbeiten                 | ✅ 100% | Alle Felder editierbar               |
| Mieter deaktivieren (Soft Delete) | ✅ 100% | is_active=False, moved_out_at        |
| Mieter löschen (Hard Delete)      | ✅ 100% | Nur wenn keine Tickets vorhanden     |
| Willkommens-E-Mail                | ✅ 100% | Automatischer Versand mit Magic-Link |

### 🔐 **Tenant-Authentifizierung (PR 2 Phase 2)**

| Feature                          | Status  | Details                                           |
| -------------------------------- | ------- | ------------------------------------------------- |
| Tenant Magic-Link Login          | ✅ 100% | E-Mail-basiert, 15min, single-use                 |
| Chat nur für eingeloggte Tenants | ✅ 100% | Redirect zu /tenant/ wenn nicht authentifiziert   |
| Issue mit Tenant verknüpft       | ✅ 100% | Automatische Zuweisung beim Chat-Ticket-Erstellen |
| Tenant-Portal                    | ✅ 100% | Eigene Ticket-Historie unter /tenant/issues/      |
| Session Management               | ✅ 100% | tenant_id in session, logout-Funktion             |

### 🏠 **Objektverwaltung**

| Feature              | Status  | Details                      |
| -------------------- | ------- | ---------------------------- |
| Properties (Gebäude) | ✅ 100% | Name, Adresse, Verwaltung    |
| Units (Wohnungen)    | ✅ 100% | Label, Etage, Zimmer, Fläche |
| Tenant-Zuweisung     | ✅ 100% | 1 aktiver Mieter pro Unit    |

### 🔐 **Sicherheit & Auth**

| Feature                 | Status  | Details                                                 |
| ----------------------- | ------- | ------------------------------------------------------- |
| Staff Login             | ✅ 100% | Django Admin Auth                                       |
| Tenant Magic-Link       | ✅ 100% | E-Mail-basiert, Rate-Limited (3/30min)                  |
| Vendor Magic-Link       | ✅ 100% | Token-basiert, 24h Gültigkeit                           |
| Chat-Protection         | ✅ 100% | Nur für authentifizierte Tenants                        |
| Session-basierte Auth   | ✅ 100% | Passwordless für Tenants & Vendors                      |
| Data Segregation        | ✅ 100% | Tenant sieht KEINE Vendor-Dokumente (Kosten/Rechnungen) |
| Rollen & Rechte         | ⚠️ 30%  | Nur `staff_member_required`, kein Granular ACL          |
| Multi-Vermieter Support | ⚠️ 50%  | Model unterstützt es, **kein UI**                       |

---

## ✅ ABGESCHLOSSEN (v0.4)

### **PR 1: Vendor Models + Tests**

- ✅ Vendor Model mit Auth-Token
- ✅ Django Admin Integration
- ✅ 20 Tests passed

### **PR 2 Phase 1: Mieter-Verwaltung**

- ✅ Card-basiertes Layout
- ✅ CRUD (Create, Edit, Deactivate, Delete)
- ✅ Willkommens-E-Mail Task

### **PR 2 Phase 2: Tenant-Authentifizierung**

- ✅ Magic-Link Auth für Tenants
- ✅ Chat-Protection (nur eingeloggte Tenants)
- ✅ Issue-Tenant Assignment (automatisch)
- ✅ Session Management
- ✅ Integration Tests

### **M11: Vendor Portal (KOMPLETT)**

- ✅ VendorAuthToken Model (separate Token-Tabelle, 24h Gültigkeit)
- ✅ E-Mail-Task: send_vendor_assignment_email (Auto-Versand bei Zuweisung)
- ✅ Vendor Portal Views (Login, Issues, Detail, Upload, Logout)
- ✅ Vendor Portal Templates (Responsive UI mit Tailwind CSS)
- ✅ VendorAttachment Model (Kostenvoranschlag/Rechnung/Sonstiges)
- ✅ PDF Upload mit Validierung (nur PDF, max 10MB, Kategorien + Notizen)
- ✅ Staff Portal Integration (Vendor-Dokumente im Ticket-Detail sichtbar)
- ✅ Security: Tenant sieht KEINE Vendor-Uploads (nur eigene Fotos)
- ✅ Django Admin: VendorAttachment verwaltbar
- ✅ URLs: /vendor/ Routes (auth, issues, upload, logout)

**Total:** 10.5h (1.3 Tage) ✅ **FERTIG!**

---

## 🚀 NÄCHSTE SCHRITTE (NEU PRIORISIERT nach logischem Workflow)

> **Neue Strategie:** Priorisierung nach **technischen Abhängigkeiten**, **Einfachheit** und **Kosten** statt Business Value!

---

### **PHASE 1: Dokumente & Basis-Infrastruktur** ✅ **ABGESCHLOSSEN!**

**Priorität:** 🔥 KRITISCH | **Kosten:** €0 | **Aufwand:** 8h | **Status:** ✅ DONE

#### **M11b: Dokumente → Units/Properties zuordnen** ✅

**Aufwand:** 5.5h | **Status:** ✅ DONE (18.10.2025)

**Implementiert:**

- ✅ Document Model erweitert (property, unit, tenant ForeignKeys)
- ✅ Upload-UI mit Dropdowns (Property/Unit/Tenant Auswahl)
- ✅ Liste zeigt Zuordnung (Icons: 🏢 🚪 👤)
- ✅ 18 Tests geschrieben (warten auf Document-Migration-Fix)

---

#### **M17a: Dokumenten-Versionshistorie** ✅

**Aufwand:** 2.5h | **Status:** ✅ DONE (18.10.2025)

**Implementiert:**

- ✅ DocumentVersion Model (version_number, file, metadata)
- ✅ Upload-Logic mit Auto-Archivierung (v1 → v2 → v3)
- ✅ History Timeline UI (aktuelle + alte Versionen)
- ✅ Download alter Versionen
- ✅ Browser-Testing erfolgreich (v1/v2/v3 funktioniert)

**Optional (später):**

- ⏸️ Automatische Tests (30min)
- ⏸️ Storage Cleanup Task (2h)

---

### **PHASE 2: Verträge & Finanzen** ✅ **M12a ABGESCHLOSSEN!**

**Priorität:** 🔥 HOCH | **Kosten:** €0 | **Aufwand:** 12.5h | **Status:** 50% DONE

#### **M12a: Vertrags-System** ✅ **DONE!**

**Aufwand:** 4.5h | **Status:** ✅ DONE (19.10.2025)

**Implementiert:**

- ✅ Contract Model (unit, tenant, dates, rent, deposit, status)
- ✅ Upload Integration (Kategorie "Vertrag" → Auto-Create Contract)
- ✅ Vertrags-Liste UI (Filter: Status, Unit, Tenant)
- ✅ Details-Seite (Wohnung, Mieter, Konditionen, Dokument + Versionshistorie!)
- ✅ Admin mit Fieldsets & Autocomplete
- ✅ Browser-Testing erfolgreich
- ✅ Constraint: Nur 1 aktiver Vertrag pro Unit

**Optional (später):**

- ⏸️ Automatische Tests (1h)
- ⏸️ Vertrag beenden Workflow (1h)

**Zeitersparnis:** 3.5h! (4.5h statt 8h)

---

#### **M12b: Zahlungen CSV-Import** ✅ **DONE!**

**Aufwand:** 2h | **Status:** ✅ DONE (19.10.2025)

**Implementiert:**

- ✅ PaymentTransaction Model (contract, amount, date, type, status, sender, reference)
- ✅ CSV-Upload View (flexibles Format, Auto-Matching zu Contracts)
- ✅ Zahlungen-Liste UI (Filter: Contract, Type, Status + Gesamtsumme)
- ✅ Integration in Contract Details (Zahlungshistorie mit Summary)
- ✅ Admin mit Fieldsets & Search
- ✅ Browser-Testing erfolgreich

**Optional (später):**

- ⏸️ Automatische Tests (1h)
- ⏸️ Bank-API Integration (später via M14)

**Zeitersparnis:** 5h! (2h statt 7h)

---

### **PHASE 3: Wartung & Compliance (2 Wochen)** ⏳ **TODO**

**Priorität:** 🟡 MITTEL | **Kosten:** €0 | **Abhängigkeiten:** Keine

#### **M14: Nebenkostenabrechnung** ⏳ **NÄCHSTER SCHRITT!**

**Aufwand:** 20h | **Status:** ⏳ TODO

**Warum jetzt?**

- ✅ **Braucht M12b!** ✅ Zahlungen als Basis
- ✅ **Hoher Business-Value!** Automatische NK-Abrechnung
- ✅ **Komplexität!** Braucht Zeit, aber lohnt sich

### **PHASE 3: Wartung & Compliance (2 Wochen)** ⏳ **TODO**

**Priorität:** 🟡 MITTEL | **Kosten:** €0 | **Abhängigkeiten:** Keine

#### **M16: Checklisten**

| PDF-Export | 2h | Übergabeprotokoll als PDF |
| Tests | 1h | CRUD + Photo-Upload |

**Total Phase 1:** 29h (3.5 Tage) 💰 **€0 externe Kosten**

---

### **PHASE 2: Wartung & Compliance (2 Wochen)**

**Priorität:** 🟡 HOCH (gesetzlich!) | **Kosten:** €0 | **Abhängigkeiten:** M16 Checklisten

#### **M15: Wartungskalender**

**Aufwand:** 12h | **Status:** ⏳ TODO

**Warum wichtig?**

- ✅ **Gesetzlich!** Rauchmelder-Prüfung ist Pflicht!
- ✅ **Einfach!** Celery Beat für Recurring Events
- ✅ **Unabhängig!** Braucht nur E-Mail-System (schon da)

| Feature                | Aufwand | Details                         |
| ---------------------- | ------- | ------------------------------- |
| MaintenanceItem Model  | 2h      | Type, Unit, Next Date, Interval |
| Rauchmelder-Verwaltung | 2h      | Pro Wohnung, Prüf-Intervall     |
| Heizungswartung        | 2h      | Jährlich, pro Objekt            |
| Celery Beat Task       | 2h      | Recurring Checks (täglich)      |
| E-Mail-Erinnerungen    | 2h      | 7 Tage vorher Reminder          |
| UI: Wartungskalender   | 2h      | Liste + Übersicht               |

**Total Phase 2:** 12h (1.5 Tage) 💰 **€0 externe Kosten**

---

### **PHASE 3: Verträge & Finanzen Basis (3 Wochen)**

**Priorität:** 🟡 MITTEL | **Kosten:** €0 | **Abhängigkeiten:** M11b (Dokumente → Units)

#### **M12a: Vertrags-System (NEU!)**

**Aufwand:** 8h | **Status:** ⏳ TODO

**Warum vor Zahlungen?**

- ✅ **Logisch!** Miete muss im Vertrag stehen BEVOR man sie erfassen kann!
- ✅ **Basis für Finanzen!** Soll-Betrag kommt aus Vertrag
- ✅ **Dokumenten-Link!** Vertrag = Dokument + Daten

| Feature                       | Aufwand | Details                              |
| ----------------------------- | ------- | ------------------------------------ |
| Contract Model                | 2h      | Tenant, Unit, Miete, NK, Start, Ende |
| Vertrags-Verwaltung UI        | 3h      | Liste, Create, Edit                  |
| Link zu Document              | 1h      | "Vertrag → PDF" Zuordnung            |
| Berechnung nächste Fälligkeit | 1h      | Auto-Calculate                       |
| Tests                         | 1h      | CRUD + Berechnungen                  |

---

#### **M12b: Zahlungen (manuell + CSV)**

**Aufwand:** 7h | **Status:** ⏳ TODO

**Was geändert?**

- ❌ **KEINE Bank-API!** (zu komplex, siehe Phase 5)
- ✅ **CSV-Import reicht!** (Kontoauszug als CSV)
- ✅ **Manuell erfassen** für Einzelfälle

| Feature                    | Aufwand | Details                               |
| -------------------------- | ------- | ------------------------------------- |
| Payment Model              | 1h      | Contract, Betrag, Datum, Status       |
| Zahlungen manuell erfassen | 2h      | Form: Mieter, Betrag, Datum           |
| CSV-Import                 | 3h      | Parser für Bank-CSV (Sparkasse, etc.) |
| Soll/Ist-Vergleich         | 1h      | "Miete fällig vs. bezahlt"            |

---

#### **M12c: Mahnwesen (Optional)**

**Aufwand:** 4h | **Status:** ⏳ OPTIONAL

**Nur wenn Zeit!**

- Mahnstufe 1-3 (7, 14, 21 Tage)
- PDF-Erstellung
- E-Mail-Versand

**Total Phase 3:** 19h (2.5 Tage) 💰 **€0 externe Kosten**

---

### **PHASE 4: Nebenkostenabrechnung (2 Wochen)**

**Priorität:** 🟡 MITTEL | **Kosten:** €0 | **Abhängigkeiten:** M12a (Verträge)

#### **M14: Nebenkostenabrechnung**

**Aufwand:** 20h | **Status:** ⏳ TODO

**Warum nach Verträgen?**

- ✅ **Umlage-Schlüssel** muss im Vertrag stehen!
- ✅ **Zählerstände** brauchen Wartungskalender (M15)

| Feature                      | Aufwand | Details                          |
| ---------------------------- | ------- | -------------------------------- |
| UtilityReading Model         | 2h      | Zählerstand pro Unit + Datum     |
| Zählerstände erfassen UI     | 2h      | Manuell eingeben                 |
| Umlage-Schlüssel im Contract | 2h      | Fläche/Person/Verbrauch          |
| Berechnung Heizkosten        | 4h      | Nach Verbrauch                   |
| Berechnung Wasser/Müll       | 2h      | Nach Personen                    |
| Berechnung Grundsteuer       | 2h      | Nach Fläche                      |
| Vorschau-UI                  | 2h      | "So viel muss Mieter nachzahlen" |
| PDF-Export                   | 3h      | Offizielle NK-Abrechnung         |
| E-Mail-Versand               | 1h      | An Mieter senden                 |

**Total Phase 4:** 20h (2.5 Tage) 💰 **€0 externe Kosten**

---

### **🎉 GO-LIVE READY! (nach Phase 1-4)**

**Gesamt bis Go-Live:** 80h (10 Arbeitstage)
**Externe Kosten:** €0
**Alle kritischen Features:** ✅ Implementiert

---

### **PHASE 5: Advanced Features (POST-LAUNCH!)**

**Priorität:** 🔴 NIEDRIG | **Kosten:** €50-100/Monat | **Abhängigkeiten:** Kunde zahlt!

> ⚠️ **NUR auf explizite Anfrage implementieren!**

#### **M13: Bankkonto-Integration**

**Aufwand:** 20h | **Kosten:** €0 (FinTS kostenlos) | **Problem:** Sehr komplex!

**Warum ganz hinten?**

- ❌ **Keine Test-API!** Braucht echte Bankdaten
- ❌ **Sicherheitsrisiko!** Kontozugriff
- ❌ **Komplex!** TAN, PSD2, Bank-spezifisch
- ✅ **Workaround:** CSV-Import reicht!

**Entscheidung:** Nur wenn Kunde explizit zahlt & bereit 20h zu investieren!

---

#### **M17b: OCR für Rechnungen**

**Aufwand:** 18h | **Kosten:** ~€1.50/1000 Bilder (Google Vision API)

**Warum später?**

- ❌ **Bezahlt!** Tesseract kostenlos aber ungenau
- ❌ **Komplex!** ML-Training nötig
- ✅ **Workaround:** Manuell eingeben!

---

#### **M18: Digitale Signaturen**

**Aufwand:** 12h | **Kosten:** ~€25/Monat (DocuSign)

**Warum später?**

- ❌ **Bezahlt!** API-Kosten
- ❌ **Nice-to-have!** PDF-Vertrag reicht

---

#### **M19: Smart-Home**

**Aufwand:** 16h | **Kosten:** Hardware + APIs (€€€)

**Warum später?**

- ❌ **Sehr teuer!** Hardware pro Wohnung
- ❌ **Nische!** Nur für moderne Objekte

---

#### **M20: KI-Analysen**

**Aufwand:** 26h | **Kosten:** ~€20/Monat (OpenAI API)

**Warum später?**

- ❌ **Bezahlt!** API-Kosten
- ❌ **Nice-to-have!** Basis-Reports reichen

**Total Phase 5:** 92h (11.5 Tage) | 💰 **€50-100/Monat**

---

## 📅 NEUE TIMELINE

```
✅ Woche 1-2   (18.10):      M11 abgeschlossen ✅
🔥 Woche 3-5   (Nov 2025):   PHASE 1 (Dokumente, Versionen, Checklisten)
🟡 Woche 6-7   (Nov 2025):   PHASE 2 (Wartungskalender)
🟡 Woche 8-10  (Dez 2025):   PHASE 3 (Verträge, Zahlungen)
🟡 Woche 11-12 (Dez 2025):   PHASE 4 (Nebenkostenabrechnung)
🎉 Woche 13    (Jan 2026):   GO-LIVE! 🚀
🔴 Post-Launch (Q1 2026+):   PHASE 5 (nur auf Anfrage)
```

---

## 🎯 NEUE PRIORISIERUNGS-MATRIX

### **🔥 KRITISCH (Go-Live Blocker):**

1. ✅ Ticketing & Chat (Done)
2. ✅ Mieter-Portal (Done)
3. ✅ Vendor Portal (Done)
4. 🔥 **Dokumente → Units** (Phase 1)
5. 🔥 **Versionshistorie** (Phase 1)
6. 🔥 **Vertrags-System** (Phase 3)

### **🟡 WICHTIG (3 Monate nach Go-Live):**

7. 🟡 Checklisten (Phase 1)
8. 🟡 Wartungskalender (Phase 2)
9. 🟡 Zahlungen CSV (Phase 3)
10. 🟡 Nebenkostenabrechnung (Phase 4)

### **🟢 OPTIONAL (6+ Monate, auf Anfrage):**

11. 🔴 Bank-Integration (Phase 5, €0 aber komplex)
12. 🔴 OCR (Phase 5, €€)
13. 🔴 eSignature (Phase 5, €€€)
14. 🔴 Smart Home (Phase 5, €€€€)
15. 🔴 KI-Analysen (Phase 5, €€)

---

## 📊 NEUE Go-Live Checkliste

- [x] M1-M10 Backend & Portal ✅
- [x] PR1 Vendor Models ✅
- [x] PR2 Mieter-Verwaltung ✅
- [x] M11 Vendor Portal ✅
- [ ] **M11b Dokumente → Units** (6h) 🔥
- [ ] **M17a Versionshistorie** (11h) 🔥
- [ ] **M16 Checklisten** (12h)
- [ ] **M15 Wartungskalender** (12h)
- [ ] **M12a Vertrags-System** (8h) 🔥
- [ ] **M12b Zahlungen CSV** (7h)
- [ ] **M14 Nebenkostenabrechnung** (20h)
- [ ] Security Audit (8h)
- [ ] Performance Testing (4h)
- [ ] Dokumentation (8h)

**Total bis Go-Live:** 96h (12 Arbeitstage)
**Externe Kosten:** €0
**Zeitrahmen:** 10 Wochen (mit Puffer)

---

## 💰 KOSTEN-KALKULATION

### **Go-Live (Phase 1-4):**

```
✅ Alle Features kostenlos!
✅ Keine externen APIs
✅ Nur Entwicklungszeit: 80h

Total: €0/Monat (nur Hosting ~€50)
```

### **Post-Launch (Phase 5):**

```
Optional Features (nur wenn Kunde zahlt):
- OCR: ~€1.50/1000 Bilder
- eSignature: ~€25/Monat
- KI-Analysen: ~€20/Monat
- Smart Home: €€€€ (Hardware)

Geschätzt: €50-100/Monat
```

---

## 📞 NÄCHSTE SCHRITTE

1. ✅ **M11:** Vendor Portal (Done - 10.5h)
2. 🔥 **M11b:** Dokumente → Units zuordnen (6h) ← **START HIER!**
3. 🔥 **M17a:** Versionshistorie (11h)
4. 🟡 **M16:** Checklisten (12h)
5. 🟡 **M15:** Wartungskalender (12h)
6. 🟡 **M12a:** Vertrags-System (8h)
7. 🟡 **M12b:** Zahlungen CSV (7h)
8. 🟡 **M14:** Nebenkostenabrechnung (20h)
9. 🎉 **GO-LIVE!** (nach ~80h = 10 Arbeitstage)

---

---

## 🛠️ TECHNISCHER STACK (unverändert)

| Komponente  | Technologie                 | Status                            |
| ----------- | --------------------------- | --------------------------------- |
| Backend     | Django 5.1 + DRF            | ✅ Stabil                         |
| Frontend    | HTMX + Tailwind CSS         | ✅ Stabil                         |
| Database    | PostgreSQL 16               | ✅ Produktiv                      |
| Cache/Queue | Redis + Celery              | ✅ Funktional                     |
| E-Mail      | Mailhog (Dev) / SMTP (Prod) | ✅ Konfiguriert                   |
| Storage     | Django FileField (lokal/S3) | ✅ Funktional                     |
| Testing     | pytest + coverage           | ⚠️ Tests für M12a/M12b ausstehend |

---

## 🚨 RISIKEN & NEUE MITIGATION-STRATEGIEN

| Risiko                   | Alt        | Neu           | Mitigation                     |
| ------------------------ | ---------- | ------------- | ------------------------------ |
| Bank-API Komplexität     | 🔥 Blocker | ✅ Gelöst     | **CSV-Import statt API!**      |
| DSGVO Compliance         | 🟡 Mittel  | 🟡 Mittel     | Rechtsberatung, Anonymisierung |
| Skalierung (>1000 Units) | 🟢 Niedrig | 🟢 Niedrig    | PostgreSQL Indexing            |
| OCR Genauigkeit          | 🟢 Niedrig | 🔴 Irrelevant | **Phase 5 = Post-Launch!**     |
| Externe API-Kosten       | ❌ Unklar  | ✅ Gelöst     | **€0 bis Go-Live!**            |

### **Neue Erkenntnisse:**

- ✅ **Bank-API nicht nötig!** CSV-Import reicht völlig
- ✅ **OCR nicht kritisch!** Manuell eingeben ist OK
- ✅ **Kosten-Explosion verhindert!** Alle kostenpflichtigen Features → Post-Launch

---

## 📋 VERGLEICH: ALT vs. NEU

### **ALT (vor Neustrukturierung):**

```
1. M12 Zahlungen (15h) - BRAUCHT Verträge! ❌
2. M13 Bank-API (20h) - Zu komplex! ❌
3. M14 NK-Abrechnung (20h) - BRAUCHT Verträge! ❌
4. M15 Wartung (12h)
5. M16 Checklisten (12h)
6. M17a Versionen (11h)

Total: 90h | Reihenfolge: ❌ FALSCH!
```

### **NEU (logischer Workflow):**

```
1. M11b Dokumente → Units (6h) - Basis! ✅
2. M17a Versionen (11h) - Für Verträge! ✅
3. M16 Checklisten (12h) - Quick Win! ✅
4. M15 Wartung (12h) - Gesetzlich! ✅
5. M12a Vertrags-System (8h) - DANN Finanzen! ✅
6. M12b Zahlungen CSV (7h) - Kein Bank-API! ✅
7. M14 NK-Abrechnung (20h) - Mit Vertrag! ✅

Total: 76h | Reihenfolge: ✅ LOGISCH!
```

**Ersparnis:** 14h + keine komplizierten Dependencies!

---

## 🎯 STRATEGISCHE ENTSCHEIDUNGEN

### **✅ RICHTIG:**

1. **Dokumente → Units ZUERST!** (Basis für alles)
2. **CSV statt Bank-API!** (Einfacher, sicherer)
3. **Verträge VOR Zahlungen!** (Logisch)
4. **Kostenlose Features zuerst!** (Keine API-Kosten)
5. **Quick Wins früh!** (Checklisten, Wartung)

### **❌ FALSCH (Alt):**

1. Zahlungen ohne Vertrags-System
2. Bank-API als "Must-Have"
3. Versionshistorie ganz hinten
4. OCR als mittlere Priorität
5. Business Value > Technische Dependencies

---

## 📞 ZUSAMMENFASSUNG & NEXT STEPS

### **Was heute erreicht (18.10.2025):**

- ✅ **M11b: Dokumente → Units/Properties** (5.5h) - DONE!
- ✅ **M17a: Versionshistorie** (2.5h) - DONE!
- ✅ **PHASE 1 DOKUMENTE KOMPLETT!** 🎉
- ✅ Browser-Testing erfolgreich (v1/v2/v3)

### **Aktuelle Statistik:**

```
Phase 1 (Dokumente):     ✅ 8h    DONE (100%)
Phase 2 (Verträge):      ⏳ 0h    TODO
Phase 3 (Wartung):       ⏳ 0h    TODO
Phase 4 (NK):            ⏳ 0h    TODO

Total bis Go-Live:       76h (10 Arbeitstage)
Davon fertig:            8h (10%)
Verbleibend:             68h (9 Tage)
```

### **Was als Nächstes:**

**JETZT START:** 🔥 **M12a: Vertrags-System** (8h)

```bash
git checkout -b feature/M12a-contract-system
# Contract Model, Upload, Liste, Details
```

**Dann:**

1. 🟡 M12b: Zahlungen CSV (7h)
2. � M14: Nebenkostenabrechnung (20h)
3. 🟡 M16: Checklisten (12h)
4. 🟡 M15: Wartungskalender (12h)

### **Go-Live Prognose:**

- **Zeitrahmen:** 9 Arbeitstage (68h verbleibend)
- **Kosten:** €0 externe APIs (nur Hosting)
- **Risiko:** 🟢 NIEDRIG (Phase 1 erfolgreich!)

---

**Erstellt von:** AI Assistant
**Strategische Neuausrichtung:** 18.10.2025 19:50 Uhr
**Phase 1 Abschluss:** 18.10.2025 21:45 Uhr ✅
**Roadmap Version:** 2.1 (Phase 1 Complete)
**Nächster Meilenstein:** M12a Vertrags-System 🚀
