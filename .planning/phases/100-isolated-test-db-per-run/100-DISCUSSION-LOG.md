# Phase 100: Isolated Test DB Per Run - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 100-isolated-test-db-per-run
**Areas discussed:** Template refresh trigger, CI parallelism policy, Benchmark suite scope

---

## Gray-area selection

Offered four areas; user selected three (Template refresh trigger, CI parallelism
policy, Benchmark suite scope). **DB create/drop mechanism** was offered but not
selected — captured as Claude's discretion (follow SEED-031: dedicated asyncpg
autocommit connection in `conftest`).

---

## Template refresh trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-refresh on drift | conftest compares alembic head vs template version; on drift drops+remigrates the template, guarded by a pg_advisory_lock so concurrent runs serialize only on the refresh path. | ✓ |
| Explicit bin/ step | A `bin/refresh_test_template.sh` run manually after each migration; forgetting it yields stale-schema failures. | |
| Auto-detect + fail-fast | Detect drift and abort with a message telling you to run the bin/ refresh step. | |

**User's choice:** Auto-refresh on drift (advisory-lock guarded).
**Notes:** Resolves Success Criteria #5. Chosen to eliminate the "forgot to refresh
template" papercut in multi-agent workflows; the only cost is paying migration time
once after each schema change, and the advisory lock keeps concurrent runs from
racing on the rare refresh.

---

## CI parallelism policy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep CI serial | Local gets `-n auto`; CI stays serial for deterministic ordering and clean bisectable logs on the production gate. | ✓ |
| Adopt -n auto in CI too | Faster CI, but adds ordering nondeterminism and the per-worker bootstrap may negate gains on 2–4 vCPU runners. | |

**User's choice:** Keep CI serial.
**Notes:** Phase goal is local concurrent agent runs. Per-worker DB mechanism is
built regardless, so enabling CI parallelism later is a one-line, separately-measured
change. Deferred.

---

## Benchmark suite scope

| Option | Description | Selected |
|--------|-------------|----------|
| Leave untouched | Separate read-only DB on 5433, already `--ignore`'d, RO role lacks CREATE DATABASE, no shared-mutable-state deadlock. | ✓ |
| Apply same isolation | Bring benchmark suite under per-run cloning; needs privilege changes for no isolation benefit. | |

**User's choice:** Leave untouched.
**Notes:** Out of scope. Scope is the main suite against dev Postgres (5432) only.

---

## Claude's Discretion

- **DB create/drop mechanism** — dedicated asyncpg autocommit connection in
  `conftest`'s `test_engine` (per SEED-031), not a `bin/` hook.
- **Per-run DB naming** — env var → `PYTEST_XDIST_WORKER` → PID (per SEED-031).
- **Stale-DB reaper** — `DROP DATABASE IF EXISTS` before create; optional age-based
  `bin/` helper.
- **pytest-xdist** — add as a dev dependency.

## Deferred Ideas

- CI `-n auto` (deferred by the CI policy decision).
- `bin/` reaper to drop `flawchess_test_*` by age (optional beyond self-heal).
- The "lighter interim" env-var stopgap from SEED-031 (explicitly not taken).
