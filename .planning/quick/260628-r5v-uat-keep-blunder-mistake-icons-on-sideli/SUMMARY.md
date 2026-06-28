---
quick_id: 260628-r5v
slug: uat-keep-blunder-mistake-icons-on-sideli
date: 2026-06-28
status: complete
---

# Summary: Persist sideline blunder/mistake icons + smaller desktop engine-line font

## What changed

Two analysis-board UAT items:

### 1. Blunder/mistake icons persist on every explored sideline move

Previously the live free-move classifier only graded the *current* board position, and
both `Analysis.tsx` (`moveListMarkers`) and `VariationTree.tsx` only painted the severity
glyph on the current node. Stepping forward in a sideline made the previous move's icon
vanish.

- **`Analysis.tsx`** — added a `liveFlawByNode: Map<NodeId, FlawSeverity>` state plus an
  effect that records each freely-played node's blunder/mistake classification as the live
  engine settles. `moveListMarkers` now merges this persisted map (and the current node's
  in-flight severity) into the game flaw markers. Read-time guards skip stale ids (reused as
  a main-line node after a game reload) and deleted nodes (collapsed PV forks); FIFO-capped at
  `LIVE_EVAL_CACHE_MAX`. Cleared on Reset.
- **`VariationTree.tsx`** — desktop `renderMoveButton` and mobile `varItems` now read the
  severity marker for any variation/free node, not only the current one.

This also satisfies the "cache the eval per sideline move" ask: the per-node classification
is cached so returning to an earlier sideline move re-shows its icon without re-grading. (The
eval *value* was already cached per position by FEN in `engineEvalByFen`.)

### 2. Smaller desktop engine-line font

Desktop engine lines (badge, move chips, move-number labels) dropped from `text-sm` to
`text-xs`, matching the already-compact mobile lines. Font now no longer differs between the
desktop and mobile (compact) variants — the `compact` split is purely row layout. `text-xs`
on this dense engine surface is a user-approved exception to the CLAUDE.md text-sm floor,
now extended to desktop per the user's explicit request.

## Files

- `frontend/src/pages/Analysis.tsx`
- `frontend/src/components/analysis/VariationTree.tsx`
- `frontend/src/components/analysis/EngineLines.tsx`
- `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` (test 15 now asserts the glyph persists on a non-current variation node)

## Verification

- `npx tsc -b` — clean
- `npm run lint` / `npm run knip` — clean (only pre-existing `coverage/` warnings)
- `npm test -- --run` — 103 files, 1217 tests pass

Frontend-only; no backend gate required.
