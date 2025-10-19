from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Issue
from ..serializers import IssueAttachmentSerializer
from ..services.attachments import save_issue_attachments


class IssueAttachmentsView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, issue_id: int):
        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            return Response({"code":"NOT_FOUND","detail":"Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist("files") or list(request.FILES.values())
        if not files:
            return Response({"code":"VALIDATION_ERROR","field":"files","detail":"No files provided"}, status=400)

        try:
            saved = save_issue_attachments(issue, files)
        except ValidationError as e:
            msg = str(e)
            if "UNSUPPORTED_MEDIA_TYPE" in msg:
                return Response({"code":"UNSUPPORTED_MEDIA_TYPE","detail":msg}, status=415)
            if "FILE_TOO_LARGE" in msg or "TOTAL_TOO_LARGE" in msg:
                return Response({"code":"PAYLOAD_TOO_LARGE","detail":msg}, status=413)
            return Response({"code":"VALIDATION_ERROR","detail":msg}, status=400)

        return Response(IssueAttachmentSerializer(saved, many=True).data, status=201)
