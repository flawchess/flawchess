---
phase: 07-add-more-game-statistics-and-charts
verified: 2026-03-14T10:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 7: Add More Game Statistics and Charts — Verification Report

**Phase Goal:** Extend the application with three statistics pages (Openings, Rating, Global Stats) providing rating-over-time charts per platform/time-control, WDL breakdowns by time control and color, and restructured 5-item navigation — all using existing game data with no schema migration.
**Verified:** 2026-03-14T10:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Navigation shows 5 items: Games, Bookmarks, Openings, Rating, Global Stats | VERIFIED | `App.tsx` NAV_ITEMS array has exactly these 5 entries |
| 2  | Openings page has identical content to the old Stats page | VERIFIED | `Openings.tsx` is a full functional copy of Stats.tsx with renamed exports/testids |
| 3  | /stats route redirects to /openings | VERIFIED | `<Route path="/stats" element={<Navigate to="/openings" replace />} />` in App.tsx line 102 |
| 4  | Rating page shows two per-platform rating-over-time line charts with togglable TC lines | VERIFIED | `Rating.tsx` renders two `<RatingChart>` instances; `RatingChart.tsx` has 4 TC Lines with `hide={hiddenKeys.has(tc)}` and legend-click toggle |
| 5  | Rating page has recency filter only | VERIFIED | `Rating.tsx` has only a recency Select; no other filters present |
| 6  | Global Stats page shows WDL breakdown by time control and color as horizontal stacked bars | VERIFIED | `GlobalStatsCharts.tsx` renders two `WDLCategoryChart` instances (`global-stats-by-tc`, `global-stats-by-color`) using vertical BarChart layout |
| 7  | Global Stats page has recency filter only | VERIFIED | `GlobalStats.tsx` has only a recency Select |
| 8  | GET /stats/rating-history returns per-game rating data points grouped by platform | VERIFIED | `stats_repository.query_rating_history` returns (date, rating, tc_bucket) tuples; service groups into chess_com/lichess; 96 tests pass |
| 9  | GET /stats/global returns WDL counts by time control and by color | VERIFIED | `stats_service.get_global_stats` aggregates via `_aggregate_wdl` helper; returns GlobalStatsResponse |
| 10 | Both endpoints filter by recency when provided | VERIFIED | Both router functions accept `recency: str | None = Query(default=None)` and pass to service which calls `recency_cutoff()` |
| 11 | Both endpoints require authentication | VERIFIED | Both router functions have `Depends(current_active_user)`; test_stats_router confirms 401 without auth |
| 12 | ECO extraction handles chess.com variation URLs gracefully (returns None) | VERIFIED | `TestChesscomEcoExtraction` class in test_normalization.py: 11 test cases covering standard URLs, variation URLs with move notation, None, and empty string |
| 13 | All new nav items have data-testid attributes | VERIFIED | App.tsx line 59: `data-testid={\`nav-${label.toLowerCase().replace(/\s+/g, '-')}\`}` produces nav-games, nav-bookmarks, nav-openings, nav-rating, nav-global-stats |

**Score:** 13/13 truths verified

---

### Required Artifacts

#### Plan 07-01 Artifacts (Backend)

| Artifact | Status | Details |
|----------|--------|---------|
| `app/schemas/stats.py` | VERIFIED | Contains `RatingDataPoint`, `RatingHistoryResponse`, `WDLByCategory`, `GlobalStatsResponse` — all Pydantic v2 BaseModel subclasses |
| `app/repositories/stats_repository.py` | VERIFIED | Exports `query_rating_history`, `query_results_by_time_control`, `query_results_by_color`; uses `cast(func.timezone("UTC", Game.played_at), Date)` |
| `app/services/stats_service.py` | VERIFIED | Exports `get_rating_history`, `get_global_stats`; imports `derive_user_result`, `recency_cutoff` from analysis_service (no duplication) |
| `app/routers/stats.py` | VERIFIED | `router = APIRouter(tags=["stats"])`; two GET endpoints wired to stats_service |
| `tests/test_stats_repository.py` | VERIFIED | 319 lines; 14 integration tests across 3 test classes (TestQueryRatingHistory, TestQueryResultsByTimeControl, TestQueryResultsByColor) |
| `tests/test_stats_router.py` | VERIFIED | 195 lines; 11 HTTP-layer integration tests confirming 401/200/structure/recency behavior |

