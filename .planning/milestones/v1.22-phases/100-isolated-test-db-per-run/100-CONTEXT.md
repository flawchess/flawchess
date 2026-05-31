# Phase 100: Isolated Test DB Per Run - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Give each `pytest` run (and each xdist worker) its own database, cloned from a
migrated template via `CREATE DATABASE … TEMPLATE`, so concurrent runs (multiple
agents + IDE coverage) are fully isolated and `pytest -n auto` becomes safe.
Retire the hostile session-start `TRUNCATE … RESTART IDENTITY CASCADE`
whole-schema `ACCESS EXCLUSIVE` lock (a fresh clone is already clean) and add a
stale-DB reaper (drop-if-exists on create) so killed runs self-heal.

The core approach is locked by SEED-031 (the recommended "per-run database cloned
from a migrated template" design). This phase implements that design; discussion
resolved the open questions around it. Scope is the **main suite against dev
Postgres (port 5432) only**.

</domain>

<decisions>
## Implementation Decisions

### Template refresh trigger (Success Criteria #5)
- **D-01:** **Auto-refresh the template on Alembic head drift**, guarded by a
  Postgres advisory lock. `conftest` compares the live `alembic head` against the
  template's `alembic_version`; on drift it drops + re-migrates
  `flawchess_test_template`. The drop/remigrate path is wrapped in a
  `pg_advisory_lock` (a fixed app-chosen lock key) so that when N runs start
  concurrently, only one performs the refresh and the others block **only on the
  refresh path**, not on every run. After refresh, all runs clone the up-to-date
  template normally (sub-second). Rationale: in multi-agent workflows, "forgot to
  refresh the template" is exactly the papercut to design out; the only cost is
  paying migration time once after each schema change.

### CI parallelism policy
- **D-02:** **Keep CI serial; enable `-n auto` locally only.** The per-worker DB
  mechanism is built regardless, but CI continues to run the suite serially.
  Rationale: the phase goal is local concurrent agent runs; GitHub runners are
  2–4 vCPU where the per-worker bootstrap cost (paid 16× locally) eats most of the
  gain, and a serial production gate keeps failure logs deterministic and
  bisectable. Flipping CI to `-n auto` later is a one-line change once it's
  measured — explicitly deferred, not part of this phase.

### Benchmark suite scope
- **D-03:** **Leave the benchmark suite (`tests/scripts/benchmarks`, port 5433)
  untouched.** Out of scope for per-run cloning. It targets a separate benchmark
  Postgres via the read-only role `flawchess_benchmark_ro` (which lacks
  `CREATE DATABASE` privilege), is already `--ignore`'d from normal runs by
  `addopts`, runs rarely on-demand, and has no shared-mutable-state / TRUNCATE
  deadlock. Bringing it into scope would require privilege changes for no
  isolation benefit.

### Claude's Discretion
- **DB create/drop mechanism** (offered but not selected for discussion): follow
  SEED-031's recommendation — create/drop the per-run DB from a **dedicated
  asyncpg autocommit connection inside `conftest`'s `test_engine` fixture**
  (connecting to `postgres`/`template1`), not a separate `bin/` pre/post hook.
  `CREATE/DROP DATABASE` cannot run inside a transaction, so this needs a small
  dedicated autocommit connection separate from the app engine. Planner/researcher
  may refine the exact plumbing.
- **Per-run DB naming**: SEED-031's priority order is fine — explicit env var
  (`TEST_DB_NAME` / suffix) → `PYTEST_XDIST_WORKER` (`gw0`, `gw1`, …) → process
  PID. e.g. `flawchess_test_gw0`, `flawchess_test_<pid>`.
- **Stale-DB reaper**: `DROP DATABASE IF EXISTS` the target name before each
  create (self-heal for killed runs). An optional `bin/` helper to drop
  `flawchess_test_*` older than N hours is nice-to-have, not required.
- **xdist as a dependency**: `pytest-xdist` is not currently installed; add it as
  a dev dependency to enable `-n auto` locally.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed (locks the approach)
- `.planning/seeds/SEED-031-isolated-test-db-per-run.md` — the recommended design,
  the alternatives considered (and why they lose), the two coupled root causes,
  the open questions resolved above, and the acceptance-criteria sketch. This is
  the primary spec for the phase.

### Current test infrastructure (what's being changed)
- `tests/conftest.py` — `test_engine` (session fixture, runs `alembic upgrade
  head` then `_truncate_all_tables`), `_truncate_all_tables` (the
  `TRUNCATE … RESTART IDENTITY CASCADE` to retire), `override_get_async_session`
  (session-scoped autouse that patches `async_session_maker` everywhere + the
  FastAPI DI override), `db_session` (per-test rollback fixture, unaffected),
  `fresh_test_user` (commits on its own session, deletes on teardown),
  `_TRUNCATE_EXCLUDE` (`alembic_version`, `openings`).
- `tests/services/test_eval_drain.py` §45-82 — commits with fixed
  `_TEST_USER_ID = 99100` / `99101` on its own session. Per-run DB isolation makes
  these fixed IDs safe across concurrent runs (no longer needs the startup
  truncate to wipe residue).
- `app/core/config.py` §14-15 — `DATABASE_URL` (dev, `…/flawchess`) and
  `TEST_DATABASE_URL` (`…/flawchess_test`). conftest already swaps
  `settings.DATABASE_URL = settings.TEST_DATABASE_URL` for the session — that's
  the patch point to redirect at the per-run clone.
- `pyproject.toml` §34-41 — `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`,
  session-scoped loop, `addopts = "--ignore=tests/scripts/benchmarks"`.

### Constraints (from CLAUDE.md)
- "No dev DB reset in plans" memory / CLAUDE.md — plans must not gate completion
  on `bin/reset_db.sh`; design verification against existing dev DB.
- Real-Postgres test policy — no SQLite; asyncpg only.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `settings.DATABASE_URL` swap in `test_engine`: the existing session-scoped
  patch point. Redirect it at the per-run clone name instead of the static
  `TEST_DATABASE_URL`.
- `override_get_async_session` already patches `async_session_maker` across
  `app.core.database`, `app.users`, `app.middleware.last_activity`,
  `app.repositories.llm_log_repository` — the per-run engine flows through this
  unchanged; only the engine's target DB changes.
- Alembic invocation in `test_engine` (`AlembicConfig("alembic.ini")` +
  `alembic_command.upgrade(cfg, "head")`) is reusable for the one-time template
  migration; point its `sqlalchemy.url` at the template DB.

### Established Patterns
- Throwaway-engine-per-loop pattern in `_truncate_all_tables` (asyncpg pools are
  event-loop-bound) is the same constraint the autocommit create/drop connection
  must respect — create + dispose within the session fixture's loop.
- `db_session` rollback isolation is untouched; the only committing fixtures
  (`fresh_test_user`, `test_eval_drain`) become trivially safe under per-run DBs.

### Integration Points
- New autocommit connection to `postgres`/`template1` for `CREATE/DROP DATABASE`
  (cannot run in a transaction).
- `PYTEST_XDIST_WORKER` env var (set by pytest-xdist) → per-run DB name suffix.
- Advisory lock around template drop/remigrate (D-01).

</code_context>

<specifics>
## Specific Ideas

- Record the actual `pytest -n auto` wall-clock number (Success Criteria #3);
  SEED-031 estimates ~8–15s vs the ~38–40s serial suite, but says measure rather
  than trust the estimate.
- Bake the `openings` seed into the template if/when it's populated, preserving
  the `_TRUNCATE_EXCLUDE` reference-data intent without the truncate.

</specifics>

<deferred>
## Deferred Ideas

- **CI `-n auto`** — deferred by D-02. Revisit as a separate measured decision
  once local parallelism is proven; flipping it on is a one-line change.
- **`bin/` reaper for old `flawchess_test_*` DBs by age** — optional nice-to-have
  beyond the drop-if-exists self-heal; not required for the phase.
- **Lighter interim (per-session env var pointing at a pre-created private DB,
  zero source change)** — explicitly NOT taken; SEED-031 documents it as the
  stopgap, but this phase implements the full fix.

</deferred>

---

*Phase: 100-Isolated Test DB Per Run*
*Context gathered: 2026-05-31*
