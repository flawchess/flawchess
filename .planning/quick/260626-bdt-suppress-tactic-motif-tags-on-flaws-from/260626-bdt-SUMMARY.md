---
phase: quick-260626-bdt
plan: "01"
subsystem: library
tags: [tactic-suppression, decided-lost, serve-layer, backend, sql]
status: complete

dependency_graph:
  requires: []
  provides:
    - decided-lost tactic suppression at SQL and Python serialization chokepoints
  affects:
    - app/repositories/library_repository.py
    - app/services/library_service.py

tech_stack:
  added: []
  patterns:
    - NULL-safe SQLAlchemy OR/AND expression for decided-lost predicate
    - Python pure-predicate mirroring the SQL gate for serialization layer

key_files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/test_library_repository.py
    - tests/test_query_utils.py

decisions:
  - Fail-open: both eval_cp and eval_mate NULL => not decided-lost (structural via NULL guards on each disjunct)
  - Use MATE_LADDER_LOPSIDED_CP imported from flaws_service; no bare 700 literals
  - Suppression at two chokepoints only: SQL (build_flaw_filter_clauses) and Python serialization (tactic_slot_visible); flaws_service.py, stored columns, and stats untouched
  - flaw_exists_from_table gets a PositionBefore LEFT JOIN (ply N-1); ply 0/1 flaws have no prior position -> NULL eval -> fail open
  - _build_flaw_item() helper extracted from query_flaws to avoid inlining is_decided_lost six times (CLAUDE.md shallow functions rule)

metrics:
  duration: ~3h (2 sessions, context overflow mid-task)
  completed: "2026-06-26T06:36:56Z"
  tasks_completed: 3
  files_modified: 4
---

# Phase quick-260626-bdt Plan 01: Suppress Decided-Lost Tactic Tags Summary

**One-liner:** Serve-layer suppression of tactic-motif tags and depth on decided-lost flaws using a NULL-safe `decided_lost_sql()` / `is_decided_lost()` predicate pair gated at the SQL filter and Python serialization chokepoints.

## What Was Built

A flaw whose pre-move eval was already decisively lost for the mover (white: `eval_cp <= -700` or `eval_mate < 0`; black: `eval_cp >= +700` or `eval_mate > 0`) now has its tactic-motif tag and depth treated as absent everywhere in the Flaws page, Games page, and eval-chart tooltip. The flaw itself still exists, still counts in blunder/mistake severity totals, and still renders an eval-chart marker. Null pre-move eval fails open (tag shown, flaw matches filters).

### Backend Architecture

Two co-located helpers in `library_repository.py`:

- `is_decided_lost(eval_cp_before, eval_mate_before, *, mover_is_white) -> bool` — pure Python predicate for serialization. Strict mate signs (`< 0` / `> 0`); cp inclusive (`<= -MATE_LADDER_LOPSIDED_CP`). Both None → False (fail open).
- `decided_lost_sql(eval_cp_col, eval_mate_col, user_color_col) -> ColumnElement[bool]` — NULL-safe SQLAlchemy equivalent. Each disjunct wrapped in `and_(col.isnot(None), ...)` so NULL columns contribute False structurally.

Both gated into:
1. **SQL filter** (`build_flaw_filter_clauses`): new `decided_lost: ColumnElement[bool] | None = None` param; when non-None, `and_(tactic_clause, not_(decided_lost))` is appended. Only the tactic clause is gated — severity/tempo/opportunity/impact/phase clauses are unaffected.
2. **Python serialization** (`tactic_slot_visible`): new `decided_lost: bool = False` first-return short-circuit before orientation/confidence/family/depth checks.

Threading:
- `flaw_exists_from_table`: new `PositionBefore = aliased(GamePosition, name="pos_before_exists")` LEFT JOIN on `ply - 1`, user+game scoped; `decided_lost_sql(...)` passed to `build_flaw_filter_clauses`.
- `query_flaws`: `PositionBefore` alias already present; `decided_lost_sql(...)` passed to `build_flaw_filter_clauses`; `_build_flaw_item()` helper computes `row_decided_lost` once per row and threads it into all 6 `tactic_slot_visible` calls.
- `_build_card` (library_service): `pos_by_ply` dict built once before the flaw loop; `fr_decided_lost` computed from `pos_by_ply.get(fr.ply - 1)` and passed into both `tactic_slot_visible` calls.

### Frontend

All three tactic render surfaces already guarded on null motif:
- `FlawCard.tsx`: `flaw.allowed_tactic_motif != null && ...` guards before every chip render.
- `LibraryGameCard.tsx`: `if (raw == null) return;` in the `collect` closure; `col != null &&` in the highlight path.
- `EvalChart.tsx` tooltip: `if (raw == null) return;` in the `add` helper.

