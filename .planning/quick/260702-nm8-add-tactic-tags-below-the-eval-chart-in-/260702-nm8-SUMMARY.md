---
phase: quick-260702-nm8
plan: 01
subsystem: frontend-analysis
tags: [analysis-page, tactic-tags, eval-chart, library-parity]
dependency-graph:
  requires: []
  provides:
    - AnalysisTagsPanel component
  affects:
    - frontend/src/pages/Analysis.tsx
tech-stack:
  added: []
  patterns:
    - Standalone sibling component mirroring an existing well-tested component's
      derivations (severity/tag/motif ply maps, click-to-cycle) without importing
      from or modifying it.
key-files:
  created:
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx
  modified:
    - frontend/src/pages/Analysis.tsx
decisions:
  - "Task 3 (hover-highlight) was NOT deferred — EvalChart already exposed a
    highlightedPlies prop, making the wiring genuinely cheap as the plan's
    OPTIONAL condition required."
metrics:
  duration: 25min
  completed: 2026-07-02
status: complete
---

# Quick 260702-nm8: Add tactic tags below the eval chart in /analysis Summary

Added a flaw-tags panel to the /analysis page (game mode) mirroring the Library
game card's severity-badge row + Missed | Allowed | Context tactic/context chip
block, with click-to-cycle navigation and (bonus) desktop hover-highlight.

## What Was Built

**Task 1 — `AnalysisTagsPanel` component** (`frontend/src/components/analysis/AnalysisTagsPanel.tsx`):
A standalone component (does not import from or modify `LibraryGameCard.tsx`, per
the plan's resolved decision 4) that:
- Renders three `SeverityBadge` elements (blunder/mistake/inaccuracy) from
  `game.severity_counts`, and a 3-column `grid grid-cols-1 md:grid-cols-3` block
  (Missed | Allowed | Context) using the existing `TacticMotifGroup`, `ChipColumn`,
  `TagChip`, and `TagLegend` leaf components.
- Derives `severityPlies`/`tagPlies`/`tagCounts`/`motifPlies`/`tacticMotifs` from
  `game.flaw_markers` scoped to `fm.is_user`, via `useMemo` — logic copied verbatim
  in spirit from `LibraryGameCard` (family-less motifs skipped, named-mate
  subtypes collapse to a single "checkmate" chip per orientation).
- Click-to-cycle: clicking a severity badge or tactic/context chip calls
  `onCyclePly(ply)` with the first ply of that ref's ascending ply list; clicking
  the same ref again advances (wrapping); clicking a different ref restarts at 0.
  A ref with an empty ply list is a no-op.
- Returns `null` when `analysis_state !== 'analyzed'` or there are no flaw
  markers (never renders `NoAnalysisState` — the page's own readiness gate is
  belt-and-suspenders on top).
- Unit test (`AnalysisTagsPanel.test.tsx`, 8 cases): severity counts, 3-column
  chip rendering with non-user-marker exclusion, cycle first/next/wrap, cycle
  restart on a different ref, empty-ply-list no-op, and both null-guard paths.

**Task 2 — Wiring into `Analysis.tsx`**:
- Desktop: `AnalysisTagsPanel` renders directly below the eval chart inside the
  board column (`data-testid="analysis-eval-chart"` sibling), game mode only.
- Mobile: a third `Tags` tab (`data-testid="analysis-tab-tags"`) added to the
  existing `Moves` / `Eval chart` tab bar, rendering the same panel.
- `onCyclePly` reuses the *exact* existing pattern from
  `handleEvalChartPlyChange`: `const nodeId = mainLine[ply]; if (nodeId !==
  undefined) goToNode(nodeId);` — a single `goToNode` call auto-syncs board, move
  list, and eval-chart crosshair (`evalChartPly` derives from `currentNodeId`).
  No new state machinery (`commandedPly`/PV plumbing) was added, per resolved
  decision 1.
- A shared `tagsPanel(withHighlight?)` render helper (mirroring the existing
  `evalChart`/`variationTree`/`boardControls` helper pattern) mounts the panel
  exactly once regardless of desktop/mobile.

**Task 3 — Desktop hover-highlight (NOT deferred)**:
The plan flagged this as optional, contingent on `EvalChart` already exposing a
highlighted-plies prop. It does (`highlightedPlies?: ReadonlySet<number> | null`),
so this was implemented rather than deferred:
- `AnalysisTagsPanel` gained an optional `onHighlightChange?: (plies: Set<number>
  | null) => void` prop, local `highlight` state, and a `highlightedPlies`
  `useMemo` mirroring `LibraryGameCard` (a cycled ref stays lit as a fallback when
  no live hover is active, so touch — which has no mouse-leave — keeps the
  highlight visible). `onHover` wired on `SeverityBadge`, `TagChip`, and
  `TacticMotifGroup`.
- `Analysis.tsx` lifts `tagsHighlightedPlies` state and wires it ONLY on the
  desktop call sites (`tagsPanel(true)` and `evalChart('h-[120px]',
  tagsHighlightedPlies)`); the mobile call sites (`tagsPanel()`,
  `evalChart('h-[120px]')`) are unchanged — mobile shows no highlight since the
  chart lives on a separate tab there, matching the plan's explicit mobile
  out-of-scope note.

## Verification

- `cd frontend && npm run lint` — clean (0 errors, knip clean).
- `cd frontend && npx tsc -b` — 0 type errors.
- `cd frontend && npm test -- --run` — 107 test files, 1253 tests, all passing
  (includes the new 8-case `AnalysisTagsPanel.test.tsx`).
- Backend untouched — no python/pytest/ruff/ty run (per plan).
- Manual browser verification (HUMAN-UAT) was NOT performed in this session —
  the plan explicitly marks it non-blocking. Recommend a quick manual check of
  `/analysis?game_id=X` (desktop panel below chart, mobile Tags tab, click-to-
  cycle syncing board+moves+chart, hover dimming on desktop) before relying on
  it in daily use.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `node_modules` missing in the worktree**
- **Found during:** Task 1 (attempting `npm test`)
- **Issue:** This git worktree had no `node_modules/` (gitignored, not shared
  across worktrees), so `npm test`/`lint`/`tsc` all failed with "command not
  found".
- **Fix:** Ran `npm install` in the worktree's `frontend/` directory (standard,
  no package changes — `package.json`/`package-lock.json` untouched).
