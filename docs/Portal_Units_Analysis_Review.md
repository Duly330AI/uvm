# Portal Units CRUD – Implementation Review (2025-10-21)

**Reviewer:** AI Code-Analyst  
**Spec under test:** `docs/Portal_Units_CRUD_and_Meters_1_0.md`

---

## 1. Summary

- ✅ The shipped code matches the v1.0 spec for unit CRUD and nested meter management.
- ✅ Previously identified gaps (archive fields, validators, throttles) were implemented before merge.
- ⚠️ Follow-up items are limited to documentation polish and monitoring.

---

## 2. Verified Alignment

| Area | Spec expectation | Implementation evidence |
| --- | --- | --- |
| Unit archiving | `is_archived`, `archived_at`, `archived_by` and `archive(user)` helper | `backend/app/landlord/models.py:148`, migration `0024_unit_archive_fields_phase1.py` |
| Validators | `area_sqm` ≥ 0 | `backend/app/landlord/models.py:131` |
| Portal views & templates | List/detail/create/edit + meter forms | `backend/app/landlord/views.py:457`, `backend/app/config/urls.py:157` |
| API endpoints | `/api/portal/units/...` + nested `/meters` | `backend/app/landlord/api/urls.py:41`, `api/units.py`, `api/unit_meters.py` |
| Rate limiting | 100/h read, 50/h write | `PortalReadThrottle` / `PortalWriteThrottle` in `backend/app/landlord/api/units.py` |
| Meter rules | One default per unit+medium, 409 on delete with readings | DB constraints + logic in `api/unit_meters.py:120` |

---

## 3. Test Coverage

- `backend/app/landlord/tests/test_unit_model.py`
- `backend/app/landlord/tests/test_unit_api.py`
- `backend/app/landlord/tests/test_unit_meter_api.py`
- Shared meter service tests: `backend/app/landlord/tests/test_utility_meter_service.py`

All suites pass with `pytest` (dev settings).

---

## 4. Outstanding Follow-ups

1. **Docs:** Extend the new property portal user guide to include unit workflows once the document exists.
2. **UI copy:** Ensure meter deletion warnings in the portal mirror the API guidance (suggest deactivation when readings exist).
3. **Monitoring:** Add dashboards for the unit API throttles after deployment to confirm the hourly caps are sufficient.

---

_Legacy review notes are archived at `docs/Archiv/Portal_Units_Analysis_Review_legacy.md` for historical reference._
