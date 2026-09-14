---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 08
subsystem: deployment
tags: [opening-cache, two-source-confirmation, release, alembic, production]

# Dependency graph
requires:
  - phase: 220-07
    provides: "Release-2 migration, candidate/promote/replace write path, confirmed-only reads, demote path; dev-measured marking walk ~1.3s over 82,586 rows"
  - phase: 220-06
    provides: "Prod repair complete; audit totals 2,192,195 screened_clean + 19,576 confirmed_clean + 4,097 repaired = 2,215,868"
provides:
  - "Production running two-source confirmation (origin/production = 6110d8631, verified server SHA) with every post-repair audit row marked confirmed (2,215,868) and 5,537 candidates"
  - "Real prod marking-walk duration on record: ~47s for 2.57M rows (dev estimate scaled 31x: ~40s)"
  - "Benchmark-lane cache growth evidence: 0 (2026-09-09) -> 9,681 (2026-09-11 13:20Z) -> 42,921 (2026-09-11 19:53Z)"
  - "First disagreement reading: disagreements >= 1 and >= 2 both 0 at 2026-09-11 19:53Z (post-deploy, no live writes yet)"
affects: []

# Actuals (#2632)
actuals:
  tokens: 12000
  tasks: 3
  commits: 2
  plan_head_before: 56c6e4f02

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - .planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-08-SUMMARY.md
  modified:
    - CHANGELOG.md

key-decisions:
  - "Release 2 shipped as one squash commit on main (9157af791) after the full seven-command pre-merge gate: ruff format (0 changes), ruff check clean, ty app/tests/scripts clean, ty analysis clean, function-size gate 1041 functions no breaches, pytest 4612 passed / 19 skipped, eslint clean, vitest 259 files / 4022 tests passed."
  - "Changelog: one chore-level `### Changed` line under `## [Unreleased]`; the user-facing bullet stays Release 1's flaw-count correction (CACHEFIX-11)."
  - "Deploy decision taken by the operator in-session (2026-09-11) with the expected downtime stated up front (~1-2 min); real Alembic step was ~47s."
  - "Task 3 step 4 (the few-days-later disagreement reading and Sentry check) is deliberately left as a follow-up; the day-0 reading is 0 / 0 and is recorded below with its timestamp."

patterns-established: []

requirements-completed: [CACHEFIX-08, CACHEFIX-11]

coverage:
  - id: D1
    description: "Full pre-merge gate green immediately before the Release 2 squash-merge, main == origin/main afterwards"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "seven-command gate run 2026-09-11 ~17:40Z; `git rev-list --left-right --count main...origin/main` = 0 0; RELEASE2-MERGED-OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "origin/production carries Release 2 and the verified server SHA matches"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "bin/deploy.sh run 34640161694 on production@6110d8631; 'Production is at 6110d863'; forward-port pushed (65f58276c)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Prod confirmed population equals the post-repair audit total and no confirmed row has n_sources < 2"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "prod query 2026-09-11 19:53Z: confirmed=true 2,215,868 (audit post-repair 2,215,868); confirmed AND n_sources<2 = 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Benchmark DB opening_position_eval is growing from its 0-row baseline"
    requirement: CACHEFIX-08
    verification:
      - kind: integration
        ref: "localhost:5433 count 42,921 at 2026-09-11 19:53Z (0 on 2026-09-09; 9,681 at 13:20Z)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Changelog carries the Release 2 entry alongside the Release 1 user-facing bullet"
    requirement: CACHEFIX-11
    verification:
      - kind: unit
        ref: "grep -c '^## \\[Unreleased\\]' CHANGELOG.md = 1; Changed line present"
        status: pass
    human_judgment: false

# Metrics
duration: ~2h15m (17:40Z gate start to 19:55Z verification)
completed: 2026-09-11
---

# Phase 220 Plan 08: Ship Release 2 Summary

