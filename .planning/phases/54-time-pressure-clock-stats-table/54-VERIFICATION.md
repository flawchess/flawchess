---
phase: 54-time-pressure-clock-stats-table
verified: 2026-04-12T17:30:00Z
status: human_needed
score: 6/6
overrides_applied: 0
human_verification:
  - test: "Open the Endgames page in a browser with a user account that has games with clock data across multiple time controls"
    expected: "A 'Time Pressure at Endgame Entry' section appears after the Score Gap section in the Stats tab, showing one row per time control with columns: Games, My avg time (% + seconds), Opp avg time, Avg clock diff, Net timeout rate. Values display in the expected format (e.g., '12% (7s)'), clock diff is green when positive and red when negative, net timeout rate is similarly color-coded."
    why_human: "Visual rendering, color coding, format correctness, and responsive layout (shared statisticsContent covers both desktop and mobile) cannot be verified programmatically."
  - test: "Apply a single time control filter (e.g., Blitz) on the Endgames page"
    expected: "The table updates to show only the Blitz row. If the user has fewer than 10 endgame games for the selected time control, the section is hidden entirely."
    why_human: "Filter interaction and conditional section visibility require live browser testing against real or seeded data."
  - test: "Open the Endgames page with a user account that has no clock data (games imported without %clk annotations)"
    expected: "The clock pressure section is hidden (rows.length === 0 guard fires). The coverage note should not be visible."
    why_human: "Edge case behavior when all clock_seconds are NULL requires a specific test account."
---

# Phase 54: Time Pressure — Clock Stats Table Verification Report

