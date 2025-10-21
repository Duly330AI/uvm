"""
Property API Views for Portal
Phase 2: API Endpoints - Properties

Implements RESTful API for Property CRUD operations with:
- List with pagination, filtering, sorting
- Detail view
- Create, Update, Delete
- Archive/Unarchive actions
- RBAC and throttling
"""
from django.db.models import Count, Q
from landlord.models import Property
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .properties_serializers import (
    PropertyCreateSerializer,
    PropertyDetailSerializer,
    PropertyListSerializer,
    PropertyUpdateSerializer,
)


class PortalReadThrottle(UserRateThrottle):
    """Throttle for Portal read operations: 100 requests/hour"""
    rate = '100/hour'


class PortalWriteThrottle(UserRateThrottle):
    """Throttle for Portal write operations: 50 requests/hour"""
    rate = '50/hour'


class PropertyPagination(PageNumberPagination):
    """Pagination for Property list"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class PropertyListAPIView(ListAPIView):
    """
    GET /api/portal/properties/

    List all properties with pagination, filtering, and sorting.

    Query Parameters:
    - is_archived (bool): Filter by archive status (default: false)
    - query (str): Search in name, city, postal_code
    - city (str): Exact match filter
    - postal_code (str): Exact match filter
    - country (str): Exact match filter (DE, AT, CH)
    - sort (str): Sort field (name, city, created_at) (default: name)
    - order (str): Sort order (asc, desc) (default: asc)
    - page (int): Page number (default: 1)
    - page_size (int): Items per page (default: 25, max: 100)
    """
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    pagination_class = PropertyPagination

    def get_queryset(self):
        """Build queryset with filters, search, and ordering"""
        queryset = Property.objects.all()
        params = self.request.query_params

        # Filter by archive status (default: exclude archived)
        is_archived = params.get('is_archived', 'false').lower()
        if is_archived == 'true':
            queryset = queryset.filter(is_archived=True)
        elif is_archived == 'false':
            queryset = queryset.filter(is_archived=False)
        # If 'all', don't filter by is_archived

        # Search query (name, city, postal_code)
        query = params.get('query', '').strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(city__icontains=query) |
                Q(postal_code__icontains=query)
            )

        # Exact match filters
        city = params.get('city', '').strip()
        if city:
            queryset = queryset.filter(city__iexact=city)

        postal_code = params.get('postal_code', '').strip()
        if postal_code:
            queryset = queryset.filter(postal_code=postal_code)

        country = params.get('country', '').strip().upper()
        if country:
            queryset = queryset.filter(country=country)

        # Annotate meters_count for serializer
        queryset = queryset.annotate(meters_count=Count('utility_meters'))

        # Ordering
        sort_field = params.get('sort', 'name')
        order = params.get('order', 'asc')

        # Validate sort field
        allowed_sorts = {'name', 'city', 'created_at', 'postal_code'}
        if sort_field not in allowed_sorts:
            sort_field = 'name'

        # Apply ordering
        if order == 'desc':
            sort_field = f'-{sort_field}'

        queryset = queryset.order_by(sort_field)

        return queryset


class PropertyDetailAPIView(RetrieveAPIView):
    """
    GET /api/portal/properties/{id}/

    Retrieve detailed information about a specific property including meters.
    """
    serializer_class = PropertyDetailSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    queryset = Property.objects.prefetch_related('utility_meters').all()
    lookup_field = 'pk'


class PropertyCreateAPIView(CreateAPIView):
    """
    POST /api/portal/properties/

    Create a new property.

    Required fields: street, postal_code, city
    Optional fields: name, country, geo_lat, geo_lng, notes
    """
    serializer_class = PropertyCreateSerializer
    permission_classes = [IsAdminUser]  # Only admins can create properties
    throttle_classes = [PortalWriteThrottle]
    queryset = Property.objects.all()

    def perform_create(self, serializer):
        """Save the new property"""
        serializer.save()


class PropertyUpdateAPIView(UpdateAPIView):
    """
    PUT/PATCH /api/portal/properties/{id}/

    Update an existing property.

    PUT: Full update (all fields required)
    PATCH: Partial update (only provided fields updated)
    """
    serializer_class = PropertyUpdateSerializer
    permission_classes = [IsAdminUser]  # Only admins can update properties
    throttle_classes = [PortalWriteThrottle]
    queryset = Property.objects.all()
    lookup_field = 'pk'

    def perform_update(self, serializer):
        """Save the updated property"""
        serializer.save()


class PropertyDeleteAPIView(DestroyAPIView):
    """
    DELETE /api/portal/properties/{id}/

    Delete a property (hard delete).

    Note: Consider using archive instead of delete for data retention.
    """
    permission_classes = [IsAdminUser]  # Only admins can delete properties
    throttle_classes = [PortalWriteThrottle]
    queryset = Property.objects.all()
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        """Delete the property"""
        instance.delete()


class PropertyArchiveAPIView(UpdateAPIView):
    """
    POST /api/portal/properties/{id}/archive/

    Archive a property (soft-delete).

    Sets is_archived=True, archived_at=now(), archived_by=current_user
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Property.objects.all()
    lookup_field = 'pk'
    http_method_names = ['post']  # Only allow POST

    def post(self, request, *args, **kwargs):
        """Archive the property"""
        instance = self.get_object()

        # Check if already archived
        if instance.is_archived:
            return Response(
                {'detail': 'Property is already archived.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Archive the property
        instance.archive(request.user)

        # Return updated property
        serializer = PropertyDetailSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PropertyUnarchiveAPIView(UpdateAPIView):
    """
    POST /api/portal/properties/{id}/unarchive/

    Unarchive a property (restore from soft-delete).

    Sets is_archived=False, clears archived_at and archived_by
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Property.objects.all()
    lookup_field = 'pk'
    http_method_names = ['post']  # Only allow POST

    def post(self, request, *args, **kwargs):
        """Unarchive the property"""
        instance = self.get_object()

        # Check if not archived
        if not instance.is_archived:
            return Response(
                {'detail': 'Property is not archived.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Unarchive the property
        instance.is_archived = False
        instance.archived_at = None
        instance.archived_by = None
        instance.save(update_fields=['is_archived', 'archived_at', 'archived_by'])

        # Return updated property
        serializer = PropertyDetailSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

