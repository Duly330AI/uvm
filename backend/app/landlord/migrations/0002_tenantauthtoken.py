# Generated migration for TenantAuthToken
# Run: python manage.py makemigrations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('landlord', '0001_initial'),  # Adjust to your latest migration
    ]

    operations = [
        migrations.CreateModel(
            name='TenantAuthToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('purpose', models.CharField(choices=[('login', 'Login')], default='login', max_length=20)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('ip_hash', models.CharField(blank=True, max_length=64)),
                ('ua_hash', models.CharField(blank=True, max_length=64)),
                ('tenant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='auth_tokens', to='landlord.tenant')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['tenant', 'purpose', 'expires_at'], name='tenant_auth_idx'),
                    models.Index(fields=['email', 'expires_at'], name='email_expires_idx'),
                ],
            },
        ),
    ]
