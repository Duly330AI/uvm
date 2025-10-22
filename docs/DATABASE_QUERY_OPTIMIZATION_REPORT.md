# Database Query Optimization Report

**Scan Date:** 2025-10-22  
**Scope:** `backend/app/landlord`, `backend/app/config`  
**Tooling:** Manual code review + Django ORM heuristics

## 🟡 N+1 Queries gefunden

- **backend/app/landlord/api/tenants.py:120** – `TenantEraseView` loops through every issue and executes `IssueNote.objects.filter(...).exists()` per row, turning a redaction request into `1 + N` queries on `IssueNote`.  
  - *Impact:* Erasing a tenant with 250 historic tickets generates 251 queries (and repeated text lookups), slowing GDPR workflows and holding a transaction open longer than necessary.  
  - *Fix (1.5h):* Fetch all affected issue IDs in one query, pre-load the set of notes that already contain the marker, and bulk-create the missing audit notes.
    ```python
    # backend/app/landlord/api/tenants.py
    issue_ids = list(Issue.objects.filter(tenant=tenant).values_list("id", flat=True))
    existing = set(
        IssueNote.objects.filter(issue_id__in=issue_ids, text__icontains=marker)
        .values_list("issue_id", flat=True)
    )
    IssueNote.objects.bulk_create(
        IssueNote(
            issue_id=i,
            text=f"{marker} by admin at {timezone.now().isoformat()}",
            visibility=getattr(IssueNote, "VISIBILITY_INTERNAL", "internal"),
        )
        for i in issue_ids
        if i not in existing
    )
    ```
  - *Verification:* Hit `/api/portal/tenants/{id}/erase/` for a tenant with >100 issues under `django-debug-toolbar`; confirm SQL queries drop to three.

## 🟡 Query Hotspots

- **backend/app/landlord/api/units.py:203-213** – `UnitDeleteAPIView` calls `.exists()` and `.count()` on four related managers one after another, doubling queries for the same relationship and triggering up to eight round-trips.  
  - *Fix (1h):* Annotate counts in the base queryset so the object arrives with dependency numbers.
    ```python
    from django.db.models import Count

    class UnitDeleteAPIView(DestroyAPIView):
        queryset = (
            Unit.objects.all()
            .annotate(
                tenant_count=Count("tenants", distinct=True),
                meter_count=Count("utility_meters", distinct=True),
                issue_count=Count("issues", distinct=True),
                contract_count=Count("contracts", distinct=True),
            )
        )

        def destroy(self, request, *args, **kwargs):
            unit = self.get_object()
            dependencies = []
            if unit.tenant_count:
                dependencies.append(f"{unit.tenant_count} Mieter")
            # ...
    ```
  - *Verification:* Delete a unit with tenants/meters while tailing PostgreSQL logs; total queries should fall from 7→2.

- **backend/app/landlord/views_tenant.py:193** – Attachment quota check iterates over every attachment (`sum(a.size_bytes or 0 for a in issue.attachments.all())`) and loads files into Python.  
  - *Fix (0.5h):* Use an aggregate to sum on the database side.
    ```python
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    total_size = issue.attachments.aggregate(
        total=Coalesce(Sum("size_bytes"), 0)
    )["total"]
    if total_size + file.size > 40 * 1024 * 1024:
        ...
    ```
  - *Verification:* Upload a file and confirm via `django-debug-toolbar` that only one attachment query is executed.

## 🟡 Missing Indexes

- **`IssueNote` time-ordered lookups** – Views (`views_portal.issue_detail`, `views_tenant.issue_detail`) fetch the latest 50 notes via `IssueNote.objects.filter(issue=...).order_by("-created_at")`. The model currently relies on the implicit FK index, leading to repeated sorts.  
  - *Fix (1h + migration):*
    ```python
    class IssueNote(TimeStampedModel):
        ...
        class Meta:
            indexes = [
                models.Index(fields=["issue", "-created_at"], name="issue_note_recent_idx"),
            ]
    ```

- **`Appointment` listings** – Multiple views filter by `issue` and `order_by("start")` (e.g., `views_portal.issue_detail`, `views_portal.appointment_list`). No composite index exists on `(issue, start)`, causing extra sort work as ticket volume grows.  
  - *Fix (1h + migration):*
    ```python
    class Appointment(TimeStampedModel):
        ...
        class Meta:
            indexes = [
                models.Index(fields=["issue", "start"], name="appointment_issue_start_idx"),
            ]
    ```

- **`VendorAttachment` history** – Portal detail pages pull `issue.vendor_attachments.select_related("vendor").order_by("-created_at")`. Add an index on `(issue, -created_at)` to keep the query using the timestamp order.  
  - *Fix (1h + migration):*
    ```python
    class VendorAttachment(TimeStampedModel):
        ...
        class Meta:
            indexes = [
                models.Index(fields=["issue", "-created_at"], name="vendor_attachment_recent_idx"),
            ]
    ```

*Migration reminder:* Add new `Meta.indexes` entries and run `python manage.py makemigrations landlord && migrate`. Update migration dependencies to avoid touching excluded directories manually.

## 🟢 Gut gemacht

- `backend/app/landlord/views_portal.py` consistently uses `select_related` for issue/tenant/property joins, keeping dashboard and list pages lean.  
- API list views (`IssuesAdminListView`, `UnitListAPIView`, `PropertyListAPIView`) combine filtering with pagination and include `annotate` where counts are needed, preventing unbounded record loads.  
- Most detail views guard against N+1 on tenants/vendors by selecting related units and properties upfront.

## Follow-Up

- Re-run the tenant erasure flow and unit delete API behind `django-debug-toolbar` to capture the reduced SQL footprint and attach screenshots to the audit trail.  
- After adding indexes, execute `EXPLAIN ANALYZE` for `IssueNote` and `Appointment` queries to confirm index utilization and document the before/after timings in `docs/db_explain_logs/`.
