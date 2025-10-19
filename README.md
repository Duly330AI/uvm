# UVM – Universal Vermieter Management (M1)

Diese README beschreibt das MVP‑Gerüst (M1) gemäß SPEC. Ziel: docker compose up bringt ein lauffähiges Django/DRF‑Gerüst mit Health‑Endpoints, Admin und Test‑Mail.

## Voraussetzungen

- Docker & Docker Compose
- Port 8000, 8025, 9000/9001 frei

## Setup & Run

1. .env erstellen

```powershell
Copy-Item .env.example .env
```

2. Build & Start

```powershell
docker compose up --build
```

Warten bis `web` healthy ist und auf http://localhost:8000 erreichbar.

3. Datenbank migrieren & Superuser anlegen (neues Terminal)

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

4. Health Checks

- GET http://localhost:8000/healthz → `{ "status": "ok", "db": true, "redis": true }`
- GET http://localhost:8000/api/ping/ → `{ "pong": true }`

5. Admin

- http://localhost:8000/admin/

6. Test‑Mail (soll in Mailhog erscheinen)

```powershell
docker compose exec web python manage.py send_test_mail you@example.com
```

- Mailhog UI: http://localhost:8025

## Lint & Format

Ruff & Black sind konfiguriert.

```powershell
ruff check .
black --check .
```

## Tests

```powershell
docker compose exec web pytest -q
```

## Environment‑Variablen

Siehe `.env.example`. In dev wird Mailhog verwendet, S3 ist optional (USE_S3=false). In prod `ALLOWED_HOSTS` eng setzen und Security‑Flags aktivieren.

## Services (Compose)

- web: Django + Gunicorn (UvicornWorker)
- worker: Celery Worker
- beat: Celery Beat
- db: PostgreSQL 16
- redis: Redis 7
- minio: S3‑kompatibles Storage (dev)
- mailhog: SMTP Dev

## Hinweis

M1 enthält noch keine Domain‑Modelle oder Chat‑FSM. Das folgt in M2.
