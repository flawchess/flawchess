---
quick_id: 260612-fow
title: Library tag-filter panel + eval-chart tag interactions
status: in_progress
branch: quick/library-tag-filter-eval-cycle
---

# Quick Task 260612-fow

Four Library-surface UI changes (Flaws/Stats subtabs, tag filter panel, game card eval chart).

## Task 1 — Blunders/Mistakes default to inactive (both-shown semantic)

Make the severity toggles behave like the other tag-filter families: default empty =
"both shown" (buttons render inactive); selecting only Blunders shows blunders only;
both selected == both inactive == both shown.

- `useFlawFilterStore.ts`: `DEFAULT_FLAW_FILTER.severity` → `[]`. Rewrite
  `isFlawFilterNonDefault` → `tags.length > 0 || severity.length === 1` (narrowing only
  when exactly one severity is picked).
- `FlawFilterControl.tsx`: drop the at-least-one-severity guard in `handleSeverityToggle`
  so deselecting the last severity yields `[]`. Update docstring/comments.
- `FlawsTab.tsx`: replace inline `isFlawModified` with `isFlawFilterNonDefault`; URL-init
  severity uses `urlSeverity` verbatim (no `['blunder','mistake']` fallback).
- Test: `FlawFilterControl.test.tsx` — replace the guard test with "deselect → []".

Backend already treats empty severity as "all M+B" (`build_flaw_filter_clauses`,
`useLibrary.ts:35`), so no backend change.

## Task 2 — Add Game Phase tag-filter family (full-stack)

Phase-tag filtering was deliberately excluded (router `FlawTagFilter` 422-rejects phase
tags; `build_flaw_filter_clauses` produces no clause). User now wants it. The
`game_flaws.phase` column already exists, so:

Backend:
- `library_repository.build_flaw_filter_clauses`: add phase family —
  `GameFlaw.phase.in_([_PHASE_INT[t] for t in phase_tags])` (OR within, AND across).
- `routers/library.py`: extend `FlawTagFilter` Literal with opening/middlegame/endgame;
  update the two docstrings/comments that say phase tags are rejected.
- Tests `test_library_router.py`: convert the two `*_422` phase-tag tests into
  acceptance + count assertions (opening→1, middlegame→3, endgame→1 flaws;
  opening→1, middlegame→2, endgame→1 games; middlegame+reversed→1).

Frontend:
- `theme.ts`: change `FAM_PHASE`/`FAM_PHASE_BG` from gold (yellow) to a distinct
  teal (`oklch(0.72 0.13 170)`) — shared with the Stats comparison grid for family
  consistency. Update the comment.
- `FlawFilterControl.tsx`: add phase icons (BookOpen/Swords/Trophy) to TAG_ICONS and a
  "Game Phase" `FAMILY_SECTIONS` entry (tags opening/middlegame/endgame, FAM_PHASE).
- `LibraryGameCard.tsx`: make the chart `outlinedPlies` phase-aware (derive each ply's
  phase from `phase_transitions`) so a phase filter outlines matching markers.
- `TagChip.tsx`: map phase tags to a proper `phase` family color (FAM_PHASE) instead of
  the impact fallback.
- Test: `FlawFilterControl.test.tsx` — phase family + buttons now present.

## Task 3 — Reduce mobile Stats subtab top gap

`LibraryPage.tsx`: mobile Stats `TabsContent` `mt-4` → `mt-1` to match Games/Flaws.

## Task 4 — Cycle eval-chart flaws on tag click (hover-highlight already exists)

Hover-highlight (dim others) is already implemented via `onHover`/`highlightedPlies`.
Add click/tap-to-cycle:
- `TagChip.tsx`: add `onActivate?` prop fired on chip click (games-card path).
- `LibraryGameCard.tsx`: track `{tag, pos}` cycle state; clicking a tag advances through
  that tag's user-marker plies (sorted), passing a `commandedPly` + `commandSeq` to the
  chart.
- `EvalChart.tsx`: add `commandedPly`/`commandSeq` props; on seq change, set the slider
  to the commanded ply, clear hover, focus the slider input + show the tooltip.

## Verification
- Backend: `uv run pytest -n auto` (library router + repository).
- Frontend: `npm run lint`, `npm test -- --run`, `npm run knip`.
- Full pre-merge gate before squash decisions (user merges the branch).
