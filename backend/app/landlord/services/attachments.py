import mimetypes
import uuid
from typing import Iterable, List

from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

from ..models import Issue, IssueAttachment

ALLOWED_MIME = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_MB = 10
MAX_TOTAL_MB = 40


def _mime_ok(name: str, content_type: str) -> bool:
    if not content_type:
        guess = mimetypes.guess_type(name)[0]
        content_type = guess or ""
    base = content_type.split(";")[0].strip().lower()
    return base in ALLOWED_MIME


def save_issue_attachments(issue: Issue, files: Iterable) -> List[IssueAttachment]:
    total = 0
    saved: List[IssueAttachment] = []
    for f in files:
        size = getattr(f, "size", 0)
        if not size and hasattr(f, "seek") and hasattr(f, "tell"):
            # compute size without consuming buffer permanently
            try:
                cur = f.tell()
                f.seek(0, 2)
                size = f.tell()
                f.seek(cur)
            except Exception:
                size = 0
        total += size
        if size > MAX_FILE_MB * 1024 * 1024:
            raise ValidationError(f"FILE_TOO_LARGE: {getattr(f,'name','file')}")
        if total > MAX_TOTAL_MB * 1024 * 1024:
            raise ValidationError("TOTAL_TOO_LARGE")
        ctype = getattr(f, "content_type", "") or ""
        name = get_valid_filename(getattr(f, "name", f"upload-{uuid.uuid4().hex}"))
        if not _mime_ok(name, ctype):
            raise ValidationError(f"UNSUPPORTED_MEDIA_TYPE: {name}")
        # Save and backfill meta via FileField.save into storage
        from django.utils import timezone
        y = timezone.now().strftime("%Y")
        m = timezone.now().strftime("%m")
        prefix = f"issues/{y}/{m}/{issue.id}/"
        unique = f"{uuid.uuid4().hex}-{name}"
        ia = IssueAttachment(issue=issue)
        ia.file.save(prefix + unique, f, save=False)
        ia.mime = (ctype.split(";")[0].strip().lower() or mimetypes.guess_type(name)[0] or "")[:100]
        ia.size_bytes = size or (len(getattr(f, 'read', lambda: b'')()) if hasattr(f, 'read') else None)
        ia.uploader_role = IssueAttachment.UploaderRole.STAFF
        ia.save()
        saved.append(ia)
    return saved
