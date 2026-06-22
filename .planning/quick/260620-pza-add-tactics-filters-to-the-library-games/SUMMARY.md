---
quick_id: 260620-pza
slug: add-tactics-filters-to-the-library-games
date: 2026-06-20
status: complete
---

# Summary: Tactic filters on Library Games tab + missed/allowed card chips

## What changed

Two user-facing changes, both replicating Flaws-tab patterns onto the Games tab.

### 1. Tactic filters on the Games tab
The Games tab Tags panel now renders the same tactic-filter section the Flaws tab has
(`showTacticFilter`): the tactic-family tag group (OR within group, AND across the other
filter groups), the Missed/Allowed orientation toggle, and the tactic-difficulty depth
range. Selecting ≥1 tactic family narrows the games list to games containing at least one
flaw whose tactic matches a selected family (the orientation's column, within the depth
range). The backend tactic `EXISTS` in `apply_game_filters` already existed; it just was
never threaded to the Games path.

### 2. Missed/allowed tactic chips on game cards
`LibraryGameCard` now surfaces BOTH tactic orientations as separate chips: "allowed: fork"
and "missed: fork" are distinct chips (previously only `allowed_tactic_motif` showed). The
backend already populated both columns on the card markers, so this was frontend-only.

## Files touched

Backend (param threading only — filter core untouched):
- `app/routers/library.py` — `get_library_games`: added `tactic_family`, `tactic_orientation`
  (default "either"), `min_tactic_depth`, `max_tactic_depth` Query params + forwarding.
- `app/services/library_service.py` — `get_library_games`: same params forwarded to repo.
- `app/repositories/library_repository.py` — `query_filtered_games`: same params → `apply_game_filters`.

Frontend:
- `frontend/src/api/client.ts` — `getGames`: added tactic params (mirrors `getFlaws`).
- `frontend/src/hooks/useLibrary.ts` — `useLibraryGames`: tactic params + query key, gated on a
  family being selected (orientation/depth are inert without a family).
- `frontend/src/pages/library/GamesTab.tsx` — pass `showTacticFilter` + tactic props to
  `FlawFilterControl` (desktop panel + mobile drawer).
- `frontend/src/components/results/LibraryGameCard.tsx` — `FlawRef`/`sameFlawRef`/`motifPlies`/
  `highlightedPlies`/`pliesForRef`/`tacticMotifs`/render now carry orientation so both
  orientations render and cycle/highlight independently.

Tests:
- `tests/test_library_repository.py` — extended `_seed_game_flaw` (tactic cols) + 2 integration
  tests (tactic-family narrowing, orientation narrowing) on `query_filtered_games`.
- `tests/test_library_router.py` — `TestGetLibraryGamesTacticParamThreading` (forwarding, defaults, 422).
- `frontend/.../useLibraryGames.test.tsx` — 2 tactic-param tests.
- `frontend/.../GamesTab.test.tsx` — asserts `showTacticFilter` enabled.
- `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx` — NEW: missed/allowed chip rendering.

Docs: `CHANGELOG.md` — two `### Added` bullets.

## Decisions

- "Like in the Flaws tab" → enabled the full tactic section (families + orientation + depth)
  via `showTacticFilter`, since `FlawFilterControl` bundles them. The depth filter is
  always-on with the Intermediate {0,5} default (same as Flaws), so deep tactics are excluded
  until the user widens the range — consistent parity, not a regression.
- Chip prefix uses the existing component value `allowed:` (not `allow:`) for app-wide consistency.
- Games-tab tactic params are sent only when ≥1 family is selected (the backend EXISTS is a
  no-op without one), keeping the default games query identical to before.

## Verification

All pre-merge gates green:
- Backend: `ruff format`/`ruff check`/`ty check` clean; full `pytest -n auto -x` = 2829 passed, 15 skipped.
- Frontend: `eslint`/`knip` clean; `tsc -b` clean; `vitest run` = 1072 passed (90 files).

## Notes / follow-ups

- The card renders `flawContent` in both a mobile (`sm:hidden`) and desktop body, so each chip
  appears twice in jsdom (CSS hides one at runtime). The new card test uses
  `getAllByTestId`/`queryAllByTestId` accordingly — not a defect.
- HUMAN-UAT (optional): visually confirm in the running app (beta user) that the Games tab
  tactic filter narrows the list and both missed/allowed chips appear on cards.
