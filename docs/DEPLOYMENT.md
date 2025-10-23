# UVM - Production Deployment Guide# Production Deployment Guide



**Phase 4.3 - Complete Production Deployment Checklist (2025-10-23)**## P0 Produktions-Härtung ✅



---Dieses Setup verwendet Gunicorn + Uvicorn Workers, WhiteNoise für Static Files, optionales S3/MinIO für Media und Security-Hardening.



## Table of Contents---



1. [Prerequisites](#prerequisites)## Voraussetzungen

2. [Pre-Deployment Checklist](#pre-deployment-checklist)

3. [Environment Configuration](#environment-configuration)- Docker & Docker Compose

4. [Database Setup](#database-setup)- Domain mit SSL-Zertifikat (z.B. via Let's Encrypt/Certbot)

5. [Docker Production Deployment](#docker-production-deployment)- SMTP-Server für E-Mail-Versand

6. [SSL/TLS Configuration](#ssltls-configuration)- Optional: S3-kompatibler Storage (MinIO, AWS S3, etc.)

7. [Static Files & Media](#static-files--media)

8. [Background Workers](#background-workers)---

9. [Monitoring & Logging](#monitoring--logging)

10. [Post-Deployment Verification](#post-deployment-verification)## Schnellstart (Lokal-Prod-Test)

11. [Rollback Procedure](#rollback-procedure)

12. [Troubleshooting](#troubleshooting)### 1. Secret Key generieren



---```bash

python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

## Prerequisites```



### System Requirements### 2. `.env` Datei erstellen



- **OS:** Linux (Ubuntu 22.04 LTS recommended)```bash

- **RAM:** Minimum 4GB, Recommended 8GB+cp .env.prod.example .env

- **Storage:** Minimum 20GB SSD# Bearbeite .env mit deinen Werten (siehe unten)

- **CPU:** 2+ cores recommended```

- **Docker:** 24.0+

- **Docker Compose:** 2.20+### 3. Build & Start



### Required Accounts```bash

# Build images

- [ ] Domain name registereddocker compose -f docker-compose.yml -f docker-compose.prod.yml build

- [ ] SSL certificate (Let's Encrypt or purchased)

- [ ] SMTP service (SendGrid, Mailgun, or Gmail)# Start services

- [ ] Sentry.io account (optional but recommended)docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

- [ ] Backup storage (S3 or compatible)

# Check logs

---docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

```

## Pre-Deployment Checklist

### 4. Superuser anlegen

### Code Quality

```bash

```bashdocker compose exec web python manage.py createsuperuser

# 1. Run all tests```

docker compose exec web pytest

# Expected: 334+ tests passing### 5. Testen



# 2. Check for security issues```bash

docker compose exec web python manage.py check --deploy# Health Check

# Expected: 0 critical issuescurl http://localhost:8000/healthz



# 3. Verify migrations# Admin (Static Files via WhiteNoise)

docker compose exec web python manage.py showmigrationsopen http://localhost:8000/admin/

# Expected: All migrations applied

# Portal

# 4. Check static filesopen http://localhost:8000/portal/

docker compose exec web python manage.py collectstatic --dry-run --noinput```

# Expected: No errors

```---



### Security Hardening## Umgebungsvariablen (.env)



- [ ] Generate new `SECRET_KEY` (never reuse dev keys!)### Pflicht

- [ ] Review `ALLOWED_HOSTS` configuration

- [ ] Enable SSL/TLS (HTTPS only)```env

- [ ] Configure secure cookiesSECRET_KEY=<dein-generierter-key>

- [ ] Set up firewall (UFW or similar)DJANGO_ALLOWED_HOSTS=yourdomain.com

- [ ] Disable DEBUG modeDJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com

- [ ] Remove default admin credentialsPOSTGRES_PASSWORD=<starkes-passwort>

```

### Database

### Email (SMTP)

- [ ] PostgreSQL 16+ installed and configured

- [ ] Database user created with limited permissions```env

- [ ] Automated backups configuredEMAIL_HOST=smtp.gmail.com

- [ ] Connection pooling configured (pgbouncer)EMAIL_PORT=587

- [ ] Database performance tuning completedEMAIL_USE_TLS=1

EMAIL_HOST_USER=your-email@gmail.com

---EMAIL_HOST_PASSWORD=your-app-password

DEFAULT_FROM_EMAIL=noreply@yourdomain.com

## Environment Configuration```



### Create Production `.env` File### S3/MinIO (optional)



```bash```env

# Copy templateUSE_S3=true

cp .env.example .env.productionAWS_ACCESS_KEY_ID=<minio-access-key>

AWS_SECRET_ACCESS_KEY=<minio-secret>

# Edit with production valuesAWS_STORAGE_BUCKET_NAME=uvm-uploads

nano .env.productionAWS_S3_ENDPOINT_URL=http://minio:9000

``````



### Required Environment Variables---



```bash## Production Features

# ============================================================================

# CORE SETTINGS### ✅ Gunicorn + Uvicorn

# ============================================================================

- 2 Worker-Prozesse (anpassen via `--workers` in docker-compose.prod.yml)

# Django Secret Key (CRITICAL - Generate new for production!)- ASGI-Support für WebSocket (vorbereitet)

# Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

SECRET_KEY=your-secret-key-here-min-50-chars### ✅ WhiteNoise



# Environment (MUST be 'production')- Statische Dateien (CSS, JS, Admin-Assets) werden komprimiert und mit Hash ausgeliefert

DJANGO_SETTINGS_MODULE=config.settings.prod- `collectstatic` wird automatisch beim Start ausgeführt (via entrypoint.sh)



# Debug (MUST be False in production)### ✅ Security Headers

DEBUG=False

- `SECURE_SSL_REDIRECT=1` (nur hinter HTTPS-Proxy)

# Allowed Hosts (comma-separated, NO SPACES)- `X-Content-Type-Options: nosniff`

ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com- `X-Frame-Options: DENY`

- `Referrer-Policy: same-origin`

# ============================================================================- HSTS mit 1 Jahr (konfigurierbar)

# DATABASE

# ============================================================================### ✅ S3/MinIO für Media



DATABASE_URL=postgres://uvm_user:secure_password@db:5432/uvm_prod- Aktivierbar via `USE_S3=true`

- Cache-Control: 24h für Uploads

# ============================================================================- Private ACL (signed URLs)

# REDIS (Cache & Celery Broker)

# ============================================================================### ✅ Redis Cache



REDIS_URL=redis://redis:6379/0- Default-Cache nutzt Redis statt In-Memory

CELERY_BROKER_URL=redis://redis:6379/0- Session-Cache via Django-Redis

CELERY_RESULT_BACKEND=redis://redis:6379/1

---

# ============================================================================

# EMAIL (SMTP)## Deployment Checkliste

# ============================================================================

- [ ] `.env` erstellt mit allen Pflicht-Variablen

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend- [ ] Secret Key generiert und gesetzt

EMAIL_HOST=smtp.sendgrid.net- [ ] ALLOWED_HOSTS auf Domain(s) gesetzt

EMAIL_PORT=587- [ ] CSRF_TRUSTED_ORIGINS mit `https://` Prefix

EMAIL_USE_TLS=True- [ ] SMTP-Credentials konfiguriert

EMAIL_HOST_USER=apikey- [ ] SSL-Zertifikat via Reverse-Proxy (nginx/Caddy/Traefik)

EMAIL_HOST_PASSWORD=your-sendgrid-api-key- [ ] `docker compose build` erfolgreich

DEFAULT_FROM_EMAIL=noreply@yourdomain.com- [ ] Migrations gelaufen (`entrypoint.sh` macht das automatisch)

SERVER_EMAIL=admin@yourdomain.com- [ ] `collectstatic` erfolgreich (siehe Container-Logs)

- [ ] Superuser angelegt

# ============================================================================- [ ] `/healthz` gibt 200 zurück

# SECURITY- [ ] Admin-Login funktioniert

# ============================================================================- [ ] Static Files laden (keine 404 in Browser-Console)

- [ ] File-Upload & Download funktioniert (S3/MinIO)

# SSL/TLS (MUST be True in production)

SECURE_SSL_REDIRECT=True---

SECURE_HSTS_SECONDS=31536000

SECURE_HSTS_INCLUDE_SUBDOMAINS=True## Monitoring & Logs

SECURE_HSTS_PRELOAD=True

### Logs anzeigen

# ============================================================================

# FILE STORAGE (Optional - S3/MinIO)```bash

# ============================================================================docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f worker

USE_S3=false```

# If USE_S3=true, configure:

# AWS_ACCESS_KEY_ID=your-key### Health Check

# AWS_SECRET_ACCESS_KEY=your-secret

# AWS_STORAGE_BUCKET_NAME=uvm-media```bash

# AWS_S3_REGION_NAME=eu-central-1curl http://localhost:8000/healthz

# AWS_S3_CUSTOM_DOMAIN=cdn.yourdomain.com# Expected: {"status": "healthy", ...}

```

# ============================================================================

# MONITORING (Optional but Recommended)### Performance

# ============================================================================

- Gunicorn Access-Logs: stdout

# Sentry.io Error Tracking- Error-Logs: stderr

SENTRY_DSN=https://...@sentry.io/...- Optional: Sentry-Integration (siehe base.py SENTRY_DSN)

SENTRY_ENVIRONMENT=production

SENTRY_TRACES_SAMPLE_RATE=0.1---

SENTRY_RELEASE=uvm@1.0.0

## Backup & Restore

# ============================================================================

# GUNICORN (Production Web Server)### Database Backup

# ============================================================================

```bash

GUNICORN_WORKERS=4docker compose exec db pg_dump -U landlord landlord > backup_$(date +%Y%m%d).sql

GUNICORN_THREADS=2```

GUNICORN_TIMEOUT=120

GUNICORN_MAX_REQUESTS=1000### Database Restore

GUNICORN_MAX_REQUESTS_JITTER=50

``````bash

cat backup_20251017.sql | docker compose exec -T db psql -U landlord landlord

### Validate Configuration```



```bash### Media Backup (wenn S3)

# Check for missing required variables

docker compose --env-file .env.production config```bash

# Via MinIO Client (mc)

# Test database connectionmc mirror minio/uvm-uploads ./backups/media/

docker compose --env-file .env.production run --rm web python manage.py dbshell```

```

---

---

## Reverse Proxy (nginx Example)

## Database Setup

```nginx

### 1. Create Production Databaseserver {

    listen 443 ssl http2;

```bash    server_name yourdomain.com;

# On database server

sudo -u postgres psql    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

CREATE DATABASE uvm_prod;

CREATE USER uvm_user WITH PASSWORD 'secure_password_here';    client_max_body_size 50M;

GRANT ALL PRIVILEGES ON DATABASE uvm_prod TO uvm_user;

    location / {

# Grant schema permissions (PostgreSQL 15+)        proxy_pass http://localhost:8000;

\c uvm_prod        proxy_set_header Host $host;

GRANT ALL ON SCHEMA public TO uvm_user;        proxy_set_header X-Real-IP $remote_addr;

GRANT ALL ON ALL TABLES IN SCHEMA public TO uvm_user;        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO uvm_user;        proxy_set_header X-Forwarded-Proto $scheme;

    }

\q

```    location /static/ {

        # WhiteNoise serves static files, but you can also serve directly via nginx

### 2. Run Migrations        proxy_pass http://localhost:8000;

    }

```bash

# Apply all migrations    location /media/ {

docker compose --env-file .env.production run --rm web python manage.py migrate        # If using local media (not S3)

        alias /var/www/uvm/media/;

# Create superuser    }

docker compose --env-file .env.production run --rm web python manage.py createsuperuser}

``````



### 3. Load Initial Data (Optional)---



```bash## Troubleshooting

# If you have fixtures

docker compose --env-file .env.production run --rm web python manage.py loaddata initial_data.json### Static Files 404

```

```bash

---# Check if collectstatic ran

docker compose exec web ls -la /app/staticfiles/

## Docker Production Deployment

# Manual run

### Production `docker-compose.prod.yml`docker compose exec web python manage.py collectstatic --noinput

```

Create or verify `docker-compose.prod.yml`:

### CSRF Errors

```yaml

version: '3.8'```bash

# Check CSRF_TRUSTED_ORIGINS

services:docker compose exec web python manage.py shell -c "from django.conf import settings; print(settings.CSRF_TRUSTED_ORIGINS)"

  web:

    image: uvm:latest# Must include https:// prefix!

    build:```

      context: ./backend/app

      dockerfile: Dockerfile### S3 Connection Errors

    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests ${GUNICORN_MAX_REQUESTS:-1000} --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-50}

    env_file:```bash

      - .env.production# Test MinIO connection

    volumes:docker compose exec web python manage.py shell

      - static_volume:/app/staticfiles>>> from django.core.files.storage import default_storage

      - media_volume:/app/media>>> default_storage.bucket_name

    depends_on:'uvm-uploads'

      - db>>> default_storage.connection  # Should connect

      - redis```

    restart: unless-stopped

    healthcheck:---

      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]

      interval: 30s## Upgrade Guide

      timeout: 10s

      retries: 3```bash

      start_period: 40s# 1. Pull latest code

git pull

  worker:

    image: uvm:latest# 2. Rebuild

    command: celery -A config worker --loglevel=info --concurrency=2docker compose -f docker-compose.yml -f docker-compose.prod.yml build

    env_file:

      - .env.production# 3. Stop & Start (migrations run automatically via entrypoint)

    volumes:docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

      - media_volume:/app/media

    depends_on:# 4. Check logs

      - dbdocker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

      - redis```

    restart: unless-stopped

---

  beat:

    image: uvm:latest## Status: ✅ P0 Complete

    command: celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

    env_file:- [x] Gunicorn + Uvicorn Workers

      - .env.production- [x] WhiteNoise für Static Files

    depends_on:- [x] collectstatic im Entrypoint

      - db- [x] Security Headers (nosniff, DENY, referrer-policy)

      - redis- [x] S3/MinIO Support (opt-in via USE_S3)

    restart: unless-stopped- [x] ENV-basierte Konfiguration

- [x] Production docker-compose.prod.yml

  db:- [x] Deployment-Dokumentation

    image: postgres:16-alpine

    env_file:**Next: M8 (Mieter-Portal mit Magic-Link)**

      - .env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-uvm_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### Deploy to Production

```bash
# 1. Build production image
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. Collect static files
docker compose --env-file .env.production run --rm web python manage.py collectstatic --noinput

# 3. Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

# 4. Verify all services are running
docker compose ps
```

---

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate (HTTP-01 challenge)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (certbot installs cron automatically)
sudo certbot renew --dry-run
```

### Nginx SSL Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream django {
        server web:8000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security Headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Static Files
        location /static/ {
            alias /app/staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Media Files
        location /media/ {
            alias /app/media/;
            expires 7d;
        }

        # Django Application
        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health Check
        location /healthz {
            access_log off;
            proxy_pass http://django;
        }
    }
}
```

---

## Static Files & Media

### Collect Static Files

```bash
# Collect to volume
docker compose --env-file .env.production run --rm web python manage.py collectstatic --noinput

# Verify
docker compose --env-file .env.production run --rm web ls -la /app/staticfiles
```

### S3/CDN Setup (Optional)

For high-traffic deployments, serve static/media from CDN:

```bash
# Install django-storages
pip install django-storages boto3

# Configure in .env.production
USE_S3=true
AWS_STORAGE_BUCKET_NAME=uvm-static
AWS_S3_CUSTOM_DOMAIN=cdn.yourdomain.com
```

---

## Background Workers

### Celery Worker Configuration

```bash
# Check worker status
docker compose logs worker -f

# Monitor tasks
docker compose exec worker celery -A config inspect active

# Restart workers (zero-downtime)
docker compose exec worker celery -A config control shutdown
docker compose restart worker
```

### Celery Beat (Scheduler)

```bash
# Verify beat is running
docker compose logs beat -f

# Check scheduled tasks
docker compose exec web python manage.py shell
>>> from django_celery_beat.models import PeriodicTask
>>> PeriodicTask.objects.all()
```

---

## Monitoring & Logging

### Application Logs

```bash
# View all logs
docker compose logs -f

# Filter by service
docker compose logs web -f
docker compose logs worker -f
docker compose logs db -f

# Save logs to file
docker compose logs --since 24h > logs_$(date +%Y%m%d).txt
```

### Sentry Integration

Verify Sentry is capturing errors:

1. Visit Sentry dashboard
2. Check for test error (if triggered)
3. Configure alert rules
4. Set up team notifications

### Health Checks

```bash
# Application health
curl https://yourdomain.com/healthz

# Database health
docker compose exec db pg_isready

# Redis health
docker compose exec redis redis-cli ping
```

---

## Post-Deployment Verification

### Checklist

- [ ] Homepage loads over HTTPS
- [ ] Admin panel accessible (https://yourdomain.com/admin/)
- [ ] Login/logout works
- [ ] Password reset email sends
- [ ] File uploads work
- [ ] Background tasks execute (check Celery logs)
- [ ] Scheduled tasks run (check Beat logs)
- [ ] Error tracking active (trigger test error in Sentry)
- [ ] SSL certificate valid (check browser)
- [ ] Security headers present (check browser dev tools)

### Load Testing (Optional)

```bash
# Install locust
pip install locust

# Run basic load test
locust -f locustfile.py --host=https://yourdomain.com --users 10 --spawn-rate 2
```

---

## Rollback Procedure

### Quick Rollback

```bash
# 1. Stop current deployment
docker compose down

# 2. Restore previous image
docker compose pull uvm:previous

# 3. Restart with previous version
docker compose up -d

# 4. Verify rollback
curl https://yourdomain.com/healthz
```

### Database Rollback

```bash
# 1. Stop application
docker compose stop web worker beat

# 2. Restore database backup
docker compose exec db pg_restore -U uvm_user -d uvm_prod /backups/backup_YYYYMMDD.dump

# 3. Restart application
docker compose start web worker beat
```

---

## Troubleshooting

### Common Issues

#### 1. "Bad Gateway" (502 Error)

```bash
# Check if web container is running
docker compose ps web

# Check web logs
docker compose logs web --tail=100

# Verify Gunicorn is listening
docker compose exec web netstat -tulpn | grep 8000
```

**Solution:** Restart web service
```bash
docker compose restart web
```

#### 2. Database Connection Errors

```bash
# Test database connection
docker compose exec web python manage.py dbshell

# Check database logs
docker compose logs db --tail=100
```

**Solution:** Verify `DATABASE_URL` in `.env.production`

#### 3. Static Files Not Loading

```bash
# Re-collect static files
docker compose run --rm web python manage.py collectstatic --noinput --clear

# Verify nginx volume
docker compose exec nginx ls -la /app/staticfiles
```

**Solution:** Restart nginx
```bash
docker compose restart nginx
```

#### 4. Celery Tasks Not Running

```bash
# Check worker logs
docker compose logs worker --tail=100

# Check Redis connection
docker compose exec worker python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
```

**Solution:** Restart worker
```bash
docker compose restart worker beat
```

#### 5. SSL Certificate Issues

```bash
# Renew certificate
sudo certbot renew

# Check certificate expiry
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

**Solution:** Reload nginx after renewal
```bash
docker compose exec nginx nginx -s reload
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error logs
- Check Sentry for new issues
- Verify backup completion

**Weekly:**
- Review performance metrics
- Update dependencies (security patches)
- Test backup restoration

**Monthly:**
- Rotate log files
- Review and archive old data
- Security audit

### Backup Strategy

```bash
# Database backup (daily cron)
0 2 * * * docker compose exec -T db pg_dump -U uvm_user uvm_prod | gzip > /backups/uvm_$(date +\%Y\%m\%d).sql.gz

# Media files backup (daily)
0 3 * * * tar -czf /backups/media_$(date +\%Y\%m\%d).tar.gz -C /var/lib/docker/volumes media_volume

# Retention: Keep 30 days
0 4 * * * find /backups -name "*.gz" -mtime +30 -delete
```

---

## Support & Resources

- **Documentation:** See `/docs` folder
- **Sentry Setup:** `docs/SENTRY_SETUP.md`
- **Issue Tracker:** GitHub Issues
- **Django Deployment:** https://docs.djangoproject.com/en/5.1/howto/deployment/
- **Docker Best Practices:** https://docs.docker.com/develop/dev-best-practices/

---

**Last Updated:** 2025-10-23  
**Version:** 1.0.0  
**Status:** Production-Ready ✅
