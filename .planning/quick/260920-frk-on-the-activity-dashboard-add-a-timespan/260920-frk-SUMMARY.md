---
phase: quick-260920-frk
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, postgres, react, tanstack-query, activity-dashboard]

requires: []
provides:
  - "GET /api/admin/activity/stats accepts an explicit start/end date pair alongside the four range presets"
  - "queries.WindowRequest / queries.SelectedRange / ResolvedWindow.window_end -- the window-resolution primitives a future custom-range feature elsewhere would reuse"
affects: []

actuals:
  tokens: 19322
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Exclusive upper bound via _end_exclusive(window_end) + `< CAST(:last AS date)`, correct for both date and timestamp columns"
    - "StatsCache keyed on a hashable WindowRequest NamedTuple (not a bare RangeKey string) with oldest-first eviction bounding the key space"

key-files:
  created: []
  modified:
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - app/routers/admin_activity.py
    - tests/test_admin_activity_stats.py
    - frontend/src/pages/activity/ActivityPage.tsx
    - frontend/src/pages/activity/styles.css
    - frontend/src/types/activity.ts
    - CHANGELOG.md

key-decisions:
  - "add-alongside, not promote: RangeKey stays the four presets; SelectedRange adds the output-only 'custom' value. ?range=custom is still a 422 -- only an explicit start/end pair produces range=='custom' in the response."
  - "Native <input type=\"date\"> inside the dashboard's own .seg pill, not the app's CustomRangePopover -- the popover is coupled to FilterPanel's pending-state commit semantics and the Tailwind design system; the dashboard is a self-contained page with its own font stack that check-activity-layout.mjs calibrates against."
  - "lead_in_start is now also clamped down to window_start (min, not just max against data_start) -- without this guard a custom window ending before data_start produces an empty days list and an out-of-range index."

requirements-completed: [FRK-01, FRK-02, FRK-03, FRK-04, FRK-05, FRK-06, FRK-07, FRK-08, FRK-09]

coverage:
  - id: D1
    description: "GET /api/admin/activity/stats?start=A&end=B returns a payload whose window begins on A (clamped up to data_start) and whose days end on B, echoing range=='custom'."
    requirement: "FRK-01"
    verification:
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_window_truncates_at_end_date"
        status: pass
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_resolve_window_custom_start_end_reports_custom"
        status: pass
    human_judgment: false
  - id: D2
    description: "start == end analyses exactly that one day, and today is a valid value for either bound."
    requirement: "FRK-02"
    verification:
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_resolve_window_custom_single_day_mid_dataset_is_complete"
        status: pass
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_resolve_window_custom_today_only_is_selectable"
        status: pass
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_today_only_includes_todays_signup"
        status: pass
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_single_past_day"
        status: pass
    human_judgment: false
  - id: D3
    description: "All 17 fetch_* queries carry an inclusive upper bound; the six cohort helpers bound their entry predicate only, keeping their documented follow-forward joins unfiltered."
    requirement: "FRK-04"
    verification:
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_window_truncates_at_end_date"
        status: pass
      - kind: unit
        ref: "tests/test_admin_activity_stats.py -x (full file, incl. pre-existing fetch_* pins)"
        status: pass
    human_judgment: false
  - id: D4
    description: "start > end, end > today, one-of-two, and a malformed date each return 422, never a 5xx and never silently coerced."
    requirement: "FRK-06"
    verification:
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_window_validation_rejections"
        status: pass
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_range_literal_still_rejected"
        status: pass
    human_judgment: false
  - id: D5
    description: "Custom windows are cached independently of each other and of the four presets, bounded to 16 resident entries."
    requirement: "FRK-05"
    verification:
      - kind: integration
        ref: "tests/test_admin_activity_stats.py#test_stats_custom_window_cached_independently_of_presets"
        status: pass
    human_judgment: false
  - id: D6
    description: "The dashboard's controls row shows a start date, end date, and Apply button alongside the four presets; applying refetches with start/end (its own query-cache entry), clicking a preset returns to preset mode, and no preset reads as pressed while a custom window is applied."
    requirement: "FRK-01"
    verification:
      - kind: unit
        ref: "cd frontend && npm test -- --run src/pages/activity"
        status: pass
      - kind: other
        ref: "cd frontend && npm run lint && npm run build && npm run check:activity-layout && npm run knip"
        status: pass
    human_judgment: true
    rationale: "No component-level test exercises the Apply/preset click interaction or the input styling; verified by running the automated gates above plus manual code review of ActivityPage.tsx. A human should click through /activity as a superuser to confirm the visual result matches the plan's manual verification step."

