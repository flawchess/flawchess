---
quick_id: 260628-qta
slug: phase-140-analysis-ply-scroll-uat
status: complete
date: 2026-06-28
---

# Quick Task 260628-qta: Analysis board ply / scroll UAT (phase 140)

More UAT feedback for Phase 140's full-game analysis board. Three small,
well-scoped frontend tweaks, executed inline (no executor subagent).

## Tasks

1. **`game_id` without `ply` loads the game at ply 0** — Game mode was keyed on
   BOTH `game_id` AND `ply` (`isGameMode = gameId != null && initialPly != null`),
   so opening `/analysis?game_id=X` with no `ply` fell back to free play and never
   loaded the game. Key game mode on `game_id` alone; the ply param stays optional
   and defaults to 0 via the existing `mainLine[initialPly ?? 0]` guards.
   - `frontend/src/pages/Analysis.tsx`: `isGameMode = gameId != null`.

2. **Analyze button omits `ply` at the game's end position** — The game card's
   Analyze button always pinned `ply` to the slider's resting (end) ply
   (`hoverPly ?? lastEvalPly ?? 0`), so opening from the default end position
   deep-linked to the last move. When the slider rests on the end position, omit
   `ply` so the board opens the game at ply 0; when scrubbed to an earlier move,
   keep that move's ply. The existing `isScrubbedBack` flag already means "slider
   is somewhere other than the last eval'd (end) ply".
   - `frontend/src/lib/analysisUrl.ts`: `buildGameAnalysisUrl(gameId, ply?)` —
     omit the ply param when `ply` is null/undefined.
   - `frontend/src/components/results/LibraryGameCard.tsx`: shared `analyzeTo` =
     `buildGameAnalysisUrl(game_id, isScrubbedBack ? hoverPly : null)`, used by
     both the desktop and mobile Analyze buttons.

3. **Open with a `ply` scrolls the selected move to the TOP of the move list** —
   The desktop move list used `scrollIntoView({ block: 'nearest' })`, which on
   initial open landed the selected move at the BOTTOM. Align it to the top once
   on first open. `loadMainLine` first parks `currentNodeId` at the game's LAST
   node before the board navigates to `initialPly`, so the top-align is held until
   `currentNodeId` actually reaches the initial-ply node; all later navigation
   keeps the minimal `block: 'nearest'` keep-in-view scroll.
   - `frontend/src/components/analysis/VariationTree.tsx`: new optional
     `initialPly` prop; `DesktopTree` computes `initialNodeId = mainLine[initialPly ?? 0]`
     and does a one-shot `block: 'start'` scroll when `currentNodeId` first reaches it.
   - `frontend/src/pages/Analysis.tsx`: pass `initialPly` (game mode only) to
     `VariationTree`.

## Verification

- `npx tsc -b` clean (shared `buildGameAnalysisUrl` / `VariationTreeProps` types).
- `npm run lint` clean (only pre-existing `coverage/` warnings).
- `npm test -- --run`: 1217 passed (added `buildGameAnalysisUrl` ply-omission cases).
- `npm run knip` clean.
- HUMAN-UAT: open `/analysis?game_id=X` (no ply) → game loads at ply 0; click
  Analyze from a card at rest → opens at ply 0; open with a `ply` → that move sits
  at the top of the move list.
