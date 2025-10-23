# Environment Variables Security Policy

**Security Fix (2025-10-23 P2-2): Guidelines for safe secret handling**

---

## Overview

UVM uses environment variables for configuration, including sensitive secrets (SECRET_KEY, database passwords, API keys). This document outlines best practices to prevent accidental exposure.

---

## Critical Secrets

### Must NEVER appear in:
- ✅ Git commits (.gitignore protects `.env`)
- ✅ Error messages (DEBUG=False hides details)
- ✅ Logs (Sentry PII scrubbing enabled)
- ✅ Environment dumps in error pages
- ✅ Docker build output (use BuildKit secrets)

### Secrets List:

| Variable | Risk Level | Description |
|----------|-----------|-------------|
| `SECRET_KEY` | 🔴 Critical | Django cryptographic key - rotate if exposed |
| `DATABASE_URL` | 🔴 Critical | Contains DB password |
| `SENTRY_DSN` | 🟡 High | Contains project ID (not private key, but sensitive) |
| `EMAIL_HOST_PASSWORD` | 🔴 Critical | SMTP credentials |
| `AWS_SECRET_ACCESS_KEY` | 🔴 Critical | S3 credentials (if using S3) |

---

## Development Environment

### `.env` File Protection

```bash
# ✅ CORRECT: .env is gitignored
.env
.env.*
!.env.example  # Template only (no real values)

# Verify:
git check-ignore .env
# Should output: .env
```

### Environment Dump Safety

```python
# ❌ DANGEROUS: Prints all env vars including secrets
import os
print(dict(os.environ))

# ✅ SAFE: Use allowlist
SAFE_VARS = ['DEBUG', 'DJANGO_SETTINGS_MODULE', 'ALLOWED_HOSTS']
safe_env = {k: v for k, v in os.environ.items() if k in SAFE_VARS}
print(safe_env)
```

---

## Production Environment

### Docker Secrets (Recommended)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    environment:
      - SECRET_KEY_FILE=/run/secrets/secret_key
    secrets:
      - secret_key

secrets:
  secret_key:
    file: ./secrets/secret_key.txt  # NOT in git!
```

### Environment Variable Injection

```bash
# ✅ GOOD: Load from external source
export SECRET_KEY=$(vault kv get -field=value secret/uvm/secret_key)
docker compose up -d

# ❌ BAD: Hardcoded in docker-compose.yml
environment:
  - SECRET_KEY=hardcoded_value_here  # Will be in git!
```

---

## Sentry DSN Security

### Risk Assessment

**Sentry DSN Format:**
```
https://PUBLIC_KEY@o4510239025594368.ingest.de.sentry.io/PROJECT_ID
```

- **PUBLIC_KEY:** Not a secret (sent to browser in client-side JS)
- **PROJECT_ID:** Not sensitive
- **Risk:** If leaked, attacker can send fake errors to your Sentry project

### Mitigation

1. **Rate Limiting:** Sentry has built-in rate limits
2. **IP Allowlist:** Configure in Sentry project settings
3. **Separate Projects:** dev vs prod DSNs
4. **Rotation:** Regenerate DSN if abused

**Verdict:** 🟡 Medium risk - not critical but avoid public exposure

---

## CI/CD Pipeline

### GitHub Actions / GitLab CI

```yaml
# ✅ CORRECT: Use encrypted secrets
env:
  SECRET_KEY: ${{ secrets.DJANGO_SECRET_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}

# ❌ WRONG: Environment variable in workflow file
env:
  SECRET_KEY: "django-insecure-hardcoded..."  # Visible in repo!
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Check for common secret patterns
if git diff --cached | grep -E "(SECRET_KEY|PASSWORD|API_KEY)\s*=\s*['\"]"; then
    echo "❌ ERROR: Possible secret in staged files!"
    echo "Please use environment variables instead."
    exit 1
fi
```

---

## Incident Response

### If SECRET_KEY is Leaked:

1. **Rotate immediately:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **Update production:**
   ```bash
   # Update .env or secrets manager
   export SECRET_KEY="new-value-here"
   docker compose restart web
   ```

3. **Force logout all users:**
   ```python
   from django.contrib.sessions.models import Session
   Session.objects.all().delete()
   ```

4. **Audit:**
   - Check audit logs for suspicious activity
   - Review Sentry for anomalies
   - Rotate related secrets (DB password if using same generator)

---

## Checklist

### Development
- [ ] `.env` in `.gitignore`
- [ ] `.env.example` has placeholder values only
- [ ] No secrets in `docker-compose.yml`
- [ ] `DEBUG=True` only in local development

### Production
- [ ] `DEBUG=False` enforced
- [ ] Secrets in environment or secrets manager
- [ ] Sentry DSN in env, not hardcoded
- [ ] Database passwords rotated regularly
- [ ] Error pages don't show environment vars

### CI/CD
- [ ] Encrypted secrets in GitHub Actions
- [ ] No secrets in workflow files
- [ ] Pre-commit hook installed (optional)

---

## Tools

### Check for Leaked Secrets

```bash
# TruffleHog (scans git history)
docker run --rm -v $(pwd):/proj trufflesecurity/trufflehog:latest filesystem /proj

# git-secrets (prevents commits with secrets)
git secrets --install
git secrets --register-aws
```

### Verify .gitignore

```bash
# List all files git will track
git ls-files

# Should NOT include .env
# Should include .env.example
```

---

## References

- [OWASP Secret Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/)
- [12 Factor App - Config](https://12factor.net/config)

---

**Last Updated:** 2025-10-23  
**Status:** Production Security Policy ✅
