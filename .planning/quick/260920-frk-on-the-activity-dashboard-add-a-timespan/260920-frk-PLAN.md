---
quick_id: 260920-frk
slug: activity-dashboard-timespan-selector
date: 2026-09-20
phase: quick-260920-frk
plan: 01
type: execute
wave: 1
depends_on: []
mode: inline-sequential
autonomous: true
requirements: [FRK-01, FRK-02, FRK-03, FRK-04, FRK-05]
files_modified:
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - app/routers/admin_activity.py
  - tests/test_admin_activity_stats.py
  - frontend/src/pages/activity/ActivityPage.tsx
  - frontend/src/pages/activity/styles.css
  - frontend/src/types/activity.ts
  - CHANGELOG.md

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "GET /api/admin/activity/stats?start=A&end=B returns a payload whose window begins on A (clamped up to data_start) and whose days end on B."
    - "start == end analyses exactly that one day, and that day may be today: the payload still carries a day entry for today and a non-negative last_complete_index."
    - "Every one of the 17 fetch_* queries stops at the selected end date — no card silently reports rows dated after it."
    - "start > end, end > today, or only one of the two supplied is rejected with 422 (never a 500, never silently coerced)."
    - "Two different custom windows are cached independently, and a custom request never evicts a preset entry inside the TTL."
    - "The four preset buttons (all/d90/d30/d7) behave exactly as before when no start/end is sent."
  artifacts:
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - app/routers/admin_activity.py
    - tests/test_admin_activity_stats.py
    - frontend/src/pages/activity/ActivityPage.tsx
    - frontend/src/pages/activity/styles.css
    - frontend/src/types/activity.ts
  key_links:
    - "admin_activity.activity_stats -> WindowRequest -> StatsCache.get: the cache key must carry the dates, not just the preset key."
    - "resolve_window -> ResolvedWindow.window_end -> every fetch_* upper bound: a query that does not receive window_end is a silently wrong card."
    - "ActivityPage TanStack query key -> /admin/activity/stats params: the custom dates must be in the key or switching windows serves a stale payload."
---

<objective>
Add an explicit start/end timespan selector to the superuser Activity Pulse dashboard, alongside the four existing range presets. Selecting a single day (start == end) analyses exactly that day, and today is selectable.

Purpose: the presets only answer "the last N days ending now". The operator needs to read a specific historical window (a launch day, a deploy week, yesterday) and to look at today on its own.
Output: `start`/`end` query params on `GET /api/admin/activity/stats`, an inclusive upper bound on all 17 dashboard queries, a window-keyed cache, and two date inputs plus an Apply button in the dashboard's controls row.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md

**Execution mode: inline, sequential, on the main working tree.** No worktree isolation, no branch creation — `main` is the current branch and stays the current branch. One commit per task, in order (Task 1 → 2 → 3).
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@app/routers/admin_activity.py
@app/services/activity_stats.py
@app/services/activity_queries.py
@tests/test_admin_activity_stats.py
@frontend/src/pages/activity/ActivityPage.tsx
@frontend/src/types/activity.ts

Verified facts about the current code (read at planning time, 2026-09-20, clean tree on `main`):

