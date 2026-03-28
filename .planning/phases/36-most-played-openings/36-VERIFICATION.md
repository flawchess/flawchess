---
phase: 36-most-played-openings
verified: 2026-03-28T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 36: Most Played Openings Verification Report

**Phase Goal:** Add "Most Played Openings" section to the Opening Statistics subtab showing the user's top 5 openings per color (White/Black) with WDL statistics, backed by a new API endpoint.
**Verified:** 2026-03-28
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                    | Status     | Evidence                                                                                     |
|----|------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | GET /stats/most-played-openings returns top 5 openings per color with WDL stats          | VERIFIED   | Router at `app/routers/stats.py:47`, response_model=MostPlayedOpeningsResponse, 39 tests pass |
| 2  | Openings with fewer than 10 games are excluded from results                              | VERIFIED   | `MIN_GAMES_FOR_OPENING = 10` in service; `.having(func.count() >= min_games)` in repository  |
| 3  | NULL opening_eco/opening_name rows are excluded from aggregation                         | VERIFIED   | `Game.opening_eco.is_not(None)` and `Game.opening_name.is_not(None)` in subquery; dedicated test passes |
| 4  | Response includes opening_eco, opening_name, label (Name (ECO)), and WDL percentages    | VERIFIED   | `OpeningWDL` schema has all fields; label computed as `f"{opening_name} ({opening_eco})"` in service |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact                                    | Expected                                        | Status   | Details                                                         |
|---------------------------------------------|-------------------------------------------------|----------|-----------------------------------------------------------------|
| `app/schemas/stats.py`                      | OpeningWDL and MostPlayedOpeningsResponse       | VERIFIED | Both classes present at lines 41 and 56                         |
| `app/repositories/stats_repository.py`     | query_top_openings_by_color function            | VERIFIED | Defined at line 118, real DB subquery+join, returns live tuples |
| `app/services/stats_service.py`             | get_most_played_openings with named constants   | VERIFIED | MIN_GAMES_FOR_OPENING=10, TOP_OPENINGS_LIMIT=5, function at line 236 |
| `app/routers/stats.py`                      | GET /stats/most-played-openings endpoint        | VERIFIED | Endpoint at line 47, calls service, auth-protected              |
| `tests/test_stats_repository.py`            | Tests for query_top_openings_by_color           | VERIFIED | TestQueryTopOpeningsByColor with 4 test methods, all pass       |
| `tests/test_stats_router.py`                | Tests for GET /stats/most-played-openings       | VERIFIED | TestGetMostPlayedOpenings with 2 test methods, both pass        |
| `frontend/src/types/stats.ts`               | OpeningWDL and MostPlayedOpeningsResponse types | VERIFIED | Interfaces at lines 28 and 41                                   |
| `frontend/src/api/client.ts`                | getMostPlayedOpenings in statsApi               | VERIFIED | getMostPlayedOpenings() at line 101, calls /stats/most-played-openings |
| `frontend/src/hooks/useStats.ts`            | useMostPlayedOpenings hook                      | VERIFIED | Exported function at line 23, queryKey: ['mostPlayedOpenings']  |
| `frontend/src/pages/Openings.tsx`           | Most Played Openings section with testids       | VERIFIED | Section at line 517, data-testid="most-played-openings", mpo-white-section, mpo-black-section |

### Key Link Verification

| From                           | To                              | Via                                    | Status   | Details                                              |
|--------------------------------|---------------------------------|----------------------------------------|----------|------------------------------------------------------|
| `app/routers/stats.py`         | `app/services/stats_service.py` | `stats_service.get_most_played_openings()` | WIRED    | Direct call at router line 53                        |
| `app/services/stats_service.py`| `app/repositories/stats_repository.py` | `query_top_openings_by_color()`  | WIRED    | Called twice (white/black) in service lines 251/258  |
| `frontend/src/hooks/useStats.ts` | `frontend/src/api/client.ts`  | `statsApi.getMostPlayedOpenings()`     | WIRED    | queryFn calls statsApi at hook line 26               |
| `frontend/src/pages/Openings.tsx` | `frontend/src/hooks/useStats.ts` | `useMostPlayedOpenings()`           | WIRED    | Imported and called at Openings.tsx lines 31 and 171 |
| `frontend/src/pages/Openings.tsx` | `WDLChartRow`                 | `<WDLChartRow data={o} ...>`           | WIRED    | Used in both white and black map() at lines 531/553  |

### Data-Flow Trace (Level 4)

