from datetime import timedelta

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from . import models


class IssueNoteInline(admin.TabularInline):
	model = models.IssueNote
	extra = 0


class IssueAttachmentInline(admin.TabularInline):
	model = models.IssueAttachment
	extra = 0


class AppointmentInline(admin.TabularInline):
	model = models.Appointment
	extra = 0


# M17: UtilityMeter Inlines
class UtilityMeterInline(admin.TabularInline):
	"""
	Inline for managing utility meters (M17: Default Meter Prefill)
	Used in both PropertyAdmin and UnitAdmin
	"""
	model = models.UtilityMeter
	extra = 0
	fields = (
		'meter_type',
		'serial_number',
		'is_default',
		'is_active',
		'initial_reading_value',
		'installed_at',
		'removed_at',
		'notes',
	)
	verbose_name = "Zähler (Stammdaten)"
	verbose_name_plural = "Zähler (Stammdaten)"

	def get_queryset(self, request):
		"""Order by: default first, then active, then meter type"""
		qs = super().get_queryset(request)
		return qs.order_by('-is_default', '-is_active', 'meter_type')


class PropertyUtilityMeterInline(UtilityMeterInline):
	"""Utility meters for Properties (building-level)"""

	def get_formset(self, request, obj=None, **kwargs):
		formset = super().get_formset(request, obj, **kwargs)
		# Set scope_type to 'property' for all forms (only if form exists)
		if hasattr(formset, 'form') and hasattr(formset.form, 'base_fields'):
			if 'scope_type' in formset.form.base_fields:
				formset.form.base_fields['scope_type'].initial = 'property'
		return formset

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.filter(scope_type='property')


class UnitUtilityMeterInline(UtilityMeterInline):
	"""Utility meters for Units (apartment-level)"""

	def get_formset(self, request, obj=None, **kwargs):
		formset = super().get_formset(request, obj, **kwargs)
		# Set scope_type to 'unit' for all forms (only if form exists)
		if hasattr(formset, 'form') and hasattr(formset.form, 'base_fields'):
			if 'scope_type' in formset.form.base_fields:
				formset.form.base_fields['scope_type'].initial = 'unit'
		return formset

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.filter(scope_type='unit')


@admin.register(models.Property)
class PropertyAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "street", "postal_code", "city", "created_at")
	search_fields = ("name", "street", "postal_code", "city")
	list_filter = ("city",)
	inlines = [PropertyUtilityMeterInline]


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
	list_display = ("id", "property", "unit_label", "is_active", "created_at")
	search_fields = ("unit_label", "property__street", "property__city")
	list_filter = ("is_active", "property")
	inlines = [UnitUtilityMeterInline]


@admin.register(models.Tenant)
class TenantAdmin(admin.ModelAdmin):
	list_display = ("id", "primary_email", "phone", "unit", "is_active", "created_at")
	search_fields = ("primary_email", "phone", "unit__unit_label")
	list_filter = ("is_active",)


@admin.register(models.Vendor)
class VendorAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "email", "phone", "trade")
	search_fields = ("name", "email", "trade")
	list_filter = ("trade",)


