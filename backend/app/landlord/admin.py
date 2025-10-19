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


@admin.register(models.Property)
class PropertyAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "street", "postal_code", "city", "created_at")
	search_fields = ("name", "street", "postal_code", "city")
	list_filter = ("city",)


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
	list_display = ("id", "property", "unit_label", "is_active", "created_at")
	search_fields = ("unit_label", "property__street", "property__city")
	list_filter = ("is_active", "property")


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

