---
phase: 128-missed-opportunity-tagging
plan: "03"
subsystem: library-orientation-filter
tags: [tactic-orientation, filter, schema, library]
status: complete

dependency_graph:
  requires:
    - 128-01  # renamed ORM columns to allowed_tactic_* / missed_tactic_*
    - 128-02  # both-orientation flaw classifier
  provides:
    - orientation-aware tactic filter at apply_game_filters + library_repository
    - both orientation column sets on FlawMarker, FlawListItem, FlawCard schemas
  affects:
    - app/repositories/query_utils.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/results/LibraryGameCard.tsx

tech_stack:
  added: []
  patterns:
    - TacticOrientation = Literal["missed", "allowed"] closed enum (T-128-05)
    - _tactic_cols(orientation) helper returns (motif_col, conf_col) ORM attr pair
    - Default "allowed" preserves all existing Library caller behavior (D-08)

key_files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/repositories/query_utils.py
    - app/services/library_service.py
    - app/schemas/library.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - tests/test_query_utils.py
    - tests/test_library_repository.py
    - tests/services/test_tactic_comparison_service.py

decisions:
  - "_tactic_cols(orientation) helper in library_repository.py centralizes column selection; imported at query_utils.py to avoid duplicating the conditional at each call site"
  - "tactic_by_ply dict in library_service changed from dict[int, tuple[str, int]] to dict[int, tuple[str|None, int|None, str|None, int|None]] carrying (allowed_motif, allowed_conf, missed_motif, missed_conf); single-dict approach avoids a parallel second dict"
  - "Frontend migrated to allowed_tactic_motif for current behavior; Phase 129 wires the orientation toggle UI"

metrics:
  duration: "~145 minutes (split across two sessions)"
  completed: "2026-06-19"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 13
---

# Phase 128 Plan 03: Orientation Filter and Schema Contract Summary

Orientation-aware tactic filter contract and schema rename that Phase 129's UI toggle binds to. Both filter sites thread a `TacticOrientation = Literal["missed", "allowed"]` param (defaulting to `"allowed"`) and the flaw/marker/list schemas expose all four orientation-labeled fields.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rename ripple — verify bare tactic_* refs | 136b3818 (bundled) | confirmed clean via grep |
| 2 (TDD) | Orientation dimension at both filter sites | d276f6d0 (RED), 136b3818 (GREEN) | query_utils.py, library_repository.py, library_service.py |
| 3 | Both orientation column sets on schemas | ee0cd431 | schemas/library.py, library.ts, frontend components |

## What Was Built

### TacticOrientation closed enum (T-128-05)

`TacticOrientation = Literal["missed", "allowed"]` defined in `library_repository.py`, imported by `query_utils.py`. No raw column-name interpolation; orientation maps to a fixed ORM-column pair via `_tactic_cols()`.

### _tactic_cols(orientation) helper

```python
def _tactic_cols(orientation: TacticOrientation) -> tuple[Any, Any]:
    if orientation == "missed":
        return GameFlaw.missed_tactic_motif, GameFlaw.missed_tactic_confidence
    return GameFlaw.allowed_tactic_motif, GameFlaw.allowed_tactic_confidence
```

Returns the `(motif_col, conf_col)` ORM attribute pair for the given orientation. Used at both filter sites and the chip-read producer.

### Filter site 1: apply_game_filters (query_utils.py)

Added `orientation: Literal["missed", "allowed"] = "allowed"` param. The `tactic_families` EXISTS subquery now selects the column pair via `_tactic_cols(orientation)`.

### Filter site 2: library_repository (build_flaw_filter_clauses, query_flaws, fetch_tactic_comparison)

`build_flaw_filter_clauses` and `query_flaws` accept `orientation: TacticOrientation = "allowed"`. `fetch_tactic_comparison` similarly threaded. Defaults preserve existing behavior (D-08).

### Schema renames (D-07)

**FlawMarker** and **FlawListItem** in `app/schemas/library.py`:
- Removed: `tactic_motif: str | None`, `tactic_confidence: int | None`
- Added: `allowed_tactic_motif: str | None = None`, `allowed_tactic_confidence: int | None = None`, `missed_tactic_motif: str | None = None`, `missed_tactic_confidence: int | None = None`

