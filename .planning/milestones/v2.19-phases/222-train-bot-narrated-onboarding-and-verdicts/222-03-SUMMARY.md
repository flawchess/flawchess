---
phase: 222-train-bot-narrated-onboarding-and-verdicts
plan: 03
subsystem: analytics (superuser activity dashboard)
tags: [fastapi, sqlalchemy, postgres, react, activity-dashboard, seed-166]

requires:
  - phase: 222-01
    provides: "no direct dependency — this plan is independent (wave 1, depends_on: [])"
provides:
  - "fetch_train_funnel(conn, window_start, data_start) on the read-only analytics engine — first-session 0-solve share and second-session return share, windowed + live all-time control"
  - "train_funnel key on the activity Payload / ActivityStatsPayload"
  - "'First-session drop-off and return rate' card in the Train sessions section of /activity"
affects: []

actuals:
  tokens: 5567
  tasks: 2
  commits: 2

commits: 2
plan_head_before: 617a28570058946923cde209eaad0b31f62e8b32

tech-stack:
  added: []
  patterns:
    - "Cohort-by-first-event CTE (first_session -> cohort -> flags), run twice through the same bound-parameter SQL string with two different cutoff dates (window_start, then data_start) to produce a windowed reading plus a live all-time control line that can never drift out of sync with it."
    - "Delta-based (baseline-before/after) test assertions against a shared session-scoped test DB, rather than absolute counts, so a global un-scoped aggregate query's test stays correct regardless of what other tests in the same pytest worker already seeded."

key-files:
  created: []
  modified:
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - tests/test_admin_activity_stats.py
    - frontend/src/types/activity.ts
    - frontend/src/pages/activity/ActivityPage.tsx
    - frontend/src/pages/activity/render.js
    - docs/activity-dashboard.md

key-decisions:
  - "Payload.train_funnel is typed dict[str, Any] (mirroring fetch_conversion's four-scalar shape), not list[list[Any]] as an earlier PATTERNS.md draft sketched — the PLAN's own action text (T-222-03-01 step 1) explicitly calls for the dict shape since this is eight scalars, not a time series; PATTERNS.md's snippet predates that reconciliation."
  - "The card uses existing `card`/`grid2`/`hero`/`cap`/`big`/`exp`/`note` CSS classes only — two `.hero` blocks placed inside a `.grid2` (not the single-hero `.split` layout the Conversion card uses, which pairs one hero with a chart) — since this card needs two independent big-number blocks and no chart, `.grid2`'s equal-width two-column grid is the closer existing fit. No new CSS class, no new chart primitive."
  - "No `data-testid` was added to the new card. The plan's own action text conditions the testid on 'if a details block is included'; this card has no `<details>`/table (the eight numbers are already fully visible across the two big-number blocks plus the all-time line), matching the Conversion card's own precedent of carrying no testid."

requirements-completed: [TRAINBOT-06]

coverage:
  - id: D1
    description: "fetch_train_funnel returns eight aggregate counts (windowed + all-time openers/zero_solve_users/finishers/returners), cohorted by each user's FIRST drill_sessions row, wired into build_payload with zero request-derived string interpolation."
    requirement: TRAINBOT-06
    verification:
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_fetch_train_funnel_seeded_cohort"
        status: pass
      - kind: unit
        ref: "tests/test_admin_activity_stats.py#test_fetch_train_funnel_excludes_opener_whose_first_session_predates_window"
        status: pass
      - kind: other
        ref: "uv run ruff check . && uv run ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Train sessions section of /activity shows both funnel metrics with numerator/denominator plus a live all-time control line and the right-censoring caveat, with no new chart primitive and no new layout-harness fixture."
    requirement: TRAINBOT-06
    verification:
      - kind: other
        ref: "cd frontend && npm run lint && npm run build && npm run check:activity-layout"
        status: pass
      - kind: other
        ref: "id-seam grep across render.js/ActivityPage.tsx for trf-zero-big/trf-zero-exp/trf-return-big/trf-return-exp/trf-alltime"
        status: pass
    human_judgment: false
  - id: D3
    description: "No Umami event was added anywhere in the dashboard seam (D-20)."
    verification:
      - kind: other
        ref: "grep -rn umami frontend/src/pages/activity/render.js frontend/src/pages/activity/ActivityPage.tsx (exits 1, no match)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-13
