---
phase: 150-consolidate-write-path
plan: 03
subsystem: api
tags: [sqlalchemy-async, eval-pipeline, refactor, completion-decision, classify-preamble]

requires:
  - phase: 150-consolidate-write-path (plan 01)
    provides: golden equivalence test (tests/services/test_flaw_upsert_equivalence.py) used as the safety net for this plan's R4 change
provides:
  - "apply_completion_decision(write_session, *, game_id, job_id, failed_ply_count, current_attempts, source, on_path_c_capacity_reached) -> bool — single Path A/B/C completion decision + guarded eval_jobs stamp, called by both _full_drain_tick and _apply_atomic_submit"
  - "_classify_with_overlay(game_id, session, *, overlay, pos_eval=None) -> list[FlawRecord] | None — single classify-preamble helper (load Game + GamePosition, optional in-memory post-move overlay, classify_game_flaws), called by all 4 R4 sites"
affects: [150-04, 150-05]

tech-stack:
  added: []
  patterns:
    - "Injectable Path-C reporting callback (on_path_c_capacity_reached: Callable[[int, int, int, str], None]) — lets two call sites keep deliberately different observability mechanisms (logger.warning vs sentry_sdk.capture_message) behind one shared decision function, instead of forcing a false unification"
    - "overlay: bool parameter distinguishing a 'DB genuinely has NULL, fill it' preamble from a 'DB already has the real permanent value, classify as-is' preamble — same load+classify shape, structurally different correctness requirement per caller"

key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - app/routers/eval_remote.py

key-decisions:
  - "source: Literal['full_eval_drain', 'remote_eval_worker'] is threaded all the way into the on_path_c_capacity_reached callback invocation (not just accepted and unused) — eval_drain.py's callback ignores it (message is drain-specific either way); eval_remote.py's callback uses it as the Sentry tag value, replacing the previous hardcoded string"
  - "EvalJob import moved from a local import inside _full_drain_tick (historical artifact, RESEARCH.md Assumption A1) to module scope in eval_drain.py — no circular import reappeared (app.models.eval_jobs has no dependency back into eval_drain.py); ruff/ty confirm clean"
  - "_classify_with_overlay takes the caller's own session (not positions_loader callable) — the 4 call sites differ in session lifecycle (3 open+close their own async_session_maker() session; _flaw_engine_plies reuses the caller's already-open load_session), so threading a session parameter is simpler than a loader-callback indirection and preserves exactly this difference"

patterns-established:
  - "Shared decision/preamble functions that must NOT force identical behavior at every call site take an explicit boolean/callback parameter for the divergent piece, documented in the docstring with the specific regression it prevents — rather than either (a) forcing byte-identical unification (breaks correctness) or (b) leaving the duplication in place (the bug-prone status quo this phase exists to remove)"

requirements-completed: [WRITE-01, WRITE-02]

coverage:
  - id: D1
    description: "Path A/B/C completion decision + guarded eval_jobs stamp lives in exactly one apply_completion_decision(...); both _full_drain_tick and _apply_atomic_submit call it; the WHERE status='leased' guard and per-caller Path-C reporting (logger.warning vs sentry capture_message) are preserved"
    requirement: "WRITE-01"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestHoleAwareCompletionGate (all cases)"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py (full file, incl. TestAtomicSubmitEndpoint completion-path cases)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Classify preamble (load positions + optional in-memory overlay + classify) runs through one _classify_with_overlay helper; the 3 overlay sites pass overlay=True, _flaw_engine_plies passes overlay=False; lichess-eval-game flaw-PV coverage (the Phase 117 regression) is preserved"
    requirement: "WRITE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py -k 'flaw or preamble or lichess or pv' (incl. TestFlawPv::test_flaw_pv_written_for_analyzed_lichess_game — asserts lichess %eval preserved at both flaw plies through the overlay=False path)"
        status: pass
      - kind: unit
        ref: "tests/services/test_flaw_upsert_equivalence.py (Plan 01 golden equivalence test — R4 did not change classify output)"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-07-04
status: complete
---

# Phase 150 Plan 03: Consolidate Write Path — Completion Decision + Classify Preamble Summary

