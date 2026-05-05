---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
plan: "05"
subsystem: frontend
tags: [frontend, table, columns, mobile, components, typescript, react]
dependency_graph:
  requires: ["80-01", "80-02", "80-03", "80-04"]
  provides: ["OpeningWDL TS mirror", "ConfidencePill component", "clockFormat helpers", "MostPlayedOpeningsTable Phase 80 columns"]
  affects: ["Openings stats subtab", "Bookmarked openings table"]
tech_stack:
  added: ["frontend/src/lib/clockFormat.ts", "frontend/src/components/insights/ConfidencePill.tsx"]
  patterns: ["shared formatter extraction", "shared component DRY refactor", "mobile responsive stacked layout"]
key_files:
  created:
    - frontend/src/lib/clockFormat.ts
    - frontend/src/lib/__tests__/clockFormat.test.ts
    - frontend/src/components/insights/ConfidencePill.tsx
    - frontend/src/components/insights/__tests__/ConfidencePill.test.tsx
    - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
  modified:
    - frontend/src/types/stats.ts
    - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/charts/EndgameClockPressureSection.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "formatSignedPct1(0) returns '0.0%' (no plus sign) — zero is neutral, neither advantage nor deficit"
  - "Outcome A: MobileMostPlayedRows in Openings.tsx also updated (separate component, not inside MostPlayedOpeningsTable)"
  - "ConfidencePill uses ReactElement return type (not JSX.Element which requires JSX namespace)"
  - "Bookmark inline OpeningWDL literal in Openings.tsx updated with Phase 80 required field defaults (eval_n:0, eval_confidence:'low', etc.)"
  - "MG triple mobile line uses grid-cols-[auto_1fr_auto_auto] (4 columns: label + bullet + pill + clock) not grid-cols-3"
  - "Tooltip constant strings exported from MostPlayedOpeningsTable.tsx so tests can import and verify D-10 wording"
metrics:
  duration: "~9 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  files_modified: 10
---

# Phase 80 Plan 05: Frontend — Mirror Schema, Shared Helpers, and Extended Table Columns

One-liner: TypeScript schema mirror (15 fields), shared ConfidencePill + clockFormat helpers (DRY), and 5 new desktop columns + 2-line mobile stack in MostPlayedOpeningsTable with D-10 tooltip wording enforcement.

## Tasks Completed

### Task 1: Mirror schema additions + extract shared helpers

**Commit:** `574aab3`

- Extended `OpeningWDL` TypeScript interface with 15 new Phase 80 fields:
  - 6 MG-entry fields: `avg_eval_pawns`, `eval_ci_low_pawns`, `eval_ci_high_pawns`, `eval_n`, `eval_p_value`, `eval_confidence: 'low' | 'medium' | 'high'`
  - 3 clock-diff fields: `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n`
  - 6 EG-entry fields: `avg_eval_endgame_entry_pawns`, `eval_endgame_ci_low_pawns`, `eval_endgame_ci_high_pawns`, `eval_endgame_n`, `eval_endgame_p_value`, `eval_endgame_confidence: 'low' | 'medium' | 'high'`
- Created `frontend/src/lib/clockFormat.ts` with `formatSignedSeconds` and `formatSignedPct1` extracted from `EndgameClockPressureSection.tsx`
- Created `frontend/src/components/insights/ConfidencePill.tsx` as shared component
- Refactored `OpeningFindingCard.tsx` to use `<ConfidencePill>` (DRY — removed inline Tooltip+span)
- Refactored `EndgameClockPressureSection.tsx` to import `formatSignedSeconds` from `@/lib/clockFormat` (no local copy remains)
- 12 new tests: 8 clockFormat + 4 ConfidencePill

### Task 2: Extend MostPlayedOpeningsTable with 5 new columns + 2-line mobile stack

**Commit:** `f036829`

