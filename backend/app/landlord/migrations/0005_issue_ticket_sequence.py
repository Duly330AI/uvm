from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("landlord", "0004_idempotency_key"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS issue_ticket_seq;",
            reverse_sql="DROP SEQUENCE IF EXISTS issue_ticket_seq;",
        )
    ]
