---
phase: quick-260613-bst
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/openings.py
  - app/services/openings_service.py
  - tests/test_openings_time_series.py
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
  - CHANGELOG.md
  - .planning/milestones/v1.18-phases/92-custom-date-range-filter/92-CONTEXT.md
autonomous: true
requirements: []

must_haves:
  truths:
    - "Bookmark card WDL bar, game count, and Score % respond to the recency / date filter (totals reflect only in-window games)."
    - "A recency window with zero matching games shows 'No matching games' on the WDL area and '—' for the game count, not frozen full-history numbers."
    - "The rolling time-series chart line is filtered to the recency window but each emitted point's trailing average is warmed up from games BEFORE the window start (the window is not reset to a 1-game count at the boundary)."
    - "A zero-match window yields total_games=0 and last_played_at=None from get_time_series."
    - "D-19 comments/decision record reflect that the time-series path now date-filters emitted points + totals while warming the rolling average from pre-window games."
  artifacts:
    - path: "app/schemas/openings.py"
      provides: "from_date/to_date on TimeSeriesRequest; amended D-19 docstring"
      contains: "from_date"
    - path: "app/services/openings_service.py"
      provides: "get_time_series date-windowed totals + warm-up rolling emission"
    - path: "frontend/src/components/stats/OpeningStatsCard.tsx"
      provides: "total===0 empty state ('No matching games' / '—')"
  key_links:
    - from: "frontend/src/pages/Openings.tsx"
      to: "TimeSeriesRequest.from_date/to_date"
      via: "dateRangeToWireParams(resolveDateRange(debouncedFilters))"
      pattern: "dateRangeToWireParams"
    - from: "app/services/openings_service.py get_time_series"
      to: "TimeSeriesPoint emission"
      via: "emit only points with played_at in [from_date, to_date]; compute totals from same subset"
      pattern: "from_date"
---

<objective>
Fix the Openings → Stats bookmark card so its WDL bar, "N Games" count, and Score % respond to the recency / date filter, while keeping the rolling time-series chart line correctly warmed up from pre-window games.

Root cause: those three values are derived from `POST /openings/time-series`, which intentionally omits date filtering (decision D-19, so the rolling chart had full-history warm-up context). The eval row uses a separately date-filtered endpoint, which is why only it updates today.

The fix date-windows the *emitted* time-series points and the WDL totals while still computing the rolling average over the full chronological history (warm-up preserved). This amends D-19: totals + emitted points are now date-filtered; the trailing average is warmed from games before the window start.

Purpose: bookmark stats must match what the Games tab shows for the same filter (currently the Games tab empties out while the bookmark card stays frozen).
Output: backend schema/service change + tests, frontend wiring + empty state + test, D-19 amendment, CHANGELOG bullet.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/2026-06-13-bookmark-wdl-stats-ignore-recency-filter-in-openings-stats-t.md

# Backend
@app/schemas/openings.py
@app/services/openings_service.py
@app/repositories/openings_repository.py
@tests/test_openings_time_series.py

# Frontend
@frontend/src/types/position_bookmarks.ts
@frontend/src/pages/Openings.tsx
@frontend/src/components/stats/OpeningStatsCard.tsx
@frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
@frontend/src/lib/recency.ts

