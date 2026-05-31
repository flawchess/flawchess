---
id: SEED-027
status: Thread A shipped via hotfix PR #144 + deploy (2026-05-26, production at commit 65511c97); Thread B remains planted
planted: 2026-05-26
thread_a_shipped: 2026-05-26 — PR #144 merged into `production`, `bin/deploy.sh` run, prod server verified at SHA 65511c9. Postgres on prod confirmed live with `shared_buffers=2GB`, `effective_cache_size=8GB`, container `mem_limit=12g`. Forward-port merge to `main` at commit `db2732e6` (CHANGELOG.md [Unreleased]/Fixed entry, docker-compose.yml, uv.lock — also bumped `starlette` 0.52.1 → 1.1.0 in the same hotfix to clear PYSEC-2026-161 surfaced by CI pip-audit). The 3-way merge into main had a subtle trap on `shared_buffers`: production went 2GB → 4GB (PR #139) → 2GB (PR #144), main went 2GB → 4GB; git's auto-resolution silently kept main's 4GB and required manual override via `git checkout origin/production -- docker-compose.yml`. Worth remembering for future hotfix forward-ports against values that ping-ponged.
planted_during: Post-mortem of user 109's dual-platform import failure at 14:18-14:24 UTC on 2026-05-26. Both jobs (chess.com `0bec4048…`, lichess `9bbcf242…`) crashed simultaneously at 14:23:58 with `asyncpg ConnectionDoesNotExistError`. `dmesg` on prod confirmed Postgres OOM-killed inside its Docker memory cgroup (memcg constraint, not host OOM): `shmem-rss=4267956kB` (= shared_buffers) + per-backend anon-rss exceeded the 10 GB container `mem_limit`. Sentry issue FLAWCHESS-3Q fired again on canary endpoints during the ~3 s Postgres restart. This is the third post-v1.18 occurrence of the same OOM family (2026-05-16 FLAWCHESS-56, 2026-05-21 FLAWCHESS-3Q hotfix PR #139, 2026-05-26 user 109) — v1.18's hotfix tightened pool size and added container caps but left Postgres tuned for a 16 GB host while the container is capped at 10 GB.
scope: Thread A — config-only hotfix, branched off `production`, PR #144 (2026-05-26). Thread B — small standalone phase off `main`, switch `bulk_insert_positions` from parameterized INSERT to asyncpg `copy_records_to_table` to cut per-backend memory pressure during the heaviest import workload. Threads split because Thread A is a clean 4-line YAML hotfix with no conflict surface against v1.19 work, while Thread B touches `app/repositories/game_repository.py` and `app/services/import_service.py` — both modified by Phase 94.2 on `main` — and therefore cannot ride the hotfix path.
priority: high — stability fix, third recurrence of the same failure mode, dual-platform imports for any user with 5k+ games are a coin flip today
references:
  - CLAUDE.md § "Production Server" (OOM history table)
  - docker-compose.yml § db service (current mem_limit=10g, shared_buffers=4GB, effective_cache_size=12GB, max_connections=30)
  - app/repositories/game_repository.py:161 (bulk_insert_positions — the heaviest INSERT path in the import pipeline)
  - app/services/import_service.py:680 (caller, runs inside the hot lane after Phase 91)
  - reports/phase91-import-stress-test-2026-05-21.md (baseline throughput numbers; the 11 g/s figure assumes single-platform)
  - PR #139 (2026-05-21 hotfix that established current container limits)
---

# SEED-027: Right-size Postgres to its container, and COPY-bulk-insert positions

## One-line summary

The Postgres container is configured as if it owns the 16 GB host (`shared_buffers=4GB`, `effective_cache_size=12GB`) but is actually capped at 10 GB by `mem_limit`. With 4 GB locked in shared buffers, only ~6 GB is left for per-backend work — and concurrent dual-platform imports exhaust it. Fix the memory budget (raise container limit, lower `shared_buffers`, align `effective_cache_size`) and reduce the per-backend cost of the hottest INSERT path (`game_positions`) by switching to asyncpg `COPY`.

## Why this matters (the incident)

User 109 (`GmAhmedAli` on chess.com / `PhAhmedAlssiad` on lichess) started two concurrent imports at 14:18 UTC on 2026-05-26. Both crashed at 14:23:58 with `asyncpg.ConnectionDoesNotExistError: connection was closed in the middle of operation`. The failing query in the lichess error_message was the bulk `INSERT INTO game_positions (...)` from the import hot lane. `dmesg` from the prod host:

```
[Tue May 26 14:23:58 2026] postgres invoked oom-killer
[Tue May 26 14:23:58 2026] oom-kill:constraint=CONSTRAINT_MEMCG,
   oom_memcg=/system.slice/docker-c09a85d1….scope, task=postgres
[Tue May 26 14:23:58 2026] Memory cgroup out of memory:
   Killed process 10816 (postgres) total-vm:5267240kB,
   shmem-rss:4267956kB, anon-rss:538784kB
```

