"""
Management Command: Create "Allgemein" units for building-level utility readings

Usage:
    python manage.py create_building_units
"""
from django.core.management.base import BaseCommand
from landlord.models import Property, Unit


class Command(BaseCommand):
    help = 'Create "Allgemein" units for each property for building-level utility readings'

    def handle(self, *args, **options):
        """
        Create an "Allgemein" unit for each property if it doesn't exist.
        This unit is used for building-level utility readings (common areas, garden water, etc.)
        """
        properties = Property.objects.all()
        created_count = 0
        existing_count = 0

        for property_obj in properties:
            # Check if "Allgemein" or "Gebäude" unit already exists
            existing = Unit.objects.filter(
                property=property_obj,
                unit_label__in=['Allgemein', 'Gebäude']
            ).first()

            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f'✓ {property_obj.name}: "Allgemein" unit already exists'
                    )
                )
                existing_count += 1
                continue

            # Create "Allgemein" unit
            unit = Unit.objects.create(
                property=property_obj,
                unit_label='Allgemein',
                floor='EG',
                area_sqm=0,  # No area for building meters
                rooms=0,
                is_active=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created "Allgemein" unit for {property_obj.name}'
                )
            )
            created_count += 1

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:\n'
                f'  Created: {created_count} new building units\n'
                f'  Existing: {existing_count} building units\n'
                f'  Total properties: {properties.count()}'
            )
        )
        self.stdout.write('='*60 + '\n')

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✓ You can now create building-level utility readings for:\n'
                    '  - Allgemeinstrom (common area electricity)\n'
                    '  - Gartenwasser (garden water)\n'
                    '  - Heizung Gesamt (total heating)\n'
                    '  - etc.\n'
                )
            )
