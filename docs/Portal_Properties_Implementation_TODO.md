# Portal Properties – Follow-up Checklist (Post v1.3)

**Document purpose:** Track the remaining work after the property CRUD + meter module shipped on 2025-10-21.  
**Primary reference:** `docs/Portal_Properties_CRUD_and_Meters_1_1.md`

---

## ✅ Delivered (reference only)

- Models, migrations, and archive helpers (`backend/app/landlord/models.py`).
- REST API and nested meter endpoints (`backend/app/landlord/api/properties.py`, `api/meters.py`).
- Portal UI screens and meter forms (`backend/app/landlord/views.py`).
- Automated coverage (see `backend/app/landlord/tests/test_property_api_phase2.py`, `test_utility_meter_api.py`, `test_property_model_extended.py`).

No additional tracking needed for the shipped scope; the legacy mega-checklist now lives in `docs/Archiv/Portal_Properties_Implementation_TODO_legacy.md` for historical context.

---

## 📌 Open Items

1. **End-user documentation**
   - Create a focussed guide under `docs/user_guide/` (currently missing) that covers the portal flows: create/edit property, manage meters, archive/unarchive.

2. **Postal code validation decision**
   - `backend/app/landlord/validators.py` exposes `validate_postal_code_de`, but serializers do not call it yet.  
   - Decide whether to enforce German 5-digit ZIP codes or keep the current permissive approach for multi-country support.

3. **Meter delete UX parity**
   - The API blocks deletion when readings exist and asks users to deactivate instead.  
   - Confirm the portal templates surface the same guidance (add toast/inline copy if missing).

4. **Monitoring hooks**
   - Once deployed, capture rate-limit metrics for `/api/portal/properties/*` to verify that the 100/hour / 50/hour defaults are appropriate.  
   - Update `docs/Portal_Properties_CRUD_and_Meters_1_1.md` if thresholds are adjusted.

---

## 🧭 Nice-to-have Ideas

- Add property-level audit logging (archive/unarchive, meter default changes) if regulatory requirements demand it.
- Evaluate whether a trigram index (`gin_trgm_ops`) on `Property.name` is needed once the dataset grows past ~10k records.

---

_Last updated by CODEx assistant on 2025-10-21_