- **Files modified:** None (only `node_modules/` populated, gitignored).
- **Commit:** N/A (no tracked files changed).

**2. [Rule 3 - Blocking issue] Test file used unavailable jest-dom matchers**
- **Found during:** Task 1, first test run
- **Issue:** The initial test draft used `toBeInTheDocument()` and
  `toBeEmptyDOMElement()`, but this project's Vitest setup does not register
  `@testing-library/jest-dom` matchers (confirmed by grepping the codebase — no
  other test file uses them either).
- **Fix:** Replaced with plain Chai assertions already used elsewhere in the
  codebase (`toBeDefined()`, `queryByTestId(...).toBeNull()`,
  `container.firstChild` for the null-render checks).
- **Files modified:** `frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx`
- **Commit:** ea8a626c (folded into Task 1's commit, pre-verification fix).

**3. [Rule 3 - Blocking issue] `window.matchMedia` not implemented in jsdom**
- **Found during:** Task 1, first test run
- **Issue:** `TagChip.tsx`'s internal `useIsMobile()` hook calls
  `window.matchMedia`, which jsdom does not implement by default, crashing every
  test that rendered a `TagChip` (the Context column).
- **Fix:** Added the same `Object.defineProperty(window, 'matchMedia', ...)`
  stub already used in `LibraryGameCard.test.tsx`, in a `beforeAll`.
- **Files modified:** `frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx`
- **Commit:** ea8a626c (folded into Task 1's commit, pre-verification fix).

No architectural deviations (Rule 4) were needed.

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired data sources were
introduced.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema
changes at trust boundaries. `game.flaw_markers`/`game.chips` (already fetched by
`useLibraryGame`) render as React children only, matching the plan's threat
register (T-nm8-01 accepted, T-nm8-02 mitigated via the existing `mainLine[ply]
!== undefined` guard pattern, reused verbatim in `tagsPanel`'s `onCyclePly`).

## Self-Check: PASSED

- `frontend/src/components/analysis/AnalysisTagsPanel.tsx` — FOUND
- `frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx` — FOUND
- Commit `ea8a626c` — FOUND (`git log --oneline --all | grep ea8a626c`)
- Commit `96f8bc72` — FOUND
- Commit `bd899cd0` — FOUND
