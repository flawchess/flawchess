---
phase: 139-tactic-mode-overlay-phase-135-subsume
reviewed: 2026-06-26T20:06:53Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - frontend/eslint.config.js
  - frontend/src/components/analysis/TacticModeOverlay.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
  - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
  - frontend/src/hooks/useAnalysisBoard.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.tactic.test.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 139: Code Review Report

**Reviewed:** 2026-06-26T20:06:53Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the Phase 139 tactic-mode overlay work: a new `TacticModeOverlay` component with
exported arrow builders, the `goToRoot` addition to `useAnalysisBoard`, the Analysis page
wiring of tactic mode, the repointed Explore buttons in `FlawCard` / `LibraryGameCard`, and
an eslint config relaxation. TacticLineExplorer + useTacticLine were deleted in the same phase.

Verification baseline: `npx tsc -b` clean, all 25 tests across the four phase test files
pass, `npm run lint` clean (only pre-existing generated `coverage/*` warnings, out of scope),
`npm run knip` clean (no dangling refs from the deletion).

No BLOCKERs. The seeding/navigation logic is sound — notably the re-seed effect correctly
relies on `goToRoot` being a *functional* `setState` so it lands at `currentNodeId = null`
after `loadMainLine` seeds the last node (order-dependent and correct). The findings below are
display-correctness and maintainability issues, with two WARNINGs worth fixing.

This phase delivered no `<structural_findings>` substrate; findings are narrative only.

## Warnings

### WR-01: Overlay shows stale depth counter + decision-position eval badge when the user forks off the stored PV

**File:** `frontend/src/pages/Analysis.tsx:218` (and `frontend/src/components/analysis/TacticModeOverlay.tsx:235-243, 316-338`)
**Issue:** The board is interactive in tactic mode (`onPieceDrop={makeMove}`), so a user can
drag a piece and fork off the stored PV. `tacticPly` is derived as:

```ts
const tacticPly = currentNodeId === null ? 0 : mainLine.indexOf(currentNodeId) + 1;
```

For a forked node (not in `mainLine`), `indexOf` returns `-1`, so `tacticPly` collapses to
`0` — the same value used for the *decision position / root*. The overlay receives
`currentPly={tacticPly}` and `displayDepth`/`isPayoff` computed from it, so while the board sits
on a forked-off position it renders:
- the depth counter as `Depth N / N` (full depth, `isPayoff` false), and
- the eval badge anchored to the **decision position** eval (`missed_eval_cp`, since
  `showsPostFlawEval` requires `currentPly >= 1`).

The arrow-source toggle is correctly hidden off-line (`showArrowSourceToggle = onMainLine`),
which signals the designers wanted reduced chrome off-line — but the depth counter and eval
badge are not gated the same way, so they display misleading root-anchored values for a
position that is neither the root nor on the stored line. The live `EvalBar`/`EngineLines`
update correctly, compounding the confusion (two disagreeing eval readouts).

**Fix:** Distinguish "off main line" from "at root". Either pass an explicit off-line flag and
hide the depth counter + stored eval badge when off-line (mirroring the arrow-source toggle), or
make `tacticPly` carry a sentinel for forked nodes rather than reusing `0`:

```ts
// Analysis.tsx — disambiguate forked nodes from the root.
const onStoredLine = currentNodeId === null || isOnMainLine(currentNodeId);
const tacticPly =
  currentNodeId === null ? 0 : onStoredLine ? mainLine.indexOf(currentNodeId) + 1 : -1;
// ...then gate the overlay's depth counter + stored eval badge on tacticPly >= 0
```

### WR-02: FlawCard Explore orientation ignores the active `tacticOrientation` filter

**File:** `frontend/src/components/library/FlawCard.tsx:148`
**Issue:**

```ts
const ori = flaw.missed_tactic_motif != null ? 'missed' : 'allowed';
```

`ori` (sent as `&orientation=` to `/analysis`) hard-codes the missed-takes-precedence rule and
ignores the `tacticOrientation` prop that controls which chip(s) the card actually renders.
When a flaw has *both* motifs but the Flaws subtab is filtered to `tacticOrientation='allowed'`,
the card shows only the allowed chip, yet Explore navigates with `orientation=missed` — the URL
contradicts what the user sees and filtered for. This is partially masked because Analysis
re-resolves orientation against the flaw-filter store (`resolveVisibleTactic` will null the
missed slot when the store filters to allowed, so `resolvedOrientation` falls back to allowed),
so the end state is usually correct — but the emitted URL is still wrong and the correctness
depends on the store and the prop staying in sync.

**Fix:** Respect the prop when it pins an orientation:

```ts
const ori =
  tacticOrientation === 'allowed'
    ? 'allowed'
    : tacticOrientation === 'missed'
      ? 'missed'
      : flaw.missed_tactic_motif != null
        ? 'missed'
        : 'allowed';
```

## Info

### IN-01: eslint `react-refresh/only-export-components` disabled for the whole `analysis/` directory

**File:** `frontend/eslint.config.js:52-57`
**Issue:** The override disables the fast-refresh-safety rule for **all** of
`src/components/analysis/**`, but only `TacticModeOverlay.tsx` co-exports non-component helpers
(`buildRootArrows`, `buildPvArrow`, `isBlackToMove`). Sibling components (`EvalBar`,
`EngineLines`, `VariationTree`) silently lose the guard against accidental mixed exports.
**Fix:** Prefer extracting the three pure helpers into a plain module (e.g.
`src/lib/tacticArrows.ts`) and dropping the override entirely — the comment even frames the
override as avoiding "a separate file indirection", but a `lib/` helper file is the standard
seam here and keeps the rule active for real components. If kept, narrow `files` to
`src/components/analysis/TacticModeOverlay.tsx`.

### IN-02: Misleading variable name `gameId = data.flaw_ply`

**File:** `frontend/src/components/analysis/TacticModeOverlay.tsx:248`
**Issue:** `const gameId = data.flaw_ply;` names a *ply* value `gameId`, then passes it as
`flawId` to the chips. The comment acknowledges it "mirrors TLE usage", but the name actively
misleads future readers.
**Fix:** Rename to `flawId` (or `chipFlawId`) to match its role:
`const flawId = data.flaw_ply;`

### IN-03: `orientation` URL param is read only at mount

**File:** `frontend/src/pages/Analysis.tsx:104-106`
**Issue:** `orientation` is seeded via a `useState` initializer from the URL param, so a second
in-page navigation to `/analysis?...&orientation=...` (without remounting) would not update the
selected orientation. This is currently safe because every Explore entry point navigates *from*
another route (Library/Games), forcing a remount — but it is brittle: a future caller that
navigates within `/analysis` would silently get the stale orientation.
**Fix:** Note the constraint explicitly, or sync the param in an effect (guarded so a manual
toggle is not clobbered), e.g. reset orientation when `gameId`/`flawPly` change.

### IN-04: Duplicated depth math between Analysis.tsx and the overlay

**File:** `frontend/src/components/analysis/TacticModeOverlay.tsx:310-314` and `frontend/src/pages/Analysis.tsx:220-227`
**Issue:** `activeDepthRaw` / `rootDisplayDepth` are computed in Analysis (to derive
`displayDepth`/`isPayoff` props) and recomputed independently inside the overlay (for the `/ N`
suffix). They agree today because both read the same `resolvedOrientation` + `tacticData`, but
the duplication invites drift if one site changes.
**Fix:** Pass `rootDisplayDepth` as a prop alongside `displayDepth`/`isPayoff` so the math lives
in exactly one place.

---

_Reviewed: 2026-06-26T20:06:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
