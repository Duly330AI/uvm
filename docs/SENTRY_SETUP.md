# Sentry.io Error Tracking & Performance Monitoring

**Phase 4.1 - Ready-to-Activate Integration (2025-10-23)**

## Overview

UVM includes production-ready Sentry.io integration for:

- **Error Tracking:** Automatic exception capture with full context
- **Performance Monitoring (APM):** Transaction tracking for slow endpoints
- **Release Tracking:** Git commit-based release tagging
- **User Context:** PII included for better debugging (user IDs, emails)

## Activation

### 1. Sign Up & Create Project

1. Go to [sentry.io](https://sentry.io) and create account
2. **Create TWO projects:**
   - **"UVM-Production"** for live errors
   - **"UVM-Development"** for local testing (already done ✅)
3. Copy the DSN (Data Source Name) from each project settings

**Why separate projects?**

- Development errors don't pollute production dashboard
- Different alert rules (dev = silent, prod = notify team)
- Clear separation of environments

### Security Note: DSN Exposure

**Sentry DSN Format:**

```
https://PUBLIC_KEY@o4510239025594368.ingest.de.sentry.io/PROJECT_ID
```

**What's in a DSN:**

- **Public Key:** Not a secret (used in client-side JavaScript)
- **Project ID:** Not sensitive
- **No authentication secret** (Sentry uses rate limiting instead)

**Risk if leaked:** Attacker can send fake errors to your Sentry project

**Mitigation:**

1. ✅ **Rate Limiting:** Sentry has built-in abuse protection (10k events/month free tier)
2. ✅ **IP Allowlist:** Configure in Sentry project settings (Enterprise plan)
3. ✅ **Separate DSNs:** dev vs prod (recommended above)
4. ✅ **Regenerate DSN:** If abused, create new DSN in Sentry settings

**Verdict:** 🟡 Medium risk - avoid public Git commits but not critical

**See Also:** `docs/SECURITY_ENV_VARS.md` for complete secret handling policy

---

### 2. Configure Environment Variables

Add to your `.env` file or environment:

```bash
# Required
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# Optional (with defaults)
SENTRY_ENVIRONMENT=production          # Default: "production"
SENTRY_TRACES_SAMPLE_RATE=0.1         # Default: 0.1 (10% of transactions)
SENTRY_RELEASE=uvm@1.0.0              # Default: "uvm@dev"
```

### 3. Install Sentry SDK (if not already installed)

```bash
pip install sentry-sdk
```

### 4. Restart Application

```bash
docker compose restart web worker beat
```

## Configuration Details

### Sample Rate

`SENTRY_TRACES_SAMPLE_RATE` controls how many transactions are sent to Sentry for performance monitoring:

- `0.0` = No performance monitoring (only errors)
- `0.1` = 10% of transactions (recommended for production)
- `1.0` = 100% of transactions (useful for staging/development, expensive in production)

**Example Performance Insights:**

Sentry will show you:

```
Slow Transactions (>2s):
1. POST /api/payments/csv/upload/  - 8.5s  (2x per day)
   └─ Cause: Synchronous file processing
   └─ Fix: Move to async Celery task ✅ (Already done in Phase 2.3!)

2. GET /portal/payments/  - 3.2s  (10x per day)
   └─ Cause: Loading all payments without pagination
   └─ Fix: Add pagination ✅ (Already done in Phase 2.2!)

3. GET /portal/issues/  - 1.8s  (50x per day)
   └─ Cause: N+1 query (loading attachments)
   └─ Fix: Use select_related() / prefetch_related()
```

This helps you identify bottlenecks **before users complain**!

### Environment Tags

`SENTRY_ENVIRONMENT` helps separate errors by deployment:

- `production` - Live production errors
- `staging` - Pre-production testing
- `development` - Local development (not recommended to enable)

### Release Tracking

`SENTRY_RELEASE` tags errors with a specific version:

```bash
# In CI/CD, use git commit hash
export SENTRY_RELEASE=uvm@$(git rev-parse --short HEAD)
```

## Integrations Included

- **Django:** Automatic request/response tracking
- **Celery:** Background task error tracking
- **Redis:** Cache operation monitoring

## What You See in Production

### Real-World Example

When a user encounters an error, Sentry captures:

**Error Details:**

- Exception type: `ValueError`, `DoesNotExist`, `IntegrityError`
- Stack trace with exact line numbers
- Request URL and method (GET/POST)
- SQL queries that were executed

**User Context:**

- User ID and email (if authenticated)
- IP address
- Browser and OS
- Session data

**Environment:**

- Release version (git commit hash)
- Server hostname
- Django version
- Database backend

**Timeline:**

- When the error occurred
- How many times it happened
- First seen vs last seen
- Affected users count

### Example Error in Sentry Dashboard

```
DoesNotExist: Property matching query does not exist.

File: landlord/views_portal.py, line 142
  property = Property.objects.get(id=property_id)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

User: admin@example.com (ID: 1)
URL: /portal/properties/999/
Request: GET
Time: 2025-10-23 16:00:00 UTC
Environment: production
Release: uvm@a1b2c3d
```

This tells you:

- ✅ What broke (Property DoesNotExist)
- ✅ Where (views_portal.py line 142)
- ✅ Who was affected (admin@example.com)
- ✅ How to reproduce (GET /portal/properties/999/)

**Action:** Add `.get_object_or_404()` or proper error handling

## Security Notes

### PII Handling

By default, Sentry captures:

- User IDs
- User emails
- Request data (headers, body)
- Session data

To scrub sensitive data, customize the `before_send` hook in `config/settings/base.py`:

```python
def before_send(event, hint):
    # Remove sensitive fields
    if 'request' in event:
        event['request'].pop('cookies', None)
        event['request'].pop('headers', None)  # Remove all headers
    return event

sentry_sdk.init(
    # ...
    before_send=before_send,
)
```

### Data Retention

Sentry retains data for 90 days by default. Adjust in project settings if needed for GDPR compliance.

## Monitoring Checklist

After activation, verify:

- [ ] Test error appears in Sentry dashboard
- [ ] Performance transactions visible in "Performance" tab
- [ ] User context includes email/ID
- [ ] Releases are tagged correctly
- [ ] No sensitive data (passwords, tokens) in error logs
- [ ] Alert rules configured for critical errors
- [ ] Team notifications set up (Slack, email)

## Cost Estimation

Sentry pricing based on:

- **Events:** Errors + Transactions
- **Data Retention:** 90 days standard

**Free tier:** 5,000 errors/month + 10,000 transactions/month

**Recommended for UVM:**

- Production: Team plan (~$26/month)
- Staging: Free tier
- Development: Disabled (local logs sufficient)

## Troubleshooting

### Sentry not initializing

Check logs for:

```
WARNING: SENTRY_DSN is set but sentry-sdk is not installed.
```

Solution: `pip install sentry-sdk` and rebuild Docker image.

### No errors appearing

1. Verify DSN is correct
2. Check `SENTRY_ENVIRONMENT` matches your expectations
3. Trigger test error (see Testing section)
4. Check network connectivity to sentry.io

### Too many events

Reduce sample rate:

```bash
SENTRY_TRACES_SAMPLE_RATE=0.01  # 1% instead of 10%
```

## Further Reading

- [Sentry Django Docs](https://docs.sentry.io/platforms/python/guides/django/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Release Tracking](https://docs.sentry.io/product/releases/)
