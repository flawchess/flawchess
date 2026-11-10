---
phase: 247-maia-stats-on-game-flaws
plan: 06
subsystem: release
tags: [maia, deploy, changelog, prod-baselines]
requires: ["247-03", "247-04", "247-05"]
provides:
  - "Phase 247 squash-merged to main (b5f3601e8) and deployed to production (55ac58177, PR #464)"
  - "CHANGELOG [Unreleased] bullet for Maia flaw stats"
  - "Prod baselines S1-S5 for plan 07"
affects: [247-07]
status: complete
execution: orchestrator-inline
key-decisions:
  - "Owner answered merge-and-deploy at the Task 1 blocking checkpoint (2026-11-08)"
  - "Phase executed in a dedicated worktree ../flawchess-247 because the main checkout carried another session's uncommitted frontend edits; squash done on a temp branch there, main fast-forwarded with --ff-only, forward-port done from the worktree"
  - "Benchmark dry-run (plan 05 Task 3) was not run; owner did not answer the offer, benchmark path stays unit-covered"
  - "Live-lane proof deferred: zero non-guest games were waiting for analysis after the deploy (all 62,460 unevaluated games are guest games, never processed), so no go-forward stamp could appear in the 60-minute window. Owner said go ahead with the backfill; live-lane stamps stay distinguishable afterwards (stamp within seconds of full_evals_completed_at)"
requirements-completed: [D-12]
---

# Phase 247 Plan 06: Ship go-forward Maia scoring Summary

Go-forward Maia flaw scoring is live on production. The migration applied (9 `maia_%` columns), the site and
API answer 200, and Sentry shows no issues since the deploy.

## Pre-merge gate (phase branch tip 71fd35f4a, identical tree to squash b5f3601e8)

| Step | Result |
|---|---|
| ruff format / ruff check --fix | 563 files unchanged / all checks passed |
| ty app/ tests/ scripts/ and analysis/ | all checks passed |
| check_function_size.py --fail-over-depth 4 | 1307 functions, no breaches |
| pytest -n auto -x | 5761 passed, 20 skipped (1:44) |
| pytest -x serial | 5761 passed, 20 skipped (4:03), exit 0 |
| frontend lint / build / test / knip | clean / ok / 6076 passed / hints only |

## Ship

- Changelog: `docs(247): changelog` (71fd35f4a), bullet under ## [Unreleased] ### Added.
- Squash: `feat(247): Maia stats on game_flaws (SEED-261108-zkp)` b5f3601e8, pushed, `main...origin/main` = `0 0`.
  Phase branch deleted.
- Release PR #464, CI green (backend, frontend, docker, test), squash-merged to production 55ac58177.
- `bin/deploy.sh`: deploy run 42521367220 green (20:41-20:42 UTC), server at 55ac5817. Forward-port skipped by the
  script (dirty main checkout) and done manually from the worktree: c119ee403, tree unchanged.

## Prod verification

- Column check: `select count(*) from information_schema.columns where table_name in ('game_flaws','games') and column_name like 'maia_%'` = **9** (baseline 0).
- `curl https://flawchess.com/` HTTP 200, `/api/health` HTTP 200. SSH log reads are denied in auto mode.
- `scripts/backfill_maia_flaws.py --db prod --status` exit 0: `stamped_games=0 unstamped_games_with_flaws=1025382 flaws_with_maia=0 flaws_total=7611640`,
  unchanged over a 30-minute poll after the deploy.
- Why 0: last full eval 20:07:49 UTC (before the deploy), last worker heartbeat 20:07:49, and every one of the
  62,460 unevaluated games belongs to a guest user. No analysis happened after the deploy, so the live lanes had
  nothing to score. The live-scoring acceptance criterion is **deferred**, not failed.

## Baselines (Task 3)

| Probe | Result |
|---|---|
| S1 (1% sample, 76,218 flaws) | blob_null 54, blob_empty 4,915, su_empty 5,746, su_present 65,503 |
| S2 late-blob exposure | 4,987 |
| S3 (1% sample, 77,166) | best_null 706, su_eq_best 4,952 |
| S4 | denom_flaws 7,611,640, mover_rating_null 32,113, games_with_flaws 1,025,382 |
| S5 | game_flaws 11 GB, games 4,293 MB |
| Go-forward stamped baseline | 0 |
| Sentry (flawchess, last 1h) | no issues |
| Prod disk (owner, `df -h /`) | 87 GB free of 150 GB |

## Deviations

- Live-scoring check deferred (see above).
- Benchmark dry-run from plan 05 not run.

## Follow-ups

- Confirm a live-lane stamp once a non-guest game is analyzed: `select id, full_evals_completed_at, maia_flaws_completed_at from games where full_evals_completed_at > '2026-11-08T20:42:48Z' order by full_evals_completed_at desc limit 5` should show the stamp within seconds of the eval.
- Untested `if blob_map:` guard in `_apply_flaw_blob_submit` (plan 04 mutation note).
