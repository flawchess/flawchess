---
quick_id: 260717-rbn
description: Add Best + Good move tiers to analysis board and library game card
date: 2026-07-17
status: complete
commits:
  - f5ca1cc1 feat(260717-rbn): emit best/good move-quality tiers from _build_eval_series
  - 931802d7 feat(260717-rbn): green star/thumbs-up corner glyphs for best/good tiers
---

# Quick Task 260717-rbn: Best + Good move tiers

## Outcome

Added two new query-time move-quality tiers (`best`, `good`) alongside the
existing `gem`/`great` tiers, surfaced as green corner glyphs on the analysis
board (both players) and the library game-card mini-board (user-scoped). No DB
schema changes, no engine work, zero impact on the running tier-4b backfill —
both tiers are pure functions of already-stored `game_positions` data.

## Task 1 — Backend (`f5ca1cc1`)

- Widened `EvalPoint.best_move_tier` in `app/schemas/library.py` to
  `Literal['gem','great','best','good'] | None`.
- `app/services/library_service.py`:
  - Added `_best_move_identity_plies` — the `best` tier, decided by a UCI
    Move-object replay comparison (played SAN parsed on the pre-move board vs
    `game_positions.best_move` parsed from UCI), NOT a SAN==UCI string compare
    (which silently never matches).
  - `good` tier reuses the existing `_run_all_moves_pass` severity
    classification (flaws_service conventions verbatim: `eval_cp_to_expected_score`
    sigmoid, Option-B mate mapping, post-move shift). A ply is `good` when its
    severity is None (sub-inaccuracy) and it is not best/gem/great. Negative
    drops fall out as good naturally.
  - Threaded `opening_ply_count` into `_build_eval_series` so book/theory plies
    never qualify for best/good.
  - Precedence enforced: gem > great > best > good.
  - best/good deliberately skip the imported-eval divergence guard (gem/great
    only, per locked scope).
- Tests: 7 new unit tests in `tests/services/test_library_service.py`; updated
  one pre-existing integration test in `tests/test_library_router.py` whose
  "every other ply is null" assumption predated this feature.
- Gates: full backend suite (3482 passed), `ty`, `ruff` clean.

## Task 2 — Frontend (`931802d7`)

- New `frontend/src/lib/bestGlyph.ts` / `goodGlyph.ts` (green circle + white
  star = best; green circle + white thumbs-up = good), reusing existing
  `MOVE_QUALITY_BEST` / `MOVE_QUALITY_GOOD` theme constants (no hard-coded
  semantic colors).
- New `SquareMarker.best` / `.good` branches in
  `frontend/src/components/board/boardMarkers.tsx`.
- `storedBestGoodByPly` wiring in `frontend/src/pages/Analysis.tsx` (both
  players).
- `bestTierByPly` widened in
  `frontend/src/components/results/LibraryGameCard.tsx` (user-scoped via
  `isUserPly`).
- Widened shared type in `frontend/src/types/library.ts`.
- Gates: `tsc -b`, `lint`, `knip` clean; frontend suite (2297/2297) passes.

## Out of scope (per locked /gsd-explore decisions)

Eval chart markers, analysis board move-list labels, severity badge row on the
game card, library filters for best/good, per-game aggregation table,
click-to-cycle chips for best/good. None of these were touched.

## Orchestration notes

- The spawn-time worktree branch-check reported a base mismatch (the documented
  `phase`-branching-vs-worktree-isolation gap); the worktree state was sound and
  the executor proceeded inside it.
- During execution (~28 min), a concurrent session advanced `main` with a
  release forward-port + phase-177 planning docs (docs-only, zero code-file
  overlap). The worktree branch merged cleanly into the advanced `main` via a
  manual `--no-ff` merge (the cleanup-wave helper fail-closed on the base
  mismatch, so cleanup was done by hand).
