from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from .validators import validate_country_whitelist, validate_serial_number_format


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Country choices for Property model
COUNTRY_CHOICES = [
    ('DE', 'Deutschland'),
    ('AT', 'Österreich'),
    ('CH', 'Schweiz'),
]


class Property(TimeStampedModel):
    name = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default='DE',
        validators=[validate_country_whitelist],
        help_text="Country code (DE, AT, CH)"
    )
    geo_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text="Latitude (-90.0 to +90.0)"
    )
    geo_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text="Longitude (-180.0 to +180.0)"
    )
    notes = models.TextField(blank=True)

    # Archive fields (soft-delete)
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-delete flag for archived properties"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when property was archived"
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='archived_properties',
        help_text="User who archived this property"
    )

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.name or f"{self.street}, {self.postal_code} {self.city}"

    def archive(self, user):
        """Archive this property (soft-delete)"""
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['city']),
            models.Index(fields=['postal_code']),
            models.Index(fields=['is_archived']),
            models.Index(fields=['city', 'postal_code']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(geo_lat__isnull=True) | (Q(geo_lat__gte=-90.0) & Q(geo_lat__lte=90.0)),
                name='property_geo_lat_valid_range'
            ),
            models.CheckConstraint(
                check=Q(geo_lng__isnull=True) | (Q(geo_lng__gte=-180.0) & Q(geo_lng__lte=180.0)),
                name='property_geo_lng_valid_range'
            ),
        ]


class Unit(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_label = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, blank=True)
    rooms = models.PositiveSmallIntegerField(null=True, blank=True)
    area_sqm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Area in square meters (must be >= 0)"
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Archive fields (soft-delete) - Phase 1: Units Portal
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-delete flag for archived units"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when unit was archived"
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='archived_units',
        help_text="User who archived this unit"
    )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.unit_label} @ {self.property}"

    def archive(self, user):
        """Archive this unit (soft-delete)"""
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.save(update_fields=['is_archived', 'archived_at', 'archived_by'])

    class Meta:
        indexes = [
            models.Index(fields=["property", "unit_label"]),
            models.Index(fields=['is_archived']),
        ]


class Tenant(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    primary_email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="tenants", db_index=True)
    moved_in_at = models.DateField(null=True, blank=True)
    moved_out_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=Q(is_active=True, moved_out_at__isnull=True),
                name="uq_active_tenant_per_unit",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.primary_email


