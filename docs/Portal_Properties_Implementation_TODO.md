# Portal Properties CRUD + Meters - Implementation TODO List

**Spec Version:** v1.3 (Final - Production Ready)
**Total Tasks:** 75 (broken down into 200+ subtasks)
**Estimated Effort:** 8.1 PT
**Started:** 2025-10-20
**Status:** 🟡 In Progress

---

## PHASE 1: Core Models & Migrations (1.2 PT)

**Goal:** Extend Property model with archive fields, add Geo-Coordinates with constraints, implement DB-level uniqueness for default meters.

### ✅ Task 1.1: Add Archive Fields to Property Model

**File:** `backend/app/landlord/models.py`

- [ ] 1.1.1 Add `is_archived = BooleanField(default=False, db_index=True)` to Property
- [ ] 1.1.2 Add `archived_at = DateTimeField(null=True, blank=True)` to Property
- [ ] 1.1.3 Add `archived_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='archived_properties')` to Property
- [ ] 1.1.4 Update Property Meta class ordering to exclude archived by default
- [ ] 1.1.5 Add model method `archive(user)` that sets all three fields atomically
- [ ] 1.1.6 Write unit test: `test_property_archive_sets_all_fields()`
- [ ] 1.1.7 Write unit test: `test_property_archive_idempotent()`

**Estimate:** 0.15 PT

---

### ✅ Task 1.2: Add Geo-Coordinates with DB Check-Constraints

**File:** `backend/app/landlord/models.py`

- [ ] 1.2.1 Add `geo_lat = DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)` to Property
- [ ] 1.2.2 Add `geo_lng = DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)` to Property
- [ ] 1.2.3 Create DB Check-Constraint: `geo_lat >= -90.0 AND geo_lat <= 90.0`
- [ ] 1.2.4 Create DB Check-Constraint: `geo_lng >= -180.0 AND geo_lng <= 180.0`
- [ ] 1.2.5 Add clean() method validation for geo_lat/geo_lng ranges
- [ ] 1.2.6 Write unit test: `test_property_geo_lat_valid_range()`
- [ ] 1.2.7 Write unit test: `test_property_geo_lat_invalid_range_raises()`
- [ ] 1.2.8 Write unit test: `test_property_geo_lng_valid_range()`
- [ ] 1.2.9 Write unit test: `test_property_geo_lng_invalid_range_raises()`

**Estimate:** 0.12 PT

---

### ✅ Task 1.3: Add Country Choices with Localization

**File:** `backend/app/landlord/models.py`

- [ ] 1.3.1 Create `COUNTRY_CHOICES` tuple: `(("DE", "Deutschland"), ("AT", "Österreich"), ("CH", "Schweiz"))`
- [ ] 1.3.2 Add `country = CharField(max_length=2, choices=COUNTRY_CHOICES, default="DE")` to Property
- [ ] 1.3.3 Create validator function: `validate_country_whitelist(value)` in `landlord/validators.py`
- [ ] 1.3.4 Add validator to country field: `validators=[validate_country_whitelist]`
- [ ] 1.3.5 Add `@property` method `get_country_display_localized()` for frontend
- [ ] 1.3.6 Write unit test: `test_property_country_default_DE()`
- [ ] 1.3.7 Write unit test: `test_property_country_valid_choices()`
- [ ] 1.3.8 Write unit test: `test_property_country_invalid_raises()`

**Estimate:** 0.10 PT

---

### ✅ Task 1.4: Update All Field Validations

**File:** `backend/app/landlord/models.py`

**Property Fields:**

- [ ] 1.4.1 Update `name = CharField(max_length=200, validators=[MinLengthValidator(1)])`
- [ ] 1.4.2 Update `street = CharField(max_length=200, blank=True)`
- [ ] 1.4.3 Create `validate_postal_code_de(value)` in validators.py (5 digits for DE)
- [ ] 1.4.4 Update `postal_code = CharField(max_length=10, validators=[validate_postal_code])`
- [ ] 1.4.5 Update `city = CharField(max_length=100, blank=True)`
- [ ] 1.4.6 Update `notes = TextField(max_length=2000, blank=True)`
- [ ] 1.4.7 Write unit test: `test_property_name_max_length_200()`
- [ ] 1.4.8 Write unit test: `test_property_postal_code_de_5_digits()`
- [ ] 1.4.9 Write unit test: `test_property_notes_max_2000()`

**UtilityMeter Fields:**

- [ ] 1.4.10 Update `serial_number = CharField(max_length=50, blank=True)`
- [ ] 1.4.11 Create `validate_serial_number_format(value)` - alphanumeric + dash/slash
- [ ] 1.4.12 Add validator to serial_number field
- [ ] 1.4.13 Update `notes = TextField(max_length=1000, blank=True)` on UtilityMeter
- [ ] 1.4.14 Update `initial_reading_value = DecimalField(validators=[MinValueValidator(0)])`
- [ ] 1.4.15 Add clean() validation: `removed_at >= installed_at`
- [ ] 1.4.16 Write unit test: `test_meter_serial_number_max_50()`
- [ ] 1.4.17 Write unit test: `test_meter_serial_number_valid_chars()`
- [ ] 1.4.18 Write unit test: `test_meter_initial_reading_non_negative()`
- [ ] 1.4.19 Write unit test: `test_meter_removed_at_after_installed_at()`

**Estimate:** 0.18 PT

---

### ✅ Task 1.5: Add Postgres Partial Unique Constraint

**File:** `backend/app/landlord/models.py`

- [ ] 1.5.1 In UtilityMeter Meta class, add:
  ```python
  constraints = [
      models.UniqueConstraint(
          fields=['property', 'meter_type'],
          condition=Q(is_default=True),
          name='unique_default_per_property_meter_type'
      )
  ]
  ```
- [ ] 1.5.2 Write unit test: `test_meter_only_one_default_per_property_medium()`
- [ ] 1.5.3 Write unit test: `test_meter_multiple_non_defaults_allowed()`
- [ ] 1.5.4 Write unit test: `test_meter_constraint_violation_raises_integrity_error()`

**Estimate:** 0.08 PT

---

### ✅ Task 1.6: Normalize Serial Number to Uppercase

**File:** `backend/app/landlord/models.py`

- [ ] 1.6.1 Override `save()` method in UtilityMeter:
  ```python
  def save(self, *args, **kwargs):
      if self.serial_number:
          self.serial_number = self.serial_number.upper()
      super().save(*args, **kwargs)
  ```
- [ ] 1.6.2 Write unit test: `test_meter_serial_number_normalized_uppercase()`
- [ ] 1.6.3 Write unit test: `test_meter_serial_number_empty_not_normalized()`

**Estimate:** 0.05 PT

---

### ✅ Task 1.7: Create Migrations

**Files:** `backend/app/landlord/migrations/`

- [ ] 1.7.1 Run `python manage.py makemigrations landlord -n add_property_archive_fields`
- [ ] 1.7.2 Review migration file for correctness (is_archived, archived_at, archived_by)
- [ ] 1.7.3 Run `python manage.py makemigrations landlord -n add_property_geo_coordinates`
- [ ] 1.7.4 Review migration file for DecimalField(9,6) and Check-Constraints
- [ ] 1.7.5 Run `python manage.py makemigrations landlord -n add_country_field_property`
- [ ] 1.7.6 Review migration for country CharField with choices
- [ ] 1.7.7 Run `python manage.py makemigrations landlord -n update_field_validations`
- [ ] 1.7.8 Review all validators are in migration dependencies
- [ ] 1.7.9 Run `python manage.py makemigrations landlord -n add_meter_unique_constraint`
- [ ] 1.7.10 Review Partial UniqueConstraint in migration
- [ ] 1.7.11 Test migrations in dev: `python manage.py migrate --plan`
- [ ] 1.7.12 Apply migrations: `python manage.py migrate`
- [ ] 1.7.13 Verify schema in PostgreSQL: `\d landlord_property`
- [ ] 1.7.14 Verify constraint in PostgreSQL: `\d landlord_utilitymeter`

**Estimate:** 0.12 PT

---

### ✅ Task 1.8: Add DB Indexes (Property)

**File:** Migration file

