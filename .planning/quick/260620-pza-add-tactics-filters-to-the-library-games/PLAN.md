---
quick_id: 260620-pza
slug: add-tactics-filters-to-the-library-games
date: 2026-06-20
---

# Quick Task: Tactic filters on Library Games tab + missed/allowed card chips

## Goal

Two related changes, both replicating patterns that already exist on the Flaws tab:

1. **Tactic filters on the Games tab.** The Tags filter panel on the Games tab
   currently exposes only severity + context tags. Surface the same tactic-filter
   section the Flaws tab already has (`showTacticFilter`): the tactic-family tag
   group (OR within group, AND across groups — same logic as the context filters),
   plus the orientation toggle and depth filter that the shared `FlawFilterControl`
   bundles under that flag. Selecting ≥1 tactic family narrows the games list to
   games containing at least one flaw matching a selected tactic.

2. **Missed/allowed prefixes on game-card tactic chips.** `LibraryGameCard` currently
   renders only `allowed_tactic_motif` chips. Surface BOTH orientations as separate
   chips with the orientation prefix the `TacticMotifChip` already supports — e.g.
   `missed: fork` and `allowed: fork` are two distinct chips.

## Context (verified)

- The backend `apply_game_filters` (query_utils.py) ALREADY accepts `tactic_families`,
  `orientation`, `min_tactic_depth`, `max_tactic_depth` and builds the correlated
  `EXISTS` over `game_flaws`. The Games path (`query_filtered_games`) simply never
  threads them. Three backend layers need the params added; the filter core is untouched.
- The backend ALREADY populates both `allowed_tactic_motif` and `missed_tactic_motif`
  on `FlawMarker` for game cards (library_service.py `_build_card`/markers, confidence-gated).
  So change #2 is frontend-only.
- `FlawFilterControl` already fully implements the tactic section behind `showTacticFilter`.
  GamesTab just needs to pass the same props FlawsTab passes (desktop + mobile).
- `TacticMotifChip` already supports the `orientation` prop → `"missed: fork"` label,
  orientation-scoped aria-label + testid.
- `isFlawFilterNonDefault` already counts the tactic fields, so the modified-dot and the
  games-query gate light correctly when a tactic family / non-default orientation/depth is set.

## Tasks

### Backend (thread tactic params through the Games path)
1. `app/repositories/library_repository.py` — `query_filtered_games`: add
   `tactic_families`, `orientation` (default `"either"`), `min_tactic_depth`,
   `max_tactic_depth` params; forward to `apply_game_filters`.
2. `app/services/library_service.py` — `get_library_games`: add the same params; forward to repo.
3. `app/routers/library.py` — `get_library_games`: add `tactic_family`,
   `tactic_orientation` (default `"either"`), `min_tactic_depth`/`max_tactic_depth`
   Query params (mirror `get_library_flaws`); pass to the service.

### Frontend (Games tab filter wiring)
4. `frontend/src/api/client.ts` — `getGames`: add the tactic params (mirror `getFlaws`).
5. `frontend/src/hooks/useLibrary.ts` — `useLibraryGames`: add tactic_family /
   orientation / depth to the params + query key (mirror `useLibraryFlaws`).
6. `frontend/src/pages/library/GamesTab.tsx` — pass `showTacticFilter` + tactic props
   to `FlawFilterControl` in BOTH the desktop panel and the mobile drawer (mirror FlawsTab).

### Frontend (game-card missed/allowed chips)
7. `frontend/src/components/results/LibraryGameCard.tsx` — surface both orientations:
   - `FlawRef` motif variant carries `orientation: 'missed' | 'allowed'`; update `sameFlawRef`.
   - `tacticMotifs` collects `{ motif, orientation }` entries (deduped per orientation+label).
   - `motifPlies` keyed by `${orientation}:${label}`; reads the matching orientation column.
   - `highlightedPlies` + `pliesForRef` honor orientation.
   - Render one `TacticMotifChip` per entry, passing `orientation`; legend gets unique labels.

### Tests
8. Backend: extend `_seed_game_flaw` (tactic cols) + add a `query_filtered_games`
   tactic-family integration test in `tests/test_library_repository.py`.
9. Frontend: add tactic-param assertions to `useLibraryGames.test.tsx`; assert the tactic
   section renders on `GamesTab.test.tsx`; assert missed+allowed chips on the card test.

## Verification
- `uv run ruff format/check`, `uv run ty check app/ tests/`, `uv run pytest -n auto -x`
- `cd frontend && npm run lint && npm test -- --run && npx tsc -b`

## Decisions / notes
- "Like in the Flaws tab" → full tactic section (families + orientation + depth) via
  `showTacticFilter`, since `FlawFilterControl` bundles them. Not just the family chips.
- Chip prefix uses the existing component value `allowed:` (not `allow:`) for consistency
  with the rest of the app; the user's `allow:` was shorthand.
