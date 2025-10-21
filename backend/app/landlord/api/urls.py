from django.urls import path

from .attachments import IssueAttachmentsView
from .issues import IssuesAdminListView
from .issues_export import IssuesExportCsvView
from .meters import (
    PropertyMeterCreateAPIView,
    PropertyMeterDeleteAPIView,
    PropertyMeterDetailAPIView,
    PropertyMeterListAPIView,
    PropertyMeterUpdateAPIView,
)
from .notes import IssueNotesView
from .properties import (
    PropertyArchiveAPIView,
    PropertyCreateAPIView,
    PropertyDeleteAPIView,
    PropertyDetailAPIView,
    PropertyListAPIView,
    PropertyUnarchiveAPIView,
    PropertyUpdateAPIView,
)
from .tenants import TenantEraseView, TenantExportView

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

    # Portal: Utility Meters (Phase 3)
    path("portal/properties/<int:property_id>/meters/", PropertyMeterListAPIView.as_view(), name="portal-property-meters-list"),
    path("portal/properties/<int:property_id>/meters/create/", PropertyMeterCreateAPIView.as_view(), name="portal-property-meters-create"),
    path("portal/properties/<int:property_id>/meters/<int:pk>/", PropertyMeterDetailAPIView.as_view(), name="portal-property-meters-detail"),
    path("portal/properties/<int:property_id>/meters/<int:pk>/update/", PropertyMeterUpdateAPIView.as_view(), name="portal-property-meters-update"),
    path("portal/properties/<int:property_id>/meters/<int:pk>/delete/", PropertyMeterDeleteAPIView.as_view(), name="portal-property-meters-delete"),
]
