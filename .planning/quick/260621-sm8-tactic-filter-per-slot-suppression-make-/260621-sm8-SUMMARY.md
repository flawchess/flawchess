---
phase: quick
plan: 260621-sm8
subsystem: library
tags: [tactic-filter, per-slot-suppression, depth-filter, orientation-filter, bug-fix]
depends_on: [260621-qz9]
provides: [tactic-slot-visibility-predicate, independent-depth-orientation-filter]
affects: [library_repository, library_service, LibraryGameCard]
tech-stack:
  patterns: [shared-predicate, per-slot-suppression, orientation-aware-filter]
key-files:
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - frontend/src/lib/tacticDepth.ts
    - frontend/src/hooks/useFlawFilterStore.ts
    - frontend/src/components/results/LibraryGameCard.tsx
    - tests/repositories/test_library_repository.py
    - tests/services/test_library_service.py
    - tests/test_library_repository.py
    - frontend/src/lib/__tests__/tacticDepth.test.ts
    - frontend/src/hooks/__tests__/useFlawFilterStore.test.ts
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
decisions:
  - "tactic_slot_visible() defined once in library_repository, imported into library_service"
  - "build_flaw_filter_clauses default orientation changed to 'either' (was 'allowed') so non-tactic callers emit no clause"
  - "Unknown tactic families still silently dropped (resolved_families guard preserves pre-existing test contract)"
  - "isTacticFilterActive() as proxy for backend nulling: hides empty tactic columns only when filter is non-default"
metrics:
  completed: 2026-06-21
status: complete
---

# Quick 260621-sm8: Tactic Filter Per-Slot Suppression Summary

Per-slot suppression at both serialization sites; depth and orientation independently meaningful; High preset as out-of-box default.

## Objective

Fix the tactic filter so depth and orientation controls are independently meaningful (not silent no-ops when no family is selected). Apply per-slot suppression at both `/library/flaws` and `/library/games` serialization sites, nulling non-matching slots. Flip the default depth preset to High (full range) so the out-of-box state shows all tactics.

## What Was Built

### Task 1: Shared `tactic_slot_visible()` predicate + independent depth/orientation in `build_flaw_filter_clauses` (commit `69acc6e3`)

**Bug fixed:** Depth and orientation predicates were nested inside `if tactic_families:` in `build_flaw_filter_clauses`, making them silent no-ops when no family chip was selected.

**New constants:**
- `_TACTIC_DEPTH_FULL_MIN = 0`, `_TACTIC_DEPTH_FULL_MAX = 11` — domain boundaries for "full range" detection
- `_tactic_controls_active()` — returns True when any of family/orientation/depth departs from all-inclusive defaults

**New exported function `tactic_slot_visible()`:** Single shared predicate used at both serialization sites. A slot is visible when:
1. Orientation matches scope (missed/allowed/either)
2. Confidence >= `_TACTIC_CHIP_CONFIDENCE_MIN` (70)
3. Family: no families selected OR motif in selected families
4. Depth: full range OR (depth + decision-anchor offset) in [min, max]

**`build_flaw_filter_clauses` refactor:**
- Resolves family strings to known `motif_ints` before `_tactic_controls_active` check (unknown families silently dropped, preserving pre-existing test contract)
- Default orientation changed from `"allowed"` to `"either"` so callers without tactic params (e.g. `flaw_exists_from_table`) emit no tactic clause

**`query_flaws` slot emission:** Rewrote to call `tactic_slot_visible` per slot instead of bare confidence gate.

### Task 2: Thread tactic params to `_build_card` + null non-matching slots (commit `b026951b`)

**`library_service.py`:**
- Added `tactic_slot_visible` import from `app.repositories.library_repository`
- `_build_card` signature extended with 4 tactic params (`tactic_families`, `tactic_orientation`, `min_tactic_depth`, `max_tactic_depth`)
- `tactic_by_ply` building loop now calls `tactic_slot_visible` for both missed/allowed slots — sets slot to `None` when not visible
- `get_library_games` call updated to pass tactic params through to `_build_card`
- Single-game path (`get_library_game`) unchanged — passes defaults (all-inclusive)

### Task 3: Default depth preset High + hide empty tactic columns on Games card (commit `ead6ce4c`)