# D-19 decision record (to amend)
@.planning/milestones/v1.18-phases/92-custom-date-range-filter/92-CONTEXT.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — date-window time-series totals + warm-up rolling emission</name>
  <files>app/schemas/openings.py, app/services/openings_service.py, tests/test_openings_time_series.py, .planning/milestones/v1.18-phases/92-custom-date-range-filter/92-CONTEXT.md</files>
  <behavior>
    Extend tests/test_openings_time_series.py (per-run DB fixtures from tests/conftest.py):
    - Date-windowed totals: a request with from_date/to_date returns total_wins/total_draws/total_losses/total_games and last_played_at computed ONLY from games whose played_at is inside the window. Assert the totals differ from the full-history totals for the same bookmark.
    - Warm-up preserved: with ROLLING_WINDOW_SIZE games before the window start and at least one inside, the first emitted point at/after the window start reports game_count == ROLLING_WINDOW_SIZE (NOT a reset 1-game window). Prove the trailing average reflects pre-window games (e.g. a point whose score could only be produced by counting games before the window).
    - Emitted points are inside the window only: every TimeSeriesPoint.date is >= from_date and <= to_date.
    - Zero-match window: a from_date/to_date range with no games yields total_games == 0, empty data list, and last_played_at is None.
    - Replace/repurpose the existing TestTimeSeriesRequestSchema assertion that forbids date fields: now assert TimeSeriesRequest exposes from_date and to_date (optional, default None) and still has NO `recency` field (D-19 still removed the preset, only the wire date bounds are added).
  </behavior>
  <action>
    Schema (app/schemas/openings.py TimeSeriesRequest): add optional `from_date: datetime.date | None = None` and `to_date: datetime.date | None = None` mirroring OpeningsRequest, plus the same `_check_date_range` model_validator (from_date <= to_date). Update the class docstring: the endpoint now date-filters the EMITTED points and the WDL totals, while the rolling average is warmed up from games before the window start; the full game history is still loaded so trailing averages anchor correctly. Do NOT re-add a `recency` preset field — only the resolved date bounds.

    Service (app/services/openings_service.py get_time_series): do NOT pass from_date/to_date to query_time_series — the repo must keep returning full-history rows for warm-up (do not date-filter in SQL). Iterate the full chronological rows exactly as today, appending to results_so_far and computing the trailing-ROLLING_WINDOW_SIZE window per game (this is the warm-up). Compute the window's TimeSeriesPoint as today. Then gate two things on whether `played_at` falls within [from_date, to_date]: (1) only insert the TimeSeriesPoint into data_by_date when in-window; (2) only increment total_wins/total_draws/total_losses and update last_played_at when in-window. When from_date/to_date are None, treat the bound as open (current behavior — everything counts). Use a small helper predicate `_in_window(played_at, from_date, to_date)` with an explicit `-> bool` return type; compare on date (the request carries datetime.date) — for the upper bound use played_at.date() <= to_date (inclusive day), matching the repo's existing `to_date + 1 day` exclusive-upper convention conceptually. Keep MIN_GAMES_FOR_TIMELINE drop and ROLLING_WINDOW_SIZE unchanged. last_played_at stays None when no in-window game updated it. Update the D-19 docstring block in get_time_series to describe the new windowed-emission + warm-up behavior.

    D-19 record (92-CONTEXT.md): annotate the D-19 bullet (around line 51) with a dated amendment note: the time-series path now accepts from_date/to_date and date-filters emitted points + WDL totals while warming the rolling average from pre-window games — superseding the original "date-filter-free" intent for the totals/points (the recency PRESET stays removed; only resolved date bounds are added). Do not rewrite history; append a clearly marked amendment.

    Follow CLAUDE.md backend rules: explicit return types, Literal/date types, no magic numbers (reuse existing constants), capture nothing new in Sentry (pure compute), em-dash sparingly in docstrings.
  </action>
  <verify>
    <automated>docker compose -f docker-compose.dev.yml -p flawchess-dev up -d >/dev/null 2>&1; uv run pytest tests/test_openings_time_series.py -x && uv run ty check app/ tests/ && uv run ruff check app/ tests/</automated>
  </verify>
  <done>New/updated tests pass: windowed totals, warm-up game_count==ROLLING_WINDOW_SIZE at boundary, in-window-only emitted points, zero-match → total_games=0 / last_played_at=None. ty + ruff clean. D-19 record annotated.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — wire recency into time-series + empty state + CHANGELOG</name>
  <files>frontend/src/types/position_bookmarks.ts, frontend/src/pages/Openings.tsx, frontend/src/components/stats/OpeningStatsCard.tsx, frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx, CHANGELOG.md</files>
  <action>
    Type (frontend/src/types/position_bookmarks.ts TimeSeriesRequest): add optional `from_date?: string` and `to_date?: string`; update the inline comment that currently says "no date filter — D-19: time-series covers full history" to note the path now date-filters totals + emitted points with warm-up.

    Wiring (frontend/src/pages/Openings.tsx ~342-358 timeSeriesRequest useMemo): import `resolveDateRange` and `dateRangeToWireParams` from '@/lib/recency'. Spread `...dateRangeToWireParams(resolveDateRange(debouncedFilters))` into the request object (mirror how the existing useBookmarkPhaseEntryMetrics / Games tab path resolves recency → from_date/to_date). Replace the stale "D-19: recency field removed" comment with a note that recency now flows through as date bounds. wdlStatsMap derives from tsData automatically, so no change there. Confirm `debouncedFilters` is a FilterState compatible with resolveDateRange (it carries `recency` + `customRange`).

    Empty state (frontend/src/components/stats/OpeningStatsCard.tsx): when `opening.total === 0`, render an empty WDL area showing "No matching games" instead of the WDLChartRow, and in linksRow show "—" instead of the `{opening.total}` games count (the Moves link stays). Apply to BOTH the mobile and desktop blocks (they share `wdlLine` and `linksRow` constants, so changing those constants covers both — verify both render paths use them). Use theme constants for muted text (text-muted-foreground), keep text-sm floor, keep data-testid attributes (add `data-testid={\`${cardTestId}-empty\`}` on the empty WDL element; keep `${cardTestId}-games` on the count). Em dash for the count per the locked decision. Note: this card is shared with Most Played Openings, but those rows drop out before reaching total===0, so the branch is bookmark-only in practice — guard purely on `opening.total === 0`.

    Test (OpeningStatsCard.test.tsx): add a test rendering an opening with total: 0 (wins/draws/losses 0) and assert the WDL empty state ("No matching games") is shown and the games count renders "—" (e.g. query `${cardTestId}-games` text contains "—", not "0").

    CHANGELOG.md: add one terse user-facing bullet under `## [Unreleased]` → `### Fixed`: bookmark WDL bar, game count, and Score % in Openings → Stats now respect the recency / date filter (and show an empty state when no games match). Keep tone terse, em-dash sparingly.

    Follow CLAUDE.md frontend rules: no text-xs, theme constants, data-testid on interactive/empty elements, semantic HTML, mobile + desktop parity. No prettier (ESLint only).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run src/components/stats/__tests__/OpeningStatsCard.test.tsx</automated>
  </verify>
  <done>timeSeriesRequest carries from_date/to_date from the active recency window; bookmark card shows "No matching games" + "—" when total===0 on both mobile and desktop; OpeningStatsCard test covers the empty state; lint + targeted test pass; CHANGELOG Fixed bullet added.</done>
