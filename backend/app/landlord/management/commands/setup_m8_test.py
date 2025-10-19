"""
Quick setup script for M8 testing
Creates a test tenant with email duly330@outlook.de
"""
from django.core.management.base import BaseCommand
from landlord.models import Property, Tenant, Unit


class Command(BaseCommand):
    help = 'Setup test tenant for M8 (Magic-Link Portal)'

    def handle(self, *args, **options):
        # Get or create test property & unit
        prop, _ = Property.objects.get_or_create(
            name="Demo Objekt",
            defaults={
                "street": "Teststraße 1",
                "postal_code": "10115",
                "city": "Berlin",
            }
        )

        unit, _ = Unit.objects.get_or_create(
            property=prop,
            unit_label="Wohnung A",
            defaults={
                "floor": "2.OG",
                "rooms": 3,
            }
        )

        # Create test tenant with your email
        tenant, created = Tenant.objects.update_or_create(
            primary_email="duly330@outlook.de",
            defaults={
                "unit": unit,
                "is_active": True,
                "phone": "+49 30 12345678",
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Tenant erstellt: {tenant.primary_email}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'🔄 Tenant aktualisiert: {tenant.primary_email}'))

        self.stdout.write(f'   Unit: {unit.unit_label} @ {prop.name}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('M8 Test-Setup komplett!'))
        self.stdout.write('Login: http://localhost:8000/tenant/')
        self.stdout.write(f'Email: {tenant.primary_email}')
