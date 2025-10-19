from django.shortcuts import get_object_or_404, render
from landlord.models import Appointment, Issue, IssueNote
from landlord.utils.public_link import parse_token


def issue_status(request, token: str):
    ticket = parse_token(token)
    issue = get_object_or_404(
        Issue.objects.select_related("unit", "tenant"),
        ticket_no=ticket
    )
    notes = IssueNote.objects.filter(issue=issue, visibility="tenant").order_by("-created_at")[:20]
    appts = Appointment.objects.filter(issue=issue).order_by("start")
    return render(request, "chat/status.html", {
        "issue": issue, "notes": notes, "appts": appts, "token": token
    })
