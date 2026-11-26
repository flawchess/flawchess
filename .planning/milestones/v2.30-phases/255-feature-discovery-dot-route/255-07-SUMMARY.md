---
phase: 255-feature-discovery-dot-route
plan: 07
subsystem: release
tags: [changelog, alembic, pre-merge-gate, uat, feature-route]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "seed migration (255-04), route arbiter and dots (255-02, 255-03, 255-05), Train completes on use (255-06)"
provides:
  - "CHANGELOG [Unreleased] bullets for the feature-discovery dot route"
  - "Alembic head re-check against main: single head, no re-point needed"
  - "Green full pre-merge gate on the phase tree"
  - "Route walk at 1280 px and 390 px as fresh signups, recorded"
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - CHANGELOG.md
key-decisions:
  - "No migration re-point: main gained no migration since the branch point, so c3f8e2a6d255 stays on down_revision a7d2c9e1b254"
requirements-completed: [D-01, D-02, D-03, D-06, D-14, D-20, D-21, D-23]
duration: n/a (two executors plus an orchestrator-driven browser walk)
completed: 2026-11-15
status: complete
commits: 1
plan_head_before: 6211a1b2aec70970213cea72a61a749b134d668d
plan_head_after: b36883b2e20584084c823e942535e7d7d542a820
actuals:
  tokens: 1000
  tasks: 2
  commits: 1
coverage:
  - deliverable: "Alembic head re-check: one head, seed migration sits on main's newest migration (Pitfall 11)"
    human_judgment: false
    verification:
      - kind: command
        ref: "uv run alembic heads (c3f8e2a6d255 only); git diff --name-only --diff-filter=A HEAD...main -- alembic/versions/ (empty)"
        status: pass
  - deliverable: "Full CLAUDE.md pre-merge gate on the phase tree"
    human_judgment: false
    verification:
      - kind: command
        ref: "ruff format and check, ty (app/tests/scripts and analysis), check_function_size, pytest -n auto -x (6624 passed, 19 skipped), frontend lint, build, vitest (6446 passed), knip"
        status: pass
  - deliverable: "CHANGELOG [Unreleased] bullets (one Added, two Changed)"
    human_judgment: false
    verification:
      - kind: file
        ref: "CHANGELOG.md#Unreleased"
        status: pass
  - deliverable: "D-01 / D-02 / D-03 / D-06 / D-14 / D-20 / D-21 / D-23: route walk at desktop and mobile widths"
    human_judgment: true
    verification:
      - kind: manual
        ref: "Task 2 route walk, 1280x800 and 390x844, fresh guest each (steps 2 to 7)"
        status: pass
      - kind: manual
        ref: "Task 2 step 8 (existing pre-migration account)"
        status: deferred
---

# Phase 255 Plan 07: Close-out (Changelog, Gate, Route Walk) Summary

The phase closes green: one Alembic head, a changelog entry, a clean full pre-merge gate, and a route walk at 1280 px and 390 px that showed at most one route dot at a time in the D-06 order. Step 8 (existing pre-migration account) is data-verified only; its browser leg is deferred to the owner.

## Task 1: Alembic head re-check, changelog, full gate (commit b36883b2e)

- `git diff --name-only --diff-filter=A HEAD...main -- alembic/versions/` was empty and `uv run alembic heads` printed `c3f8e2a6d255 (head)` only, with `down_revision` a7d2c9e1b254 confirmed. No re-point and no merge of main were needed.
- `CHANGELOG.md` `[Unreleased]` gained 1 Added bullet ("one feature at a time") and 2 Changed bullets (Train clears on Start; the Bookmarks dot is removed and existing accounts start complete).
- The full pre-merge gate passed on the first run, so no style or chore commit followed:
  - ruff format: 617 files left unchanged; ruff check: all checks passed.
  - ty on `app/ tests/ scripts/` and on `analysis/`: all checks passed.
  - function-size gate: 1555 functions scanned, no breaches.
  - pytest: 6624 passed, 19 skipped, 35 warnings in 165.82 s.
  - frontend: lint rc 0, build rc 0, vitest 367 files and 6446 tests passed, knip rc 0 (two pre-existing configuration hints only).

## Task 2: Route walk (checkpoint:human-verify, approved)

The orchestrator drove the walk on the owner's behalf, as the plan allows, against the dev stack on this checkout. It used a same-origin iframe at exactly 1280x800 and 390x844 on `http://127.0.0.1:5173`, each width with its own fresh guest account. Evidence is DOM-based: visible `[data-testid*="notification-dot"]` elements and their host control.

### Desktop, 1280 px (fresh guest, zero games)