class Vendor(TimeStampedModel):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    trade = models.CharField(max_length=100, blank=True)
    address_text = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Issue(TimeStampedModel):
    class Category(models.TextChoices):
        WATER = "water", "Water"
        HEATING = "heating", "Heating"
        ELECTRICITY = "electricity", "Electricity"
        STRUCTURAL = "structural", "Structural"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        WAITING_TENANT = "WAITING_TENANT", "Waiting tenant"
        WAITING_VENDOR = "WAITING_VENDOR", "Waiting vendor"
        SCHEDULED = "SCHEDULED", "Scheduled"
        RESOLVED = "RESOLVED", "Resolved"
        CANCELLED = "CANCELLED", "Cancelled"

    ticket_no = models.CharField(max_length=32, null=True, blank=True, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name="issues")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="issues", null=True, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    severity = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    summary = models.CharField(max_length=255)
    description_raw = models.TextField(blank=True)
    description_struct = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    location_hint = models.CharField(max_length=200, blank=True)
    contact_times = models.CharField(max_length=200, blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    created_via = models.CharField(max_length=20, default="chat")

    # SLA Tracking (M9)
    first_response_at = models.DateTimeField(null=True, blank=True, help_text="When status changed from NEW")
    done_at = models.DateTimeField(null=True, blank=True, help_text="When status changed to RESOLVED/DONE")

    # Vendor Tracking (M10)
    vendor = models.ForeignKey('Vendor', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    vendor_first_contact_at = models.DateTimeField(null=True, blank=True, help_text="When vendor first logged in/commented")
    vendor_accepted_at = models.DateTimeField(null=True, blank=True, help_text="When vendor accepted the job")
    quote_document = models.ForeignKey('Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='quoted_issues')
    invoice_document = models.ForeignKey('Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoiced_issues')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(tenant__isnull=False) | Q(unit__isnull=False),
                name="ck_issue_has_tenant_or_unit",
            )
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["tenant", "unit"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Auto-generate ticket_no if not set (M9.5 Polish)
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only generate ticket_no for new issues without one
        if is_new and not self.ticket_no:
            from datetime import datetime
            year = datetime.now().year
            self.ticket_no = f"TCK-{year}-{str(self.pk).zfill(5)}"
            # Update without triggering save() again
            Issue.objects.filter(pk=self.pk).update(ticket_no=self.ticket_no)

    def __str__(self) -> str:  # pragma: no cover
        return f"#{self.pk or 'NEW'} {self.summary[:40]}"


class IssueAttachment(TimeStampedModel):
    class UploaderRole(models.TextChoices):
        TENANT = "tenant", "Tenant"
        STAFF = "staff", "Staff"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="issues/%Y/%m/%d/")
    mime = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    uploader_role = models.CharField(max_length=10, choices=UploaderRole.choices, default=UploaderRole.TENANT)


class VendorAttachment(TimeStampedModel):
    """Vendor uploads (Kostenvoranschlag, Rechnung)"""
    class Category(models.TextChoices):
        ESTIMATE = "estimate", "Kostenvoranschlag"
        INVOICE = "invoice", "Rechnung"
        OTHER = "other", "Sonstiges"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="vendor_attachments")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="uploads")
    category = models.CharField(max_length=20, choices=Category.choices)
    file = models.FileField(upload_to="vendor/%Y/%m/%d/")
    mime = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Optional notes about the file")

    def __str__(self) -> str:
        return f"{self.get_category_display()} - {self.issue.ticket_no}"


class IssueNote(TimeStampedModel):
    class Visibility(models.TextChoices):
        INTERNAL = "internal", "Internal"
        PUBLIC = "public", "Public"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.INTERNAL)
    text = models.TextField()


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        CONFIRMED = "confirmed", "Confirmed"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="appointments")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="appointments")
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INVITED)
    notes = models.TextField(blank=True)


class ChatSession(TimeStampedModel):
    class State(models.TextChoices):
        GREETING = "GREETING", "GREETING"
        CAPTURE_SUMMARY = "CAPTURE_SUMMARY", "CAPTURE_SUMMARY"
        CAPTURE_OCCURRED_AT = "CAPTURE_OCCURRED_AT", "CAPTURE_OCCURRED_AT"
        CAPTURE_LOCATION = "CAPTURE_LOCATION", "CAPTURE_LOCATION"
        CAPTURE_SEVERITY = "CAPTURE_SEVERITY", "CAPTURE_SEVERITY"
        CAPTURE_MEDIA = "CAPTURE_MEDIA", "CAPTURE_MEDIA"
        CAPTURE_CONTACT = "CAPTURE_CONTACT", "CAPTURE_CONTACT"
        CONFIRM = "CONFIRM", "CONFIRM"
        CREATE_ISSUE = "CREATE_ISSUE", "CREATE_ISSUE"
        DONE = "DONE", "DONE"

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    version = models.PositiveIntegerField(default=0)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_sessions")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_sessions")
    state = models.CharField(max_length=40, choices=State.choices, default=State.GREETING)
    payload = models.JSONField(default=dict, blank=True)
    transcript = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    issue = models.OneToOneField(
        "landlord.Issue",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_session",
    )

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
        ]


class IdempotencyKey(TimeStampedModel):
    key = models.UUIDField()
    scope = models.CharField(max_length=50)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="idempotency_keys")
    issue = models.ForeignKey(Issue, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "scope"], name="uq_idempotency_key_scope")
        ]


