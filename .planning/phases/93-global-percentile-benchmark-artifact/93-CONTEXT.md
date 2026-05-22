# Phase 93: Global Percentile Benchmark Artifact - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce the global empirical-CDF benchmark artifact that downstream percentile annotations (Phase 94 chip, Phase 95 LLM payload) consume. Two-task scope:

- **Task A — Methodology (skill):** extend `/benchmarks` SKILL.md with a CDF subchapter documenting the canonical CTE + tail-densified breakpoint set + per-rating-bucket sanity checks. Running the subchapter produces `reports/global-percentile-cdf-latest.md` (with the existing rotation rule).
- **Task B — Mechanization (script + artifact):** write `scripts/gen_global_percentile_cdf.py` that runs the canonical CTE deterministically against the benchmark DB and emits committed Python source at `app/services/global_percentile_cdf.py`. The DB → Python regen is a manual recalibration step, like `scripts/backfill_eval.py --db benchmark`. No CI gate on this step.

The artifact ships **the 4 chipped ΔES metrics only**:
- `score_gap` (Endgame Score Gap, page-level)
- `achievable_score_gap` (Achievable Score Gap, page-level)
- `section2_score_gap_parity` (Section 2 Parity ΔES)
- `section2_score_gap_conv` (Section 2 Conversion ΔES)

Recovery Score Gap and the 3 raw % gauges are explicitly out of scope (Recovery: opponent-confounded, d=0.95 inverted; raw gauges: redundant chips on cards whose ΔES row is already chipped).

Phase 93 ships **no client-side code and no frontend codegen** — see D-01.

</domain>

<decisions>
## Implementation Decisions

### TS codegen integration
- **D-01: Python-only artifact, no TS mirror, no CI Python→TS drift-guard.** The CDF table has no frontend consumer in v1.19. Phase 94's backend interpolates the user's value against `GLOBAL_PERCENTILE_CDF` at request time and emits a scalar `{metric}_percentile` field in the API response; the chip + popover render from that scalar. `scripts/gen_endgame_zones_ts.py` and `frontend/src/generated/endgameZones.ts` are untouched by this phase. **Why we considered a mirror:** pattern-match against `endgame_zones.py`, which does need a TS mirror because gauge band painting happens client-side. **Why it doesn't apply here:** unlike IQR zone bands, the CDF output (a percentile in [0,100]) is computed server-side and shipped as a scalar. **If a future phase ships a client-side viz** (sparkline showing the user's position on the global distribution, "what value puts me in the top X%" widget), the codegen mirror is added then, not pre-built.

