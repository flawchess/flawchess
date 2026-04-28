---
phase: 76
plan: 05
subsystem: frontend
tags: [frontend, move-explorer, score-coloring, confidence-column, mute-rule]
dependency_graph:
  requires: ["76-03", "76-04"]
  provides: ["INSIGHT-UI-02", "INSIGHT-UI-03", "INSIGHT-UI-07"]
  affects: ["frontend/src/components/move-explorer/MoveExplorer.tsx"]
tech_stack:
  added: []
  patterns:
    - "score-based getArrowColor(score, gameCount, isHovered) call site"
    - "Conf column header with data-testid for automation"
    - "extended mute rule: game_count < 10 OR confidence === 'low'"
key_files:
  created: []
  modified:
    - "frontend/src/components/move-explorer/MoveExplorer.tsx"
    - "frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx"
decisions:
  - "Used score: 0.50 in makeMoves() helper to keep existing no-tint highlightedMove tests stable; makeEntry fixture default remains score: 0.625 per plan spec"
  - "Replaced toHaveTextContent (requires @testing-library/jest-dom, not installed) with textContent assertions consistent with existing test patterns"
  - "Kept '(low)' text in Games column using inline game_count < MIN_GAMES_FOR_RELIABLE_STATS check after renaming isBelowThreshold to isUnreliable"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-28"
  tasks_completed: 2
  files_modified: 2
---

# Phase 76 Plan 05: MoveExplorer Conf Column + Score-Based Tint Summary

**One-liner:** Conf column (low/med/high), score-based getArrowColor call site fix, and extended mute rule (game_count<10 OR confidence=low) wired into MoveExplorer.tsx with 5 new tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Conf column, update getArrowColor call site, extend mute rule | 22f90c7 | MoveExplorer.tsx |
| 2 | Extend MoveExplorer.test.tsx for Conf column + mute rule | 6d89d4f | MoveExplorer.test.tsx |

## What Was Built

### Task 1: MoveExplorer.tsx

- **getArrowColor call site fixed:** `getArrowColor(entry.win_pct, entry.loss_pct, entry.game_count, false)` replaced with `getArrowColor(entry.score, entry.game_count, false)` — resolves the build-breaking signature mismatch introduced in Plan 03.
- **Extended mute rule (D-11):** `isBelowThreshold` replaced with `isLowConfidence = entry.confidence === 'low'` and `isUnreliable = game_count < MIN_GAMES_FOR_RELIABLE_STATS || isLowConfidence`. Both conditions independently trigger `UNRELIABLE_OPACITY`.
- **Conf column header:** `<th data-testid="move-explorer-th-conf">Conf</th>` inserted between Games and Results column headers. Width `w-[2.5rem]` keeps table compact at 375px viewport.
- **Conf cell per row:** `{entry.confidence === 'medium' ? 'med' : entry.confidence}` renders low/med/high per row. Medium abbreviates to "med" per D-08. Inline ternary avoids noUncheckedIndexedAccess pitfall.
- **Mobile parity:** MoveExplorer uses a single responsive table layout (no separate mobile branch) — Step E was a no-op.

### Task 2: MoveExplorer.test.tsx

- **makeEntry fixture extended** with `score: 0.625`, `confidence: 'high'`, `p_value: 0.05` defaults.
- **makeMoves() updated** to use `score: 0.50` (neutral) so existing no-background-tint highlightedMove tests remain stable.
- **5 new tests** in `describe('Phase 76 — Conf column + mute extension')`:
  1. Conf header renders with `data-testid="move-explorer-th-conf"`
  2. low/med/high labels render per entry.confidence
  3. UNRELIABLE_OPACITY applied when confidence === "low"
  4. UNRELIABLE_OPACITY applied when game_count < 10
  5. UNRELIABLE_OPACITY NOT applied when game_count >= 10 AND confidence !== "low"

## Verification

- `cd frontend && npx vitest run src/components/move-explorer/__tests__/MoveExplorer.test.tsx` — 11/11 tests pass
- `cd frontend && npx tsc --noEmit` — zero errors
- `cd frontend && npm run lint` — 0 errors (3 warnings in coverage/ files, pre-existing)
- `cd frontend && npm run knip` — clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixture default score 0.625 caused existing tint-tests to fail**
- **Found during:** Task 2 — first test run
- **Issue:** Plan specified `score: 0.625` as the `makeEntry` default. This caused `getArrowColor(0.625, 100, false)` to return `DARK_GREEN`, giving rows a severity tint background. Two existing tests that assert `row.style.backgroundColor === ''` (checking no highlight tint) failed.
- **Fix:** Updated `makeMoves()` to explicitly pass `score: 0.50` per move, keeping existing tests focused on the highlight mechanism. The `makeEntry` fixture default remains `0.625` per plan spec.
- **Files modified:** MoveExplorer.test.tsx

**2. [Rule 1 - Bug] toHaveTextContent not available (jest-dom not installed)**
- **Found during:** Task 2 — first test run
- **Issue:** Plan specified `toHaveTextContent()` matcher which requires `@testing-library/jest-dom`. The project only has `@testing-library/react` with no jest-dom setup.
- **Fix:** Used `th.textContent?.trim()` and `.textContent.toContain()` consistent with the existing test patterns in the file (`row.style.*` assertions).
- **Files modified:** MoveExplorer.test.tsx

## Known Stubs

None — all cells render live data from `entry.confidence` and `entry.score`.

## Threat Flags

None — pure-frontend rendering of Pydantic-validated Literal string. No new trust boundaries.

## Self-Check: PASSED

- `frontend/src/components/move-explorer/MoveExplorer.tsx` — file exists, contains `move-explorer-th-conf` and `getArrowColor(entry.score`
- `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` — file exists, contains `Phase 76 — Conf column`
- Commit `22f90c7` — verified in git log
- Commit `6d89d4f` — verified in git log