**Extracted `apply_completion_decision` (R1, 2 duplicated copies → 1) and `_classify_with_overlay` (R4, 4 duplicated preambles → 1, overlay-parameterized) from `eval_drain.py`/`eval_remote.py` — structure-only, zero behavior change**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-04T15:45:00Z (approx.)
- **Completed:** 2026-07-04T16:07:08Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Unified the Path A/B/C completion-decision + guarded `eval_jobs` stamp (previously duplicated in `_full_drain_tick` and `_apply_atomic_submit`) into one `apply_completion_decision(...)` in `eval_drain.py`, called by both live write lanes, with per-caller Path-C reporting preserved via an injectable callback (drain keeps `logger.warning` per FLAWCHESS-5V; router keeps `sentry_sdk.capture_message`).
- Moved the `EvalJob` import from a local import inside `_full_drain_tick` to module scope in `eval_drain.py` (RESEARCH.md Assumption A1 confirmed safe — no circular import).
- Unified the classify preamble (load `Game` + ordered `GamePosition` rows, optional in-memory post-move overlay, `classify_game_flaws`) shared by `_flaw_engine_plies`, `_missing_flaw_pv_targets`, `_build_flaw_multipv2_blobs`, and `_derive_atomic_sentinel_lines` into one `_classify_with_overlay(game_id, session, *, overlay, pos_eval=None)`, with the 3 "big" sites passing `overlay=True` and `_flaw_engine_plies` passing `overlay=False` — preserving the exact lichess-eval-game correctness requirement (the Phase 117 "0% flaw-PV coverage" regression) that RESEARCH.md flagged as structurally different, not a copy-paste target.
- `eval_remote.py`'s import block shrank by one whole symbol category (`MAX_EVAL_ATTEMPTS`, `EvalJob`, `_mark_full_evals_completed`, `_mark_full_pv_completed` are no longer imported — their only remaining use is inside `apply_completion_decision` itself).

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract apply_completion_decision (R1, 2 copies)** - `d126dba2` (feat)
2. **Task 2: Unify classify preamble with overlay parameter (R4)** - `7d030ab7` (feat)

_Note: no plan-metadata doc commit was required beyond this summary — see final_commit below._

## Files Created/Modified
- `app/services/eval_drain.py` - Added `apply_completion_decision` (R1) + `_log_path_c_capacity_reached` callback; added `_classify_with_overlay` (R4) and rewired all 4 call sites to use it; moved `EvalJob` import to module scope; added `Callable` to the `collections.abc` import and `FlawRecord` to the `flaws_service` import.
- `app/routers/eval_remote.py` - Replaced `_apply_atomic_submit`'s inline Path A/B/C block + eval_jobs stamp with a call to `eval_drain.apply_completion_decision`, passing a new `_report_path_c_capacity_reached` sentry callback; removed the now-unused `EvalJob` module-level import and the `MAX_EVAL_ATTEMPTS`/`_mark_full_evals_completed`/`_mark_full_pv_completed` imports (all now only needed inside `apply_completion_decision`).

## Decisions Made
- `source` is threaded all the way into the Path-C callback signature (`Callable[[int, int, int, str], None]`) rather than being consumed only inside `apply_completion_decision` — this lets the router's callback set the Sentry tag from the parameter instead of a second hardcoded literal, while the drain's callback simply ignores it (documented in its docstring).
- `_classify_with_overlay` takes the caller's own `session` rather than the plan's example `positions_loader` callable signature — simpler, and it naturally preserves the real difference between the 3 sites (own short-lived session) and `_flaw_engine_plies` (reuses the caller's already-open `load_session`) without an extra layer of indirection.
- Did not add a new lichess-flaw-PV-coverage regression test: `tests/services/test_full_eval_drain.py::TestFlawPv::test_flaw_pv_written_for_analyzed_lichess_game` already drives the `overlay=False` path end-to-end via `_full_drain_tick` and explicitly asserts the lichess `%eval` is preserved (not overwritten to `None`) at both flaw plies — exactly the Phase 117 regression this plan's must-have requires guarding. Cited per the plan's own instruction ("unless read_first confirms TestFlawPv already exercises it explicitly, cite that test instead of adding a redundant one").

## Deviations from Plan

None - plan executed exactly as written. Both RESEARCH.md corrections (R1 = 2 live copies not 3; R4's 4th site is structurally different, not a byte-identical copy) were already baked into the plan's task descriptions, so no re-discovery or re-scoping was needed during implementation.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `apply_completion_decision` and `_classify_with_overlay` are both available in `app/services/eval_drain.py` for Plan 04 (R7 module split into `app/services/eval_apply.py`) to relocate alongside the rest of the shared write path — per RESEARCH.md, both must be **moved** (not re-exported) into `eval_apply.py` to avoid the `eval_drain.py <-> eval_apply.py` circular-import trap.
- Plan 05 (R3 diff/upsert) is unaffected by this plan's changes — `_classify_and_fill_oracle`'s delete-then-insert body was not touched; only its callers' surrounding preamble/completion-decision code was consolidated.
- Full backend suite green (3162 passed, 18 skipped — pre-existing skips, unrelated to this plan) after both tasks; `ruff check` and `uv run ty check app/ tests/` both clean.

---
*Phase: 150-consolidate-write-path*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: app/services/eval_drain.py
- FOUND: app/routers/eval_remote.py
- FOUND: .planning/phases/150-consolidate-write-path/150-03-SUMMARY.md
- FOUND commit: d126dba2 (Task 1)
- FOUND commit: 7d030ab7 (Task 2)
- FOUND commit: 73e93e2c (SUMMARY commit)