**Two-source confirmation is live on production: 2,215,868 cache rows confirmed straight from the repair's audit trail, 5,537 candidates, zero self-confirmed rows, and the benchmark lane caching openings for the first time (42,921 rows from a 0 baseline).**

## Performance

- **Duration:** ~2h15m wall clock, most of it CI (7m20s PR run + ~11 min deploy run) and the full local gate.
- **Tasks:** 3 (1 auto, 2 human-action checkpoints run by the orchestrator with the operator's go-ahead)

## Accomplishments

- Chore-level changelog line for Release 2 under `## [Unreleased]`.
- Full CLAUDE.md pre-merge gate green as one run, then Release 2 squash-merged into `main` as `9157af791`, phase branch deleted, `main == origin/main`.
- Release PR #357 (`main -> production`) opened, CI green, squash-merged as `6110d8631`; `bin/deploy.sh` run 34640161694 converged, server verified at `6110d863`, forward-port pushed to `main` (`65f58276c`).
- Post-deploy verification through the prod tunnel and against the benchmark DB (below).

## Pre-merge gate

| Step | Result |
|---|---|
| `uv run ruff format app/ tests/ scripts/ analysis/` | 478 files unchanged |
| `uv run ruff check . --fix` | All checks passed |
| `uv run ty check app/ tests/ scripts/` | All checks passed |
| `uv run --project analysis --with ty ty check analysis/` | All checks passed |
| `scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` | 1041 functions, no breaches |
| `uv run pytest -n auto -x` | 4612 passed, 19 skipped (55.9s) |
| `npm run lint && npm test -- --run` (frontend) | eslint clean; 259 files / 4022 tests passed |

## Release and deploy

| Item | Value |
|---|---|
| Release 2 squash commit on `main` | `9157af791` |
| Release PR | #357, CI run 34639409319 (test 7m20s, green) |
| `origin/production` | `6110d8631 Release: two-source confirmation for the opening eval cache (Phase 220 Release 2) (#357)` |
| Deploy run | 34640161694, `workflow_dispatch` on `production@6110d8631`, success |
| Verified server SHA | `6110d863` (matches `git rev-parse origin/production`) |
| Forward-port | `65f58276c` pushed to `main` by `bin/deploy.sh` |
| Liveness | `https://flawchess.com/` HTTP 200 in 0.093s; backend/caddy up, db healthy |

### Marking-walk duration (T-220-16)

| | Rows | Wall clock |
|---|---|---|
| Dev (220-07) | 82,586 cache / 106,615 audit | ~1.3s for the whole `alembic upgrade head` |
| Dev estimate scaled 31x | 2.57M | ~40s |
| **Prod (actual)** | 2,221,405 cache / post-repair audit 2,215,868 | **~47s**: `Running upgrade a1c2e3f40001 -> b7d4f5a60002` logged at 19:51:22.9Z, `Waiting for application startup` at 19:52:10.1Z (upper bound; includes the ALTER TABLE and app import) |

The migration runs in one transaction, so `opening_position_eval` was read-locked for those ~47s, inside the normal container restart window.

## Post-deploy verification (Task 3)

All queries read-only, taken 2026-09-11 19:53Z unless stated.

1. **Confirmed split on prod**
   `SELECT confirmed, count(*) ... GROUP BY confirmed` -> `false: 5,537 (n_sources 1..1)`, `true: 2,215,868 (n_sources 2..2)`.
   Audit total `screened_clean 2,192,195 + confirmed_clean 19,576 + repaired 4,097 = 2,215,868` (220-06-SUMMARY). **Exact match.** The 5,537 candidates are rows written after the audit seed (by design; `engine_version` is NULL everywhere because no Release-2 write had landed yet).
2. **Self-promotion sanity**
   `SELECT count(*) ... WHERE confirmed AND n_sources < 2` -> **0**.
3. **Benchmark lane (CACHEFIX-12 Q11/Q12)**
   `localhost:5433` `SELECT count(*) FROM opening_position_eval` -> **42,921** (baseline 0 on 2026-09-09 per 220-02-SUMMARY; 9,681 at 13:20Z per 220-06-SUMMARY). The submit-path cache write is firing in the remote-only lane and the count keeps growing. The "leased cached game carries fewer engine targets" assertion is not directly observable read-only (lease targets are not persisted); it is covered by the `confirmed_only` lease-omit tests in `tests/test_eval_worker_endpoints.py` and by the count growth itself.
4. **Disagreement watch (day 0)**
   `disagreements >= 1` -> **0**, `disagreements >= 2` -> **0** (2026-09-11 19:53Z). No live Release-2 write had happened yet (`candidates_last_15m = 0`, `live_promotions_last_15m = 0`). The few-days-later reading and the Sentry `source=opening-cache` check remain a follow-up.
5. **No benchmark regeneration**
   `git log --oneline -40 -- reports/benchmark/ analysis/`: only `analysis/tilt_study` docs commits since 2026-09-08; `reports/benchmark/` last touched 2026-08-18. No `gen_benchmarks` run, no benchmark DB re-clone in this phase.

## Task Commits

1. **Task 1: changelog + gate + squash-merge** — `576094099` (changelog line, on the phase branch), squashed into `9157af791` on `main`
2. **Task 2: deploy** — no repo commit; `6110d8631` on `production`, forward-port `65f58276c` on `main`
3. **Task 3: verification** — this SUMMARY

## Files Created/Modified

- `CHANGELOG.md` — one `### Changed` line for Release 2
- `.planning/phases/220-opening-eval-cache-repair-two-source-confirmation/220-08-SUMMARY.md`

## Decisions Made

See `key-decisions` in the frontmatter.

## Deviations from Plan

- The two `checkpoint:human-action` tasks were executed by the orchestrator after the operator's explicit "Deploy now" (the decision that needed a human), rather than handed back as manual steps.
- Task 3 step 4's few-days-later reading is a follow-up, not done here (it cannot be, by construction).

## Issues Encountered

- A concurrent session committed `docs(tilt)` (`4f3e8f2bc`) directly to local `main` while this phase ran on its branch; the working tree already matched that commit byte-for-byte, so the checkout back to `main` was done by stashing and dropping the identical copy. No content was lost; the squash-merge landed on top of it.
- `gh pr merge` printed nothing, but `origin/production` advanced correctly; verified by `git fetch` + `git log`.

## User Setup Required

- **Benchmark-lane backend (`uvicorn ... --port 8001`, started 2026-09-11 13:33 on Release 1 code) must not be restarted on the current working tree until the benchmark DB is migrated.** Its Alembic head is `e55d2651a373`; Release 2's write path expects the seven provenance columns. Run `bin/benchmark_db.sh start` (idempotent, applies migrations) before the next restart of that process. The marking walk will confirm nothing there (its `opening_cache_audit` is empty), so every benchmark cache row starts as a candidate and confirms through live two-source agreement.
- In a few days: re-run `SELECT count(*) FROM opening_position_eval WHERE disagreements >= 1` / `>= 2` on prod and check Sentry for the `source=opening-cache` message. A growing `>= 2` population is a new seed (D-12), not a tolerance.

## Next Phase Readiness

Phase 220 is fully shipped: Release 1 (repair pipeline) and Release 2 (two-source confirmation) are both on production, the confirmed population is provably the repair's own audit trail, and the benchmark lane has opening dedup for the first time. Open follow-ups: the disagreement watch above, the benchmark DB migration before the lane's next restart, and the deferred post-hardening re-audit mode (CONTEXT deferred idea).

## Self-Check: PASSED

- `origin/production` = `6110d8631` (Release 2), verified server SHA `6110d863`.
- Prod: confirmed 2,215,868 == audit 2,215,868; confirmed with n_sources<2 == 0.
- Benchmark DB: 42,921 rows (baseline 0).
- `CHANGELOG.md` has exactly one `## [Unreleased]` heading with the Release 2 line.
- `git log -- reports/benchmark/ analysis/` shows no regeneration commit.
