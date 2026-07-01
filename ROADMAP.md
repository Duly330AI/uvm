# 🗺️ UVM Roadmap (Stand 2025-10-23)

**Projektstatus:** Advanced MVP / portfolio prototype · **MVP-Module:** M1–M16 implementiert · **Rest:** optionale Erweiterungen (M17–M20)

---

## ✅ Meilenstein-Übersicht (M1–M16)
| ID | Modul | Status | Notizen |
| --- | --- | --- | --- |
| M1 | Chat-Erfassung | ✅ | FSM v2, Validierung, Severity-Heuristik |
| M2 | Ticket-Workflow | ✅ | SLA-Tracking, Audit-Logs, Portal-Badges |
| M3 | Tenant-Portal | ✅ | Magic-Link Login, DSGVO-orientierte Namensfelder |
| M4 | Vendor-Portal | ✅ | Auftragszuweisung, Token-Handling |
| M5 | Issue Notes/Attachments | ✅ | Async Uploads, Finalize Task |
| M6 | Reporting & KPIs | ✅ | 30‑Tage Dashboard mit Cache |
| M7 | Document Storage | ✅ | Objekt-/Einheits-Zuordnung |
| M8 | Document Versioning (M17a) | ✅ | DocumentVersion, Timeline |
| M9 | Contract Management | ✅ | Vertrags-CRUD, Tenant Binding |
| M10 | Payment CSV Import | ✅ | HMAC-Signatur, O(N)-Matching |
| M11 | Utility Meter & Billing | ✅ | HeizkostenV-orientierter Calculator |
| M12 | Nebenkostenabrechnung | ✅ | Verbrauchs-/Vorschuss-Berechnung |
| M13 | Checklisten | ✅ | Ein-/Auszug, Wartung, PDF-Export |
| M14 | Wartungskalender | ✅ | Overdue Detection, Staff Assignment |
| M15 | Audit & Monitoring | ✅ | Immutable Logs, Sentry ready |
| M16 | Deployment/Operations | ✅ | Guide, Runbook, Health Checks |

**Zeitbudget:** 40 h Refactoring (Phase 1–4) · **Ist:** 40 h/40 h abgeschlossen

---

## 📋 Geplante Erweiterungen (M17–M20)
| ID | Feature | Status | Ziel |
| --- | --- | --- | --- |
| M17b | OCR & Dokument-Automation | 📋 | Belegerkennung, Smart Tags |
| M18 | Bank-/Buchhaltungs-APIs | 📋 | Kontoabgleich, DATEV-Export |
| M19 | Analytics & Self-Service Dashboards | 📋 | KPIs für Eigentümer:innen |
| M20 | Optionale Integrationen | 📋 | Drittsysteme, SSO |

> Priorität abhängig von fachlicher Prüfung und Projektziel.

---

## 🧭 Timeline & Fortschritt
- **T0 (2025-10-20):** Codex-Audit, 62/100 → Maßnahmenplan
- **T1 (2025-10-22):** Phase 1 & 2 abgeschlossen (Security, Performance)
- **T2 (2025-10-23):** Phase 3 & 4 abgeschlossen (Code Quality, Monitoring)
- **Heute:** fortgeschrittener MVP-Snapshot, interner Review-Score 90/100, Coverage ~80 %
- **Nächste Meilensteine:** Entscheidung über M17–M20 Umfang & Budget

---

## 🔍 Referenzen
- [docs/MASTER_ACTION_PLAN.md](./docs/MASTER_ACTION_PLAN.md)
- [docs/MASTER_ACTION_PLAN_DONE.md](./docs/MASTER_ACTION_PLAN_DONE.md)
- [docs/codex_executive_summary.md](./docs/codex_executive_summary.md)
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

---

## 📝 Notizen
- Sämtliche „44 %“-Angaben entfernt – aktuelle Kennzahl: **80 %**
- Tenant-Modell erweitert (Migration `0026_add_tenant_names.py`)
- Test Suite +26 Fälle → 384 Gesamttests, 7 Skips dokumentiert
- Coverage-Aufholjagd abgeschlossen (validators/public_link 100 %)

