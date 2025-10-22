# Code Complexity Analysis Report

**Scan Date:** 2025-10-22  
**Scope:** `backend/app/landlord`, `backend/app/config`  
**Tooling:** Radon 6.0.1 (`radon cc`, `radon mi`)

## 🔴 Critical (refactor immediately)

- **ChatFSM.next** – `backend/app/landlord/fsm.py:24` (Cyclomatic Complexity **F / 46**)  
  - *Symptoms:* 11 sequential state branches, repeated heuristics for category derivation, inline validation, and multiple early returns make the finite-state machine hard to extend and reason about. A single change to state ordering risks regressions because invariants are implicit.  
  - *Action (6h):* Refactor to a dictionary of per-state handler functions returning `(next_state, prompt, delta, warnings)` to isolate validation logic. Extract category keyword detection into a helper shared by `GREETING` and `CAPTURE_SUMMARY`. Cover each transition with unit tests (`tests/services/test_chat_fsm.py`) capturing edge states and validation errors.
    ```python
    STATE_HANDLERS = {
        "GREETING": handle_greeting,
        "CAPTURE_SUMMARY": handle_summary,
        # ...
    }

    def next(self, state, message, payload):
        try:
            handler = STATE_HANDLERS[state]
        except KeyError:
            raise ValueError("VALIDATION:state:unknown")
        return handler(message, payload)
    ```

- **ChatMessageView.post** – `backend/app/landlord/views.py:163` (Cyclomatic Complexity **E / 40**)  
  - *Symptoms:* Performs throttling, optimistic locking, state mismatch detection, serializer orchestration, manual payload merging, and exception translation in one 120+ line method. The current structure mixes HTTP concerns with FSM domain rules; adding a new state currently requires touching four separate `if` ladders.  
  - *Action (5h):* Split into targeted helpers (`_guard_state_transition`, `_build_payload`, `_call_message_service`) and use a DRF serializer for CAS/version checks. Move the repeated STATE_MISMATCH checks into a reusable validator tied to `ChatMessageSerializer`. Add regression tests around `STATE_VERSION_CONFLICT`, invalid transitions, and burst throttling (`tests/views/test_chat_message_view.py`).

## 🟡 Medium (prioritize before release)

- **IssuesAdminListView.get_queryset** – `backend/app/landlord/api/issues.py:30` (Cyclomatic Complexity **C / 20**)  
  - *Symptoms:* Performs 10 independent filter branches, search, date parsing, and ordering sanitisation inline, leading to nested `if` blocks and duplicated parsing code.  
  - *Action (3h):* Introduce a `IssueListFilterSet` via `django-filter` or break filtering into composable helpers (e.g., `_filter_by_status(qs, params)`). Unit-test each filter to prevent regressions and document accepted query params.

- **UtilityMeterService.get_default_meter** – `backend/app/landlord/services/utility_meter_service.py:32` (Cyclomatic Complexity **C / 19**)  
  - *Symptoms:* Branch-heavy logic with repeated cache writes and near-identical result dictionaries for each case. Hard to extend for new meter types or caching tweaks.  
  - *Action (4h):* Factor case evaluation into strategy functions (`_result_for_default`, `_result_for_single_active`, `_result_for_multiple`) and centralise cache reads/writes. Return a dataclass for clarity and add unit tests covering property and unit scopes.

- **ChatMessageSerializer.validate** – `backend/app/landlord/serializers.py:40` (Cyclomatic Complexity **C / 15**)  
  - *Symptoms:* Encodes per-state validation through a sequence of `if state == ...` branches, duplicating FSM checks and regex compilation on every request.  
  - *Action (2h):* Move per-state validators into dedicated methods (e.g., `validate_capture_location`) and precompile regex patterns at module load. Couple serializer and FSM by sharing a validation registry so each state declares required fields in one place.

- **chat_session.confirm workflow** – `backend/app/landlord/services/chat_session.py:44` (length ~130 lines)  
  - *Symptoms:* Single function performs transactional locking, idempotency handling, issue creation, ticket sequencing, file I/O, and payload cleanup. Difficult to test, and I/O errors inside the transaction can hold locks unnecessarily.  
  - *Action (5h):* Split into (1) `fetch_or_lock_session`, (2) `create_issue_from_payload`, (3) `finalise_staged_files`. Wrap file-copying outside the main transaction and guard with try/finally to ensure tmp files are deleted even on failure. Add unit tests plus a temporary storage backend fixture.

- **Duplicated UnitMeter validation** – `backend/app/landlord/views.py:604` & `backend/app/landlord/views.py:649`  
  - *Symptoms:* `UnitMeterCreateView.form_valid` and `UnitMeterUpdateView.form_valid` contain nearly identical logic ensuring a single default meter per scope.  
  - *Action (1h):* Extract a shared validator (e.g., `validate_single_default(form.instance)`) into `utility_meter_service.py` or a mixin to reduce copy/paste and keep validation consistent.

## 🟢 Low (opportunistic clean-up)

- **Tenant onboarding views** – `backend/app/landlord/views_portal.py:204` & `backend/app/landlord/views_portal.py:228`  
  - *Observation:* `tenant_create` and `tenant_edit` manually mirror field handling and unit list retrieval. Use a `ModelForm` or shared helper to reduce maintenance burden and enable form-level validation.

- **Category keyword heuristics** – repeated in `ChatFSM.next` for both `GREETING` and `CAPTURE_SUMMARY`. Move into a helper and centralise keywords to prevent divergence when categories evolve.

- **Result dict construction** – `UtilityMeterService.get_default_meter` rebuilds the same dictionaries across branches; replace with a dataclass or factory to keep structure consistent and make future fields (e.g., `meter_readings`) easier to add.

## Metrics Snapshot

| Metric | Result |
| --- | --- |
| Files analysed | 58 |
| Functions/methods graded C or worse | 24 |
| Highest CC score | `ChatFSM.next` — 46 (grade F) |
| Maintainability Index | All inspected modules scored **A** |

## Follow-Up

- Implement refactor spikes for the two critical hotspots, accompanied by unit tests around edge transitions and throttling conflicts.  
- Adopt `django-filter` (or equivalent helper pattern) for API list views to guard against future parameter creep.  
- Schedule a focused review of `chat_session.confirm` after breaking out file I/O to ensure transactional semantics are preserved.  
- After changes, rerun `radon cc -s landlord config --exclude '*/migrations/*,*/tests/*'` and capture the before/after metrics in `docs/code_quality_metrics.md` for audit traceability.
