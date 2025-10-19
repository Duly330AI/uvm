from django.urls import path

from .attachments import IssueAttachmentsView
from .issues import IssuesAdminListView
from .issues_export import IssuesExportCsvView
from .notes import IssueNotesView
from .tenants import TenantEraseView, TenantExportView

urlpatterns = [
    path("admin/issues/", IssuesAdminListView.as_view(), name="admin-issues-list"),
    path("admin/issues/export.csv", IssuesExportCsvView.as_view(), name="admin-issues-export-csv"),
    path("admin/issues/<int:issue_id>/notes/", IssueNotesView.as_view(), name="admin-issue-notes"),
    path("admin/issues/<int:issue_id>/attachments/", IssueAttachmentsView.as_view(), name="admin-issue-attachments"),
    path("admin/tenants/<int:id>/export", TenantExportView.as_view(), name="admin-tenant-export"),
    path("admin/tenants/<int:id>/erase", TenantEraseView.as_view(), name="admin-tenant-erase"),
]
