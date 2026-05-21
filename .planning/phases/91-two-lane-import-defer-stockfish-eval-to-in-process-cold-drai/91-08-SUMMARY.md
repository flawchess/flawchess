---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "08"
subsystem: testing
tags:
  - stress-test
  - instrumentation
  - dev-only
  - memory
  - acceptance-gates

dependency_graph:
  requires:
    - "91-01 (evals_completed_at column)"
    - "91-02 (cold-drain coroutine)"
    - "91-04 (GET /imports/eval-coverage endpoint)"
  provides:
    - "scripts/measure_dual_import_rss.py: Phase 91 dual-import stress-test harness"
    - "logs/.gitkeep: tracked logs/ directory placeholder"
  affects:
    - "ROADMAP Phase 91 verification clause"

tech-stack:
  added: []
  patterns:
    - "Async httpx stress harness with asyncio polling loop"
    - "Prod-safety guard via _is_prod_api_base() refuse-without-flag"
    - "Per-proc RSS measurement via /proc/<pid>/status (Linux native)"
    - "Docker stats parsing for containerised services (Postgres)"

key-files:
  created:
    - scripts/measure_dual_import_rss.py
    - logs/.gitkeep
  modified: []

key-decisions:
  - "Backend RSS measured via /proc/<pid>/status (not docker stats) since dev backend is native uvicorn, not a container"
  - "--backend-pid optional arg: omit if backend RSS measurement not needed"
  - "POSTGRES_CONTAINER_NAME = flawchess-dev-db-1 (only postgres is dockerised in dev)"
  - "Login path POST /api/auth/jwt/login confirmed from FastAPI-Users router include in auth.py"
  - "CSV header matches baseline log semantics: timestamp,rss_mb,pg_anon_mb,swap_used_mb,swap_total_mb,swap_pct,job1_status,job2_status,coverage_pct,coverage_pending"

requirements-completed:
  - "Phase 91 Scope #6 (tests — dev 2x20k stress test instrumentation)"

duration: ~20min
completed: 2026-05-21
---

# Phase 91 Plan 08: Stress-Test Harness Summary

**`scripts/measure_dual_import_rss.py` stress-test harness built: triggers dual 20k-game imports, polls RSS/swap/coverage every 30 s, and gates on Phase 91 ROADMAP acceptance bounds — awaiting operator execution (Task 8.2).**

## Performance

- **Duration:** ~20 min (Task 8.1 only; Task 8.2 is operator-gated, ~30-90 min wall)
- **Started:** 2026-05-21T (execution start)
- **Completed:** 2026-05-21T (partial — Task 8.2 pending)
- **Tasks completed:** 1 of 2 (Task 8.2 is a `checkpoint:human-action`)
- **Files modified:** 2

## Accomplishments

- `scripts/measure_dual_import_rss.py` (521 lines): async stress-test harness that authenticates via FastAPI-Users JWT (`POST /api/auth/jwt/login`), triggers two concurrent imports (`POST /api/imports`), polls docker stats (Postgres container) + `/proc/pid/status` (native uvicorn) + `free -m` (swap) + `GET /api/imports/active` + `GET /api/imports/eval-coverage` every 30 s, writes structured CSV to `logs/import-stress-20k-each-<date>.log`, evaluates five acceptance gates, and exits 0/1.
- `logs/.gitkeep`: tracks the `logs/` directory so operators can drop log files there without a git-ignore issue.
- Prod-safety guard (`--allow-prod` required for any non-localhost API base) addresses T-91-28.
- `--password -` reads from `STRESS_TEST_PASSWORD` env var to avoid plain-text credentials in the process table (T-91-29).

## Task Commits

| Task | Name | Commit | Type |
|------|------|--------|------|
| 8.1 | Build scripts/measure_dual_import_rss.py | 098e612e | feat |
| 8.2 | Operator-gated stress-test execution | PENDING | checkpoint:human-action |

## Files Created/Modified

- `scripts/measure_dual_import_rss.py` — Async stress-test harness with six named constants, CSV polling loop, acceptance gate evaluation, prod-safety guard
- `logs/.gitkeep` — Directory placeholder so `logs/` is tracked in git

