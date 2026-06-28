---
quick_id: 260628-qta
slug: phase-140-analysis-ply-scroll-uat
status: complete
date: 2026-06-28
commit: aac82a37
---

# Summary — Quick Task 260628-qta

Phase 140 full-game analysis board UAT. Three small ply / scroll-behavior tweaks,
done inline (well-scoped frontend, no executor subagent).

## Changes

- **`frontend/src/pages/Analysis.tsx`** — `isGameMode` now keys on `gameId != null`
  alone (was `gameId != null && initialPly != null`), so `/analysis?game_id=X` with
  no `ply` param loads the game and opens at ply 0 (all `mainLine[initialPly ?? 0]`
  guards already default to 0; `syncPly` drives the eval chart slider to 0 to match).
  Passes `initialPly` (game mode only) to `VariationTree` for the top-align.
- **`frontend/src/lib/analysisUrl.ts`** — `buildGameAnalysisUrl(gameId, ply?)`: `ply`
  is now optional; null/undefined omits the param (board opens at ply 0).
- **`frontend/src/components/results/LibraryGameCard.tsx`** — shared `analyzeTo` =
  `buildGameAnalysisUrl(game_id, isScrubbedBack ? hoverPly : null)`. At the slider's
  end position (`!isScrubbedBack`) the ply is omitted → opens at ply 0; scrubbed back
  → deep-links to that move. Used by both the desktop and mobile Analyze buttons (was
  `hoverPly ?? lastEvalPly ?? 0` duplicated in both).
- **`frontend/src/components/analysis/VariationTree.tsx`** — new optional `initialPly`
  prop. `DesktopTree` computes `initialNodeId = mainLine[initialPly ?? 0]` and does a
  one-shot `scrollIntoView({ block: 'start' })` when `currentNodeId` first reaches it,
  held past the `loadMainLine` last-node transient (`didInitialAlign` ref). Free play
  (empty mainLine → `initialNodeId` undefined) keeps the original `block: 'nearest'`.
- **`frontend/src/lib/analysisUrl.test.ts`** — added ply-omission cases (explicit `0`
  kept; `null`/`undefined` omit the param).

## Result

- `npx tsc -b` clean · `npm run lint` clean (pre-existing `coverage/` warnings only) ·
  `npm test -- --run` 1217 passed · `npm run knip` clean.

## Follow-up (HUMAN-UAT)

Visual confirmation on a real game: (1) open `/analysis?game_id=X` (no ply) → game
loads at ply 0; (2) click Analyze on a card at its resting end position → opens at
ply 0; scrub back first → opens at that move; (3) open with a `ply` (Flaws-tab Analyze
or a deep link) → the selected move sits at the TOP of the move list, not the bottom.