- `RangeKey = Literal["all", "d90", "d30", "d7"]` and `RANGE_WINDOW_DAYS` live in `app/services/activity_queries.py`. `resolve_window(range_key, now_utc, data_start, data_end)` derives `window_start` with `min(max(raw_cutoff, data_start), data_end)`, builds `days` from `lead_in_start` to `data_end`, and sets `last_complete_index = len(days) - (2 if data_end >= today and len(days) > 1 else 1)`.
- `ResolvedWindow` is a `NamedTuple` with `range_key, data_start, lead_in_start, window_start, days, window_start_index, last_complete_index`. It has no end field today — the end is implicitly `data_end`.
- `build_payload(engine, range_key, now_utc)` calls `fetch_window` then 17 `fetch_*` helpers; each takes `window_start` (two take `lead_in_start`) and no upper bound.
- `StatsCache._entries` is keyed by `RangeKey` alone and is uncapped in size (4 possible keys today).
- Three monkeypatched fakes in `tests/test_admin_activity_stats.py` (around lines 241, 347, 389) have the signature `fake_build_payload(_engine, _range_key, _now_utc)` — changing `build_payload`'s arity breaks them.
- `render.js` reads `D.window_start_index`, `D.last_complete_index`, `D.data_start` and `DAYS`; it never reads `payload.range`. `renderActivesCard` computes `last = Math.max(0, D.last_complete_index - D.window_start_index)`, so a window whose only visible day is today already resolves to index 0.
- Baseline is green: `uv run ruff check .`, `uv run ty check app/ tests/ scripts/` and `npm run check:activity-layout` all pass right now. Any failure in those commands after a task is caused by that task.
- `frontend/src/components/filters/CustomRangePopover.tsx` exists but is not reusable here: it renders only a `PopoverContent` body, is driven by `FilterPanel`'s pending-state commit semantics and a `PopoverAnchor` that FilterPanel owns, and is styled by the app's Tailwind design system. The dashboard is a self-contained page whose every rule is scoped under `.activity-dash` in its own `styles.css` with its own Google font stack (which `frontend/scripts/check-activity-layout.mjs` calibrates against). Native `<input type="date">` styled in that same `styles.css` is the smaller and visually consistent choice.
</context>

<assumption_delta_decision>
Noun: the dashboard's time window.
Decision: **add-alongside** (not promote).
Rationale: the window moves from "one of four preset keys" to "a preset key OR a chosen (start, end) pair". The presets are not replaced — they stay as one-click shortcuts and remain the default (`range=all` when no dates are sent), so every existing caller, test and cached entry keeps its current meaning. Concretely, `RangeKey` stays the four presets (so `?range=custom` is still a 422) and a separate `SelectedRange` Literal carries the extra `"custom"` value that the payload reports back.
</assumption_delta_decision>

<source_audit>
| # | Source | Item | Covered by |
|---|--------|------|-----------|
| FRK-01 | USER | Start + end date selector on the activity dashboard | Task 1 (API), Task 3 (UI) |
| FRK-02 | USER | A single day (start == end) analyses just that day | Task 1 (window resolution), Task 2 (test) |
| FRK-03 | USER | Today is selectable as start and/or end | Task 1 (`last_complete_index`, no clamp to `data_end`), Task 2 (test) |
| FRK-04 | ORCH | Every `fetch_*` query gets a real upper bound; none silently ignores the end | Task 1 (all 17, table in the action) |
| FRK-05 | ORCH | `StatsCache` keys on the resolved window, not the range key | Task 1 (`WindowRequest` cache key) |
| FRK-06 | ORCH | Validate start <= end, end <= today, start >= data_start | Task 1 (422 for the first two, clamp for the third), Task 2 (tests) |
| FRK-07 | ORCH | Keep preset shortcuts; reuse a date picker if one fits, else native inputs | Task 3 (presets kept, native inputs — rejection rationale in `<context>`) |
| FRK-08 | ORCH | Tests: start/end, single-day, today-only, validation failure | Task 1 (end-to-end truncation), Task 2 (the rest) |
| FRK-09 | ORCH | Threat model with ASVS L1 input validation on the new params | `<threat_model>` below |

