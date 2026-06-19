---
phase: 126-comparison-stats-frontend
plan: "01"
subsystem: backend
tags: [tactic-comparison, library, flaw-chip, backend]
dependency_graph:
  requires: [app/repositories/query_utils.py, app/repositories/library_repository.py, app/services/library_service.py, app/schemas/library.py, app/routers/library.py]
  provides: [GET /api/library/tactic-comparison, TacticBullet, TacticComparisonResponse, FAMILY_TO_MOTIF_INTS, get_tactic_comparison, fetch_tactic_comparison, tactic_families filter, tactic_motif/tactic_confidence on flaw rows]
  affects: [plans 126-02 and 126-03 (frontend consumes this endpoint and chip fields)]
tech_stack:
  added: []
  patterns: [flaw-comparison mirror pattern, is_opponent_expr player/opponent split, Wilson Wald-z CI, lazy import for circular dep avoidance, TDD RED/GREEN]
key_files:
  created:
    - tests/services/test_tactic_comparison_service.py
    - tests/routers/test_library_tactic_comparison.py
  modified:
    - app/repositories/query_utils.py
    - app/repositories/library_repository.py
    - app/schemas/library.py
    - app/services/library_service.py
    - app/routers/library.py
decisions:
  - "TACTIC_COMPARISON_GATE=20 mirrors FLAW_COMPARISON_GATE (same minimum sample floor)"
  - "MIN_TACTIC_CHIP_CONFIDENCE=70 (0-100 scale); constant in library_repository gating query_flaws + service re-export"
  - "FAMILY_TO_MOTIF_INTS covers all 24 TacticMotifInt values exactly once across 6 families"
  - "tactic_families filter uses correlated EXISTS in apply_game_filters (T-126-02 injection prevention)"
  - "_TACTIC_CHIP_CONFIDENCE_MIN defined in library_repository.py (used at row-build time without service-layer call)"
  - "FlawMarker tactic fields wired via tactic_by_ply dict passed into _build_eval_series (TACUI-01 single-game card)"
metrics:
  duration: "14 minutes"
  completed: "2026-06-18"
  tasks_completed: 3
  files_modified: 7
status: complete
---

# Phase 126 Plan 01: Tactic Comparison Backend Summary

GET /api/library/tactic-comparison returns per-family (6 collapsed families) you-vs-opponent tactic-motif rates normalized per game, with Wald-z Wilson significance verdict, section-level sample gate, honoring all existing game filters + severity + new tactic_families filter.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for family mapping + service | 68355312 | tests/services/test_tactic_comparison_service.py |
| 1 | FAMILY_TO_MOTIF_INTS + tactic_families filter | 30ec802e | app/repositories/library_repository.py, app/repositories/query_utils.py |
| 2 | Schemas, repo fn, service fn | 89ceb238 | app/schemas/library.py, app/repositories/library_repository.py, app/services/library_service.py, tests/services/ |
| RED | Failing router tests | aab0655d | tests/routers/test_library_tactic_comparison.py |
| 3 | GET /tactic-comparison endpoint | 22416201 | app/routers/library.py |

## What Was Built

### Backend (TACCMP-01/02/03 + TACUI-01 backend)

**`app/repositories/library_repository.py`**
- `FAMILY_TO_MOTIF_INTS: dict[str, list[int]]` — 6-family taxonomy mapping all 24 TacticMotifInt values exactly once (D-08)
- `_TACTIC_CHIP_CONFIDENCE_MIN: int = 70` — confidence threshold constant used at row-build time
- `fetch_tactic_comparison` — LEFT JOIN aggregation with 12 COUNT columns (6 families × player/opp), uses `is_opponent_expr` (never inline ply % 2), gates on `tactic_confidence >= min`
- Updated `query_flaws` row build to populate `tactic_motif` (string) / `tactic_confidence` (int) on `FlawListItem`, gated by confidence threshold
- Updated `_filtered_games_base` to accept and forward `tactic_families` param

**`app/repositories/query_utils.py`**
- `apply_game_filters()` extended with `tactic_families: Sequence[str] | None = None` param
- Uses correlated EXISTS (lazy import of `FAMILY_TO_MOTIF_INTS` from library_repository to avoid circular dep)
- Unknown family keys silently yield no ints (T-126-02 injection prevention)