status: complete
---

# Phase 222 Plan 3: Train First-Session Funnel on the Activity Dashboard Summary

**One CTE (`fetch_train_funnel`) turns SEED-166's one-off production queries into a live `/activity` card — first-session 0-solve share, second-session return share, and a self-consistent all-time control line, with the dev-DB smoke reading (9/2/5/3) matching RESEARCH Finding J's own dev-DB reading exactly.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-13T~17:10:00Z (approx.)
- **Completed:** 2026-09-13T~18:05:00Z (approx.)
- **Tasks:** 2 (T-222-03-01, T-222-03-02)
- **Files modified:** 7

## Accomplishments

- `app/services/activity_queries.py`: new `fetch_train_funnel(conn, window_start, data_start) -> dict[str, Any]`, placed beside `fetch_train`. Runs RESEARCH Finding J's `first_session -> cohort -> flags` CTE twice (once per cutoff) through the same bound-parameter SQL string, returning eight `int`-coerced scalars: `openers`, `zero_solve_users`, `finishers`, `returners`, and their `all_time_*` counterparts. `Payload.train_funnel: dict[str, Any]` added beside `train`.
- `app/services/activity_stats.py`: one new sequential `await` line inside `build_payload`'s existing `async with` block — never `asyncio.gather`.
- `tests/test_admin_activity_stats.py`: two new tests seeding real `drill_sessions`/`drill_solves` rows via `test_engine` and calling `fetch_train_funnel` directly (no HTTP round trip needed for this query-level coverage). Both tests measure a delta (baseline fetched before seeding, result fetched after) rather than an absolute count, so they hold regardless of what else has landed in the shared session-scoped test DB from other tests in the same pytest worker.
- `frontend/src/types/activity.ts`: `ActivityStatsPayload.train_funnel` typed explicitly (eight named `number` fields), not an index signature.
- `frontend/src/pages/activity/ActivityPage.tsx`: new "First-session drop-off and return rate" card in the Train sessions section, after the "Sessions per day by outcome" card. Two `.hero` blocks (`trf-zero-*`, `trf-return-*`) inside a `.grid2`, plus a `<p className="note">` for the right-censoring caveat and a `#trf-alltime` line for the live all-time control text.
- `frontend/src/pages/activity/render.js`: `TRAINFUN` added to the payload destructure; new `renderTrainFunnelCard()` (built on the `#conv-big`/`#conv-exp` text pattern, with the same zero-denominator fallback shape as `renderConversionCard`) called from `render()` next to `renderTrainCard()`.
- `docs/activity-dashboard.md`: new "Train first-session funnel (SEED-166, D-19)" subsection documenting the cohort definition, both metric definitions, the live all-time control line, and the right-censoring caveat; notes that the frozen SEED-166 baselines stay in the seed file as historical record and are deliberately not hardcoded on the card.

## Task Commits

Each auto task was committed atomically:

1. **T-222-03-01: fetch_train_funnel on the read-only engine, with a seeded-cohort test** - `27a500cd9` (feat)
2. **T-222-03-02: The dashboard card — type mirror, DOM ids, renderer and the censoring caveat** - `82c10fcae` (feat)

**Plan metadata:** committed after this SUMMARY (see final commit below).

## Files Created/Modified

- `app/services/activity_queries.py` - `fetch_train_funnel`, `Payload.train_funnel`
- `app/services/activity_stats.py` - one new `await queries.fetch_train_funnel(...)` line in `build_payload`
- `tests/test_admin_activity_stats.py` - `fake_payload()` updated with `train_funnel={}`, plus `_seed_funnel_session` helper and two new seeded-cohort tests
- `frontend/src/types/activity.ts` - `ActivityStatsPayload.train_funnel`
- `frontend/src/pages/activity/ActivityPage.tsx` - new funnel card in the Train sessions section
- `frontend/src/pages/activity/render.js` - `TRAINFUN` destructure + `renderTrainFunnelCard()`
- `docs/activity-dashboard.md` - new "Train first-session funnel" subsection

