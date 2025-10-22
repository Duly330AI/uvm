# UVM Performance Audit – Executive Summary

**Audit Datum:** 2025-10-22  
**Geprüfte Codebase:** `backend/app/landlord`, `backend/app/config`

## 🎯 Overall Score: 62/100
Stabile Basis, aber zentrale Sicherheits- und Infrastrukturthemen verhindern Produktionsreife. Kritische Patches (Gunicorn, Django-Settings, CSV-Leistung) haben höchste Priorität.

## 🔴 Critical Issues (Top 5)
1. **Gunicorn 22.0.0 Request-Smuggling** — `pyproject.toml` (TASK 1)  
   Upgrade auf `23.0.0`, Build & Regression-Tests ausführen.
2. **Prod-EntryPoints laden Dev-Settings** — `config/wsgi.py:5`, `config/asgi.py:5`, `config/celery_app.py:5` (TASK 5)  
   Standard auf `config.settings.prod` setzen, sonst bleiben DEBUG und offene Hosts aktiv.
3. **OSS-SECRET_KEY-Fallback „change-me“** — `config/settings/base.py:20` (TASK 5)  
   Harte Fail-Fast-Validierung + Secret Rotation erforderlich.
4. **CSV-Import skaliert nicht** — `landlord/views_payments.py:118` (TASK 6)  
   `Contract.objects.filter` pro Zeile sorgt für O(N×M)-Queries; Lookup-Caching implementieren.
5. **Chat FSM ohne Tests / hohe Komplexität** — `landlord/fsm.py:24` (TASK 3 + TASK 4)  
   State-Handler refaktorisieren und Unit-Tests ergänzen, um Regressionen zu verhindern.

## 🟡 Medium Issues (Top 10)
1. **pip CVE-2025-8869** — Container-Build (`pip==25.2`) → Update auf 25.3 sobald verfügbar (TASK 1).  
2. **Celery-Mail-Spikes ohne Concurrency-Limit** — `config/settings/base.py:70` (TASK 6).  
3. **ChatMessageView.post Monolith** — `landlord/views.py:163` (TASK 3) → Helfer extrahieren, Tests ergänzen.  
4. **UtilityMeterService Branch-Explosion** — `services/utility_meter_service.py:32` (TASK 3).  
5. **REST-API Defaults erlauben Anonymous** — `config/settings/base.py` → `DEFAULT_PERMISSION_CLASSES` setzen (TASK 5).  
6. **Tenants-API GDPR-Duplikate** — `landlord/api/tenants.py:83` → Idempotenz & Tests erweitern (TASK 4).  
7. **Payment-Listen ohne Pagination** — `landlord/views_payments.py:24` (TASK 6).  
8. **Reports-KPIs ohne Cache** — `landlord/views_reports.py:18` (TASK 6).  
9. **FSM-Regex & Validierung im Serializer verteilt** — `landlord/serializers.py:40` (TASK 3).  
10. **Coverage 69 % / Config ungemessen** — `coverage.xml`, `pyproject.toml:56` → Tests & Quellumfang erweitern (TASK 4).

## 📊 Metriken
- **Security:** 1 kritische, 1 mittlere Abhängigkeitsschwachstelle; 3 Django Deploy-Warnungen.  
- **Performance:** 2 kritische (CSV, Zahlungslisten), 3 mittlere Engpässe (Chat-Uploads, KPIs, Celery).  
- **Code Quality:** 24 Funktionen ≥ CC C; 2 Hotspots (FSM `46`, Chat View `40`).  
- **Test Coverage:** 69 % Linienabdeckung; Schlüsselmodule (`auth.py`, `fsm.py`, `chat_session.py`) <20 %.

## 🚀 Nächste Schritte (Priorisierte Fixes)
1. **Security Patch & Settings-Hardening** (8 h)  
   Gunicorn → 23.0.0, SECRET_KEY-Fallback entfernen, EntryPoints auf Prod-Settings umstellen, deploy check mit Prod-Profil automatisieren.
2. **CSV-Import & Payment-UI skalieren** (10 h)  
   Vertrags-Lookups cachen, Aggregationen/Pagination einführen, Benchmark hinzufügen.
3. **Chat-FSM & API Stabilisierung** (12 h)  
   State-Handler refaktorieren, Message-View in Helpers, umfassende Unit-/Integrationstests.
4. **Test Coverage auf 80 % anheben** (12 h)  
   Kritische Module testen (auth, FSM, chat_session, tenants API), Coverage-Quelle um `config` erweitern.
5. **Celery & KPI Performance Tuning** (6 h)  
   Email-Queue-Konfiguration, KPI-Caching, Chat-Anhang-Transfer in Hintergrundtask verschieben.

**Geschätzter Gesamtaufwand:** ~48 h bis Produktionsreife.
