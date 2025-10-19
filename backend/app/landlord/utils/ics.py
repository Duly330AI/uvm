from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone as dt_timezone

from django.utils import timezone


def _fmt(dt: datetime) -> str:
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    dt = dt.astimezone(dt_timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(s: str) -> str:
    return (s or "").replace("\r", " ").replace("\n", " ").replace(";", r"\;").replace(",", r"\,")


def build_ics(appt, site_domain: str) -> bytes:
    uid = f"{uuid.uuid4()}@{site_domain}"
    now = timezone.now()
    organizer = f"MAILTO:noreply@{site_domain}"
    attendee = f"MAILTO:{(appt.issue.tenant.primary_email if getattr(appt.issue, 'tenant', None) and appt.issue.tenant.primary_email else 'unknown@example.com')}"
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//UVM//1.0//DE",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_fmt(now)}",
        f"DTSTART:{_fmt(appt.start)}",
        f"DTEND:{_fmt(appt.end)}",
        f"SUMMARY:{_ics_escape(f'Termin {appt.issue.ticket_no}')}",
        f"ORGANIZER:{organizer}",
        f"ATTENDEE:{attendee}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    # CRLF join per RFC
    return ("\r\n".join(lines)).encode("utf-8")