class TenantAuthToken(models.Model):
    """Magic-Link Token für Mieter-Login (passwordless)"""
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="auth_tokens", null=True)
    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.LOGIN)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    ua_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "purpose", "expires_at"], name="tenant_auth_idx"),
            models.Index(fields=["email", "expires_at"], name="email_expires_idx"),
        ]

    def is_valid(self) -> bool:
        from django.utils import timezone
        return not self.used_at and self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"Token {self.id} for {self.email}"


class VendorAuthToken(models.Model):
    """Magic-Link Token für Vendor-Login (passwordless)"""
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        INVITE = "invite", "Invitation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="auth_tokens")
    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.LOGIN)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    ua_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["vendor", "purpose", "expires_at"], name="vendor_auth_idx"),
            models.Index(fields=["email", "expires_at"], name="vendor_email_expires_idx"),
        ]

    def is_valid(self) -> bool:
        from django.utils import timezone
        return not self.used_at and self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"VendorToken {self.id} for {self.email}"


class Document(TimeStampedModel):
    """Central document storage for all entities"""
    class Category(models.TextChoices):
        CONTRACT = "vertrag", "Vertrag"
        INVOICE = "rechnung", "Rechnung"
        HANDOVER = "übergabe", "Übergabe"
        PLAN = "plan", "Plan/Grundriss"
        PHOTO = "foto", "Foto"
        OTHER = "sonstiges", "Sonstiges"

    class RelatedType(models.TextChoices):
        PROPERTY = "property", "Property"
        UNIT = "unit", "Unit"
        TENANT = "tenant", "Tenant"
        ISSUE = "issue", "Issue"
        VENDOR = "vendor", "Vendor"

    file = models.FileField(upload_to="docs/%Y/%m/")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)

    # Generic relation fields (DEPRECATED - use direct FKs below)
    related_type = models.CharField(max_length=20, choices=RelatedType.choices, db_index=True, blank=True)
    related_id = models.PositiveIntegerField(db_index=True, null=True, blank=True)

    # M11b: Direct ForeignKeys for easier querying
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Dokument gehört zu diesem Objekt"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Dokument gehört zu dieser Wohnung"
    )
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Dokument gehört zu diesem Mieter"
    )

    # Metadata
    size_bytes = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    notes = models.TextField(blank=True)

    # Versioning (M17a)
    current_version = models.PositiveSmallIntegerField(
        default=1,
        help_text="Current version number of this document"
    )
    supersedes = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='superseded_by',
        help_text="DEPRECATED: Use DocumentVersion instead"
    )

    # Validity period
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    # Uploader tracking
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=["related_type", "related_id", "category"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["valid_from", "valid_to"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class DocumentVersion(TimeStampedModel):
    """
    M17a: Stores historical versions of documents

    When a document is re-uploaded, the old version is archived here.
    This allows tracking changes over time and restoring old versions.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions',
        help_text="Parent document"
    )
    version_number = models.PositiveSmallIntegerField(
        help_text="Version number (1, 2, 3...)"
    )
    file = models.FileField(
        upload_to="docs/versions/%Y/%m/",
        help_text="Archived version of the file"
    )

    # Snapshot of metadata at time of archival
    size_bytes = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)

    # Who uploaded this version and when
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_document_versions'
    )

    # Optional comment about this version
    upload_comment = models.TextField(
        blank=True,
        help_text="Comment about this version (e.g. 'Corrected rent amount')"
    )

    class Meta:
        ordering = ['-version_number']  # Newest first
        unique_together = [['document', 'version_number']]
        indexes = [
            models.Index(fields=['document', '-version_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.document.name} v{self.version_number}"


class Contract(TimeStampedModel):
    """
    M12a: Mietvertrags-Verwaltung

    Represents a rental contract (Mietvertrag) between a landlord and tenant.
    Each contract is tied to a specific unit and tenant.
    """
    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ACTIVE = "active", "Aktiv"
        ENDED = "ended", "Beendet"
        CANCELLED = "cancelled", "Gekündigt"

    # Core Relations
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='contracts',
        help_text="Wohnung für diesen Vertrag"
    )
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='contracts',
        help_text="Mieter für diesen Vertrag"
    )

    # Contract Document (M11b + M17a)
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts',
        help_text="Vertrags-PDF (nutzt Versionshistorie!)"
    )

    # Contract Dates
    start_date = models.DateField(
        help_text="Vertragsbeginn (Einzugsdatum)"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Vertragsende (leer = unbefristet)"
    )
    notice_date = models.DateField(
        null=True,
        blank=True,
        help_text="Kündigungsdatum (falls gekündigt)"
    )

    # Financial Terms
    rent_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Kaltmiete pro Monat (€)"
    )
    additional_costs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Nebenkosten-Vorauszahlung pro Monat (€)"
    )
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Kaution (€)"
    )
    payment_day = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Zahlungstag im Monat (1-28)"
    )

    # Contract Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )

    # M14: Nebenkostenabrechnung - Umlage-Schlüssel
    class AllocationKey(models.TextChoices):
        AREA = 'area', 'Nach Fläche (m²)'
        PERSONS = 'persons', 'Nach Personenzahl'
        CONSUMPTION = 'consumption', 'Nach Verbrauch'
        UNITS = 'units', 'Nach Anzahl Wohnungen (gleichmäßig)'

    allocation_key = models.CharField(
        max_length=20,
        choices=AllocationKey.choices,
        default=AllocationKey.AREA,
        help_text='Wie werden Nebenkosten umgelegt? (M14)'
    )
    occupants_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Anzahl der Bewohner (für Personen-Umlage, M14)'
    )

    # Additional Info
    notes = models.TextField(
        blank=True,
        help_text="Interne Notizen zum Vertrag"
    )

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['unit', 'status']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        constraints = [
            # Only one active contract per unit
            models.UniqueConstraint(
                fields=['unit'],
                condition=Q(status='active'),
                name='unique_active_contract_per_unit'
            ),
        ]

    def __str__(self) -> str:
        return f"Vertrag {self.unit.unit_label} - {self.tenant.primary_email} ({self.start_date})"

    @property
    def total_rent(self) -> float:
        """Warmmiete (Kalt + NK)"""
        rent = float(self.rent_amount) if self.rent_amount is not None else 0.0
        costs = float(self.additional_costs) if self.additional_costs is not None else 0.0
        return rent + costs

    @property
    def is_active(self) -> bool:
        """Is contract currently active?"""
        return self.status == self.Status.ACTIVE

    @property
    def is_unlimited(self) -> bool:
        """Is contract unlimited (unbefristet)?"""
        return self.end_date is None


class PaymentTransaction(TimeStampedModel):
    """
    M12b: Zahlungstransaktionen für Mietverträge

    Tracks all payment transactions (rent, deposits, etc.) for contracts.
    Can be imported via CSV from bank statements.
    """
    class Type(models.TextChoices):
        RENT = "rent", "Miete"
        DEPOSIT = "deposit", "Kaution"
        ADDITIONAL_COSTS = "additional_costs", "Nebenkosten"
        OTHER = "other", "Sonstiges"

    class Status(models.TextChoices):
        PENDING = "pending", "Ausstehend"
        RECEIVED = "received", "Eingegangen"
        OVERDUE = "overdue", "Überfällig"
        CANCELLED = "cancelled", "Storniert"

    # Relations
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Zugehöriger Mietvertrag"
    )

    # Payment Details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Betrag in €"
    )
    transaction_date = models.DateField(
        help_text="Datum der Transaktion (Valutadatum)"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fälligkeitsdatum (wenn bekannt)"
    )

    # Type & Status
    payment_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.RENT,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
        db_index=True
    )

    # Bank Details
    reference = models.CharField(
        max_length=500,
        blank=True,
        help_text="Verwendungszweck / Referenz"
    )
    sender_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name des Zahlenden"
    )
    sender_iban = models.CharField(
        max_length=34,
        blank=True,
        help_text="IBAN des Zahlenden"
    )

    # Import Metadata
    csv_import_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Wann wurde diese Zahlung importiert?"
    )
    csv_row_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Original CSV-Zeile für Debugging"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Interne Notizen"
    )

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['contract', 'transaction_date']),
            models.Index(fields=['transaction_date', 'status']),
            models.Index(fields=['payment_type', 'status']),
        ]

    def __str__(self) -> str:
        return f"{self.get_payment_type_display()} €{self.amount} - {self.contract.unit.unit_label} ({self.transaction_date})"

    @property
    def is_overdue(self) -> bool:
        """Is this payment overdue?"""
        from django.utils import timezone
        if self.due_date and self.status == self.Status.PENDING:
            return self.due_date < timezone.now().date()
        return False


# ============================================================================
# M14: NEBENKOSTENABRECHNUNG (UTILITY BILLING)
# ============================================================================

class UtilityMeter(TimeStampedModel):
    """
    Zähler-Stammdaten für Versorgungsleistungen.
    M17: Default Meter Prefill

    Speichert die physischen Zähler (Seriennummern) pro Property/Unit.
    Ermöglicht automatisches Vorbefüllen der Zählernummer beim Erfassen.
    """

    class ScopeType(models.TextChoices):
        PROPERTY = 'property', 'Gebäudezähler'
        UNIT = 'unit', 'Wohnungszähler'

    class MeterType(models.TextChoices):
        WATER_COLD = 'cold_water', 'Kaltwasser'
        WATER_HOT = 'hot_water', 'Warmwasser'
        ELECTRICITY = 'electricity', 'Strom'
        GAS = 'gas', 'Gas (kWh)'

    # Polymorphic scope - either property OR unit
    scope_type = models.CharField(
        max_length=10,
        choices=ScopeType.choices,
        help_text='Ist dies ein Gebäude- oder Wohnungszähler?'
    )

    # FK to Property (if scope_type=property)
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='utility_meters',
        null=True,
        blank=True,
        help_text='Gebäude (nur wenn Gebäudezähler)'
    )

    # FK to Unit (if scope_type=unit)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='utility_meters',
        null=True,
        blank=True,
        help_text='Wohnung (nur wenn Wohnungszähler)'
    )

    meter_type = models.CharField(
        max_length=20,
        choices=MeterType.choices,
        help_text='Art des Zählers (Medium)'
    )

    serial_number = models.CharField(
        max_length=50,
        blank=True,
        validators=[validate_serial_number_format],
        help_text='Seriennummer des Versorgers (optional, A-Z/a-z/0-9/-/)'
    )

    is_default = models.BooleanField(
        default=False,
        help_text='Standardzähler für automatisches Vorbefüllen (max. 1 pro Scope+Medium)'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Ist der Zähler aktiv/installiert?'
    )

    initial_reading_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Startwert bei Installation (wird einmalig als "vorheriger Stand" verwendet)'
    )

    installed_at = models.DateField(
        null=True,
        blank=True,
        help_text='Installationsdatum'
    )

    removed_at = models.DateField(
        null=True,
        blank=True,
        help_text='Datum der Entfernung/Deaktivierung'
    )

    notes = models.TextField(
        blank=True,
        help_text='Notizen zum Zähler'
    )

    class Meta:
        ordering = ['scope_type', 'meter_type', '-is_default', '-is_active', 'serial_number']
        indexes = [
            models.Index(fields=['scope_type', 'property', 'meter_type']),
            models.Index(fields=['scope_type', 'unit', 'meter_type']),
            models.Index(fields=['is_default', 'is_active']),
        ]
        constraints = [
            # Ensure only ONE default per (scope_type, scope_id, meter_type)
            # For Property scopes
            models.UniqueConstraint(
                fields=['scope_type', 'property', 'meter_type'],
                condition=Q(is_default=True, scope_type='property'),
                name='unique_default_meter_property'
            ),
            # For Unit scopes
            models.UniqueConstraint(
                fields=['scope_type', 'unit', 'meter_type'],
                condition=Q(is_default=True, scope_type='unit'),
                name='unique_default_meter_unit'
            ),
            # Ensure scope consistency: property XOR unit
            models.CheckConstraint(
                check=(
                    Q(scope_type='property', property__isnull=False, unit__isnull=True) |
                    Q(scope_type='unit', unit__isnull=False, property__isnull=True)
                ),
                name='utility_meter_scope_consistency'
            ),
        ]

    def __str__(self) -> str:
        scope_name = str(self.property) if self.scope_type == 'property' else str(self.unit)
        sn = f" ({self.serial_number})" if self.serial_number else ""
        default = " [DEFAULT]" if self.is_default else ""
        return f"{self.get_meter_type_display()} - {scope_name}{sn}{default}"

    def save(self, *args, **kwargs):
        """Override save to normalize serial_number to uppercase"""
        if self.serial_number:
            self.serial_number = self.serial_number.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate scope consistency and default uniqueness"""
        from django.core.exceptions import ValidationError

        # Validate scope consistency
        if self.scope_type == 'property' and not self.property_id:
            raise ValidationError("Gebäudezähler benötigt eine Property-Zuordnung")
        if self.scope_type == 'unit' and not self.unit_id:
            raise ValidationError("Wohnungszähler benötigt eine Unit-Zuordnung")
        if self.scope_type == 'property' and self.unit_id:
            raise ValidationError("Gebäudezähler kann keine Unit haben")
        if self.scope_type == 'unit' and self.property_id:
            raise ValidationError("Wohnungszähler kann keine Property haben")

        # Validate default uniqueness (only if setting is_default=True)
        if self.is_default:
            existing_defaults = UtilityMeter.objects.filter(
                scope_type=self.scope_type,
                meter_type=self.meter_type,
                is_default=True
            )

            if self.scope_type == 'property':
                existing_defaults = existing_defaults.filter(property_id=self.property_id)
            else:
                existing_defaults = existing_defaults.filter(unit_id=self.unit_id)

            if self.pk:
                existing_defaults = existing_defaults.exclude(pk=self.pk)

            if existing_defaults.exists():
                raise ValidationError(
                    "Pro Objekt/Wohnung und Medium ist nur ein Standardzähler zulässig."
                )

    def get_scope_object(self):
        """Return the actual Property or Unit object"""
        return self.property if self.scope_type == 'property' else self.unit

    def get_reading_unit(self):
        """Return the reading unit for this meter type"""
        if self.meter_type in ['cold_water', 'hot_water']:
            return 'm³'
        else:  # electricity, gas
            return 'kWh'


class UtilityReading(TimeStampedModel):
    """
    Zählerstand für Versorgungsleistungen (Strom, Wasser, Gas, Heizung).
    M14: Nebenkostenabrechnung
    """

    class MeterType(models.TextChoices):
        WATER_COLD = 'water_cold', 'Kaltwasser'
        WATER_HOT = 'water_hot', 'Warmwasser'
        ELECTRICITY = 'electricity', 'Strom'
        GAS = 'gas', 'Gas'
        HEATING = 'heating', 'Heizung'

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='utility_readings',
        help_text='Wohnung für die der Zählerstand erfasst wird'
    )
    meter_type = models.CharField(
        max_length=20,
        choices=MeterType.choices,
        help_text='Art des Zählers'
    )
    reading_date = models.DateField(
        help_text='Datum der Ablesung'
    )
    meter_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Zählernummer (optional)'
    )
    current_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Aktueller Zählerstand'
    )
    previous_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Vorheriger Zählerstand (optional, wird automatisch gesetzt)'
    )
    consumption = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Verbrauch (current - previous, wird automatisch berechnet)'
    )
    notes = models.TextField(
        blank=True,
        help_text='Notizen zur Ablesung'
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utility_readings',
        help_text='Wer hat den Zählerstand erfasst?'
    )

    class Meta:
        ordering = ['-reading_date', '-created_at']
        indexes = [
            models.Index(fields=['unit', 'meter_type', 'reading_date']),
            models.Index(fields=['reading_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'meter_type', 'reading_date'],
                name='unique_reading_per_unit_type_date'
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_meter_type_display()} - {self.unit.unit_label} ({self.reading_date}): {self.current_value}"

    def save(self, *args, **kwargs):
        """Auto-calculate consumption if previous_value is set"""
        if self.previous_value is not None:
            self.consumption = self.current_value - self.previous_value

        # Auto-set previous_value from last reading if not provided
        if self.previous_value is None and self.pk is None:
            last_reading = UtilityReading.objects.filter(
                unit=self.unit,
                meter_type=self.meter_type,
                reading_date__lt=self.reading_date
            ).order_by('-reading_date').first()

            if last_reading:
                self.previous_value = last_reading.current_value
                self.consumption = self.current_value - self.previous_value

        super().save(*args, **kwargs)


# ============================================================================
# M16: CHECKLISTEN (HANDOVER PROTOCOLS)
# ============================================================================

class ChecklistTemplate(TimeStampedModel):
    """
    Template für Checklisten (z.B. Einzug, Auszug, Wartung).
    M16: Checklisten-System
    """

    class TemplateType(models.TextChoices):
        MOVE_IN = 'move_in', 'Einzugsprotokoll'
        MOVE_OUT = 'move_out', 'Auszugsprotokoll'
        INSPECTION = 'inspection', 'Wohnungsbesichtigung'
        MAINTENANCE = 'maintenance', 'Wartungsprotokoll'
        CUSTOM = 'custom', 'Benutzerdefiniert'

    name = models.CharField(
        max_length=200,
        help_text='Name der Vorlage (z.B. "Standard Einzugsprotokoll")'
    )
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        help_text='Art der Checkliste'
    )
    description = models.TextField(
        blank=True,
        help_text='Beschreibung und Verwendungszweck'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Ist diese Vorlage aktiv?'
    )

    # Template Items (stored as JSON for flexibility)
    default_items = models.JSONField(
        default=list,
        help_text='Standard-Prüfpunkte als JSON Array: [{"name": "...", "category": "...", "order": 1}]'
    )

    class Meta:
        ordering = ['template_type', 'name']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.get_template_type_display()}: {self.name}"