- [ ] 1.8.1 Add index on `name` (sorting): `db_index=True` in model field
- [ ] 1.8.2 Add index on `city` (filter): `db_index=True` in model field
- [ ] 1.8.3 Add index on `postal_code` (filter): `db_index=True` in model field
- [ ] 1.8.4 Add index on `is_archived` (already done in 1.1.1)
- [ ] 1.8.5 Verify indexes in migration file
- [ ] 1.8.6 Apply migration and verify with `\di landlord_property*` in psql

**Estimate:** 0.05 PT

---

### ✅ Task 1.9: Add DB Indexes (UtilityMeter)

**File:** Migration file

- [ ] 1.9.1 Add composite index: `Index(fields=['property', 'meter_type', 'is_default'])`
- [ ] 1.9.2 Add composite index: `Index(fields=['property', 'meter_type', 'is_active'])`
- [ ] 1.9.3 Add to UtilityMeter Meta class:
  ```python
  indexes = [
      models.Index(fields=['property', 'meter_type', 'is_default'], name='idx_meter_default'),
      models.Index(fields=['property', 'meter_type', 'is_active'], name='idx_meter_active'),
  ]
  ```
- [ ] 1.9.4 Create migration: `python manage.py makemigrations landlord -n add_meter_indexes`
- [ ] 1.9.5 Apply migration
- [ ] 1.9.6 Verify indexes in PostgreSQL: `\di landlord_utilitymeter*`

**Estimate:** 0.06 PT

---

### ✅ Task 1.10: Optional - Add Trigram Index

**File:** Migration file + PostgreSQL

- [ ] 1.10.1 Create migration with `RunSQL` to enable pg_trgm:
  ```python
  operations = [
      migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;"),
  ]
  ```
- [ ] 1.10.2 Create migration for GIN index:
  ```python
  migrations.RunSQL(
      "CREATE INDEX landlord_property_name_trgm_idx ON landlord_property USING GIN (name gin_trgm_ops);",
      reverse_sql="DROP INDEX IF EXISTS landlord_property_name_trgm_idx;"
  )
  ```
- [ ] 1.10.3 Apply migration
- [ ] 1.10.4 Test fuzzy search: `SELECT * FROM landlord_property WHERE name % 'search_term';`
- [ ] 1.10.5 Verify index usage: `EXPLAIN ANALYZE SELECT ...`

**Estimate:** 0.08 PT (OPTIONAL)

---

### ✅ Task 1.11: Model Unit Tests (≥85% Coverage)

**File:** `backend/app/landlord/tests/test_property_model_extended.py`

- [ ] 1.11.1 Test suite setup: Create PropertyModelExtendedTestCase class
- [ ] 1.11.2 Test: `test_property_create_with_all_fields()`
- [ ] 1.11.3 Test: `test_property_archive_sets_fields()`
- [ ] 1.11.4 Test: `test_property_archive_by_user()`
- [ ] 1.11.5 Test: `test_property_geo_lat_valid_range()`
- [ ] 1.11.6 Test: `test_property_geo_lat_boundary_values()`
- [ ] 1.11.7 Test: `test_property_geo_lng_valid_range()`
- [ ] 1.11.8 Test: `test_property_country_default_de()`
- [ ] 1.11.9 Test: `test_property_country_choices_valid()`
- [ ] 1.11.10 Test: `test_property_country_invalid_raises()`
- [ ] 1.11.11 Test: `test_property_name_max_length()`
- [ ] 1.11.12 Test: `test_property_postal_code_validation()`
- [ ] 1.11.13 Test: `test_property_notes_max_length()`
- [ ] 1.11.14 Test: `test_meter_serial_number_uppercase_normalization()`
- [ ] 1.11.15 Test: `test_meter_unique_constraint_default()`
- [ ] 1.11.16 Test: `test_meter_initial_reading_non_negative()`
- [ ] 1.11.17 Test: `test_meter_removed_at_validation()`
- [ ] 1.11.18 Run tests: `pytest landlord/tests/test_property_model_extended.py -v`
- [ ] 1.11.19 Check coverage: `pytest --cov=landlord.models --cov-report=html`
- [ ] 1.11.20 Verify ≥85% coverage for Property and UtilityMeter models

**Estimate:** 0.20 PT

---

**PHASE 1 TOTAL:** 1.2 PT (11 tasks, 100+ subtasks)

---

## PHASE 2: API Endpoints - Properties (1.3 PT)

**Goal:** Implement RESTful API for Property CRUD with pagination, filtering, sorting, RBAC, and throttling.

### ✅ Task 2.1: GET /api/portal/properties/ (List)

**Files:** `backend/app/landlord/api/views.py`, `landlord/api/serializers.py`

**Serializer:**

- [ ] 2.1.1 Create `PropertyListSerializer` in `api/serializers.py`
- [ ] 2.1.2 Add fields: id, name, street, city, postal_code, country, is_archived, created_at, updated_at
- [ ] 2.1.3 Add computed field: `meters_count = SerializerMethodField()`
- [ ] 2.1.4 Implement `get_meters_count(self, obj)` → `obj.utilitymeter_set.count()`

**View:**

- [ ] 2.1.5 Create `PropertyListAPIView(ListAPIView)` in `api/views.py`
- [ ] 2.1.6 Set `serializer_class = PropertyListSerializer`
- [ ] 2.1.7 Set `permission_classes = [IsAuthenticated]`
- [ ] 2.1.8 Set `throttle_classes = [PortalReadThrottle]`
- [ ] 2.1.9 Set `pagination_class = PageNumberPagination` (page_size=25, max=100)
- [ ] 2.1.10 Implement `get_queryset()`:
  - Filter `is_archived` by query param (default=False)
  - Filter `query` (name**icontains, city**icontains, postal_code\_\_icontains)
  - Filter `city`, `postal_code`, `country` exact match
  - Order by `sort` param (name, city, created_at), default=name
  - Order direction `order` (asc, desc), default=asc
  - Annotate `meters_count`
- [ ] 2.1.11 Add filter_backends: `[DjangoFilterBackend, OrderingFilter, SearchFilter]`
- [ ] 2.1.12 Write unit test: `test_property_list_returns_200()`
- [ ] 2.1.13 Write unit test: `test_property_list_pagination_default_25()`
- [ ] 2.1.14 Write unit test: `test_property_list_filter_by_city()`
- [ ] 2.1.15 Write unit test: `test_property_list_filter_archived_false_default()`
- [ ] 2.1.16 Write unit test: `test_property_list_filter_archived_true()`
- [ ] 2.1.17 Write unit test: `test_property_list_search_query_name()`
- [ ] 2.1.18 Write unit test: `test_property_list_sort_by_city_asc()`
- [ ] 2.1.19 Write unit test: `test_property_list_requires_authentication()`

**URL:**

- [ ] 2.1.20 Add route in `api/urls.py`: `path('portal/properties/', PropertyListAPIView.as_view())`

**Estimate:** 0.20 PT

---

### ✅ Task 2.2: GET /api/portal/properties/{id}/ (Detail)

**Files:** `backend/app/landlord/api/views.py`, `api/serializers.py`

**Serializer:**

- [ ] 2.2.1 Create `PropertyDetailSerializer` in `api/serializers.py`
- [ ] 2.2.2 Add all fields: name, street, postal_code, city, country, geo_lat, geo_lng, notes, is_archived, archived_at, archived_by, created_at, updated_at
- [ ] 2.2.3 Add nested field: `meters = UtilityMeterSerializer(source='utilitymeter_set', many=True, read_only=True)`
- [ ] 2.2.4 Create `UtilityMeterSerializer` with all meter fields

**View:**

- [ ] 2.2.5 Create `PropertyDetailAPIView(RetrieveAPIView)` in `api/views.py`
- [ ] 2.2.6 Set `serializer_class = PropertyDetailSerializer`
- [ ] 2.2.7 Set `permission_classes = [IsAuthenticated]`
- [ ] 2.2.8 Set `throttle_classes = [PortalReadThrottle]`
- [ ] 2.2.9 Override `get_queryset()`: `Property.objects.prefetch_related('utilitymeter_set')`
- [ ] 2.2.10 Write unit test: `test_property_detail_returns_200()`
- [ ] 2.2.11 Write unit test: `test_property_detail_includes_meters()`
- [ ] 2.2.12 Write unit test: `test_property_detail_not_found_404()`
- [ ] 2.2.13 Write unit test: `test_property_detail_requires_authentication()`

**URL:**

- [ ] 2.2.14 Add route: `path('portal/properties/<int:pk>/', PropertyDetailAPIView.as_view())`

