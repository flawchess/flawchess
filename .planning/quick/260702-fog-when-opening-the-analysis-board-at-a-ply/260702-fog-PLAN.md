---
quick_id: 260702-fog
title: Auto-open tactic line when analysis board opens at a tactic ply
status: planned
date: 2026-07-02
---

# Quick Task 260702-fog

## Goal

When the analysis board opens (game mode, `?game_id=X&ply=Y`) at a ply that carries a
user tactic tag, automatically open the tactic line — exactly as if the user had clicked
that tactic chip in the move list. Rules:

- If the ply has a **missed** tactic → open the missed line (forks at the decision board,
  `ply - 1`).
- If the ply has an **allowed** tactic (and no missed) → open the allowed line (forks at
  the flaw position, `ply`).
- If it has **both** → open the **missed** line (precedence).
- If it has neither → existing behavior (navigate to `initialPly`, no line opened).

## Context (from codebase exploration)

- `frontend/src/pages/Analysis.tsx` is the analysis board.
  - `activePvFlaw` state (`{ ply, orientation }`) drives the whole "open a tactic line"
    machinery: setting it enables `useTacticLines` (line ~212), which triggers the
    insert-PV-sideline effect (lines ~254-269).
  - `handlePvChipClick` (lines ~622-641) is the chip-click behavior we must replicate:
    `setActivePvFlaw(flaw)` + `goToNode(mainLine[forkPlyForOrientation(ply, orientation)])`.
  - `forkPlyForOrientation` (lines ~116-118): `allowed → flawPly`, `missed → flawPly - 1`.
  - Effect at lines ~244-251 navigates to `initialPly` once after the main line loads
    (`hasNavigatedToInitialPly` ref guard). This is where the auto-open hooks in.
  - `gameData.flaw_markers` is `FlawMarker[] | null` (`@/types/library`); the user-scoping
    logic (only `is_user` flaws, `missed_tactic_motif` / `allowed_tactic_motif`) matches
    `flawMarkerByNodeId` (lines ~334-362).

## Tasks

### Task 1 — Auto-open the tactic line at the opening ply

**Files:** `frontend/src/pages/Analysis.tsx`

**Action:**
1. Add a module-level pure helper (next to `forkPlyForOrientation`), exported for testing:
   ```ts
   export function tacticOrientationAtPly(
     flawMarkers: FlawMarker[] | null | undefined,
     ply: number | null,
   ): 'missed' | 'allowed' | null
   ```
   Returns `'missed'` if a user flaw at `ply` has `missed_tactic_motif`, else `'allowed'`
   if it has `allowed_tactic_motif`, else `null`. Missed takes precedence.
2. Import `FlawMarker` type from `@/types/library`.
3. In the initial-ply navigation effect (lines ~244-251), before the plain `goToNode`,
   compute `tacticOrientationAtPly(gameData?.flaw_markers, ply)`. If non-null: set
   `activePvFlaw = { ply, orientation }` and `goToNode(mainLine[forkPlyForOrientation(...)])`,
   then return. Fall back to the existing `goToNode(mainLine[ply])` when null or the fork
   node is out of bounds. Keep the `hasNavigatedToInitialPly` once-guard.

**Verify:** `npx tsc -b` clean; behavior traced against `handlePvChipClick`.
**Done:** Opening `?game_id=X&ply=Y` where ply Y has a missed (or allowed) user tactic
shows the line opened, board parked at the fork ply.

### Task 2 — Unit-test the selection helper

**Files:** `frontend/src/pages/__tests__/Analysis.orientation.test.ts` (new)

**Action:** Cover the decision logic of `tacticOrientationAtPly`: missed-only → missed,
allowed-only → allowed, both → missed (precedence), neither → null, opponent flaw
(`is_user: false`) → null, no marker at ply → null, null markers/ply → null.

**Verify:** `npm test -- --run` green.
**Done:** New test file passes.

## Pre-merge gate

`cd frontend && npm run lint && npm test -- --run && npx tsc -b`

## Notes

- No changelog entry required beyond the STATE.md quick-task row per project convention
  (small behavior tweak). Actually surfaces a real UX behavior change — add an Unreleased
  bullet is optional; skipped here as a minor deep-link nicety.
- Executed inline (no executor subagent): single-file change + pure-function test, and the
  repo's worktree/SSE re-spawn failure modes make inline the safer path for small work.
</content>
</invoke>