| Step | Outcome |
| ---- | ------- |
| 2 | Landed on `/library/import`; the only dot was `train-notification-dot` on the Train nav. PASS |
| 3 | On `/train` the only dot was `train-start-notification-dot` inside `btn-train-start`, none on the nav. On the Leaderboard tab it was `train-today-notification-dot` on `tab-train-today`. After pressing Start the only dot was `bots-notification-dot` on the Bots nav. The waiting-count badge `train-notification-badge` showed alongside as the only other red mark (D-17). PASS |
| 4 | On `/bots`, home and `/library/import`: zero route dots; the Openings and Endgames nav items were `aria-disabled`. PASS (D-23) |
| 5 | Lichess import (account `thibault`, default filters) ran about 350 s. A 500 ms sampler saw zero dots and a locked nav for the whole import; `openings-notification-dot` appeared within 1 s of the import going idle and the nav unlocking. Chain then followed: `played-as-notification-dot` on `sidebar-strip-btn-color`, toggle, `filters-notification-dot` on `sidebar-strip-btn-filters` (stays while the filter panel is open), Apply, `openings-stats-notification-dot` on `tab-stats`, open Stats, `endgames-notification-dot` on `nav-endgames`, open Endgames, `library-notification-dot` on `nav-library`, open Library, `library-stats-notification-dot` on `tab-stats`, open it, no dot on any page. PASS |
| 6 | Covered by the step 5 chain at this width. PASS |
| 7 | Never more than one route dot; no What's New panel and no New pill (D-01). PASS |

Server state after the walk: all nine steps `done` in `feature_route.steps` (import with `with_dot` false, the rest true).

### Mobile, 390 px (second fresh guest, zero games)

| Step | Outcome |
| ---- | ------- |
| 2 | `train-notification-dot-mobile` on `mobile-nav-train`; with the More drawer open the same item also showed `train-notification-dot-drawer` on `drawer-nav-train`. PASS |
| 3 | Start-button dot, Today-tab dot on Leaderboard, then `bots-notification-dot-mobile` after Start. PASS |
| 4 | No dot on Bots, Library/Import, or in the More drawer. PASS (D-23) |
| 5 | Lichess import (blitz only, cap 1000) ran about 84 s with zero dots; `openings-notification-dot-mobile` (and the drawer twin) appeared 1 s after it went idle. PASS |
| 6 | `played-as-notification-dot-mobile` on `btn-toggle-played-as` on Moves (10x10 px at the top-right of the 44x44 button). On the Stats tab the same dot sat at the top-right edge of `opening-color-switch-mobile`; choosing a colour there moved it to `filters-notification-dot-mobile` on `subnav-filter-button`; Apply moved it to `endgames-notification-dot-mobile`; then `library-notification-dot-mobile` (plus drawer twin) on Endgames; then `library-stats-notification-dot-mobile` on `tab-stats-mobile`; opening it left no dot on any page or in the drawer. PASS |
| 7 | At most one route dot (plus its drawer twin while the drawer is open); no What's New panel and no New pill. PASS |

Not observed at 390 px: the hop onto the mobile Openings Stats tab (`tab-stats-mobile`). The walk opened Stats first to check the colour-switch placement, so the Stats visit was already recorded and the route went from filters straight to Endgames. That hop is covered at 1280 px and by the 255-05 vitest cases.

### Step 8: existing pre-migration account

Not walked in a browser. Signing in as the owner's dev account with a minted token was denied by the session's permission classifier and was not worked around. Substitute evidence: a read-only dev DB query shows all 20 users carry `feature_route` with nine steps (user 28's `openings` step is `{status: done, with_dot: false, date: 2026-11-15}`), and a guest in the identical all-done state shows no dot on any page at either width. Recorded as data-verified, browser leg deferred to the owner.

## Deviations from Plan

None. No code changed in this plan beyond `CHANGELOG.md`; the walk produced no defects.

## Issues / Follow-ups

1. After the final step completes, `feature_route.current` still holds `{step: library-stats, since_days: 1}` although that step is done. No dot renders, so the UI is unaffected, but the stamp is never cleared. Candidate follow-up for the code review.
2. Two UAT guest accounts with imported lichess games remain in the dev DB.
3. On the mobile Import page a synthesized pointer-event sequence did not start the sync while a plain `.click()` did. This is a UAT-tooling note, not a product finding.
4. Step 8 browser leg (owner signs in to a pre-migration account and confirms no dot anywhere) is deferred to the owner.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

`CHANGELOG.md` exists; commit b36883b2e is an ancestor of HEAD; `git rev-list --count 6211a1b2a..HEAD` is 1, matching `commits: 1`.