class Checklist(TimeStampedModel):
    """
    Konkrete Checkliste für eine Wohnung (erstellt aus Template).
    M16: Checklisten-System
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        IN_PROGRESS = 'in_progress', 'In Bearbeitung'
        COMPLETED = 'completed', 'Abgeschlossen'
        ARCHIVED = 'archived', 'Archiviert'

    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklists',
        help_text='Vorlage (optional, falls aus Template erstellt)'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='checklists',
        help_text='Wohnung für die diese Checkliste gilt'
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklists',
        help_text='Mieter (bei Ein-/Auszug)'
    )

    # Checklist Info
    title = models.CharField(
        max_length=200,
        help_text='Titel der Checkliste'
    )
    checklist_type = models.CharField(
        max_length=20,
        choices=ChecklistTemplate.TemplateType.choices,
        help_text='Art der Checkliste'
    )
    checklist_date = models.DateField(
        help_text='Datum der Begehung/Prüfung'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Participants
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_checklists',
        help_text='Durchgeführt von (Staff)'
    )

    # Notes
    general_notes = models.TextField(
        blank=True,
        help_text='Allgemeine Anmerkungen'
    )

    # Completion
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Wann wurde die Checkliste abgeschlossen?'
    )

    class Meta:
        ordering = ['-checklist_date', '-created_at']
        indexes = [
            models.Index(fields=['unit', 'checklist_date']),
            models.Index(fields=['status', 'checklist_date']),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.unit.unit_label} ({self.checklist_date})"

    @property
    def is_completed(self) -> bool:
        """Is checklist completed?"""
        return self.status == self.Status.COMPLETED

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on checked items"""
        total = self.items.count()
        if total == 0:
            return 0.0
        checked = self.items.filter(is_checked=True).count()
        return (checked / total) * 100


