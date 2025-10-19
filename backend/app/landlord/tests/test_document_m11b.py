"""
M11b Tests: Document Model mit Property/Unit/Tenant ForeignKeys
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from landlord.models import Document, Property, Tenant, Unit

User = get_user_model()


class DocumentModelM11bTest(TestCase):
    """Test Document Model mit neuen ForeignKeys"""

    def setUp(self):
        self.property = Property.objects.create(
            name="Test Objekt A",
            street="Teststraße 1",
            postal_code="12345",
            city="Teststadt"
        )
        self.unit = Unit.objects.create(
            property=self.property,
            unit_label="2.OG / Whg 3",
            floor="2",
            rooms=3,
            area_sqm=75.5
        )
        self.tenant = Tenant.objects.create(
            unit=self.unit,
            primary_email="test@example.com",
            is_active=True
        )

    def test_document_create_with_property(self):
        """Dokument kann Objekt zugeordnet werden"""
        doc = Document.objects.create(
            name="Mietvertrag.pdf",
            category="vertrag",
            property=self.property,
            size_bytes=1024,
            content_type="application/pdf"
        )

        assert doc.property == self.property
        assert doc.unit is None
        assert doc.tenant is None
        assert doc.name == "Mietvertrag.pdf"

    def test_document_create_with_unit(self):
        """Dokument kann Wohnung zugeordnet werden"""
        doc = Document.objects.create(
            name="Übergabeprotokoll.pdf",
            category="übergabe",
            unit=self.unit,
            size_bytes=2048,
            content_type="application/pdf"
        )

        assert doc.unit == self.unit
        assert doc.property is None
        assert doc.tenant is None

    def test_document_create_with_tenant(self):
        """Dokument kann Mieter zugeordnet werden"""
        doc = Document.objects.create(
            name="Personalausweis.pdf",
            category="sonstiges",
            tenant=self.tenant,
            size_bytes=512,
            content_type="application/pdf"
        )

        assert doc.tenant == self.tenant
        assert doc.property is None
        assert doc.unit is None

    def test_document_create_without_assignment(self):
        """Dokument kann auch OHNE Zuordnung erstellt werden"""
        doc = Document.objects.create(
            name="Allgemein.pdf",
            category="sonstiges",
            size_bytes=256,
            content_type="application/pdf"
        )

        assert doc.property is None
        assert doc.unit is None
        assert doc.tenant is None

    def test_document_related_name_property(self):
        """Related name 'documents' funktioniert für Property"""
        doc = Document.objects.create(
            name="Test.pdf",
            property=self.property
        )

        assert doc in self.property.documents.all()
        assert self.property.documents.count() == 1

    def test_document_related_name_unit(self):
        """Related name 'documents' funktioniert für Unit"""
        doc = Document.objects.create(
            name="Test.pdf",
            unit=self.unit
        )

        assert doc in self.unit.documents.all()
        assert self.unit.documents.count() == 1

    def test_document_related_name_tenant(self):
        """Related name 'documents' funktioniert für Tenant"""
        doc = Document.objects.create(
            name="Test.pdf",
            tenant=self.tenant
        )

        assert doc in self.tenant.documents.all()
        assert self.tenant.documents.count() == 1

    def test_document_cascade_delete_property(self):
        """Dokument wird gelöscht wenn Property gelöscht wird"""
        doc = Document.objects.create(
            name="Test.pdf",
            property=self.property
        )
        doc_id = doc.id

        self.property.delete()

        assert not Document.objects.filter(id=doc_id).exists()

    def test_document_cascade_delete_unit(self):
        """Dokument wird gelöscht wenn Unit gelöscht wird"""
        doc = Document.objects.create(
            name="Test.pdf",
            unit=self.unit
        )
        doc_id = doc.id

        self.unit.delete()

        assert not Document.objects.filter(id=doc_id).exists()


class DocumentUploadViewM11bTest(TestCase):
    """Test Document Upload via Portal mit Property/Unit/Tenant Zuordnung"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staff",
            password="test123",
            is_staff=True
        )
        self.property = Property.objects.create(
            name="Upload Test Objekt",
            street="Uploadstraße 1",
            postal_code="54321",
            city="Uploadstadt"
        )
        self.unit = Unit.objects.create(
            property=self.property,
            unit_label="1.OG / Whg 1",
            floor="1"
        )
        self.tenant = Tenant.objects.create(
            unit=self.unit,
            primary_email="upload@test.com"
        )

    def test_document_upload_with_property(self):
        """Upload mit Property-Zuordnung"""
        self.client.force_login(self.staff_user)

        # Create fake PDF
        pdf_content = b"%PDF-1.4 fake pdf content"
        pdf_file = SimpleUploadedFile(
            "test_property.pdf",
            pdf_content,
            content_type="application/pdf"
        )

        response = self.client.post('/portal/document/upload/', {
            'file': pdf_file,
            'property': self.property.id,
            'category': 'plan',
            'tags': 'grundriss,2025',
            'notes': 'Test-Upload für Property'
        })

        assert response.status_code == 302  # Redirect nach Upload
        assert response.url == '/portal/documents/'

        # Verify Document created
        doc = Document.objects.last()
        assert doc is not None
        assert doc.property == self.property
        assert doc.unit is None
        assert doc.tenant is None
        assert doc.category == 'plan'
        assert doc.tags == 'grundriss,2025'
        assert doc.uploaded_by == self.staff_user

    def test_document_upload_with_unit(self):
        """Upload mit Unit-Zuordnung"""
        self.client.force_login(self.staff_user)

        pdf_file = SimpleUploadedFile(
            "test_unit.pdf",
            b"%PDF-1.4 fake",
            content_type="application/pdf"
        )

        response = self.client.post('/portal/document/upload/', {
            'file': pdf_file,
            'unit': self.unit.id,
            'category': 'vertrag',
            'notes': 'Mietvertrag 2025'
        })

        assert response.status_code == 302

        doc = Document.objects.last()
        assert doc.unit == self.unit
        assert doc.property is None
        assert doc.tenant is None
        assert doc.category == 'vertrag'

    def test_document_upload_with_tenant(self):
        """Upload mit Tenant-Zuordnung"""
        self.client.force_login(self.staff_user)

        pdf_file = SimpleUploadedFile(
            "test_tenant.pdf",
            b"%PDF-1.4 fake",
            content_type="application/pdf"
        )

        response = self.client.post('/portal/document/upload/', {
            'file': pdf_file,
            'tenant': self.tenant.id,
            'category': 'sonstiges'
        })

        assert response.status_code == 302

        doc = Document.objects.last()
        assert doc.tenant == self.tenant
        assert doc.property is None
        assert doc.unit is None

    def test_document_upload_without_assignment(self):
        """Upload OHNE Zuordnung (alle FKs leer)"""
        self.client.force_login(self.staff_user)

        pdf_file = SimpleUploadedFile(
            "test_no_assignment.pdf",
            b"%PDF-1.4 fake",
            content_type="application/pdf"
        )

        response = self.client.post('/portal/document/upload/', {
            'file': pdf_file,
            'category': 'foto'
        })

        assert response.status_code == 302

        doc = Document.objects.last()
        assert doc.property is None
        assert doc.unit is None
        assert doc.tenant is None


