---
phase: 113-opponent-flaw-materialization
plan: 01
subsystem: database
tags: [flaws, classification, sqlalchemy, parity, tdd, game-flaws, opponent]

# Dependency graph
requires:
  - phase: 108-library-flaw-materialization
    provides: classify_game_flaws kernel, FlawRecord, flaw_record_to_row, game_flaws table
provides:
  - is_opponent_expr(ply_col, user_color_col) -> ColumnElement[bool] in query_utils.py — single source of ply-parity convention
  - player_only_gate() convenience inverse wrapper for reader-gating call sites (D-04)
  - classify_game_flaws generalized to emit BOTH movers with per-mover subject_result
affects: [113-02-reader-gating, 113-03-backfill, 115-comparison-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "is_opponent_expr: SQLAlchemy case() helper in query_utils.py, not inline ply % 2 math, not a hybrid property"
    - "TDD: RED (failing test) → GREEN (implementation) cycle per task"
    - "Per-mover subject_result: derive_user_result(game.result, mover) called once per flaw in the emit loop"

key-files:
  created:
    - ".planning/phases/113-opponent-flaw-materialization/113-01-SUMMARY.md"
  modified:
    - "app/repositories/query_utils.py"
    - "app/services/flaws_service.py"
    - "tests/services/test_flaws_service.py"
    - "tests/test_flaws_materialization.py"

key-decisions:
  - "is_opponent_expr placed in query_utils.py as a plain helper (not hybrid expression) — matches established module pattern, independently testable, avoids new pattern"
  - "player_only_gate() convenience inverse added (Claude's Discretion, D-01) — improves read-site readability in Plan 02"
  - "_PLY_EVEN_MOVER_WHITE = 0 named constant — no bare magic number for the parity modulus"
  - "Per-mover subject_result computed inside the emit loop (not pre-resolved at top of function) — fixes the lucky end-rule for opponent flaws"
  - "3 pre-existing tests updated (Rule 1 auto-fix) to reflect both-sides kernel behavior"

patterns-established:
  - "Parity convention: even ply → white mover; odd ply → black mover (mirrors _run_all_moves_pass)"
  - "is_opponent_expr is the ONLY place ply % 2 logic lives — readers import from query_utils"
  - "TestIsOpponentExpr uses live DB eval (not compiled SQL inspection) — required by prior off-by-one history"

requirements-completed: [FLAWX-01, FLAWX-02]

# Metrics
duration: 38min
completed: 2026-06-10
---

# Phase 113 Plan 01: is_opponent_expr Parity Helper + Both-Sides Kernel Summary

**Both-mover flaw classification via dropped player-only filter + single tested is_opponent_expr parity helper, closing the documented off-by-one trap**

## Performance

- **Duration:** ~38 min
- **Started:** 2026-06-10T05:30:00Z
- **Completed:** 2026-06-10T06:08:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `is_opponent_expr(ply_col, user_color_col) -> ColumnElement[bool]` to `query_utils.py` as the single source of the ply-parity convention (even ply = white mover, odd ply = black mover), with `player_only_gate()` convenience inverse
- Dropped `if mover != user_color: continue` filter from `classify_game_flaws`, making the kernel emit FlawRecords for BOTH movers at zero added engine cost
- Fixed the `lucky` end-of-game tag: now uses `derive_user_result(game.result, mover)` per-mover instead of the pre-resolved `user_result`, so an opponent's end-of-game loss is never tagged "lucky"
- Added 11 new tests: `TestIsOpponentExpr` (4 parity combos via live DB), `TestClassifyBothColors` (3), `TestOpponentLuckyTag` (2), `TestBothSidesMaterialization` (2); full suite 2480 passed

## Parity Convention (for Plan 02 / Plan 03)

```
even ply → white mover → is_opponent iff user_color == 'black'
odd ply  → black mover → is_opponent iff user_color == 'white'
```

Verified by `TestIsOpponentExpr` executing `is_opponent_expr(literal(ply), literal(color))` against the real DB for all 4 combinations. Helper signature:

```python
is_opponent_expr(GameFlaw.ply, Game.user_color)   # bool expr: True = opponent row
player_only_gate(GameFlaw.ply, Game.user_color)   # bool expr: True = player row (~above)
```

## Task Commits

1. **Task 1: Add is_opponent_expr parity helper with TestIsOpponentExpr** - `848e7aaa` (feat)
2. **Task 2: Generalize classify_game_flaws to emit both movers** - `6a974a33` (feat)

## Files Created/Modified

- `app/repositories/query_utils.py` — Added `is_opponent_expr()` + `player_only_gate()` + `_PLY_EVEN_MOVER_WHITE` constant
- `app/services/flaws_service.py` — Dropped player-only filter, added per-mover subject_result computation, added explanatory comment at the changed site
- `tests/services/test_flaws_service.py` — Added `TestIsOpponentExpr`, `TestClassifyBothColors`, `TestOpponentLuckyTag`; updated 3 pre-existing tests for both-sides behavior
- `tests/test_flaws_materialization.py` — Added `TestBothSidesMaterialization`

## Decisions Made

- `is_opponent_expr` placed in `query_utils.py` as a plain helper function (not a SQLAlchemy hybrid expression on `GameFlaw`) — consistent with existing module pattern, no new patterns introduced, independently testable
- `player_only_gate()` added (Claude's Discretion per D-01) — intent-based naming at D-04 reader sites
- Named constant `_PLY_EVEN_MOVER_WHITE = 0` for the parity modulus (no magic numbers rule)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 3 pre-existing tests that asserted player-only kernel behavior**
- **Found during:** Task 2 (classify_game_flaws generalization)
- **Issue:** `TestClassifyGameFlaws::test_opponent_flaws_not_in_result_for_white_user` asserted no opponent flaws would appear. `TestOracleCloseness::test_derived_counts_close_to_oracle_white` and `_black` computed aggregate counts across both movers without filtering by side.
- **Fix:** Renamed the first test and flipped its assertion to verify opponent flaws ARE present. Updated the oracle tests to filter by `f["side"] == "white"` / `"black"` before counting.
- **Files modified:** `tests/services/test_flaws_service.py`
- **Verification:** All 119 tests in the two affected files pass; full suite 2480 passed
- **Committed in:** `6a974a33` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix in tests)
**Impact on plan:** Necessary correctness fix — the tests were asserting the behavior being intentionally changed. No scope creep.

## Issues Encountered

None — the implementation followed the plan exactly. The ty `return-value` rule was found to be unknown (the `case()` return type needed no suppression), so the `# ty: ignore` comment was removed before commit.

## Known Stubs

None — this plan adds a helper function and drops a filter. No UI-facing data is involved.

## Threat Flags

None — no new endpoints, no new user input, all existing `GameFlaw.user_id == user_id` IDOR scoping preserved (T-113-01 parity correctness closed by the mandatory `TestIsOpponentExpr` unit test).

## Next Phase Readiness

- `is_opponent_expr` and `player_only_gate` are ready for Plan 02 (reader gating)
- `classify_game_flaws` now emits both movers — Plan 02 must gate all 5 `library_repository.py` read sites before the dev backfill runs (D-04)
- Plan 03 (backfill) requires no kernel changes — the D-10 single-classify-path invariant means `backfill_flaws.py`, `reclassify_positions.py`, and `eval_drain.py` all propagate both sides automatically

---
*Phase: 113-opponent-flaw-materialization*
*Completed: 2026-06-10*
</content>
</invoke>