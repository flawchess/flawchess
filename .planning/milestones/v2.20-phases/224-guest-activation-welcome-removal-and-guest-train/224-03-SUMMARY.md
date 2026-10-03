---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 03
subsystem: analytics
tags: [fastapi, raw-sql, activity-dashboard, umami, growth-metrics, pytest]

# Dependency graph
requires: []
provides:
  - "fetch_guest_train raw-SQL reader (guest-cohort Train sessions completed before promotion, purged guests excluded) wired into the Activity payload"
  - "Activity Train card renders the guest-cohort line (#tr-guest-note) as text only, no new chart series"
  - "reports/growth/guest-activation-baseline-2026-09-17.md: four separate lever readings with their committed SQL, three prod-DB rows filled, the Umami row deferred to the phase UAT"
affects: [224-verification, growth-after-reading]

# Actuals (#2632)
actuals:
  tokens: 0
  tasks: 4
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guest-cohort analytics queries reuse the _GUEST_COHORT predicate and CAST(:first AS date) named binding; the only f-string content is the module-level constant"
    - "Prod baseline rows are read by the orchestrating session through the read-only flawchess-prod-db MCP tool, never by a spawned executor (subagents do not inherit project-scoped MCP servers)"

key-files:
  created:
    - reports/growth/guest-activation-baseline-2026-09-17.md
  modified:
    - app/services/activity_queries.py
    - app/services/activity_stats.py
    - tests/test_admin_activity_stats.py
    - frontend/src/pages/activity/render.js
    - frontend/src/pages/activity/ActivityPage.tsx

key-decisions:
  - "The three prod-DB baseline rows were read by the orchestrator via the read-only MCP role after the executor found the tool unavailable in its context; query text was not altered"
  - "The /welcome landings Umami row stays `PENDING OPERATOR READING` on purpose: the user chose to test at the end of the phase, so it is carried as a human_verification item into the phase UAT rather than blocking the remaining waves"
  - "Lever A metric 1 uses the funnel's purged-guest exclusion (cohort 367) while lever B metric 1 keeps purged guests (cohort 468); the note explains the difference instead of harmonising the two definitions"

requirements-completed: [GUESTACT-12, GUESTACT-13]

coverage:
  - id: D1
    description: "Activity Train card reports guest-cohort sessions completed and distinct guests, pre-promotion only, purged excluded"
    requirement: "GUESTACT-12"
    verification:
      - kind: unit
        ref: "tests/test_admin_activity_stats.py (fetch_guest_train cases)"
        status: pass
      - kind: other
        ref: "npm run check:activity-layout"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dated baseline note holds four separate readings with committed SQL; prod rows filled, no combined number"
    requirement: "GUESTACT-13"
    verification:
      - kind: other
        ref: "grep -c 'UNRESOLVED' reports/growth/guest-activation-baseline-2026-09-17.md == 0; grep -c 'no combined' > 0"
        status: pass
      - kind: manual
        ref: "Umami reading of /welcome landings and home-visitor denominator (window 2026-06-19..2026-09-17)"
        status: pending
    human_judgment: true

duration: 25 min executor + orchestrator close-out
completed: 2026-09-18
status: complete
---

# Phase 224 Plan 3: Metrics Baseline and Dashboard Guest Cohort Summary

**The Activity dashboard's Train card now carries a guest-cohort reading (`fetch_guest_train`, text only), and `reports/growth/guest-activation-baseline-2026-09-17.md` records the pre-merge numbers for both levers as four separate readings with their exact SQL; the three prod-DB rows are filled, and the one Umami row is deferred to the end-of-phase operator test by the user's decision.**

## Performance

- **Duration:** ~25 min executor (tasks 1–3) plus orchestrator close-out
- **Started:** 2026-09-17T21:00:00Z
- **Completed:** 2026-09-18 (close-out)
- **Tasks:** 4 (3 autonomous, 1 human-action checkpoint carried into UAT)
- **Files modified:** 6

## Accomplishments

