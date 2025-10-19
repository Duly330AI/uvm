import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("landlord", "0003_recreate_chatsession_uuid"),
    ]

    operations = [
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.UUIDField()),
                ("scope", models.CharField(max_length=50)),
                ("issue", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="landlord.issue")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="idempotency_keys", to="landlord.chatsession")),
            ],
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.UniqueConstraint(fields=("key", "scope"), name="uq_idempotency_key_scope"),
        ),
    ]
