from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("landlord", "0006_merge_conflict_fix"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE landlord_issue ADD COLUMN IF NOT EXISTS ticket_no varchar(32);"
                "CREATE UNIQUE INDEX IF NOT EXISTS landlord_issue_ticket_no_uniq ON landlord_issue(ticket_no);"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS landlord_issue_ticket_no_uniq;"
                "ALTER TABLE landlord_issue DROP COLUMN IF EXISTS ticket_no;"
            ),
        )
    ]