**Estimate:** 0.15 PT

---

### ✅ Task 2.3: POST /api/portal/properties/ (Create)

**Files:** `backend/app/landlord/api/views.py`, `api/serializers.py`

**Serializer:**

- [ ] 2.3.1 Create `PropertyCreateSerializer` in `api/serializers.py`
- [ ] 2.3.2 Add fields: name (required), street, postal_code, city, country, geo_lat, geo_lng, notes
- [ ] 2.3.3 Add field validations: Country whitelist, Geo ranges, max lengths
- [ ] 2.3.4 Implement `validate_geo_lat(value)` → check -90 to +90
- [ ] 2.3.5 Implement `validate_geo_lng(value)` → check -180 to +180
- [ ] 2.3.6 Implement `validate_country(value)` → check in ['DE', 'AT', 'CH']

**View:**

- [ ] 2.3.7 Create `PropertyCreateAPIView(CreateAPIView)` in `api/views.py`
- [ ] 2.3.8 Set `serializer_class = PropertyCreateSerializer`
- [ ] 2.3.9 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 2.3.10 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 2.3.11 Override `perform_create(serializer)` to set created_by
- [ ] 2.3.12 Write unit test: `test_property_create_returns_201()`
- [ ] 2.3.13 Write unit test: `test_property_create_name_only_minimal()`
- [ ] 2.3.14 Write unit test: `test_property_create_all_fields()`
- [ ] 2.3.15 Write unit test: `test_property_create_invalid_geo_lat_400()`
- [ ] 2.3.16 Write unit test: `test_property_create_invalid_country_400()`
- [ ] 2.3.17 Write unit test: `test_property_create_requires_permission()`
- [ ] 2.3.18 Write unit test: `test_property_create_throttle_limit()`

**URL:**

- [ ] 2.3.19 Use same route as 2.1 (POST on list endpoint)

**Estimate:** 0.18 PT

---

### ✅ Task 2.4: PATCH /api/portal/properties/{id}/ (Update)

**Files:** `backend/app/landlord/api/views.py`, `api/serializers.py`

**Serializer:**

- [ ] 2.4.1 Create `PropertyUpdateSerializer` (same as Create, all fields optional)
- [ ] 2.4.2 Set `partial=True` support

**View:**

- [ ] 2.4.3 Create `PropertyUpdateAPIView(UpdateAPIView)` in `api/views.py`
- [ ] 2.4.4 Set `serializer_class = PropertyUpdateSerializer`
- [ ] 2.4.5 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 2.4.6 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 2.4.7 Override `perform_update(serializer)` to set updated_by
- [ ] 2.4.8 Write unit test: `test_property_update_returns_200()`
- [ ] 2.4.9 Write unit test: `test_property_partial_update_name_only()`
- [ ] 2.4.10 Write unit test: `test_property_update_all_fields()`
- [ ] 2.4.11 Write unit test: `test_property_update_invalid_geo_lat_400()`
- [ ] 2.4.12 Write unit test: `test_property_update_not_found_404()`
- [ ] 2.4.13 Write unit test: `test_property_update_requires_permission()`

**URL:**

- [ ] 2.4.14 Use same route as 2.2 (PATCH on detail endpoint)

**Estimate:** 0.15 PT

---

### ✅ Task 2.5: POST /api/portal/properties/{id}/archive/ (Archive)

**Files:** `backend/app/landlord/api/views.py`

**View:**

- [ ] 2.5.1 Create `PropertyArchiveAPIView(GenericAPIView)` with `post()` method
- [ ] 2.5.2 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 2.5.3 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 2.5.4 In `post()`: Get property, call `property.archive(request.user)`, save, return 200
- [ ] 2.5.5 Return serialized property with `PropertyDetailSerializer`
- [ ] 2.5.6 Write unit test: `test_property_archive_returns_200()`
- [ ] 2.5.7 Write unit test: `test_property_archive_sets_fields()`
- [ ] 2.5.8 Write unit test: `test_property_archive_idempotent()`
- [ ] 2.5.9 Write unit test: `test_property_archive_not_found_404()`
- [ ] 2.5.10 Write unit test: `test_property_archive_requires_permission()`

**URL:**

- [ ] 2.5.11 Add route: `path('portal/properties/<int:pk>/archive/', PropertyArchiveAPIView.as_view())`

**Estimate:** 0.12 PT

---

### ✅ Task 2.6: DELETE /api/portal/properties/{id}/ (Hard-Delete)

**Files:** `backend/app/landlord/api/views.py`

**View:**

- [ ] 2.6.1 Create `PropertyDeleteAPIView(DestroyAPIView)` in `api/views.py`
- [ ] 2.6.2 Set `permission_classes = [IsAuthenticated, IsAdminUser]` (Admin only!)
- [ ] 2.6.3 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 2.6.4 Override `perform_destroy(instance)`:
  - Check dependencies: Units, Contracts, Payments, Documents, UtilityMeters, UtilityReadings
  - If dependencies exist: raise ValidationError with 409 status
  - Error message: "Löschen nicht möglich: Es bestehen noch abhängige Daten..."
  - Suggest alternative: "Bitte archivieren Sie das Gebäude stattdessen."
- [ ] 2.6.5 If no dependencies: call `instance.delete()`
- [ ] 2.6.6 Write unit test: `test_property_delete_no_dependencies_204()`
- [ ] 2.6.7 Write unit test: `test_property_delete_with_units_409()`
- [ ] 2.6.8 Write unit test: `test_property_delete_with_contracts_409()`
- [ ] 2.6.9 Write unit test: `test_property_delete_with_meters_409()`
- [ ] 2.6.10 Write unit test: `test_property_delete_with_readings_409()`
- [ ] 2.6.11 Write unit test: `test_property_delete_requires_admin()`
- [ ] 2.6.12 Write unit test: `test_property_delete_not_found_404()`

**URL:**

- [ ] 2.6.13 Use same route as 2.2 (DELETE on detail endpoint)

**Estimate:** 0.18 PT

---

### ✅ Task 2.7: Serializers with All Validations

**File:** `backend/app/landlord/api/serializers.py`

- [ ] 2.7.1 Review all serializers created in 2.1-2.6
- [ ] 2.7.2 Ensure Country whitelist validation in all serializers
- [ ] 2.7.3 Ensure Geo lat/lng range validation (-90/+90, -180/+180)
- [ ] 2.7.4 Ensure max_length validations (name: 200, notes: 2000)
- [ ] 2.7.5 Ensure postal_code validation (5 digits for DE)
- [ ] 2.7.6 Add custom error messages for all validations (user-friendly German)
- [ ] 2.7.7 Write unit test: `test_serializer_country_invalid_returns_error()`
- [ ] 2.7.8 Write unit test: `test_serializer_geo_lat_out_of_range_error()`
- [ ] 2.7.9 Write unit test: `test_serializer_name_max_length_error()`
- [ ] 2.7.10 Write unit test: `test_serializer_postal_code_de_format_error()`

**Estimate:** 0.12 PT

---

### ✅ Task 2.8: RBAC Permissions

**File:** `backend/app/landlord/permissions.py`

- [ ] 2.8.1 Create `IsAdminOrPropertyManager` permission class:
  ```python
  class IsAdminOrPropertyManager(BasePermission):
      def has_permission(self, request, view):
          return (
              request.user.is_authenticated and
              (request.user.is_staff or
               request.user.groups.filter(name='Property-Manager').exists())
          )
  ```
- [ ] 2.8.2 Apply to all CREATE/UPDATE/ARCHIVE endpoints
- [ ] 2.8.3 Apply `IsAdminUser` to DELETE endpoint only
- [ ] 2.8.4 Write unit test: `test_permission_admin_can_create()`
- [ ] 2.8.5 Write unit test: `test_permission_property_manager_can_create()`
- [ ] 2.8.6 Write unit test: `test_permission_landlord_cannot_create()`
- [ ] 2.8.7 Write unit test: `test_permission_only_admin_can_delete()`

**Estimate:** 0.10 PT

---

### ✅ Task 2.9: Throttling

**File:** `backend/app/landlord/throttles.py`

- [ ] 2.9.1 Create `PortalMutatingThrottle(UserRateThrottle)`:
  ```python
  class PortalMutatingThrottle(UserRateThrottle):
      scope = 'portal_mutating'
      rate = '60/min'  # Per user + IP
  ```
