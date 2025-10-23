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
2. Create new project (select "Django" as platform)
3. Copy the DSN (Data Source Name) from project settings

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
- `1.0` = 100% of transactions (useful for staging, expensive in production)

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

## Testing

### Trigger Test Error

Add a test view to trigger an error:

```python
# Add to config/urls.py for testing
def sentry_test(request):
    division_by_zero = 1 / 0

urlpatterns = [
    # ...
    path('sentry-test/', sentry_test),  # Remove after testing!
]
```

Visit `/sentry-test/` - error should appear in Sentry dashboard within seconds.

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
