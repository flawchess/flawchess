---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
verified: 2026-05-03T21:40:00Z
status: human_needed
score: 11/12
overrides_applied: 0
human_verification:
  - test: "Navigate to /openings/stats on desktop (lg+ viewport). Confirm chess board is hidden. Confirm MostPlayedOpeningsTable shows 5 new column headers: MG entry | MG conf. | MG clock | EG entry | EG conf."
    expected: "Board not visible; 5 column headers visible with InfoPopover icons"
    why_human: "lg:hidden CSS class on board container — cannot verify Tailwind responsive class without rendering in browser"
  - test: "Hover the MG entry column header InfoPopover. Confirm tooltip text contains 'across analyzed games'."
    expected: "Tooltip reads 'Average Stockfish evaluation when your middlegame begins ... Computed across analyzed games (Lichess analyses ~66% of imported games).'"
    why_human: "Tooltip rendering requires live browser — unit test confirms text but not hover interaction"
  - test: "Hover the EG entry column header InfoPopover. Confirm tooltip text does NOT contain 'across analyzed games'."
    expected: "Tooltip reads 'Average Stockfish evaluation when your endgame begins, signed from your perspective.' without any coverage caveat."
    why_human: "Tooltip rendering requires live browser"
  - test: "At 320px viewport (mobile), open Openings > Stats. Confirm each opening row shows: line 1 = name+games+WDL, line 2 = 'MG entry' label + bullet + pill + clock-diff, line 3 = 'EG entry' label + bullet + pill. Confirm no horizontal overflow."
    expected: "Three stacked lines per row; no scroll beyond viewport width at 320px"
    why_human: "Responsive layout at 320px requires device/viewport simulation"
  - test: "For an opening with data: MG bullet chart shows a filled bar with a thin horizontal whisker (95% CI). Confidence pill shows 'low', 'medium', or 'high'. Clock diff shows '+X.X% (+Ys)' format or '—'."
    expected: "Bullet bar colored by zone (danger/neutral/success); whisker visible; pill matches p-value bucket; clock format consistent with EndgameClockPressureSection"
    why_human: "Visual rendering of SVG-free CSS bullet chart + CI whisker requires browser inspection"
  - test: "For a row with low confidence (eval_n < 10 or eval_confidence === 'low'), verify the MG bullet cell and EG bullet cell are dimmed at 0.5 opacity."
    expected: "Both bullet cells show at UNRELIABLE_OPACITY (0.5) when respective confidence is 'low'"
    why_human: "Inline style opacity requires visual browser inspection"
  - test: "Navigate to /openings/stats. Verify bookmarked openings table shows 5 new column headers. Note that all eval/clock cells show '—' (no data for bookmarks). This is expected — bookmark data comes from a different API path. Confirm the table renders without errors."
    expected: "Bookmarked table has the same 5 column headers; all new cells show '—'; no JS errors in console"
    why_human: "Requires live bookmark data and browser console inspection"
  - test: "EXPLAIN ANALYZE /api/stats/most-played-openings for Adrian's user (heavy user). Confirm no Nested Loop hang and query completes in < 2s."
    expected: "Query plan uses index scans; no sequential scan on full game_positions for a single user; wall time < 2s"
    why_human: "Requires production-level data volume and direct DB access — cannot verify with test fixtures"
---

# Phase 80: Opening Stats Middlegame-Entry Eval and Clock-Diff Columns — Verification Report

**Phase Goal:** Extend the Openings > Stats subtab tables (bookmarked openings + most-played openings) with five new columns consuming Phase 79 Stockfish evals at phase boundaries: (1) avg eval at MG entry as MiniBulletChart with 95% CI whisker, (2) MG confidence pill (one-sample t-test vs 0), (3) avg clock diff at MG entry, (4) avg eval at EG entry as MiniBulletChart with wider domain, (5) EG confidence pill. Both desktop and mobile layouts updated. Chess board hidden on Stats subtab desktop.

