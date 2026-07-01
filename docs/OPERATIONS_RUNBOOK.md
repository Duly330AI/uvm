# UVM - Operations Runbook

**Phase 4.4 - Production Operations & Incident Response (2025-10-23)**

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Daily Operations](#daily-operations)
3. [Monitoring](#monitoring)
4. [Incident Response](#incident-response)
5. [Common Runbooks](#common-runbooks)
6. [Performance Tuning](#performance-tuning)
7. [Security Operations](#security-operations)
8. [Disaster Recovery](#disaster-recovery)

---

## System Architecture

### Service Overview

```
┌─────────────────────────────────────────────────────────┐
│                     NGINX (Reverse Proxy)                │
│                    Port 80/443 (HTTPS)                   │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐
    │  Web    │ │  Web   │ │  Web   │  Gunicorn Workers
    │Worker 1 │ │Worker 2│ │Worker 3│  (4x by default)
    └────┬────┘ └───┬────┘ └───┬────┘
         │          │          │
         └──────────┼──────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    ┌────▼─────┐ ┌──▼───┐ ┌───▼────┐
    │PostgreSQL│ │Redis │ │ Celery │
    │   DB     │ │Cache │ │Workers │
    └──────────┘ └──────┘ └───┬────┘
                                │
                           ┌────▼────┐
                           │  Celery │
                           │  Beat   │
                           └─────────┘
```

### Key Components

| Service         | Port    | Purpose                        | Resource Limits      |
| --------------- | ------- | ------------------------------ | -------------------- |
| Nginx           | 80, 443 | Reverse proxy, SSL termination | 512MB RAM            |
| Web (Gunicorn)  | 8000    | Django application             | 1GB RAM per worker   |
| Worker (Celery) | -       | Background tasks               | 512MB RAM per worker |
| Beat (Celery)   | -       | Task scheduler                 | 256MB RAM            |
| PostgreSQL      | 5432    | Primary database               | 2GB RAM              |
| Redis           | 6379    | Cache & message broker         | 256MB RAM            |

### Service Dependencies

- **Web** depends on: PostgreSQL, Redis
- **Worker** depends on: PostgreSQL, Redis
- **Beat** depends on: PostgreSQL, Redis
- **Nginx** depends on: Web

---

## Daily Operations

### Morning Checklist (09:00)

```bash
#!/bin/bash
# daily_check.sh - Run every morning

echo "=== UVM Daily Operations Check ==="
echo "Date: $(date)"

# 1. Check all services are running
echo "\n1. Service Status:"
docker compose ps

# 2. Check disk space
echo "\n2. Disk Space:"
df -h | grep -E "/$|/var"

# 3. Check database size
echo "\n3. Database Size:"
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT pg_size_pretty(pg_database_size('uvm_prod'));"

# 4. Check Redis memory
echo "\n4. Redis Memory:"
docker compose exec redis redis-cli info memory | grep used_memory_human

# 5. Check recent errors (last 24h)
echo "\n5. Recent Errors:"
docker compose logs --since 24h web worker beat 2>&1 | grep -i error | wc -l

# 6. Check Celery queue length
echo "\n6. Celery Queue:"
docker compose exec worker celery -A config inspect active_queues

# 7. Verify backups
echo "\n7. Last Backup:"
ls -lh /backups/*.sql.gz | tail -1

echo "\n=== Check Complete ==="
```

Save as `/opt/uvm/daily_check.sh` and schedule:

```cron
0 9 * * * /opt/uvm/daily_check.sh | mail -s "UVM Daily Check" ops@yourdomain.com
```

### Evening Checklist (18:00)

```bash
#!/bin/bash
# evening_check.sh

echo "=== UVM Evening Operations Check ==="

# 1. Today's error count
echo "Errors today:"
docker compose logs --since "00:00" 2>&1 | grep -i error | wc -l

# 2. Today's user activity
echo "\nUser activity:"
docker compose exec web python manage.py shell << EOF
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
User = get_user_model()
today = timezone.now().date()
active_users = User.objects.filter(last_login__date=today).count()
print(f"Active users today: {active_users}")
EOF

# 3. Today's issues created
echo "\nIssues created:"
docker compose exec web python manage.py shell << EOF
from landlord.models import Issue
from django.utils import timezone
today = timezone.now().date()
issues_today = Issue.objects.filter(created_at__date=today).count()
print(f"Issues created today: {issues_today}")
EOF

echo "\n=== Evening Check Complete ==="
```

---

## Monitoring

### Key Metrics to Monitor

#### Application Metrics

```bash
# Request rate (via Nginx logs)
tail -f /var/log/nginx/access.log | pv -l -i 10 > /dev/null

# Response times (Sentry Performance tab)
# Check: https://sentry.io/performance/

# Error rate (Sentry Issues tab)
# Check: https://sentry.io/issues/
```

#### System Metrics

```bash
# CPU usage
docker stats --no-stream

# Memory usage
free -h

# Disk I/O
iostat -x 1 5

# Network traffic
iftop -i eth0
```

#### Database Metrics

```bash
# Active connections
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Slow queries (>1s)
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT query, state, query_start FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '1 second';"

# Table sizes
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"

# Index usage
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT schemaname, tablename, indexname, idx_scan FROM pg_stat_user_indexes ORDER BY idx_scan ASC LIMIT 10;"
```

#### Celery Metrics

```bash
# Worker status
docker compose exec worker celery -A config inspect stats

# Active tasks
docker compose exec worker celery -A config inspect active

# Scheduled tasks
docker compose exec worker celery -A config inspect scheduled

# Queue lengths
docker compose exec redis redis-cli llen celery
```

### Alerting Thresholds

| Metric         | Warning | Critical | Action                      |
| -------------- | ------- | -------- | --------------------------- |
| CPU Usage      | >70%    | >90%     | Scale horizontally          |
| Memory Usage   | >75%    | >90%     | Restart services / Scale    |
| Disk Usage     | >75%    | >90%     | Clean logs / Expand storage |
| DB Connections | >50     | >80      | Check connection leaks      |
| Error Rate     | >10/min | >50/min  | Check logs immediately      |
| Response Time  | >2s     | >5s      | Check slow queries          |
| Queue Length   | >100    | >500     | Add workers                 |

---

## Incident Response

### Incident Severity Levels

| Level         | Description             | Response Time | Example             |
| ------------- | ----------------------- | ------------- | ------------------- |
| P0 (Critical) | Service down, data loss | Immediate     | Database corruption |
| P1 (High)     | Major feature broken    | <15 min       | Login not working   |
| P2 (Medium)   | Feature degraded        | <1 hour       | Slow page loads     |
| P3 (Low)      | Minor issue             | <24 hours     | UI glitch           |

### P0 - Critical Incident Response

```bash
#!/bin/bash
# critical_response.sh - Run immediately for P0 incidents

echo "=== P0 INCIDENT RESPONSE ==="
echo "Time: $(date)"
echo "Responder: $USER"

# 1. Check all services
echo "\n1. SERVICE STATUS:"
docker compose ps

# 2. Check recent logs (last 100 lines)
echo "\n2. RECENT LOGS:"
docker compose logs --tail=100 web worker beat

# 3. Check system resources
echo "\n3. SYSTEM RESOURCES:"
free -h
df -h

# 4. Check database connectivity
echo "\n4. DATABASE:"
docker compose exec db pg_isready

# 5. Check Redis
echo "\n5. REDIS:"
docker compose exec redis redis-cli ping

# 6. Take snapshot of current state
mkdir -p /tmp/incident_$(date +%Y%m%d_%H%M%S)
docker compose ps > /tmp/incident_$(date +%Y%m%d_%H%M%S)/ps.txt
docker compose logs --tail=1000 > /tmp/incident_$(date +%Y%m%d_%H%M%S)/logs.txt
docker stats --no-stream > /tmp/incident_$(date +%Y%m%d_%H%M%S)/stats.txt

echo "\n=== Snapshot saved to /tmp/incident_* ==="
echo "Next steps: Analyze logs and determine root cause"
```

### Communication Template

```markdown
**Incident Report: [P0/P1/P2/P3] - [Brief Description]**

**Time Detected:** YYYY-MM-DD HH:MM UTC
**Detected By:** [Name]
**Severity:** [P0/P1/P2/P3]

**Impact:**

- Users affected: [Estimate]
- Features impacted: [List]
- Data integrity: [OK/At Risk]

**Status:** [Investigating/Identified/Monitoring/Resolved]

**Timeline:**

- HH:MM - Incident detected
- HH:MM - Team notified
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

**Root Cause:**
[Brief explanation]

**Resolution:**
[Steps taken]

**Action Items:**

- [ ] Post-mortem scheduled
- [ ] Monitoring alerts updated
- [ ] Documentation updated
```

---

## Common Runbooks

### Runbook 1: High CPU Usage

```bash
# Identify culprit
docker stats --no-stream

# If web container:
# 1. Check for slow requests
docker compose exec web tail -100 /app/logs/gunicorn-access.log | awk '{print $NF}' | sort -n | tail -10

# 2. Check for slow database queries
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 5;"

# 3. If needed, restart with more workers
# Edit .env.production: GUNICORN_WORKERS=8
docker compose restart web

# 4. Scale horizontally (if load balancer available)
docker compose up -d --scale web=3
```

### Runbook 2: Database Connection Errors

```bash
# 1. Check active connections
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Check max connections
docker compose exec db psql -U uvm_user -d uvm_prod -c "SHOW max_connections;"

# 3. Terminate idle connections (>5 minutes)
docker compose exec db psql -U uvm_user -d uvm_prod -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND now() - state_change > interval '5 minutes';"

# 4. Restart application to reset connection pool
docker compose restart web worker

# 5. If persistent, increase max_connections
# Edit postgresql.conf: max_connections = 200
docker compose restart db
```

### Runbook 3: Celery Tasks Stuck

```bash
# 1. Check worker status
docker compose exec worker celery -A config inspect ping

# 2. Check active tasks
docker compose exec worker celery -A config inspect active

# 3. Purge queue (CAUTION: Data loss!)
docker compose exec worker celery -A config purge

# 4. Restart workers
docker compose restart worker beat

# 5. Verify recovery
docker compose logs worker -f
```

### Runbook 4: Disk Space Full

```bash
# 1. Identify large files
du -sh /var/lib/docker/volumes/* | sort -h | tail -10

# 2. Clean Docker
docker system prune -a --volumes

# 3. Rotate logs
docker compose logs --since 1h > /backups/logs_$(date +%Y%m%d).txt
truncate -s 0 /var/log/nginx/*.log
docker compose restart nginx

# 4. Clean old backups
find /backups -name "*.sql.gz" -mtime +30 -delete

# 5. Check space
df -h
```

### Runbook 5: SSL Certificate Renewal

```bash
# 1. Check certificate expiry
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates

# 2. Renew certificate
sudo certbot renew

# 3. Copy new certificates to nginx volume
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/

# 4. Reload nginx
docker compose exec nginx nginx -s reload

# 5. Verify
curl -I https://yourdomain.com
```

---

## Performance Tuning

### Database Optimization

```sql
-- Analyze table statistics
ANALYZE;

-- Vacuum to reclaim space
VACUUM ANALYZE;

-- Reindex if needed
REINDEX DATABASE uvm_prod;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct < 0
ORDER BY abs(n_distinct) DESC
LIMIT 20;
```

### Gunicorn Tuning

```bash
# Optimal workers: (2 x CPU cores) + 1
# Example: 4 cores → 9 workers

# Update .env.production
GUNICORN_WORKERS=9
GUNICORN_THREADS=2
GUNICORN_WORKER_CLASS=sync
GUNICORN_WORKER_CONNECTIONS=1000

# Restart
docker compose restart web
```

### Redis Optimization

```bash
# Check memory usage
docker compose exec redis redis-cli info memory

# Set eviction policy (if cache-only)
docker compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Persist to disk
docker compose exec redis redis-cli BGSAVE
```

---

## Security Operations

### Security Audit Checklist

```bash
# 1. Check for CVEs in dependencies
docker compose exec web pip list --outdated

# 2. Django security check
docker compose exec web python manage.py check --deploy

# 3. Check firewall rules
sudo ufw status

# 4. Review access logs for suspicious activity
tail -1000 /var/log/nginx/access.log | grep -E "404|401|403" | awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# 5. Check failed login attempts
docker compose exec web python manage.py shell << EOF
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone

# Failed logins (no direct tracking, but check audit logs)
from landlord.models_audit import AuditLog
recent_failures = AuditLog.objects.filter(
    action='permission_change',
    timestamp__gte=timezone.now() - timedelta(hours=24)
).count()
print(f"Recent permission changes: {recent_failures}")
EOF
```

### Incident Security Response

```bash
# 1. Rotate SECRET_KEY immediately
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Force logout all users
docker compose exec web python manage.py shell << EOF
from django.contrib.sessions.models import Session
Session.objects.all().delete()
print("All sessions cleared")
EOF

# 3. Review and revoke API tokens (if applicable)
# Check Sentry logs for unauthorized access

# 4. Update .env.production with new SECRET_KEY
# Restart all services
docker compose restart
```

---

## Disaster Recovery

### Backup Verification

```bash
#!/bin/bash
# verify_backup.sh - Test backup restoration

BACKUP_FILE="/backups/uvm_$(date +%Y%m%d).sql.gz"

echo "=== Testing Backup Restoration ==="

# 1. Create test database
docker compose exec db psql -U uvm_user -c "CREATE DATABASE uvm_test;"

# 2. Restore backup
gunzip -c $BACKUP_FILE | docker compose exec -T db psql -U uvm_user -d uvm_test

# 3. Verify tables
docker compose exec db psql -U uvm_user -d uvm_test -c "\dt"

# 4. Check record counts
docker compose exec db psql -U uvm_user -d uvm_test -c "SELECT 'properties', count(*) FROM landlord_property UNION SELECT 'units', count(*) FROM landlord_unit UNION SELECT 'issues', count(*) FROM landlord_issue;"

# 5. Clean up
docker compose exec db psql -U uvm_user -c "DROP DATABASE uvm_test;"

echo "=== Backup Verification Complete ==="
```

### Full System Recovery

```bash
#!/bin/bash
# disaster_recovery.sh - Complete system restoration

echo "=== DISASTER RECOVERY PROCEDURE ==="
echo "WARNING: This will overwrite current data!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# 1. Stop all services
docker compose down

# 2. Restore database
LATEST_BACKUP=$(ls -t /backups/uvm_*.sql.gz | head -1)
echo "Restoring from: $LATEST_BACKUP"
docker compose up -d db
sleep 10
gunzip -c $LATEST_BACKUP | docker compose exec -T db psql -U uvm_user -d uvm_prod

# 3. Restore media files
LATEST_MEDIA=$(ls -t /backups/media_*.tar.gz | head -1)
echo "Restoring media from: $LATEST_MEDIA"
tar -xzf $LATEST_MEDIA -C /var/lib/docker/volumes

# 4. Start all services
docker compose up -d

# 5. Verify
sleep 30
docker compose ps
curl -f https://yourdomain.com/healthz

echo "=== Recovery Complete ==="
echo "Verify application functionality manually."
```

---

## Contact Information

| Role             | Name | Contact                 | Availability   |
| ---------------- | ---- | ----------------------- | -------------- |
| On-Call Engineer | TBD  | +49-XXX                 | 24/7           |
| Database Admin   | TBD  | dba@yourdomain.com      | Business hours |
| Security Team    | TBD  | security@yourdomain.com | 24/7           |
| Management       | TBD  | ops@yourdomain.com      | Business hours |

---

## Revision History

| Date       | Version | Changes         | Author   |
| ---------- | ------- | --------------- | -------- |
| 2025-10-23 | 1.0.0   | Initial runbook | UVM Team |

---

**Last Updated:** 2025-10-23
**Status:** Prototype operations notes; requires manual review before production use