## Acceptance Bounds (from ROADMAP)

| Metric | Limit | Constant |
|--------|-------|----------|
| Backend RSS plateau | <= 1,600 MB | `RSS_PLATEAU_MAX_MB` |
| Postgres anon+shmem | <= 1,200 MB | `POSTGRES_MEMORY_MAX_MB` |
| Swap usage | <= 50% | `SWAP_USAGE_MAX_PCT` |
| Both imports | status=completed | — |
| Eval coverage | 100% within 60 min | `DEFAULT_COVERAGE_TIMEOUT_MIN` |

## Verification Checks Passed (Task 8.1)

- `uv run ruff check scripts/measure_dual_import_rss.py` — PASS
- `uv run ty check scripts/measure_dual_import_rss.py` — PASS
- `uv run python scripts/measure_dual_import_rss.py --help` — exits 0, all CLI args shown
- All 6 named constants present (grep count = 22)
- Uses `httpx.AsyncClient` (count = 9 references); zero `requests.get/post` calls
- Prod refusal: `--api-base https://flawchess.com` exits 1 with "refusing" in stderr

## Decisions Made

- Backend in dev is native (not containerised), so RSS is measured via `/proc/<pid>/status` using the optional `--backend-pid` argument rather than `docker stats`. Operators who run the backend in Docker can still use the docker stats path by passing `BACKEND_CONTAINER_NAME` adjustment.
- The `POSTGRES_CONTAINER_NAME` constant is `flawchess-dev-db-1` matching the `docker-compose.dev.yml` project name `flawchess-dev` + service name `db`.
- `asyncio.gather` is used to start the two imports concurrently (not on the same session — CLAUDE.md constraint honoured; these are `httpx` calls, not SQLAlchemy sessions).

## Deviations from Plan

None — plan executed as specified. The docker stats backend-container path in the plan assumed a containerised backend; since dev runs uvicorn natively, added `/proc` fallback. This is an additive enhancement consistent with plan intent and CLAUDE.md correctness requirements.

## Task 8.2 Status: AWAITING OPERATOR ACTION

Task 8.2 is `checkpoint:human-action` with `gate="blocking-human"`. The stress-test execution:
- Resets the dev DB (destructive — requires explicit operator approval per CLAUDE.md)
- Consumes 30-90 min wall time
- Requires a dev user with both chess.com and lichess handles configured

**Operator instructions:** See checkpoint payload below and the plan's `<how-to-verify>` section.

## Stress-Test Execution Results (Task 8.2 — to be filled by operator)

| Field | Value |
|-------|-------|
| Execution date | TBD |
| Exit code | TBD |
| Peak backend RSS | TBD MB |
| Peak Postgres memory | TBD MB |
| Peak swap % | TBD % |
| chess.com import status | TBD |
| lichess import status | TBD |
| Time to 100% coverage | TBD min |
| Postgres survived? | TBD (baseline OOM-killed at T+28 min) |
| Sentry events (source=eval_drain) | TBD |
| Phase 91 PASS/FAIL | TBD |

## Issues Encountered

None during Task 8.1 execution.

## Next Phase Readiness

Script is ready for operator-gated execution. Phase 91 verification is blocked on Task 8.2 outcome:
- Exit code 0 → Phase 91 quantitative goals confirmed; milestone boundary ready.
- Exit code 1 → Gap-closure planning required (`/gsd:plan-phase --gaps`).

---

## Self-Check

- [x] `scripts/measure_dual_import_rss.py` exists: `ls scripts/measure_dual_import_rss.py` confirmed
- [x] `logs/.gitkeep` exists: `ls logs/.gitkeep` confirmed
- [x] Task 8.1 commit 098e612e exists: `git log --oneline | head -1` = `098e612e feat(91-08): add Phase 91 dual-import stress-test harness`
- [x] Task 8.2 NOT attempted (correct: it is `checkpoint:human-action`)

## Self-Check: PASSED

*Phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai*
*Partial completion: 2026-05-21 (Task 8.2 awaiting operator)*