**Verified:** 2026-05-03T21:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OpeningWDL schema has 15 new optional Phase 80 fields (6 MG eval + 3 clock-diff + 6 EG eval) with Literal confidence types | VERIFIED | `app/schemas/stats.py:61-93` — all 15 fields present, `eval_confidence: Literal["low","medium","high"]` at line 69, `eval_endgame_confidence: Literal["low","medium","high"]` at line 93 |
| 2 | `compute_eval_confidence_bucket` uses two-sided Wald-z, Bessel-corrected variance, n<10 gate, no scipy, reuses OPENING_INSIGHTS_CONFIDENCE_* constants, returns tuple[Literal,float,float,float] | VERIFIED | `app/services/eval_confidence.py:47-124` — Bessel: line 97, z-test: line 109 `math.erfc(abs(z)/math.sqrt(2.0))`, n<10 gate: line 115, constants imported from `opening_insights_constants` at lines 39-44 |
| 3 | SQL aggregation uses single-pass `phase IN (1,2)` with FILTER partitioning; outlier trim `abs(eval_cp) < 2000` inside FILTER predicate; gp_entry/gp_opp joins include `user_id` (WR-03 fix) | VERIFIED | `stats_repository.py:511-672` — ROW_NUMBER phase IN (1,2) at line 529, FILTER predicates lines 612-655, `has_continuous_in_domain_eval` includes `func.abs(gp_entry.eval_cp) < EVAL_OUTLIER_TRIM_CP` at line 592, user_id in gp_entry join at line 663, gp_opp join at line 669 |
| 4 | `get_most_played_openings` calls `compute_eval_confidence_bucket` exactly twice per opening (MG + EG), sequentially (no asyncio.gather); clock_diff_pct uses per-game-average ratio (WR-04 fix) | VERIFIED | `stats_service.py:411-444` — two sequential calls at lines 412, 425; no asyncio import or gather in file; per-game ratio at lines 443-444 `avg_base_time = pe.base_time_sum / pe.clock_diff_n; avg_clock_diff_pct = (avg_clock_diff_seconds / avg_base_time) * 100.0` |
| 5 | MiniBulletChart extended with optional `ciLow`/`ciHigh` props; undefined → unchanged render; end-cap suppressed when CI exceeds domain | VERIFIED | `MiniBulletChart.tsx:48-51` props declared optional; line 160 `ciLow !== undefined && ciHigh !== undefined` guard; lines 176-186 `!lowOpen` / `!highOpen` end-cap suppression |
| 6 | ConfidencePill is a single shared component used in MostPlayedOpeningsTable (4x desktop, 4x mobile per row) AND OpeningFindingCard; eval-context tooltip (WR-02 fix) when `evalMeanPawns` provided | VERIFIED | `ConfidencePill.tsx` exists at `frontend/src/components/insights/ConfidencePill.tsx`; `OpeningFindingCard.tsx:113` uses it; `MostPlayedOpeningsTable.tsx:210,241` (desktop MG/EG); `Openings.tsx:217,269` (mobile MG/EG); `ConfidenceTooltipContent.tsx:48-72` eval branch on `evalMeanPawns` |
| 7 | MostPlayedOpeningsTable has 5 new desktop columns; mobile two-line stack (line 2 MG triple, line 3 EG pair); `eval_n === 0` shows "—"; low confidence dims at UNRELIABLE_OPACITY (0.5); testIds on all cells including mobile pills (IN-01 fix) | VERIFIED | `MostPlayedOpeningsTable.tsx:148` 8-column grid; lines 196-248 desktop columns 4-8; lines 251-303 mobile MG line + EG line; line 93 em-dash fallback for MG; line 110 for EG; lines 200,231 `style={...UNRELIABLE_OPACITY...}`; testIds at lines 199,209,215,221,229,239,259,264,289,294 (including mobile) |
| 8 | Both tables (bookmarked + most-played) render 5 new column cells via shared MostPlayedOpeningsTable component | VERIFIED (component); WARNING (data) | `Openings.tsx:1157,1188` bookmarked openings desktop; `Openings.tsx:1230,1262` most-played openings desktop — all 4 use `MostPlayedOpeningsTable`. However, bookmark rows are constructed with `eval_n: 0` (line 1113) — all eval/clock cells show "—" for bookmarks because bookmark data comes from time-series API, not phase-entry metrics API. Column structure exists; real data absent. See WARNING below. |
| 9 | Chess board hidden on Stats subtab desktop at lg+ via `getBoardContainerClassName`; mobile unchanged | VERIFIED | `openingsBoardLayout.ts:15-17` returns `lg:hidden` when `activeTab === 'stats'`; `Openings.tsx:1404` uses this; JSX element preserved (not removed) for chess.js state |
| 10 | D-10: MG header tooltip contains "across analyzed games"; EG header tooltip does NOT | VERIFIED | `MostPlayedOpeningsTable.tsx:29-33` — `MG_EVAL_HEADER_TOOLTIP` contains "across analyzed games"; `EG_EVAL_HEADER_TOOLTIP` at line 32-33 does not; rendered at lines 336, 366 |
| 11 | CHANGELOG [Unreleased] has Phase 80 user-facing entry under `### Added` referencing both MG and EG pillars | VERIFIED | `CHANGELOG.md:11-17` — Phase 80 entry under `### Added` with five-column description; `### Changed` section documents DRY refactors |
| 12 | Test discipline: 1241 backend tests pass; 270 frontend tests pass; ty zero errors; ruff clean; knip clean; build succeeds | VERIFIED | `uv run pytest`: 1241 passed, 6 skipped; `npm test -- --run`: 270 passed; `uv run ty check app/ tests/`: 0 errors; `uv run ruff check .`: clean; `npm run knip`: clean; `npm run build`: successful; eslint 0 errors (3 pre-existing coverage/ warnings) |