</task>

</tasks>

<verification>
Full pre-merge gate (run at integration, not necessarily inside this plan):
- uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix
- uv run ty check app/ tests/  (zero errors)
- uv run pytest -n auto -x
- ( cd frontend && npm run lint && npm test -- --run )

Manual UAT (dev DB, existing data — no DB reset): bookmark a position in Openings, switch to the Stats tab, change recency to a narrow window (e.g. "1 month"); the WDL bar / N Games / Score % must change with it, the chart line must shorten to the window while still showing a smooth trailing average at the window start (not a reset-from-1 spike), and a window with no matching games must show "No matching games" + "—".
</verification>

<success_criteria>
- Bookmark card WDL bar, game count, and Score % reflect only in-window games for any recency / date filter.
- Zero-match window shows "No matching games" + "—" (em dash) instead of frozen full-history numbers.
- Rolling chart line is date-windowed but warmed up from pre-window games (boundary point game_count == ROLLING_WINDOW_SIZE).
- get_time_series returns total_games=0 / last_played_at=None for an empty window; emitted points all fall inside the window.
- D-19 record + comments amended; CHANGELOG Fixed bullet added.
- ty, ruff, frontend lint, and all touched tests pass.
</success_criteria>

<output>
Create `.planning/quick/260613-bst-bookmark-wdl-stats-respect-recency-date-/260613-bst-SUMMARY.md` when done.
</output>