The constraint is `CONSTRAINT_MEMCG` — the DB container's 10 GB cgroup cap was hit. Host had 8.4 GB free at the time of inspection (and ~similar at incident time given idle traffic). FLAWCHESS-3Q picked up the canary failures on `/api/imports/eval-coverage` and `/api/users/me/profile` at 14:23:59–14:24:01 during the ~3 s Postgres auto-recovery.

This is the same failure mode as 2026-05-16 (FLAWCHESS-56) and 2026-05-21 (FLAWCHESS-3Q, PR #139). v1.18 was the "Import Pipeline Hardening" milestone yet two more occurrences shipped after it.

## Why v1.18 did not fix it

v1.18's PR #139 hotfix took the right shape on the *connection* axis (SQLAlchemy pool 10+10, `max_connections=30`) and added container caps (`mem_limit=10g`, `memswap_limit=10g` to disable in-container swap). But it kept the Postgres memory settings that were tuned for the host, not the container:

| Setting | Value | Notes |
|---|---|---|
| `mem_limit` (container) | 10 GB | hard cap — what the cgroup enforces |
| `shared_buffers` | **4 GB** | locked shmem — 40% of container budget gone before any query runs |
| `effective_cache_size` | **12 GB** | larger than the entire container; the planner thinks it has more memory than exists |
| `work_mem` | 16 MB × 30 conns ≈ 480 MB worst case | fine |
| `maintenance_work_mem` | 512 MB × 3 autovacuum workers ≈ 1.5 GB | fine |

Effective budget for all backend anon-rss + WAL buffers + temp files + page cache after `shared_buffers`: ~6 GB. Phase 91's two-lane split made each import lighter per-batch, but dual-platform doubles the concurrent backend count again, and `bulk_insert_positions` is the heaviest INSERT in the system (up to 1700 rows × 19 columns per stmt, called repeatedly per batch). Twenty active backends × ~300 MB anon during bulk INSERT bursts is enough to blow 6 GB.

## Scope

Two threads, both in a single phase. Threading them together because the verification (a dual-platform stress test like Phase 91's, but at higher game-count) measures the combined effect.

### Thread A — Right-size Postgres to its container, and raise the container

The exact numbers should be settled in `/gsd-discuss-phase`, but the shape:

| Setting | Current | Target (proposal) | Rationale |
|---|---|---|---|
| db `mem_limit` / `memswap_limit` | 10 GB / 10 GB | **12 GB / 12 GB** | Host has 8.4 GB free with backend at 2 GB / 4 GB cap. Leaves backend container at 4 GB, db at 12 GB, caddy/umami at ~0.5 GB, host overhead ~1 GB → ~17.5 GB on a 16 GB box (over) — so we need to also trim somewhere, or accept that the db container's headroom only materializes when backend isn't at its cap. Real headroom audit goes in the discuss phase. |
| `shared_buffers` | 4 GB | **2 GB** | 25%-of-container heuristic against a 12 GB container = 3 GB; 2 GB is more conservative and gives us 10 GB of headroom for the backend processes. The page cache on the host (effective_cache_size territory) is what actually keeps reads fast, not shared_buffers, on a write-heavy import workload. |
| `effective_cache_size` | 12 GB | **8 GB** | Must be ≤ what the container can actually access. Tells the planner "you have ~8 GB of OS page cache available" — true under the new mem_limit. |
| `work_mem` | 16 MB | unchanged (16 MB) | 30 conns × 16 MB = 480 MB worst case is fine in the new envelope. |
| `maintenance_work_mem` | 512 MB | unchanged (512 MB) | 3 autovacuum workers × 512 MB = 1.5 GB worst case is fine. |
| `max_connections` | 30 | unchanged (30) | Already aligned with SQLAlchemy pool (10 + 10 per uvicorn proc) + headroom for psql/migrations/monitoring. |

**Open question for the discuss phase:** does `shared_buffers=2GB` measurably hurt read latency on the analytics queries (opening explorer, endgame stats)? Expected answer: no, because PG hits the OS page cache for hot data and the analytics workload is dominated by indexed lookups on `game_positions(full_hash)` / `game_positions(white_hash)` / `game_positions(black_hash)` rather than sequential scans. Worth verifying with `pg_stat_statements` from the prod read-only tunnel before/after.

**Comment update**: the `docker-compose.yml` block above the db service has a comment saying "shared_buffers ~25% of RAM, effective_cache_size ~75% per standard tuning" — that's true for the *host* but wrong for the *container*. Update the comment to make the container-vs-host distinction explicit, so the next reader doesn't re-introduce the bug.

### Thread B — Switch `bulk_insert_positions` to asyncpg COPY

Current implementation at `app/repositories/game_repository.py:161`:

```python
async def bulk_insert_positions(session: AsyncSession, position_rows: list[dict]) -> None:
    chunk_size = 1700  # asyncpg's 32767 param ceiling / 19 columns
    for i in range(0, len(position_rows), chunk_size):
        chunk = position_rows[i : i + chunk_size]
        stmt = insert(GamePosition).values(chunk)
        await session.execute(stmt)
    await session.flush()
```

Every row's columns become individual bound parameters. For a 1700-row chunk that's ~32k parameters, each materialized in the Postgres backend's parser/executor memory. Multiple concurrent batches across two platforms multiply this.

Switch to asyncpg's `Connection.copy_records_to_table` (binary COPY protocol). It:
- streams rows through the wire as a binary blob, no per-column parameter binding,
- eliminates the 32k-param ceiling (so chunking is for asyncio yield points, not protocol limits),
- is the documented fastest path for bulk insert in asyncpg,
- runs in roughly constant per-backend memory regardless of batch size.

Implementation notes:
- Get the raw asyncpg connection via `session.connection().get_raw_connection().connection` (SQLAlchemy async wrapper → asyncpg `Connection`).
- Match column order exactly to `GamePosition.__table__.columns`, including nullable columns (`eval_cp`, `eval_mate`, `endgame_class`, `piece_count`, …) — pass `None` for missing.
- Wrap the COPY in the existing session transaction. asyncpg's COPY participates in the active transaction, so atomicity vs `bulk_insert_games` is preserved.
- Keep `bulk_insert_games` on `pg_insert(...).values(...)` because it uses `ON CONFLICT DO NOTHING` for deduplication, which COPY can't express. Only positions move to COPY.

Expected wins:
- Lower per-backend anon-rss during the burst (the proximate cause of the OOM).
- Faster bulk insert wall-clock (asyncpg benchmarks typically show 3–10× for COPY vs INSERT-with-values on 1k+ row batches).
- Smaller blast radius if a future regression re-introduces memory pressure — the heaviest INSERT path becomes the lightest.

## Out of scope

- Per-user concurrent-platform serialization (was point 2 in the post-mortem). Deferred to a separate SEED if Thread A + B don't fully eliminate the failure under dual-platform stress; the simpler memory fix may make serialization unnecessary.
- Switching `bulk_insert_games` to COPY (loses `ON CONFLICT DO NOTHING`).
- Replacing the orphan-job reaper or DB-recovery retry — both shipped in Phase 90 and are working as designed (the failed jobs *are* marked failed; the issue is they failed at all).
- Stockfish pool sizing — the cold-drain lane was not the trigger this time (the failing SQL was the position INSERT, not an `evals_completed_at` UPDATE; the chess.com job did fail on an `evals_completed_at` UPDATE but that's the same Postgres crash, not a separate eval-lane issue).

## Verification plan (for the phase)

1. Dual-platform stress test mirroring Phase 91's setup: pick a known multi-platform user with 7k+ games (or replay user 109's import locally against a seeded dev DB). Run chess.com + lichess imports concurrently. Capture host + container memory via `docker stats` at 5 s intervals and Postgres backend count via `pg_stat_activity`.
2. Acceptance: peak `flawchess-db-1` memory stays under 9 GB (75% of new 12 GB cap), peak backend anon-rss per connection stays under 200 MB, no `ConnectionDoesNotExistError` in either job's error_message.
3. Read-latency sanity check: `pg_stat_statements` top-20 queries before and after `shared_buffers` change on dev (or on prod via read-only tunnel during a quiet window). No regression > 20% on any analytics query mean time.
4. UAT: re-run user 109's dual-platform import on prod after deploy. Both jobs complete `status='completed'` with `games_imported == games_fetched`.

## Open questions for the discuss phase

- Final numbers for `mem_limit` / `shared_buffers` / `effective_cache_size` after the host-headroom audit. The proposal above is a starting point, not a decision.
- Should the COPY path be feature-flagged behind an env var (e.g. `IMPORT_POSITIONS_COPY=1`) for the first deploy so we can roll back without a code revert if it surfaces an asyncpg edge case? Argument for: the bulk-insert path is on the critical path for every import. Argument against: feature flags rot, and the rollback is one revert away anyway.
- Do we want to add a memory-pressure alert in Sentry or Grafana (peak `flawchess-db-1` cgroup memory > 80% of `mem_limit` for > 60 s) so the next near-miss surfaces before it becomes a crash? Probably yes, but might belong to a separate observability SEED.

## Why this is a seed, not a phase yet

Needs `/gsd-discuss-phase` to lock the exact Postgres numbers (Thread A's table is a proposal, not a decision) and to settle the feature-flag question on Thread B. Once those are nailed down it's a small phase — two plans, one verification.
