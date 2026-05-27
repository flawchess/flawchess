---
title: Percentile chip — canonical-slice user metric (filter-independent)
date: 2026-05-23
context: Captured during a /gsd-explore session. Phase 93/94 ship a "top X%" percentile chip on the 4 ΔES rows. The chip currently reads the *filter-applied* user metric value and compares it against the pooled global CDF from `reports/global-percentile-cdf-latest.md`. That comparison is apples-to-oranges in two ways: (a) the global CDF was built on benchmark users selected with canonical filters (status='completed', ±100 ELO opponents at game time, sparse-cell exclusion, 36-month recency by virtue of monthly PGN dump selection) — when the FlawChess user sets no UI filters, their pooled-over-all-time, no-strength-match metric is being compared to a pool that *was* strength-matched; (b) when the user toggles recency or opponent-strength filters in the UI, their personal metric slice narrows but the benchmark CDF stays fixed, so the percentile moves a lot without that movement being meaningful signal.
related_files:
  - reports/global-percentile-cdf-latest.md
  - app/services/global_percentile_cdf.py
  - scripts/gen_global_percentile_cdf.py
  - scripts/import_stress_monitor.py
  - .claude/skills/benchmarks/SKILL.md
  - frontend/src/components/score-gap/PercentileChip.tsx
  - frontend/src/components/score-gap/ScoreGapRow.tsx
  - app/services/endgame_service.py
related_phases: [93, 94, 94.1, 95]
---

# Percentile chip — canonical-slice user metric

## The problem in one sentence

The percentile chip introduced in Phase 94 compares a *filter-applied* user metric value against a *fixed* benchmark CDF — so the comparison is structurally invalid both at default (no filters) and under any filter combination.

## Why the current setup is apples-to-oranges

Two distinct mismatches stack:

1. **Default-state mismatch.** Benchmark CDF cohort users were selected from a recent monthly Lichess PGN dump and their per-user metric values were computed under the canonical filters: `status='completed'` + ±100 ELO opponent filter (at game time) + sparse-cell `(2400, classical)` exclusion + game-time ELO bucketing + per-metric inclusion floors. A FlawChess user with *no* UI filters set computes their metric over their *entire* import history, with no opponent-strength match. Even at default, the two pools are not comparable.
2. **Filter-induced drift.** When the user enables UI filters (custom date range, opponent strength, time control, platform, rated, opponent type), their personal metric slice narrows; the benchmark CDF stays fixed. The percentile then moves substantially without that movement being meaningful — it's reading slice composition, not skill change.

## Architecture decision: canonical-slice user value, filter-independent chip

The chip is a **trait** of the user, not a **view** of their data. Like Elo: it doesn't change because you toggled "show only blitz." Concretely:

- The user's "chip value" is computed once, from a *canonical slice* of their games defined to match the benchmark cohort's filters.
- The chip is **independent of UI filter state.** Toggling recency / opponent strength / TC / platform in the UI does not change the chip.
- The displayed metric value on the row (filter-applied) and the chip-implied metric value (canonical-slice) will not match when filters are active. This is solved in copy — the chip is labeled as "vs. benchmark" and the tooltip makes the slice explicit. Users learn the distinction quickly.

### Canonical slice definition

For each user, the canonical-slice game set is:

