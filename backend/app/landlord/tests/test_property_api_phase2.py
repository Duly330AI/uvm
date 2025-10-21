"""
Property API Tests - Phase 2
Tests for all Property API endpoints with RBAC, throttling, pagination, etc.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from landlord.models import Property
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user(db):
    """Create regular authenticated user"""
    return User.objects.create_user(
        username='user',
        email='user@test.com',
        password='testpass123'
    )


@pytest.fixture
def sample_properties(db):
    """Create sample properties for testing"""
    props = []
    props.append(Property.objects.create(
        name="Berlin Office",
        street="Hauptstraße 123",
        postal_code="10115",
        city="Berlin",
        country="DE"
    ))
    props.append(Property.objects.create(
        name="Munich Apartment",
        street="Bahnhofstraße 456",
        postal_code="80331",
        city="München",
        country="DE"
    ))
    props.append(Property.objects.create(
        name="Vienna House",
        street="Ringstraße 789",
        postal_code="1010",
        city="Wien",
        country="AT"
    ))
    return props


@pytest.mark.django_db
class TestPropertyListAPI:
    """Tests for GET /api/portal/properties/"""

    def test_list_requires_authentication(self, api_client):
        """Test that unauthenticated requests are rejected"""
        url = reverse('portal-properties-list')
        response = api_client.get(url)
        # DRF returns 403 for unauthenticated with IsAuthenticated permission
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_list_returns_200_authenticated(self, api_client, regular_user):
        """Test that authenticated users can list properties"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_pagination_default_25(self, api_client, regular_user, db):
        """Test default pagination is 25 items per page"""
        # Create 30 properties
        for i in range(30):
            Property.objects.create(
                name=f"Property {i}",
                street=f"Street {i}",
                postal_code=f"{10000 + i}",
                city="Berlin"
            )

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) == 25
        assert response.data['count'] == 30

    def test_list_pagination_custom_page_size(self, api_client, regular_user, sample_properties):
        """Test custom page_size parameter"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'page_size': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_list_filter_by_city(self, api_client, regular_user, sample_properties):
        """Test filtering by city"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'city': 'Berlin'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['city'] == 'Berlin'

    def test_list_filter_by_country(self, api_client, regular_user, sample_properties):
        """Test filtering by country"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'country': 'AT'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['country'] == 'AT'

    def test_list_filter_archived_false_default(self, api_client, regular_user, sample_properties, admin_user):
        """Test that archived properties are excluded by default"""
        # Archive one property
        prop = sample_properties[0]
        prop.archive(admin_user)

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2  # 3 - 1 archived

    def test_list_filter_archived_true(self, api_client, regular_user, sample_properties, admin_user):
        """Test filtering to show only archived properties"""
        # Archive one property
        prop = sample_properties[0]
        prop.archive(admin_user)

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'is_archived': 'true'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['is_archived'] is True

    def test_list_search_query_name(self, api_client, regular_user, sample_properties):
        """Test search query in name field"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'query': 'Berlin'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert 'Berlin' in response.data['results'][0]['name']

    def test_list_search_query_city(self, api_client, regular_user, sample_properties):
        """Test search query in city field"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'query': 'München'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['city'] == 'München'

    def test_list_sort_by_city_asc(self, api_client, regular_user, sample_properties):
        """Test sorting by city ascending"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'sort': 'city', 'order': 'asc'})

        assert response.status_code == status.HTTP_200_OK
        cities = [p['city'] for p in response.data['results']]
        assert cities == sorted(cities)

    def test_list_sort_by_city_desc(self, api_client, regular_user, sample_properties):
        """Test sorting by city descending"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url, {'sort': 'city', 'order': 'desc'})

        assert response.status_code == status.HTTP_200_OK
        cities = [p['city'] for p in response.data['results']]
        assert cities == sorted(cities, reverse=True)

    def test_list_includes_meters_count(self, api_client, regular_user, sample_properties):
        """Test that meters_count is included in response"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'meters_count' in response.data['results'][0]


