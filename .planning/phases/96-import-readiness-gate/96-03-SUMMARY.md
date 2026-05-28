---
phase: 96-import-readiness-gate
plan: "03"
subsystem: frontend
tags: [eval-gating, openings, ui-state, cleanup]
dependency_graph:
  requires: ["96-01"]
  provides: ["EvalCpuPlaceholder", "tier2-gated-eval-rows", "auto-reload-free-eval-coverage"]
  affects: ["frontend/src/components/stats/OpeningStatsCard.tsx", "frontend/src/hooks/useEvalCoverage.ts", "frontend/src/components/insights/EvalConfidenceTooltip.tsx"]
tech_stack:
  added: []
  patterns: ["tier2-gating", "pulsating-Cpu-placeholder", "reactive-reveal"]
key_files:
  created:
    - frontend/src/components/stats/EvalCpuPlaceholder.tsx
    - frontend/src/components/stats/__tests__/EvalCpuPlaceholder.test.tsx
  modified:
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
    - frontend/src/components/insights/EvalConfidenceTooltip.tsx
    - frontend/src/components/insights/__tests__/EvalConfidenceTooltip.test.tsx
    - frontend/src/components/insights/BulletConfidencePopover.tsx
    - frontend/src/hooks/useEvalCoverage.ts
    - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
decisions:
  - "Inlined amber Tailwind classes in EvalCpuPlaceholder (2 sites total with EvalCoverageHeader) per UI-SPEC Amber Token Note — no new theme constant added"
  - "useReadiness (not useEvalCoverage) drives OpeningStatsCard tier2 gate; useEvalCoverage remains solely for EvalCoverageHeader global bar"
  - "Replaced 3 caveat-presence tests in EvalConfidenceTooltip.test.tsx with 6 caveat-absence assertions confirming removal"
metrics:
  duration: "9 minutes"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 7
  files_created: 2
---

# Phase 96 Plan 03: Eval-CPU Placeholder, Tier2 Gate, and Auto-Reload Removal Summary

**One-liner:** Amber pulsating-Cpu placeholder hides eval rows in OpeningStatsCard until Tier 2, eval counter removed from tooltips, and `window.location.reload()` retired from `useEvalCoverage`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Build EvalCpuPlaceholder + gate OpeningStatsCard eval row on tier2 | 74382a93 | EvalCpuPlaceholder.tsx, OpeningStatsCard.tsx, EvalCpuPlaceholder.test.tsx |
| 2 | Remove eval counter from EvalConfidenceTooltip + BulletConfidencePopover props | 1e1b33fd | EvalConfidenceTooltip.tsx, BulletConfidencePopover.tsx, EvalConfidenceTooltip.test.tsx |
| 3 | Retire window.location.reload from useEvalCoverage + verify knip/build green | bb5abdea | useEvalCoverage.ts, useEvalCoverage.test.tsx |

## What Was Built

### Task 1: EvalCpuPlaceholder + tier2 gate

New `EvalCpuPlaceholder` component mirrors `EvalCoverageHeader` styling exactly: amber border (`border-amber-400/40 bg-amber-50/60`), pulsating `Cpu` icon, "Analyzing…" label, `data-testid="eval-cpu-placeholder"`. Spans the full 2-column grid (`col-span-2`) to replace both the eval bullet row and eval-text+popover row as a unit.

`OpeningStatsCard` now imports `useReadiness` instead of `useEvalCoverage`, destructures `tier2`, and wraps the two eval rows in a conditional: `{tier2 ? <bullet+text rows> : <EvalCpuPlaceholder />}`. The WDL score row is unconditionally rendered.

### Task 2: Eval counter removed

`EvalConfidenceTooltip` had `isPending`/`pendingCount` props and a `data-testid="eval-pending-caveat"` JSX block that showed "Stockfish is still analysing N more games…". These are deleted. `AlertTriangle` import also removed. `BulletConfidencePopover` forwarded those props; both the interface and forwarding are removed. `OpeningStatsCard` already stopped passing them in Task 1.

### Task 3: Auto-reload retired

`useEvalCoverage.ts` had a module-level `evalCompletionReloadFired` boolean guard, a `wasPendingRef`, and a `useEffect` that called `window.location.reload()` on a pending→complete transition. All three are deleted along with the now-unused `useRef`/`useEffect` imports. The return shape (`pendingCount`, `totalCount`, `pct`, `isPending`, `isLoading`) is unchanged — `EvalCoverageHeader` global bar continues to work. A comment documents the design decision.

## Test Results

- `npm test -- --run EvalCpuPlaceholder`: 8 tests pass (4 standalone + 4 tier2-gate OpeningStatsCard cases)
- `npm test -- --run EvalConfidenceTooltip`: 6 tests pass (all caveat-absence assertions)
- `npm test -- --run useEvalCoverage`: 5 tests pass (4 existing + 1 new reload-absent assertion)
- `npm run knip`: exits 0 (no dead exports)
- ESLint on all modified files: clean

## Deviations from Plan

None — plan executed exactly as written. The `vi.mock` hoisting issue in the initial EvalCpuPlaceholder test was addressed by switching to `vi.fn()` at module level + `vi.mocked(...).mockReturnValue(...)` in individual tests, which is idiomatic vitest practice.

## Known Stubs

None. `EvalCpuPlaceholder` renders "Analyzing…" as the in-progress label — this is intentional copy, not placeholder text.

## Threat Flags

None. The changes are display-only UI gating of the user's own data. Threat T-96-06 (auto-reload removal) and T-96-07 (partial eval data hidden behind placeholder) are both mitigated as planned.

## Self-Check: PASSED

Files exist:
- `frontend/src/components/stats/EvalCpuPlaceholder.tsx` — FOUND
- `frontend/src/components/stats/__tests__/EvalCpuPlaceholder.test.tsx` — FOUND

Commits exist:
- 74382a93 (Task 1) — FOUND
- 1e1b33fd (Task 2) — FOUND
- bb5abdea (Task 3) — FOUND
