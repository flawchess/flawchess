---
quick_id: 260612-fow
title: Library tag-filter panel + eval-chart tag interactions
status: complete
branch: quick/library-tag-filter-eval-cycle
date: 2026-06-12
---

# Quick Task 260612-fow — Summary

Four Library-surface changes. Done inline (Opus) rather than via a sonnet executor
because the tasks are interrelated and Task 4's interactive cycling is non-trivial.
All work is on the feature branch `quick/library-tag-filter-eval-cycle` (per the
user's request) — **not merged**; the user merges it.

## Task 1 — Blunders/Mistakes default to inactive (both-shown) · `225a2e8e`

Severity now narrows like the other tag families.
- `useFlawFilterStore.ts`: `DEFAULT_FLAW_FILTER.severity` → `[]`; `isFlawFilterNonDefault`
  rewritten to `tags.length > 0 || severity.length === 1` (narrowing only when exactly
  one tier is picked; empty and both-selected both = "both shown").
- `FlawFilterControl.tsx`: dropped the at-least-one-severity guard.
- `FlawsTab.tsx`: inline modified-dot → `isFlawFilterNonDefault`; URL-init uses the
  parsed severity verbatim (no `['blunder','mistake']` fallback).
- Backend needed no change — empty severity already means "all M+B"
  (`build_flaw_filter_clauses`, `useLibrary.ts:35`, `client.ts`).

## Task 2 — Game Phase tag-filter family (full-stack) · `069d3b72`

Reversed the deliberate "phase tags are display-only" exclusion (the `game_flaws.phase`
column already existed).
- Backend: `build_flaw_filter_clauses` adds a phase-family clause
  (`GameFlaw.phase.in_(...)`, OR within / AND across); router `FlawTagFilter` Literal
  accepts opening/middlegame/endgame on `/games` and `/flaws`. The two
  phase-tag-422-rejection router tests were converted to acceptance + count assertions;
  two `build_flaw_filter_clauses` predicate unit tests flipped.
- Frontend: `FlawFilterControl` gains a "Game Phase" family (BookOpen/Swords/Trophy
  icons, matching the Stats grid). `FAM_PHASE` recolored **gold→teal**
  (`oklch(0.72 0.13 170)`) so it never clashes with the yellow inaccuracy severity;
  shared with the Stats comparison grid for family-color consistency. The eval-chart
  filter outline (`LibraryGameCard`) is now phase-aware (phase derived from
  `phase_transitions`). `TagChip` gets a proper `phase` family color.

**Heads-up for the user:** `FAM_PHASE` changed globally, so the Stats tab's Flaw
comparison "Phase" card is now teal instead of gold. This was intentional (one color
per family). Say if you'd rather keep the Stats grid gold and only recolor the filter.

## Task 3 — Mobile Stats subtab top gap · `f9413a99`

`LibraryPage.tsx`: mobile Stats `TabsContent` `mt-4` → `mt-1` to match Games/Flaws.

## Task 4 — Cycle eval-chart flaws on tag click · `2fbe8002`

Hover-highlight already existed (`onHover`/`highlightedPlies`). Added click/tap-to-cycle:
- `TagChip.tsx`: new `onActivate?` prop (click + Enter/Space), games-card path only.
- `LibraryGameCard.tsx`: `{tag, pos}` cycle state + a per-tag sorted ply list; clicking
  advances through that tag's flaw plies (wraps), passing `commandedPly` + `commandSeq`
  to the chart and emphasizing the tag.
- `EvalChart.tsx`: new `commandedPly`/`commandSeq` props; on a new seq it scrubs the
  slider to the commanded ply, clears hover, focuses the slider (fine pointer), and
  shows the tooltip. Touch dismissal reuses the existing outside-touch handler.

## Follow-up requests (same branch)

Three further user requests, implemented on the same branch after the four above.

### F1 — Severity badges also cycle eval-chart flaws · `24fc2989`

The Blunders/Mistakes/Inaccuracy count badges now cycle the eval chart on click,
like the tag chips. The cycle logic in `LibraryGameCard` was generalized over a
`FlawRef` (`{kind:'tag'} | {kind:'severity'}`), with a `severityPlies` map alongside
`tagPlies`. `SeverityBadge` gained an `onActivate` prop (button role + Enter/Space).
Cycling to an **inaccuracy** reveals its normally-hidden dot (via the existing
highlight path), and `EvalChart`'s tooltip now shows flaw detail whenever the
marker's dot is visible (M/B always; inaccuracy when revealed/cycled/focused) —
replacing the old strict mb-only gate.

### F2 — Phase tag in the Flaws subtab tag list · `f633d9ab`

`_reconstruct_tags` (Flaws-list only) now appends the flaw's phase tag from
`game_flaws.phase`. The Games-card chips are curated separately and still omit phase;
eval-chart markers already carried phase (filtered out of the tooltip).

### F3 — Tag icons in tooltip + unified clock format · `ae21a2a8`

The eval-chart tooltip lists a flaw's tags with their family-colored icons instead of
plain bullets, and shows clock info as "🕐 mm:ss · Move Ns". `FlawCard` adopts the same
clock format. Tag icon + family-color maps were extracted to `frontend/src/lib/tagVisuals.ts`
(shared by `TagChip` and the tooltip; de-duplicates the maps and satisfies the
react-refresh rule that component files only export components).

## Gates (full pre-merge gate, all green)

- Backend: `ruff format --check` clean, `ruff check` clean, `ty check` clean,
  `pytest -n auto` = **2522 passed, 10 skipped**.
- Frontend: `npm run lint` clean, `npm run knip` clean, `npm test -- --run` =
  **903 passed (78 files)**, `npm run build` succeeds.

## Follow-ups / HUMAN-UAT

- Visual verify: phase filter on both Games + Flaws tabs; teal phase-family color in the
  filter panel and the Stats comparison grid; click-to-cycle on desktop (focus + keyboard
  arrows) and mobile (tap); reduced mobile Stats gap.
- Confirm the global `FAM_PHASE` recolor is acceptable on the Stats grid (see Task 2 note).
- Merge `quick/library-tag-filter-eval-cycle` into `main` when satisfied.