@pytest.mark.django_db
class TestPropertyDetailAPI:
    """Tests for GET /api/portal/properties/{id}/"""

    def test_detail_requires_authentication(self, api_client, sample_properties):
        """Test that unauthenticated requests are rejected"""
        url = reverse('portal-properties-detail', kwargs={'pk': sample_properties[0].pk})
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_detail_returns_200_authenticated(self, api_client, regular_user, sample_properties):
        """Test that authenticated users can view property details"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-detail', kwargs={'pk': sample_properties[0].pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == sample_properties[0].pk
        assert response.data['name'] == sample_properties[0].name

    def test_detail_includes_all_fields(self, api_client, regular_user, sample_properties):
        """Test that all fields are included"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-detail', kwargs={'pk': sample_properties[0].pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        expected_fields = [
            'id', 'name', 'street', 'postal_code', 'city', 'country',
            'country_display', 'geo_lat', 'geo_lng', 'notes',
            'is_archived', 'archived_at', 'archived_by', 'archived_by_email',
            'meters', 'created_at', 'updated_at'
        ]
        for field in expected_fields:
            assert field in response.data

    def test_detail_includes_meters(self, api_client, regular_user, sample_properties):
        """Test that meters are included in detail view"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-detail', kwargs={'pk': sample_properties[0].pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'meters' in response.data
        assert isinstance(response.data['meters'], list)

    def test_detail_not_found(self, api_client, regular_user):
        """Test 404 for non-existent property"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-detail', kwargs={'pk': 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPropertyCreateAPI:
    """Tests for POST /api/portal/properties/create/"""

    def test_create_requires_authentication(self, api_client):
        """Test that unauthenticated requests are rejected"""
        url = reverse('portal-properties-create')
        data = {
            'street': 'New Street 1',
            'postal_code': '12345',
            'city': 'Berlin'
        }
        response = api_client.post(url, data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_requires_admin(self, api_client, regular_user):
        """Test that regular users cannot create properties"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-create')
        data = {
            'street': 'New Street 1',
            'postal_code': '12345',
            'city': 'Berlin'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_success_admin(self, api_client, admin_user):
        """Test that admins can create properties"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-create')
        data = {
            'name': 'New Property',
            'street': 'New Street 1',
            'postal_code': '12345',
            'city': 'Berlin',
            'country': 'DE'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Property'
        assert response.data['city'] == 'Berlin'

        # Verify in database
        assert Property.objects.filter(name='New Property').exists()

    def test_create_with_geo_coordinates(self, api_client, admin_user):
        """Test creating property with geo coordinates"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-create')
        data = {
            'name': 'Geo Property',
            'street': 'Street 1',
            'postal_code': '12345',
            'city': 'Berlin',
            'country': 'DE',
            'geo_lat': '52.520008',
            'geo_lng': '13.404954'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        # Verify coordinates
        prop = Property.objects.get(name='Geo Property')
        assert prop.geo_lat == Decimal('52.520008')
        assert prop.geo_lng == Decimal('13.404954')

    def test_create_validation_required_fields(self, api_client, admin_user):
        """Test validation for required fields"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-create')
        data = {
            'name': 'Incomplete Property'
            # Missing: street, postal_code, city
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'street' in response.data
        assert 'postal_code' in response.data
        assert 'city' in response.data


@pytest.mark.django_db
class TestPropertyUpdateAPI:
    """Tests for PUT/PATCH /api/portal/properties/{id}/update/"""

    def test_update_requires_admin(self, api_client, regular_user, sample_properties):
        """Test that regular users cannot update properties"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-update', kwargs={'pk': sample_properties[0].pk})
        data = {'name': 'Updated Name'}
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_success_admin(self, api_client, admin_user, sample_properties):
        """Test that admins can update properties"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-update', kwargs={'pk': sample_properties[0].pk})
        data = {'name': 'Updated Name'}
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

        # Verify in database
        sample_properties[0].refresh_from_db()
        assert sample_properties[0].name == 'Updated Name'


@pytest.mark.django_db
class TestPropertyDeleteAPI:
    """Tests for DELETE /api/portal/properties/{id}/delete/"""

    def test_delete_requires_admin(self, api_client, regular_user, sample_properties):
        """Test that regular users cannot delete properties"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-delete', kwargs={'pk': sample_properties[0].pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_success_admin(self, api_client, admin_user, sample_properties):
        """Test that admins can delete properties"""
        api_client.force_authenticate(user=admin_user)
        prop_id = sample_properties[0].pk
        url = reverse('portal-properties-delete', kwargs={'pk': prop_id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted from database
        assert not Property.objects.filter(pk=prop_id).exists()


@pytest.mark.django_db
class TestPropertyArchiveAPI:
    """Tests for POST /api/portal/properties/{id}/archive/"""

    def test_archive_requires_admin(self, api_client, regular_user, sample_properties):
        """Test that regular users cannot archive properties"""
        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-archive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_archive_success_admin(self, api_client, admin_user, sample_properties):
        """Test that admins can archive properties"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-archive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_archived'] is True
        assert response.data['archived_by'] == admin_user.id

        # Verify in database
        sample_properties[0].refresh_from_db()
        assert sample_properties[0].is_archived is True
        assert sample_properties[0].archived_by == admin_user

    def test_archive_already_archived(self, api_client, admin_user, sample_properties):
        """Test archiving already archived property returns 400"""
        # Archive first
        sample_properties[0].archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-archive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPropertyUnarchiveAPI:
    """Tests for POST /api/portal/properties/{id}/unarchive/"""

    def test_unarchive_requires_admin(self, api_client, regular_user, sample_properties, admin_user):
        """Test that regular users cannot unarchive properties"""
        # Archive first
        sample_properties[0].archive(admin_user)

        api_client.force_authenticate(user=regular_user)
        url = reverse('portal-properties-unarchive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unarchive_success_admin(self, api_client, admin_user, sample_properties):
        """Test that admins can unarchive properties"""
        # Archive first
        sample_properties[0].archive(admin_user)

        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-unarchive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_archived'] is False
        assert response.data['archived_by'] is None

        # Verify in database
        sample_properties[0].refresh_from_db()
        assert sample_properties[0].is_archived is False
        assert sample_properties[0].archived_by is None

    def test_unarchive_not_archived(self, api_client, admin_user, sample_properties):
        """Test unarchiving non-archived property returns 400"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('portal-properties-unarchive', kwargs={'pk': sample_properties[0].pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