## Decisions Made

- `Payload.train_funnel` is `dict[str, Any]`, mirroring `fetch_conversion`'s four-scalar shape (eight scalars here, not a time series) — the plan's own action text calls for this explicitly, superseding an earlier `list[list[Any]]` sketch in `222-PATTERNS.md` that predates that reconciliation.
- The card lays its two big-number blocks (`trf-zero-*`, `trf-return-*`) side by side inside `.grid2`, not the single-hero `.split` layout the Conversion card uses (which pairs one hero with a chart) — `.grid2`'s equal two-column grid was the closer existing fit for two independent stats with no chart, so no new CSS class was added.
- No `data-testid` on the new card: the plan conditions the testid on including a `<details>`/table, and this card needs neither (all eight numbers are already visible across the two hero blocks plus the all-time line) — matching the Conversion card's own precedent of carrying no testid.

## Deviations from Plan

None - plan executed exactly as written. Both tests were written directly against `fetch_train_funnel` via `test_engine` (as the plan's `<read_first>` pointed at `tests/routers/test_train.py`'s seeding helpers for the pattern to borrow, not to reuse verbatim) with self-contained seeding, matching this test file's own stated convention of not sharing helpers across files.

## Known Stubs

None.

## Threat Flags

None. All four threat-register entries (T-222-03-01 through T-222-03-04, T-222-03-SC) are discharged by construction: bound parameters only (`CAST(:cutoff AS date)`, no f-string SQL for this query — verified by the plan's own compound grep check), the pre-existing `current_superuser` gate on `GET /api/admin/activity/stats` is untouched and its tests stay green, the funnel SELECT list returns aggregate counts only (no `user_id`/`email`/`id`), and no package was installed (`git diff --exit-code -- pyproject.toml uv.lock frontend/package.json frontend/package-lock.json` exits 0).

## Issues Encountered

The first draft of the two new backend tests asserted absolute funnel counts (e.g. `openers == 3`). The second test's fixture reused `status="open"` for two sessions belonging to the same user, tripping the pre-existing `uq_drill_sessions_user_open` partial unique index (at most one open session per user) — fixed by seeding `status="expired"` instead, since the test only needs a non-`'completed'` status. Separately, the first test's absolute-count assertions were then found to be fragile against the shared session-scoped `test_engine` database: rows from the OTHER new test (seeded earlier in the same file, same worker) fell inside the second test's `data_start..` window and inflated its `all_time_openers` count from the expected 1 to 5. Rewrote both tests to assert on a delta (funnel result fetched once before seeding, once after) rather than an absolute count — this is the same class of fix the codebase's own "Eval lottery test isolation" precedent calls for on any un-scoped global aggregate query test. Not logged as a plan deviation since it never touched production code or acceptance criteria, only test robustness within Task 1's own scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The funnel card is live on `/activity` and the post-release reading procedure recorded in the plan (`<verification>` §Post-release reading procedure) can be followed as soon as this phase deploys: set the window to a range ending before the release date, read both shares; set it to a range starting at the release date, read them again. The all-time line is the running control, and the frozen 2026-09-12 production baselines (52/123 = 42%; 26/53 = 49%) stay in `.planning/seeds/SEED-166-train-first-session-retention.md`.
- **Dev-database smoke datapoint** (recorded per this plan's `<output>` instruction), read via a one-off script calling `fetch_train_funnel` directly against the dev database with `window_start` = 30 days before today and `data_start` = the dev DB's earliest `drill_sessions.session_date` (2026-08-04):
  - Windowed (last 30 days): `openers=3, zero_solve_users=1, finishers=1, returners=0`
  - All-time: `openers=9, zero_solve_users=2, finishers=5, returners=3` — this matches RESEARCH Finding J's own dev-DB reading (`openers=9 zero_solve_users=2 finishers=5 returners=3`) exactly, confirming the shipped query reproduces the query drafted during research.
- No blockers. This plan (wave 1, `depends_on: []`) is independent of plans 01/02/04/05/06 in this phase.

---
*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Completed: 2026-09-13*

## Self-Check: PASSED
