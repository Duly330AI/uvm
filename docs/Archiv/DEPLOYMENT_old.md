# Legacy Deployment Notes

## P0 Produktions-Härtung ✅

Dieses Setup verwendet Gunicorn + Uvicorn Workers, WhiteNoise für Static Files, optionales S3/MinIO für Media und Security-Hardening.

---

## Voraussetzungen

- Docker & Docker Compose
- Domain mit SSL-Zertifikat (z.B. via Let's Encrypt/Certbot)
- SMTP-Server für E-Mail-Versand
- Optional: S3-kompatibler Storage (MinIO, AWS S3, etc.)

---

## Schnellstart (Lokal-Prod-Test)

### 1. Secret Key generieren

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 2. `.env` Datei erstellen

```bash
cp .env.prod.example .env
# Bearbeite .env mit deinen Werten (siehe unten)
```

### 3. Build & Start

```bash
# Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
```

### 4. Superuser anlegen

```bash
docker compose exec web python manage.py createsuperuser
```

### 5. Testen

```bash
# Health Check
curl http://localhost:8000/healthz

# Admin (Static Files via WhiteNoise)
open http://localhost:8000/admin/

# Portal
open http://localhost:8000/portal/
```

---

## Umgebungsvariablen (.env)

### Pflicht

```env
SECRET_KEY=<dein-generierter-key>
DJANGO_ALLOWED_HOSTS=example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com
POSTGRES_PASSWORD=<change-me>
```

### Email (SMTP)

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### S3/MinIO (optional)

```env
USE_S3=true
AWS_ACCESS_KEY_ID=<minio-access-key>
AWS_SECRET_ACCESS_KEY=<minio-secret>
AWS_STORAGE_BUCKET_NAME=uvm-uploads
AWS_S3_ENDPOINT_URL=http://minio:9000
```

---

## Production Features

### ✅ Gunicorn + Uvicorn

- 2 Worker-Prozesse (anpassen via `--workers` in docker-compose.prod.yml)
- ASGI-Support für WebSocket (vorbereitet)

### ✅ WhiteNoise

- Statische Dateien (CSS, JS, Admin-Assets) werden komprimiert und mit Hash ausgeliefert
- `collectstatic` wird automatisch beim Start ausgeführt (via entrypoint.sh)

### ✅ Security Headers

- `SECURE_SSL_REDIRECT=1` (nur hinter HTTPS-Proxy)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- HSTS mit 1 Jahr (konfigurierbar)

### ✅ S3/MinIO für Media

- Aktivierbar via `USE_S3=true`
- Cache-Control: 24h für Uploads
- Private ACL (signed URLs)

### ✅ Redis Cache

- Default-Cache nutzt Redis statt In-Memory
- Session-Cache via Django-Redis

---

## Deployment Checkliste

- [ ] `.env` erstellt mit allen Pflicht-Variablen
- [ ] Secret Key generiert und gesetzt
- [ ] ALLOWED_HOSTS auf Domain(s) gesetzt
- [ ] CSRF_TRUSTED_ORIGINS mit `https://` Prefix
- [ ] SMTP-Credentials konfiguriert
- [ ] SSL-Zertifikat via Reverse-Proxy (nginx/Caddy/Traefik)
- [ ] `docker compose build` erfolgreich
- [ ] Migrations gelaufen (`entrypoint.sh` macht das automatisch)
- [ ] `collectstatic` erfolgreich (siehe Container-Logs)
- [ ] Superuser angelegt
- [ ] `/healthz` gibt 200 zurück
- [ ] Admin-Login funktioniert
- [ ] Static Files laden (keine 404 in Browser-Console)
- [ ] File-Upload & Download funktioniert (S3/MinIO)

---

## Monitoring & Logs

### Logs anzeigen

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f worker
```

### Health Check

```bash
curl http://localhost:8000/healthz
# Expected: {"status": "healthy", ...}
```

### Performance

- Gunicorn Access-Logs: stdout
- Error-Logs: stderr
- Optional: Sentry-Integration (siehe base.py SENTRY_DSN)

---

## Backup & Restore

### Database Backup

```bash
docker compose exec db pg_dump -U landlord landlord > backup_$(date +%Y%m%d).sql
```

### Database Restore

```bash
cat backup_20251017.sql | docker compose exec -T db psql -U landlord landlord
```

### Media Backup (wenn S3)

```bash
# Via MinIO Client (mc)
mc mirror minio/uvm-uploads ./backups/media/
```

---

## Reverse Proxy (nginx Example)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        # WhiteNoise serves static files, but you can also serve directly via nginx
        proxy_pass http://localhost:8000;
    }

    location /media/ {
        # If using local media (not S3)
        alias /var/www/uvm/media/;
    }
}
```

---

## Troubleshooting

### Static Files 404

```bash
# Check if collectstatic ran
docker compose exec web ls -la /app/staticfiles/

# Manual run
docker compose exec web python manage.py collectstatic --noinput
```

### CSRF Errors

```bash
# Check CSRF_TRUSTED_ORIGINS
docker compose exec web python manage.py shell -c "from django.conf import settings; print(settings.CSRF_TRUSTED_ORIGINS)"

# Must include https:// prefix!
```

### S3 Connection Errors

```bash
# Test MinIO connection
docker compose exec web python manage.py shell
>>> from django.core.files.storage import default_storage
>>> default_storage.bucket_name
'uvm-uploads'
>>> default_storage.connection  # Should connect
```

---

## Upgrade Guide

```bash
# 1. Pull latest code
git pull

# 2. Rebuild
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 3. Stop & Start (migrations run automatically via entrypoint)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Check logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
```

---

## Status: ✅ P0 Complete

- [x] Gunicorn + Uvicorn Workers
- [x] WhiteNoise für Static Files
- [x] collectstatic im Entrypoint
- [x] Security Headers (nosniff, DENY, referrer-policy)
- [x] S3/MinIO Support (opt-in via USE_S3)
- [x] ENV-basierte Konfiguration
- [x] Production docker-compose.prod.yml
- [x] Deployment-Dokumentation

**Next: M8 (Mieter-Portal mit Magic-Link)**