@admin.register(models.Issue)
class IssueAdmin(admin.ModelAdmin):
	list_display = ("ticket_no", "status", "category", "severity", "unit", "tenant", "created_at")
	list_filter = ("status", "category", "severity", "unit__property")
	search_fields = (
		"ticket_no",
		"summary",
		"tenant__user__email",
		"tenant__user__first_name",
		"tenant__user__last_name",
	)
	date_hierarchy = "created_at"
	inlines = [IssueNoteInline, IssueAttachmentInline, AppointmentInline]
	actions = ("mark_in_progress", "assign_vendor_krach", "mark_waiting_tenant",)
	readonly_fields = ("ticket_no_copy",)

	def ticket_no_copy(self, obj):
		from django.utils.html import format_html
		return format_html(
			'<code id="ticket">{}</code> '
			'<button type="button" class="button" onclick="navigator.clipboard.writeText(document.getElementById(\'ticket\').innerText)">Copy</button>',
			obj.ticket_no,
		)

	ticket_no_copy.short_description = "Ticket"

	@admin.action(description="Status: In Arbeit setzen")
	def mark_in_progress(self, request, queryset):
		from .services.issues import update_status
		with transaction.atomic():
			for issue in queryset:
				update_status(issue, models.Issue.Status.IN_PROGRESS)

	@admin.action(description="Vendor Krach zuweisen (+ Termin +2d/1h)")
	def assign_vendor_krach(self, request, queryset):
		# pick or create a demo vendor "Krach"
		vendor, _ = models.Vendor.objects.get_or_create(name="Krach", defaults={"trade": "Sanitär"})
		in_two_days = timezone.now() + timedelta(days=2)
		with transaction.atomic():
			for issue in queryset:
				start = in_two_days
				end = start + timedelta(hours=1)
				appt = models.Appointment.objects.create(issue=issue, vendor=vendor, start=start, end=end)
				issue.status = models.Issue.Status.WAITING_VENDOR
				issue.save(update_fields=["status", "updated_at"])
		try:
			from .tasks import send_appointment_invite
			for issue in queryset:
				appt = issue.appointments.order_by("-created_at").first()
				if appt:
					send_appointment_invite.delay(appt.id)
		except Exception:
			messages.warning(request, "Termin-Mail konnte nicht enqueued werden.")

	@admin.action(description="Status: Wartet auf Mieter setzen")
	def mark_waiting_tenant(self, request, queryset):
		with transaction.atomic():
			updated = queryset.update(status=models.Issue.Status.WAITING_TENANT)
		messages.info(request, f"{updated} Ticket(s) aktualisiert.")


@admin.register(models.IssueAttachment)
class IssueAttachmentAdmin(admin.ModelAdmin):
	list_display = ("id", "issue", "mime", "size_bytes", "uploader_role", "created_at")
	list_filter = ("uploader_role",)


@admin.register(models.IssueNote)
class IssueNoteAdmin(admin.ModelAdmin):
	list_display = ("id", "issue", "author", "visibility", "created_at")
	list_filter = ("visibility",)
	search_fields = ("text",)


