from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Property(TimeStampedModel):
    name = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Deutschland")
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.name or f"{self.street}, {self.postal_code} {self.city}"


class Unit(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_label = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, blank=True)
    rooms = models.PositiveSmallIntegerField(null=True, blank=True)
    area_sqm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["property", "unit_label"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.unit_label} @ {self.property}"


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
        return float(self.rent_amount) + float(self.additional_costs)

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


