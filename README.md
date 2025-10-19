# 🏢 UVM – Universal Vermieter Management

**Version:** 0.9.0 (Development)
**Status:** 32% Complete (24.5h / 76h)
**Repository:** https://github.com/Duly330AI/uvm

---

## 📊 Projekt-Status

### **Implementierte Features:**

```
✅ Phase 1: Dokumente (8h DONE)
   - M11b: Documents → Units/Properties
   - M17a: Document Version History

✅ Phase 2: Verträge (4.5h DONE)
   - M12a: Contract Management System

✅ Phase 3: Zahlungen (2h DONE)
   - M12b: Payment CSV Import

✅ Phase 4: Nebenkostenabrechnung (10h DONE → 1.5h actual!)
   - M14: Utility Readings & Cost Calculation
   - ✓ Zählerstand-Erfassung (Wasser, Strom, Gas, Heizung)
   - ✓ Automatische Verbrauchsberechnung
   - ✓ 4 Umlage-Schlüssel (Fläche, Personen, Verbrauch, Units)
   - ✓ HeizkostenV-konforme Berechnung (30% Grund + 70% Verbrauch)
   - ✓ Vorschuss-Berechnung & Nachzahlung/Guthaben
   - ✓ CSV-Export (PDF optional)
   - ✓ 14 Tests (90 total passed)
```

### **Nächste Schritte:**

```
⏳ M16: Checklisten (12h → ~6h)
⏳ M15: Wartungskalender (12h → ~6h)
⏳ M13: Workflow-Management (8h → ~4h)
```

**Siehe:** [ROADMAP.md](./ROADMAP.md) für Details

---

## 🚀 Quick Start

### **Voraussetzungen:**

- Docker & Docker Compose
- Ports: 8000, 8025, 5432, 6379

### **1. Repository klonen:**

```bash
git clone https://github.com/Duly330AI/uvm.git
cd uvm
```

### **2. Environment Setup:**

```powershell
Copy-Item .env.example .env
```

### **3. Build & Start:**

```powershell
docker compose up --build -d
```

### **4. Datenbank migrieren:**

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### **5. Öffnen:**

- **Portal:** http://localhost:8000/portal/
- **Admin:** http://localhost:8000/admin/
- **Mailhog:** http://localhost:8025/

---

## 🧪 Testing & Quality

### **Tests ausführen:**

```powershell
docker compose exec web pytest -q
```

**Aktueller Stand:** 90 Tests passing, Coverage ~72%

### **Coverage Report:**

```powershell
docker compose exec web pytest --cov=landlord --cov-report=html
```

Coverage Report: `backend/app/htmlcov/index.html`

### **Linting:**

```powershell
# In Container
docker compose exec web ruff check .
docker compose exec web black --check .

# Lokal (mit .venv aktiviert)
ruff check .
black --check .
```

---

## 📦 Services (Docker Compose)

| Service | Port | Beschreibung      |
| ------- | ---- | ----------------- |
| web     | 8000 | Django + Gunicorn |
| worker  | -    | Celery Worker     |
| beat    | -    | Celery Beat       |
| db      | 5432 | PostgreSQL 16     |
| redis   | 6379 | Redis 7           |
| mailhog | 8025 | SMTP Dev Server   |

---

## 🔧 Development

### **Feature Branch erstellen:**

```bash
git checkout -b feature/M14-nebenkostenabrechnung
```

### **Code ändern & committen:**

```bash
git add .
git commit -m "feat: Add Nebenkostenabrechnung feature"
git push -u origin feature/M14-nebenkostenabrechnung
```

### **Django Shell:**

```powershell
docker compose exec web python manage.py shell
```

### **Logs ansehen:**

```powershell
docker compose logs -f web
docker compose logs -f worker
```

---

## 📚 Dokumentation

- **[ROADMAP.md](./ROADMAP.md)** - Feature-Roadmap & Priorisierung
- **[docs/SPEC_v_0_5_19_10.md](./docs/uvm_universal_vermieter_managment_SPEC_v_0_5_19_10.md)** - Technical Specification
- **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Deployment Guide

---

## 🔒 Environment-Variablen

Siehe [.env.example](./.env.example) für alle verfügbaren Optionen.

**Wichtige Variablen:**

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=landlord
POSTGRES_USER=landlord
POSTGRES_PASSWORD=landlord123

# Email (Dev)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mailhog
EMAIL_PORT=1025
```

---

## 🎯 Features

### **✅ Implementiert:**

- Chat-basierte Anliegen-Meldung
- Ticket-Verwaltung (Status-Workflow)
- Mieter-Portal (Magic-Link Auth)
- Vendor-Portal (Handwerker)
- Dokumenten-Management mit Versionshistorie
- Vertrags-Verwaltung
- Zahlungen CSV-Import
- Reports & KPIs

### **⏳ In Entwicklung:**

- Nebenkostenabrechnung
- Checklisten (Wohnungsübergabe)
- Wartungskalender

---

## 📞 Health Checks

```bash
# API Health
GET http://localhost:8000/healthz
→ { "status": "ok", "db": true, "redis": true }

# API Ping
GET http://localhost:8000/api/ping/
→ { "pong": true }
```

---

## 🛠️ Tech Stack

- **Backend:** Django 5.1, Python 3.12
- **Frontend:** HTMX, TailwindCSS, Alpine.js
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis 7 + Celery
- **Storage:** Local FileSystem (S3-ready)
- **Email:** Mailhog (Dev) / SMTP (Prod)

---

## 📈 Projektfortschritt

```
Total bis Go-Live: 76h (10 Arbeitstage)
Fertig: 14.5h (19%)
Verbleibend: 61.5h (8 Tage)

Features:
✅ M11b: Dokumente → Units (5.5h)
✅ M17a: Versionshistorie (2.5h)
✅ M12a: Vertrags-System (4.5h)
✅ M12b: Zahlungen CSV (2h)

Nächste:
⏳ M14: Nebenkostenabrechnung (20h)
⏳ M16: Checklisten (12h)
⏳ M15: Wartungskalender (12h)
```

---

## 🤝 Contributing

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'feat: Add AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

---

## 📄 License

Private Repository - All Rights Reserved

---

**Erstellt von:** AI Assistant
**Letzte Aktualisierung:** 19.10.2025 03:00 Uhr
**Version:** 0.8.0 (M12a + M12b Complete)
