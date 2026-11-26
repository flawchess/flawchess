---
phase: 258-library-stats-recent-sample-snapshots
plan: 04
subsystem: performance
tags: [perf, timing, explain, changelog, pre-merge-gate, library-stats]
status: complete

requires:
  - phase: 258-library-stats-recent-sample-snapshots
    provides: the windowed flaw, facepalm and tactic services (plans 01 and 02) and the frontend basis line and quiet-TC state (plan 03)
provides:
  - temp/library-258/time_snapshot_endpoints.py, a read-only one-connection before/after timing tool for the three snapshot endpoints (gitignored)
  - temp/library-258/window_explain.sql, the account query and the two window EXPLAIN statements for D-19 (gitignored)
  - the user-facing CHANGELOG bullet for the phase
  - a green pre-merge gate (everything except the full pytest run, which the orchestrator ran)
affects: [prod D-18 / D-19 measurement by the orchestrator, squash-merge of phase 258]

actuals:
  tokens: 6000
  tasks: 2
  commits: 1

plan_head_before: 459a100fe4d24e35ff0ba81a17cd7924ea77db9b
plan_head_after: d2c025bca

key-files:
  created:
    - temp/library-258/time_snapshot_endpoints.py (gitignored, not committed)
    - temp/library-258/window_explain.sql (gitignored, not committed)
  modified:
    - CHANGELOG.md

key-decisions:
  - "The timing script needs `import app.models` (plus oauth_account and user) before the first query: a standalone script does not register the User mapper otherwise, and the first query fails with NoReferencedTableError"
  - "tactic arm of 'today' keeps count_analyzed_by_tc(require_tactic_blobs=True) alive, as instructed"

requirements-completed: [D-18, D-19]

coverage:
  - id: C1
    description: "The prod D-18 / D-19 tool exists, is read-only on one connection, and runs on dev with a row per endpoint"
    requirement: "D-18"
    verification:
      - kind: command
        ref: "uv run python temp/library-258/time_snapshot_endpoints.py --db dev --rounds 1 --warmup 0"
        status: pass
    human_judgment: false
  - id: C2
    description: "The prod timing verdict and the prod window EXPLAIN (D-18, D-19) are not measured here"
    requirement: "D-19"
    human_judgment: true
    rationale: "Needs prod data over the tunnel and the prod MCP, which executors do not have"
  - id: C3
    description: "The changelog bullet and the pre-merge gate"
    requirement: "D-18"
    verification:
      - kind: command
        ref: "grep -c 'The Flaws Timeline still shows all your games' CHANGELOG.md"
        status: pass
    human_judgment: false
---

# Phase 258 Plan 04: Performance tool, changelog and pre-merge gate Summary

A read-only, one-connection before/after timing script and the window EXPLAIN SQL for the prod D-18 / D-19 check (both proven on dev), the phase's CHANGELOG bullet, and a green pre-merge gate; the prod measurement itself is handed to the orchestrator.

**Duration:** about 25 min. **Tasks:** 2. **Files:** 1 committed (CHANGELOG.md) plus 2 gitignored operator files.

## Accomplishments

- `temp/library-258/time_snapshot_endpoints.py`: flags `--db {dev,prod}`, `--user`, `--rounds`, `--warmup`, `--from-date`. Engine with `pool_size=1, max_overflow=0`; every timed call opens a session, runs `SET TRANSACTION READ ONLY` first and rolls back. "Today" arm rebuilt from surviving primitives (`count_analyzed_by_tc` x2 + `fetch_flaw_comparison`; `fetch_facepalm_comparison`; tactic blob count + two `fetch_tactic_comparison`) plus the same pure builders; "windowed" arm calls `get_flaw_comparison` / `get_facepalm_comparison` / `get_tactic_comparison`. Arms interleaved, order alternating per round, medians and a PASS / REGRESSION table, exit 0 / 1 / 2. It also prints the windowed per-TC `total_n` / `analyzed_n` / `cap_reached`.
- `temp/library-258/window_explain.sql`: the account query and the 36-month and 5-year window `EXPLAIN (ANALYZE, BUFFERS)` statements with `:uid`, plus a note on what to read in the plan.
- CHANGELOG `[Unreleased]` / `### Changed`: the Library Stats bullet, verbatim from the plan.

## Dev dry-run (user 28, 5,401 analyzed games, `--db dev`)

Required dry run (1 round, no warm-up, cold caches), `temp/library-258/dry-run-dev.txt`:

| endpoint | today median ms | windowed median ms | change % | verdict |
|---|---|---|---|---|
| flaw-comparison | 2037 | 198 | -90 | PASS |
| facepalm-comparison | 635 | 557 | -12 | PASS |
| tactic-comparison | 1084 | 275 | -75 | PASS |

Warm run, 5 rounds + 2 warm-up (`dry-run-dev-warm.txt`):

| endpoint | today median ms | windowed median ms | change % | verdict |
|---|---|---|---|---|
| flaw-comparison | 672 | 208 | -69 | PASS |
| facepalm-comparison | 569 | 471 | -17 | PASS |
| tactic-comparison | 895 | 251 | -72 | PASS |

