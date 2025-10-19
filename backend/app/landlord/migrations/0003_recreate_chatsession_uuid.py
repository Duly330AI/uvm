import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landlord", "0002_alter_issue_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="ChatSession"),
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "state",
                    models.CharField(
                        max_length=40,
                        default="GREETING",
                        choices=[
                            ("GREETING", "GREETING"),
                            ("CAPTURE_SUMMARY", "CAPTURE_SUMMARY"),
                            ("CAPTURE_OCCURRED_AT", "CAPTURE_OCCURRED_AT"),
                            ("CAPTURE_LOCATION", "CAPTURE_LOCATION"),
                            ("CAPTURE_SEVERITY", "CAPTURE_SEVERITY"),
                            ("CAPTURE_MEDIA", "CAPTURE_MEDIA"),
                            ("CAPTURE_CONTACT", "CAPTURE_CONTACT"),
                            ("CONFIRM", "CONFIRM"),
                            ("CREATE_ISSUE", "CREATE_ISSUE"),
                            ("DONE", "DONE"),
                        ],
                    ),
                ),
                ("payload", models.JSONField(default=dict, blank=True)),
                ("transcript", models.JSONField(default=list, blank=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=0)),
                (
                    "tenant",
                    models.ForeignKey(
                        to="landlord.tenant",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="chat_sessions",
                    ),
                ),
                (
                    "unit",
                    models.ForeignKey(
                        to="landlord.unit",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="chat_sessions",
                    ),
                ),
                (
                    "issue",
                    models.OneToOneField(
                        to="landlord.issue",
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="chat_session",
                    ),
                ),
            ],
        ),
    ]