- All imported games for the user
- Where `status='completed'`
- Where the user's game-time rating is within ±100 ELO of the opponent's game-time rating
- Excluding the sparse cell `(2400 game-time bucket, classical TC)` to match the benchmark
- Within the last 36 months (matching the benchmark's monthly-dump recency)
- Variant = standard only (already enforced upstream at import)
- Pooled across TCs (no per-TC cap) — the pooled benchmark CDF was built without per-TC caps too, so a bullet-heavy user is naturally compared to a bullet-heavy population

Each of the 4 chipped metrics is then computed from this slice with its existing per-metric inclusion floor:

- `score_gap` — ≥30 endgame AND ≥30 non-endgame games
- `achievable_score_gap` — ≥20 endgame-entry games
- `section2_score_gap_conv` — ≥20 spans per entry-eval bucket
- `section2_score_gap_parity` — ≥20 spans per entry-eval bucket

A metric whose user data fails its inclusion floor under canonical conditions produces no chip (and no LLM percentile field for that metric).

## Storage: separate table

A dedicated table, not columns on `users`:

```
user_benchmark_percentiles
  user_id        FK -> users.id   ON DELETE CASCADE
  metric         VARCHAR / enum   -- 'score_gap' | 'achievable_score_gap'
                                  -- | 'section2_score_gap_conv' | 'section2_score_gap_parity'
  value          DOUBLE PRECISION -- the user's canonical-slice metric value
  percentile     SMALLINT NULL    -- 1..99 from GLOBAL_PERCENTILE_CDF lookup; NULL below inclusion floor
  n_games        INTEGER          -- sample size used at compute time (for tooltip / debugging)
  cdf_snapshot   DATE             -- which benchmark CDF snapshot the percentile was looked up against
  computed_at    TIMESTAMPTZ
  PRIMARY KEY (user_id, metric)
```

The composite primary key `(user_id, metric)` gives uniqueness for free — PostgreSQL builds a unique index on the PK automatically. Recompute is UPSERT (`INSERT ... ON CONFLICT (user_id, metric) DO UPDATE`), so exactly one row exists per `(user_id, metric)` at any time and the prior computation is overwritten in place. No surrogate `id` column, no history table, no separate unique constraint.

Reasons:

- **Schema cleanliness.** The set of badged metrics will grow (future endgame-class metrics, time-pressure, recovery rework). Rows-per-metric scales; columns-per-metric in `users` does not.
- **CDF versioning.** When the benchmark CDF refreshes (new monthly snapshot), `value` is still valid but `percentile` is potentially stale — `cdf_snapshot` lets a future job re-look-up percentiles cheaply without recomputing values.
- **Storing the value (not just the percentile).** The metric value is reusable: tooltips, LLM payload, future "your value vs. cohort band" overlays. Recomputing it on read would mean re-running the canonical-slice query — defeats the point of materialising.

## Two-stage compute, hooked into the import pipeline

Aligned with the existing two-lane import (Phase 91 cold drain):

- **Stage A — post-import, eval-independent.** Triggered when import completes (background task, not in the import transaction). Computes `score_gap` only — this metric is derived from game outcomes (W/D/L) and games table fields, no Stockfish eval needed.
- **Stage B — post-cold-drain, eval-dependent.** Triggered when the Stockfish cold-drain pipeline finishes. Computes `achievable_score_gap`, `section2_score_gap_conv`, `section2_score_gap_parity` — each depends on `eval_cp` / `eval_mate` at endgame entry / span boundaries.

The chip lights up incrementally — `score_gap` appears within seconds-to-minutes of import completion, the three eval-based chips appear when the cold drain wraps. Better UX than waiting for the full eval drain before any chip renders, and the implementation seam (post-import hook vs. post-drain hook) is already established in the codebase.

Both stages are background tasks — neither blocks the user, neither extends import latency.

## Initial rollout: backfill script

The Stage A / Stage B hooks only populate the table for users whose import (or cold drain) runs *after* Phase 94.1 ships. To light up the chip for the entire existing user base on rollout — not just users who happen to re-import after the deploy — Phase 94.1 ships a one-shot backfill script:

- Path: `scripts/backfill_user_percentiles.py`
- CLI: `--target dev|prod` (mirroring the `--target` convention in `scripts/import_stress_monitor.py`)
  - `dev` connects to the local Docker DB on `localhost:5432`.
  - `prod` connects via `bin/prod_db_tunnel.sh` on `localhost:15432` and refuses to run if the tunnel is down.
  - Why not `--db benchmark`? The backfill operates on the *application* DBs (dev / prod) where actual user games live; the benchmark DB is the population pool for the *CDF*, not for FlawChess users. `--db benchmark` is the right flag for `gen_global_percentile_cdf.py`; `--target dev|prod` is the right flag for this backfill.
- Idempotent under the UPSERT semantics — re-runs only update changed rows, safe to invoke repeatedly during rollout debugging.
- Optional narrowing flags: `--user-id <id>` for single-user testing, `--metric <id>` for single-metric backfill (useful when iterating on a metric's compute path).
- Honours the Stage A vs. Stage B split: eval-dependent metrics are computed only for users whose cold drain has completed for the relevant span set; users with pending eval get a Stage-A-only backfill row (matches the steady-state behaviour of the per-import hooks).
- Emits a summary table at exit: rows upserted / skipped per metric per inclusion-floor reason, so the operator can spot-check rollout health (e.g., "60% of users below score_gap floor — expected for sparse-history accounts").

The backfill is part of the deploy checklist for the Phase 94.1 release: deploy → run `--target prod` once → chips appear for the whole user base. Subsequent imports keep the table fresh via the per-import hooks.

## Recompute triggers

- **Stage A:** after each successful import job completion.
- **Stage B:** after the cold-drain pipeline finishes evaluating the user's pending endgame-entry rows.
- **Benchmark snapshot refresh:** when `GLOBAL_PERCENTILE_CDF` is regenerated (manual recalibration, like `scripts/backfill_eval.py --db benchmark`), a one-shot re-lookup job updates `percentile` for every existing row without recomputing `value`. The `cdf_snapshot` column gates which rows still need re-lookup.

## Chip read path (Phase 94 wiring change)

Phase 94 currently emits `{metric}_percentile` from a per-request interpolation against the filter-applied value. That changes to: read `(value, percentile)` from `user_benchmark_percentiles` for the current user, ignoring filter state, and emit both on the API response. The chip reads the stored percentile; the row's filter-applied metric value continues to come from the existing per-request compute. Tooltip copy makes the dual-value relationship explicit.

## Label convention (separate but related)

The "Top X%" → percentile-format label flip was discussed but **not adopted** in this session. The current "Top X%" form stays. Re-litigate as a separate UI note if/when the question recurs.

## Alternatives considered and rejected

- **Architecture 2 — filter-responsive chip with per-filter benchmark CDF recompute.** Combinatorial explosion across recency × opponent-strength × TC × platform × rated × opp-type. Some filters (e.g., specific opponent username) are not recomputable at all. Rejected: cost not justified by user benefit.
- **Architecture 3 — filter-responsive chip, no benchmark recompute, honest copy.** Cheaper than (2) but worse than (1): chip moves with filters but the comparison is admittedly invalid. Rejected: solves nothing, adds confusion.
- **Per-cell chips (one per qualifying user cell, ELO bucket × TC).** Methodologically purest if the benchmark were treated as a per-cell distribution. But the published benchmark CDF in `reports/global-percentile-cdf-latest.md` is already *pooled* across cells. Mirroring that with one pooled user value is correct and simpler. Rejected as over-engineering.
- **Per-TC cap on the user's canonical slice (e.g., 1000 most-recent games per TC).** Considered for stability / compute. Rejected: benchmark cohort users have no per-TC cap on their contributing games, so adding one for FlawChess users would *introduce* an apples-to-oranges asymmetry rather than resolve it. Compute is cheap post-import (values are derived from already-stored game rows).
- **Store only percentile, not value.** Rejected: value is reusable for tooltips, LLM payload, and future overlays. Recomputing it on read defeats materialisation.
- **Wide columns on `users`.** Rejected: doesn't scale as more metrics get badges, conflates trait data with derived compute artifacts.

## CTE sharing with `gen_global_percentile_cdf.py` — anti-drift requirement

The canonical CTE machinery in `scripts/gen_global_percentile_cdf.py` is the *source of truth* for the canonical slice: `_canonical_selected_users_cte`, `_per_user_cte_score_gap`, `_per_user_cte_achievable`, `_per_user_cte_section2`, `_equal_footing_filter_sql`, `_sparse_exclusion_sql`, `_elo_bucket_expr`. These templates define what "benchmark-compatible" means at the SQL level — every per-user value in the published CDF was computed through them.

The per-user compute path added in Phase 94.1 (Stage A + Stage B + backfill) must use the *same* templates. The two structural differences:

- **Filter target.** The benchmark CDF iterates over rows in `selected_users` (benchmark cohort); the per-user path filters by a single `user_id` from the application DB. The same CTE structure with a different join target.
- **Aggregation target.** The benchmark CDF aggregates per-(user, cell) for percentile pooling; the per-user path collapses to one pooled value per user per metric (matching the published CDF's pooled-across-cells shape). The aggregation step differs; the canonical-slice game-set definition does not.

Phase 94.1 must either:

1. **Extract the canonical CTE builders into a shared module** (e.g., `app/services/canonical_slice_sql.py`) that both `scripts/gen_global_percentile_cdf.py` and the new per-user compute service import. Refactor `gen_global_percentile_cdf.py` to consume from the shared module.
2. **Document a deliberate decision to duplicate**, with explicit rationale, plus a drift-detection mechanism (e.g., a test that compares the two implementations against a fixed user fixture and asserts identical SQL output, or asserts equivalent metric values within float tolerance).

Silent drift between the two methodologies is unacceptable — the chip's validity rests on the per-user value being computed under *exactly* the same definition that produced the CDF. The Phase 94.1 plan must pick a mechanism. Option 1 is the more durable choice; Option 2 is acceptable only if Option 1 has a concrete cost we don't yet see in this design.

## Open questions deferred to phase planning

- Exact placement of the post-import and post-drain hooks (which function/module).
- Index strategy on `user_benchmark_percentiles` — primary key `(user_id, metric)` covers per-user lookup; whether an additional index on `cdf_snapshot` is needed depends on whether the snapshot-refresh re-lookup job will scan the table or filter by `cdf_snapshot < <new_snapshot>`.
- LLM payload integration — the Phase 95 prompt rework should read the canonical-slice percentile from the new table rather than recomputing per-request. Worth confirming the Phase 95 plan before its execution.
- Whether Phase 94's already-shipped per-request `interpolate_percentile` call path is removed cleanly or kept as a fallback during transition.
- Exact choice between CTE-sharing options (1) and (2) above — depends on how cleanly the `gen_global_percentile_cdf.py` builders extract without rewriting the script's report-generation surface.
- Backfill operational details: order of users (creation-asc to surface old accounts first? batched commits to bound transaction size?); how to skip users with `n_games=0` for the canonical slice without per-user query overhead.