**Phase Goal:** Users see a per-time-control summary table of clock state when entering endgames, answering "how much time do I have when endgames start?" with columns for avg time remaining (% + absolute seconds), opponent avg time, clock diff, and net timeout rate
**Verified:** 2026-04-12T17:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Table shows one row per time control (bullet/blitz/rapid/classical) with columns: Games, My avg time (% + seconds), Opp avg time (% + seconds), Avg clock diff (seconds), Net timeout rate (%) | VERIFIED | `EndgameClockPressureSection.tsx` renders all 6 columns; `_compute_clock_pressure` iterates `_TIME_CONTROL_ORDER = ["bullet","blitz","rapid","classical"]` |
| 2 | User clock = clock_seconds at first user-ply in endgame span; opponent clock = first opponent-ply; time % = clock_seconds / time_control_seconds * 100 | VERIFIED | `_extract_entry_clocks` walks by parity (even=white, odd=black); pct computation at line 710: `user_clock / tc_secs * 100`. 18 unit tests pass (9 for extraction, 9 for pressure computation). |
| 3 | Net timeout rate = (endgame timeout wins − endgame timeout losses) / total endgame games * 100 | VERIFIED | `_compute_clock_pressure` lines 751-753: deduplicates game_ids via sets; formula matches spec. Test `test_net_timeout_rate_computation` confirms (3-1)/20*100 = 10.0. |
| 4 | Games without clock_seconds are excluded from time/clock columns; net timeout uses all endgame games; a note shows "Based on X of Y endgame games (Z% have clock data)" | VERIFIED | Both clocks required for clock averages (line 703: `if user_clock is not None and opp_clock is not None`); `total_endgame_games` accumulates all game_ids. Coverage note at EndgameClockPressureSection.tsx line 127-131. |
| 5 | Time control filter behavior: no filter → all rows (hide < 10 games), one selected → single row, multiple → selected rows only | VERIFIED | `query_clock_stats_rows` receives `time_control` parameter and passes it to `apply_game_filters`. When a specific TC is selected, only those rows are returned by the DB query. The `MIN_GAMES_FOR_CLOCK_STATS = 10` threshold filters sparse rows at line 735. |
| 6 | Section appears in a new "Time Pressure at Endgame Entry" container after the Score Gap section | VERIFIED | `Endgames.tsx` line 278: `clockPressureData && clockPressureData.rows.length > 0` guard, rendered in `charcoal-texture` container after `scoreGapData` block at line 273. `statisticsContent` shared across desktop (line 439) and mobile (line 512). |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/endgames.py` | ClockStatsRow and ClockPressureResponse Pydantic models | VERIFIED | `class ClockStatsRow` at line 227; `class ClockPressureResponse` at line 246; `clock_pressure: ClockPressureResponse` added to `EndgameOverviewResponse` at line 273 |
| `app/repositories/endgame_repository.py` | query_clock_stats_rows function | VERIFIED | `async def query_clock_stats_rows` at line 568; full `array_agg` with `ARRAY(FloatType())` for clock arrays; `apply_game_filters` applied |
| `app/services/endgame_service.py` | _extract_entry_clocks, _compute_clock_pressure, wired into get_endgame_overview | VERIFIED | All three present; `_extract_entry_clocks` at line 627; `_compute_clock_pressure` at line 651; wired at lines 1259-1278 |
| `tests/test_endgame_service.py` | Unit tests for _extract_entry_clocks and _compute_clock_pressure | VERIFIED | `class TestExtractEntryClocks` (9 tests); `class TestComputeClockPressure` (9 tests); `TestGetEndgameOverview` mocks `query_clock_stats_rows`; 18 clock tests pass |
| `frontend/src/types/endgames.ts` | ClockStatsRow and ClockPressureResponse TypeScript interfaces | VERIFIED | Both interfaces at lines 130-147; `clock_pressure: ClockPressureResponse` in `EndgameOverviewResponse` at line 155 |
| `frontend/src/components/charts/EndgameClockPressureSection.tsx` | Table component rendering clock pressure data | VERIFIED | Full component with format helpers, color-coded diffs, InfoPopover, coverage note, all `data-testid` attributes |
| `frontend/src/pages/Endgames.tsx` | Integration of EndgameClockPressureSection into Stats tab | VERIFIED | Imported at line 25; `clockPressureData` extracted at line 136; rendered at lines 278-282 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/endgame_service.py` | `app/repositories/endgame_repository.py` | `import query_clock_stats_rows` | WIRED | Line 26: `from app.repositories.endgame_repository import ..., query_clock_stats_rows` |
| `app/services/endgame_service.py` | `app/schemas/endgames.py` | `import ClockStatsRow, ClockPressureResponse` | WIRED | Both imported from `app.schemas.endgames` |
| `app/services/endgame_service.py:get_endgame_overview` | `_compute_clock_pressure` | sequential call | WIRED | Lines 1259-1270; result assigned `clock_pressure=clock_pressure` at line 1278 |
| `frontend/src/pages/Endgames.tsx` | `EndgameClockPressureSection.tsx` | import and render | WIRED | Imported at line 25; rendered at line 280 |
| `EndgameClockPressureSection.tsx` | `frontend/src/types/endgames.ts` | `import ClockPressureResponse` | WIRED | Line 8: `import type { ClockPressureResponse } from '@/types/endgames'` |
| `frontend/src/types/endgames.ts` | `EndgameOverviewResponse.clock_pressure` | field present | WIRED | Line 155: `clock_pressure: ClockPressureResponse` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EndgameClockPressureSection.tsx` | `data: ClockPressureResponse` | `overviewData?.clock_pressure` from `useEndgameOverview` TanStack Query hook, which calls `GET /api/endgames/overview` | Yes — backend query aggregates `GamePosition.clock_seconds` from DB via `query_clock_stats_rows` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 18 clock unit tests pass | `uv run pytest tests/test_endgame_service.py -x -q -k "clock or Clock"` | 18 passed, 74 deselected | PASS |
| All 92 endgame service tests pass | `uv run pytest tests/test_endgame_service.py -x -q` | 92 passed | PASS |
| ty type check passes | `uv run ty check app/ tests/` | All checks passed | PASS |
| TypeScript compiles cleanly | `npx tsc --noEmit` | No output (zero errors) | PASS |
| ESLint passes | `npm run lint` | No output (zero errors) | PASS |
| Knip finds no dead exports | `npm run knip` | No output (zero issues) | PASS |

### Requirements Coverage

Phase 54 has no formal requirement IDs (N/A per ROADMAP.md). Coverage tracked via ROADMAP Success Criteria SC-1 through SC-6, all verified above. Both plans declared requirements as plan-internal SCs:

- Plan 01: ["SC-1", "SC-2", "SC-3", "SC-4", "SC-5"] — all verified via backend implementation
- Plan 02: ["SC-1", "SC-4", "SC-5", "SC-6"] — all verified via frontend implementation

### Anti-Patterns Found

No blockers, warnings, or stub patterns detected in modified files. All format helpers (`formatClockCell`, `formatSignedSeconds`, `formatNetTimeoutRate`) produce real values. The `defaultdict` accumulators populate from actual DB query results, not hardcoded empty data.

### Human Verification Required

#### 1. Visual Table Rendering and Color Coding

**Test:** Open the Endgames page in a browser with a user account that has games with clock data across multiple time controls.
**Expected:** "Time Pressure at Endgame Entry" section appears after the Score Gap section in the Stats tab. Table shows one row per time control. Clock cells format as "X% (Ys)". Avg clock diff is green when positive, red when negative, neutral at zero. Net timeout rate is color-coded the same way. InfoPopover renders on the header.
**Why human:** Visual rendering, color accuracy, and number formatting cannot be verified programmatically.

#### 2. Time Control Filter Interaction

**Test:** Apply a single time control filter (e.g., Blitz only) on the Endgames page.
**Expected:** The table updates to show only the Blitz row (or is hidden if fewer than 10 blitz endgame games exist). The "Based on X of Y" coverage note reflects only blitz games.
**Why human:** Filter state interaction and conditional section visibility require a live browser session.

#### 3. Zero Clock Data Edge Case

**Test:** Access the Endgames page with an account whose games have no `%clk` annotations (e.g., very old games imported without clock data).
**Expected:** The clock pressure section is hidden entirely (the `rows.length > 0` guard fires). No error, no empty table visible.
**Why human:** Requires a specific test account configuration or seeded data with no clock data.

### Gaps Summary

No gaps. All 6 roadmap success criteria are verified by code inspection and automated tests. Three human verification items remain for visual/interactive behavior that cannot be confirmed programmatically.

---

_Verified: 2026-04-12T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
