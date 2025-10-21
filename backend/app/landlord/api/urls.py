from django.urls import path

from .attachments import IssueAttachmentsView
from .issues import IssuesAdminListView
from .issues_export import IssuesExportCsvView
from .notes import IssueNotesView
from .tenants import TenantEraseView, TenantExportView
from .properties import (
    PropertyListAPIView,
    PropertyDetailAPIView,
    PropertyCreateAPIView,
    PropertyUpdateAPIView,
    PropertyDeleteAPIView,
    PropertyArchiveAPIView,
    PropertyUnarchiveAPIView,
)

urlpatterns = [
    # Admin: Issues
    path("admin/issues/", IssuesAdminListView.as_view(), name="admin-issues-list"),
    path("admin/issues/export.csv", IssuesExportCsvView.as_view(), name="admin-issues-export-csv"),
    path("admin/issues/<int:issue_id>/notes/", IssueNotesView.as_view(), name="admin-issue-notes"),
    path("admin/issues/<int:issue_id>/attachments/", IssueAttachmentsView.as_view(), name="admin-issue-attachments"),
    
    # Admin: Tenants
    path("admin/tenants/<int:id>/export", TenantExportView.as_view(), name="admin-tenant-export"),
    path("admin/tenants/<int:id>/erase", TenantEraseView.as_view(), name="admin-tenant-erase"),
    
    # Portal: Properties (Phase 2)
    path("portal/properties/", PropertyListAPIView.as_view(), name="portal-properties-list"),
    path("portal/properties/create/", PropertyCreateAPIView.as_view(), name="portal-properties-create"),
    path("portal/properties/<int:pk>/", PropertyDetailAPIView.as_view(), name="portal-properties-detail"),
    path("portal/properties/<int:pk>/update/", PropertyUpdateAPIView.as_view(), name="portal-properties-update"),
    path("portal/properties/<int:pk>/delete/", PropertyDeleteAPIView.as_view(), name="portal-properties-delete"),
    path("portal/properties/<int:pk>/archive/", PropertyArchiveAPIView.as_view(), name="portal-properties-archive"),
    path("portal/properties/<int:pk>/unarchive/", PropertyUnarchiveAPIView.as_view(), name="portal-properties-unarchive"),
]