duration: 55min
completed: 2026-09-20
status: complete
---

# Quick 260920-frk: Activity dashboard timespan selector Summary

**Custom start/end window on `GET /api/admin/activity/stats` (17 bounded queries, window-keyed cache) plus a native date-range picker on the Activity Pulse dashboard**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified:** 8
- **Commits:** 3

## Accomplishments

- `resolve_window()` accepts `custom_start`/`custom_end` and returns a `ResolvedWindow.window_end`; every `fetch_*` helper in `app/services/activity_queries.py` now takes a `window_end` and applies an exclusive-upper-bound predicate (`< CAST(:last AS date)`), correct for both `date` and timestamp columns.
- The six cohort helpers (`fetch_funnel`, `fetch_purged_excluded`, `fetch_time_to_import`, `fetch_stickiness`, `fetch_conversion`, `fetch_conversion_compare`) bound their entry predicate on both sides while their documented follow-forward joins (`games`, `user_activity`, `bot_game_settings`) stay unfiltered, unchanged from before this plan.
- `fetch_train_funnel`'s all-time control line binds a new `_ALL_TIME_END` sentinel (9999-12-31) so it keeps meaning "all time" even when the windowed run is truncated to a custom end date.
- `GET /api/admin/activity/stats` accepts optional `start`/`end` query params; `_build_window_request` rejects `start > end`, `end > today`, and a one-of-two pair with 422, while a `start` before the dataset is clamped up (existing preset behaviour, not an error).
- `StatsCache` now keys on the full `WindowRequest` (range key + optional dates) instead of a bare `RangeKey`, with `_MAX_ENTRIES = 16` and oldest-first eviction, since the key space is now every date pair a caller can name.
- The dashboard's controls row gained a start date, end date, and Apply button in their own `.seg` pill; Apply commits the two inputs into the query key (`applied?.start`/`applied?.end`), a preset click clears `applied` and returns to preset mode, and preset `aria-pressed` only reads true when no custom window is applied.

## Task Commits

1. **Task 1: Custom window end-to-end — request params, window resolution, upper bound on all 17 queries** - `cdad719e2` (feat, tdd tracer)
2. **Task 2: Coverage for the single-day, today, validation and cache-keying cases** - `f34891e69` (test)
3. **Task 3: Date inputs and Apply on the dashboard controls row** - `b244d0ebf` (feat)

_Note: Task 1 is `tdd="true"`. The end-to-end test (`test_stats_custom_window_truncates_at_end_date`) was written and run to a confirmed RED state (`AssertionError: assert 'all' == 'custom'`) before any production code changed, then the whole task's implementation and RED-to-GREEN transition landed in a single commit per the plan's tracer instructions._

## Files Created/Modified

- `app/services/activity_queries.py` - `SelectedRange`, `WindowRequest`, `_ALL_TIME_END`, `_end_exclusive`, `resolve_window(custom_start=, custom_end=)`, `window_end` on `ResolvedWindow`, upper-bound predicate on all 17 `fetch_*` helpers
- `app/services/activity_stats.py` - `build_payload(request: WindowRequest, ...)`, `StatsCache` keyed on `WindowRequest` with `_MAX_ENTRIES` eviction
- `app/routers/admin_activity.py` - `start`/`end` query params, `_build_window_request` validation helper
- `tests/test_admin_activity_stats.py` - RED-then-GREEN end-to-end test, 6 pure `resolve_window` custom-window cases, 5 endpoint cases (single day, today, 5-way validation, cache independence, `?range=custom` rejection), signature follow-ups on 3 `fake_build_payload` fakes and 8 direct `fetch_*` call sites
- `frontend/src/pages/activity/ActivityPage.tsx` - `todayIso()`, `startDate`/`endDate`/`applied` state, extended query key, Apply/preset handlers, the new date-input `.seg` group
- `frontend/src/pages/activity/styles.css` - `.seg input[type="date"]` styling + narrow-viewport padding overrides mirroring `.seg button`
- `frontend/src/types/activity.ts` - `ActivitySelectedRange`, retyped `ActivityStatsPayload.range`
- `CHANGELOG.md` - one bullet under `## [Unreleased]` / `### Added`