**Score:** 11/12 truths verified (11 VERIFIED or VERIFIED with warning, 1 requires human confirmation)

---

### WARNING: Bookmarked Openings Eval Data

Truth #8 is VERIFIED at the component level but has a data gap. The `buildBookmarkRows` function in `Openings.tsx:1087-1121` constructs `OpeningWDL` objects from the time-series API (not the `stats/most-played-openings` endpoint). The inline row literal sets `eval_n: 0`, `eval_confidence: 'low'`, `clock_diff_n: 0`, `eval_endgame_n: 0`, `eval_endgame_confidence: 'low'`. All five new cells therefore display "—" for bookmarked openings.

This is documented as an explicit plan decision (80-05-SUMMARY.md decision line 30: "Bookmark inline OpeningWDL literal in Openings.tsx updated with Phase 80 required field defaults"). The column headers and cell structure are present in the bookmarked table; a future phase could wire a `stats/bookmark-phase-entry` endpoint to populate real data.

**Impact:** The ROADMAP says "Both tables (bookmarked + most-played) get the same new columns" — component columns exist. But if "columns" means "columns with actual data", the bookmarked table delivers only column scaffolding. This is a scope boundary judgment, not an implementation error.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/eval_confidence.py` | `compute_eval_confidence_bucket` with Wald-z, Bessel, n-gate | VERIFIED | 125 lines; correct implementation |
| `app/schemas/stats.py` | `OpeningWDL` with 15 new optional fields | VERIFIED | Lines 61-93; all 15 fields; Literal typing |
| `app/repositories/stats_repository.py` | `query_opening_phase_entry_metrics_batch` with FILTER partitioning | VERIFIED | Lines 469-694; single-pass SQL; user_id in joins |
| `app/services/stats_service.py` | `get_most_played_openings` calls helper twice per opening | VERIFIED | Lines 326-365 (batch queries); 411-444 (finalizer with 2 calls) |
| `frontend/src/types/stats.ts` | `OpeningWDL` TS interface with 15 new fields | VERIFIED | Lines 45-66; optional fields; Literal types |
| `frontend/src/lib/clockFormat.ts` | `formatSignedPct1`, `formatSignedSeconds` | VERIFIED | 33 lines; both functions; imported by EndgameClockPressureSection |
| `frontend/src/components/insights/ConfidencePill.tsx` | Shared component with eval-context tooltip branch | VERIFIED | 58 lines; `evalMeanPawns` prop; used by OpeningFindingCard and MostPlayedOpeningsTable |
| `frontend/src/components/charts/MiniBulletChart.tsx` | Extended with `ciLow`/`ciHigh` optional props | VERIFIED | Lines 48-51 props; lines 160-196 CI whisker render with end-cap suppression |
| `frontend/src/lib/openingsBoardLayout.ts` | `getBoardContainerClassName` hides board at lg+ on stats tab | VERIFIED | Line 16: `lg:hidden` appended when `activeTab === 'stats'` |
| `frontend/src/lib/openingStatsZones.ts` | MG zones (±0.20 neutral, ±1.50 domain) + EG zones (±0.35 neutral, ±3.50 domain) | VERIFIED | Lines 28-47; all 6 constants match D-07 calibration |
| `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` | 5 new desktop columns + 2-line mobile stack + D-10 tooltips | VERIFIED | Lines 148-423; 8-column grid; mobile lines 251-303; InfoPopovers with D-10 strings |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `eval_confidence.py` | `opening_insights_constants.py` | `from app.services.opening_insights_constants import OPENING_INSIGHTS_CI_Z_95, ..._HIGH_MAX_P, ..._MEDIUM_MAX_P, ..._MIN_N` | VERIFIED | Lines 39-44 |
| `stats_service.py` | `eval_confidence.py` | `from app.services.eval_confidence import compute_eval_confidence_bucket` + calls at lines 412, 425 | VERIFIED | Lines 27, 412, 425 |
| `stats_service.py` | `stats_repository.py` | `query_opening_phase_entry_metrics_batch` called with all filter params sequentially | VERIFIED | Lines 326-338 (white), 353-365 (black) |
| `MostPlayedOpeningsTable.tsx` | `MiniBulletChart.tsx` | `<MiniBulletChart ciLow={...} ciHigh={...} domain={EVAL_*_DOMAIN_PAWNS} .../>` | VERIFIED | Lines 97-104 (MG), 115-124 (EG) |
| `MostPlayedOpeningsTable.tsx` | `ConfidencePill.tsx` | `<ConfidencePill level={o.eval_confidence} evalMeanPawns={o.avg_eval_pawns} .../>` | VERIFIED | Lines 210-216, 241-247 (desktop); 265-273, 294-300 (mobile) |
| `MostPlayedOpeningsTable.tsx` | `clockFormat.ts` | `import { formatSignedPct1, formatSignedSeconds } from '@/lib/clockFormat'` | VERIFIED | Line 18 |
| `MostPlayedOpeningsTable.tsx` | `openingStatsZones.ts` | `import { EVAL_BULLET_DOMAIN_PAWNS, EVAL_NEUTRAL_*, EVAL_ENDGAME_* } from '@/lib/openingStatsZones'` | VERIFIED | Lines 11-17 |
| `EndgameClockPressureSection.tsx` | `clockFormat.ts` | `import { formatSignedSeconds } from '@/lib/clockFormat'` | VERIFIED | Line 11 of EndgameClockPressureSection.tsx |
| `Openings.tsx` | `openingsBoardLayout.ts` | `import { getBoardContainerClassName } from '@/lib/openingsBoardLayout'` + used at line 1404 | VERIFIED | Lines 76, 1404 |
| `OpeningFindingCard.tsx` | `ConfidencePill.tsx` | `import { ConfidencePill } from '@/components/insights/ConfidencePill'` + used at line 113 | VERIFIED | Lines 4, 113 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `MostPlayedOpeningsTable.tsx` | `o.avg_eval_pawns`, `o.eval_confidence`, `o.avg_clock_diff_pct`, `o.avg_eval_endgame_entry_pawns` | `stats/most-played-openings` API → `get_most_played_openings` → `query_opening_phase_entry_metrics_batch` + `compute_eval_confidence_bucket` | Yes — DB query aggregates `game_positions` with FILTER partitioning; `eval_cp` from Phase 79 import pipeline | FLOWING (most-played); STATIC (bookmarks: hardcoded `eval_n:0`) |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `compute_eval_confidence_bucket` unit tests | `uv run pytest tests/services/test_eval_confidence.py -q --tb=no` | 17 passed in 0.2s | PASS |
| Phase-entry repository tests | `uv run pytest tests/test_stats_repository_phase_entry.py -q --tb=no` | 12 passed | PASS |
| Phase-entry service tests | `uv run pytest tests/services/test_stats_service_phase_entry.py -q --tb=no` | 9 passed | PASS |
| Full backend suite | `uv run pytest -x -q --tb=short` | 1241 passed, 6 skipped | PASS |
| Frontend tests (includes MostPlayedOpeningsTable, ConfidencePill, clockFormat, MiniBulletChart tests) | `npm test -- --run` (from frontend/) | 270 passed, 24 files | PASS |
| ty type check | `uv run ty check app/ tests/` | 0 errors | PASS |
| ruff lint | `uv run ruff check .` | 0 issues | PASS |
| knip dead exports | `npm run knip` | 0 issues | PASS |
| eslint | `npm run lint` | 0 errors (3 pre-existing coverage/ warnings) | PASS |
| Frontend build | `npm run build` | Successful (5.7s, 1102 kB main bundle) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| D-01 | 80-01, 80-05 | Avg eval at MG entry as MiniBulletChart (signed, user-perspective, ±1.50 pawn domain) | VERIFIED | `MostPlayedOpeningsTable.tsx:92-104` |
| D-02 | 80-03 | MiniBulletChart extended with optional ciLow/ciHigh whisker props | VERIFIED | `MiniBulletChart.tsx:48-51, 160-196` |
| D-03 | 80-04 | Board hidden on Stats subtab desktop (lg+), mobile unchanged | VERIFIED | `openingsBoardLayout.ts:16`; `Openings.tsx:1404` |
| D-04 | 80-01, 80-05 | MG confidence pill (ConfidencePill) one-sample Wald-z, n>=10 gate, reuses OPENING_INSIGHTS_CONFIDENCE_* | VERIFIED | `eval_confidence.py:47-124`; `ConfidencePill.tsx` |
| D-05 | 80-01, 80-05 | Clock-diff cell "+X.X% (+Ys)" using formatSignedPct1/formatSignedSeconds | VERIFIED | `clockFormat.ts:28-33`; `MostPlayedOpeningsTable.tsx:134-139` |
| D-06 | 80-05 | Mobile two-line stack: line 2 MG triple, line 3 EG pair | VERIFIED | `MostPlayedOpeningsTable.tsx:251-303`; `Openings.tsx:173-303` (MobileMostPlayedRows) |
| D-07 | 80-04 | MG zones [-0.20,+0.20] ±1.50 domain; EG zones [-0.35,+0.35] ±3.50 domain | VERIFIED | `openingStatsZones.ts:28-47` |
| D-08 | 80-02 | Outlier trim `|eval_cp| < 2000` inside FILTER predicate (SQL) | VERIFIED | `stats_repository.py:592` `func.abs(gp_entry.eval_cp) < EVAL_OUTLIER_TRIM_CP` in `has_continuous_in_domain_eval` |
| D-09 | 80-01, 80-02, 80-05 | EG-entry parallel pillar (MiniBulletChart + ConfidencePill); `phase = 2` FILTER; `eval_endgame_*` fields | VERIFIED | `stats_repository.py:640-655` EG FILTER; `stats_service.py:423-433`; `MostPlayedOpeningsTable.tsx:107-124` |
| D-10 | 80-05 | MG header tooltip: "across analyzed games"; EG header tooltip: no coverage caveat | VERIFIED | `MostPlayedOpeningsTable.tsx:28-33`; test 13/14/15 in test file |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `frontend/src/pages/Openings.tsx:1113-1117` | Bookmark rows hardcoded `eval_n: 0`, `clock_diff_n: 0` | INFO | Intentional: bookmark data API does not provide phase-entry metrics. Cells show "—". Column structure exists. Documented in 80-05-SUMMARY.md. |
| `frontend/src/lib/clockFormat.ts:30` | Double rounding: `Math.round(pct*10)/10` then `.toFixed(1)` | INFO | Cosmetic only; functionally correct. Also: `-0.05%` edge case renders as `-0.0%` — won't occur in practice. Noted as IN-03 in review, not fixed (low impact). |

---

### Human Verification Required

#### 1. Board Hide on Stats Subtab (Desktop, D-03)

**Test:** Navigate to /openings/stats on a desktop viewport (1280px+). Verify the chess board container is not visible.
**Expected:** The board area (below the opening filter) is hidden; the stats tables span the full available width.
**Why human:** The `lg:hidden` Tailwind class is applied correctly in code, but rendering requires a browser at the correct breakpoint.

#### 2. D-10 Tooltip Wording — "across analyzed games" Verbatim

**Test:** Hover the MG entry column header (ⓘ icon). Verify the tooltip body contains "across analyzed games". Hover the EG entry column header. Verify its tooltip does NOT contain "across analyzed games".
**Expected:** MG tooltip: "...Computed across analyzed games (Lichess analyses ~66% of imported games)." EG tooltip: "Average Stockfish evaluation when your endgame begins, signed from your perspective."
**Why human:** Tooltip text correctness is tested in unit tests (Test 13/14/15), but visual rendering in the UI requires live browser hover interaction.

#### 3. Bullet Chart + CI Whisker Visual Smoke (D-01, D-02, D-09)

**Test:** With an opening that has eval_n >= 2, confirm the MG entry column shows a MiniBulletChart with: (a) a colored bar from zero to the mean value, (b) a thin horizontal whisker representing the 95% CI, (c) end-caps on the whisker where CI does not exceed domain.
**Expected:** Bar and whisker visible; whisker is thinner than bar; end-caps visible at CI endpoints when within domain.
**Why human:** CSS-based bullet chart rendering requires visual inspection; unit tests confirm DOM structure but not visual appearance.

#### 4. Mobile Layout — No Overflow at 320px (D-06)

**Test:** At 320px viewport width, open Openings > Stats. For each opening row: confirm line 2 (MG entry label + bullet + pill + clock-diff) and line 3 (EG entry label + bullet + pill) do not overflow horizontally.
**Expected:** All three lines fit within 320px; no horizontal scroll; text/charts truncate or wrap gracefully.
**Why human:** Responsive overflow requires device/viewport simulation; CSS grid `grid-cols-[auto_1fr_auto_auto]` may still overflow on certain label lengths.

#### 5. Confidence Pill Tooltip — Eval Context Language (WR-02 fix)

**Test:** Hover a confidence pill in the MG entry or EG entry column. Confirm the tooltip shows eval-centric language (avg eval in pawns, p-value, "significant eval advantage/disadvantage") rather than WDL score/strength/weakness language.
**Expected:** Tooltip contains "Avg eval: +X.XX pawns (avg at phase entry)" and "Possibly a significant eval advantage/disadvantage" (medium) or "Likely a significant eval advantage/disadvantage" (high).
**Why human:** Tooltip rendering with dynamic data requires live browser with real eval values.

#### 6. Bookmarked Openings Table Rendering (Data Gap Note)

**Test:** Navigate to /openings/stats with bookmarks. Confirm the bookmarked openings table shows 5 new column headers (MG entry, MG conf., MG clock, EG entry, EG conf.). Confirm all new cells show "—". Confirm no JS errors in console.
**Expected:** Column headers visible; all eval/clock cells show em-dash; table renders without errors.
**Why human:** Requires live bookmark data and browser console access. The "—" behavior is intentional (bookmark data pipeline does not populate phase-entry metrics).

#### 7. EXPLAIN ANALYZE Performance Check (Deferred from Plan 06)

**Test:** Run `EXPLAIN ANALYZE` on `/api/stats/most-played-openings` for a heavy user (e.g., Adrian's account with 3000+ games). Confirm no Nested Loop hang; query completes in < 2s.
**Expected:** Query plan uses index scans on `game_positions (user_id, phase, ply)` or equivalent; wall clock time < 2s.
**Why human:** Requires production-level data volume and SSH tunnel to production DB or direct DB access. Cannot reproduce with test fixtures.

---

### Gaps Summary

No blockers found. All 12 observable truths verified at code level. The one WARNING (bookmarked openings showing "—" for eval/clock) is documented as an explicit plan decision and reflects a genuine data-pipeline constraint: the bookmark time-series API does not expose phase-entry metrics. Adding that data would require a new backend endpoint — a reasonable Phase 81+ scope item.

The 8 human verification items (board hide, tooltip wording, bullet chart visual, mobile overflow, pill tooltip language, bookmark rendering, performance) are standard pre-merge UAT. The user confirmed they will run visual smoke before opening the PR.

---

*Verified: 2026-05-03T21:40:00Z*
*Verifier: Claude (gsd-verifier)*
