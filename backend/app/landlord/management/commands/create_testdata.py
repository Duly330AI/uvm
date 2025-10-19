"""
Django Management Command: Create Test Data
Generates complete test dataset for UVM system
"""
from decimal import Decimal
from datetime import date, timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from landlord.models import (
    Property, Unit, Tenant, Contract, 
    Issue, Vendor, PaymentTransaction,
    Document, MaintenanceItem
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Create comprehensive test data for UVM system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Creating test data...'))
        
        # 1. Properties
        properties = self.create_properties()
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(properties)} properties'))
        
        # 2. Units
        units = self.create_units(properties)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(units)} units'))
        
        # 3. Tenants
        tenants = self.create_tenants(units)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(tenants)} tenants'))
        
        # 4. Contracts
        contracts = self.create_contracts(units, tenants)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(contracts)} contracts'))
        
        # 5. Vendors
        vendors = self.create_vendors()
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(vendors)} vendors'))
        
        # 6. Issues/Tickets
        issues = self.create_issues(units, tenants)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(issues)} issues/tickets'))
        
        # 7. Maintenance Tasks
        tasks = self.create_maintenance_tasks(units, vendors)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(tasks)} maintenance tasks'))
        
        # 8. Payments
        payments = self.create_payments(contracts)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(payments)} payments'))
        
        # 9. Documents
        documents = self.create_documents(properties, units, tenants)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(documents)} documents'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 All test data created successfully!'))
        self.print_summary(properties, units, tenants, contracts, vendors, issues)

    def create_properties(self):
        """Create 2 properties"""
        properties = [
            Property.objects.create(
                name="Residenz am Park",
                street="Parkstraße 15",
                postal_code="10115",
                city="Berlin",
                country="DE"
            ),
            Property.objects.create(
                name="Stadtvillen München",
                street="Maximilianstraße 42",
                postal_code="80539",
                city="München",
                country="DE"
            )
        ]
        return properties

    def create_units(self, properties):
        """Create 8 units (4 per property)"""
        units = []
        
        # Property 1 - Residenz am Park
        for i in range(1, 5):
            unit = Unit.objects.create(
                property=properties[0],
                unit_label=f"{i}.OG / Whg {i}",
                floor=str(i),
                rooms=2 + (i % 2),  # 2-3 rooms
                area_sqm=Decimal(str(55 + i * 5)),  # 60-75 sqm
                description=f"Moderne {2 + (i % 2)}-Zimmer-Wohnung mit Balkon"
            )
            units.append(unit)
        
        # Property 2 - Stadtvillen München
        for i in range(1, 5):
            unit = Unit.objects.create(
                property=properties[1],
                unit_label=f"EG-{i}" if i <= 2 else f"OG-{i-2}",
                floor="EG" if i <= 2 else "1",
                rooms=3 + (i % 2),  # 3-4 rooms
                area_sqm=Decimal(str(75 + i * 10)),  # 85-115 sqm
                description=f"Exklusive {3 + (i % 2)}-Zimmer-Wohnung mit Garten" if i <= 2 else f"Penthouse-Wohnung"
            )
            units.append(unit)
        
        return units

    def create_tenants(self, units):
        """Create 8 tenants (1 per unit)"""
        tenant_data = [
            ("Max", "Mustermann", "max.mustermann@email.de", "+49 30 12345678"),
            ("Anna", "Schmidt", "anna.schmidt@email.de", "+49 30 23456789"),
            ("Thomas", "Müller", "thomas.mueller@email.de", "+49 30 34567890"),
            ("Julia", "Weber", "julia.weber@email.de", "+49 30 45678901"),
            ("Michael", "Wagner", "michael.wagner@email.de", "+49 89 12345678"),
            ("Sarah", "Becker", "sarah.becker@email.de", "+49 89 23456789"),
            ("Daniel", "Schulz", "daniel.schulz@email.de", "+49 89 34567890"),
            ("Laura", "Koch", "laura.koch@email.de", "+49 89 45678901"),
        ]
        
        tenants = []
        for i, unit in enumerate(units):
            first_name, last_name, email, phone = tenant_data[i]
            tenant = Tenant.objects.create(
                unit=unit,
                first_name=first_name,
                last_name=last_name,
                primary_email=email,
                phone=phone,
                is_active=True
            )
            tenants.append(tenant)
        
        return tenants

    def create_contracts(self, units, tenants):
        """Create contracts for all tenants"""
        contracts = []
        base_date = date.today() - timedelta(days=365)
        
        for i, (unit, tenant) in enumerate(zip(units, tenants)):
            start_date = base_date + timedelta(days=i * 30)
            contract = Contract.objects.create(
                unit=unit,
                tenant=tenant,
                start_date=start_date,
                end_date=start_date + timedelta(days=730),  # 2 years
                rent_amount=Decimal(str(800 + i * 100)),
                deposit_amount=Decimal(str(2400 + i * 300)),
                status=Contract.Status.ACTIVE
            )
            contracts.append(contract)
        
        return contracts

    def create_vendors(self):
        """Create vendors for various services"""
        vendor_data = [
            ("Elektro Blitz GmbH", "Elektrik", "service@elektroblitz.de", "+49 30 11111111"),
            ("Sanitär Meister", "Sanitär", "info@sanitaermeister.de", "+49 30 22222222"),
            ("Heizung & Klima Pro", "Heizung", "kontakt@heizungpro.de", "+49 30 33333333"),
            ("Maler Farbwelt", "Maler", "anfrage@farbwelt.de", "+49 30 44444444"),
            ("Hausmeister Service 24", "Allgemein", "service@hausmeister24.de", "+49 30 55555555"),
            ("Garten & Grün", "Garten", "info@gartengruen.de", "+49 30 66666666"),
        ]
        
        vendors = []
        for name, service_type, email, phone in vendor_data:
            vendor = Vendor.objects.create(
                name=name,
                service_type=service_type,
                email=email,
                phone=phone,
                is_active=True
            )
            vendors.append(vendor)
        
        return vendors

    def create_issues(self, units, tenants):
        """Create 2 random problem tickets"""
        issue_templates = [
            {
                'title': 'Heizung funktioniert nicht',
                'category': 'heizung',
                'severity': 'hoch',
                'description': 'Die Heizung in der Wohnung ist seit gestern ausgefallen. Es wird nicht mehr warm.'
            },
            {
                'title': 'Wasserhahn tropft',
                'category': 'sanitaer',
                'severity': 'mittel',
                'description': 'Der Wasserhahn im Bad tropft ständig. Bitte um zeitnahe Reparatur.'
            },
            {
                'title': 'Fenster lässt sich nicht schließen',
                'category': 'sonstiges',
                'severity': 'mittel',
                'description': 'Das Fenster im Wohnzimmer klemmt und lässt sich nicht mehr richtig schließen.'
            },
            {
                'title': 'Steckdose ohne Strom',
                'category': 'elektrik',
                'severity': 'hoch',
                'description': 'Eine Steckdose in der Küche liefert keinen Strom mehr.'
            },
        ]
        
        issues = []
        for i in range(2):
            template = random.choice(issue_templates)
            unit = random.choice(units)
            tenant = Tenant.objects.filter(unit=unit).first()
            
            issue = Issue.objects.create(
                unit=unit,
                tenant=tenant,
                title=template['title'],
                category=template['category'],
                severity=template['severity'],
                description=template['description'],
                status='offen',
                reported_via='portal'
            )
            issues.append(issue)
        
        return issues

    def create_maintenance_tasks(self, units, vendors):
        """Create some maintenance tasks"""
        tasks = []
        for i in range(3):
            unit = random.choice(units)
            vendor = random.choice(vendors)
            
            task = MaintenanceItem.objects.create(
                unit=unit,
                vendor=vendor,
                title=f"Wartung {vendor.service_type}",
                description=f"Reguläre Wartung für {unit.unit_label}",
                scheduled_date=date.today() + timedelta(days=random.randint(7, 30)),
                status='planned'
            )
            tasks.append(task)
        
        return tasks

    def create_payments(self, contracts):
        """Create payment transactions"""
        payments = []
        for contract in contracts[:4]:  # First 4 contracts
            # Create 2 rent payments per contract
            for month in range(2):
                payment_date = date.today() - timedelta(days=60 - month * 30)
                payment = PaymentTransaction.objects.create(
                    contract=contract,
                    amount=contract.rent_amount,
                    transaction_date=payment_date,
                    payment_type=PaymentTransaction.Type.RENT,
                    status=PaymentTransaction.Status.RECEIVED,
                    reference=f"Miete {payment_date.strftime('%m/%Y')}"
                )
                payments.append(payment)
        
        return payments

    def create_documents(self, properties, units, tenants):
        """Create some document entries (without actual files)"""
        documents = []
        
        # Property documents
        for prop in properties:
            doc = Document.objects.create(
                name=f"Grundriss_{prop.name.replace(' ', '_')}.pdf",
                category="sonstiges",
                property=prop,
                size_bytes=1024000,
                content_type="application/pdf"
            )
            documents.append(doc)
        
        # Unit documents
        for unit in units[:2]:
            doc = Document.objects.create(
                name=f"Übergabeprotokoll_{unit.unit_label.replace(' ', '_')}.pdf",
                category="vertrag",
                unit=unit,
                size_bytes=512000,
                content_type="application/pdf"
            )
            documents.append(doc)
        
        return documents

    def print_summary(self, properties, units, tenants, contracts, vendors, issues):
        """Print summary of created data"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 TEST DATA SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'\n🏢 Properties: {len(properties)}')
        for prop in properties:
            self.stdout.write(f'   - {prop.name} ({prop.city})')
        
        self.stdout.write(f'\n🏠 Units: {len(units)}')
        self.stdout.write(f'   {len([u for u in units if u.property == properties[0]])} in {properties[0].name}')
        self.stdout.write(f'   {len([u for u in units if u.property == properties[1]])} in {properties[1].name}')
        
        self.stdout.write(f'\n👥 Tenants: {len(tenants)}')
        self.stdout.write(f'📄 Active Contracts: {len(contracts)}')
        self.stdout.write(f'🔧 Vendors: {len(vendors)}')
        self.stdout.write(f'🎫 Open Issues: {len([i for i in issues if i.status == "offen"])}')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ Ready to test!'))
        self.stdout.write('='*60 + '\n')
