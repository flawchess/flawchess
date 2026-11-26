---
phase: 261-blunder-check-exploration-arm
plan: 07
subsystem: blunder-check
tags: [release, changelog, gate, serial-suite, prod-explain, D-10]

requires:
  - phase: 261-blunder-check-exploration-arm
    provides: plans 01 to 06 merged on the phase branch
provides:
  - CHANGELOG bullet for the avatar feedback under [Unreleased]
  - D-10 prod EXPLAIN report with verdict pass
  - green full pre-merge gate, green parallel suite, green serial suite
  - STATE.md open thread for the post-release share acceptance
affects: [squash-merge to main, release]

actuals:
  tasks: 3
  commits: 3
plan_head_before: f12c5d6d008d55d63861d76b41f960f84d763a01

key-files:
  created:
    - reports/blunder-check/exploration-probe-explain-261.md
  modified:
    - CHANGELOG.md
    - tests/test_game_repository.py
    - .planning/STATE.md

key-decisions:
  - "D-10 verdict pass: both scored probes read game_flaws through ix_game_flaws_game_id and ran faster than their cut counterparts; no new index"
  - "The changelog does not announce the exploration draw (owner-adjustable assumption from the plan)"

requirements-completed: [SEED-261121-t50, D-10]

status: complete
completed: 2026-11-22
human_verification_pending:
  - "Task 3 steps 1 to 4: feedback paragraph seen in the running app on the desktop card and the 375 px phone strip"
---

# Plan 261-07 summary: release readiness

## Task 1 (executor): tracer, changelog, pick SQL, full gate

Commit `2a79a4529` (CHANGELOG.md). No style commit was needed.

| Step | Exit | Result |
| ---- | ---- | ------ |
| `uv run pytest tests/routers/test_blunder_check_exploration.py -x` | 0 | 3 passed |
| `uv run ruff format app/ tests/ scripts/ analysis/` | 0 | 611 files unchanged |
| `uv run ruff check . --fix` | 0 | clean |
| `uv run ty check app/ tests/ scripts/` | 0 | clean |
| `uv run --project analysis --with ty ty check analysis/` | 0 | clean |
| `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` | 0 | 1679 functions, no breaches |
| `uv run pytest -n auto -x` | 0 | 6951 passed, 8 skipped |
| frontend `npm run lint` | 0 | clean |
| frontend `npm run build` | 0 | built |
| frontend `npm test -- --run` | 0 | 6762 passed |
| frontend `npm run knip` | 0 | 2 pre-existing configuration hints |

`temp/261-explore/pick-explain.sql` (gitignored) holds the four statements under their header lines; `grep -c TABLESAMPLE` prints 4. The helper replaces the pyformat `%%` with `%` so the statements run as-is.

## Task 2 (orchestrator): serial suite and D-10 on prod

**Serial suite.** First run: `1 failed, 5609 passed, 8 skipped`, `exit=1`. The failure was
`tests/test_game_repository.py::TestGetPlatformGameIdsForUser::test_returns_platform_game_ids_scoped_to_user_and_platform`.
Cause: the test hard-coded user id 801, and in a serial run the registered seeded-portfolio user
(`tests/seed_fixtures.py`, committed games `seed-NN`) was handed id 801 by the users id sequence once this
phase's new tests had registered enough users ahead of it. Parallel runs hid it (one DB and a shorter
sequence per worker). It is a test-isolation defect, not a product defect. Fix, commit `38d5abd1f`: the two
ids moved to 900801 / 900802, with a comment at the fix site. Second run:
`6951 passed, 8 skipped, 3 warnings in 380.58s (0:06:20)`, `exit=0`.

Not changed: the same file still hard-codes ids 1, 2, 42, 55, 601 to 606, 701, 702, 711 to 713. They did
not collide in this run, and the seeded user's id has already moved past them, but the pattern is fragile.
Follow-up candidate, not done here (out of plan scope).

**D-10.** Four statements, four runs each (one cold, three warm), prod, read-only, one connection.
Report: `reports/blunder-check/exploration-probe-explain-261.md`, commit `8d13abd40`.

| Pick | Cut warm median | Scored warm median | Bound | Seq Scan on game_flaws |
| ---- | ---- | ---- | ---- | ---- |
| foreign | 115.8 ms | 46.5 ms | 231.6 ms | no |
| nearest | 450.7 ms | 339.1 ms | 901.5 ms | no |

verdict: pass. Resume signal: "serial green; D-10 pass (46.5 ms / 339.1 ms)".

## Task 3 (orchestrator): browser check and share follow-up

- Step 5 done: `.planning/STATE.md` carries the "Phase 261 share acceptance" open thread.
- Steps 1 to 4 NOT performed: this session had no browser tool, so the feedback paragraph was not seen in
  the running app on the desktop card or the phone strip. Component tests cover both layouts and the router
  tests cover the wire, but that is not the visual check the plan asks for. It is carried as pending human
  verification.

## Deviations

- One fix outside the plan's `files_modified`: `tests/test_game_repository.py` (the serial failure above).
  The plan's Task 2 calls for fixing a serial failure before any merge.
- Task 3's browser steps are pending (see above).

## Self-Check: PASSED (with the browser check pending human verification)