- `app/services/activity_queries.py`: `fetch_guest_train(conn, first)` returns `sessions_completed` and `users` for `_GUEST_COHORT` users created in the window, counting only `drill_sessions.status = 'completed'` dated strictly before `promoted_at` (D-11), with `games_purged_at IS NULL` (D-12). `CAST(:first AS date)` named binding, no value interpolation (T-224-10).
- `app/services/activity_stats.py`: `guest_train` added to the payload via `build_payload`.
- `tests/test_admin_activity_stats.py`: 26 tests green, including the new guest-train cases (pre/post promotion boundary, purged exclusion, window bound).
- `frontend/src/pages/activity/render.js` + `ActivityPage.tsx`: `renderTrainCard` writes the guest line into `#tr-guest-note`; no new chart series, `npm run check:activity-layout` still passes at all four phone widths.
- `reports/growth/guest-activation-baseline-2026-09-17.md`: four metric sections, each with its committed SQL and the S-7 "no combined number" statement. Prod rows read 2026-09-17 with `:first = '2026-06-19'`:
  - Lever A metric 1: 125 of 367 surviving guests started an import (34.1%)
  - Lever B metric 1: 74 of 468 guests promoted (15.8%); 3.28 vs 1.41 active days
  - Lever B metric 2: 0 guest Train sessions completed (expected pre-merge)

## Task Commits

1. **Task 1: fetch_guest_train reader and its Payload wiring** - `3647d720e` (feat)
2. **Task 2: Render the guest cohort line in the Activity Train card** - `4abda89c0` (feat)
3. **Task 3: Author the baseline note with its four queries** - `4d7ba195b` (docs)
4. **Task 4 (partial, orchestrator): fill the three prod-DB rows** - `ec2934a71` (docs)

## Files Created/Modified

- `app/services/activity_queries.py` - new `fetch_guest_train` reader
- `app/services/activity_stats.py` - `guest_train` payload key
- `tests/test_admin_activity_stats.py` - guest-train unit coverage
- `frontend/src/pages/activity/render.js` - guest-cohort line in the Train card
- `frontend/src/pages/activity/ActivityPage.tsx` - `#tr-guest-note` element
- `reports/growth/guest-activation-baseline-2026-09-17.md` - baseline note

## Decisions Made

- The executor could not call the query-only `flawchess-prod-db` MCP tool (spawned subagents inherit only user-scoped MCP servers), so it wrote `UNRESOLVED — see checkpoint` placeholders per the plan's own precondition rule. The orchestrating session then ran the three committed queries verbatim through that MCP tool over `bin/prod_db_tunnel.sh` and pasted the raw results (`ec2934a71`).
- The Umami reading could not be automated in this session: the Chrome extension was not connected and the auto-mode classifier denied a read-only `psql` against the Umami database over SSH. The user chose "Continue, I'll test at the end", so the row keeps its `PENDING OPERATOR READING` marker and is carried as a human_verification item into the phase UAT instead of blocking waves 2–3 (which have no dependency on this plan).

## Deviations from Plan

### Checkpoint carried forward (user decision)

**Task 4's `blocking-human` checkpoint is not resolved inside this plan.** The plan's Task 4 verification (`grep -c 'PENDING OPERATOR READING' … == 0`) is intentionally still failing. The resume signal (`landings=<N> denominator=<M> basis=<pageviews|sessions>`) is unchanged; when the user pastes it, replace the placeholder in section "Lever A, metric 2" with the two numbers, the percentage, the basis and the reading date, and commit the note. Nothing else in the phase depends on it.

### Auto-fixed

None in tasks 1–3.

---

**Total deviations:** 1 carried-forward human checkpoint (by user decision), 0 auto-fixed.
**Impact on plan:** All code and all automatable measurements landed. The after-reading for lever A metric 2 remains comparable to the prior published 390/1,051 once the operator supplies the same-window numbers.

## Issues Encountered

- `mcp__flawchess-prod-db__query` unavailable to the gsd-executor subagent (project-scoped MCP servers are not inherited). Worked around at the orchestrator, recorded in memory so future plans route prod reads to the orchestrator.
- Umami numbers remain a genuine human leg in this environment (see Decisions).

## User Setup Required

At the end-of-phase test: read the two Umami numbers for the FlawChess app site, window 2026-06-19 to 2026-09-17, and paste `landings=<N> denominator=<M> basis=<pageviews|sessions>`.

## Next Phase Readiness

- Dashboard reading is live; the after-reading of lever B metric 2 needs no hand-run SQL.
- Baseline note is committed with the SQL beside every number; only the Umami row is pending.
- Ready for phase verification; the Umami row is the phase's one open human item.

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-18*

## Self-Check: PASSED

- `app/services/activity_queries.py` contains `async def fetch_guest_train` (FOUND)
- `app/services/activity_stats.py` contains `fetch_guest_train` (FOUND)
- `frontend/src/pages/activity/render.js` contains `tr-guest-note` (FOUND)
- `reports/growth/guest-activation-baseline-2026-09-17.md` exists, >60 lines, 0 `UNRESOLVED` (FOUND)
- Commits `3647d720e`, `4abda89c0`, `4d7ba195b`, `ec2934a71` on the phase branch (FOUND)