@admin.register(models.Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = ("id", "issue", "vendor", "start", "end", "status")
	list_filter = ("status", "vendor")
	date_hierarchy = "start"


@admin.register(models.VendorAttachment)
class VendorAttachmentAdmin(admin.ModelAdmin):
	list_display = ("id", "issue", "vendor", "category", "size_bytes", "created_at")
	list_filter = ("category", "vendor")
	search_fields = ("issue__ticket_no", "vendor__name", "notes")
	readonly_fields = ("created_at", "updated_at")


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "category", "property", "unit", "tenant", "size_bytes", "created_at")
	list_filter = ("category", "property", "unit")
	search_fields = ("name", "notes", "tags")
	readonly_fields = ("created_at", "updated_at", "size_bytes", "content_type")
	autocomplete_fields = ["property", "unit", "tenant"]
	fieldsets = (
		("Dokument", {
			"fields": ("file", "name", "category")
		}),
		("Zuordnung (M11b)", {
			"fields": ("property", "unit", "tenant"),
			"description": "Wähle Property ODER Unit ODER Tenant"
		}),
		("Metadaten", {
			"fields": ("size_bytes", "content_type", "tags", "notes")
		}),
		("Versioning (M17a)", {
			"fields": ("current_version", "supersedes", "valid_from", "valid_to"),
			"classes": ("collapse",)
		}),
		("System", {
			"fields": ("uploaded_by", "created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)


@admin.register(models.Contract)
class ContractAdmin(admin.ModelAdmin):
	list_display = ("id", "unit", "tenant", "start_date", "end_date", "rent_amount", "status", "created_at")
	list_filter = ("status", "start_date", "created_at")
	search_fields = ("unit__unit_label", "tenant__primary_email", "notes")
	readonly_fields = ("created_at", "updated_at", "total_rent", "is_active", "is_unlimited")
	autocomplete_fields = ["unit", "tenant", "document"]
	date_hierarchy = "start_date"
	fieldsets = (
		("Vertragsparteien (M12a)", {
			"fields": ("unit", "tenant", "document")
		}),
		("Vertragslaufzeit", {
			"fields": ("start_date", "end_date", "notice_date", "status")
		}),
		("Finanzielle Konditionen", {
			"fields": ("rent_amount", "additional_costs", "deposit_amount", "payment_day")
		}),
		("Nebenkostenabrechnung (M14)", {
			"fields": ("allocation_key", "occupants_count"),
			"description": "Umlage-Schlüssel für Nebenkosten-Verteilung"
		}),
		("Berechnete Felder (readonly)", {
			"fields": ("total_rent", "is_active", "is_unlimited"),
			"classes": ("collapse",)
		}),
		("Notizen", {
			"fields": ("notes",)
		}),
		("System", {
			"fields": ("created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)

	def total_rent(self, obj):
		"""Display Warmmiete in admin"""
		return f"€{obj.total_rent:.2f}"
	total_rent.short_description = "Warmmiete (Kalt + NK)"


@admin.register(models.DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
	list_display = ("id", "document", "version_number", "size_bytes", "uploaded_by", "created_at")
	list_filter = ("created_at", "uploaded_by")
	search_fields = ("document__name", "upload_comment")
	readonly_fields = ("created_at", "updated_at", "size_bytes", "content_type")
	autocomplete_fields = ["document"]
	fieldsets = (
		("Version Info", {
			"fields": ("document", "version_number", "file")
		}),
		("Metadata", {
			"fields": ("size_bytes", "content_type", "upload_comment")
		}),
		("System", {
			"fields": ("uploaded_by", "created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)


@admin.register(models.PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
	list_display = ("id", "contract", "amount", "transaction_date", "payment_type", "status", "created_at")
	list_filter = ("payment_type", "status", "transaction_date", "created_at")
	search_fields = ("reference", "sender_name", "sender_iban", "notes", "contract__unit__unit_label", "contract__tenant__primary_email")
	readonly_fields = ("created_at", "updated_at", "csv_import_date", "is_overdue")
	autocomplete_fields = ["contract"]
	date_hierarchy = "transaction_date"
	fieldsets = (
		("Zahlung (M12b)", {
			"fields": ("contract", "amount", "transaction_date", "due_date")
		}),
		("Typ & Status", {
			"fields": ("payment_type", "status")
		}),
		("Bank-Details", {
			"fields": ("reference", "sender_name", "sender_iban")
		}),
		("CSV-Import", {
			"fields": ("csv_import_date", "csv_row_data"),
			"classes": ("collapse",)
		}),
		("Notizen", {
			"fields": ("notes",)
		}),
		("System", {
			"fields": ("created_at", "updated_at", "is_overdue"),
			"classes": ("collapse",)
		}),
	)

	def is_overdue(self, obj):
		"""Display if payment is overdue"""
		return "✗ Überfällig" if obj.is_overdue else "✓ OK"
	is_overdue.short_description = "Überfällig?"


# ============================================================================
# M14: NEBENKOSTENABRECHNUNG (UTILITY BILLING)
# ============================================================================

@admin.register(models.UtilityMeter)
class UtilityMeterAdmin(admin.ModelAdmin):
	"""
	Admin für Zähler-Stammdaten (M17: Default Meter Prefill)
	"""
	list_display = (
		"id",
		"scope_type",
		"get_scope_display",
		"meter_type",
		"serial_number",
		"is_default",
		"is_active",
		"installed_at",
	)
	list_filter = (
		"scope_type",
		"meter_type",
		"is_default",
		"is_active",
	)
	search_fields = (
		"serial_number",
		"property__name",
		"property__street",
		"unit__unit_label",
	)
	fieldsets = (
		("Zuordnung", {
			'fields': ('scope_type', 'property', 'unit'),
		}),
		("Zähler-Details", {
			'fields': ('meter_type', 'serial_number', 'is_default', 'is_active'),
		}),
		("Startwert & Zeiträume", {
			'fields': ('initial_reading_value', 'installed_at', 'removed_at'),
			'description': 'Startwert wird einmalig als "vorheriger Zählerstand" beim ersten Reading verwendet.'
		}),
		("Notizen", {
			'fields': ('notes',),
			'classes': ('collapse',),
		}),
	)

	def get_scope_display(self, obj):
		"""Display the actual Property or Unit"""
		return str(obj.get_scope_object())
	get_scope_display.short_description = "Objekt/Wohnung"

	def get_queryset(self, request):
		"""Optimize with select_related"""
		qs = super().get_queryset(request)
		return qs.select_related('property', 'unit')


@admin.register(models.UtilityReading)
class UtilityReadingAdmin(admin.ModelAdmin):
	"""Admin für Zählerstände (M14)"""
	list_display = (
		"id",
		"reading_date",
		"unit",
		"meter_type",
		"current_value",
		"previous_value",
		"consumption",
		"recorded_by"
	)
	list_filter = (
		"meter_type",
		"reading_date",
		"unit__property"
	)
	search_fields = (
		"unit__unit_label",
		"meter_number",
		"notes"
	)
	autocomplete_fields = ["unit", "recorded_by"]
	date_hierarchy = "reading_date"
	readonly_fields = ("consumption", "created_at", "updated_at")

	fieldsets = (
		("Zählerstand (M14)", {
			"fields": ("unit", "meter_type", "reading_date", "meter_number")
		}),
		("Werte", {
			"fields": ("current_value", "previous_value", "consumption")
		}),
		("Notizen", {
			"fields": ("notes", "recorded_by")
		}),
		("System", {
			"fields": ("created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)

	def save_model(self, request, obj, form, change):
		"""Auto-set recorded_by to current user"""
		if not obj.recorded_by:
			obj.recorded_by = request.user
		super().save_model(request, obj, form, change)


# ============================================================================
# M16: CHECKLISTEN (HANDOVER PROTOCOLS)
# ============================================================================

@admin.register(models.ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
	"""Admin für Checklisten-Vorlagen (M16)"""
	list_display = (
		"id",
		"name",
		"template_type",
		"is_active",
		"item_count",
		"created_at"
	)
	list_filter = ("template_type", "is_active")
	search_fields = ("name", "description")
	readonly_fields = ("created_at", "updated_at")

	fieldsets = (
		("Vorlage (M16)", {
			"fields": ("name", "template_type", "description", "is_active")
		}),
		("Standard-Prüfpunkte (JSON)", {
			"fields": ("default_items",),
			"description": 'Format: [{"name": "Fenster", "category": "Wohnzimmer", "order": 1}]'
		}),
		("System", {
			"fields": ("created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)

	def item_count(self, obj):
		"""Display number of default items"""
		return len(obj.default_items) if obj.default_items else 0
	item_count.short_description = "Anzahl Prüfpunkte"


class ChecklistItemInline(admin.TabularInline):
	"""Inline for Checklist Items"""
	model = models.ChecklistItem
	extra = 0
	fields = ("category", "name", "order", "is_checked", "condition", "notes")
	ordering = ("order", "category", "name")


@admin.register(models.Checklist)
class ChecklistAdmin(admin.ModelAdmin):
	"""Admin für Checklisten (M16)"""
	list_display = (
		"id",
		"title",
		"unit",
		"tenant",
		"checklist_type",
		"checklist_date",
		"status",
		"completion_display",
		"conducted_by"
	)
	list_filter = (
		"checklist_type",
		"status",
		"checklist_date",
		"unit__property"
	)
	search_fields = (
		"title",
		"unit__unit_label",
		"tenant__primary_email",
		"general_notes"
	)
	autocomplete_fields = ["template", "unit", "tenant", "conducted_by"]
	date_hierarchy = "checklist_date"
	readonly_fields = ("completed_at", "created_at", "updated_at", "completion_percentage")
	inlines = [ChecklistItemInline]

	fieldsets = (
		("Checkliste (M16)", {
			"fields": ("template", "title", "checklist_type", "checklist_date")
		}),
		("Zuordnung", {
			"fields": ("unit", "tenant", "conducted_by")
		}),
		("Status", {
			"fields": ("status", "completion_percentage", "completed_at")
		}),
		("Notizen", {
			"fields": ("general_notes",)
		}),
		("System", {
			"fields": ("created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)

	def completion_display(self, obj):
		"""Display completion percentage"""
		percentage = obj.completion_percentage
		if percentage == 100:
			return f"✓ {percentage:.0f}%"
		elif percentage > 0:
			return f"⋯ {percentage:.0f}%"
		else:
			return f"○ {percentage:.0f}%"
	completion_display.short_description = "Fortschritt"


@admin.register(models.ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
	"""Admin für einzelne Checklist-Items (M16)"""
	list_display = (
		"id",
		"checklist",
		"category",
		"name",
		"is_checked",
		"condition",
		"has_photo"
	)
	list_filter = (
		"is_checked",
		"condition",
		"category",
		"checklist__checklist_type"
	)
	search_fields = (
		"name",
		"category",
		"notes",
		"checklist__title"
	)
	autocomplete_fields = ["checklist"]
	readonly_fields = ("created_at", "updated_at")

	fieldsets = (
		("Prüfpunkt (M16)", {
			"fields": ("checklist", "category", "name", "order")
		}),
		("Prüfung", {
			"fields": ("is_checked", "condition", "notes", "photo")
		}),
		("System", {
			"fields": ("created_at", "updated_at"),
			"classes": ("collapse",)
		}),
	)

	def has_photo(self, obj):
		"""Display if item has photo"""
		return "📷 Ja" if obj.photo else "○ Nein"
	has_photo.short_description = "Foto"


# ============================================================================
# M15: WARTUNGSKALENDER ADMIN
# ============================================================================

@admin.register(models.MaintenanceItem)
class MaintenanceItemAdmin(admin.ModelAdmin):
	"""Admin für Wartungsaufgaben (M15)"""

	list_display = [
		'title',
		'category',
		'due_date',
		'status',
		'location',
		'assigned_to',
		'estimated_cost',
		'is_overdue_display',
	]
	list_filter = [
		'status',
		'category',
		'due_date',
		'property',
	]
	search_fields = [
		'title',
		'description',
		'property__name',
		'unit__unit_label',
	]
	readonly_fields = [
		'created_at',
		'updated_at',
		'completed_at',
		'completed_by',
	]
	autocomplete_fields = [
		'property',
		'unit',
		'assigned_to',
	]

	fieldsets = (
		('Basis-Info', {
			'fields': (
				'title',
				'description',
				'category',
			)
		}),
		('Zuordnung', {
			'fields': (
				'property',
				'unit',
				'assigned_to',
			)
		}),
		('Termine & Status', {
			'fields': (
				'due_date',
				'status',
				'completed_at',
				'completed_by',
			)
		}),
		('Kosten', {
			'fields': (
				'estimated_cost',
				'actual_cost',
			)
		}),
		('Notizen', {
			'fields': ('notes',),
			'classes': ('collapse',),
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',),
		}),
	)

	def location(self, obj):
		"""Display location"""
		if obj.property:
			return f"🏠 {obj.property}"
		elif obj.unit:
			return f"🚪 {obj.unit}"
		return "—"
	location.short_description = "Ort"

	def is_overdue_display(self, obj):
		"""Display if overdue"""
		from datetime import date
		if obj.status == models.MaintenanceItem.Status.PENDING and obj.due_date < date.today():
			return "⚠️ Überfällig"
		return "—"
	is_overdue_display.short_description = "Status"