## Decisions Made

- **add-alongside, not promote** (plan's own `<assumption_delta_decision>`): `RangeKey` stays the four presets; `?range=custom` is still a 422. `SelectedRange` is the payload's echo-only superset.
- **Native `<input type="date">`** over the app's `CustomRangePopover`: that component is wired to `FilterPanel`'s pending-state commit semantics and a `PopoverAnchor` it doesn't own here, and the dashboard's own Tailwind-free `.activity-dash` stylesheet (calibrated by `check-activity-layout.mjs`) is a poor fit for a Tailwind-driven popover.
- **`lead_in_start` gets a second clamp** (`min(..., window_start)` in addition to the existing `max(..., data_start)`): a custom window ending before `data_start` would otherwise produce `lead_in_start > window_start`, an empty `days` list, and an out-of-range `window_start_index` — this is the guard the plan calls out in step 3, exercised by `test_resolve_window_custom_entirely_before_data_start_stays_safe`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Follow-on signature fixes for direct `fetch_*`/`fetch_train_funnel`/`fetch_guest_train` call sites not named in Task 1's action item 12**

- **Found during:** Task 1, after changing every `fetch_*` helper's signature
- **Issue:** The plan's action item 12 only named the 3 `fake_build_payload` monkeypatch fakes at the file's known line numbers. Running the test suite surfaced 4 pre-existing test functions (`test_fetch_train_funnel_seeded_cohort`, `test_fetch_train_funnel_excludes_opener_whose_first_session_predates_window`, `test_purged_user_excluded_from_game_derived_cohorts`, `test_fetch_guest_train_d11_d12_semantics`) that call `fetch_train_funnel`, `fetch_funnel`, `fetch_time_to_import`, `fetch_stickiness`, `fetch_conversion_compare`, `fetch_purged_excluded`, and `fetch_guest_train` directly, without going through `build_payload`. These broke with `TypeError: missing 1 required positional argument: 'window_end'`.
- **Fix:** Added a `window_end` local to each of the 4 test functions, set far enough in the future to keep every seeded row inside the window (matching each test's own point — cohort ENTRY semantics, not the new truncation), and threaded it through the existing direct calls.
- **Files modified:** `tests/test_admin_activity_stats.py`
- **Verification:** `uv run pytest tests/test_admin_activity_stats.py -x` — all 27 tests (later 41, after Task 2) pass.
- **Committed in:** `cdad719e2` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking signature follow-up, Rule 3)
**Impact on plan:** No scope creep — this is the necessary tail of the plan's own action item 6 (give every `fetch_*` a required `window_end`); the plan's list of "who calls `build_payload`" callers just didn't enumerate direct `fetch_*` callers.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Feature is complete and self-contained; no follow-on phase depends on this.
- Manual UAT (plan's `<verification>` "Manual (operator, not gating)" step — open `/activity` as a superuser, set both dates to today, Apply, confirm the header/DAU tile, then a past week) was not run in this session; recommended before considering the feature fully signed off, though not blocking given the automated coverage above (see D6's `human_judgment: true`).

## Self-Check: PASSED

All 9 files (8 code/docs files + this SUMMARY) and all 3 task commit hashes (`cdad719e2`, `f34891e69`, `b244d0ebf`) verified present.

---
*Phase: quick-260920-frk*
*Completed: 2026-09-20*
