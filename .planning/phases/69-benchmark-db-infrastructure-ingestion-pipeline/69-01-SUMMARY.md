---
phase: 69-benchmark-db-infrastructure-ingestion-pipeline
plan: 01
subsystem: infra
tags: [postgres, docker, alembic, benchmark]

# Dependency graph
requires:
  - phase: dev-db-baseline
    provides: docker-compose.dev.yml + deploy/init-dev-db.sql + bin/reset_db.sh patterns
provides:
  - "Isolated flawchess-benchmark PostgreSQL 18 container on localhost:5433"
  - "deploy/init-benchmark-db.sql with app user + read-only role (SELECT-only)"
  - "bin/benchmark_db.sh lifecycle script (start/stop/reset)"
  - "Benchmark DB URL: postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark"
affects: [69-02 alembic migration, 69-03 mcp wiring, 69-04 ingestion, 69-05 baselines, 69-06 docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-environment compose file + project name + named volume + port + DB name + DB user (5-axis isolation)"
    - "Alembic routed via DATABASE_URL env override to non-default DB"
    - "RO role with SELECT-only + ALTER DEFAULT PRIVILEGES for future tables"

key-files:
  created:
    - docker-compose.benchmark.yml
    - deploy/init-benchmark-db.sql
    - bin/benchmark_db.sh
  modified: []

key-decisions:
  - "5-axis isolation from dev/prod: project name flawchess-benchmark, volume benchmarkpgdata, port 5433, db flawchess_benchmark, app user flawchess_benchmark"
  - "RO role flawchess_benchmark_ro committed with <PASSWORD> placeholder; user rotates locally before MCP wiring in Plan 03"
  - "No flawchess_benchmark_test database — benchmark-only, no test DB needed"
  - "No --yes confirmation prompt on reset (matches bin/reset_db.sh convention)"

patterns-established:
  - "benchmark_db.sh: case start|stop|reset with shared wait_healthy + run_migrations helpers"
  - "DATABASE_URL=$BENCHMARK_DB_URL uv run alembic upgrade head — env override is the routing mechanism"

requirements-completed: [INFRA-01]

# Metrics
duration: ~5min (code) + manual checkpoint resolution
completed: 2026-04-26
---

# Phase 69 Plan 01: Benchmark DB Infrastructure Summary

**Isolated flawchess-benchmark PostgreSQL 18 container on port 5433 with read-only MCP role, Alembic-driven migration, and start/stop/reset lifecycle script — paused at manual verification checkpoint.**

## Status

**COMPLETE.** Tasks 01-01..01-03 committed by the executor. Task 01-04 (manual smoke verification) was run by the user; one finding (RO SELECT default-privileges scoping bug) was fixed during the checkpoint and verified live: container healthy on 5433, alembic_version + canonical tables present, `has_table_privilege(flawchess_benchmark_ro, games, SELECT)=t / INSERT=f`, ports 5432/5433 isolated.

## Performance

- **Duration:** ~5 min code + ~10 min checkpoint round-trip (RO grant fix)
- **Started:** 2026-04-25T20:30:00Z
- **Code tasks completed:** 3
- **Manual checkpoint completed:** 2026-04-26 (with one fix landing during verification)
- **Files created:** 3 (and a follow-up edit to two of them)

## Accomplishments

- `docker-compose.benchmark.yml` defines PostgreSQL 18 service on host port 5433, named volume `benchmarkpgdata`, mounts init SQL, with the same pg_stat_statements + healthcheck setup as dev. Validated with `docker compose config`.
- `deploy/init-benchmark-db.sql` creates `flawchess_benchmark` database, `flawchess_benchmark` app user (full grants), and `flawchess_benchmark_ro` read-only user (CONNECT + USAGE + SELECT only, plus ALTER DEFAULT PRIVILEGES so future tables created by Alembic are auto-readable). No INSERT/UPDATE/DELETE/TRUNCATE grants. Password placeholder `<PASSWORD>` committed deliberately.
- `bin/benchmark_db.sh` (chmod +x) provides `start`/`stop`/`reset` subcommands. `start` brings the container up, waits for `pg_isready`, then runs `DATABASE_URL=$BENCHMARK_DB_URL uv run alembic upgrade head` to migrate the empty DB. `reset` adds `down -v` to wipe the volume first. `bash -n` syntax-clean.

## Task Commits

1. **Task 01-01: Create docker-compose.benchmark.yml** - `eb52b0f` (feat)
2. **Task 01-02: Create deploy/init-benchmark-db.sql** - `78733c6` (feat)
3. **Task 01-03: Create bin/benchmark_db.sh** - `20d6f87` (feat)
4. **Task 01-04: Manual smoke verification** — RAN BY USER 2026-04-26. Step 4 (RO SELECT) initially returned `s=f`; fix landed in this commit (init SQL scoped + `ensure_ro_grants` step in lifecycle script). Re-verified `s=t, i=f` live; SELECT-then-INSERT behavioral probe also confirms read works and write is denied.

## Files Created/Modified

- `docker-compose.benchmark.yml` — PostgreSQL 18 service definition, port 5433, volume `benchmarkpgdata`, init SQL mount.
- `deploy/init-benchmark-db.sql` — DB + app user + RO user creation with SELECT-only privileges.
- `bin/benchmark_db.sh` — start/stop/reset lifecycle script, executable, runs Alembic with `DATABASE_URL` override.

## Decisions Made

None beyond what the plan specified. The plan was prescriptive (exact SQL, exact bash content) and was followed verbatim.

## Deviations from Plan

None at the structural level. One **fix applied during checkpoint verification**:
- The original `init-benchmark-db.sql` set `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ...`. Without `FOR ROLE flawchess_benchmark`, the grant was scoped to the `postgres` session role running the init script. Tables created later by Alembic as `flawchess_benchmark` therefore did not inherit SELECT, and `has_table_privilege('flawchess_benchmark_ro', 'games', 'SELECT')` returned `f` instead of `t`.
- Fix: scoped the `ALTER DEFAULT PRIVILEGES` to `FOR ROLE flawchess_benchmark` (covers both tables and sequences) AND added an idempotent `ensure_ro_grants()` step in `bin/benchmark_db.sh` that runs after every `start`/`reset`. The lifecycle step also retroactively grants SELECT on existing tables, so the user did not need a `reset` to recover. Verified live: `s=t, i=f`, and a behavioral SELECT-then-INSERT probe as `flawchess_benchmark_ro` confirmed read works and write is denied.

## Issues Encountered

- See deviation above (default-privileges scoping bug, fixed at checkpoint).
- One transient verification false-negative during executor self-check: chaining a grep of `'$BENCHMARK_DB_URL'` with `&& ...` in Bash interpreted the variable in the chained command, masking a successful match. Re-running with `grep -F` confirmed the file content was correct. No code change needed; tracking here so future verifiers do not get confused by the same shell-quoting interaction.

## Threat Model Coverage

The plan's STRIDE register has three mitigations all delivered by these three files:

- **T-69-01 Tampering (5-axis isolation):** project name `flawchess-benchmark` (CLI `-p` in script), volume `benchmarkpgdata`, port `5433:5432`, DB `flawchess_benchmark`, user `flawchess_benchmark`. Verifiable by checkpoint step 6.
- **T-69-02 RO privilege escalation:** init SQL grants only CONNECT/USAGE/SELECT. No INSERT/UPDATE/DELETE/TRUNCATE present (negative grep verified). Verifiable by checkpoint step 5.
- **T-69-03 RO password disclosure:** `<PASSWORD>` literal placeholder committed; real password set out-of-band before Plan 03 MCP wiring. CLAUDE.md update lives in Plan 06.

## Next Plan Readiness

Once Task 01-04 verification is approved, Plan 02 (Alembic migration for benchmark schema) can run `DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark uv run alembic upgrade head` against the empty benchmark DB. The interfaces in the plan's `<interfaces>` block are now realized.

## Self-Check: PASSED

- Files exist:
  - FOUND: `docker-compose.benchmark.yml`
  - FOUND: `deploy/init-benchmark-db.sql`
  - FOUND: `bin/benchmark_db.sh` (executable)
- Commits exist on `worktree-agent-a39405691c9a98e50`:
  - FOUND: `eb52b0f` (docker-compose)
  - FOUND: `78733c6` (init SQL)
  - FOUND: `20d6f87` (lifecycle script)
- Compose file validates: `docker compose -f docker-compose.benchmark.yml config` exits 0.
- Bash syntax: `bash -n bin/benchmark_db.sh` exits 0.
- Negative checks: file does NOT contain `devpgdata` or `5432:5432`; init SQL does NOT contain `GRANT (INSERT|UPDATE|DELETE|TRUNCATE).*flawchess_benchmark_ro`.

---
*Phase: 69-benchmark-db-infrastructure-ingestion-pipeline*
*Plan: 01*
*Status: paused at checkpoint Task 01-04 (human-verify)*
*Date: 2026-04-25*
