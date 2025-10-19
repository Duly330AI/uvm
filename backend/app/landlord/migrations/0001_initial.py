import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Property",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(blank=True, max_length=200)),
                ("street", models.CharField(max_length=200)),
                ("postal_code", models.CharField(max_length=20)),
                ("city", models.CharField(max_length=100)),
                ("country", models.CharField(default="Deutschland", max_length=100)),
                ("geo_lat", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("geo_lng", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("notes", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="Vendor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("trade", models.CharField(blank=True, max_length=100)),
                ("address_text", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="Unit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("unit_label", models.CharField(max_length=100)),
                ("floor", models.CharField(blank=True, max_length=50)),
                ("rooms", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("area_sqm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("property", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="units", to="landlord.property")),
            ],
        ),
        migrations.AddIndex(
            model_name="unit",
            index=models.Index(fields=["property", "unit_label"], name="landlord_un_propert_aeb15a_idx"),
        ),
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("primary_email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("moved_in_at", models.DateField(blank=True, null=True)),
                ("moved_out_at", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tenants", to="landlord.unit")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Issue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.CharField(choices=[("water", "Water"), ("heating", "Heating"), ("electricity", "Electricity"), ("structural", "Structural"), ("other", "Other")], default="other", max_length=20)),
                ("severity", models.PositiveSmallIntegerField(default=3)),
                ("status", models.CharField(choices=[("NEW", "New"), ("IN_PROGRESS", "In progress"), ("WAITING_TENANT", "Waiting tenant"), ("WAITING_VENDOR", "Waiting vendor"), ("SCHEDULED", "Scheduled"), ("RESOLVED", "Resolved"), ("CANCELLED", "Cancelled")], default="NEW", max_length=20)),
                ("summary", models.CharField(max_length=255)),
                ("description_raw", models.TextField(blank=True)),
                ("description_struct", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(blank=True, null=True)),
                ("location_hint", models.CharField(blank=True, max_length=200)),
                ("contact_times", models.CharField(blank=True, max_length=200)),
                ("sla_due_at", models.DateTimeField(blank=True, null=True)),
                ("created_via", models.CharField(default="chat", max_length=20)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="issues", to="landlord.tenant")),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="issues", to="landlord.unit")),
            ],
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["status", "created_at"], name="landlord_is_status_e16df2_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["unit"], name="landlord_is_unit_id_f9b5bb_idx"),
        ),
        migrations.CreateModel(
            name="IssueAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file", models.FileField(upload_to="issues/%Y/%m/%d/")),
                ("mime", models.CharField(blank=True, max_length=100)),
                ("size_bytes", models.PositiveIntegerField(blank=True, null=True)),
                ("uploader_role", models.CharField(choices=[("tenant", "Tenant"), ("staff", "Staff")], default="tenant", max_length=10)),
                ("issue", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="landlord.issue")),
            ],
        ),
        migrations.CreateModel(
            name="IssueNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("visibility", models.CharField(choices=[("internal", "Internal"), ("public", "Public")], default="internal", max_length=10)),
                ("text", models.TextField()),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("issue", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="landlord.issue")),
            ],
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                ("status", models.CharField(choices=[("invited", "Invited"), ("confirmed", "Confirmed"), ("done", "Done"), ("cancelled", "Cancelled")], default="invited", max_length=10)),
                ("notes", models.TextField(blank=True)),
                ("issue", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="appointments", to="landlord.issue")),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="landlord.vendor")),
            ],
        ),
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("state", models.CharField(choices=[
                    ("GREETING", "GREETING"),
                    ("CAPTURE_SUMMARY", "CAPTURE_SUMMARY"),
                    ("CAPTURE_OCCURRED_AT", "CAPTURE_OCCURRED_AT"),
                    ("CAPTURE_LOCATION", "CAPTURE_LOCATION"),
                    ("CAPTURE_SEVERITY", "CAPTURE_SEVERITY"),
                    ("CAPTURE_MEDIA", "CAPTURE_MEDIA"),
                    ("CAPTURE_CONTACT", "CAPTURE_CONTACT"),
                    ("CONFIRM", "CONFIRM"),
                    ("CREATE_ISSUE", "CREATE_ISSUE"),
                    ("DONE", "DONE")
                ], default="GREETING", max_length=40)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("transcript", models.JSONField(blank=True, default=list)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_sessions", to="landlord.tenant")),
                ("unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_sessions", to="landlord.unit")),
            ],
        ),
    ]
