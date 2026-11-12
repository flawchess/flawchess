---
phase: 252-short-engine-line-repair-backfill-seed-261112-s4v
plan: 05
subsystem: release
tags: [release, deploy, pre-merge-gate, prod-baseline]

requires:
  - phase: 252-01
    provides: repair subcommand and engine root_moves
  - phase: 252-02
    provides: per-line tier-4 blob lane
  - phase: 252-03
    provides: blob-only server-pool drain tick, /atomic-lease tier-4/4b guard
  - phase: 252-04
    provides: feed, measure-flips, status subcommands
provides:
  - "Phase 252 code squash-merged on main (3de671271) and live in production (356370219)"
  - "pre-repair prod baselines for plans 06 and 07"
affects: [252-06, 252-07, 252-08, 252-09]

actuals:
  tasks: 3
  commits: 3
---

# Plan 252-05: merge, deploy and post-deploy baselines

Phase 252's code is on main and in production. All three tasks were performed by the orchestrator session.

## Task 1: owner go-ahead

Owner's answer, verbatim: **"Merge and deploy"** (option merge-and-deploy), given 2026-11-12 before any merge.

At decision time the code diff between `origin/production` and `origin/main` (excluding `.planning`) was empty, so
the release ships Phase 252 only.

## Task 2: gate, changelog, squash-merge, deploy

Pre-merge gate on the phase branch (head before the changelog commit: `b5967a218`), all exit 0:

| Step | Result |
|------|--------|
| `ruff format app/ tests/ scripts/ analysis/` | 576 files left unchanged |
| `ruff check . --fix` | All checks passed |
| `ty check app/ tests/ scripts/` | All checks passed |
| `ty check analysis/` (analysis project) | All checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | 1338 functions, no breaches |
| `pytest -n auto -x` | 5992 passed, 20 skipped |
| frontend lint, build, test, knip | exit 0 |
| serial `pytest -x` | 5992 passed, 20 skipped (12 min 16 s) |
| `pytest tests/services/test_engine_nodes.py` (real Stockfish) | 12 passed |

No formatter or autofix changes, so no `style(252)` commit.

- CHANGELOG bullet under `## [Unreleased]` / `### Fixed`, committed as `docs(252): changelog`.
- Squash-merge in the `flawchess-252` worktree: `3de671271 feat(252): short engine line repair backfill, per-line
  tier-4 re-walk`. The squash tree equals the phase branch tree (empty diff). Phase branch deleted, main pushed,
  `main...origin/main` = `0 0`.
- Release PR #474, CI green (backend, docker, frontend, test), squash-merged to production as `356370219`.
- `bin/deploy.sh`: first attempt stopped at the `scp` step because the fresh worktree had no `.prod.env` (nothing
  reached the server). The owner copied the file in; the second run succeeded. Deploy run 43277444981 finished
  2026-11-12T18:14:24Z, server verified at `35637021`, equal to the production head.
- Forward-port pushed: main is `7ee0fdbd5`, equal to origin/main.
- The worktree stays on main for plans 06-09 (D-09).

## Task 3: post-deploy health and baselines (prod, read-only, 2026-11-12T18:15:50Z)

| Probe | Value |
|-------|-------|
| Flaws with exactly one NULL blob line | 0 (the OR probe re-opened nothing) |
| Flaws with both blob lines NULL | 4,531 (unchanged from plan time) |
| Non-guest games without a full eval (tier-3 backlog) | 0 (guests: 56,007) |
| Non-guest evaluated games with `blobs_completed_at` NULL (natural tier-4 backlog) | 0 (guests: 2,063) |
| `pg_stat_activity` connections | 11 |
| `https://flawchess.com/` | HTTP 200 |

The two backlog rows were counted from `games` columns (`full_evals_completed_at`, `lichess_evals_at`,
`blobs_completed_at`) joined to `users.is_guest`; they reproduce the plan-time CONTEXT numbers exactly.

Worker snapshot, last 2 days (informational, D-15: no worker update is a precondition):

| worker_id | schema version | last_seen (UTC) |
|-----------|----------------|-----------------|
| amalie-nb | 3 | 2026-11-12 16:29:49 |
| amalie-pc | 3 | 2026-11-12 16:29:44 |
| mp9lr2n5 | 2 | 2026-11-12 13:22:08 |
| xqg864th | 2 | 2026-11-12 13:21:39 |
| xk9sox3f | 2 | 2026-11-12 13:21:22 |
| ai-slim | 2 | 2026-11-12 07:46:57 |

No remote worker had a heartbeat in the 105 minutes before the snapshot, so at that moment the re-walk capacity
was the server pool alone. Relevant for the D-10 drain-rate gate in plan 07.

Sentry (project flawchess): no issue first seen in the 2 hours up to the check. The check ran about 2 minutes
after the deploy, so the 60-minute window was not yet complete; it is re-read before the first prod write of
plan 06 and the result recorded in 252-06-SUMMARY.md.

Benchmark backend: pid 2978177 listens on :8001 with cwd `/home/aimfeld/Projects/Games/flawchess`, which is on
`gsd/phase-249-blunder-check-playable-mvp` and does NOT contain the Phase 252 squash commit. Plan 07 Task 2
must restart :8001 from the `flawchess-252` worktree on main before the benchmark line repair.

The `docker compose ps` and backend log tail from the deploy skill's step 7 were not run (remote exec was denied
in this session); `deploy.sh`'s own health check and server SHA verification passed.

## Deviations

- The pre-merge gate was started before the go-ahead was given (read-only on the phase branch); nothing was
  merged or pushed before the answer.
- This SUMMARY was written by the orchestrator instead of a continuation executor.

## Self-Check: PASSED
