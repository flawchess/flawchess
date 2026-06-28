---
quick_id: 260627-thl
slug: more-uat-feedback-for-phase-140-analysis
date: 2026-06-27
status: complete
---

# Summary: Phase 140 analysis-board UAT round 5

Five frontend UAT tweaks. All atomic commits; full frontend gate green
(eslint 0 errors, `tsc -b` clean, 1205 vitest tests pass).

## What changed

1. **Desktop move list 25px shorter** (`c5389b1d`) — the list is `flex-1` (fills the
   panel so the controls bottom-align with the eval-chart slider), so prior `max-height`
   tweaks never bound. Added `mb-[25px]` to the flex-grow scroll area: a flex item's size
   excludes its margins, so the list shrinks 25px while the controls stay bottom-aligned
   (small gap opens above them — user-confirmed). `VariationTree.tsx`.

2. **Best-move arrow off-by-one** (`24e51872`) — root cause: `game_positions[X].best_move`
   is the engine's best move FROM position X (the decision position, before `move_san[X]`),
   verified against the dev DB. But the analysis board and the games-card MiniBoard both
   show the position AFTER the played move (`mainLine[k]` / `perPly[activePly]` = position
   k+1), so they drew `best_move[k]` — the move that *led into* the shown position — leaving
   the blue arrow one ply behind the live grey 2nd-best (from the current position). Fixed
   to `best_move[k+1]` (best move from the displayed position) in `useGameOverlay.ts` and
   `LibraryGameCard.tsx`. The missed-tactic depth label was dropped from the arrow (it
   described the prior decision, not the continuation; missed tactics remain in the
   move-list chips, allowed depth still rides the played-move corner glyph). `FlawCard` was
   confirmed correct (it shows the pre-flaw decision position) and left untouched. Updated
   the `useGameOverlay` blue-arrow source-contract test.

3. **Blunder/mistake glyphs in the move list** (`7073791d`) — the `??`/`?` glyph was gated
   behind `!hasTacticChip`, hiding it on any flawed move that also carried a tactic chip.
   Dropped the gate (desktop + mobile) so the glyph always shows for blunder/mistake moves.
   `VariationTree.tsx`.

4. **Forward button steps into the open flaw sideline** (`139ae6ff`, test `3919fcd4`) —
   after opening a flaw line the board parks at the fork node, where the main-line
   continuation (lower id) and the grafted PV node share a parent; `findFirstChild` picked
   the main line. `goForward` now advances into `pvLine[0]` when the current node is the
   PV's fork. `useAnalysisBoard.ts` + new unit test.

5. **Miniboard tooltip on engine-move hover** (`6fdeb472`) — replay each engine PV line to
   per-step `{san, fen}` and wrap each move chip in a `Tooltip` whose content is a
   `MiniBoard` of the position after that move. Desktop hover only (Tooltip suppresses on
   touch). Board orientation threaded from `Analysis.tsx`. `EngineLines.tsx` + regression
   test.

## Verification
- `cd frontend && npm run lint` → 0 errors (3 pre-existing warnings in `coverage/`)
- `npx tsc -b` → clean
- `npm test -- --run` → 103 files, 1205 tests pass
- Manual UAT: open `/analysis?game_id=…&ply=…` (HUMAN).

## Notes / follow-ups
- Items touched the analysis board only (plus the shared games-card MiniBoard for item 2,
  per user note). No backend changes. No changelog entry — this is pre-merge UAT polish on
  the unmerged phase-140 branch (consistent with rounds 2–4).
