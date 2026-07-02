---
quick_id: 260702-fog
title: Auto-open tactic line when analysis board opens at a tactic ply
status: complete
date: 2026-07-02
commit: f4c74706
---

# Quick Task 260702-fog — Summary

## What changed

Deep-linking the analysis board to a ply that carries a **user** tactic tag
(`/analysis?game_id=X&ply=Y`) now opens that tactic line automatically — the same result
as clicking the tactic chip in the move list. No extra URL params: the board reads the
existing `flaw_markers` for the opening ply.

Selection rules:
- Missed tactic present → open **missed** (board forks at the decision board, `ply - 1`).
- Allowed tactic present (no missed) → open **allowed** (board at the flaw position, `ply`).
- Both present → **missed** wins (more instructive "what you should have played").
- Neither → unchanged (navigate to `initialPly`, open no line).
- Opponent-only tactics (`is_user: false`) are ignored, matching the move-list chip scoping.

## Implementation

- **`frontend/src/lib/tacticOrientation.ts`** (new) — pure `tacticOrientationAtPly(flawMarkers, ply)`
  helper returning `'missed' | 'allowed' | null`. Extracted to a lib module (not inlined in
  `Analysis.tsx`) because the `react-refresh/only-export-components` lint rule forbids
  exporting non-component functions from a component file.
- **`frontend/src/pages/Analysis.tsx`** — the once-only initial-ply navigation effect now
  checks `tacticOrientationAtPly(gameData?.flaw_markers, ply)`; when non-null it sets
  `activePvFlaw` and navigates to the fork node (reusing `forkPlyForOrientation`), letting
  the existing `useTacticLines → insertPvLine` effect chain graft the sideline. Falls back
  to plain navigation when there's no tactic or the fork ply is out of bounds.
- **`frontend/src/lib/__tests__/tacticOrientation.test.ts`** (new) — 7 cases covering
  missed-only, allowed-only, both (precedence), no-tactic, opponent flaw, no-marker-at-ply,
  and null inputs.

## Verification

- `npx tsc -b` — clean (0 errors)
- `npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/*` files)
- `npm run knip` — clean
- `npm test -- --run` — 106 files, 1244 tests pass (includes the 7 new cases)

## Follow-up (UAT) — commit f30d1c20

The move list didn't scroll to the highlighted move when a tactic auto-opened (it worked
for the no-tactic case). Cause: `VariationTree`'s first-open top-align holds until the board
reaches `mainLine[initialPly]`, but an auto-opened tactic navigates to the **fork** node
(missed → `ply-1`), so the guard never released. Fix: a shared `initialTactic` memo now
drives both the navigation effect and a derived `initialAlignPly` (the fork ply when a
tactic auto-opens, else the entry ply); `VariationTree` receives `initialAlignPly`, while
the `EvalChart` slider keeps the true entry ply. `frontend/src/pages/Analysis.tsx` +
`frontend/src/components/analysis/VariationTree.tsx` (prop doc). tsc/lint/knip clean, 1244
tests green.

## Notes / trade-offs

- The effect-level wiring (state + navigation) is not covered by a new integration test —
  the existing `Analysis.test.tsx` uses static module-level mocks for `useLibraryGame` /
  `useTacticLines` that can't be per-test overridden, so game-mode integration testing would
  require restructuring those mocks (out of scope for a quick task). The auto-open path is a
  direct mirror of the already-shipped `handlePvChipClick` behavior; the risk-bearing
  decision logic (which orientation, precedence, scoping) is the pure helper, which is
  unit-tested.
- Executed inline (no executor subagent): single-file logic change + pure-function test.
</content>
