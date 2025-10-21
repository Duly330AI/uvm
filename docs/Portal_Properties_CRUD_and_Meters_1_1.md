# Portal Properties CRUD & Meter Management – Implementation Snapshot (v1.3)

**Last reviewed:** 2025-10-21  
**Status:** ✅ Shipped in repo (see references below)

This document replaces the legacy planning notes (archived under `docs/Archiv/Portal_Properties_CRUD_and_Meters_1_1_legacy.md`) and captures the behaviour that is implemented in code today.

---

## 1. Feature Snapshot

- Property CRUD (list/detail/create/update/delete) with soft-archive support (`backend/app/landlord/models.py:44`).
- Nested utility meter management for building scopes, including transactional default handling and delete safeguards (`backend/app/landlord/api/meters.py`).
- Portal UI for property and meter management under `/portal/properties/...` (`backend/app/config/urls.py:120`).
- REST API under `/api/portal/properties/...` secured with `IsAuthenticated`/`IsAdminUser` and DRF throttles (`backend/app/landlord/api/properties.py`).
- Country whitelist (DE/AT/CH) and geo coordinate constraints at the database level (`backend/app/landlord/models.py:58`).

---

## 2. Data Model Essentials

### Property (`backend/app/landlord/models.py:30`)

- `name`: optional `CharField(max_length=200)`; UI treats it as recommended but not required.
- `street`, `postal_code`, `city`: required core address fields (`postal_code` allows up to 20 characters; no country-specific format enforcement yet).
- `country`: two-letter code with validator `validate_country_whitelist` (DE/AT/CH).
- `geo_lat` / `geo_lng`: optional `DecimalField(9,6)` guarded by DB check constraints (`property_geo_lat_valid_range`, `property_geo_lng_valid_range`).
- Archive fields: `is_archived`, `archived_at`, `archived_by` plus `archive(user)` helper (`backend/app/landlord/models.py:68`).
- Index coverage for frequent lookups on name, city, postal code, archive flag (`backend/app/landlord/models.py:88`).

### UtilityMeter (`backend/app/landlord/models.py:835`)

- Scope-aware via `scope_type` (`property` or `unit`) with mutually exclusive FK usage enforced by `utility_meter_scope_consistency` check constraint.
- Serial numbers are normalised to uppercase inside `UtilityMeter.save()` and validated via `validate_serial_number_format`.
- Partial unique constraints guarantee at most one default per `(scope_type, property/unit, meter_type)` (`unique_default_meter_property` / `_unit`).
- Optional lifecycle fields: `initial_reading_value`, `installed_at`, `removed_at`; `removed_at` is auto-populated when a meter is deactivated through the API (`backend/app/landlord/api/meters.py:88`).

_Unit-scoped meter details are documented separately in `docs/Portal_Units_CRUD_and_Meters_1_0.md`._

---

## 3. API Surface (`backend/app/landlord/api/urls.py:23`)

Base prefix: `/api/portal/properties/…`

| Endpoint | View | Auth | Throttle |
| --- | --- | --- | --- |
| `GET /` | `PropertyListAPIView` | `IsAuthenticated` | `PortalReadThrottle (100/hour)` |
| `POST /create/` | `PropertyCreateAPIView` | `IsAdminUser` | `PortalWriteThrottle (50/hour)` |
| `GET /{id}/` | `PropertyDetailAPIView` | `IsAuthenticated` | `PortalReadThrottle` |
| `PUT/PATCH /{id}/update/` | `PropertyUpdateAPIView` | `IsAdminUser` | `PortalWriteThrottle` |
| `DELETE /{id}/delete/` | `PropertyDeleteAPIView` | `IsAdminUser` | `PortalWriteThrottle` |
| `POST /{id}/archive/` | `PropertyArchiveAPIView` | `IsAdminUser` | `PortalWriteThrottle` |
| `POST /{id}/unarchive/` | `PropertyUnarchiveAPIView` | `IsAdminUser` | `PortalWriteThrottle` |

Nested utility meter endpoints (property scope): `/api/portal/properties/{property_id}/meters/...` handled by `PropertyMeter*APIView` classes. Deletion is blocked with a `ValidationError` if unit meter readings exist; property-level meters can always be removed (no readings yet).

Response serialisation is implemented in `backend/app/landlord/api/properties_serializers.py`.

---

## 4. Portal UI (`backend/app/config/urls.py:120`)

- `GET /portal/properties/` – list view with filtering, search, archive toggle.
- `GET|POST /portal/properties/new` – creation form (property choices limited to active records).
- `GET /portal/properties/{id}/` – detail page exposing meter list.
- `GET|POST /portal/properties/{id}/edit` – update form.
- `GET|POST /portal/properties/{property_id}/meters/{pk?}/(new|edit)` – building meter CRUD views backed by the same business rules as the API (`backend/app/landlord/views.py:320`).

Each form hides archived properties from dropdowns and mirrors the server-side validation for default meters.

---

## 5. Business Rules & Validation

- **Default-meter handling:** Setting `is_default=True` clears other defaults for the same medium & scope inside a DB transaction (`backend/app/landlord/api/meters.py:59`).
- **Serial numbers:** Trimmed and uppercased automatically in `UtilityMeter.save()` to guarantee consistent comparisons (`backend/app/landlord/models.py:970`).
- **Archive propagation:** API & list views exclude archived properties by default; clients can opt-in via `?is_archived=true` (see `PropertyListAPIView.get_queryset()`).
- **Postal code:** No automatic country-specific validation yet despite helper `validate_postal_code_de`. If stricter handling is needed, wire it into serializers.
- **Meter removal:** Unit meters with attached readings raise a 409-equivalent DRF validation error, encouraging deactivation instead of deletion.

---

## 6. Rate Limiting & Permissions

- DRF throttles are defined inline (`PortalReadThrottle`, `PortalWriteThrottle`) with static hourly limits and default `UserRateThrottle.get_ident` behaviour.
- Permissions: read endpoints require authenticated landlord/staff users; mutating endpoints are limited to admins via `IsAdminUser`.

---

## 7. Test Coverage

- Model tests: `backend/app/landlord/tests/test_property_model_extended.py`, `test_utility_meter_model.py`, `test_utility_meter_model_phase1.py`.
- API tests: `backend/app/landlord/tests/test_property_api_phase2.py`, `test_utility_meter_api.py`.
- Service/caching: `backend/app/landlord/tests/test_utility_meter_cache.py`.
- Portal views are exercised indirectly through integration tests where applicable; see `tests/test_chat_acceptance.py` for portal auth scaffolding.

All listed suites pass under `pytest` with `DJANGO_SETTINGS_MODULE=config.settings.dev`.

---

## 8. Outstanding Follow-Ups

- Publish end-user documentation for property management flows (placeholder referenced in legacy TODO lives at `docs/user_guide/property_management.md` but file is missing).
- Decide if the optional `validate_postal_code_de` should be enforced in serializers to catch malformed German ZIP codes.
- Monitor API rate limits once deployed behind a proxy; adjust if the hourly caps prove too strict.

---

## 9. Related Documents

- Units module: `docs/Portal_Units_CRUD_and_Meters_1_0.md`
- Default meter prefill: `docs/Utility_Readings_Default_Meter_Prefill_1_2.md`
- Security posture: `docs/Security_Fixes_2025_10_20.md`