class DocumentListViewM11bTest(TestCase):
    """Test Document List zeigt Property/Unit/Tenant korrekt"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staff",
            password="test123",
            is_staff=True
        )
        self.property = Property.objects.create(
            name="List Test Objekt",
            street="Liststraße 1",
            postal_code="11111",
            city="Liststadt"
        )
        self.unit = Unit.objects.create(
            property=self.property,
            unit_label="3.OG / Whg 5"
        )
        self.tenant = Tenant.objects.create(
            unit=self.unit,
            primary_email="list@test.com"
        )

    def test_list_shows_property_assignment(self):
        """Liste zeigt Property-Zuordnung"""
        Document.objects.create(
            name="Property Doc.pdf",
            property=self.property,
            category="plan"
        )

        self.client.force_login(self.staff_user)
        response = self.client.get('/portal/documents/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "List Test Objekt" in content
        assert "🏢" in content  # Property Icon

    def test_list_shows_unit_assignment(self):
        """Liste zeigt Unit-Zuordnung"""
        Document.objects.create(
            name="Unit Doc.pdf",
            unit=self.unit,
            category="vertrag"
        )

        self.client.force_login(self.staff_user)
        response = self.client.get('/portal/documents/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "3.OG / Whg 5" in content
        assert "List Test Objekt" in content  # Unit zeigt auch Property
        assert "🚪" in content  # Unit Icon

    def test_list_shows_tenant_assignment(self):
        """Liste zeigt Tenant-Zuordnung"""
        Document.objects.create(
            name="Tenant Doc.pdf",
            tenant=self.tenant,
            category="sonstiges"
        )

        self.client.force_login(self.staff_user)
        response = self.client.get('/portal/documents/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "list@test.com" in content
        assert "👤" in content  # Tenant Icon

    def test_list_shows_no_assignment(self):
        """Liste zeigt 'Keine Zuordnung' wenn alle FKs leer"""
        Document.objects.create(
            name="Unassigned Doc.pdf",
            category="foto"
        )

        self.client.force_login(self.staff_user)
        response = self.client.get('/portal/documents/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Keine Zuordnung" in content or "kein" in content.lower()

    def test_list_loads_dropdowns_for_upload_modal(self):
        """Liste lädt Properties/Units/Tenants für Upload-Modal"""
        self.client.force_login(self.staff_user)
        response = self.client.get('/portal/documents/')

        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Check Dropdowns exist
        assert 'name="property"' in content
        assert 'name="unit"' in content
        assert 'name="tenant"' in content

        # Check our test data is in dropdowns
        assert "List Test Objekt" in content
        assert "3.OG / Whg 5" in content
        assert "list@test.com" in content