| Artifact                              | Data Variable    | Source                                   | Produces Real Data | Status   |
|---------------------------------------|------------------|------------------------------------------|--------------------|----------|
| `frontend/src/pages/Openings.tsx`     | mostPlayedData   | useMostPlayedOpenings() -> statsApi -> /stats/most-played-openings -> DB subquery+join | Yes — SQLAlchemy query against games table | FLOWING |

The repository uses a real subquery (SQLAlchemy `select()` with `.having()`, `.order_by()`, `.limit()`) joined back to fetch individual game rows. The service aggregates these into `OpeningWDL` objects. The hook fetches from the live endpoint. The component renders `o.label`, `o.total`, and passes `o` as `data` to `WDLChartRow`.

No hardcoded empty arrays or static return values found.

### Behavioral Spot-Checks

| Behavior                                      | Command                                                                   | Result       | Status |
|-----------------------------------------------|---------------------------------------------------------------------------|--------------|--------|
| Repository tests pass (4 tests)               | `uv run pytest tests/test_stats_repository.py::TestQueryTopOpeningsByColor -v` | 4 passed | PASS   |
| Router tests pass (2 tests)                   | `uv run pytest tests/test_stats_router.py::TestGetMostPlayedOpenings -v`  | 2 passed     | PASS   |
| Full test suite — no regressions              | `uv run pytest --tb=no -q`                                                | 457 passed   | PASS   |
| Frontend TypeScript build                     | `npm run build`                                                           | 0 errors     | PASS   |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                           | Status    | Evidence                                                                                 |
|-------------|------------|-----------------------------------------------------------------------------------------------------------------------|-----------|------------------------------------------------------------------------------------------|
| MPO-01      | 36-01-PLAN | "Most Played Openings" section with White and Black subsections appears at the top of the Opening Statistics subtab   | SATISFIED | `statisticsContent` starts with the MPO section (line 514); used at desktop (682) and mobile (897) |
| MPO-02      | 36-01-PLAN | Each subsection lists the top 5 openings by game count, based on opening_eco/opening_name from the games table        | SATISFIED | TOP_OPENINGS_LIMIT=5 constant; subquery orders by COUNT DESC LIMIT 5                     |
| MPO-03      | 36-01-PLAN | Openings with fewer than 10 games excluded; if none meet threshold, explanatory message shown                         | SATISFIED | MIN_GAMES_FOR_OPENING=10; HAVING >= min_games; empty state message in JSX at lines 527/549 |
| MPO-04      | 36-01-PLAN | Openings displayed as WDL charts (WDLChartRow) with ECO code in parentheses in the title label                        | SATISFIED | WDLChartRow used with `label={o.label}`; label built as `f"{opening_name} ({opening_eco})"` |

All 4 requirement IDs from the PLAN frontmatter accounted for. No orphaned requirements found in REQUIREMENTS.md for Phase 36.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/Openings.tsx` | 918 | `placeholder="Bookmark label"` | Info | HTML input placeholder attribute — not a code stub, unrelated to this phase |

No blockers or warnings found in phase-modified files.

### Human Verification Required

#### 1. Visual layout and color indicators

**Test:** Log in, import games with at least 10 games of one opening as White or Black, navigate to Opening Statistics subtab.
**Expected:** Most Played Openings section appears at the top of the tab with a charcoal background. White subsection shows a small white circle indicator; Black subsection shows a dark circle. WDLChartRow bars are proportionally sized relative to the top-entry game count.
**Why human:** Visual rendering, color accuracy, and proportion of bar widths cannot be verified statically.

#### 2. Empty state behavior

**Test:** Log in with an account that has no openings exceeding 10 games, navigate to Opening Statistics subtab.
**Expected:** Most Played Openings section is hidden entirely (not rendered). The bookmarks section follows immediately.
**Why human:** Requires a real user account with sparse game data to trigger the `mostPlayedData.white.length === 0 && mostPlayedData.black.length === 0` branch that hides the entire section.

#### 3. Mobile layout

**Test:** Open Opening Statistics subtab on a mobile viewport (or DevTools responsive mode).
**Expected:** Most Played Openings section renders identically to desktop — same charcoal container, White/Black subsections, WDLChartRow components.
**Why human:** `statisticsContent` is shared between desktop and mobile TabsContent, but actual rendering on small screens requires visual inspection.

### Gaps Summary

No gaps. All must-haves verified. All 4 requirement IDs (MPO-01 through MPO-04) are satisfied with implementation evidence.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
