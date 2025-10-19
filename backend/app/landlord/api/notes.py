from rest_framework.exceptions import NotFound
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAdminUser

from ..models import Issue, IssueNote
from ..serializers import IssueNoteCreateSerializer, IssueNoteSerializer


class IssueNotesView(ListCreateAPIView):
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        issue_id = self.kwargs["issue_id"]
        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            raise NotFound("Issue not found")
        return IssueNote.objects.filter(issue=issue).select_related("author").order_by("-created_at", "-id")

    def get_serializer_class(self):
        return IssueNoteCreateSerializer if self.request.method == "POST" else IssueNoteSerializer

    def perform_create(self, serializer):
        issue_id = self.kwargs["issue_id"]
        issue = Issue.objects.get(pk=issue_id)
        serializer.save(issue=issue, author=self.request.user)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        resp.status_code = 201
        return resp
