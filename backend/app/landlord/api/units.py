"""
Unit API Views for Portal
Phase 4: API Endpoints - Units

Implements RESTful API for Unit CRUD operations with:
- List with pagination, filtering, sorting
- Detail view
- Create, Update, Delete
- Archive/Unarchive actions
- RBAC and throttling
"""
from django.db.models import Count, Q
from landlord.models import Unit
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

from .units_serializers import (
    UnitCreateSerializer,
    UnitDetailSerializer,
    UnitListSerializer,
    UnitUpdateSerializer,
)


class PortalReadThrottle(UserRateThrottle):
    """Throttle for Portal read operations: 100 requests/hour"""
    rate = '100/hour'


class PortalWriteThrottle(UserRateThrottle):
    """Throttle for Portal write operations: 50 requests/hour"""
    rate = '50/hour'


class UnitPagination(PageNumberPagination):
    """Pagination for Unit list"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class UnitListAPIView(ListAPIView):
    """
    GET /api/portal/units/

    List all units with pagination, filtering, and sorting.

    Query Parameters:
    - is_archived (bool): Filter by archive status (default: false)
    - query (str): Search in unit_label, property name, floor
    - property_id (int): Filter by property
    - is_active (bool): Filter by active status
    - sort (str): Sort field (unit_label, property__name, floor, rooms, created_at) (default: unit_label)
    - order (str): Sort order (asc, desc) (default: asc)
    - page (int): Page number (default: 1)
    - page_size (int): Items per page (default: 25, max: 100)
    """
    serializer_class = UnitListSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    pagination_class = UnitPagination

    def get_queryset(self):
        """Build queryset with filters, search, and ordering"""
        queryset = Unit.objects.select_related('property').all()
        params = self.request.query_params

        # Filter by archive status (default: exclude archived)
        is_archived = params.get('is_archived', 'false').lower()
        if is_archived == 'true':
            queryset = queryset.filter(is_archived=True)
        elif is_archived == 'false':
            queryset = queryset.filter(is_archived=False)

        # Search query (unit_label, property name, floor)
        query = params.get('query', '').strip()
        if query:
            queryset = queryset.filter(
                Q(unit_label__icontains=query) |
                Q(property__name__icontains=query) |
                Q(floor__icontains=query)
            )

        # Filter by property
        property_id = params.get('property_id', '').strip()
        if property_id:
            try:
                queryset = queryset.filter(property_id=int(property_id))
            except ValueError:
                pass

        # Filter by is_active
        is_active = params.get('is_active', '').strip().lower()
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        # Annotate meters_count
        queryset = queryset.annotate(meters_count=Count('utility_meters'))

        # Ordering
        sort_field = params.get('sort', 'unit_label')
        order = params.get('order', 'asc')

        # Validate sort field
        allowed_sorts = {'unit_label', 'property__name', 'floor', 'rooms', 'created_at', 'meters_count'}
        if sort_field not in allowed_sorts:
            sort_field = 'unit_label'

        # Apply ordering
        if order == 'desc':
            sort_field = f'-{sort_field}'

        queryset = queryset.order_by(sort_field)

        return queryset


class UnitDetailAPIView(RetrieveAPIView):
    """
    GET /api/portal/units/{id}/

    Retrieve detailed information about a specific unit including meters.
    """
    serializer_class = UnitDetailSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalReadThrottle]
    queryset = Unit.objects.select_related('property').prefetch_related('utility_meters').all()
    lookup_field = 'pk'


class UnitCreateAPIView(CreateAPIView):
    """
    POST /api/portal/units/

    Create a new unit.

    Required fields: property, unit_label
    Optional fields: floor, rooms, area_sqm, notes, is_active (default: true)
    """
    serializer_class = UnitCreateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]

    def perform_create(self, serializer):
        """Save the new unit"""
        serializer.save()


class UnitUpdateAPIView(UpdateAPIView):
    """
    PATCH /api/portal/units/{id}/

    Update an existing unit.

    Supports partial updates (PATCH).
    """
    serializer_class = UnitUpdateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Unit.objects.all()
    lookup_field = 'pk'


class UnitDeleteAPIView(DestroyAPIView):
    """
    DELETE /api/portal/units/{id}/

    Delete a unit.

    Returns 409 if unit has dependencies (tenants, contracts, readings, etc.)
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Unit.objects.all()
    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        """Check for dependencies before deletion"""
        unit = self.get_object()

        # Check dependencies
        dependencies = []
        
        if unit.tenants.exists():
            dependencies.append(f"{unit.tenants.count()} Mieter")
        
        if unit.utility_meters.exists():
            dependencies.append(f"{unit.utility_meters.count()} Zähler")
        
        if unit.issues.exists():
            dependencies.append(f"{unit.issues.count()} Tickets")

        # Check contracts (if exists)
        if hasattr(unit, 'contracts') and unit.contracts.exists():
            dependencies.append(f"{unit.contracts.count()} Verträge")

        if dependencies:
            return Response(
                {
                    'error': 'Unit hat Abhängigkeiten und kann nicht gelöscht werden.',
                    'dependencies': dependencies,
                    'suggestion': 'Bitte archivieren Sie die Wohnung stattdessen.'
                },
                status=status.HTTP_409_CONFLICT
            )

        # Perform deletion
        return super().destroy(request, *args, **kwargs)


class UnitArchiveAPIView(UpdateAPIView):
    """
    POST /api/portal/units/{id}/archive/

    Archive a unit (soft-delete).
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Unit.objects.all()
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        """Archive the unit"""
        unit = self.get_object()

        if unit.is_archived:
            return Response(
                {'error': 'Wohnung ist bereits archiviert.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Archive using model method
        unit.archive(user=request.user)

        return Response(
            {
                'success': True,
                'message': f'Wohnung "{unit.unit_label}" wurde archiviert.',
                'archived_at': unit.archived_at,
            },
            status=status.HTTP_200_OK
        )


class UnitUnarchiveAPIView(UpdateAPIView):
    """
    POST /api/portal/units/{id}/unarchive/

    Unarchive a unit (restore from soft-delete).
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [PortalWriteThrottle]
    queryset = Unit.objects.all()
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        """Unarchive the unit"""
        unit = self.get_object()

        if not unit.is_archived:
            return Response(
                {'error': 'Wohnung ist nicht archiviert.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if property is archived
        if unit.property.is_archived:
            return Response(
                {
                    'error': 'Kann Wohnung nicht wiederherstellen.',
                    'reason': f'Das Gebäude "{unit.property.name}" ist archiviert.',
                    'suggestion': 'Bitte stellen Sie zuerst das Gebäude wieder her.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Unarchive
        unit.is_archived = False
        unit.archived_at = None
        unit.archived_by = None
        unit.save(update_fields=['is_archived', 'archived_at', 'archived_by'])

        return Response(
            {
                'success': True,
                'message': f'Wohnung "{unit.unit_label}" wurde wiederhergestellt.',
            },
            status=status.HTTP_200_OK
        )