No item is MISSING. No package installs are introduced, so the package-legitimacy gate does not apply (no new dependency in `pyproject.toml` or `frontend/package.json`).
</source_audit>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Custom window end-to-end — request params, window resolution, upper bound on all 17 queries</name>
  <files>app/services/activity_queries.py, app/services/activity_stats.py, app/routers/admin_activity.py, tests/test_admin_activity_stats.py</files>
  <precondition>The dev PostgreSQL container is running (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`); the pytest session clones its database from the migrated template and will fail to collect without it.</precondition>
  <behavior>
    Write this end-to-end test FIRST in `tests/test_admin_activity_stats.py` and watch it fail before touching the implementation:
    - `test_stats_custom_window_truncates_at_end_date`: as a superuser, after `touch_user_activity`, request `/api/admin/activity/stats` with `start` = today minus 3 days and `end` = today minus 1 day. Assert 200; assert `body["range"] == "custom"`; assert `body["days"][-1]` equals the `end` date; assert no row in `body["signups"]` carries today's date (the superuser this test just registered is dated today and must fall outside the window). Use a membership/absence assertion, never an absolute count — the test database is shared within a session and other tests seed users.
    Both assertions fail today for different reasons (422 on the unknown params, then an unbounded query) — that is the RED state to confirm.
  </behavior>
  <action>
In `app/services/activity_queries.py`:

1. Keep `RangeKey` as the four presets and add `SelectedRange = Literal["all", "d90", "d30", "d7", "custom"]` next to it, documented as "what the payload reports back — the four presets plus the explicit-range case". Update the stale comment above `RangeKey` (it currently promises "no custom range ... exactly these four, ever") to say that the four presets are the only preset keys and that an explicit `start`/`end` pair reports as `custom`. Retype `Payload["range"]` and `ResolvedWindow.range_key` as `SelectedRange`.

2. Add a hashable request object so the window a caller asked for can be threaded through and used as a cache key:
   `class WindowRequest(NamedTuple)` with fields `range_key: RangeKey = "all"`, `start: datetime.date | None = None`, `end: datetime.date | None = None`. Docstring: a preset key, or an explicit inclusive date range; both `start` and `end` are set together or not at all (the router enforces that).

3. Add `window_end: datetime.date` to `ResolvedWindow` (the inclusive last day of the selected window) and extend `resolve_window` with two keyword parameters defaulting to `None`: `custom_start` and `custom_end`. Every existing positional call site and test stays valid. New body shape, keeping the existing clamp comments and extending them:
   - When both custom dates are given: `selected_key = "custom"`, `window_end = custom_end`, `raw_cutoff = custom_start`.
   - Otherwise: `selected_key = range_key`, `window_end = data_end`, and `raw_cutoff` as today.
   - `window_start = min(max(raw_cutoff, data_start), window_end)` — the identical two-sided clamp as before, with `window_end` replacing the hard-coded `data_end`, so preset behaviour is byte-identical.
   - `lead_in_start = min(max(window_start - ROLLING_LEAD_IN_DAYS, data_start), window_start)`. The outer `min` is new and is a guard, not cosmetics: a custom window that ends before `data_start` would otherwise produce `lead_in_start > window_start`, an empty `days` list and an out-of-range `window_start_index` that crashes the page. For every preset it is a no-op.
   - `days` runs from `lead_in_start` to `window_end` inclusive.
   - `last_complete_index = len(days) - (2 if window_end >= today and len(days) > 1 else 1)` — the same expression with `window_end` replacing `data_end`. Add a comment recording why a today-only window is still safe: `days` then has the 30-day lead-in in front of today, so this index points at yesterday, and `render.js`'s `Math.max(0, last_complete_index - window_start_index)` resolves the single visible day to index 0.

4. Add `_ALL_TIME_END: Final[datetime.date] = datetime.date(9999, 12, 31)` with a comment that `fetch_train_funnel`'s control line is deliberately unbounded, and a module-level helper `_end_exclusive(window_end: datetime.date) -> datetime.date` returning `window_end + one day`. Document why exclusive: the bounded columns are a mix of `date` (`activity_date`, `session_date`) and timestamp (`created_at`, `played_at`, `solved_at`, `started_at`), and `< CAST(:last AS date)` against the day AFTER the selected end is the single predicate form that is correct for both, where `<= :end` would drop every timestamped row after midnight on the end date.

5. Change `fetch_window(conn, request: WindowRequest, now_utc)` to read `data_start`/`data_end` as it does now and call `resolve_window(request.range_key, now_utc, data_start, data_end, custom_start=request.start, custom_end=request.end)`.

6. Give every `fetch_*` helper a `window_end: datetime.date` parameter (positional, after its existing date parameters), bind `last=_end_exclusive(window_end)` and add `AND <column> < CAST(:last AS date)` to the WHERE clause named below. Work through this table and change exactly these predicates — a helper left without an upper bound is a card that silently reports rows after the selected end:

   | Helper | Bounded column |
   |---|---|
   | `fetch_activity` | `a.activity_date` (the `first_seen` CTE stays unfiltered — it is a global fact) |
   | `fetch_signups` | `created_at` |
   | `fetch_bot_games` | `g.played_at` |
   | `fetch_bot_players` | `g.played_at` |
   | `fetch_train` | `session_date` |
   | `fetch_train_funnel` | `session_date` inside the `cohort` CTE |
   | `fetch_solves` | `solved_at` |
   | `fetch_imports` | `started_at` |
   | `fetch_persona` | `g.played_at` |
   | `fetch_elo` | `g.played_at` |
   | `fetch_funnel` | `u.created_at` in the `u` CTE |
   | `fetch_purged_excluded` | `u.created_at` |
   | `fetch_time_to_import` | `created_at` in the `u` CTE |
   | `fetch_stickiness` | `created_at` in the `u` CTE |
   | `fetch_conversion` | `created_at` in the `u` CTE |
   | `fetch_guest_train` | `u.created_at` |
   | `fetch_conversion_compare` | `u.created_at` in the `u` CTE |

   For `fetch_train_funnel`, the windowed run binds the real exclusive end and the all-time control run binds `_ALL_TIME_END`, so the control line keeps meaning all time.

   For the six cohort helpers (`fetch_funnel`, `fetch_purged_excluded`, `fetch_time_to_import`, `fetch_stickiness`, `fetch_conversion`, `fetch_conversion_compare`) bound the ENTRY predicate only. Their joined `games` / `user_activity` / `bot_game_settings` CTEs stay unfiltered, exactly as their existing docstrings instruct: a cohort that entered inside the window is still followed forward to today. Extend each of those docstrings' windowing note to say the entry predicate is now bounded on both sides while the follow-forward join is deliberately not.

In `app/services/activity_stats.py`:

7. Change `build_payload(engine, request: WindowRequest, now_utc)` — arity unchanged, second parameter retyped. Resolve the window once, then pass `window.window_end` to every `fetch_*` call.

8. Rekey `StatsCache._entries` to `dict[queries.WindowRequest, tuple[queries.Payload, float]]` and change `get(self, request: WindowRequest, *, now_utc, force=False)`. Update the class docstring: it serves one payload per requested window, not per range key. Add `_MAX_ENTRIES: Final[int] = 16` and, after inserting a fresh entry, drop the oldest entries by their stored timestamp until the dict is within the cap. The cap exists because the key space is no longer four values but every date pair a caller can name; without it a long session grows one full dashboard payload per distinct window, unbounded.

In `app/routers/admin_activity.py`:

9. Add two optional query parameters to `activity_stats`: `start: Annotated[datetime.date | None, Query()] = None` and `end: Annotated[datetime.date | None, Query()] = None`. FastAPI parses ISO dates and rejects malformed input with its own 422 before the handler body runs.

10. Add a module-level helper `_build_window_request(range_key, start, end, today) -> queries.WindowRequest` so the handler body stays short. It returns `WindowRequest(range_key=range_key)` when both dates are `None`, and otherwise raises `HTTPException(422, detail=...)` for: only one of the two supplied ("start and end must be given together"), `start > end`, and `end > today`. A `start` before the dataset begins is NOT an error — `resolve_window` clamps it up to `data_start`, which is the existing preset behaviour for a window wider than the data. The handler takes `today` from the injected `now_utc.date()`, never an inline clock read.

11. Call the helper, pass the resulting request to `cache.get(...)`, and extend the handler docstring's existing note about `range` validation: these 422s are expected validation failures too and are deliberately not captured to Sentry.

12. Update the three `fake_build_payload` monkeypatch fakes in `tests/test_admin_activity_stats.py` to the new second parameter (`request`), reading `request.range_key` where they currently read the range key, and retype `fake_payload`'s parameter as `queries.SelectedRange`. These are signature-follow edits; leave each test's assertions alone.
  </action>
  <verify>
    <automated>uv run pytest tests/test_admin_activity_stats.py -x</automated>
    <automated>uv run ty check app/ tests/ scripts/</automated>
    <automated>uv run ruff check . &amp;&amp; uv run ruff format --check app/ tests/</automated>
    <automated>uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200</automated>
  </verify>
  <done>`GET /api/admin/activity/stats?start=A&amp;end=B` returns 200 with `range == "custom"`, `days` ending on B, and no signup row dated after B. All pre-existing tests in the file still pass unchanged, and `?range=d30` / no-param requests produce the same window they did before. ty, ruff, and the function-size gate are clean.</done>
</task>

<task type="auto">
  <name>Task 2: Coverage for the single-day, today, validation and cache-keying cases</name>
  <files>tests/test_admin_activity_stats.py</files>
  <action>
Extend `tests/test_admin_activity_stats.py`. Put the pure-function cases in the existing `resolve_window` section and the endpoint cases after the existing range tests, following the file's own conventions (self-contained seeding, `make_superuser` + `touch_user_activity`, `cache_override` where a fake cache is needed).

Pure `resolve_window` cases (no DB):
- Explicit start/end: window starts on the given start, `window_end` is the given end, `days[-1]` is the end, `days[window_start_index]` is the start, and `range_key == "custom"`.
- Single day, mid-dataset: `custom_start == custom_end == some past day` gives exactly one visible day (`len(days) - window_start_index == 1`) and `last_complete_index >= window_start_index` is false only in the today case — assert here that the single visible day is complete.
- Today only: `custom_start == custom_end == today` where `data_end` is YESTERDAY (the realistic case — `user_activity` has no row for today yet). Assert `days[-1]` is today, `0 <= window_start_index <= len(days) - 1`, and `last_complete_index >= 0`. This is the regression guard for "selecting today must be possible".
- Start before `data_start`: clamped up to `data_start`, `window_start_index == 0`.
- A window entirely before `data_start`: `days` is non-empty and `0 <= window_start_index <= len(days) - 1` (the `lead_in_start` guard from Task 1 — without it this raises or renders an empty page).
- Preset regression: with `custom_start`/`custom_end` omitted, `window_end == data_end` for every `RangeKey` value.

Endpoint cases (real app, superuser token):
- Single past day: `start == end == yesterday` returns 200 and a payload whose `days[-1]` is yesterday.
- Today only: `start == end == today` returns 200, `days[-1]` is today, and `body["signups"]` contains a row dated today (the superuser registered by the test itself) — proving today's data is analysed rather than dropped as incomplete.
- Validation: `start` after `end` → 422; `end` after today → 422; `start` without `end` → 422; `end` without `start` → 422; a malformed date such as `start=not-a-date` → 422. Assert the status code only, never a message string.
- Still 422, not 500, is the point of the malformed case — assert `resp.status_code == 422` and that the body is JSON.
- Cache keying: with a `cache_override` and a counting `fake_build_payload`, two requests for the same custom window build once, a third request for a DIFFERENT custom window builds again, and a fourth request for `?range=d30` builds again — three builds total, proving windows are cached independently of each other and of the presets.
- `?range=custom` is still rejected with 422 (the `RangeKey` Literal is unchanged; `"custom"` is an output value only).

Derive dates in the tests from a single `datetime.datetime.now(datetime.timezone.utc).date()` local, not from literals, so the suite does not rot; the endpoint reads the real clock through `dev_now_utc` in the test environment.
  </action>
  <verify>
    <automated>uv run pytest tests/test_admin_activity_stats.py -x</automated>
    <automated>uv run ty check app/ tests/ scripts/</automated>
    <automated>uv run ruff check . &amp;&amp; uv run ruff format --check app/ tests/</automated>
  </verify>
  <done>The new cases cover single-day, today-only, all five validation rejections, the window-independent cache, and the `lead_in_start` guard. The whole file passes.</done>
</task>

<task type="auto">
  <name>Task 3: Date inputs and Apply on the dashboard controls row</name>
  <files>frontend/src/pages/activity/ActivityPage.tsx, frontend/src/pages/activity/styles.css, frontend/src/types/activity.ts, CHANGELOG.md</files>
  <action>
In `frontend/src/types/activity.ts`: keep `ActivityRangeKey` as the four presets, add `export type ActivitySelectedRange = ActivityRangeKey | 'custom';`, retype `ActivityStatsPayload["range"]` to it, and correct the comment above `ActivityRangeKey` the same way Task 1 corrected its Python mirror (four presets, plus `custom` reported back for an explicit date range). Do not otherwise touch this file.

In `frontend/src/pages/activity/ActivityPage.tsx`:
- Add a module-level `todayIso()` helper returning the local date as `YYYY-MM-DD` (build it from `getFullYear`/`getMonth`/`getDate` and pad — `toISOString` would shift the date across UTC midnight for anyone west of Greenwich).
- Add three state values: `startDate` and `endDate`, both initialised to `todayIso()`, and `applied: { start: string; end: string } | null` initialised to `null`. Starting the inputs on today means the user's single most likely request — analyse today — is one click.
- Extend `fetchActivityStats` to take the applied window and send `{ start, end }` when it is set and `{ range }` when it is not, keeping the existing `refresh: 1` merge in both branches.
- Extend the TanStack query key to `['activity-stats', range, applied?.start ?? '', applied?.end ?? '']` so each window gets its own cache entry; `staleTime: Infinity` and the no-poll settings stay as they are.
- Apply handler: set `applied` to the two input values. Preset handler: set the range AND clear `applied` to `null`, so clicking a preset always returns to preset mode.
- Preset `aria-pressed` becomes `applied === null && range === '<key>'`, so no preset reads as active while a custom window is showing.
- Render the two inputs and the Apply button inside the existing time-range `.controls` row, after the preset `.seg`, in their own `.seg` group with `role="group"` and `aria-label="Custom date range"`. Both are `<input type="date">` with `max={todayIso()}`, `aria-label="Range start date"` / `"Range end date"`, `data-testid="filter-range-start"` / `"filter-range-end"`, and `disabled={isFetching}`. The Apply button carries `data-testid="btn-apply-range"`, is `type="button"`, and is disabled when `isFetching` or `startDate > endDate` (ISO strings compare correctly as strings — no date parsing needed). Update the row's `.hint` copy to mention that a single day is selected by setting both dates the same. The header already renders the resolved window into `#w-range` from the payload, so no extra status text is needed.
- Keep the component under the gated complexity/`max-statements` limits: this is three state values, two handlers and JSX. Do not restructure the existing render or the audience row.

In `frontend/src/pages/activity/styles.css`: add rules under `.activity-dash` for `.seg input[type="date"]` (inherit the page font at `.9375rem`, `var(--ink)` on `var(--surface)`, `1px solid var(--rule)`, pill radius, the same `7px 10px` padding the seg buttons use) and a `:focus-visible` outline matching the existing `.seg button:focus-visible` rule. Keep every selector scoped under `.activity-dash` — an unscoped `input[type=date]` rule would restyle the whole SPA. Mirror the existing narrow-viewport overrides so the row still wraps rather than overflowing on a 320px screen.

In `CHANGELOG.md`: add one bullet under `## [Unreleased]` describing the new start/end selector on the Activity Pulse dashboard, single-day and today included, tagged `(quick 260920-frk)`. Create the `## [Unreleased]` section only if it is absent; do not touch released sections.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run lint</automated>
    <automated>cd frontend &amp;&amp; npm run build</automated>
    <automated>cd frontend &amp;&amp; npm test -- --run src/pages/activity</automated>
    <automated>cd frontend &amp;&amp; npm run check:activity-layout</automated>
    <automated>cd frontend &amp;&amp; npm run knip</automated>
  </verify>
  <done>The dashboard's time-range row shows the four presets plus a start date, an end date and an Apply button. Applying a window refetches with `start`/`end`, clicking a preset returns to preset mode, and no preset shows as pressed while a custom window is applied. Lint, the TypeScript build, the existing activity tests, the layout harness and knip all pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → `GET /api/admin/activity/stats` | Superuser-authenticated HTTP; the new `start`/`end` query params are untrusted input crossing into date arithmetic and SQL bind parameters. |
| FastAPI service → read-only Postgres engine | Every statement runs under `default_transaction_read_only`; the connection is opened by `build_readonly_engine`. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-frk-01 | Tampering | `start`/`end` → `activity_queries` SQL | high | mitigate | Params are typed `datetime.date`, so FastAPI rejects anything that is not an ISO date with 422 before the handler runs; they reach SQL only as named bind parameters (`:first`, `:last`) through `text()`. The f-string SQL in this module interpolates module-level constants (`_GUEST_COHORT`, `_PROMOTED_GUEST`) only — Task 1 must not interpolate request input into any query string. |
| T-frk-02 | Denial of Service | `StatsCache._entries` | medium | mitigate | The key space grows from four preset keys to every date pair a caller can name. `_MAX_ENTRIES = 16` with oldest-first eviction bounds resident payloads (Task 1, step 8). |
| T-frk-03 | Denial of Service | window width → 17 aggregate queries + `days` array | medium | mitigate | `window_start` is clamped up to `data_start` and `end` after today is a 422, so the widest reachable window is the dataset span plus the 29-day lead-in — the same ceiling the `all` preset already has. The 300s `StatsCache` TTL still bounds repeat load. |
| T-frk-04 | Elevation of Privilege | `/admin/activity/stats` | high | mitigate | The new params sit behind the unchanged `Depends(current_superuser)`; `test_stats_requires_authentication`, `test_stats_requires_superuser` and `test_stats_rejects_impersonation_token` must stay green in Task 1's verify. |
| T-frk-05 | Information Disclosure | error path for invalid dates | low | mitigate | Rejections are 422 with a static detail string (no echo of internals, no variable data in the message per the Sentry grouping rule) and are deliberately not captured to Sentry — they are expected validation failures, matching the existing comment about an unrecognised `range`. |
| T-frk-06 | Repudiation | — | low | accept | The endpoint is read-only and superuser-only; no state changes, so there is nothing to repudiate. No audit logging added. |

No package-manager install is introduced by this plan, so no supply-chain (`T-*-SC`) row applies.
</threat_model>

<verification>
- `uv run pytest tests/test_admin_activity_stats.py -x` — the full file, including every pre-existing preset/cache/auth test.
- `uv run ty check app/ tests/ scripts/` and `uv run ruff check . && uv run ruff format --check app/ tests/` — both are green at baseline, so any error is from this work.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200`.
- `cd frontend && npm run lint && npm run build && npm test -- --run src/pages/activity && npm run check:activity-layout && npm run knip`.
- Manual (operator, not gating): open `/activity` as a superuser, set both dates to today, Apply, and confirm the header window reads today and the DAU tile is today's number; then set a past week and confirm the charts stop at the chosen end date.
</verification>

<success_criteria>
- An explicit `start`/`end` pair produces a window that begins on the start date (clamped up to `data_start`) and ends on the end date, with `range == "custom"` echoed back.
- `start == end` analyses exactly that one day, and today is a valid value for either bound.
- All 17 `fetch_*` helpers carry an inclusive upper bound; the six cohort helpers bound their entry predicate while keeping their documented follow-forward joins unfiltered.
- `start > end`, `end > today`, one-of-two, and malformed dates each return 422.
- Custom windows are cached independently of each other and of the four presets, under a bounded number of entries.
- The four preset buttons and every existing test behave exactly as before.
</success_criteria>

<output>
Create `.planning/quick/260920-frk-on-the-activity-dashboard-add-a-timespan/260920-frk-SUMMARY.md` when done.
</output>