**`tacticDepth.ts`:** `DEPTH_DEFAULT_PRESET` changed from `'medium'` to `'high'`; `DEFAULT_TACTIC_DEPTH_VALUE` now `{0, 11}`.

**`useFlawFilterStore.ts`:** Added `isTacticFilterActive(filter)` — True when any tactic control (family, orientation, or depth) departs from all-inclusive default. Used by `LibraryGameCard` to distinguish filtered-empty from genuinely-no-tactics.

**`LibraryGameCard.tsx`:** Added dynamic grid-cols based on visible tactic columns:
- When `isTacticFilterActive` is True, orientation columns with no chips are hidden (`null`)
- `md:grid-cols-1/2/3` set dynamically from `visibleTacticColCount + 1`

### Task 4: Tests (commit `717ebeaa`)

**`tests/repositories/test_library_repository.py`** (new file):
- `TestTacticSlotVisible` — 9 pure unit tests for `tactic_slot_visible` (confidence gate, orientation scope, family filter, depth with/without allowed offset)
- `TestQueryFlawsPerSlotSuppression` — 4 DB integration tests: scenarios (a) no filter shows both slots, (b) orientation=missed nulls allowed, (c) orientation=allowed nulls missed, (d) family filter nulls non-matching family

**`tests/services/test_library_service.py`** (additions):
- `TestBuildCardTacticPerSlotSuppression` — 2 tests: default filter shows both slots; orientation filter on games path nulls excluded slot

### Task 5: Pre-merge gate (commits `cecb023b`, `6a913c71`)

Multiple gate-driven fixes:

**Backend (`cecb023b`):**
- `build_flaw_filter_clauses` default orientation `"allowed"` → `"either"` (prevented `flaw_exists_from_table` from emitting spurious tactic clause)
- `resolved_families` guard for unknown-only family inputs
- Updated `TestTacticOrientationBuildFlawFilterClauses.test_default_orientation_references_allowed_column` → `test_default_orientation_references_both_columns` to match new `"either"` default

**Frontend (`6a913c71`):**
- `tacticDepth.test.ts`: `DEPTH_DEFAULT_PRESET` assertion updated to `'high'`; `DEFAULT_TACTIC_DEPTH_VALUE` to `{0, 11}`
- `useFlawFilterStore.test.ts`: Default filter assertions updated to `{0, 11}`; test cases for Medium as non-default, `{0, 11}` as default
- `LibraryGameCard.test.tsx` + `FlawCard.test.tsx`: Added `isTacticFilterActive: () => false` to `vi.mock` stubs for `useFlawFilterStore`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `build_flaw_filter_clauses` default orientation broke `flaw_exists_from_table` and existing predicate tests**

- **Found during:** Task 5 (pre-merge gate — full pytest run)
- **Issue:** The original default `orientation="allowed"` in `build_flaw_filter_clauses` was a no-op under the old `if tactic_families:` guard. After removing that guard, calling with default params emitted an orientation-restricted tactic clause that `flaw_exists_from_table` never expected. Tests `test_empty_severity_and_tags_returns_no_clauses`, `test_unknown_tactic_family_adds_no_clause`, and `test_default_orientation_references_allowed_column` all failed.
- **Fix:** Changed default from `"allowed"` to `"either"` (the neutral all-inclusive value); computed `resolved_families` before `_tactic_controls_active` so unknown-only family specs still produce no clause; updated the pre-existing `test_default_orientation_references_allowed_column` test to assert the new `"either"` behaviour (both columns in scope).
- **Files modified:** `app/repositories/library_repository.py`, `tests/test_library_repository.py`
- **Commit:** `cecb023b`

**2. [Rule 1 - Bug] Frontend tests referencing old `"medium"` default preset failed; mocks missing `isTacticFilterActive`**

- **Found during:** Task 5 (frontend test run)
- **Issue:** `tacticDepth.test.ts` and `useFlawFilterStore.test.ts` hard-coded `{0, 5}` as the default depth value. `LibraryGameCard.test.tsx` and `FlawCard.test.tsx` mocked `useFlawFilterStore` without exporting `isTacticFilterActive`, causing a Vitest "no export defined" error.
- **Fix:** Updated all four test files to reflect the new `'high'` / `{0, 11}` default; added `isTacticFilterActive: () => false` to both mock stubs.
- **Files modified:** 4 frontend test files
- **Commit:** `6a913c71`

