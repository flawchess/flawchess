---
phase: 150-consolidate-write-path
plan: 02
subsystem: api
tags: [stockfish, sqlalchemy-async, efraimidis-spirakis, weighted-lottery, refactor]

requires: []
provides:
  - "EnginePool._acquire_and_analyse(board, limit, timeout, *, multipv=None) — single shared acquire/timeout/restart/release skeleton behind evaluate(), evaluate_nodes(), evaluate_nodes_with_pv(), and evaluate_nodes_multipv2()"
  - "_es_weighted_user_pick / _es_weighted_game_pick — two generic Efraimidis-Spirakis weighted-pick building blocks shared by the tier-3 (_claim_tier3_derived) and tier-4 (_claim_tier4_blob) eval-queue lotteries"
affects: []

tech-stack:
  added: []
  patterns:
    - "isinstance(result, list) narrowing over a chess.engine.InfoDict | list[InfoDict] | None union to recover per-caller post-processing after a shared acquisition method"
    - "Caller-supplied trusted SQL fragments (candidate_exists_sql / game_where_sql / recency_col_sql) composed via f-string into sa.text() query SHAPE, while all numeric VALUES stay bound via the params dict — same discipline as the pre-existing CASE-key-literal pattern in this file"

key-files:
  created: []
  modified:
    - app/services/engine.py
    - app/services/eval_queue_service.py

key-decisions:
  - "EnginePool._acquire_and_analyse keeps the exact plan-specified union return type (InfoDict | list[InfoDict] | None); callers narrow via isinstance(result, list) rather than @overload (no @overload precedent in this codebase)"
  - "_es_weighted_game_pick's base query is always FROM games g alone (no JOIN); the tier-3 residual fallback's old JOIN users ... is_guest=false became an equivalent EXISTS subquery (games.user_id -> users.id is 1:1, no cardinality change), and the paired user_id is fetched via one cheap PK-indexed follow-up SELECT since the shared helper only returns game_id"
  - "extra_params: dict[str, Any] | None = None added to _es_weighted_game_pick (not in the plan's literal signature sketch) to bind :picked_user for tier-3 Step 2 and tier-4 Stage 2 without breaking the sa.text bound-params discipline"

patterns-established:
  - "Generic ES weighted-pick building blocks (_es_weighted_user_pick / _es_weighted_game_pick) parameterized on trusted SQL-shape fragments + bound numeric values — reusable by a future tier-5 lottery without duplicating the ES key or TC-multiplier CASE block"

requirements-completed: [WRITE-05, WRITE-06]

coverage:
  - id: D1
    description: "EnginePool exposes exactly one generic acquire/analyse/restart method (_acquire_and_analyse); evaluate/evaluate_nodes/evaluate_nodes_with_pv/evaluate_nodes_multipv2 preserve their exact return shapes and failure sentinels"
    requirement: "WRITE-05"
    verification:
      - kind: unit
        ref: "tests/services/test_engine.py (12 tests, incl. TestEvaluateNodesMultipv2 return-shape/sentinel guards)"
        status: pass
      - kind: unit
        ref: "tests/services/test_engine_nodes.py (7 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tier-3/tier-4 ES lotteries share _es_weighted_user_pick / _es_weighted_game_pick building blocks; tier-3 keeps its residual-fallback stage, tier-4 keeps its no-fallback 2-stage shape and full_evals_completed_at anchor; all params bound via sa.text dicts"
    requirement: "WRITE-06"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_queue.py (25 tests, incl. tier3/tier4 anti-starvation, recency-weighting, residual-fallback, guest-exclusion)"
        status: pass
      - kind: unit
        ref: "tests/test_eval_queue_service.py::test_claim_tier4_blob_anti_starvation_and_recency_preference"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-04
status: complete
---

# Phase 150 Plan 02: Consolidate Write Path — EnginePool + ES Lottery Ride-Alongs Summary

**Collapsed EnginePool's 3 near-identical analyse methods into one generic `_acquire_and_analyse`, and parameterized the tier-3/tier-4 eval-queue lotteries into two shared Efraimidis-Spirakis weighted-pick building blocks — both structure-only, zero behavior change**

## Performance