#### Plan 07-02 Artifacts (Navigation)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/App.tsx` | VERIFIED | NAV_ITEMS has 5 entries; data-testid normalization using `.replace(/\s+/g, '-')`; 5 routes including /stats redirect |
| `frontend/src/pages/Openings.tsx` | VERIFIED | 323 lines; full functional copy of Stats.tsx with `OpeningsPage` export, h1 "Openings", `data-testid="openings-page"`, `data-testid="openings-btn-analyze"` |
| `frontend/src/pages/Rating.tsx` | VERIFIED (full impl) | 59 lines; full Rating page — not a placeholder (upgraded in plan 07-03) |
| `frontend/src/pages/GlobalStats.tsx` | VERIFIED (full impl) | 52 lines; full GlobalStats page — not a placeholder (upgraded in plan 07-03) |

#### Plan 07-03 Artifacts (Frontend Charts)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/types/stats.ts` | VERIFIED | 27 lines; exports `RatingDataPoint`, `RatingHistoryResponse`, `WDLByCategory`, `GlobalStatsResponse` matching backend Pydantic schemas exactly |
| `frontend/src/api/client.ts` | VERIFIED | `statsApi` exported with `getRatingHistory` calling `/stats/rating-history` and `getGlobalStats` calling `/stats/global` |
| `frontend/src/hooks/useStats.ts` | VERIFIED | 19 lines; exports `useRatingHistory` and `useGlobalStats` TanStack Query hooks; 'all' normalized to null before API call |
| `frontend/src/components/stats/RatingChart.tsx` | VERIFIED | 127 lines; ChartContainer + 4 Line components with `hide={hiddenKeys.has(tc)}`, `connectNulls={true}`, legend-click toggle, empty state, data-testid |
| `frontend/src/components/stats/GlobalStatsCharts.tsx` | VERIFIED | 103 lines; local `WDLCategoryChart` (unexported to avoid lint violation); two chart instances with `data-testid="global-stats-by-tc"` and `data-testid="global-stats-by-color"`; empty state per chart |

---

### Key Link Verification

#### Plan 07-01 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `app/routers/stats.py` | `app/services/stats_service.py` | function call | WIRED | Line 12: `from app.services import stats_service`; router calls `stats_service.get_rating_history` and `stats_service.get_global_stats` |
| `app/services/stats_service.py` | `app/repositories/stats_repository.py` | function call | WIRED | Lines 7-11: imports all three query functions; all called in service functions |
| `app/main.py` | `app/routers/stats.py` | `app.include_router` | WIRED | Line 5: `from app.routers.stats import router as stats_router`; line 22: `app.include_router(stats_router)` |

#### Plan 07-02 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `frontend/src/App.tsx` | `frontend/src/pages/Openings.tsx` | Route element | WIRED | Line 99: `<Route path="/openings" element={<OpeningsPage />} />`; import at line 12 |
| `frontend/src/App.tsx` | `frontend/src/pages/Rating.tsx` | Route element | WIRED | Line 100: `<Route path="/rating" element={<RatingPage />} />`; import at line 13 |
| `frontend/src/App.tsx` | `frontend/src/pages/GlobalStats.tsx` | Route element | WIRED | Line 101: `<Route path="/global-stats" element={<GlobalStatsPage />} />`; import at line 14 |

