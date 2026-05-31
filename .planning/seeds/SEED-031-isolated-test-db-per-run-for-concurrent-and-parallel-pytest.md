# SEED-031: Isolated test DB per run — unblock concurrent agent runs and `pytest -n auto`

**Status:** Scheduled — v1.22 Maintenance, Phase 100 (Isolated Test DB Per Run)
**Created:** 2026-05-31
**Source:** Investigation on 2026-05-31 into a slow/"hanging" test run that turned out to be six overlapping `pytest` invocations (multiple agents + a PyCharm coverage run) deadlocking on the shared `flawchess_test` DB.
**Related:** `tests/conftest.py` (`test_engine`, `_truncate_all_tables`, `db_session` fixtures); SEED-022 (import concurrency / Postgres headroom — shares the "concurrent connections vs one Postgres" theme); CLAUDE.md "No dev DB reset in plans" + real-Postgres test policy.

---

## One-liner

All `pytest` runs share the single `flawchess_test` database, and each run begins by taking an `ACCESS EXCLUSIVE` lock on every table (`TRUNCATE … RESTART IDENTITY CASCADE` at session start). The moment two runs overlap they serialize/deadlock and corrupt each other's committed fixtures. Give each run (and each xdist worker) its own database, cloned from a migrated template, so concurrent runs are fully isolated. Same mechanism also unlocks `pytest -n auto` to cut the ~40s suite to roughly 8–15s.

---

## Context

The suite normally runs in ~38–40s. On 2026-05-31 a run appeared to hang for minutes. Root cause was **not** a hung test: six independent `pytest` processes were alive at once (multiple Claude agents, a manual run, and a PyCharm "Run with Coverage" `--cov` run), all pointed at the same dev Postgres. They were serializing on locks.

This is structural, not a flaky test. The design assumes "one suite run at a time." Given the way work increasingly happens here (multiple agents in parallel, IDE coverage runs alongside CLI runs), that assumption no longer holds.