- Added 5 new desktop grid columns: **MG entry** (bullet+CI) | **MG conf.** (pill) | **MG clock** (diff) | **EG entry** (bullet+CI) | **EG conf.** (pill)
- Both bullet cells consume calibrated constants from `openingStatsZones.ts` (MG: EVAL_*, EG: EVAL_ENDGAME_*)
- Independent dimming gates per phase (`isMgUnreliable` / `isEgUnreliable`)
- Em-dash fallback: `eval_n === 0` for MG bullet, `eval_endgame_n === 0` for EG bullet, `clock_diff_n === 0` for clock cell
- Mobile D-06 two-line stack appended to each `OpeningRow`:
  - Line 2: `MG entry` label + bullet + pill + clock-diff
  - Line 3: `EG entry` label + bullet + pill
- 5 InfoPopovers on column headers with named tooltip constants (D-10 enforcement)
- 18 new component tests

## Mobile Renderer Discovery — Outcome A

**Discovery:** A separate `MobileMostPlayedRows` component exists in `frontend/src/pages/Openings.tsx` (line 84-187). Desktop uses `MostPlayedOpeningsTable`, mobile uses this separate component.

**Action applied:** Both components updated with the MG/EG lines per CLAUDE.md "Always apply changes to mobile too."

**Additional file modified:** `frontend/src/pages/Openings.tsx` — `MobileMostPlayedRows` received the same Phase 80 D-06 two-line treatment.

## D-10 Wording Verification

- `MG_EVAL_HEADER_TOOLTIP` contains verbatim `"across analyzed games"` (Lichess ~66% coverage caveat). Test 13 enforces this.
- `EG_EVAL_HEADER_TOOLTIP` does NOT contain that string (99.99% coverage; no caveat). Test 14 enforces this.
- Both constants are exported from `MostPlayedOpeningsTable.tsx` for test-time verification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSX.Element return type in ConfidencePill**
- **Found during:** Task 2 `npm run build`
- **Issue:** Return type `JSX.Element` requires the `JSX` namespace which is not available without explicit import in strict mode
- **Fix:** Changed return type to `ReactElement` (imported from `react`)
- **Files modified:** `frontend/src/components/insights/ConfidencePill.tsx`

**2. [Rule 1 - Bug] Bookmark inline OpeningWDL literal missing required Phase 80 fields**
- **Found during:** Task 2 `npm run build`
- **Issue:** Bookmark row construction at `Openings.tsx:1092` didn't include the new required fields (`eval_n`, `eval_confidence`, `clock_diff_n`, `eval_endgame_n`, `eval_endgame_confidence`)
- **Fix:** Added default values (`eval_n: 0`, `eval_confidence: 'low'`, `clock_diff_n: 0`, `eval_endgame_n: 0`, `eval_endgame_confidence: 'low'`)
- **Files modified:** `frontend/src/pages/Openings.tsx`

### Design Clarifications (not deviations)

- `formatSignedPct1(0)` returns `'0.0%'` (no plus sign). Documented in code comment.
- Mobile grid for MG triple uses `grid-cols-[auto_1fr_auto_auto]` (4 tracks: label + bullet + pill + clock), which correctly arranges the 4 cells.

## Test Results

| Suite | New Tests | Status |
|-------|-----------|--------|
| clockFormat.test.ts | 8 | Passed |
| ConfidencePill.test.tsx | 4 | Passed |
| MostPlayedOpeningsTable.test.tsx | 18 | Passed |
| Full suite | 266 total | Passed |

## Known Stubs

None — all new cells render real data from the backend payload (Phase 80 Plans 01 + 02 populated the fields). When `eval_n === 0` (no eval data for a row), the cell renders '—' which is the correct "no data" state, not a stub.

## Threat Flags

None — this plan is purely presentational. New cells consume existing signed data from the backend. The `eval_confidence` and `eval_endgame_confidence` Literal union types prevent arbitrary strings reaching `ConfidencePill`. Tooltip strings are static constants, not user-interpolated data.

## Self-Check: PASSED

All created files exist on disk. Both task commits verified in git log.

| Item | Result |
|------|--------|
| frontend/src/lib/clockFormat.ts | FOUND |
| frontend/src/components/insights/ConfidencePill.tsx | FOUND |
| frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx | FOUND |
| 80-05-SUMMARY.md | FOUND |
| Commit 574aab3 (Task 1) | FOUND |
| Commit f036829 (Task 2) | FOUND |
