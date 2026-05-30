---
title: Move COHORT_PERCENTILE_CDF out of source into a DB table
date: 2026-05-31
context: /gsd-explore session — "refactor this monster of a module (app/services/global_percentile_cdf.py); probably put the data into a DB table; update generator + lookup"
status: decided (drives the Phase 99.1 spec)
---

# Move COHORT_PERCENTILE_CDF out of source into a DB table

## The problem

`app/services/global_percentile_cdf.py` is **3.1 MB / 130,369 lines**, but only
**~250 lines are logic** (the `CdfTable` dataclass, the `CdfMetricId` Literal,
breakpoint constants, and the interpolation helpers). The other ~130,119 lines
are float literals for the `COHORT_PERCENTILE_CDF` dict, machine-written between
`# --- BEGIN/END GENERATED REGISTRY ---` sentinels by
`scripts/gen_global_percentile_cdf.py`.

The pain is that **data is encoded as source code**: slow import/parse, ugly
130k-line diffs on every regen, hostile to IDE/git.

## Access pattern (decisive)

The CDF lookup is **not on any request hot path**.
`interpolate_cohort_percentile()` is called **only** in `compute_stage_a` /
`compute_stage_b` in `app/services/user_benchmark_percentiles_service.py` —
background tasks that run **once per import**, loop over (TC × metric family,
~32 lookups for one user), and `upsert_percentile()` the result into the
`user_benchmark_percentiles` table. The chart endpoint later just reads those
**already-stored** percentile rows; it never touches the CDF.

Consequence: at ~32 indexed lookups per import, **direct DB queries are fine** —
no in-memory cache, no startup load. The "load it into memory for speed"
objection only applies to hot/per-request lookups, which these are not. A DB
table is therefore the right call: SQL-analyzable (a stated goal), no source
bloat, and no runtime cost.

The *type* `CdfMetricId` is imported widely (model, repo, schemas,
`canonical_slice_sql`, `endgame_service`); only the **data** moves.

## Decisions (locked)

1. **DB table** `benchmark_cohort_cdf` holds the breakpoints. New SQLAlchemy
   model + Alembic migration (**schema only**). `snapshot_month` stays as a
   plain audit column (which benchmark month each cell came from), **not** an
   idempotency gate.
2. **Generator** (`gen_global_percentile_cdf.py`) stops rewriting the `.py`
   between sentinels; it emits a **compact seed file** to `app/data/` instead.
3. **Manual idempotent seed script** `scripts/seed_cohort_cdf.py`, modeled on
   `scripts/seed_openings.py`: read the seed file, `INSERT ... ON CONFLICT DO
   UPDATE`. Run with `uv run python -m scripts.seed_cohort_cdf`.
   - **`ON CONFLICT DO UPDATE` is the idempotency** — re-running picks up new
     cells *and* changed values with zero gate logic. This is why we rejected a
     `snapshot_month` gate (adding new CDF families doesn't bump the month) and a
     content-hash gate (unnecessary once the upsert is idempotent).
   - Prod uses the same in-container pattern as openings:
     `docker compose exec backend /app/.venv/bin/python -m scripts.seed_cohort_cdf`.
4. **`bin/run_local.sh`**: add a count-gated block mirroring the openings one
   (lines 39-44) so first-time local setup auto-seeds.
5. **`global_percentile_cdf.py` shrinks 130k → ~250 lines**: keep `CdfMetricId`,
   `CdfTable`, the breakpoint constants, and the interpolation math.
   `interpolate_cohort_percentile` becomes **`async`**, takes a session, queries
   the table for the `(metric, anchor, tc)` row, then runs the existing
   `_interpolate_with_table` math in Python (interpolation stays in Python — no
   need to do it in SQL).
6. **Update callers + drift test**: `compute_stage_a` / `compute_stage_b` are
   already async with a session, so threading it in is trivial; the regen drift
   test now compares regenerated **seed-file content**, not source bytes.

## Rejected / not doing

- **Data file loaded into an in-memory dict** (sync lookup): kills the bloat too,
  but gives no SQL-analysis surface, which the user wants. Only worth it for hot
  lookups, which these aren't.
- **Auto-seed on the Alembic/backend-startup entrypoint**: deemed too complex.
  Manual seed script matches the established `seed_openings` pattern.
- **Hash gate / `snapshot_month` gate**: unnecessary — the upsert is already
  idempotent and re-seeds correctly when new CDFs are added.
- **Data-only Alembic migration full of INSERTs**: that's the same monster in a
  SQL hat, and a new multi-MB file every regen. The seed-file + seed-script split
  keeps the migration trivial.

## Flagged

- **Operational:** like openings, a fresh prod DB shows **suppressed chips until
  the seed is run** (lookup returns `None` → chip suppresses, degrades
  gracefully). Accepted project pattern (no openings → no explorer). Note it in
  the runbook.
- **Deferred to the plan phase — table layout:**
  - **long** (one row per breakpoint: `metric, anchor_elo, tc, percentile,
    value, n_users, snapshot_month` → ~130k rows) — best for SQL analysis.
  - **wide** (one row per cell with a `float[]` breakpoints column → ~1.3k rows)
    — trivial upsert, a literal mirror of `CdfTable`.
  - Lean **long** given the analysis goal; final call belongs to the planner.
