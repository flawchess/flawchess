---
phase: 113-opponent-flaw-materialization
plan: 02
subsystem: database
tags: [flaws, library, sqlalchemy, data-isolation, tdd, player-gate, game-flaws]

# Dependency graph
requires:
  - phase: 113-01
    provides: is_opponent_expr/player_only_gate helpers in query_utils.py; both-sides kernel

provides:
  - player_only_gate on all 5 game_flaws read sites (R1-R5) in library_repository.py
  - R6 (cross-tab EXISTS) fixed automatically via R1 choke point — no query_utils.py edit
  - Game JOIN added to fetch_stats_aggregates (R4) and fetch_stats_trend (R5)
  - No-regression tests proving gated == player-only baseline, ungated > baseline

affects: [113-03-backfill, 115-comparison-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "player_only_gate(GameFlaw.ply, Game.user_color) applied at each D-04 gating site as a named expression"
    - "R3/R4/R5 required Game JOIN to bring user_color into scope — JOIN approach used (simpler than correlated subquery)"
    - "R1 choke point gating: flaw_exists_from_table gates all callers via apply_game_filters delegation (no edit to query_utils.py)"
    - "is_opponent_expr/player_only_gate params widened to Any — ty does not recognise InstrumentedAttribute as ColumnElement subtype"
    - "TDD: RED (failing test) → GREEN (implementation) cycle per task"

key-files:
  created:
    - ".planning/phases/113-opponent-flaw-materialization/113-02-SUMMARY.md"
  modified:
    - "app/repositories/library_repository.py"
    - "app/repositories/query_utils.py"
    - "tests/test_flaw_predicate.py"
    - "tests/test_library_repository.py"
    - "tests/test_library_router.py"

key-decisions:
  - "R3 (fetch_page_game_flaws) gated via .join(Game) + player_only_gate — no Game JOIN existed before; JOIN preferred over correlated subquery (RESEARCH A2)"
  - "R4/R5 (fetch_stats_aggregates/trend) gated via .join(Game) + player_only_gate — JOIN added to aggregate stmt and flaw_counts_subq respectively"
  - "R6 fixed via R1 (flaw_exists_from_table) with no query_utils.py edit — delegation chain propagates the gate automatically"
  - "player_only_gate/is_opponent_expr param type widened from ColumnElement to Any — InstrumentedAttribute is not a ColumnElement in ty's type hierarchy (runtime correct, tested)"
  - "test_library_router.py fixture updated: game_a1 (black user) flaws moved to odd plies (5,7) from even plies (4,8) — even plies are now opponent rows for black user after both-sides kernel"

patterns-established:
  - "D-04 gate pattern: .join(Game, Game.id == GameFlaw.game_id) + player_only_gate(GameFlaw.ply, Game.user_color) in WHERE"
  - "Choke-point gating: gating flaw_exists_from_table (R1) covers the cross-tab Flaw filter (R6) via apply_game_filters delegation"
  - "No-regression baseline test: assert gated == pre-both-sides baseline AND ungated_direct_count > baseline"

requirements-completed: [FLAWX-01, FLAWX-04]

# Metrics
duration: 16min
completed: 2026-06-10
---

# Phase 113 Plan 02: D-04 Player-Only Gate on All game_flaws Readers Summary

**Player-only gate applied to all 5 library_repository.py game_flaws read sites (R1-R5) via player_only_gate helper + Game JOIN where needed; R6 cross-tab Flaw filter fixed automatically via R1 choke point; no-regression baseline tests prove gated == pre-phase counts while ungated is strictly higher**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-06-10T05:41:22Z
- **Completed:** 2026-06-10T05:57:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Gated all 5 `game_flaws` read sites in `library_repository.py` with `player_only_gate(GameFlaw.ply, Game.user_color)`, preventing opponent flaws from appearing in the self-only Library UI (D-04)
- R3 (`fetch_page_game_flaws`), R4 (`fetch_stats_aggregates`), R5 (`fetch_stats_trend`) required a new `Game JOIN` to bring `Game.user_color` into scope — JOIN approach used as recommended (RESEARCH A2)
- R1 (`flaw_exists_from_table`) gating automatically fixed R6 (cross-tab Flaw filter via `apply_game_filters`) with no edit to `query_utils.py`
- Widened `is_opponent_expr`/`player_only_gate` param types from `ColumnElement` to `Any` — ty does not recognize `InstrumentedAttribute` as a `ColumnElement` subtype; runtime behavior is correct and tested
- Added 11 new integration tests across 4 test classes; full suite 2491 passed (plus 10 skipped)

## Gate Sites Applied

| # | File | Function | Change |
|---|------|----------|--------|
| R1 | `library_repository.py` | `flaw_exists_from_table` | Added `player_only_gate(...)` to EXISTS WHERE |
| R2 | `library_repository.py` | `query_flaws` | Added `player_only_gate(...)` to base_stmt WHERE (Game already joined) |
| R3 | `library_repository.py` | `fetch_page_game_flaws` | Added `.join(Game)` + `player_only_gate(...)` to WHERE |
| R4 | `library_repository.py` | `fetch_stats_aggregates` | Added `.join(Game)` + `player_only_gate(...)` to aggregate stmt WHERE |
| R5 | `library_repository.py` | `fetch_stats_trend` | Added `.join(Game)` + `player_only_gate(...)` inside `flaw_counts_subq` WHERE |
| R6 | `query_utils.py` | `apply_game_filters` | Fixed automatically via R1 — no edit needed |

`count_game_severities` confirmed unchanged (reads `game_positions`, has its own mover filter — verified).

## No-Regression Baseline (D-04 Invariant)

`TestStatsAggregatesPlayerOnly::test_stats_aggregates_gated_equals_player_only_baseline`:
- Seeded 4 player-only flaws (2 per game × 2 games — white user + black user)
- Baseline `fetch_stats_aggregates` returned total 4 (mistake+blunder)
- After inserting 4 opponent flaws (both-sides), gated aggregate still returned 4 (unchanged)
- Direct ungated DB count returned 8 (strictly > 4 baseline — opponent rows present)
- Both parity branches exercised (white user: even plies = player; black user: odd plies = player)

## Task Commits

1. **Task 1: Gate R1/R2/R3 + TestFlawExistsPlayerOnly + TestPlayerOnlyGate + TestPageFlawsPlayerOnly** - `7c555cd5` (feat)
2. **Task 2: Gate R4/R5 + TestStatsAggregatesPlayerOnly** - `490434ba` (feat)
3. **Rule 1 auto-fix: test_library_router fixture plies** - `a4fba380` (fix)

## Files Created/Modified

- `app/repositories/library_repository.py` — 5 read sites gated; Game JOIN added to R3/R4/R5
- `app/repositories/query_utils.py` — `is_opponent_expr`/`player_only_gate` params widened to Any
- `tests/test_flaw_predicate.py` — Added `TestFlawExistsPlayerOnly` (5 tests); `_seed_game` gets `user_color` param
- `tests/test_library_repository.py` — Added `TestPlayerOnlyGate` (2), `TestPageFlawsPlayerOnly` (2), `TestStatsAggregatesPlayerOnly` (2); added imports for `Subquery`, `GameFlaw`, `fetch_stats_aggregates`, `fetch_stats_trend`, `_analyzed_game_ids_subquery`
- `tests/test_library_router.py` — Fixed `flaws_test_state` fixture: game_a1 (black user) flaws moved from even plies (4,8) to odd plies (5,7); updated 4 test assertions/comments

## Decisions Made

- R3 Game JOIN: added `.join(Game, Game.id == GameFlaw.game_id)` rather than a correlated subquery — simpler, consistent with R4/R5 approach, negligible perf at this scale (RESEARCH A2)
- R4/R5 Game JOIN: same approach as R3; aggregate stmt and flaw_counts_subq both joined to Game
- R6 via R1 choke point: no edit to `query_utils.py` — the delegation `apply_game_filters -> flaw_exists_from_table` propagates the R1 gate automatically, exactly as designed in RESEARCH §Pattern 3
- `Any` widening: ty does not see `InstrumentedAttribute[T]` as a subtype of `ColumnElement[T]`. Using `Any` is the correct fix (same as `apply_game_filters`'s `stmt: Any` pattern in the same file). Runtime and TestIsOpponentExpr confirm correctness.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_library_router.py fixture to use player plies for black-user game**
- **Found during:** Full test suite run after Tasks 1+2
- **Issue:** `flaws_test_state` fixture had game_a1 (`user_color="black"`) flaws at even plies (4, 8). After the player-only gate, even plies for a black user are opponent rows — so 3 tests failed: `test_ordering_recent_first_then_ply_asc`, `test_severity_filter_mistake_only`, `test_tag_reversed_matches_only_its_game`. The fixture was seeding the old pre-gate assumption (player_only kernel behavior).
- **Fix:** Changed ply=4 → ply=5 and ply=8 → ply=7 for game_a1 (odd plies = black mover = player for black user). Updated 4 test assertions/comments. Flaw counts unchanged (3 blunders, 2 mistakes, 5 total).
- **Files modified:** `tests/test_library_router.py`
- **Verification:** 3 previously failing tests now pass; full suite 2491 passed
- **Committed in:** `a4fba380` (Rule 1 fix commit)

**2. [Rule 3 - Blocking] Widened is_opponent_expr/player_only_gate param types to Any**
- **Found during:** Task 1 (after GREEN implementation)
- **Issue:** `uv run ty check` reported 6 `invalid-argument-type` errors: `InstrumentedAttribute[int]` is not `ColumnElement[int]` in ty's type system. All 3 `player_only_gate(GameFlaw.ply, Game.user_color)` call sites failed.
- **Fix:** Changed `ply_col: ColumnElement[int]` and `user_color_col: ColumnElement[str]` to `Any` in both `is_opponent_expr` and `player_only_gate`. Updated docstrings to explain the widening.
- **Files modified:** `app/repositories/query_utils.py`
- **Verification:** `uv run ty check app/ tests/` → 0 errors
- **Committed in:** `7c555cd5` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - bug, 1 Rule 3 - blocking)
**Impact on plan:** Both fixes essential for correctness and ty compliance. No scope creep.

## Issues Encountered

None — implementation followed the plan exactly. The ty type widening was a known risk for SQLAlchemy attribute types; the solution (Any) is consistent with `apply_game_filters`'s existing `stmt: Any` pattern.

## Known Stubs

None — this plan adds WHERE clauses only. No UI-facing data is involved.

## Threat Flags

None — no new endpoints, no new user input. All existing `GameFlaw.user_id == user_id` IDOR scoping preserved at every gated site (T-113-03/T-113-04 closed by TestFlawExistsPlayerOnly + TestStatsAggregatesPlayerOnly).

## Next Phase Readiness

- All 5 `library_repository.py` read sites are gated — opponent flaws cannot leak into the self-only Library UI
- Phase 113 Plan 03 (backfill) can now run safely: `backfill_flaws.py` will write both sides, and readers are already gated to return only player flaws
- Phase 115 (comparison endpoint) will pass `player_only_gate=False` (or omit the gate) at its own call sites to intentionally read both sides

---
*Phase: 113-opponent-flaw-materialization*
*Completed: 2026-06-10*

## Self-Check: PASSED

- FOUND: `.planning/phases/113-opponent-flaw-materialization/113-02-SUMMARY.md`
- FOUND: `app/repositories/library_repository.py`
- FOUND: `app/repositories/query_utils.py`
- FOUND: `tests/test_flaw_predicate.py`
- FOUND: `tests/test_library_repository.py`
- FOUND commit: `7c555cd5` (Task 1)
- FOUND commit: `490434ba` (Task 2)
- FOUND commit: `a4fba380` (Rule 1 fix)
- All 2491 tests passed
