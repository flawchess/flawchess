---
slug: insights-diskfull-shm
status: awaiting_human_verify
trigger: |
  After importing 40k games for user 95 in prod, going to https://flawchess.com/openings/insights
  shows "Something went wrong." Sentry FLAWCHESS-6K (issue 128366391):
  asyncpg.exceptions.DiskFullError: could not resize shared memory segment to 16777216 bytes:
  No space left on device, at /api/insights/openings. Possibly-related FLAWCHESS-6G (issue 128345511):
  N+1 query at /api/eval/remote/entry-submit (user thought it was fixed).
created: 2026-06-16
updated: 2026-06-16
---

# Debug Session: insights-diskfull-shm

## Symptoms

- **Expected:** GET/POST /api/insights/openings returns opening insights for user 95.
- **Actual:** Frontend shows "Something went wrong." API 500s.
- **Error (FLAWCHESS-6K, primary):**
  `sqlalchemy ... asyncpg.exceptions.DiskFullError: could not resize shared memory segment`
  `"/PostgreSQL.793728662" to 16777216 bytes: No space left on device`
  - `handled: yes`, occurrences 5, users impacted 0, first/last seen 2026-06-16 17:44–17:52 UTC.
  - Raised at `app/repositories/openings_repository.py:709` (`await session.execute(stmt)`)
    inside `query_opening_transitions`, called from
    `app/services/opening_insights_service.py:581` `_collect_attribution_hashes`,
    from `compute_insights` (line 972).
  - The failing SQL is a heavy aggregate over `game_positions JOIN games`:
    `count(distinct(games.id))` plus several `FILTER` clauses, `GROUP BY full_hash, move_san`,
    `ply BETWEEN 0 AND 16`, `user_id = 95`. Request: color=all, opponent_type=human, no other filters.
- **Error (FLAWCHESS-6G, secondary / likely separate):**
  N+1 query (performance issue, not an exception) at `/api/eval/remote/entry-submit`,
  `SELECT game_positions.* WHERE game_id = $1 AND user_id = $2 ORDER BY ply`, 54 occurrences,
  http 200, source `eval_drain`. User believed this was already fixed.
- **Timeline:** Started right after importing 40k games for user 95 (large dataset). New in prod 2026-06-16.
- **Repro:** Import ~40k games for a user, open /openings/insights.

## Current Focus

- **hypothesis:** CONFIRMED. "No space left on device" is NOT real disk exhaustion. 16777216 = 16 MB;
  the segment `/PostgreSQL.xxxx` is a Postgres dynamic-shared-memory (DSM) segment in the container's
  `/dev/shm`. Docker defaults `/dev/shm` to 64 MB. A parallel hash-aggregate over user 95's ~40k
  games × many positions spawns multiple parallel workers, each requesting a 16 MB DSM segment;
  total exceeds 64 MB and the resize fails.
- **fix:** Added `shm_size: "256m"` to the `db` service in `docker-compose.yml`. Requires a prod
  restart to take effect (db container restart sufficient; `docker compose restart db`). Chosen over
  `dynamic_shared_memory_type=mmap` (would incur perf cost on all parallel queries) and over capping
  `max_parallel_workers_per_gather` (would degrade query performance for large datasets legitimately
  needing parallelism).
- **next_action:** user to deploy / restart db container in prod and confirm /openings/insights loads.

## Evidence

- timestamp: 2026-06-16T18:xx UTC
  checked: Sentry FLAWCHESS-6K stacktrace
  found: DiskFullError on segment name "/PostgreSQL.793728662" — that prefix is the Postgres posix
    DSM naming convention. Raised at openings_repository.py:709 inside query_opening_transitions
    on a COUNT(DISTINCT) × 4 FILTER + GROUP BY full_hash,move_san JOIN query at 40k-game scale.
    16777216 bytes = 16 MB = exactly one Postgres DSM segment unit.
  implication: Postgres is trying to grow /dev/shm by 16 MB and failing. This is a parallel
    worker DSM allocation, not real disk space.

- timestamp: 2026-06-16
  checked: docker-compose.yml db service
  found: NO shm_size key present. Docker default 64 MB /dev/shm applies.
  implication: 4 parallel workers × 16 MB = 64 MB would exactly exhaust the limit.
    5 workers = 80 MB → first resize fails. Confirmed no override in place.

- timestamp: 2026-06-16
  checked: docker-compose.yml db command: block
  found: No dynamic_shared_memory_type setting (defaults to 'posix' → uses /dev/shm).
    No max_parallel_workers_per_gather setting (defaults to 2; Postgres may use more
    workers depending on cost estimates at 40k-game scale).
  implication: Parallel plans fully enabled, DSM goes to /dev/shm. No override to soften this.

- timestamp: 2026-06-16
  checked: query_opening_transitions SQL (openings_repository.py lines 641-710)
  found: Heavy aggregate: COUNT(DISTINCT game_id) with 4 FILTER clauses (win/draw/loss/n),
    func.min(ARRAY[ply, game_id]), func.max(played_at), GROUP BY full_hash+move_san,
    JOIN game_positions → games, WHERE ply BETWEEN 0 AND 16 AND user_id=95.
    At ~40k games this JOIN produces hundreds of thousands of rows, driving the planner
    into a parallel hash-aggregate plan.
  implication: Workload is exactly what triggers parallel plans. Error only appeared after
    user 95 hit ~40k games — consistent with dataset crossing the planner's parallelism
    cost threshold.

## Eliminated

- hypothesis: Real disk space exhaustion on the prod NVMe.
  evidence: Error segment name "/PostgreSQL.793728662" is a Postgres posix DSM segment in
    /dev/shm, not a filesystem path. 16 MB resize request is a DSM segment allocation unit.
    Prod is on a 160 GB NVMe and Postgres would report a different error for real disk full.
  timestamp: 2026-06-16

## Resolution

root_cause: |
  Docker's default 64 MB /dev/shm is exhausted by Postgres parallel hash-aggregate workers
  when executing query_opening_transitions for user 95's ~40k games. Each parallel worker
  allocates a 16 MB posix DSM segment in /dev/shm; enough workers are spawned to exceed
  the 64 MB cap, causing asyncpg.DiskFullError on the segment resize. This is NOT a real
  disk-full condition.

fix: |
  Added `shm_size: "256m"` to the `db` service in docker-compose.yml (above mem_limit).
  256 MB gives 16 parallel workers of /dev/shm headroom and is well within the 12 GB
  mem_limit. Does not touch shared_buffers, work_mem, or effective_cache_size (all
  OOM-sensitive per historical record). Requires db container restart in prod.

verification: awaiting user confirmation that /openings/insights loads for user 95 post-restart.

files_changed:
  - docker-compose.yml (added shm_size: "256m" to db service with explanatory comment)