- **Duration:** 25 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `EnginePool` now has one `_acquire_and_analyse(board, limit, timeout, *, multipv=None)` method holding the single acquire/timeout/restart/release skeleton; `_analyse`, `_analyse_with_pv`, and `_analyse_multipv2` are gone, with each public method (`evaluate`, `evaluate_nodes`, `evaluate_nodes_with_pv`, `evaluate_nodes_multipv2`) applying its own post-processing via `isinstance(result, list)` narrowing
- `_claim_tier3_derived` and `_claim_tier4_blob` now both call `_es_weighted_user_pick` and `_es_weighted_game_pick` instead of hand-rolling the ES key + TC-multiplier CASE block twice; tier-3 keeps its 3-stage shape (user-pick → game-pick → residual-fallback game-pick), tier-4 keeps its 2-stage shape (user-pick → game-pick, no fallback)
- All WHERE/EXISTS predicates, named half-life/floor constants, and TC weights (classical=8/rapid=4/blitz=2/bullet=1/other=0.5) are byte-identical per tier — verified by the full existing engine + eval-queue test suites passing unmodified, plus a full `pytest -n auto` run (3162 passed, 18 skipped, zero failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: EnginePool generic acquire/analyse/restart method (R5)** - `a700044a` (refactor)
2. **Task 2: Parameterize tier-3/tier-4 ES lottery (R6)** - `ac181699` (refactor)

**Plan metadata:** (this commit)

## Files Created/Modified
- `app/services/engine.py` - `_acquire_and_analyse` replaces `_analyse`/`_analyse_with_pv`/`_analyse_multipv2`; 4 public methods updated to call it and narrow the return type themselves
- `app/services/eval_queue_service.py` - `_es_weighted_user_pick`/`_es_weighted_game_pick` added; `_claim_tier3_derived`/`_claim_tier4_blob` rewired to call them

## Decisions Made
- Kept `_acquire_and_analyse`'s declared return type as the plan-specified union (`InfoDict | list[InfoDict] | None`) rather than introducing `@overload` (no existing `@overload` usage in this codebase to extend); each caller narrows via `isinstance(result, list)`, which `ty` follows correctly.
- `_es_weighted_game_pick`'s base query is always `FROM games g` with no JOIN. The tier-3 residual fallback's old `JOIN users u ON u.id = g.user_id ... AND u.is_guest = false` became an `EXISTS (SELECT 1 FROM users u WHERE u.id = g.user_id AND u.is_guest = false)` — semantically identical (games.user_id → users.id is a 1:1 FK relationship, so no cardinality change). Since the shared helper only returns `game_id`, the residual fallback fetches the paired `user_id` via one additional PK-indexed `SELECT` — a trivial, non-behavior-affecting extra round trip on a rare path.
- Added an `extra_params: dict[str, Any] | None = None` parameter to `_es_weighted_game_pick` (not literally in the plan's signature sketch) so tier-3 Step 2 and tier-4 Stage 2 can bind `:picked_user` into their `game_where_sql` fragment without breaking the "never f-string-interpolate VALUES" discipline — only the trusted, hardcoded SQL fragment (never user input) is composed structurally via f-string, exactly mirroring the existing CASE-key-literal pattern already in this file.

## Deviations from Plan

None - plan executed exactly as written. The `extra_params` addition and the EXISTS-vs-JOIN residual-fallback rewrite are implementation refinements within the plan's own "may refine" signature sketch and explicit "no behavior change" contract, not deviations from a locked interface — no new files, no schema changes, no test rewrites were needed since both functions' public call signatures (`_claim_tier3_derived(session)`, `_claim_tier4_blob(session)`) and return shapes were preserved exactly.

## Issues Encountered
- The `Edit` tool's exact-string-match requirement failed against the large multi-line docstrings in `eval_queue_service.py` (unicode en-dashes / Greek letters likely triggered a subtle mismatch). Worked around by reading the file into a Python script, slicing the exact old block by line range, and writing the replacement programmatically — no impact on the resulting code, verified via `python3 -c "import ast; ast.parse(...)"` and the full test/lint/type-check gate afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both ride-alongs (R5/WRITE-05, R6/WRITE-06) are independent of the write-path chain (D-06) and fully done — no blockers for 150-03/04/05.
- `app/services/engine.py` and `app/services/eval_queue_service.py` are untouched by the remaining write-path consolidation plans (150-03 onward touch `eval_drain.py`, `eval_remote.py`, `eval_apply.py`), so no merge-order dependency exists.

---
*Phase: 150-consolidate-write-path*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: app/services/engine.py
- FOUND: app/services/eval_queue_service.py
- FOUND: .planning/phases/150-consolidate-write-path/150-02-SUMMARY.md
- FOUND: a700044a (Task 1 commit)
- FOUND: ac181699 (Task 2 commit)
- FOUND: 22962682 (SUMMARY commit)