### Inherited locked decisions (from SEED-019 + ROADMAP success criteria — not re-discussed)
- **D-02: In-scope metric set is exactly 4.** Endgame Score Gap, Achievable Score Gap, Parity ΔES, Conversion ΔES. Recovery dropped (opponent confound). Raw % gauges keep their zone bands but get no chips. Empirically justified in `reports/benchmarks-gap-metrics-percentile-candidacy.md` (2026-05-22).
- **D-03: Internal metric IDs reuse existing `MetricId` literals** in `app/schemas/endgames.py`: `score_gap`, `achievable_score_gap`, `section2_score_gap_parity`, `section2_score_gap_conv`. No new IDs introduced.
- **D-04: Output module path is `app/services/global_percentile_cdf.py`** — a sibling of `app/services/endgame_zones.py`, NOT a graft into it. CDF tables (25 tail-densified breakpoints per metric, global-pooled) are a different artifact shape than ZoneSpec (IQR bands per (TC, ELO) cell).
- **D-05: Canonical CTE inherited verbatim from `/benchmarks` skill.** Lichess username join (NOT benchmark_user_id), `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing opponent filter `|opp_rating − user_rating| ≤ 100`, **game-time** ELO bucketing (NOT snapshot `rating_bucket` — see "Rating-lag selection bias" in SKILL.md Chapter 1), sub-800 dropped. Bypassing the canonical CTE produces a wrong global distribution and therefore wrong percentiles for every user; the CDF tails are more sensitive to CTE drift than the IQR zone bands are.
- **D-06 (REVISED 2026-05-22): Breakpoint set is every integer percentile from p1 through p99** — 99 breakpoints total (`p1, p2, p3, ..., p98, p99`). Tail-bounded at p1/p99 (NOT extended to p0.1/p99.9 — n≈2000 cohort gives ~5pp sampling SE at the deep tails, swinging on single outliers). NO sub-percent steps (NO p0.5, p2.5, p97.5, p99.5) — chip-rendered phrasing operates on whole-percent precision. This supersedes the earlier 19-breakpoint tail-densified set and the intermediate 15-breakpoint p1..p99 set. See ROADMAP §Phase 93 success criterion #5 for the authoritative rationale.
- **D-07: Report has rotation rule.** `reports/global-percentile-cdf-latest.md` is overwritten each run; the prior dated report is archived in place, mirroring the existing `reports/benchmarks-latest.md` rotation pattern.

### Claude's Discretion
The user picked TS codegen as the only gray area worth discussing. The remaining shape decisions are left to research + planning:
- Exact dataclass design for `GLOBAL_PERCENTILE_CDF` (e.g. `Mapping[MetricId, CdfTable]` where `CdfTable` carries breakpoints + sample n + snapshot month). Should follow the typed-Mapping pattern already established in `endgame_zones.py` (`ZONE_REGISTRY`, `PER_CLASS_GAUGE_ZONES`).
- Per-user inclusion floor per metric — keep the pre-flight's per-metric floors (≥30 endgame AND ≥30 non-endgame for Endgame Score Gap; ≥20 endgame-entry for Achievable; ≥20 spans/bucket for Section 2 ΔES) or unify. Recommend keeping per-metric to preserve continuity with the pre-flight, but planner is free to argue for unified floor with reasoning.
- Report depth — slim (breakpoint tables + one per-rating-bucket sanity-check table per metric) vs rich (full pre-flight-style per-bucket distribution percentiles + skew/kurtosis + ELO collapse verdicts). Slim is sufficient for success criterion #3; rich is closer to the pre-flight precedent.
- Whether the committed Python source carries a `BENCHMARK_DB_SNAPSHOT_MONTH = "2026-03"` constant + per-metric `n_users` field for audit trail. Recommend yes — small cost, real benefit for future recalibrations.

These are HOW decisions inside the locked WHAT. Planner can resolve them in PLAN.md without coming back to the user, but should document the chosen shape briefly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source of truth
- `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` — the canonical design doc for Phases 93/94/95. Includes the empirical refinement note, the 4-metric scope, the two-task split, and the open decisions deferred to phase planning. **Note:** the seed's TS codegen guidance is superseded by D-01 in this CONTEXT.md (a refinement note has been added to the seed).
- `reports/benchmarks-gap-metrics-percentile-candidacy.md` (2026-05-22) — empirical pre-flight that justified the 4-metric scope, Recovery drop, and Conversion ΔES "improvement-focus" framing. Tier table downstream of this report.
- `.planning/REQUIREMENTS.md` §PCTL-01 — the user-facing milestone requirement Phase 93 fulfills (updated 2026-05-22 to drop the TS drift-guard clause).
- `.planning/ROADMAP.md` Phase 93 section — phase scope and success criteria (updated 2026-05-22).

### Methodology + SQL templates
- `.claude/skills/benchmarks/SKILL.md` — canonical CTE, sparse-cell rule, equal-footing filter, game-time ELO bucketing methodology. **Task A extends this file** with a new CDF subchapter (placement: §3.5 or top-level Chapter 4, planner to decide based on existing chapter structure).
- `.claude/skills/benchmarks/SKILL.md` §1 "Rating-lag selection bias (game-time bucketing)" — the methodology fix the CDF must inherit; bucketing on snapshot rating instead of game-time rating silently inflates ELO-axis Cohen's d and biases the pooled distribution.

### Code touchpoints
- `app/services/endgame_zones.py` — sibling module pattern to mirror (typed `Mapping[MetricId, ...]` constants, dataclass shapes, docstring conventions). Do NOT graft CDF tables into this file.
- `app/schemas/endgames.py` — defines `MetricId` Literal that the CDF registry keys off of (no new IDs needed).
- `app/services/endgame_service.py:205` — `PVALUE_RELIABILITY_MIN_N = 10` lives here, not in `endgame_zones.py` (SEED-019 misattributed it). Phase 94 will use this constant for chip gating; Phase 93 only needs an inclusion floor for CDF *generation*, which is a separate concept.
- `scripts/backfill_eval.py` — reference for the "manual recalibration script that connects to the benchmark DB" pattern; same DB-config style and `--db benchmark` flag convention.
- `scripts/gen_endgame_zones_ts.py` — **NOT touched by Phase 93** (per D-01). Listed here so planner doesn't try to extend it.

### Inherited from prior decisions / memories
- Project memory `feedback_benchmark_source_of_truth.md` — the `/benchmarks` report is the source of truth for "typical"; any user-facing normative copy must trace back to it. CDF artifact is downstream of the same source.
- Project memory `project_benchmark_outliers_unfiltered.md` — SKILL.md filters `status='completed'` and excludes the sparse `(2400, classical)` cell from marginals; CDF must inherit.
- Project memory `feedback_no_dev_db_reset_in_plans.md` — Phase 93 plan must not gate completion on `bin/reset_db.sh`. The benchmark DB is separate (`bin/benchmark_db.sh`) and is expected to be running for the manual recalibration step; planning should design verification around that or flag it as HUMAN-UAT.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Typed registry pattern in `app/services/endgame_zones.py`**: `ZONE_REGISTRY: Mapping[MetricId, ZoneSpec]`, `PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands]`. New `GLOBAL_PERCENTILE_CDF: Mapping[MetricId, CdfTable]` should follow the same Mapping + dataclass shape.
- **Benchmark DB connection in `scripts/backfill_eval.py`**: handles `--db benchmark` flag, refuses to run unless `DATABASE_URL` contains `flawchess_benchmark` AND port `5433`. Reuse the same safety guard in `gen_global_percentile_cdf.py`.
- **Canonical CTE blocks in `.claude/skills/benchmarks/SKILL.md`** — copy verbatim into the new subchapter and into the script. The SKILL.md has tested CTE templates per metric family.
- **Report rotation rule** — already used by `reports/benchmarks-latest.md`. New `reports/global-percentile-cdf-latest.md` follows the same convention (planner to confirm the rotation mechanism is shared/extensible).

### Established Patterns
- **Methodology source = SKILL.md; Mechanization = script; Committed artifact = Python source**. Already the shape for `endgame_zones.py` (calibrated from `/benchmarks` reports, committed as the source of truth, regenerated manually when the methodology changes). Phase 93 follows this pattern exactly.
- **Per-class IDs + per-metric Literals** in `app/schemas/endgames.py` keep the typed Mapping keys grep-able and Pydantic-validated.
- **Manual recalibration scripts** (`scripts/backfill_eval.py`, `scripts/select_benchmark_users.py`, `scripts/import_benchmark_users.py`) are documented in CLAUDE.md §Scripts; `gen_global_percentile_cdf.py` joins this list.

### Integration Points
- `app/services/global_percentile_cdf.py` is consumed by Phase 94 backend (interpolation helper + nullable `{metric}_percentile` field on endgame response schemas). Phase 93 does NOT write that consumer — it only ships the typed registry plus a minimal runtime helper if one is needed for clean Phase 94 hand-off (planner may include a `interpolate_percentile(metric_id, value) -> float | None` helper in `global_percentile_cdf.py` itself; defer the per-user-N gating to Phase 94).
- The `MetricId` Literal in `app/schemas/endgames.py` is the only schema touchpoint — the 4 IDs already exist; no new schema work in Phase 93.
- No router, no frontend, no migration in Phase 93. Pure service-module artifact + skill subchapter + script.

</code_context>

<specifics>
## Specific Ideas

- The Conversion ΔES metric has skew −0.95 and excess kurt +1.42 (per pre-flight). The CDF stores the empirical distribution faithfully; popover framing (Phase 94) handles the asymmetric "improvement-focus" advice. No special-case storage for Conversion in Phase 93.
- The pre-flight at `reports/benchmarks-gap-metrics-percentile-candidacy.md` is essentially a dry run of the CDF methodology — its per-metric tables, per-bucket medians, and skew/kurtosis values are the format the Phase 93 report should mirror at minimum.

</specifics>

<deferred>
## Deferred Ideas

- **TS codegen mirror of the CDF** — deferred. Add it only when a client-side CDF consumer ships (sparkline of user's position on global distribution; "what value puts me in the top X%" interactive widget; offline what-if calculator). No current Phase 94 or 95 requirement needs it.
- **Tier-4 per-type CDFs** (per-class Conv / Recov / Score / Score Gap) — deferred per REQUIREMENTS.md §Future Requirements. Per-type samples are too thin (~8 rook conversion spans per user is noise). Revisit when per-user samples deepen materially.
- **Opening insights percentile annotations** — out of scope for v1.19; candidate for a future Opening Insights v2 milestone.
- **CDF granularity beyond 19 breakpoints** — the locked tail-densified breakpoint set is sufficient for honest "top 0.1%" rendering. If a future use case needs finer granularity (e.g. monotone spline interpolation between breakpoints rather than linear), revisit then.

</deferred>

---

*Phase: 93-global-percentile-benchmark-artifact*
*Context gathered: 2026-05-22*