No frontend code changes were needed. `npm run lint` and `npm run build` pass unchanged.

### Tests

`TestDecidedLostSuppression` class in `tests/test_library_repository.py` with 6 tests:
1. `test_decided_lost_fork_excluded_from_motif_filter` — decided-lost fork excluded; contestable fork included.
2. `test_decided_lost_flaw_still_counts_severity` — flaw still present in unfiltered results, severity='blunder', tactic fields None.
3. `test_null_pre_move_eval_fails_open` — both eval cols NULL => fork NOT suppressed, motif non-None.
4. `test_flaws_and_games_paths_agree` — query_flaws and flaw_exists_from_table agree on matched game set.
5. `test_pov_sign_flip` — white/black mover losing suppressed; winning equivalents not; eval_mate=-2 suppressed, +2 not.
6. `test_boundary_threshold` — eval_cp=-700 (==-MATE_LADDER_LOPSIDED_CP) suppressed (inclusive); -300 not.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed brittle test assertion in test_query_utils.py**
- **Found during:** Task 2 / full-suite run
- **Issue:** `test_mate_exemption_removed_when_depth_set` asserted `" OR " not in sql` for the entire EXISTS subquery. The new `NOT(decided_lost_sql(...))` clause correctly adds `OR` inside its own scope — the assertion was over-broad.
- **Fix:** Replaced blanket OR check with `depth_term = depth_ctx.split(" AND ")[0]` (just the depth predicate's own AND-term) and asserted no OR in that narrow slice. The original invariant — no mate exemption OR adjacent to the depth predicate — is still enforced.
- **Files modified:** `tests/test_query_utils.py`
- **Commit:** 466b5a94

**2. [Rule 1 - Bug] E402 lint: _DL_USER_ID constant placed before app imports**
- **Found during:** Full verification (ruff check)
- **Issue:** `_DL_USER_ID = 99997` was declared between stdlib imports and app imports, causing E402.
- **Fix:** Moved constant to after all imports (after `from app.repositories.query_utils import apply_game_filters`).
- **Files modified:** `tests/test_library_repository.py`
- **Commit:** 466b5a94

**3. [Rule 1 - Bug] ty error: bare str type on _query_flaws_fork orientation param**
- **Found during:** Full verification (ty check)
- **Issue:** Helper method `_query_flaws_fork` declared `orientation: str = "allowed"` — ty flagged the call to `query_flaws(..., orientation=orientation)` as `invalid-argument-type` (expected `Literal[...]`, got `str`).
- **Fix:** Added `TacticOrientation` to the `library_repository` import block; typed the param as `TacticOrientation`; removed the `# type: ignore[arg-type]` comment.
- **Files modified:** `tests/test_library_repository.py`
- **Commit:** 466b5a94

## Commits

| Hash | Message | Task |
|------|---------|------|
| efbb7ccb | feat(260626-bdt): decided-lost predicate + SQL gate + serialization | Task 1 |
| 231eb090 | test(260626-bdt): decided-lost tactic suppression backend tests | Task 2 |
| 466b5a94 | test(260626-bdt): fix test isolation and test_mate_exemption assertion | Task 2 fixes |

## Verification Results

```
uv run ruff format app/ tests/ && uv run ruff check app/ tests/  ->  All checks passed!
uv run ty check app/ tests/                                       ->  All checks passed!
uv run pytest -n auto -x                                          ->  2895 passed, 18 skipped
cd frontend && npm run lint                                       ->  0 errors, 3 pre-existing coverage warnings
cd frontend && npm run build                                      ->  build succeeded
cd frontend && npm test -- --run                                  ->  1150 passed (95 test files)
```

Sanity greps:
- `decided_lost`/`is_decided_lost`/`decided_lost_sql` found in all 4 threading sites: `build_flaw_filter_clauses`, `flaw_exists_from_table`, `query_flaws`, `_build_card`.
- No bare `700` in `library_repository.py`.
- `flaws_service.py` unchanged (git diff empty).

## Self-Check: PASSED

- `app/repositories/library_repository.py` — FOUND (committed efbb7ccb)
- `app/services/library_service.py` — FOUND (committed efbb7ccb)
- `tests/test_library_repository.py` — FOUND (committed 231eb090 + 466b5a94)
- `tests/test_query_utils.py` — FOUND (committed 466b5a94, deviation fix)
- `efbb7ccb` — FOUND in git log
- `231eb090` — FOUND in git log
- `466b5a94` — FOUND in git log