#### Plan 07-03 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `frontend/src/pages/Rating.tsx` | `frontend/src/hooks/useStats.ts` | useRatingHistory hook | WIRED | Line 9 import; line 15 call: `useRatingHistory(recency)` |
| `frontend/src/pages/GlobalStats.tsx` | `frontend/src/hooks/useStats.ts` | useGlobalStats hook | WIRED | Line 9 import; line 15 call: `useGlobalStats(recency)` |
| `frontend/src/hooks/useStats.ts` | `frontend/src/api/client.ts` | statsApi calls | WIRED | Line 2 import; lines 9, 17 calls to `statsApi.getRatingHistory` and `statsApi.getGlobalStats` |
| `frontend/src/api/client.ts` | `GET /stats/rating-history` | axios GET | WIRED | Line 74: `apiClient.get<RatingHistoryResponse>('/stats/rating-history', ...)` |
| `frontend/src/api/client.ts` | `GET /stats/global` | axios GET | WIRED | Line 78: `apiClient.get<GlobalStatsResponse>('/stats/global', ...)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STATS-01 | 07-02 | Navigation restructured from 3 to 5 items | SATISFIED | App.tsx NAV_ITEMS has 5 entries with correct routes and data-testid attributes |
| STATS-02 | 07-02 | Openings page replaces Stats with identical content | SATISFIED | Openings.tsx is a full functional copy of Stats.tsx including all filters, WDLBarChart, WinRateChart, and bookmark integration |
| STATS-03 | 07-03 | Rating page shows per-platform rating-over-time line charts with togglable TC lines and recency filter | SATISFIED | Rating.tsx + RatingChart.tsx: two platform charts, 4 TC lines each with legend toggle, recency Select |
| STATS-04 | 07-03 | Global Stats page shows WDL breakdown by time control and color with recency filter | SATISFIED | GlobalStats.tsx + GlobalStatsCharts.tsx: stacked horizontal bar charts for TC and color categories, recency Select |
| STATS-05 | 07-01 | Backend GET endpoints for rating history and global stats with recency filter and auth | SATISFIED | GET /stats/rating-history and GET /stats/global in stats_router; both auth-gated, recency-filtered, 96 tests passing |
| STATS-06 | 07-01 | ECO extraction test coverage confirms chess.com variation URLs handled correctly | SATISFIED | TestChesscomEcoExtraction class with 11 test cases in test_normalization.py |

**Note on REQUIREMENTS.md:** STATS-01 through STATS-06 are "provisional" requirements defined only in ROADMAP.md Phase 7. They do not appear in REQUIREMENTS.md (which covers only v1 requirements through Phase 4). This is consistent with the ROADMAP.md structure which notes Phase 7 has "6 provisional requirements (STATS-01 through STATS-06)". All 6 are satisfied.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None in phase-7 files | — | — | — |

Scan results:
- No TODO/FIXME/HACK/PLACEHOLDER comments in any phase-7 files
- No stub implementations (`return null`, `return {}`, `return []` only)
- Rating.tsx and GlobalStats.tsx are fully implemented pages (not the placeholders created in plan 07-02)
- `frontend/src/pages/Dashboard.tsx` contains `placeholder="Bookmark label"` — this is an HTML `placeholder` attribute on an input element, unrelated to this phase and not a stub

Dead code note: `frontend/src/pages/Stats.tsx` remains as dead code (noted in SUMMARY and STATE.md). This is an info item, not a blocker — it was intentionally kept per the plan decision.

---

### Human Verification Required

The following items cannot be verified programmatically and should be confirmed manually:

#### 1. Rating Chart Line Toggle Works

**Test:** Open `/rating`, wait for data to load. Click a time control label in the chart legend.
**Expected:** The corresponding line disappears from the chart; clicking again restores it.
**Why human:** Legend-click wiring in Recharts requires browser rendering to verify the `hiddenKeys` state causes actual line hiding.

#### 2. Rating Chart Empty State Per Platform

**Test:** If only chess.com games exist, open `/rating` and observe the Lichess section.
**Expected:** "No Lichess games imported." message appears in place of the chart.
**Why human:** Requires knowing which platforms have data in the real database.

#### 3. WDL Stacked Bars Render Correctly

**Test:** Open `/global-stats` with games in the database. Observe the bar charts.
**Expected:** Horizontal stacked bars show green (wins), grey (draws), red (losses) proportional segments per category label.
**Why human:** Visual correctness of Recharts stacked bar rendering requires a browser.

#### 4. /stats Redirect Works

**Test:** Navigate directly to `http://localhost:5173/stats` in the browser.
**Expected:** Browser URL changes to `/openings` and the Openings page renders.
**Why human:** React Router Navigate behavior needs real browser routing to confirm.

#### 5. Recency Filter Updates Chart Data

**Test:** On `/rating`, change the recency Select from "All time" to "Past month".
**Expected:** Chart data updates to show only games from the past 30 days (line may shorten or disappear).
**Why human:** TanStack Query re-fetch behavior and actual data change requires live API call.

---

### Test Suite Results

**96 tests passed** in `tests/test_stats_repository.py`, `tests/test_stats_router.py`, and `tests/test_normalization.py` (0 failures, 9 deprecation warnings from JWT key length — pre-existing, not introduced by this phase).

**TypeScript:** `npx tsc --noEmit` exits with no errors.

---

## Summary

Phase 7 goal is fully achieved. All three statistics pages (Openings, Rating, Global Stats) exist and are fully wired:

- **Openings** is a functional rename of Stats with all existing bookmark analysis functionality preserved.
- **Rating** has two per-platform Recharts LineCharts with 4 time-control lines each, legend toggle, and recency filter — wired through `useRatingHistory` hook to the verified `GET /stats/rating-history` endpoint.
- **Global Stats** has WDL stacked horizontal bar charts by time control and by color — wired through `useGlobalStats` hook to the verified `GET /stats/global` endpoint.
- Navigation is restructured from 3 to 5 items with correct `data-testid` attributes including hyphen-normalization for "Global Stats".
- Both backend endpoints are auth-gated, recency-filtered, fully tested, and registered in `app.main`.
- ECO extraction test coverage added for chess.com variation URL edge cases.
- No schema migration was required.

---

_Verified: 2026-03-14T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
