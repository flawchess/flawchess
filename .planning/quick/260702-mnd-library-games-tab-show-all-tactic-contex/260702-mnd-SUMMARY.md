---
quick_id: 260702-mnd
title: Library Games tab — show all tactic + context tags on every selected card
status: complete
date: 2026-07-02
commit: af25d3a9
---

# Summary — 260702-mnd

Decoupled "filter selects which games appear" from "filter prunes which tags show on
the card" for the Library Games tab. The active tactic/severity/context/depth/orientation
filter now only decides WHICH games are returned; every returned card shows its full set
of tactic + context tags, with the active-filter ring lighting only on chips that truly
match the filter across all axes.

## What changed

### Backend (Task 1)

- `app/services/library_service.py` `_build_card`: dropped the five pruning params
  (`flaw_severity`, `tactic_families`, `tactic_orientation`, `min_tactic_depth`,
  `max_tactic_depth`). The `tactic_by_ply` construction loop now calls
  `tactic_slot_visible(...)` with filter-neutral arguments (`tactic_families=()`,
  `tactic_orientation="either"`, no depth bounds) and no longer gates on severity
  (`severity_ints` computation + guard removed — D-1). Only the two validity gates
  remain: `decided_lost` and the confidence floor.
- `get_library_games` stops forwarding the pruning params into `_build_card` (game
  SELECTION via `query_filtered_games` is unchanged — it still keeps its own filter
  params for that purpose).
- `get_library_game` (the single-game "View game" path) and its router endpoint shed
  the now-dead `flaw_severity`/`tactic_family`/`tactic_orientation`/`*_tactic_depth`
  params entirely (D-3) — the single-game path does no game selection, so those params
  only ever drove the now-removed per-slot pruning.
- Docstrings rewritten to describe the new selection-only semantics.

### Frontend (Task 2)

- `LibraryGameCard.tsx`: `outlinedPlies` (the context-filter set) no longer gates the
  tactic-chip derivations (`motifPlies`, `tacticMotifs`, `highlightedPlies`) — every
  user tactic chip renders and highlights unconditionally, matching context chips.
  `outlinedPlies` keeps its sole remaining role: driving the eval-chart white marker
  outline.
- Added depth-aware active-filter ring (D-2, the plan's preferred option): a new
  `tacticFilterActive` boolean (true when family/orientation/depth axis is non-default)
  and a `matchingFilterKeys` memo using the existing `resolveVisibleTactic` helper
  (mirrors the backend `tactic_slot_visible` across all axes including depth) to decide,
  per chip, whether it truly matches the active filter.
- `TacticMotifChip.tsx` gained an optional `filterRingActive` prop that overrides the
  legacy store-derived (family+orientation only) ring; `undefined` preserves the old
  behavior for `FlawCard`, which passes no override. `TacticMotifGroup.tsx` forwards the
  prop through.
- `renderChipsBlock()` is the single shared source feeding both the mobile and desktop
  bodies, so the change lands on both breakpoints from one call site.

### Frontend cleanup (Task 3, D-3)

- `frontend/src/api/client.ts` `getGame`: dropped the `params` argument entirely — a
  plain `GET /library/games/${gameId}` with no query params.
- `frontend/src/hooks/useLibrary.ts` `useLibraryGame`: dropped the `flawFilter`
  parameter and every derived query param; `queryKey` simplified to
  `['library-game', gameId]`. Sole caller (`Analysis.tsx`) already passed no filter, so
  no behavior change there.
- `CHANGELOG.md`: added an `## [Unreleased] / ### Changed` bullet.

## Test changes

- `tests/services/test_library_service.py` (`TestBuildCardTacticPerSlotSuppression`):
  flipped `test_single_game_depth_filter_nulls_out_of_range_slot` →
  `test_single_game_shows_all_tactic_slots_depth_filter_removed` (both slots now
  populated); flipped `test_severity_filter_gates_tactic_slots_in_games_response` →
  `test_severity_filter_no_longer_gates_tactic_slots_in_games_response` (both plies'
  tactics survive under every severity value); flipped
  `test_single_game_severity_filter_gates_tactic_slots` →
  `test_single_game_shows_all_severities_severity_param_removed`. Kept
  `test_default_filter_both_slots_populated_in_games_response` and
  `test_single_game_default_filter_unaffected` as regression guards. Left
  `test_orientation_filter_nulls_excluded_slot_in_flaw_markers` unchanged (it exercises
  `query_flaws`, the Flaws subtab, which still prunes per-slot — comment added
  clarifying scope). Added a new lock-in test,
  `test_games_filter_selects_only_card_content_shows_every_motif`, seeding two tactic
  flaws where only one matches an active `tactic_families`+depth filter (selecting the
  game) and asserting BOTH survive on the card.
- `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx`: flipped the
  "gated by active context filter" describe block to assert chips are NOT hidden by an
  active context filter; added a new describe block covering the depth-aware ring
  (in-range chip rings, out-of-range same-family chip does not; no ring at all when no
  tactic filter is active). Extended the mocked flaw-filter store to include the full
  `FlawFilterState` shape (`tacticFamilies`/`tacticOrientation`/`tacticDepthMin`/
  `tacticDepthMax`) needed by the new ring logic.
- `frontend/src/hooks/__tests__/useLibraryGame.test.tsx`: dropped the
  "forwards the active tactic filter" test and the forwarded-param assertions;
  `getGame` is now asserted to be called with only `gameId`.

## Decisions (user-confirmed before execution)

- **D-1**: the severity filter also stops pruning tactic tags (not just the tactic
  family/orientation/depth params named in the original ask) — keeps tactic chips
  consistent with context chips, which never pruned by severity.
- **D-2**: depth-aware filter ring (the plan's preferred option) — chips render
  unconditionally, but the active-filter ring only lights on chips that match the full
  filter including depth, via the existing `resolveVisibleTactic` helper.
- **D-3**: removed the now-dead single-game filter params end-to-end (router → service
  → frontend client → hook), since they existed only to drive the now-removed pruning
  and the single-game path does no game selection.

## Deviations from Plan

None — plan executed as written (with the three flagged decisions confirmed by the
user before execution).

## Verification

- `uv run ruff format app/ tests/`: 268 files left unchanged.
- `uv run ruff check app/ tests/ --fix`: All checks passed.
- `uv run ty check app/ tests/`: All checks passed (0 errors).
- `uv run pytest -n auto -x`: 3101 passed, 18 skipped (full backend suite, dev DB via
  `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`, started for this
  run — it was not already running).
- `cd frontend && npx tsc -b`: clean (no output = success).
- `cd frontend && npm run lint`: clean.
- `cd frontend && npm run knip`: clean.
- `cd frontend && npm test -- --run`: 106 test files, 1245 tests passed.

## Commits

- `b4375240` — feat(quick-260702-mnd): stop pruning tactic tags in Games card; shed dead single-game filter params
- `1fe6e04c` — feat(quick-260702-mnd): render all tactic chips on Games cards; depth-aware active-filter ring
- `af25d3a9` — refactor(quick-260702-mnd): remove dead single-game filter forwarding (D-3)
- `61320363` — docs(changelog): note Library Games cards now show all tactic + context tags

## Self-Check: PASSED

All 12 files created/modified verified present on disk; all 4 commit hashes verified
present in `git log --oneline --all`.