class ChecklistItem(TimeStampedModel):
    """
    Einzelner Prüfpunkt in einer Checkliste.
    M16: Checklisten-System
    """

    class Condition(models.TextChoices):
        EXCELLENT = 'excellent', 'Sehr gut'
        GOOD = 'good', 'Gut'
        FAIR = 'fair', 'Befriedigend'
        POOR = 'poor', 'Schlecht'
        DAMAGED = 'damaged', 'Beschädigt'
        NOT_APPLICABLE = 'n/a', 'Nicht zutreffend'

    checklist = models.ForeignKey(
        Checklist,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Zugehörige Checkliste'
    )

    # Item Info
    category = models.CharField(
        max_length=100,
        help_text='Kategorie (z.B. "Küche", "Bad", "Wohnzimmer")'
    )
    name = models.CharField(
        max_length=200,
        help_text='Name des Prüfpunkts (z.B. "Herd", "Dusche", "Fenster")'
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Reihenfolge der Anzeige'
    )

    # Check Status
    is_checked = models.BooleanField(
        default=False,
        help_text='Wurde dieser Punkt geprüft?'
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        blank=True,
        help_text='Zustand des geprüften Elements'
    )

    # Details
    notes = models.TextField(
        blank=True,
        help_text='Anmerkungen zu diesem Prüfpunkt'
    )
    photo = models.ImageField(
        upload_to='checklists/%Y/%m/',
        null=True,
        blank=True,
        help_text='Beweisfoto (optional)'
    )

    class Meta:
        ordering = ['checklist', 'order', 'category', 'name']
        indexes = [
            models.Index(fields=['checklist', 'order']),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_checked else "○"
        return f"{status} {self.category}: {self.name}"


# ============================================================================
# M15: WARTUNGSKALENDER (MAINTENANCE CALENDAR) - SIMPLIFIED
# ============================================================================

class MaintenanceItem(TimeStampedModel):
    """
    Wartungsaufgabe (z.B. Rauchmelder-Prüfung, Heizungswartung).
    M15: Wartungskalender
    """

    class Category(models.TextChoices):
        SMOKE_DETECTOR = 'smoke_detector', 'Rauchmelder'
        HEATING = 'heating', 'Heizung'
        ELEVATOR = 'elevator', 'Aufzug'
        FIRE_EXTINGUISHER = 'fire_extinguisher', 'Feuerlöscher'
        INSPECTION = 'inspection', 'Begehung'
        OTHER = 'other', 'Sonstiges'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        COMPLETED = 'completed', 'Erledigt'
        CANCELLED = 'cancelled', 'Abgebrochen'

    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices)

    # Assignment (EITHER property OR unit)
    property = models.ForeignKey(
        'Property',
        on_delete=models.CASCADE,
        related_name='maintenance_items',
        null=True,
        blank=True
    )
    unit = models.ForeignKey(
        'Unit',
        on_delete=models.CASCADE,
        related_name='maintenance_items',
        null=True,
        blank=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance'
    )

    # Schedule
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_maintenance'
    )

    # Cost
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['due_date', 'category']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['property', 'due_date']),
        ]

    def __str__(self) -> str:
        location = str(self.property) if self.property else (str(self.unit) if self.unit else "Allgemein")
        return f"{self.title} - {location} ({self.due_date})"


# Import AuditLog model
from landlord.models_audit import AuditLog  # noqa: E402, F401