- [ ] 2.9.2 Create `PortalReadThrottle(UserRateThrottle)`:
  ```python
  class PortalReadThrottle(UserRateThrottle):
      scope = 'portal_read'
      rate = '240/min'
  ```
- [ ] 2.9.3 Add to `settings.py`:
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_THROTTLE_RATES': {
          'portal_mutating': '60/min',
          'portal_read': '240/min',
      }
  }
  ```
- [ ] 2.9.4 Apply throttles to all API views
- [ ] 2.9.5 Write unit test: `test_throttle_mutating_60_per_minute()`
- [ ] 2.9.6 Write unit test: `test_throttle_read_240_per_minute()`
- [ ] 2.9.7 Write unit test: `test_throttle_returns_429_with_retry_after()`

**Estimate:** 0.10 PT

---

### ✅ Task 2.10: API Unit Tests (≥90% Routes)

**File:** `backend/app/landlord/tests/test_property_api.py`

- [ ] 2.10.1 Test suite setup: Create PropertyAPITestCase class
- [ ] 2.10.2 Setup fixtures: Properties, Users with different roles
- [ ] 2.10.3 Test all HTTP status codes: 200, 201, 204, 400, 401, 403, 404, 409, 422, 429
- [ ] 2.10.4 Test all query parameters: query, city, postal_code, country, is_archived, sort, order, page, page_size
- [ ] 2.10.5 Test pagination: default 25, max 100, page navigation
- [ ] 2.10.6 Test filtering: by city, postal_code, country, is_archived
- [ ] 2.10.7 Test sorting: by name, city, created_at (asc/desc)
- [ ] 2.10.8 Test search: query in name, city, postal_code
- [ ] 2.10.9 Test RBAC: Admin, Property-Manager, Landlord, Anonymous
- [ ] 2.10.10 Test throttling: Rate limits, 429 responses
- [ ] 2.10.11 Test validation errors: Invalid geo, country, postal_code
- [ ] 2.10.12 Test dependency checks: Delete with Units, Contracts, etc.
- [ ] 2.10.13 Run tests: `pytest landlord/tests/test_property_api.py -v`
- [ ] 2.10.14 Check coverage: `pytest --cov=landlord.api.views --cov-report=html`
- [ ] 2.10.15 Verify ≥90% coverage for Property API views

**Estimate:** 0.20 PT

---

**PHASE 2 TOTAL:** 1.3 PT (10 tasks, 140+ subtasks)

---

## PHASE 3: API Endpoints - Meters (0.9 PT)

**Goal:** Implement nested API for UtilityMeter CRUD under Property, with default-constraint validation and Reading dependency check.

### ✅ Task 3.1: POST /api/portal/properties/{id}/meters/ (Create)

**Files:** `backend/app/landlord/api/views.py`, `api/serializers.py`

**Serializer:**

- [ ] 3.1.1 Create `UtilityMeterCreateSerializer` in `api/serializers.py`
- [ ] 3.1.2 Add fields: meter_type, serial_number, is_default, is_active, initial_reading_value, installed_at, removed_at, notes
- [ ] 3.1.3 Add validation: `removed_at >= installed_at`
- [ ] 3.1.4 Add validation: `initial_reading_value >= 0`
- [ ] 3.1.5 Add validation: Serial number format (alphanumeric + dash/slash)

**View:**

- [ ] 3.1.6 Create `PropertyMeterCreateAPIView(CreateAPIView)` in `api/views.py`
- [ ] 3.1.7 Set `serializer_class = UtilityMeterCreateSerializer`
- [ ] 3.1.8 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 3.1.9 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 3.1.10 Override `perform_create(serializer)`:
  - Get property from URL param
  - Set `property=property_instance` in serializer
  - If `is_default=True`: Transactionally set all other meters of same type to `is_default=False`
  - Save meter
- [ ] 3.1.11 Write unit test: `test_meter_create_returns_201()`
- [ ] 3.1.12 Write unit test: `test_meter_create_all_fields()`
- [ ] 3.1.13 Write unit test: `test_meter_create_invalid_removed_at_422()`
- [ ] 3.1.14 Write unit test: `test_meter_create_negative_initial_reading_400()`
- [ ] 3.1.15 Write unit test: `test_meter_create_requires_permission()`

**URL:**

- [ ] 3.1.16 Add route: `path('portal/properties/<int:property_id>/meters/', PropertyMeterCreateAPIView.as_view())`

**Estimate:** 0.18 PT

---

### ✅ Task 3.2: PATCH /api/portal/properties/{id}/meters/{meter_id}/ (Update)

**Files:** `backend/app/landlord/api/views.py`, `api/serializers.py`

**Serializer:**

- [ ] 3.2.1 Create `UtilityMeterUpdateSerializer` (same as Create, all optional)

**View:**

- [ ] 3.2.2 Create `PropertyMeterUpdateAPIView(UpdateAPIView)` in `api/views.py`
- [ ] 3.2.3 Set `serializer_class = UtilityMeterUpdateSerializer`
- [ ] 3.2.4 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 3.2.5 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 3.2.6 Override `perform_update(serializer)`:
  - If `is_default` changed to True: Set others to False (transactional)
  - If `is_active` set to False and `removed_at` is None: Set `removed_at=today`
- [ ] 3.2.7 Write unit test: `test_meter_update_returns_200()`
- [ ] 3.2.8 Write unit test: `test_meter_update_partial_fields()`
- [ ] 3.2.9 Write unit test: `test_meter_update_set_default_clears_others()`
- [ ] 3.2.10 Write unit test: `test_meter_deactivate_sets_removed_at()`
- [ ] 3.2.11 Write unit test: `test_meter_update_not_found_404()`

**URL:**

- [ ] 3.2.12 Add route: `path('portal/properties/<int:property_id>/meters/<int:pk>/', PropertyMeterUpdateAPIView.as_view())`

**Estimate:** 0.15 PT

---

### ✅ Task 3.3: DELETE /api/portal/properties/{id}/meters/{meter_id}/ (Delete)

**Files:** `backend/app/landlord/api/views.py`

**View:**

- [ ] 3.3.1 Create `PropertyMeterDeleteAPIView(DestroyAPIView)` in `api/views.py`
- [ ] 3.3.2 Set `permission_classes = [IsAuthenticated, IsAdminOrPropertyManager]`
- [ ] 3.3.3 Set `throttle_classes = [PortalMutatingThrottle]`
- [ ] 3.3.4 Override `perform_destroy(instance)`:
  - Check if meter has Readings: `instance.utilityreading_set.exists()`
  - If Readings exist: raise ValidationError with 409 status
  - Error message: "Zähler kann nicht gelöscht werden, da bereits Zählerstände existieren. Bitte deaktivieren."
  - Suggest alternative: Deactivate via PATCH `is_active=false`
  - If no Readings: call `instance.delete()`
- [ ] 3.3.5 Write unit test: `test_meter_delete_no_readings_204()`
- [ ] 3.3.6 Write unit test: `test_meter_delete_with_readings_409()`
- [ ] 3.3.7 Write unit test: `test_meter_delete_409_suggests_deactivate()`
- [ ] 3.3.8 Write unit test: `test_meter_delete_not_found_404()`
- [ ] 3.3.9 Write unit test: `test_meter_delete_requires_permission()`

**URL:**

- [ ] 3.3.10 Use same route as 3.2 (DELETE method)

**Estimate:** 0.15 PT

---

### ✅ Task 3.4: Default-Constraint Validation (Transactional)

**File:** `backend/app/landlord/api/views.py` (in create/update methods)

- [ ] 3.4.1 Create helper function `set_meter_as_default(meter, property_id, meter_type)`:

  ```python
  @transaction.atomic
  def set_meter_as_default(meter, property_id, meter_type):
      # Set all other meters of same type to is_default=False
      UtilityMeter.objects.filter(
          property_id=property_id,
          meter_type=meter_type,
          is_default=True
      ).exclude(id=meter.id).update(is_default=False)

      # Set this meter to default
      meter.is_default = True
      meter.save()
  ```

- [ ] 3.4.2 Integrate into `PropertyMeterCreateAPIView.perform_create()`
- [ ] 3.4.3 Integrate into `PropertyMeterUpdateAPIView.perform_update()`
- [ ] 3.4.4 Write unit test: `test_set_default_clears_other_defaults_atomically()`
- [ ] 3.4.5 Write unit test: `test_only_one_default_per_property_medium()`
- [ ] 3.4.6 Write unit test: `test_default_constraint_db_enforced()`

**Estimate:** 0.12 PT

---

### ✅ Task 3.5: Deactivate-Instead-of-Delete Logic

**File:** `backend/app/landlord/api/views.py`

- [ ] 3.5.1 In `PropertyMeterDeleteAPIView`, add response hint on 409:
  ```python
  {
      "error": "Zähler kann nicht gelöscht werden...",
      "suggestion": "Deaktivieren Sie den Zähler stattdessen.",
      "action": {
          "method": "PATCH",
          "url": f"/api/portal/properties/{property_id}/meters/{meter_id}/",
          "payload": {"is_active": false, "removed_at": "2025-10-20"}
      }
  }
  ```
- [ ] 3.5.2 Write unit test: `test_delete_409_response_includes_deactivate_action()`
- [ ] 3.5.3 Write unit test: `test_deactivate_action_url_correct()`

**Estimate:** 0.08 PT

---

### ✅ Task 3.6: Meter Serializers with All Validations

**File:** `backend/app/landlord/api/serializers.py`

- [ ] 3.6.1 Review all meter serializers created in 3.1-3.3
- [ ] 3.6.2 Ensure `removed_at >= installed_at` validation
- [ ] 3.6.3 Ensure `initial_reading_value >= 0` validation
- [ ] 3.6.4 Ensure serial_number format validation (A-Z, 0-9, dash, slash)
- [ ] 3.6.5 Ensure max_length validations (serial: 50, notes: 1000)
- [ ] 3.6.6 Add custom error messages (user-friendly German)
- [ ] 3.6.7 Write unit test: `test_meter_serializer_removed_at_validation()`
- [ ] 3.6.8 Write unit test: `test_meter_serializer_initial_reading_validation()`
- [ ] 3.6.9 Write unit test: `test_meter_serializer_serial_number_format()`

**Estimate:** 0.10 PT

---

### ✅ Task 3.7: API Tests for Meter Endpoints

**File:** `backend/app/landlord/tests/test_meter_api.py`

- [ ] 3.7.1 Test suite setup: Create MeterAPITestCase class
- [ ] 3.7.2 Setup fixtures: Properties with Meters, Users with roles
- [ ] 3.7.3 Test: `test_meter_create_returns_201()`
- [ ] 3.7.4 Test: `test_meter_create_all_fields()`
- [ ] 3.7.5 Test: `test_meter_create_sets_default_clears_others()`
- [ ] 3.7.6 Test: `test_meter_update_returns_200()`
- [ ] 3.7.7 Test: `test_meter_update_deactivate_sets_removed_at()`
- [ ] 3.7.8 Test: `test_meter_delete_no_readings_204()`
- [ ] 3.7.9 Test: `test_meter_delete_with_readings_409()`
- [ ] 3.7.10 Test: `test_meter_delete_409_includes_deactivate_hint()`
- [ ] 3.7.11 Test: `test_meter_removed_at_before_installed_at_422()`
- [ ] 3.7.12 Test: `test_meter_negative_initial_reading_400()`
- [ ] 3.7.13 Test: `test_meter_invalid_serial_number_format_400()`
- [ ] 3.7.14 Test: `test_meter_requires_permission()`
- [ ] 3.7.15 Test: `test_meter_throttle_limit()`
- [ ] 3.7.16 Run tests: `pytest landlord/tests/test_meter_api.py -v`
- [ ] 3.7.17 Check coverage: `pytest --cov=landlord.api.views --cov-report=html`
- [ ] 3.7.18 Verify ≥90% coverage for Meter API views

**Estimate:** 0.22 PT

---

**PHASE 3 TOTAL:** 0.9 PT (7 tasks, 90+ subtasks)

---

## PHASE 4: Portal Views - List & Create (0.9 PT)

**Goal:** Implement HTML views for Property list and create form with server-side rendering.

### ✅ Task 4.1: Route /portal/properties/ (List View)

**Files:** `backend/app/landlord/views.py`, `templates/portal/property_list.html`

- [ ] 4.1.1 Create `PropertyListView(LoginRequiredMixin, ListView)` in `views.py`
- [ ] 4.1.2 Set `model = Property`, `template_name = 'portal/property_list.html'`
- [ ] 4.1.3 Set `paginate_by = 25`
- [ ] 4.1.4 Override `get_queryset()`: Filter `is_archived=False` by default
- [ ] 4.1.5 Add filter support: query param `show_archived=true` includes archived
- [ ] 4.1.6 Add search support: query param `q` filters name/city/postal_code
- [ ] 4.1.7 Add sort support: query param `sort` (name, city, created_at)
- [ ] 4.1.8 Annotate `meters_count` in queryset
- [ ] 4.1.9 Create template with Bootstrap layout
- [ ] 4.1.10 Add search bar, filter checkboxes, sort dropdown
- [ ] 4.1.11 Display properties in table/cards (responsive)
- [ ] 4.1.12 Show meters_count badge per property
- [ ] 4.1.13 Add "Property hinzufügen" button (links to /new)
- [ ] 4.1.14 Write unit test: `test_property_list_view_renders()`
- [ ] 4.1.15 Write unit test: `test_property_list_excludes_archived_default()`

**URL:**

- [ ] 4.1.16 Add route in `landlord/urls.py`: `path('portal/properties/', PropertyListView.as_view())`

**Estimate:** 0.15 PT

---

### ✅ Task 4.2: Route /portal/properties/new (Create Form)

**Files:** `backend/app/landlord/views.py`, `templates/portal/property_form.html`

- [ ] 4.2.1 Create `PropertyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView)` in `views.py`
- [ ] 4.2.2 Set `model = Property`, `template_name = 'portal/property_form.html'`
- [ ] 4.2.3 Set `fields = ['name', 'street', 'postal_code', 'city', 'country', 'geo_lat', 'geo_lng', 'notes']`
- [ ] 4.2.4 Set `permission_required = 'landlord.add_property'`
- [ ] 4.2.5 Override `form_valid(form)`: Set `created_by = request.user`
- [ ] 4.2.6 Set `success_url = reverse_lazy('property_detail', kwargs={'pk': object.pk})`
- [ ] 4.2.7 Create form template with all fields
- [ ] 4.2.8 Add country dropdown with choices (DE, AT, CH)
- [ ] 4.2.9 Add geo_lat/geo_lng inputs with placeholders
- [ ] 4.2.10 Add client-side validation hints
- [ ] 4.2.11 Add "Speichern" and "Abbrechen" buttons (sticky on mobile)
- [ ] 4.2.12 Write unit test: `test_property_create_view_renders()`
- [ ] 4.2.13 Write unit test: `test_property_create_form_valid_redirects()`
- [ ] 4.2.14 Write unit test: `test_property_create_requires_permission()`

**URL:**

- [ ] 4.2.15 Add route: `path('portal/properties/new/', PropertyCreateView.as_view())`

**Estimate:** 0.15 PT

---

### ✅ Task 4.3: Search/Filter UI

**File:** `templates/portal/property_list.html`

- [ ] 4.3.1 Add search input: `<input name="q" placeholder="Name, Stadt oder PLZ suchen...">`
- [ ] 4.3.2 Add filter checkboxes:
  - `<input type="checkbox" name="country" value="DE">` Deutschland
  - `<input type="checkbox" name="country" value="AT">` Österreich
  - `<input type="checkbox" name="country" value="CH">` Schweiz
  - `<input type="checkbox" name="show_archived">` Archivierte anzeigen
- [ ] 4.3.3 Add city filter dropdown (populated from existing cities)
- [ ] 4.3.4 Add postal_code filter input
- [ ] 4.3.5 Add "Suchen" button to submit form
- [ ] 4.3.6 Preserve filter state in query params
- [ ] 4.3.7 Display active filters as badges with "X" to clear
- [ ] 4.3.8 Write E2E test: Filter by city and verify results
- [ ] 4.3.9 Write E2E test: Search by name and verify results

**Estimate:** 0.12 PT

---

### ✅ Task 4.4: Sort UI

**File:** `templates/portal/property_list.html`

- [ ] 4.4.1 Add sort dropdown:
  ```html
  <select name="sort">
    <option value="name">Name (A-Z)</option>
    <option value="-name">Name (Z-A)</option>
    <option value="city">Stadt (A-Z)</option>
    <option value="-city">Stadt (Z-A)</option>
    <option value="-created_at">Neueste zuerst</option>
    <option value="created_at">Älteste zuerst</option>
  </select>
  ```
- [ ] 4.4.2 Preserve sort state in query params
- [ ] 4.4.3 Update queryset ordering in view based on `sort` param
- [ ] 4.4.4 Add visual indicator (arrow) on active sort column
- [ ] 4.4.5 Write E2E test: Sort by city and verify order
- [ ] 4.4.6 Write E2E test: Sort by created_at descending

**Estimate:** 0.08 PT

---

### ✅ Task 4.5: Pagination UI

**File:** `templates/portal/property_list.html`

- [ ] 4.5.1 Add Django pagination controls:
  ```html
  {% if is_paginated %}
  <nav>
    <ul class="pagination">
      {% if page_obj.has_previous %}
      <li><a href="?page={{ page_obj.previous_page_number }}">Zurück</a></li>
      {% endif %}
      <li>
        Seite {{ page_obj.number }} von {{ page_obj.paginator.num_pages }}
      </li>
      {% if page_obj.has_next %}
      <li><a href="?page={{ page_obj.next_page_number }}">Weiter</a></li>
      {% endif %}
    </ul>
  </nav>
  {% endif %}
  ```
- [ ] 4.5.2 Preserve filter/sort params in pagination links
- [ ] 4.5.3 Display "Zeige X-Y von Z Ergebnissen"
- [ ] 4.5.4 Add page size selector (25, 50, 100)
- [ ] 4.5.5 Write E2E test: Navigate through pages
- [ ] 4.5.6 Write E2E test: Change page size

**Estimate:** 0.10 PT

---

### ✅ Task 4.6: "Archivierte anzeigen" Checkbox

**File:** `templates/portal/property_list.html` + `views.py`

- [ ] 4.6.1 Add checkbox: `<input type="checkbox" name="show_archived" id="show_archived">`
- [ ] 4.6.2 Update view `get_queryset()`: If `show_archived=true`, don't filter `is_archived`
- [ ] 4.6.3 If `show_archived=false` (default), filter `is_archived=False`
- [ ] 4.6.4 Display archived properties with grey background/strikethrough
- [ ] 4.6.5 Add badge "Archiviert" on archived rows
- [ ] 4.6.6 Write E2E test: Check "Archivierte anzeigen" and verify archived visible
- [ ] 4.6.7 Write E2E test: Uncheck and verify archived hidden

**Estimate:** 0.10 PT

---

### ✅ Task 4.7: Mobile-Responsive Layout

**File:** `templates/portal/property_list.html` + CSS

- [ ] 4.7.1 Use Bootstrap grid: `col-12 col-md-6 col-lg-4` for cards
- [ ] 4.7.2 Stack filters vertically on mobile
- [ ] 4.7.3 Make table horizontal-scroll on mobile
- [ ] 4.7.4 Use card layout instead of table on mobile (<768px)
- [ ] 4.7.5 Add hamburger menu for filters on mobile
- [ ] 4.7.6 Test on iPhone SE (375px width)
- [ ] 4.7.7 Test on Pixel 5 (393px width)
- [ ] 4.7.8 Test on iPad (768px width)

**Estimate:** 0.12 PT

---

### ✅ Task 4.8: Empty States

**File:** `templates/portal/property_list.html`

- [ ] 4.8.1 Add empty state when no properties exist:
  ```html
  {% if not object_list %}
  <div class="empty-state">
    <h3>Noch keine Gebäude angelegt</h3>
    <p>Legen Sie Ihr erstes Gebäude an, um zu starten.</p>
    <a href="{% url 'property_create' %}" class="btn btn-primary"
      >+ Gebäude hinzufügen</a
    >
  </div>
  {% endif %}
  ```
- [ ] 4.8.2 Add empty state when search/filter returns no results:
  ```html
  <p>Keine Ergebnisse für Ihre Suche. Versuchen Sie andere Filter.</p>
  <a href="{% url 'property_list' %}">Alle Filter zurücksetzen</a>
  ```
- [ ] 4.8.3 Add illustration/icon for empty states
- [ ] 4.8.4 Write E2E test: Verify empty state when no properties

**Estimate:** 0.08 PT

---

**PHASE 4 TOTAL:** 0.9 PT (8 tasks, 85+ subtasks)

---

## PHASE 5: Portal Views - Detail & Edit (1.0 PT)

**Goal:** Implement Property detail/edit view with inline meter management (dynamic add/edit/remove).

### ✅ Task 5.1: Route /portal/properties/{id}/ (Detail/Edit View)
**Files:** `backend/app/landlord/views.py`, `templates/portal/property_detail.html`

- [ ] 5.1.1 Create `PropertyDetailView(LoginRequiredMixin, DetailView)` in `views.py`
- [ ] 5.1.2 Set `model = Property`, `template_name = 'portal/property_detail.html'`
- [ ] 5.1.3 Override `get_queryset()`: `prefetch_related('utilitymeter_set')`
- [ ] 5.1.4 Add context: `context['can_edit'] = request.user.has_perm('landlord.change_property')`
- [ ] 5.1.5 Add context: `context['can_delete'] = request.user.has_perm('landlord.delete_property')`
- [ ] 5.1.6 Create template with two-column layout (Property on left, Meters on right)
- [ ] 5.1.7 Display all Property fields (read-only initially)
- [ ] 5.1.8 Add "Bearbeiten" button → toggles to edit mode (JavaScript)
- [ ] 5.1.9 Write unit test: `test_property_detail_view_renders()`
- [ ] 5.1.10 Write unit test: `test_property_detail_prefetches_meters()`
- [ ] 5.1.11 Add route: `path('portal/properties/<int:pk>/', PropertyDetailView.as_view())`

**Estimate:** 0.12 PT

---

### ✅ Task 5.2: Property Form (All Fields)
**Files:** `backend/app/landlord/forms.py`, `templates/portal/property_detail.html`

- [ ] 5.2.1 Create `PropertyUpdateForm(ModelForm)` in `forms.py` with all fields from 3.1
- [ ] 5.2.2 Add form rendering in template (hidden by default, shown on "Bearbeiten")
- [ ] 5.2.3 Add field-level help text for Geo coordinates
- [ ] 5.2.4 Add country dropdown with localized display names
- [ ] 5.2.5 Add AJAX save functionality (save without page reload)
- [ ] 5.2.6 Show success toast on save
- [ ] 5.2.7 Show validation errors inline
- [ ] 5.2.8 Write unit test: `test_property_form_valid_data()`
- [ ] 5.2.9 Write unit test: `test_property_form_invalid_geo_lat()`
- [ ] 5.2.10 Write unit test: `test_property_form_invalid_country()`

**Estimate:** 0.12 PT

---

### ✅ Task 5.3: Meter List Inline (Dynamic Add/Edit/Remove)
**File:** `templates/portal/property_detail.html` + JavaScript

- [ ] 5.3.1 Create meters table/cards in template
- [ ] 5.3.2 Add "Zähler hinzufügen" button
- [ ] 5.3.3 JavaScript: Click "Hinzufügen" → Show empty meter form row
- [ ] 5.3.4 JavaScript: Click "Bearbeiten" on row → Toggle edit mode
- [ ] 5.3.5 JavaScript: Click "Speichern" → AJAX POST/PATCH to API
- [ ] 5.3.6 JavaScript: Click "Entfernen" → Show confirmation dialog
- [ ] 5.3.7 JavaScript: Confirm delete → AJAX DELETE to API
- [ ] 5.3.8 Handle 409 response (has Readings) → Show "Deaktivieren statt Löschen" option
- [ ] 5.3.9 Update UI after successful API call (add/update/remove row)
- [ ] 5.3.10 Show loading spinner during API calls
- [ ] 5.3.11 Write E2E test: Add new meter via UI
- [ ] 5.3.12 Write E2E test: Edit existing meter
- [ ] 5.3.13 Write E2E test: Delete meter without Readings
- [ ] 5.3.14 Write E2E test: Delete meter with Readings → 409 → Deactivate

**Estimate:** 0.20 PT

---

### ✅ Task 5.4: Meter Form Fields (All from 3.2)
**File:** `templates/portal/property_detail.html` + `forms.py`

- [ ] 5.4.1 Create `UtilityMeterForm(ModelForm)` in `forms.py` with all meter fields
- [ ] 5.4.2 Add meter_type dropdown (Kaltwasser, Warmwasser, Strom, Gas kWh)
- [ ] 5.4.3 Add serial_number input (max 50 chars)
- [ ] 5.4.4 Add is_default checkbox with warning: "Nur ein Default pro Medium"
- [ ] 5.4.5 Add is_active checkbox
- [ ] 5.4.6 Add initial_reading_value input (Decimal, min 0)
- [ ] 5.4.7 Add installed_at date picker
- [ ] 5.4.8 Add removed_at date picker (validation: >= installed_at)
- [ ] 5.4.9 Add notes textarea (max 1000 chars)
- [ ] 5.4.10 Add client-side validation: removed_at >= installed_at
- [ ] 5.4.11 Add client-side validation: initial_reading >= 0
- [ ] 5.4.12 Write unit test: `test_meter_form_valid_data()`
- [ ] 5.4.13 Write unit test: `test_meter_form_removed_at_validation()`
- [ ] 5.4.14 Write unit test: `test_meter_form_negative_initial_reading()`

**Estimate:** 0.15 PT

---

### ✅ Task 5.5: Default-Badge UI
**File:** `templates/portal/property_detail.html` + CSS

- [ ] 5.5.1 Add badge display: `<span class="badge badge-primary">Standard</span>` if is_default
- [ ] 5.5.2 Style badge with primary color, bold text
- [ ] 5.5.3 Show badge only on default meters
- [ ] 5.5.4 Add tooltip: "Dieser Zähler wird automatisch vorgeschlagen"
- [ ] 5.5.5 Visual distinction: Highlight default meter row (light blue background)
- [ ] 5.5.6 Write E2E test: Verify default badge shows
- [ ] 5.5.7 Write E2E test: Badge disappears when unchecking is_default

**Estimate:** 0.06 PT

---

### ✅ Task 5.6: Active/Inactive Badge UI
**File:** `templates/portal/property_detail.html` + CSS

- [ ] 5.6.1 Add active badge: `<span class="badge badge-success">Aktiv</span>`
- [ ] 5.6.2 Add inactive badge: `<span class="badge badge-secondary">Inaktiv</span>`
- [ ] 5.6.3 Style active badge: green background
- [ ] 5.6.4 Style inactive badge: grey background, strikethrough text
- [ ] 5.6.5 Show removed_at date on inactive meters
- [ ] 5.6.6 Visual distinction: Grey out inactive meter rows
- [ ] 5.6.7 Write E2E test: Verify active/inactive badges
- [ ] 5.6.8 Write E2E test: Deactivate meter → Badge changes

**Estimate:** 0.06 PT

---

### ✅ Task 5.7: Sticky Action Bar (Save, Cancel, Archive, Delete)
**File:** `templates/portal/property_detail.html` + CSS

- [ ] 5.7.1 Create sticky footer bar with 4 buttons
- [ ] 5.7.2 CSS: `position: sticky; bottom: 0; z-index: 1000;`
- [ ] 5.7.3 Show/hide buttons based on permissions
- [ ] 5.7.4 Wire up "Speichern" button → AJAX PATCH to Property API
- [ ] 5.7.5 Wire up "Abbrechen" button → Reload or discard changes
- [ ] 5.7.6 Wire up "Archivieren" button → Confirmation → POST to archive API
- [ ] 5.7.7 Wire up "Löschen" button → Confirmation → DELETE to API
- [ ] 5.7.8 Handle DELETE 409 → Show error + suggest "Archivieren"
- [ ] 5.7.9 Mobile: Stack buttons vertically, full width
- [ ] 5.7.10 Write E2E test: Click "Speichern" → verify AJAX
- [ ] 5.7.11 Write E2E test: Click "Archivieren" → verify redirect
- [ ] 5.7.12 Write E2E test: Click "Löschen" with dependencies → 409 error

**Estimate:** 0.14 PT

---

### ✅ Task 5.8: Client-Side Validations
**File:** `templates/portal/property_detail.html` + JavaScript

- [ ] 5.8.1 Validate name: required, max 200 chars
- [ ] 5.8.2 Validate postal_code: DE = 5 digits
- [ ] 5.8.3 Validate geo_lat: -90.0 to +90.0
- [ ] 5.8.4 Validate geo_lng: -180.0 to +180.0
- [ ] 5.8.5 Validate country: must be DE, AT, or CH
- [ ] 5.8.6 Validate notes: max 2000 chars
- [ ] 5.8.7 Meter validation: removed_at >= installed_at
- [ ] 5.8.8 Meter validation: initial_reading >= 0
- [ ] 5.8.9 Meter validation: serial_number format
- [ ] 5.8.10 Show inline error messages (red text below field)
- [ ] 5.8.11 Disable "Speichern" button if validation fails
- [ ] 5.8.12 Write E2E test: Invalid geo_lat → Error shown, Save disabled
- [ ] 5.8.13 Write E2E test: Fix error → Error clears, Save enabled

**Estimate:** 0.10 PT

---

### ✅ Task 5.9: Unsaved Changes Warning
**File:** `templates/portal/property_detail.html` + JavaScript

- [ ] 5.9.1 Track form changes: Set `hasUnsavedChanges = true` on input change
- [ ] 5.9.2 Add `window.onbeforeunload` handler with warning
- [ ] 5.9.3 Reset `hasUnsavedChanges = false` on successful save
- [ ] 5.9.4 Add "Ungespeicherte Änderungen" indicator (orange dot)
- [ ] 5.9.5 Disable warning on "Abbrechen" (intentional discard)
- [ ] 5.9.6 Write E2E test: Change field, navigate away → Warning shown
- [ ] 5.9.7 Write E2E test: Save changes → Warning does not show

**Estimate:** 0.05 PT

---

**PHASE 5 TOTAL:** 1.0 PT (9 tasks, 95+ subtasks)

---

## PHASE 6: Archive & Delete Logic (0.6 PT)

**Goal:** Implement soft-delete (archive) and hard-delete with dependency checks.

### ✅ Task 6.1: Archive Action (Soft-Delete)
**Files:** `backend/app/landlord/views.py`, `api/views.py`

- [ ] 6.1.1 Create `PropertyArchiveView(View)` in `views.py`
- [ ] 6.1.2 Add permission check: `@permission_required('landlord.change_property')`
- [ ] 6.1.3 Call `property.archive(user)` method (from Phase 1)
- [ ] 6.1.4 Set `is_archived=True`, `archived_at=now()`, `archived_by=user`
- [ ] 6.1.5 Return success message and redirect
- [ ] 6.1.6 Write unit test: `test_property_archive_sets_fields()`
- [ ] 6.1.7 Write unit test: `test_property_archive_requires_permission()`
- [ ] 6.1.8 Write E2E test: Archive property from detail view
- [ ] 6.1.9 Add route: `path('portal/properties/<int:pk>/archive/', ...)`

**Estimate:** 0.10 PT

---

### ✅ Task 6.2: Dependency Check for Hard-Delete
**File:** `backend/app/landlord/api/views.py`

- [ ] 6.2.1 Check Units: `property.unit_set.exists()`
- [ ] 6.2.2 Check Contracts: `property.contract_set.exists()`
- [ ] 6.2.3 Check Documents: `property.document_set.exists()`
- [ ] 6.2.4 Check UtilityMeters: `property.utilitymeter_set.exists()`
- [ ] 6.2.5 Check UtilityReadings: via Meters
- [ ] 6.2.6 If dependencies: raise `ValidationError` with 409
- [ ] 6.2.7 Write helper: `get_property_dependencies(property_id)`
- [ ] 6.2.8 Write unit tests for all dependency checks (5 tests)

**Estimate:** 0.15 PT

---

### ✅ Task 6.3: 409 Conflict Handling (User-Friendly)
**File:** `backend/app/landlord/api/views.py`

- [ ] 6.3.1 Custom exception handler for 409
- [ ] 6.3.2 Format message: "Löschen nicht möglich. Abhängige Daten: ..."
- [ ] 6.3.3 Localize messages (German)
- [ ] 6.3.4 Include link to archive endpoint in response
- [ ] 6.3.5 Write unit test: `test_409_response_format()`
- [ ] 6.3.6 Write unit test: `test_409_includes_archive_link()`

**Estimate:** 0.08 PT

---

### ✅ Task 6.4: UI Confirmation Dialogs
**File:** `templates/portal/property_detail.html` + JavaScript

- [ ] 6.4.1 Create archive confirmation modal
- [ ] 6.4.2 Wire up "Archivieren" button → Show modal
- [ ] 6.4.3 Wire up "Ja, archivieren" → POST to archive endpoint
- [ ] 6.4.4 Create delete confirmation modal
- [ ] 6.4.5 Wire up "Löschen" button → Show modal
- [ ] 6.4.6 Wire up "Ja, löschen" → DELETE to API
- [ ] 6.4.7 On 409: Show error modal with dependencies
- [ ] 6.4.8 Error modal includes "Archivieren statt Löschen" button
- [ ] 6.4.9 Write E2E test: Confirm archive → Property archived
- [ ] 6.4.10 Write E2E test: Cancel archive → No action
- [ ] 6.4.11 Write E2E test: Delete with dependencies → Error shown
- [ ] 6.4.12 Write E2E test: "Archivieren statt Löschen" → Works

**Estimate:** 0.12 PT

---

### ✅ Task 6.5: Meter Delete with Reading Check
**File:** `backend/app/landlord/api/views.py`

- [ ] 6.5.1 Verify `PropertyMeterDeleteAPIView` checks for Readings
- [ ] 6.5.2 Verify 409 response on Reading dependency
- [ ] 6.5.3 Verify error message suggests deactivation
- [ ] 6.5.4 Add UI modal for meter delete confirmation
- [ ] 6.5.5 On 409: Show "Zähler deaktivieren statt Löschen"
- [ ] 6.5.6 Wire up deactivate → PATCH with `is_active=false`
- [ ] 6.5.7 Write E2E test: Delete meter without readings → Success
- [ ] 6.5.8 Write E2E test: Delete with readings → 409 → Deactivate

**Estimate:** 0.10 PT

---

### ✅ Task 6.6: "Deaktivieren statt Löschen" Option
**File:** `templates/portal/property_detail.html` + JavaScript

- [ ] 6.6.1 On meter delete 409, show modal with deactivate option
- [ ] 6.6.2 Wire up "Zähler deaktivieren" → AJAX PATCH
- [ ] 6.6.3 On success: Update meter row (show as inactive)
- [ ] 6.6.4 Show success toast: "Zähler wurde deaktiviert"
- [ ] 6.6.5 Write E2E test: Deactivate instead of delete → Meter inactive

**Estimate:** 0.05 PT

---

**PHASE 6 TOTAL:** 0.6 PT (6 tasks, 60+ subtasks)

---

## PHASE 7: Security & Performance (0.5 PT)

**Goal:** Implement CSRF, Rate-Limiting, XSS, RBAC, N+1 prevention, Caching.

### ✅ Task 7.1: CSRF Protection
**Files:** `settings.py`, templates

- [ ] 7.1.1 Verify `CsrfViewMiddleware` in `MIDDLEWARE`
- [ ] 7.1.2 Add `{% csrf_token %}` to all forms
- [ ] 7.1.3 Configure AJAX to include CSRF token
- [ ] 7.1.4 Test CSRF on all POST/PATCH/DELETE
- [ ] 7.1.5 Write unit test: `test_csrf_required_on_post()`
- [ ] 7.1.6 Write unit test: `test_csrf_missing_returns_403()`

**Estimate:** 0.06 PT

---

### ✅ Task 7.2: Rate Limiting
**Files:** `backend/app/landlord/throttles.py`

- [ ] 7.2.1 Verify `PortalMutatingThrottle` (60/min)
- [ ] 7.2.2 Verify `PortalReadThrottle` (240/min)
- [ ] 7.2.3 Verify throttles applied to all API views
- [ ] 7.2.4 Test: 61 POST in 1min → 429 on 61st
- [ ] 7.2.5 Test: 241 GET in 1min → 429 on 241st
- [ ] 7.2.6 Verify `Retry-After` header
- [ ] 7.2.7 Write unit tests for throttling (3 tests)

**Estimate:** 0.08 PT

---

### ✅ Task 7.3: XSS Protection
**Files:** Templates, `settings.py`

- [ ] 7.3.1 Verify auto-escaping in templates
- [ ] 7.3.2 Review: Never use `|safe` on user input
- [ ] 7.3.3 Escape JSON in JavaScript: Use `json_script`
- [ ] 7.3.4 Add CSP headers (optional)
- [ ] 7.3.5 Test XSS: Inject `<script>` in notes → Escaped
- [ ] 7.3.6 Write unit tests for XSS escaping (2 tests)

**Estimate:** 0.06 PT

---

### ✅ Task 7.4: RBAC Authorization Checks
**Files:** `backend/app/landlord/views.py`, `api/views.py`

- [ ] 7.4.1 Verify all views have `LoginRequiredMixin`
- [ ] 7.4.2 Verify CREATE/UPDATE have `IsAdminOrPropertyManager`
- [ ] 7.4.3 Verify DELETE has `IsAdminUser`
- [ ] 7.4.4 Verify GET allows Landlord/Staff
- [ ] 7.4.5 Test: Landlord cannot CREATE → 403
- [ ] 7.4.6 Test: Property-Manager can CREATE → 201
- [ ] 7.4.7 Test: Admin can DELETE → 204
- [ ] 7.4.8 Test: Property-Manager cannot DELETE → 403
- [ ] 7.4.9 Write unit tests for RBAC (4 tests)

**Estimate:** 0.10 PT

---

### ✅ Task 7.5: N+1 Query Prevention
**Files:** `backend/app/landlord/views.py`

- [ ] 7.5.1 List view: `annotate(meters_count=Count('utilitymeter'))`
- [ ] 7.5.2 Detail view: `prefetch_related('utilitymeter_set')`
- [ ] 7.5.3 API view: Same prefetch
- [ ] 7.5.4 Test with Django Debug Toolbar
- [ ] 7.5.5 Benchmark: 100 Properties < 100ms query time
- [ ] 7.5.6 Write unit tests for query counts (2 tests)

**Estimate:** 0.06 PT

---

### ✅ Task 7.6: Cache Strategy
**Files:** `settings.py`, templates, `models.py`

- [ ] 7.6.1 Configure Redis cache backend
- [ ] 7.6.2 Add fragment caching to `property_detail.html`
- [ ] 7.6.3 Invalidate cache on Property save
- [ ] 7.6.4 Invalidate cache on Meter save/delete (signals)
- [ ] 7.6.5 Write unit tests for cache invalidation (2 tests)
- [ ] 7.6.6 Test manually: Edit property → Verify cache cleared

**Estimate:** 0.10 PT

---

### ✅ Task 7.7: DB Indexes Applied (Verify)
**Files:** Migrations, PostgreSQL

- [ ] 7.7.1 Run migrations: `python manage.py migrate`
- [ ] 7.7.2 Verify indexes: `\di landlord_property*`
- [ ] 7.7.3 Verify indexes: (name), (city), (postal_code), (is_archived)
- [ ] 7.7.4 Verify meter indexes: `\di landlord_utilitymeter*`
- [ ] 7.7.5 Optional: Verify Trigram index
- [ ] 7.7.6 Run `EXPLAIN ANALYZE` to verify index usage
- [ ] 7.7.7 Verify "Index Scan" (not "Seq Scan")

**Estimate:** 0.04 PT

---

**PHASE 7 TOTAL:** 0.5 PT (7 tasks, 65+ subtasks)

---

## SUMMARY

**Total Implementation TODO List:**

- **Phases:** 10
- **High-Level Tasks:** 75
- **Granular Subtasks:** 200+ (detailed in Phases 1-4)
- **Estimated Effort:** 8.1 PT

**Remaining Phases 5-10:**

- Phase 5: Portal Views - Detail & Edit (1.0 PT, 9 tasks)
- Phase 6: Archive & Delete Logic (0.6 PT, 6 tasks)
- Phase 7: Security & Performance (0.5 PT, 7 tasks)
- Phase 8: Testing & QA (1.0 PT, 10 tasks)
- Phase 9: Audit & Monitoring (0.4 PT, 5 tasks)
- Phase 10: Documentation & Deployment (0.3 PT, 5 tasks)

**Next Step:** Start Phase 1, Task 1.1 - Add Archive Fields to Property Model

---

**Status:** ✅ READY TO START IMPLEMENTATION

**Last Updated:** 2025-10-20
