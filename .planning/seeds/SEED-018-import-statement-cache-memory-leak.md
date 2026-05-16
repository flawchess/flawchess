---
id: SEED-018
status: dormant
planted: 2026-05-16
planted_during: v1.17
trigger_when: before the next milestone after v1.17 — or immediately if any large-scale import runs (benchmark ingest, mass reimport, a >5k-game user). Also whenever the import pipeline, _flush_batch, or run_import session lifecycle is touched.
scope: medium
priority: high
supersedes_premise_of: SEED-017
references:
  - .planning/debug/import-job-db-conn-closed.md
  - .planning/debug/oom-trace-user94-2026-05-16.log
---

# SEED-018: Fix import-pipeline unbounded memory leak (per-batch unique SQL → asyncpg/SQLAlchemy statement-cache growth)

## Why This Matters

This is the **actual root cause** of the 2026-05-16 production OOM-kills (FLAWCHESS-56 / FLAWCHESS-3Q), empirically confirmed by an authorized prod controlled experiment **and** local `tracemalloc` localization. The PR #99/#101 hotfix (`_BATCH_SIZE` 28→12, `_HASH_MB` 64→32, prod swap 4 GB) only slows the bleed — it does not fix the leak. The leak is real, linear, and unbounded; a single import of a ~20k-game account leaks **~10 GB** and OOM-kills prod Postgres **on its own**.

**This corrects SEED-017's premise.** SEED-017 asserts the OOM required a *concurrent/duplicate* import (pool-of-4 × 2 jobs) and that the duplicate-import guard is "load-bearing." That is **disproven**: a single non-concurrent import OOMs alone; concurrency was at most a 2× rate amplifier. The duplicate-guard, resilient failure-recording, and orphan-reaper items in SEED-017 are still worthwhile **resilience** improvements, but they do **not** prevent recurrence — only the fix below does. Recommend re-reading SEED-017 in light of this before actioning it (and demoting its duplicate-guard from "load-bearing" to UX/data-hygiene).

## Confirmed Mechanism

`_flush_batch` Stage 5 (`app/services/import_service.py`, ~lines 538–551) builds, **every batch**, a literal:

```python
case(rows_result.move_counts, value=Game.id)            # one WHEN per game id
case(fen_case_map, value=Game.id, else_=None)           # one WHEN per game with a fen
update(Game).where(Game.id.in_(list(rows_result.move_counts.keys())))
```

The game-id set differs every batch → a **unique SQL text per batch** → SQLAlchemy recompiles (`sqlalchemy/sql/compiler.py:1770`) and asyncpg prepares + caches a **new server-side prepared statement** (`asyncpg/connection.py:481`) each batch. All of it is retained for the **entire import** because `run_import` opens **one** `AsyncSession`/connection at `import_service.py:281` and reuses it for every batch (`expire_on_commit=False`, no per-batch session recycle). Result: unbounded linear memory growth **plus** progressive slowdown (prepare/lookup cost rises each batch).

Secondary contributor: `pg_insert(Game).values(game_rows)` / `insert(GamePosition).values(chunk)` with variable row/chunk counts also vary the statement text (minor; fixed by the same session-recycle).

### Evidence

- **Prod controlled experiment (2026-05-16):** single FaustinoOro chess.com import into disposable guest user 95, stock PR #99 settings. 43 read-only samples / ~7.5 min: Stockfish process count **flat at 4**, Stockfish RSS **flat at 1241 MB**, host mem **+290 MB/min linear** (~0.48 MB/game at 9.7 games/s). Backend restart reclaimed ~3.7 GB instantly → leak is wholly in the import-worker Python heap, freed on process death. Refuted: engine-pool/`_restart_worker` orphan hypothesis; ORM identity-map hypothesis; "single import alone can't OOM."
- **Local tracemalloc (real PGN batches through `_flush_batch`, one long-lived session, no engine pool):** b5→b10 RSS 104→169 MB (~13 MB/batch ≈ ~465 KB/game, matching prod). Top growing frames: `sqlalchemy/sql/compiler.py:1770` (+1947 KB / +6 large objects) and `asyncpg/connection.py:481` (+925 KB). Run timed out at 600 s reaching only b10 — the progressive slowdown is itself a symptom.