Note on scope/calibration: per-run DB isolation is a **standard** pattern (Django's test runner auto-creates `test_db_gw0/gw1/…`; pytest-django + xdist and Rails `parallelize` do the same), but it is normally adopted to enable **in-run parallelism**, not specifically to support N independent concurrent runs. So this seed is only worth scheduling if (a) concurrent agent runs are going to be a recurring workflow, and/or (b) we want the xdist speedup. If neither, the lighter interim below is enough and this can stay parked.

---

## Problem — two coupled root causes

### 1. Shared database + whole-schema exclusive lock at startup

`tests/conftest.py`:

- `test_engine` (session fixture) runs `alembic upgrade head` against `flawchess_test`, then calls `_truncate_all_tables`.
- `_truncate_all_tables` issues `TRUNCATE TABLE <every public table except alembic_version/openings> RESTART IDENTITY CASCADE`.

`TRUNCATE` takes `ACCESS EXCLUSIVE` — the strongest lock Postgres has, conflicting with even a plain `SELECT`. `CASCADE` over all public tables locks the **entire schema** at once. So while run A truncates, run B cannot read or write anything; and `RESTART IDENTITY` resets sequences out from under any rows run B already committed, breaking B's ID-based assertions.

### 2. A few tests commit outside the rollback scope, with fixed IDs

Most tests use `db_session` (per-test `conn.begin()` … `conn.rollback()`), which is well isolated and cheap. But some deliberately commit on their own connection because the rollback-scoped session can't observe cross-connection writes:

- `fresh_test_user` (own session, commits, deletes on teardown)
- `create_llm_log` (D-02 own-session write path)
- `tests/services/test_eval_drain.py` commits with a fixed `_TEST_USER_ID = 99100`

Across two concurrent runs these collide on primary keys / unique constraints. The startup truncate exists precisely to wipe this committed residue between runs — which is why removing the truncate alone is **not** a fix (it would downgrade "actively hostile / deadlock" to "merely flaky / occasional collision," not to "safe").

The two causes are coupled: true concurrency safety requires each run to own its data. Once it does, the truncate becomes unnecessary (a fresh clone is already empty), so the fix also retires the hostile lock.

---

## Proposed approach (recommended): per-run database cloned from a migrated template

Postgres `CREATE DATABASE … TEMPLATE` is a fast file-level copy (sub-second), so each run gets a private, already-migrated DB without re-running migrations and without any cross-run locking.

1. **One-time / per-session bootstrap of a template.** Maintain a migrated `flawchess_test_template` (run `alembic upgrade head` against it once; refresh when migrations change — e.g. detect head mismatch and re-migrate the template).
2. **Per-run DB in `conftest.py` (`test_engine`).** Derive a unique name and create the DB from the template:
   - Name source, in priority order: explicit env var (`TEST_DB_NAME` / suffix) → `PYTEST_XDIST_WORKER` (`gw0`, `gw1`, …) → process PID. e.g. `flawchess_test_gw0`, `flawchess_test_<pid>`.
   - `CREATE DATABASE flawchess_test_<id> TEMPLATE flawchess_test_template;`
   - Point the session engine + the `settings.TEST_DATABASE_URL` override at that DB (the conftest already swaps `settings.DATABASE_URL` for the session, so the patch point exists).
   - `DROP DATABASE flawchess_test_<id>` at session teardown.
3. **Drop the session-start `TRUNCATE … CASCADE`** — a fresh clone is already clean, so `_truncate_all_tables` and its hostile lock can go away entirely. (Keep the `_TRUNCATE_EXCLUDE` reference-data intent by baking `openings` seed, if any, into the template.)
4. **Stale-DB reaper** for runs killed mid-flight: on create, `DROP DATABASE IF EXISTS` the target name first; optionally a `bin/` helper to drop `flawchess_test_*` older than N hours.

`CREATE/DROP DATABASE` must run on an autocommit connection to `postgres`/`template1`, not inside a transaction — needs a small dedicated psycopg/asyncpg connection in the fixture, separate from the app engine.

### Secondary win: `pytest -n auto`

With per-worker DBs in place, pytest-xdist (`-n auto`) becomes safe. The suite is DB-bound (each test is a Postgres round trip), which parallelizes well. On this dev box (16 logical / 8 physical cores) expect roughly **8–15s** wall time, not the theoretical 40/16 ≈ 2.5s, because: per-worker fixed setup cost is paid 16×, wall time is bound by the slowest worker (stragglers like the 3.5s `test_seed_openings` setup and the 2s `test_eval_drain` call), and hyperthreaded cores give ~20–30% not 2×. Worth measuring rather than trusting the estimate. xdist exposes `PYTEST_XDIST_WORKER` specifically so each worker picks its own DB name — same hook as step 2.

---

## Alternatives considered (and why they lose)

- **Schema-per-run** (distinct `search_path` in one DB): good isolation, but Alembic/models assume `public`; fiddly, and cross-schema `TRUNCATE CASCADE` stays risky.
- **Drop the truncate, go rollback-only everywhere:** doesn't fix the committing fixed-ID fixtures; leaves cross-run flakiness.
- **Advisory lock / queue so runs serialize:** defeats the purpose — agents wait instead of running concurrently.
- **One Docker Postgres per agent (ports 5432/5433/…):** full isolation but wasteful RAM (we already hit OOM territory in prod) and clumsy for N agents.

The template-clone approach is the only one that gives true concurrency **and** keeps a single Postgres instance **and** enables xdist from the same mechanism.

---

## Lighter interim (no source change, if full fix isn't justified yet)

Convention + tiny `bin/` helper: each agent/session exports a distinct `TEST_DATABASE_URL` pointing at a pre-created private DB. The existing conftest then works unchanged (it migrates + truncates that private DB). Zero source changes, solves the deadlock today, but doesn't retire the truncate or unlock xdist. Good stopgap if the pile-up was a one-off.

---

## Open questions

- Template refresh trigger: detect Alembic head drift and re-migrate the template automatically, or make it an explicit `bin/` step?
- Where to create/drop DBs from in tests — a dedicated asyncpg autocommit connection in the session fixture vs a `bin/` pre/post hook driven by env var?
- Does the benchmark suite (`tests/scripts/benchmarks`, already `--ignore`d by default) need the same treatment, or is it run rarely enough to leave shared?
- Should CI adopt `-n auto` too, or keep CI serial (deterministic ordering) and only parallelize locally?

---

## Acceptance criteria sketch

- Two (or more) full `pytest` runs can execute simultaneously against the dev Postgres with zero deadlocks and zero cross-run data corruption.
- Session-start `TRUNCATE … RESTART IDENTITY CASCADE` removed; per-run DB created from a migrated template and dropped at teardown; killed runs self-heal (drop-if-exists on next create).
- `pytest -n auto` runs green and measurably faster than serial (record the actual number).
- ruff / ty / pytest all green; no behavior change to individual tests.

---

## Recommendation

LOW urgency, HIGH clarity. The full fix is ~30–50 lines of `conftest.py` plumbing plus a template bootstrap, with the existing suite as the safety net. Schedule as a single self-contained phase **if** parallel agent runs become a normal workflow or we want the xdist speedup; otherwise take the no-code interim and leave this parked. Not to be planned without explicit go-ahead.