Windowed per-TC sample on dev: blitz 173 games (not at cap), rapid 1000 (cap reached), classical 9.

Explicit-recency path (`--from-date 2021-11-21`, 3 rounds, 1 warm-up, `dry-run-dev-fromdate.txt`): flaw 244 -> 173 ms PASS, tactic 340 -> 239 ms PASS, **facepalm 220 -> 662 ms (+201%) REGRESSION**. Both blitz and rapid hit the cap there (2,009 games windowed against about 3,186 filtered games today). This is one dev observation on a noisy machine and dev is not the gate, but it is the only regression seen and it is on the path where the window is wide: see "Handed to UAT" check 1, where the prod run with `--from-date` five years back is already planned. If it reproduces on prod, the likely suspects are the `= ANY(:ids)` list of about 2,000 ids against the facepalm expression, or the ~2k-element anchor plan.

## Pre-merge gate

| Step | Result |
|---|---|
| `ruff format app/ tests/ scripts/ analysis/` | 631 files unchanged |
| `ruff check . --fix` | All checks passed |
| `ty check app/ tests/ scripts/` | All checks passed |
| `ty check analysis/` (analysis venv) | All checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1682 functions, no breaches |
| Serial run of the six touched backend test files | 253 passed |
| `npm run lint` | clean |
| `npm run build` (tsc -b + vite) | exit 0 |
| `npm test -- --run` | 379 files, 6736 tests passed |
| `npm run knip` | exit 0 (two configuration hints only, pre-existing) |
| full `uv run pytest -n auto -x` | run by the orchestrator (7320 passed, 19 skipped after plan 02; re-run after this plan) |

No formatter or autofix changed any tracked file, so no `style(258)` commit was needed.

## Handed to UAT

1. **Orchestrator, prod read-only (D-18 / D-19), must be green before the squash-merge.** Run `bin/prod_db_tunnel.sh`. Through the `flawchess-prod-db` MCP run the account query of `temp/library-258/window_explain.sql`; for the account with the most analyzed games (and the one with the most games if different) run both window `EXPLAIN (ANALYZE, BUFFERS)` statements with its id. Then run `uv run python temp/library-258/time_snapshot_endpoints.py --db prod --user <id> --rounds 3` in the foreground (one connection, a few minutes; avoid the 02:15 UTC prod reboot), and once more with `--from-date` five years back. Expected: every row PASS and exit 0; plan uses `ix_games_user_played_at`, a sort and WindowAgg with a Run Condition; a JIT block with meaningful time on the flaw or tactic path means adding `disable_jit_for_transaction` there. Any REGRESSION is fixed before the merge; an index is measured on a non-prod DB before any migration (D-19). Watch the facepalm row on the `--from-date` run in particular (dev showed +201% there).
2. **Dev app, Library, Stats.** Read the basis line with default filters, with a Recency preset, and with Played as White; open a card popover; find a time control whose games are all older than 36 months (or shift the dev clock forward) and select it. Expected: the line follows D-13 ("Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed." / "... in the selected period ..." / "... in the current filters ..."); popovers say "in the recent sample"; the quiet time control shows "No {tc} games in the last 36 months." and the "5 years" hint above its timeline, with no tiles and no You vs. your opponents or Tactic motifs section; the timeline header says "All games in the current filters". Judgement items: D-13 polish, D-17 option label, research A5 / A6.

## Deviations from Plan

**1. [Orchestrator instruction] Full `pytest -n auto -x` not run by this executor**
- **Reason:** the orchestrator ran it green after plan 02 and re-runs it after this plan (executor-side long runs have died before). Recorded as "full pytest -n auto: run by the orchestrator".

**2. [Rule 3 - Blocking] Timing script import setup**
- **Found during:** Task 1
- **Issue:** a script in `temp/library-258/` has its own directory, not the repo root, on `sys.path` (`ModuleNotFoundError: app`); `MIN_TACTIC_CHIP_CONFIDENCE` lives in `library_repository`, not `tactic_detector`; and without `import app.models` the User mapper is unregistered (`NoReferencedTableError`).
- **Fix:** repo root inserted into `sys.path`, import corrected, models imported. Operator script only, nothing committed.

**Total deviations:** 1 orchestrator-directed gate change, 1 auto-fixed blocker (uncommitted operator script). **Impact:** none on committed code.

## Known Stubs

None.

## Threat Flags

None. The script and its outputs stay under gitignored `temp/library-258/` (T-258-09), use one connection and read-only transactions (T-258-10), and were run against dev only.

## Self-Check: PASSED

- `temp/library-258/time_snapshot_endpoints.py`, `window_explain.sql`, `dry-run-dev.txt`: present; `git check-ignore` exits 0.
- `grep -cE "^\| (flaw|facepalm|tactic)-comparison " temp/library-258/dry-run-dev.txt` = 3; `SET TRANSACTION READ ONLY` count in the script = 3; EXPLAIN statements in the SQL = 2.
- CHANGELOG greps return 1 and 1; commit d2c025bca is on the branch.
