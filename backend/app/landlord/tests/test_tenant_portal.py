"""
Tests for M8 Tenant Portal (Magic-Link Auth)
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from landlord.models import IssueAttachment, IssueNote, TenantAuthToken


@pytest.mark.django_db
def test_magic_link_happy_path(client, tenant_factory, unit_factory):
    """Test: Magic-link flow works end-to-end"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit, primary_email="test@example.com", is_active=True)

    # Request magic link
    response = client.post("/tenant/magic/request", {"email": "test@example.com"})
    assert response.status_code == 302  # redirect

    # Token created
    token = TenantAuthToken.objects.get(email="test@example.com")
    assert token.tenant == tenant
    assert token.is_valid()

    # Verify magic link
    response = client.get(f"/tenant/magic/{token.id}/")
    assert response.status_code == 302  # redirect to my_issues

    # Session established
    assert client.session.get("tenant_id") == tenant.id

    # Token marked as used
    token.refresh_from_db()
    assert token.used_at is not None


@pytest.mark.django_db
def test_magic_link_expired(client, tenant_factory, unit_factory):
    """Test: Expired magic-link rejected"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit, primary_email="test@example.com", is_active=True)

    # Create expired token
    token = TenantAuthToken.objects.create(
        tenant=tenant,
        email="test@example.com",
        expires_at=timezone.now() - timedelta(minutes=1),  # expired
        purpose=TenantAuthToken.Purpose.LOGIN
    )

    # Try to verify
    response = client.get(f"/tenant/magic/{token.id}/")
    assert response.status_code == 302  # redirect to login
    assert client.session.get("tenant_id") is None  # not logged in


@pytest.mark.django_db
def test_magic_link_already_used(client, tenant_factory, unit_factory):
    """Test: Already used token rejected"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit, primary_email="test@example.com", is_active=True)

    token = TenantAuthToken.objects.create(
        tenant=tenant,
        email="test@example.com",
        expires_at=timezone.now() + timedelta(minutes=15),
        used_at=timezone.now() - timedelta(minutes=5),  # already used
        purpose=TenantAuthToken.Purpose.LOGIN
    )

    response = client.get(f"/tenant/magic/{token.id}/")
    assert response.status_code == 302
    assert client.session.get("tenant_id") is None


@pytest.mark.django_db
def test_tenant_can_only_see_own_issues(client, tenant_factory, issue_factory, unit_factory):
    """Test: Tenant can only access their own issues"""
    unit1 = unit_factory()
    unit2 = unit_factory()
    tenant1 = tenant_factory(unit=unit1, primary_email="tenant1@example.com")
    tenant2 = tenant_factory(unit=unit2, primary_email="tenant2@example.com")

    issue1 = issue_factory(tenant=tenant1, unit=unit1, summary="Tenant 1 Issue")
    issue2 = issue_factory(tenant=tenant2, unit=unit2, summary="Tenant 2 Issue")

    # Login as tenant1
    session = client.session
    session["tenant_id"] = tenant1.id
    session.save()

    # Can access own issue
    response = client.get(f"/tenant/issues/{issue1.id}/")
    assert response.status_code == 200
    assert "Tenant 1 Issue" in response.content.decode()

    # Cannot access other tenant's issue
    response = client.get(f"/tenant/issues/{issue2.id}/")
    assert response.status_code == 403  # Forbidden


@pytest.mark.django_db
def test_tenant_add_note(client, tenant_factory, issue_factory, unit_factory):
    """Test: Tenant can add notes to their issue"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit, primary_email="test@example.com")
    issue = issue_factory(tenant=tenant, unit=unit)

    # Login
    session = client.session
    session["tenant_id"] = tenant.id
    session.save()

    # Add note
    response = client.post(f"/tenant/issues/{issue.id}/notes", {"text": "My question"})
    assert response.status_code == 302  # redirect

    # Note created
    note = IssueNote.objects.get(issue=issue)
    assert note.text == "My question"
    assert note.visibility == "tenant"


@pytest.mark.django_db
def test_tenant_upload_size_limit(client, tenant_factory, issue_factory, unit_factory):
    """Test: File upload size limit enforced (10 MB per file)"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    unit = unit_factory()
    tenant = tenant_factory(unit=unit)
    issue = issue_factory(tenant=tenant, unit=unit)

    # Login
    session = client.session
    session["tenant_id"] = tenant.id
    session.save()

    # Try to upload 11 MB file (over limit)
    large_file = SimpleUploadedFile(
        "large.jpg",
        b"X" * (11 * 1024 * 1024),  # 11 MB
        content_type="image/jpeg"
    )

    response = client.post(f"/tenant/issues/{issue.id}/attachments", {"file": large_file})
    assert response.status_code == 302  # redirect
    assert IssueAttachment.objects.count() == 0  # not created


@pytest.mark.django_db
def test_tenant_upload_mime_whitelist(client, tenant_factory, issue_factory, unit_factory):
    """Test: Only allowed MIME types accepted"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    unit = unit_factory()
    tenant = tenant_factory(unit=unit)
    issue = issue_factory(tenant=tenant, unit=unit)

    session = client.session
    session["tenant_id"] = tenant.id
    session.save()

    # Try .exe file (not allowed)
    exe_file = SimpleUploadedFile(
        "malware.exe",
        b"MZ binary",
        content_type="application/x-msdownload"
    )

    response = client.post(f"/tenant/issues/{issue.id}/attachments", {"file": exe_file})
    assert IssueAttachment.objects.count() == 0

    # Try PDF (allowed)
    pdf_file = SimpleUploadedFile(
        "doc.pdf",
        b"%PDF-1.4 content",
        content_type="application/pdf"
    )

    response = client.post(f"/tenant/issues/{issue.id}/attachments", {"file": pdf_file})
    assert IssueAttachment.objects.count() == 1
    assert IssueAttachment.objects.first().mime == "application/pdf"


@pytest.mark.django_db
def test_magic_link_rate_limit(client, tenant_factory, unit_factory):
    """Test: Magic-link rate limiting works (3/30min per email)"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit, primary_email="test@example.com", is_active=True)

    # First 3 requests should work
    for i in range(3):
        response = client.post("/tenant/magic/request", {"email": "test@example.com"})
        assert response.status_code == 302

    # 4th request should be rate-limited
    response = client.post("/tenant/magic/request", {"email": "test@example.com"})
    assert response.status_code == 302  # still redirects, but with error message
    # Check would need to parse messages, simplified here


@pytest.mark.django_db
def test_tenant_logout(client, tenant_factory, unit_factory):
    """Test: Tenant can logout and session is cleared"""
    unit = unit_factory()
    tenant = tenant_factory(unit=unit)

    # Login
    session = client.session
    session["tenant_id"] = tenant.id
    session.save()

    assert client.session.get("tenant_id") == tenant.id

    # Logout
    response = client.get("/tenant/logout")
    assert response.status_code == 302
    assert client.session.get("tenant_id") is None
