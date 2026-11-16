---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 14
subsystem: release
tags: [facepalm-score, column-drop, migration, deploy, one-way]
requires:
  - phase: 254-10
    provides: "Strict prod parity record, expression vs stored column"
  - phase: 254-12
    provides: "Refit live on prod, readers on the expression"
  - phase: 254-13
    provides: "Writers keep facts only"
  - phase: 254-17
    provides: "Migration c9f4e1a3d254 and the model without the six columns"
provides:
  - "Prod, dev and benchmark schemas at c9f4e1a3d254: no stored facepalm score, no line_loss_1/3/5/7/9"
affects: []
tech-stack:
  added: []
  patterns:
    - "Squash onto a main that another session has checked out: git commit-tree of the branch tree on origin/main, push, then pull --ff-only in the main checkout"
key-files:
  created: []
  modified:
    - CHANGELOG.md
key-decisions:
  - "drop-now (owner, 2026-11-16: 'Proceed with both')"
  - "Shipped together with Phase 255 (owner, 2026-11-16: 'ship both')"
requirements-completed: [D-02]
coverage:
  - id: D1
    description: "Dev end to end on the dropped schema: line pass, status, calibration"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "dev line pass (2880 games, 4557 scored), status, calibration, all exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full pre-merge gate green on the rebased branch tip"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "pytest -n auto -x (6627 passed, 19 skipped); frontend lint, build, test (6453 passed), knip; ruff, ty, analysis ty, nesting gate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nothing lost on prod: every stored score is reproducible from the facts"
    requirement: "D-02"
    verification:
      - kind: manual
        ref: "prod SQL before the drop: stored 1,952,854, expression 1,952,863, stored without played fact 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Prod schema at c9f4e1a3d254 with no facepalm_score or line_loss column"
    requirement: "D-02"
    verification:
      - kind: manual
        ref: "prod MCP: alembic_version c9f4e1a3d254, information_schema count 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Hook still writes facts and stamps after the deploy"
    requirement: "D-02"
    verification:
      - kind: manual
        ref: "prod MCP at 14:23Z: 11 games processed since the deploy, 27 user blunders with reply spread, both arrays and best prob"
        status: pass
    human_judgment: false
duration: 100 min
completed: 2026-11-16
status: complete
commits: 1
actuals:
  tasks: 3
  commits: 1
---

# Phase 254 Plan 14: drop the stored score on prod Summary

**The stored facepalm score and the five old line-loss columns are gone from prod (`83410165c`, deployed 2026-11-16T05:56Z). The score is computed from the stored facts everywhere. The hook was seen writing all facts on the new schema the same day (14:23Z).**

## Task 1: dev end to end and gate

- Dev DB at `c9f4e1a3d254`. Line pass over 2880 games, `scores_set=4557`; status `user_blunders_with_score=4557 user_blunders_qualifying=1883` (cut 0.50); calibration exit 0.
- `CHANGELOG.md` `## [Unreleased]`: "Internal: removed the stored facepalm score and the old line-loss columns; the score is computed from the stored facts."
- Gate on the rebased tip (after Renovate #483 landed on main), every command exit 0: ruff format, ruff check, ty, analysis ty, nesting gate, `pytest -n auto -x` (6627 passed, 19 skipped), frontend lint, build, test (6453 passed), knip. A later docs-only commit on main (`4426f919a`) needed a second rebase and no gate rerun.

## Task 2: decision

- **drop-now**, owner, 2026-11-16.
- Evidence on prod before the drop: 1,952,854 rows with a stored score; the expression scores 1,952,863; 0 rows with a stored score and no played fact; 930,227 qualifying.
- Plan 10 parity line: `stored_scored=1850930 expression_scored=1850930 both_scored=1850930 max_abs_diff=1.003345291294977e-07 cut_side_mismatches=0`.
- No open seed reads the dropped columns (0ke closed; iuv names service files only).

## Task 3: ship

- No operator script running against prod.
- Squash on main: `cb79fc0a6` (tree identical to the gated branch tip); phase branch and worktree deleted.
- Release PR #484, CI green (run 43812470536), squash-merged to production as `83410165c`. The release also carries Phase 255 (owner: "ship both").
- `bin/deploy.sh` exit 0, finished 2026-11-16T05:56:45Z, server SHA verified, site 200. Forward-port `7e6c09c5e` (done by the script).
- Prod: `alembic_version` = `c9f4e1a3d254`; no `facepalm_score` or `line_loss%` column on `game_flaws`.
- Benchmark DB: `bin/benchmark_db.sh start` applied `c3f8e2a6d255` and `c9f4e1a3d254`. The :8001 backend was started after the drop reached main, so it was not restarted.
- Sentry: 05:58Z, 06:28Z and 06:58Z (one hour after the deploy): no issue first seen in the previous 2 h, no unresolved issue with an event in the previous 90 min.

## Open

- **Hook check (S4):** at 06:28Z and 06:58Z no game had been imported or analysed since 04:55Z (the last one got its Maia stamp at 04:55:36Z, before the deploy), and no analysed game is waiting for the hook. The write path is covered by the dev run and the test suite on the dropped schema. Re-check once prod has traffic: games with `maia_flaws_completed_at > '2026-11-16 05:57+00'` above 0.

- **Update 07:16Z:** the first game since the deploy (3294647) was imported and processed at 07:13Z. The hook ran on the dropped schema: all three stamps set, `maia_played_prob` written on its one flaw, no Sentry issue. That flaw is a mistake, not a blunder, so the blunder-only facts (reply spread, material arrays, best prob) are not expected on it and have not yet been seen written after the deploy.

- **Closed 14:23Z:** 11 games have been processed since the deploy. 27 of their blunders carry the reply spread, both material arrays and the best-move probability. The hook check passes.

## Task Commits

1. **Drop squash (plans 13, 17, changelog)** - `cb79fc0a6` (refactor)

## Deviations from Plan

- **Tasks ran inline in the orchestrator** (dev reads, gate, deploy).
- **Squash by `git commit-tree`:** main was checked out in the shared main checkout by another session, so the squash commit was built from the branch tree on `origin/main`, pushed, and the main checkout fast-forwarded.
- **Migration parent:** `c9f4e1a3d254` chains after Phase 255's `c3f8e2a6d255`, not `a7d2c9e1b254` as planned.
- **Release scope:** Phase 255 shipped in the same release.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The downgrade re-adds the columns empty; the data is reproducible from the facts.

## Self-Check: PASSED

`origin/production` is `83410165c`; prod `alembic_version` is `c9f4e1a3d254`; `git branch --show-current` prints `main`.