**`app/schemas/library.py`**
- `TacticBullet` schema (family, you_rate, opp_rate, delta, ci_low/ci_high, p_value, you_events/opp_events, zone_lo/zone_hi=0.0, has_zone=False)
- `TacticComparisonResponse` schema (bullets, analyzed_n, analyzed_gate, below_gate)
- `FlawListItem` + `FlawMarker`: added `tactic_motif: str | None = None` and `tactic_confidence: int | None = None` (TACUI-01)

**`app/services/library_service.py`**
- `TACTIC_COMPARISON_GATE: int = 20` and `MIN_TACTIC_CHIP_CONFIDENCE: int = 70` (re-exported)
- `_compute_tactic_bullets` — aggregates per-game rows into ranked TacticBullet list (significant gap first by |delta|, volume fallback, cap at 6)
- `get_tactic_comparison` — full pipeline with Sentry capture, mirrors `get_flaw_comparison`
- `_build_eval_series` extended with `tactic_by_ply` param to populate FlawMarker chip data from game_flaws rows

**`app/routers/library.py`**
- `GET /tactic-comparison` endpoint, mirrors `/flaw-comparison` exactly plus `tactic_families` Query param
- from_date > to_date 422 guard; user_id from `current_active_user` only (T-126-01 IDOR prevention)
- Backend NOT beta-gated per D-01a

## Verification Results

```
uv run pytest -n auto tests/routers/test_library_tactic_comparison.py tests/services/test_tactic_comparison_service.py -x
# 13 passed

uv run pytest -n auto -x
# 2787 passed, 15 skipped, 3 warnings

uv run ty check app/ tests/
# All checks passed!

uv run ruff check app/ tests/
# All checks passed!

grep -nc 'ply % 2' app/repositories/library_repository.py
# 3 (all in comments only — no actual ply % 2 math)

FAMILY_TO_MOTIF_INTS coverage: sorted(all 24 motif ints) == list(range(1, 25)) ✓
```

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 - Missing critical] FlawMarker tactic field wiring**
- **Found during:** Task 2
- **Issue:** Plan said "do the equivalent wherever FlawMarker rows are built" but `_build_eval_series` had no access to `game_flaws` data
- **Fix:** Added `tactic_by_ply: dict[int, tuple[str, int]] | None = None` param to `_build_eval_series`; `_build_card` builds this dict from pre-fetched `flaw_rows` and passes it through. Backward compatible (defaults to None).
- **Files modified:** app/services/library_service.py

**2. [Rule 2 - Architecture] _TACTIC_CHIP_CONFIDENCE_MIN placement**
- **Found during:** Task 2
- **Issue:** Plan said constant lives in `library_service.py` but `query_flaws` (repo layer) needs it without a service import (circular dep)
- **Fix:** Defined `_TACTIC_CHIP_CONFIDENCE_MIN` in `library_repository.py`; `library_service.py` re-exports it as `MIN_TACTIC_CHIP_CONFIDENCE` via import. No duplication.
- **Files modified:** app/repositories/library_repository.py, app/services/library_service.py

## Known Stubs

None — all functionality is wired. `has_zone=False` on TacticBullet is intentional per plan (no tactic benchmark pipeline this phase per CONTEXT §Deferred).

## Threat Flags

None — all STRIDE threats from the plan's threat register are mitigated:
- T-126-01 (IDOR): user_id from current_active_user only, router test confirms 401 without auth
- T-126-02 (injection): tactic_families mapped through FAMILY_TO_MOTIF_INTS dict lookup, unknown keys produce empty int list
- T-126-03 (beta gate): frontend-only gate per D-01a, accepted residual
- T-126-04 (DoS): same gate + analyzed-set bounding as /flaw-comparison

## Self-Check: PASSED

All created/modified files exist on disk. All 5 task commits verified in git log.
- 2787 backend tests pass, 0 failures
- ty check: zero errors
- ruff check: zero errors
- FAMILY_TO_MOTIF_INTS: all 24 motif ints covered exactly once