### Chip-read producer (library_repository.query_flaws)

Populates all four fields. Each pair is gated by `_TACTIC_CHIP_CONFIDENCE_MIN` independently:
- allowed pair: from `fr.allowed_tactic_motif / fr.allowed_tactic_confidence`
- missed pair: from `fr.missed_tactic_motif / fr.missed_tactic_confidence`

### tactic_by_ply in library_service

Extended from `dict[int, tuple[str, int]]` to `dict[int, tuple[str | None, int | None, str | None, int | None]]` carrying `(allowed_motif, allowed_conf, missed_motif, missed_conf)`. `_build_eval_series` updated to unpack and populate all four `FlawMarker` orientation-labeled fields.

### Frontend types and components

`FlawMarker` and `FlawListItem` in `frontend/src/types/library.ts` mirror the backend rename. `EvalChart.tsx`, `FlawCard.tsx`, `LibraryGameCard.tsx`, `TacticMotifChip.tsx` migrated to `allowed_tactic_motif` to preserve current behavior. Phase 129 will wire the orientation UI toggle.

## TDD Gate Compliance

- RED commit `d276f6d0`: 9 failing tests across `TestTacticOrientationFilter` and `TestTacticOrientationBuildFlawFilterClauses`
- GREEN commit `136b3818`: all 9 orientation tests pass (38 total in the two files)
- REFACTOR: none required (implementation clean on first pass)

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `grep -rn "GameFlaw.tactic_" app/` | 0 matches |
| `grep -c "[^_]tactic_motif:" app/schemas/library.py` | 0 |
| `uv run ty check app/ tests/` | All checks passed |
| `uv run ruff check app/ tests/` | All checks passed |
| `uv run pytest -n auto -x` | 2818 passed, 15 skipped |
| Frontend `npm run lint` | Clean |
| Frontend `npx tsc -b` | Clean |
| Frontend `npm test -- --run` | 989 passed |
| `grep -c "FAMILY_TO_MOTIF_INTS" app/repositories/library_repository.py` | Single definition (D-09) |

## Deviations from Plan

### Auto-added: Frontend type and component migration

- **Found during:** Task 3
- **Issue:** Backend schema field renames (`tactic_motif` → `allowed_tactic_motif`) broke TypeScript types and components that read the old field names.
- **Fix:** Updated `frontend/src/types/library.ts` (both FlawMarker and FlawListItem interfaces), plus `EvalChart.tsx`, `FlawCard.tsx`, `LibraryGameCard.tsx`, `TacticMotifChip.tsx` to use `allowed_tactic_motif`. Each component now uses `allowed_tactic_motif` for current rendering; Phase 129 will add the orientation toggle.
- **Files modified:** `frontend/src/types/library.ts`, 4 frontend components
- **Commit:** ee0cd431
- **Rule:** Rule 3 (blocking issue — TypeScript and frontend tests would fail without this)

### Auto-fixed: ruff format reformatting

- **Found during:** Task 3 (pre-commit run)
- **Fix:** `ruff format` applied whitespace changes to `app/repositories/library_repository.py` and `tests/services/test_flaws_service.py`
- **Commit:** ee0cd431 (staged alongside Task 3 changes)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries beyond what the plan's threat model covers. T-128-05 mitigated: `TacticOrientation` is a closed `Literal` enum; `_tactic_cols()` maps it to a fixed ORM-column pair with no raw column-name interpolation.

## Self-Check: PASSED

- [x] `app/repositories/library_repository.py` exists
- [x] `app/schemas/library.py` exists
- [x] `app/services/library_service.py` exists
- [x] `frontend/src/types/library.ts` exists
- [x] Commit d276f6d0 (TDD RED) exists
- [x] Commit 136b3818 (TDD GREEN / Task 1+2) exists
- [x] Commit ee0cd431 (Task 3) exists
- [x] `grep -rn "GameFlaw.tactic_" app/` = 0 matches
- [x] `grep -c "[^_]tactic_motif:" app/schemas/library.py` = 0
