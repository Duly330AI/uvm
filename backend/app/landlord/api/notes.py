from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.exceptions import NotFound
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAdminUser

if TYPE_CHECKING:
    from django.db.models import QuerySet

from ..models import Issue, IssueNote
from ..serializers import IssueNoteCreateSerializer, IssueNoteSerializer


class IssueNotesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]

    def get_queryset(self) -> QuerySet[IssueNote]:  # type: ignore[override]
        issue_id = self.kwargs["issue_id"]
        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            raise NotFound("Issue not found") from None
        return IssueNote.objects.filter(issue=issue).select_related("author").order_by("-created_at", "-id")

    def get_serializer_class(self):  # type: ignore[override]
        return IssueNoteCreateSerializer if self.request.method == "POST" else IssueNoteSerializer

    def perform_create(self, serializer):
        issue_id = self.kwargs["issue_id"]
        issue = Issue.objects.get(pk=issue_id)
        serializer.save(issue=issue, author=self.request.user)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        resp.status_code = 201
        return resp
