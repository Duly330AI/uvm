import io

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from landlord.models import Issue, Property, Tenant, Unit


@pytest.mark.django_db
def test_issue_attachments_limits_types_and_no_files_case(client):
    admin = User.objects.create_superuser("admin","a@x.de","pw")
    client.force_login(admin)
    prop = Property.objects.create(name="Haus A", street="x", postal_code="1", city="B")
    unit = Unit.objects.create(property=prop, unit_label="WE 1")
    t = Tenant.objects.create(unit=unit, primary_email="mieter@example.com")
    issue = Issue.objects.create(ticket_no="TCK-2025-00013", unit=unit, tenant=t, status="NEW", severity=3, summary="Wasser")

    url = reverse("admin-issue-attachments", kwargs={"issue_id": issue.id})

    # 400: no files
    r = client.post(url, {}, format="multipart")
    assert r.status_code == 400
    assert r.json().get("code") == "VALIDATION_ERROR"

    # ok: small png
    png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00"*1000)
    png.name = "bild.png"
    r = client.post(url, {"files": png}, format="multipart")
    assert r.status_code == 201

    # bad type
    txt = io.BytesIO(b"hello")
    txt.name = "note.txt"
    r = client.post(url, {"files": txt}, format="multipart")
    assert r.status_code == 415

    # too big (>10MB)
    big = io.BytesIO(b"\x00" * (10*1024*1024 + 1))
    big.name = "big.pdf"
    r = client.post(url, {"files": big}, format="multipart")
    assert r.status_code == 413