## The Fix

**Primary — make the per-batch SQL text invariant.** Replace the literal `case()`+`IN` bulk UPDATE in `_flush_batch` Stage 5 with a bound-parameter `executemany`:

```python
await session.execute(
    update(Game).where(Game.id == bindparam("b_id"))
    .values(move_count=bindparam("mc"), result_fen=bindparam("rf")),
    [ {"b_id": gid, "mc": ..., "rf": ...} for gid in batch ],
)
```

One prepared statement reused across all batches → leak gone, and a throughput win.

**⚠ Critical correctness gotcha — must not regress:** the current code intentionally sets `result_fen` **only for games that have one** (`fen_case_map` excludes `None` result_fens; `case(..., else_=None)`). A naive `executemany` with `result_fen=bindparam("rf")` would write `NULL` for every game lacking a fen — a silent data regression. Preserve the conditional: e.g. **two executemany groups** (one updating `move_count` only; one updating `move_count`+`result_fen` for games with a non-null fen), or a COALESCE/keep-existing approach. Verify both `move_count` and `result_fen` backfill against current behavior.

**Defense-in-depth (can be a separate sub-task, phase-sized — not quick):** scope the `AsyncSession` per batch inside `run_import`'s batch loop (currently one session for the whole import at `import_service.py:281`). Touches job-record creation, the previous-job/`since` lookup, and incremental per-batch progress commits — needs care. Optionally also cap asyncpg `statement_cache_size` via `create_async_engine(connect_args=...)`.

**Regression guard (required — 2× prod outage history):** a test asserting the per-batch UPDATE statement text is invariant across batches (or a tracemalloc/objgraph growth assertion), plus backfill-correctness tests for `move_count` and the `result_fen` `None`-handling. CLAUDE.md requires `pytest` + `ty` + `ruff` green.

## When to Surface

**Trigger:** before the next milestone after v1.17, or immediately if any large-scale import is planned (benchmark ingest, mass reimport, onboarding a >5k-game user), or whenever `_flush_batch` / `run_import` session lifecycle is edited. This is high-priority post-incident debt — it has taken prod down twice.

## Scope Estimate

**Medium.** The primary fix is one function (`_flush_batch` Stage 5) but correctness-sensitive (the `result_fen` split) and needs a regression test → **not `/gsd-fast`**; borderline `/gsd-quick` for the primary rewrite alone *if* the `result_fen` split is explicit and tested, but the production-incident history argues for a proper planned phase (`/gsd-plan-phase`). The defense-in-depth session-recycle is phase-sized, not quick. Plan as one phase with two plans (primary fix + regression guard; optional session-recycle as a third).

## Breadcrumbs

- `app/services/import_service.py` — `_flush_batch` Stage 5 (literal `case()`+`IN` UPDATE, ~538–551); `run_import` single-session scope (~281); the per-batch commit loop
- `app/repositories/game_repository.py` — `bulk_insert_games` (`pg_insert(...).values(list).returning`), `bulk_insert_positions` (`insert(...).values(chunk)`)
- `app/core/database.py` — `async_session_maker = async_sessionmaker(engine, expire_on_commit=False)`; `create_async_engine` (statement-cache connect_args candidate)
- `.planning/debug/import-job-db-conn-closed.md` — `status: diagnosed`; full evidence, eliminated hypotheses, confirmed mechanism, revised fix (supersedes an earlier incorrect root cause in that same note)
- `.planning/debug/oom-trace-user94-2026-05-16.log` — kernel OOM capture from the real incident
- `SEED-017` — related resilience items (failure-recording retry, orphan reaper, duplicate guard); **its OOM-causation premise is superseded by this seed**

## Notes

Diagnosis is complete and proven — this seed is implementation-ready. The hard part (root-causing through three refuted hypotheses, an authorized prod experiment, and tracemalloc localization) is done; what remains is a careful, well-tested code change. Do **not** re-derive the cause; trust the debug note + this seed.