**3. [Rule 1 - Bug] Redundant `cast(object, ...)` warnings in service tests**

- **Found during:** Task 5 (ty check)
- **Issue:** `tests/services/test_library_service.py` used `cast(object, game)` where `game` was already typed as `object`, generating ty redundant-cast warnings.
- **Fix:** Removed the redundant casts, using `game` directly.
- **Files modified:** `tests/services/test_library_service.py`
- **Commit:** `cecb023b`

## Pre-existing Issues (Not Introduced by This Task)

`tests/test_library_repository.py` (the root-level pre-existing test file) has 14 ty errors at lines 738 and 744 — `**_kwargs` spread typing mismatch with `count_filtered_and_analyzed`. These were present before this task (21 errors before, 14 after — my changes actually reduced them by 7). The pre-existing `count_filtered_and_analyzed` typing mismatch is a deferred item.

## Known Stubs

None. All slots are fully wired through to the API response.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

All key files found. All commits verified:
- `69acc6e3` — feat: shared predicate + independent depth/orientation
- `b026951b` — feat: thread tactic params to _build_card
- `ead6ce4c` — feat: High default preset + hide empty columns
- `717ebeaa` — test: per-slot suppression tests
- `cecb023b` — fix: default orientation to 'either'
- `6a913c71` — test: frontend tests for High preset + isTacticFilterActive

Backend: 2853 passed, 15 skipped. Frontend: 1079 passed (90 test files).

## Follow-up (commit a134374e) — two more gaps the filter exposed

UAT surfaced that opening a game from a flaw card still showed out-of-filter
tactics. Root cause: the single-game path was deliberately left at filter
defaults in this task, but flaw cards open *into* it.

- **View-game modal** (`GET /library/games/{id}` → `get_library_game`): now
  accepts the four tactic params and threads them to `_build_card` (same shared
  `tactic_slot_visible` predicate). Frontend: `FlawCard` → `useLibraryGame` →
  `getGame` forward the active `useFlawFilterStore` filter; tactic params join
  the query key so changing the filter refetches the open modal.
- **`useLibraryGames` gating**: it sent depth/orientation only when a family was
  selected, so a depth-only or orientation-only filter never reached the
  Games-tab list (same defect class as the original bug, on the Games surface).
  Depth + orientation are now always sent (default = backend no-op).
- Tests added: single-game depth-filter nulling + default-unaffected (service);
  Games-list depth-only + default-state param wiring; `useLibraryGame` forwards
  the filter (frontend).
- Full gate re-run green: backend 2855 passed/15 skipped, ty app/ zero
  (tests/ 14 pre-existing, 0 new), frontend lint + 1081 tests + tsc -b.

## Follow-up 2 (commit 3ca0e55e) — Games-tab row filter ignored depth/orientation

UAT: Games count stayed "5130 of 5138" regardless of depth. The per-slot chip
nulling worked, but games with no matching tactic still appeared. Root cause:
the Games-tab tactic EXISTS row-filter lives in a SEPARATE block
(`apply_game_filters` in `query_utils.py`) that was still gated on
`if tactic_families:` — sm8 only fixed the Flaws-path `build_flaw_filter_clauses`.

- Gate the EXISTS on `_tactic_controls_active` (family OR orientation OR depth),
  family-match term optional per branch — mirrors `build_flaw_filter_clauses`.
- Flipped the vestigial `"allowed"` default orientation → `"either"` on
  `apply_game_filters`, `_filtered_games_base`, `count_filtered_and_analyzed`.
  Required because the EXISTS can now activate on orientation alone, so an
  `"allowed"` default would make non-tactic callers (endgame/openings/stats and
  the coverage/comparison counts) wrongly filter. No caller relied on it.
- Tests: Games row-filter restricts by depth-only + orientation-only (no family);
  default-state guard that non-tactic games still appear; updated the
  query_utils default-orientation SQL test (now expects both columns).
- Gate green: backend 2858 passed/15 skipped, ty app/ zero (tests/ 14
  pre-existing). Frontend unchanged this round.
