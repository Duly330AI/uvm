from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from landlord import (
    views_checklist,
    views_contracts,
    views_documents,
    views_maintenance,
    views_payments,
    views_portal,
    views_public,
    views_reports,
    views_tenant,
    views_utility,
    views_vendor,
)
from landlord.admin_views import issue_report
from landlord.views import (
    ChatConfirmView,
    ChatMessageView,
    ChatPageView,
    chat_session_create_plain,
)


def healthz_view(_request):
    # Lazy imports to avoid DB/Redis at import time
    from django.db import connections
    from django.db.utils import OperationalError

    db_ok = False
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            db_ok = True
    except OperationalError:
        db_ok = False

    redis_ok = False
    try:
        import redis

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return JsonResponse({"status": "ok", "db": db_ok, "redis": redis_ok})


def api_ping_view(_request):
    return JsonResponse({"pong": True})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("landlord.api.urls")),
    path("admin/landlord/issue/report/", admin.site.admin_view(issue_report), name="landlord_issue_report"),
    path("healthz", healthz_view),
    path("api/ping/", api_ping_view),
    # Chat API
    path("chat/", ChatPageView.as_view(), name="chat_page"),
    # Plain Django view first to accept empty POST without parser 415s
    path("api/chat/sessions/", chat_session_create_plain),
    path("api/chat/sessions/<uuid:id>/message", ChatMessageView.as_view()),
    path("api/chat/sessions/<uuid:id>/confirm", ChatConfirmView.as_view()),
    # Public ticket status
    path("t/<str:token>/", views_public.issue_status, name="issue_status"),
    # Vermieter-Portal (staff-only)
    path("portal/", views_portal.dashboard, name="portal_dashboard"),
    path("portal/issues/", views_portal.issues_list, name="portal_issues"),
    path("portal/issues/<int:pk>/", views_portal.issue_detail, name="portal_issue_detail"),
    # HTMX Actions
    path("portal/issues/<int:pk>/status", views_portal.issue_set_status, name="portal_issue_set_status"),
    path("portal/issues/<int:pk>/notes", views_portal.issue_add_note, name="portal_issue_add_note"),
    path("portal/issues/<int:pk>/appointment", views_portal.issue_add_appointment, name="portal_issue_add_appt"),
    path("portal/issues/<int:pk>/assign-vendor", views_portal.issue_assign_vendor, name="portal_issue_assign_vendor"),
    path("portal/appointments/<int:pk>/delete", views_portal.appointment_delete, name="portal_appointment_delete"),
    # Tenant (Mieter) Portal
    path("tenant/", views_tenant.login_page, name="tenant_login"),
    path("tenant/magic/request", views_tenant.request_magic_link, name="tenant_magic_request"),
    path("tenant/magic/<str:token_id>/", views_tenant.verify_magic_link, name="tenant_magic_verify"),
    path("tenant/issues/", views_tenant.my_issues, name="tenant_my_issues"),
    path("tenant/issues/<int:pk>/", views_tenant.issue_detail, name="tenant_issue_detail"),
    path("tenant/issues/<int:pk>/notes", views_tenant.add_note, name="tenant_add_note"),
    path("tenant/issues/<int:pk>/attachments", views_tenant.add_attachment, name="tenant_add_attachment"),
    path("tenant/logout", views_tenant.logout, name="tenant_logout"),
    # Documents (M9 + M17a)
    path("portal/documents/", views_documents.documents_list, name="portal_documents"),
    path("portal/documents/upload", views_documents.document_upload, name="portal_document_upload"),
    path("portal/documents/<int:pk>/delete", views_documents.document_delete, name="portal_document_delete"),
    path("portal/documents/<int:pk>/history/", views_documents.document_history, name="portal_document_history"),
    path("portal/documents/<int:pk>/version/<int:version_number>/", views_documents.document_version_download, name="portal_document_version_download"),
    # Contracts (M12a)
    path("portal/contracts/", views_contracts.contracts_list, name="portal_contracts"),
    path("portal/contracts/<int:pk>/", views_contracts.contract_detail, name="portal_contract_detail"),
    # Payments (M12b)
    path("portal/payments/", views_payments.payments_list, name="portal_payments"),
    path("portal/payments/upload", views_payments.payment_csv_upload, name="portal_payment_csv_upload"),
    # Utility Billing (M14)
    path("portal/utility/readings/", views_utility.utility_readings_list, name="portal_utility_readings"),
    path("portal/utility/readings/create", views_utility.utility_reading_create, name="portal_utility_reading_create"),
    path("portal/utility/calculation/", views_utility.utility_calculation_preview, name="portal_utility_calculation"),
    path("portal/utility/export/<int:property_id>/<str:start_date>/<str:end_date>/", views_utility.utility_billing_export, name="portal_utility_export"),
    # M17: Utility Meter Prefill API
    path("api/utility/meters/default", views_utility.api_get_default_meter, name="api_get_default_meter"),
    path("api/utility/meters/last-reading", views_utility.api_get_last_reading, name="api_get_last_reading"),
    # Checklisten (M16)
    path("portal/checklists/", views_checklist.checklists_list, name="portal_checklists"),
    path("portal/checklists/templates/", views_checklist.checklist_templates_list, name="portal_checklist_templates"),
    path("portal/checklists/create", views_checklist.checklist_create, name="portal_checklist_create"),
    path("portal/checklists/<int:pk>/", views_checklist.checklist_detail, name="portal_checklist_detail"),
    path("portal/checklists/<int:pk>/complete", views_checklist.checklist_complete, name="portal_checklist_complete"),
    path("portal/checklists/<int:pk>/pdf", views_checklist.checklist_export_pdf, name="portal_checklist_pdf"),
    path("portal/checklists/items/<int:pk>/update", views_checklist.checklist_item_update, name="portal_checklist_item_update"),
    # M15: Wartungskalender
    path("portal/maintenance/", views_maintenance.maintenance_list, name="portal_maintenance_list"),
    path("portal/maintenance/create", views_maintenance.maintenance_create, name="portal_maintenance_create"),
    path("portal/maintenance/<int:pk>/", views_maintenance.maintenance_detail, name="portal_maintenance_detail"),
    path("portal/maintenance/<int:pk>/complete", views_maintenance.maintenance_complete, name="portal_maintenance_complete"),
    path("portal/maintenance/<int:pk>/edit", views_maintenance.maintenance_edit, name="portal_maintenance_edit"),
    path("portal/maintenance/<int:pk>/delete", views_maintenance.maintenance_delete, name="portal_maintenance_delete"),
    # Reports & KPI (M9)
    path("portal/reports/", views_reports.reports_kpi, name="portal_reports"),
    path("portal/reports/export", views_reports.export_kpi_csv, name="portal_reports_export"),
    # Tenant Management (PR 2)
    path("portal/tenants/", views_portal.tenants_list, name="portal_tenants"),
    path("portal/tenants/new", views_portal.tenant_create, name="portal_tenant_create"),
    path("portal/tenants/<int:pk>/edit", views_portal.tenant_edit, name="portal_tenant_edit"),
    path("portal/tenants/<int:pk>/deactivate", views_portal.tenant_deactivate, name="portal_tenant_deactivate"),
    path("portal/tenants/<int:pk>/delete", views_portal.tenant_delete, name="portal_tenant_delete"),
    # Vendor Portal (M11)
    path("vendor/", views_vendor.vendor_login, name="vendor_login"),
    path("vendor/auth/<str:token_id>/", views_vendor.vendor_magic_link, name="vendor_magic_link"),
    path("vendor/issues/", views_vendor.vendor_issues, name="vendor_issues"),
    path("vendor/issues/<int:pk>/", views_vendor.vendor_issue_detail, name="vendor_issue_detail"),
    path("vendor/issues/<int:pk>/upload", views_vendor.vendor_upload_file, name="vendor_upload_file"),
    path("vendor/logout", views_vendor.vendor_logout, name="vendor_logout"),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
