# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- ✅ **v1.4 Improvements** — Phase 24 (shipped 2026-03-22)
- ✅ **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33 (shipped 2026-03-28)
- ✅ **v1.6 UI Polish & Improvements** — Phases 34-39 (shipped 2026-03-30)
- ✅ **v1.7 Consolidation, Tooling & Refactoring** — Phases 40-43 (shipped 2026-04-03)
- ✅ **v1.8 Guest Access** — Phases 44-47 (shipped 2026-04-06)
- ✅ **v1.9 UI/UX Restructuring** — Phases 49-51 (shipped 2026-04-10) — see [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md)
- ✅ **v1.10 Advanced Analytics** — Phases 48, 52-55, 57, 57.1, 59-62 (shipped 2026-04-19) — see [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md)
- ✅ **v1.11 LLM-first Endgame Insights** — Phases 63-68 (shipped 2026-04-24) — see [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md)
- ✅ **v1.12 Benchmark DB Infrastructure & Ingestion Pipeline** — Phase 69 (shipped 2026-04-26) — see [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md)
- ✅ **v1.13 Opening Insights** — Phases 70, 71, 71.1 (shipped 2026-04-27; Phases 72-74 descoped) — see [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md)
- ✅ **v1.14 Score-Based Opening Insights** — Phases 75, 76, 77 (shipped 2026-04-29; INSIGHT-UI-04 descoped) — see [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md)
- ✅ **v1.15 Eval-Based Endgame Classification** — Phases 78, 79 (shipped 2026-05-03; VAL-01 / PHASE-VAL-01 rescinded) — see [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md)
- ✅ **v1.16 Stockfish Eval Analyses** — Phases 80, 80.1, 81, 82, 83 (shipped 2026-05-11) — see [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md)
- ✅ **v1.17 Endgame Stats Card Redesign** — Phases 84-88.4 (shipped 2026-05-19; Phase 89 dropped, 87.3 superseded) — see [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md)
- ✅ **v1.18 Import Pipeline Hardening** — Phases 90, 91, 92 (shipped 2026-05-22; PRs #130, #137, #138 + hotfix #139) — see [milestones/v1.18-ROADMAP.md](milestones/v1.18-ROADMAP.md)
- 🔄 **v1.19 Endgame Percentiles & LLM Statistical Reasoning** — Phases 93, 94, 94.1, 94.2, 94.3, 95 (in progress, planning)

## Phases

- [ ] **Phase 93: Global Percentile Benchmark Artifact** — Per-metric empirical CDF for the 4 chipped ΔES metrics (Endgame Score Gap, Achievable Score Gap, Parity ΔES, Conversion ΔES), produced via /benchmarks skill subchapter + `scripts/gen_global_percentile_cdf.py`, committed to `app/services/global_percentile_cdf.py` (Python-only artifact — no TS mirror; backend interpolates at request time and emits a scalar percentile)
- [ ] **Phase 94: Backend & Frontend Percentile Annotations** — Nullable `{metric}_percentile` on endgame responses + "top X%" chip on 4 ΔES rows (desktop + mobile parity, metric-aware popover copy)
- [ ] **Phase 94.1: Canonical-Slice User Percentile Materialisation** — New `user_benchmark_percentiles` table storing per-(user, metric) canonical-slice value + percentile + cdf_snapshot; two-stage compute hooks (Stage A post-import for `score_gap`, Stage B post-cold-drain for the 3 eval-dependent metrics); backfill script with `--target dev|prod` for one-shot population of existing users; chip reads from table (filter-independent), tooltip copy updated to make the canonical-slice framing explicit
- [x] **Phase 94.2: Pooled-Per-User Percentile Redesign** — Replace per-cell stratified methodology with one-point-per-user pooled model on both CDF construction and per-user lookup sides; recent 1000 games per TC, ≤36 months, pooled across TCs; single ≥30-games inclusion floor on the pool; regenerate `GLOBAL_PERCENTILE_CDF` against new methodology; re-run backfill; SKILL.md methodology chapter refresh (completed 2026-05-24)
- [x] **Phase 94.3: Per-TC Percentile Chips on Time Pressure Cards** *(INSERTED — SEED-025)* — Extend the Phase 94.2 pooled-per-user contract to per-TC surfaces. 12 new metrics added to `user_benchmark_percentiles` ENUM (Time Pressure Score Gap, Clock Gap, Net Flag Rate × {bullet, blitz, rapid, classical}) reusing the pooled-per-user methodology parameterised by TC; new per-TC pooled-aggregate SQL builders in `canonical_slice_sql.py`; 12 new keys in `GLOBAL_PERCENTILE_CDF`; chips wired to `TimePressureTcCard` headers (3 chips per card) via the existing `PercentileChip` component; backfill extended for one-shot population. No schema change. (completed 2026-05-24)
- [ ] **Phase 94.4: Peer-Relative Percentile Chip Refinement** *(INSERTED — SEED-026 v2)* — Pivot the chip from global-pool ("vs all benchmark users") to peer-relative ("vs same-rated-cohort users"). Per-(user, TC) rating anchor (median over latest ~1000 games per TC; Lichess wins precedence, chess.com converted via hardcoded ChessGoals Table 2 snapshot). Replace `GLOBAL_PERCENTILE_CDF` with a per-(metric, ELO anchor, TC) cohort CDF family built as 50-Elo sliding windows of K=200 floor-passing users (±150 Elo max, suppress otherwise). TC-aggregated metrics (`score_gap`, `achievable_score_gap`, the 2 Section-2 metrics) compute per-TC sub-percentiles aggregated via game-count-weighted mean. Chip UX shrinks to `p23` pill + tooltip-only; tooltip leads with cohort framing + rating-anchor disclosure. Metric eligibility re-opened — Conversion / Recovery / Endgame Score Gap rescued under peer-relative framing (~7-12 chip surface, up from ~3-5). Storage shape on `user_benchmark_percentiles` unchanged (still one scalar percentile per (user, metric)).
- [ ] **Phase 95: LLM Endgame-Insights Statistical-Reasoning Rework** — Payload extension (p-values, CI bounds, percentiles) + prompt rewrite reasoning over CIs/percentiles with guardrails, prompt version bump from `endgame_v35`, UAT pass

## Phase Details

### Phase 93: Global Percentile Benchmark Artifact

**Goal**: Produce the global empirical-CDF benchmark artifact that every downstream percentile annotation depends on. Per the SEED-019 empirical refinement (`reports/benchmarks-gap-metrics-percentile-candidacy.md`, 2026-05-22), the in-scope set is the **4 chipped ΔES metrics**: Endgame Score Gap (page-level), Achievable Score Gap (page-level), Parity Score Gap (Section 2), Conversion Score Gap (Section 2). Recovery Score Gap is dropped (opponent-confounded, d=0.95 inverted); raw % gauges get no chips (redundant with the ΔES chip on the same card). Mechanism is split across two tasks: (A) extend `/benchmarks` SKILL.md with a CDF subchapter that documents methodology + SQL templates and writes a human-readable report to `reports/global-percentile-cdf-latest.md`; (B) write `scripts/gen_global_percentile_cdf.py` that runs the canonical CTE deterministically against the benchmark DB and emits committed Python source at `app/services/global_percentile_cdf.py` (NOT `endgame_zones.py` — that file is the ZoneSpec / IQR-band registry; a 25-breakpoint CDF per metric is a different artifact shape). The artifact is Python-only — Phase 94's backend interpolates each user's metric value against `GLOBAL_PERCENTILE_CDF` at request time and emits a scalar `{metric}_percentile` in the API response; the frontend renders a chip from that scalar without needing the CDF on the client. The DB→Python step is a manual recalibration, like `scripts/backfill_eval.py --db benchmark`.
**Depends on**: Nothing within v1.19 (depends on shipped v1.17 metric set + v1.12 benchmark DB)
**Requirements**: PCTL-01
**Success Criteria** (what must be TRUE):

  1. Running `scripts/gen_global_percentile_cdf.py` against the current benchmark DB emits a per-metric breakpoint table covering the 4 chipped ΔES metrics: Endgame Score Gap, Achievable Score Gap, Parity Score Gap (Section 2), Conversion Score Gap (Section 2). Recovery Score Gap is intentionally NOT in scope per the empirical pre-flight.
  2. The breakpoint tables are committed at `app/services/global_percentile_cdf.py` as a typed `GLOBAL_PERCENTILE_CDF` registry; the module is Python-only (no TS mirror, no Python→TS drift-guard) — Phase 94's backend interpolates at request time and ships a scalar percentile to the frontend.
  3. The /benchmarks SKILL.md CDF subchapter exists, documenting methodology + SQL templates + expected report shape; running it produces `reports/global-percentile-cdf-latest.md` with per-metric breakpoint tables and per-rating-bucket sanity checks (median + skew/kurtosis), with the rotation rule applied (prior dated report archived).
  4. The artifact uses the canonical CTE verbatim (lichess_username join, `status='completed'`, sparse-cell exclusion, equal-footing filter, game-time ELO bucketing, sub-800 dropped) — verifiable by inspection of the SKILL.md subchapter and `scripts/gen_global_percentile_cdf.py`.
  5. Breakpoint set is **every integer percentile from p1 through p99** (99 breakpoints total: p1, p2, p3, ..., p98, p99) — tail-bounded at p1 / p99, NOT extended to p0.1 / p99.9, and NO sub-percent steps (no p0.5, p2.5, p97.5, p99.5). Rationale: at the current pooled cohort (n ≈ 2000 across the 4 metrics) the p0.1 / p99.9 breakpoints have ~5pp sampling SE and would render "top 0.1%" estimates that swing on single outliers; sub-percent steps are also discarded because chip-rendered phrasing operates on whole-percent precision. Chip-rendered phrasing always uses the "top X%" form (NO "bottom X%" wording) — a user at p1 renders as "top 99%", a user at p99 renders as "top 1%". Tighter tails are a future ops task (cohort re-selection at higher `--per-cell`), not v1.19 scope.

**Plans:** 2 plans

Plans:
**Wave 1**

- [x] 93-01-PLAN.md — Extend /benchmarks SKILL.md with Chapter 4 (Global Percentile CDF methodology + SQL templates + report shape)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 93-02-PLAN.md — Write scripts/gen_global_percentile_cdf.py + commit app/services/global_percentile_cdf.py typed registry + interpolate_percentile helper + initial report

### Phase 94: Backend & Frontend Percentile Annotations

**Goal**: Surface percentile annotations end-to-end on the **4 chipped ΔES rows** (per SEED-019 empirical refinement). Backend interpolates each user's metric value against `GLOBAL_PERCENTILE_CDF`, emits a nullable `{metric}_percentile` field gated by a metric-specific minimum-N reliability floor. Frontend renders a compact "top X%" chip beside the metric value with desktop + mobile parity, theme-driven colors, and **metric-aware popover copy**: skill-isolating framing for low-d metrics (Endgame Score Gap, Achievable Score Gap, Parity ΔES — d ≤ 0.32); improvement-focus framing for the high-d metric (Conversion ΔES — d=1.37, "tracks rating; if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO"). Raw % gauges (Conv/Parity/Recov) and the Recovery ΔES row keep their existing IQR zone bands but get no chips.
**Depends on**: Phase 93
**Requirements**: PCTL-02, PCTL-03, PCTL-04, PCTL-05, PCTL-06
**Success Criteria** (what must be TRUE):

  1. The 4 chipped rows render a percentile chip beside the metric value when the user's sample size clears the per-metric reliability gate; below the gate, no chip renders and no percentile is emitted (PCTL-06). No chip appears on the Recovery ΔES row or on any of the 3 raw % gauges.
  2. Chip phrasing always uses the "top X%" form (NO "bottom X%" wording) — a user at p1 renders as "top 99%", a user at p99 renders as "top 1%", neutral fallback near p50 (e.g. "top 50%"). Rounding is honest (no spurious decimals), and colors come from `theme.ts` (no hard-coded values).
  3. Popover copy is metric-aware: the 3 low-d chips frame the percentile as skill-isolating (separate from rating); the Conversion ΔES chip frames the percentile as improvement-focus (tracks rating, surfaces the biggest single ELO improvement available to weaker players).
  4. Annotations render with full desktop + mobile parity on the 4 affected rows: `EndgameOverallScoreGapRow.tsx` (Endgame Score Gap + Achievable Score Gap rows) and `EndgameMetricCard.tsx` (Parity card ΔES bullet + Conversion card ΔES bullet). Verified at 375px and desktop widths.
  5. API responses include nullable `{metric}_percentile` fields alongside existing value / CI / zone fields without breaking any current consumer.

**Plans:** 3 plans

Plans:
**Wave 1**

- [x] 94-01-PLAN.md — Backend: add 4 nullable `{metric}_percentile` Pydantic fields + gated `interpolate_percentile` calls at the 2 compute sites + schema/gate tests (PCTL-02, PCTL-06)

**Wave 2** *(blocked on Wave 1)*

- [x] 94-02-PLAN.md — Frontend: mirror 4 new fields into TS types + build `PercentileChip` component (banded color pill + flame tiers + Radix popover shell + flavor-routed body) + unit tests (PCTL-03, PCTL-04, PCTL-05)

**Wave 3** *(blocked on Wave 2)*

- [x] 94-03-PLAN.md — Frontend wiring: add `chipSlot` to `ScoreGapRow` + wire chips on 4 rows (Section 1 page-level + Section 2 conv/parity; Recovery defensively excluded) + extend component tests + HUMAN-UAT mobile parity at 375px (PCTL-03, PCTL-04, PCTL-05, PCTL-06)

**UI hint**: yes

### Phase 94.1: Canonical-Slice User Percentile Materialisation

**Goal**: Resolve the apples-to-oranges comparison shipped in Phase 94 by materialising each user's canonical-slice metric value + percentile in a new `user_benchmark_percentiles` table, decoupling the chip from UI filter state. The Phase 94 chip currently interpolates a *filter-applied* user value against the *filter-fixed* global CDF — invalid both at default (user has no opponent-strength match, benchmark cohort does) and under filtered views (chip moves with slice composition rather than skill change). New contract: the chip is a *trait* of the user, not a *view* of their data — computed once per user per metric from a canonical slice that mirrors the benchmark CTE (status='completed' + ±100 ELO opponent at game time + sparse-cell `(2400, classical)` exclusion + 36-month recency, pooled across TCs with no per-TC cap), stored with the lookup percentile and a `cdf_snapshot` reference, and refreshed via two stages hooked into the existing two-lane import pipeline: Stage A at import completion for the eval-independent `score_gap` metric, Stage B at Stockfish cold-drain completion for the three eval-dependent metrics (`achievable_score_gap`, `section2_score_gap_conv`, `section2_score_gap_parity`). A one-shot backfill script (`scripts/backfill_user_percentiles.py` with `--target dev|prod` per the `import_stress_monitor.py` convention) populates existing users on each environment in a single batch — required so the chip lights up for the entire user base on rollout, not just users who import after the phase ships. Phase 94's per-request `interpolate_percentile` call site is rewired to read from the table; tooltip copy is updated to make the canonical-slice framing explicit. Detailed design and rejected alternatives captured in `.planning/notes/percentile-chip-canonical-slice.md`.
**Depends on**: Phase 94 (consumes the chip wiring + popover copy slot; replaces the per-request interpolation seam)
**Requirements**: PCTL-07, PCTL-08, PCTL-09, PCTL-10
**Success Criteria** (what must be TRUE):

  1. A new `user_benchmark_percentiles` table exists with columns `(user_id, metric, value, percentile, n_games, cdf_snapshot, computed_at)` and composite primary key `(user_id, metric)`, created via an Alembic migration. `user_id` has `ON DELETE CASCADE` to `users.id`. There is exactly one row per `(user_id, metric)` at any time — each recompute UPSERTs (`INSERT ... ON CONFLICT (user_id, metric) DO UPDATE`) so the prior row is overwritten in place, keeping only the most recent computation. No surrogate `id` column.
  2. The canonical-slice game set for percentile computation matches the benchmark cohort definition: `status='completed'` + ±100 ELO opponent filter at game time + sparse-cell `(2400, classical)` exclusion + 36-month recency + standard variant + the existing per-metric inclusion floor. Verifiable by inspection of the compute service against `.claude/skills/benchmarks/SKILL.md` §1. No per-TC cap is applied (matches benchmark cohort methodology).
  3. Stage A computes and persists `score_gap` for the importing user as a background task triggered at import job completion, without extending import latency (does not run inside the import transaction). Stage B computes and persists `achievable_score_gap`, `section2_score_gap_conv`, `section2_score_gap_parity` as a background task triggered at Stockfish cold-drain completion. Both stages tolerate partial state — a user whose inclusion floor fails under canonical conditions for a given metric gets `percentile=NULL` (or no row) and no chip; users still pre-cold-drain see only the Stage A chip.
  4. Phase 94's chip render path reads `(value, percentile)` from `user_benchmark_percentiles` instead of from the per-request `interpolate_percentile` call. The chip is independent of UI filter state — toggling recency / opponent strength / TC / platform / rated / opponent type does not change the chip. The row's filter-applied metric value continues to display from the existing per-request compute; the chip's tooltip explains the dual-value framing (per-row value reflects filters; chip reflects career under canonical conditions). The pre-existing per-request `interpolate_percentile` code path is removed from the request handler once the table-backed read is verified.
  5. A `cdf_snapshot` column on the table records which benchmark CDF version each percentile was looked up against. When `GLOBAL_PERCENTILE_CDF` is regenerated, a documented re-lookup path updates `percentile` for existing rows without recomputing `value`. (Implementing the re-lookup as a scheduled job is out of scope for this phase; the column + a manual-run script are sufficient.)
  6. A `scripts/backfill_user_percentiles.py` script exists that computes and UPSERTs canonical-slice values + percentiles for all (user, metric) pairs across the chosen DB target. CLI: `--target dev|prod` (mirroring `scripts/import_stress_monitor.py` lines 13-19 — `dev` connects to the local Docker DB on `localhost:5432`; `prod` connects via the `bin/prod_db_tunnel.sh` tunnel on `localhost:15432` and refuses to run if the tunnel is down). Optional `--user-id <id>` flag to backfill a single user for testing. Optional `--metric <id>` to backfill a single metric. The script is idempotent (UPSERT semantics) — re-runs are safe and only update changed rows. Eval-dependent metrics are computed only for users whose cold drain has completed; users with pending eval get a Stage-A-only backfill row (matches Success Criterion 3). The script emits a summary table (users processed / rows upserted / rows skipped per metric per inclusion-floor reason) so operators can spot-check rollout health.
  7. The canonical CTE machinery in `scripts/gen_global_percentile_cdf.py` (per-metric `_per_user_cte_*` builders, `_canonical_selected_users_cte`, `_equal_footing_filter_sql`, `_sparse_exclusion_sql`, `_elo_bucket_expr`) is the source of truth for the canonical slice. Phase 94.1 either extracts these into a shared module that both the benchmark CDF generator and the new per-user compute path import, OR documents an explicit decision (with rationale) to duplicate the SQL templates. Drift between benchmark-cohort methodology and per-user compute methodology is unacceptable — the chosen mechanism must make accidental drift impossible or visibly tracked.

**Plans:** 12 plans (8 shipped + 4 gap-closure from 94.1-VERIFICATION.md)

Plans:
**Wave 0** *(test scaffolding — Nyquist)*

- [x] 94.1-01-PLAN.md — Wave 0 test scaffolding: canonical_slice_sql + alembic + ENUM + repo + gen-script regression
- [x] 94.1-02-PLAN.md — Wave 0 test scaffolding: compute-service + hooks + chip-decoupling + backfill + frontend tooltip

**Wave 1** *(blocked on Wave 0)*

- [x] 94.1-03-PLAN.md — Extract shared canonical_slice_sql module; refactor gen_global_percentile_cdf.py consumer (D-11)
- [x] 94.1-04-PLAN.md — Alembic migration (benchmark_metric ENUM + user_benchmark_percentiles table) + ORM model + repository

**Wave 2** *(blocked on Wave 1)*

- [x] 94.1-05-PLAN.md — Per-user compute service: compute_stage_a + compute_stage_b with Sentry isolation

**Wave 3** *(blocked on Wave 2)*

- [x] 94.1-06-PLAN.md — Stage A hook in import_service._complete_import_job + Stage B hook in eval_drain post-commit

**Wave 4** *(blocked on Waves 1 + 3)*

- [x] 94.1-07-PLAN.md — endgame_service chip rewire + PercentileChip tooltip canonical-slice clarifier
- [x] 94.1-08-PLAN.md — Backfill script (--target dev|prod) + final phase ship gate (blocking human-verify)

**Wave 5** *(gap closure from 94.1-VERIFICATION.md — parallel)*

- [x] 94.1-09-PLAN.md — CRITICAL: fix selected_users_cte bindparam bug (`:user_id::int` → `CAST(:user_id AS int)`) + lift skipped happy-path & SC-7 parity tests + new real-data integration test + dev backfill HUMAN-UAT (closes VERIFICATION gap #1 + #2)
- [x] 94.1-12-PLAN.md — WR-01: collapse eval-drain N+1 to one aggregated `users_with_zero_pending` query + repository helper + unit test

**Wave 6** *(blocked on Wave 5 — IN-03 classifier fix shares the backfill script)*

- [x] 94.1-10-PLAN.md — IN-03: `_compute_and_count` classifier fix (return False on below-floor; remove dead row_before probe) + unit test driving all three branches

**Wave 7** *(blocked on Wave 5/6 — rename runs after backfill writes real rows)*

- [x] 94.1-11-PLAN.md — CR-01: rename `n_games` → `n_cells_floor` (reversible Alembic migration + ORM/repository/service/test renames + HUMAN-UAT). HUMAN-UAT superseded by Plan 13 (column being dropped); Task 3 (endgameOverview cache invalidation) remains valid and is preserved.

**Wave 8** *(blocked on Wave 7 — supersedes Plan 11's column rename)*

- [x] 94.1-13-PLAN.md — Drop `n_cells_floor` column entirely; refactor `_compute_metric_for_user` to single `apply_floor=True` query (fixes pre-floor avg bug; user 28 case: +0.1204 → −0.0322 for achievable_score_gap); add active-import gate to `users_with_zero_pending` (prevents Stage B re-fire mid-import); re-backfill dev DB. Gap surfaced during 94.1-11 HUMAN-UAT.

### Phase 94.2: Pooled-Per-User Percentile Redesign

**Goal**: Replace Phase 94.1's per-cell stratified methodology with a one-point-per-user pooled model on both the CDF construction side and the per-user lookup side. For every subject (cohort user during CDF generation; app user at lookup time), pool their games across all TCs played, capped at the most recent 1000 games per TC and ≤36 months old, then compute the metric once on that pool. Build the CDF as `percentile_cont` over those one-point-per-user values — a single globally pooled CDF per metric, representing the whole benchmark cohort's *current* state rather than an average across each user's rating journey. The app user looks up their pooled value against this same global CDF, so the chip answers "where I stand among all chess players, on my recent play" rather than today's "average across the (elo_bucket, tc_bucket) cells I've ever played in." Inclusion floor is a single ≥30-games threshold on the pooled set (≥30 endgame + ≥30 non-endgame for `score_gap`; ≥30 entry-eval games for `achievable_score_gap`; ≥30 spans/bucket for `section2_score_gap_conv` / `_parity`). Acknowledged tradeoff: percentile correlates with rating because the underlying metrics correlate with rating — chosen intentionally so the chip honestly reads as "where you stand," not "where you stand controlled for your level." Phase 94.1's apply_floor=True per-cell behaviour is superseded but remains a valid intermediate state through the redesign rollout. Detailed design rationale, code touchpoints, and the rejected ELO-conditioned alternative captured in `.planning/notes/per-user-percentile-pooled-redesign.md`.
**Depends on**: Phase 94.1 (consumes `user_benchmark_percentiles` table + Stage A/B trigger pattern + backfill script harness; replaces the per-cell `_compute_metric_for_user` implementation and `gen_global_percentile_cdf.py` CDF construction query)
**Requirements**: PCTL-08, PCTL-09 (methodology refresh — value/percentile semantics shift)
**Success Criteria** (what must be TRUE):

  1. The canonical-slice CTE machinery (`app/services/canonical_slice_sql.py`) produces a single pooled aggregate per subject rather than one row per `(user_id, elo_bucket, tc_bucket)` cell. The recent-1000-per-TC cap and ≤36-month recency filter are applied identically on the benchmark and single_user code paths. `apply_floor` dual-mode is removed; a single inclusion-floor gate (≥30 of the metric-relevant unit) is applied on the pool. Drift between the two paths remains structurally impossible — the same shared SQL builder is used by both `scripts/gen_global_percentile_cdf.py` and `app/services/user_benchmark_percentiles_service.py`.
  2. `scripts/gen_global_percentile_cdf.py:_build_metric_breakpoint_query` builds the CDF from one row per cohort user (deduped across `(rating_bucket, tc_bucket)` selection slots), not one row per cell. The `n_users` label in `global_percentile_cdf.CdfTable` now accurately reflects the distinct-user count. The byte-identical regression test (`tests/scripts/test_gen_global_percentile_cdf_unchanged.py`) is regenerated against the new goldens — the prior cell-based goldens are no longer authoritative.
  3. `app/services/user_benchmark_percentiles_service._compute_metric_for_user` runs a single pooled query and stores the pooled value. The `n_cells_floor` concept and the `apply_floor` argument are removed from the codebase. The Plan 13 correctness fix (single floor-passing query) is moot under the new model because there are no cells to average — verified by inspection.
  4. `app/services/global_percentile_cdf.py:GLOBAL_PERCENTILE_CDF` is regenerated against the new methodology and committed. The numeric breakpoints will shift materially from the Phase 93 / 94.1 values — that drift is expected and documented in the regen report.
  5. The backfill script `scripts/backfill_user_percentiles.py` is updated to use the new compute path and is re-run against dev (and prod via tunnel after sign-off) so existing users' stored `(value, percentile)` rows reflect the new methodology. The summary table emitted by the backfill script shows users-included / floor-rejected counts per metric.
  6. `.claude/skills/benchmarks/SKILL.md` methodology chapter is updated to describe the one-point-per-user pooled model. The Chapter 4 cohort-construction description, the per-metric inclusion-floor table, and any diagrams referencing per-cell stratification are revised. Cross-references from Phase 94.1's CONTEXT.md / PLAN.md remain valid as historical context but are flagged as superseded methodology where they describe per-cell behaviour.
  7. The `PercentileChip` tooltip copy is reviewed against the new semantics — the "canonical-slice career" framing becomes "your recent play vs the whole cohort." Any UI copy that previously hinted at per-bucket averaging is corrected. No frontend logic changes (the chip still reads from `user_benchmark_percentiles.percentile`); only copy.
  8. An open-question investigation is captured during planning: after collapsing the benchmark cohort to one row per `lichess_username`, what is the distinct-user count per metric and how do the tails (`p1` / `p99`) behave? If a metric's deduped cohort drops below a stability threshold (TBD during planning), surface it as a planning blocker rather than shipping an unstable CDF.

**UI hint**: yes (tooltip copy only — no new UI primitives)

**Plans:** 6/6 plans complete

Plans:
**Wave 1** *(atomic cutover — three plans, single PR, no incoherent intermediate state)*

- [x] 94.2-01-PLAN.md — Refactor canonical_slice_sql.py: collapse per-cell to pooled-per-user; drop apply_floor + n_cells_floor + per-row sparse exclusion; add recent-1000-per-TC cap + 36-month recency + snapshot_date kwarg; dedup benchmark cohort by lichess_username per D-1
- [x] 94.2-02-PLAN.md — Rewrite gen_global_percentile_cdf.py:_build_metric_breakpoint_query to consume pooled shape; add --snapshot-date CLI flag; regenerate GLOBAL_PERCENTILE_CDF literal against benchmark DB; archive prior 94.1 report; regenerate byte-identical regression goldens
- [x] 94.2-03-PLAN.md — Rewrite _compute_metric_for_user to single pooled query; drop apply_floor; preserve Stage A/B trigger contract; update user_benchmark_percentile.py n_games docstring

**Wave 2** *(blocked on Wave 1 — independent downstream updates, parallel-safe)*

- [x] 94.2-04-PLAN.md — Rewrite .claude/skills/benchmarks/SKILL.md Chapter 1 + Chapter 4 for pooled-per-user methodology; flag 94.1 per-cell content as superseded
- [x] 94.2-05-PLAN.md — Widen PercentileChip flavor enum to 4 metric-named variants; rewrite popover body for D-4 disclosure (benchmark composition + recent-games basis + filter independence + per-metric rating-correlation framing per Cohen'''s d); update 4 call sites in EndgameOverallPerformanceSection.tsx + EndgameMetricCard.tsx

**Wave 3** *(blocked on Wave 1 — DB-touching, HUMAN-UAT on prod step)*

- [x] 94.2-06-PLAN.md — Update backfill_user_percentiles.py _MetricSummary classification for pooled semantics; run dev backfill; HUMAN-UAT checkpoint for prod backfill via bin/prod_db_tunnel.sh

### Phase 94.3: Per-TC Percentile Chips on Time Pressure Cards (INSERTED — SEED-025)

**Goal**: Extend the Phase 94.2 pooled-per-user percentile contract to the Time Pressure section, where the card structure is per-TC by construction (bullet / blitz / rapid / classical) and the user-meaningful comparison is "top X% of *bullet* players", not "top X% of all players". Add 12 new metrics to the `user_benchmark_percentiles` ENUM — `{time_pressure_score_gap, clock_gap, net_flag_rate}_{bullet, blitz, rapid, classical}` — each computed via the existing pooled-per-user methodology *parameterised by TC* (the per-TC CDF restricts the pool to one TC, all other knobs verbatim from 94.2: universal filters, ±100 equal-footing, 36-month recency, 1000/TC cap). Time Pressure Score Gap is a *binary collapse* of the existing per-quintile bullet chart — `score(user-pressured games) − score(opp-pressured games)` where pressured = `clock_pct < 40%` at endgame entry — chosen over a per-(TC, quintile) decomposition to avoid mixed-construct CDFs from inclusion-floor variance. Three new per-TC pooled-aggregate SQL builder families added to `app/services/canonical_slice_sql.py`, consumed by both `scripts/gen_global_percentile_cdf.py` (12 new CDF keys) and `app/services/user_benchmark_percentiles_service.py` (12 new compute calls). All 12 metrics run in **Stage B** (post-cold-drain) because Time Pressure Score Gap + Clock Gap both depend on Stockfish eval for endgame-entry detection (Net Flag Rate could be Stage A but bundles with Stage B to avoid a special-case hook). Backfill script extended for one-shot population. Frontend reuses `PercentileChip` verbatim — three chip slots on each of the 4 `TimePressureTcCard` headers, tooltip copy follows the 4-bullet disclosure mandate per `feedback_percentile_chip_tooltip_disclosure` with the first two bullets TC-scoped. No schema change. Per-quintile bullet chart beneath the chip is unchanged. Detailed design, rejected alternatives, open design questions, and tier rationale captured in `.planning/seeds/SEED-025-per-tc-percentile-annotations-time-pressure.md`.
**Depends on**: Phase 94.2 (consumes pooled-per-user methodology, `canonical_slice_sql.py` shared builders, `user_benchmark_percentiles` storage contract, Stage A/B trigger pattern, backfill harness, `PercentileChip` component + tooltip disclosure contract); Phase 88/88.4 (`TimePressureTcCard` schema + per-quintile bullet chart)
**Requirements**: SEED-025, TPCTL-01, TPCTL-02, TPCTL-03, TPCTL-04, TPCTL-05, TPCTL-06, TPCTL-07
**Success Criteria** (what must be TRUE):

  1. `app/services/canonical_slice_sql.py` exposes three new per-TC pooled-aggregate SQL builder families (`time_pressure_score_gap`, `clock_gap`, `net_flag_rate`) parameterised by TC. Each builder restricts the pool to one TC and otherwise reuses verbatim the 94.2 universal-filter / equal-footing / 36-month-recency / 1000/TC-cap pipeline. Both `scripts/gen_global_percentile_cdf.py` (CDF construction) and `app/services/user_benchmark_percentiles_service.py` (per-user lookup) consume the same shared builder for each metric — drift is structurally impossible.
  2. The `benchmark_metric` ENUM in the `user_benchmark_percentiles` table is extended with 12 new values (`{metric_base}_{tc}` for the 3 metric families × 4 TCs) via a reversible Alembic migration. No other schema change. The Phase 94.2 row shape (`value`, `percentile`, `n_games`, `cdf_snapshot`, `computed_at`) is reused verbatim.
  3. `app/services/global_percentile_cdf.py:GLOBAL_PERCENTILE_CDF` gains 12 new entries — one CDF per `(metric_base, tc)` pair, p1..p99 breakpoints (matching Phase 94 chip resolution). Per-TC cohort sizes are smaller than the global pool; tail-SE widening at extremes is the documented trade-off for methodological parity with the global chip surface. `interpolate_percentile(metric_id, value)` dispatches on the metric ENUM verbatim — no signature change.
  4. All 12 per-user computations run in Stage B (post-cold-drain) — Time Pressure Score Gap and Clock Gap both require Stockfish-eval-derived endgame-entry detection. Net Flag Rate bundles with Stage B for hook simplicity despite being outcome-only.
  5. `scripts/backfill_user_percentiles.py` is extended with the 12 new metrics and re-run against dev (and prod via tunnel after sign-off). Backfill summary shows users-included / floor-rejected counts per (metric × TC).
  6. Each `TimePressureTcCard` header renders three `PercentileChip` instances (one per metric), gated on inclusion-floor reliability — below floor, no chip renders. Mobile + desktop parity. Per-quintile bullet chart beneath each chip is unchanged. The 4-bullet tooltip disclosure (per `feedback_percentile_chip_tooltip_disclosure`) is satisfied with the first two bullets TC-scoped ("Calibrated against benchmarked Lichess players in {tc}, all ratings", "Uses your most recent 1000 games in {tc} (last 36 months)") and the fourth bullet (rating-correlation framing) populated from a discuss-step extension of `reports/benchmarks-gap-metrics-percentile-candidacy.md` covering the 12 new (metric × TC) cells.
  7. Open design questions from SEED-025 §Open Design Questions are resolved during the discuss step: (a) Net Flag Rate chip direction (lower-is-better — popover prose, not just "top X%"); (b) Clock Gap signed-metric semantics ("top 5%" = most clock-advantage, confirmed against user phrasing); (c) inclusion floor for Time Pressure Score Gap (≥30 per pressured cell starting point, tuned against benchmark cohort coverage); (d) <40% cutpoint validation against benchmark-data score-gap-vs-cutpoint curve; (e) per-(metric × TC) Cohen's d table for tooltip-copy calibration.

**UI hint**: yes (3 new chip slots × 4 cards = 12 chip placements; per-quintile bullet chart unchanged; tooltip copy is new prose per chip variant)

**Plans:** 6/6 plans complete

Plans:
**Wave 0** *(research-time candidacy extension)*

- [x] 94.3-01-PLAN.md — Extend `reports/benchmarks-gap-metrics-percentile-candidacy.md` with a 12-cell (metric × TC) Cohen's d candidacy table; feeds Plan 06's per-chip tooltip 4th-bullet copy

**Wave 1** *(atomic cutover — three plans, single PR, three sequential commits; no incoherent intermediate state on `main`)*

- [x] 94.3-02-PLAN.md — `canonical_slice_sql.py`: add 3 new per-TC pooled-aggregate SQL builder families (`per_user_cte_time_pressure_score_gap`, `per_user_cte_clock_gap`, `per_user_cte_net_flag_rate`) parameterised by `tc: TimeControlBucket`; widen `per_user_cte_for` dispatcher with 12 new arms; pytest goldens + parity tests for all 12 (metric × TC) cells
- [x] 94.3-03-PLAN.md — `scripts/gen_global_percentile_cdf.py` + `app/services/global_percentile_cdf.py`: widen `CdfMetricId` + `IN_SCOPE_METRICS` from 4 to 16; widen `_registry_entry_comment` / `_metric_display_name`; regenerate `GLOBAL_PERCENTILE_CDF` literal + byte-identical regression goldens + fresh `reports/global-percentile-cdf-latest.md`
- [x] 94.3-04-PLAN.md — Alembic ENUM extension migration (12 new values, downgrade no-op stub per RESEARCH §Pattern 2) + Stage B compute widening (`STAGE_B_METRICS` 3 → 15) + `TimePressureTcCard` schema (3 new nullable fields) + `endgame_service._compute_time_pressure_cards` percentile attach + frontend type codegen

**Wave 2** *(parallel-safe after Wave 1 merges to main)*

- [x] 94.3-05-PLAN.md — `scripts/backfill_user_percentiles.py`: widen `--metric` argparse choices to 16; dev rerun (autonomous); prod rerun gated by blocking HUMAN-UAT checkpoint via `bin/prod_db_tunnel.sh`
- [x] 94.3-06-PLAN.md — Frontend: `PercentileChip` flavor widening (4 → 16) + `DIRECTION_BY_FLAVOR` map + direction-branched rendering helpers + Net Flag "Lower is better" prepended popover line + TC-scoped popover bullets 1 + 2 + 3 chip slots wired on each of the 4 `TimePressureTcCard` instances + ≥ 25 new Vitest cases + mobile-parity audit at 375px

### Phase 94.4: Peer-Relative Percentile Chip Refinement (INSERTED — SEED-026 v2)

**Goal**: Pivot the percentile chip from global-pool ("vs all benchmark users") to peer-relative ("vs same-rated-cohort users"). Two arguments drive the pivot: (a) global percentile is largely redundant with what the zone band already shows visually (band is centered on benchmark-population typical range, so global percentile is the band position numericized); (b) peer-relative makes the chip coherent across rating-coupled metrics — within-cohort comparison removes the rating-echo failure mode that v1 of this seed worked around by dropping Conversion / Recovery / Endgame Score Gap chips. Cohort assignment uses a single rating anchor per (user, TC) — median rating over the user's latest ~1000 games at that TC, Lichess wins precedence over chess.com. chess.com inputs are converted via a hardcoded snapshot of **ChessGoals Table 2** (https://chessgoals.com/rating-comparison/, snapshot-dated module constant in `app/services/chesscom_to_lichess.py`) because no principled closed-form chess.com↔Lichess conversion exists. Cohort CDFs are precomputed at 50-Elo anchors (800, 850, ..., 2400) as sliding windows of K=200 floor-passing users per (metric, anchor, TC), ranked by user-anchor distance; if the K-th user falls beyond ±150 Elo the anchor suppresses. The live user's per-TC anchor rounds to nearest 50 and looks up directly — no interpolation step. All metrics use the same per-(metric, anchor, TC) shape — TC-stratified metrics consume one CDF; previously-TC-aggregated metrics (`score_gap`, `achievable_score_gap`, the 2 Section-2 metrics) compute per-TC sub-percentiles aggregated via game-count-weighted mean. Chip UX shrinks to `p23`/`23%` pill + tooltip-only; tooltip leads with cohort framing ("Compared to other ~1600-rated players") and rating-anchor disclosure ("Anchored on your Lichess rapid rating; chess.com ratings converted to Lichess-equivalent"). Metric eligibility re-opened — Conversion / Recovery / Endgame Score Gap chips rescued under peer-relative framing. Storage shape on `user_benchmark_percentiles` unchanged (still one scalar percentile per (user, metric)). Detailed design, error budget, open questions, and rejected alternatives captured in `.planning/seeds/SEED-026-percentile-chip-refinement.md`.
**Depends on**: Phase 94.2 (consumes pooled-per-user `user_benchmark_percentiles` storage contract, Stage A/B trigger pattern, backfill harness, `PercentileChip` component + tooltip disclosure contract); Phase 94.3 (per-TC sub-percentile compute pattern in `canonical_slice_sql.py` extends to the 4 previously-TC-aggregated metrics). Supersedes SEED-019 § "Final Tier-1 chip set" once shipped.
**Requirements**: SEED-026, TBD (refine at /gsd-discuss-phase 94.4 — likely chip-eligibility, conversion-table, cohort-CDF, rating-anchor, UX-shrink, tooltip-copy buckets)
**Success Criteria** (what must be TRUE):

  1. `scripts/gen_global_percentile_cdf.py` (or sibling `gen_cohort_percentile_cdf.py`) emits per-(metric, ELO anchor, TC) cohort CDF tables under the 50-Elo sliding-window protocol (K=200 floor-passing users per anchor, ±150-Elo max window, suppress otherwise). Approximate count: ~16 chip-eligible metrics × ~33 anchors × 4 TCs ≈ ~2,000 CdfTable instances, minus suppressed anchors. Each CDF is 99 floats. The pooled global CDF artifact is replaced (not extended) — the `GLOBAL_PERCENTILE_CDF` registry retires.
  2. A new `app/services/chesscom_to_lichess.py` module ships the ChessGoals Table 2 snapshot (`CHESSCOM_BLITZ_TO_LICHESS`) and Table 1 intra-chess.com offsets (`CHESSCOM_INTRA_TC`) as typed Python constants with snapshot-date + source-URL module constants. `convert_chesscom_to_lichess(rating, source_tc, target_tc)` covers chess.com Blitz directly and Bullet/Rapid via Table 1 inversion. Daily returns None (caller suppresses chip).
  3. A per-(user, TC) rating-anchor compute runs at import time (Stage A or alongside it), producing up to 4 anchors per user. Reads `games.white_rating`/`games.black_rating` for the user's latest ~1000 games per TC, applies Lichess-first precedence, falls back to ChessGoals conversion for chess.com-only TCs. Anchors stored for tooltip-disclosure visibility (lean: new `user_rating_anchors` table).
  4. TC-stratified metric lookup replaces `interpolate_percentile(metric, value)` with `interpolate_cohort_percentile(metric, per_tc_value, elo_anchor_for_tc, tc)`. Previously-TC-aggregated metrics compute up to 4 per-TC sub-percentiles and aggregate via game-count-weighted mean — output shape on `user_benchmark_percentiles` unchanged (still one scalar percentile per (user, metric) row). Per-TC user-scalar CTEs for the 4 `_score_gap` family metrics added to `canonical_slice_sql.py`, mirroring the Phase 94.3 per-TC CTE pattern.
  5. Metric eligibility re-evaluated under peer-relative framing. Endgame Score Gap, Conversion Score Gap, Recovery Score Gap all rescue from v1's drop list (peer-relative absorbs ELO coupling). Best-guess surviving set: ~7-12 chip surface (page-level: Endgame / Achievable / Parity / Conversion / Recovery Score Gap; per-TC: Clock Gap, Net Flag Rate, Time Pressure Score Gap × 4 TCs). Final set locked at /gsd-discuss-phase time against the peer-relative tooltip-copy honesty check.
  6. Chip UX shrinks from "Bottom 23%" / "Top 5%" verbose form to `p23` (or `23%` — locked at discuss) small pill, ~24px tall, mobile-comfortable, reads as a side-note. Visual emphasis stays on the metric value + zone band.
  7. Tooltip copy reworked per peer-relative framing: leads with cohort phrasing ("Compared to other ~1600-rated players. Independent of your filter settings."), discloses rating anchor source ("Anchored on your Lichess rapid rating; chess.com ratings converted to Lichess-equivalent."), drops the v1 per-metric rating-correlation copy. Recent-N-games disclosure preserved. Satisfies `feedback_percentile_chip_tooltip_disclosure` under new framing.
  8. SEED-019 § "Final Tier-1 chip set" marked superseded; historical Cohen's d / Spearman ρ analysis preserved as context (no longer load-bearing — cohort absorbs coupling).
  9. UAT confirms credibility-recovery on elite users: a 2400-rated user landing at `p15` Endgame Score Gap reads as "even compared to other 2400s, your endgame is unusually unbalanced" rather than "FlawChess thinks I'm bad at chess."

**UI hint**: yes (chip shrink to pill across all chip surfaces, mobile + desktop parity; tooltip copy rewrite; new chip slots if Endgame/Conversion/Recovery rescue lands; rating-anchor disclosure surface)

**Plans**: 10 plans (Plan 05 split into 05a/05b/05c per checker B5 — atomic cutover preserved at PR level via depends_on + same-PR squash)

Plans:
- [x] 94.4-01-PLAN.md — chesscom_to_lichess.py conversion module + 3 ChessGoals tables + USCF/FIDE accessors per D-14
- [x] 94.4-02-PLAN.md — user_rating_anchors table (+ chesscom_raw_rating column per D-07 bullet 4) + Alembic migration + median-anchor SQL builder
- [x] 94.4-03-PLAN.md — 4 new per-TC ΔES SQL builders + Pitfall 1 user_id widening across all 7 per-TC builders
- [x] 94.4-04-PLAN.md — cohort CDF regen (8 metrics × ~33 anchors × 4 TCs) + suppression-flag report + HUMAN-VERIFY checkpoint per D-11
- [x] 94.4-05a-PLAN.md — user_benchmark_percentiles schema reshape (drop/recreate per D-02) + 8-value ENUM + 3-column PK + repository nested-dict fetch
- [x] 94.4-05b-PLAN.md — Stage A/B service rewrite (compute_anchors_for_user + chesscom_raw_rating capture per D-07 bullet 4) + legacy-stub retirement
- [x] 94.4-05c-PLAN.md — API shaper _aggregate_per_tc_percentile per D-08/D-08b + RatingAnchorOut schema + frontend type regen + terminal Pre-PR sweep
- [x] 94.4-06-PLAN.md — backfill script extension + dev rerun + prod rerun via tunnel after HUMAN-UAT (PRPCR-09 credibility check)
- [x] 94.4-07-PLAN.md — PercentileChip rewrite (p23 face, NO flame, 8 flavors + tc prop, 4-bullet peer-relative popover) + 4 component reshapes
- [x] 94.4-08-PLAN.md — SEED-019 supersession banner + feedback_percentile_chip_tooltip_disclosure amendment + CHANGELOG

### Phase 95: LLM Endgame-Insights Statistical-Reasoning Rework

**Goal**: Rework the endgame-insights LLM payload + prompt so the model reasons explicitly over the v1.17 statistical-rigor metric set (Phase 85.1 / 86 / 87.2 / 87.6 / 88 — Endgame Score Gap & Achievable Score family, Section 2 ΔES Score Gap family, Time Pressure hypothesis tests) using p-values, confidence interval bounds, and the new Phase 94 percentile annotations. Preserve the prior `feedback_llm_significance_signal` decision — the cohort `zone` field remains the gate on whether a metric is narrated; CIs / p-values / percentiles inform *how* once a zone-driven narration decision has been made. Bump the endgame prompt version from `endgame_v35`, leave cache invalidation to the `_PROMPT_VERSION` cache key, and validate via at least one UAT pass over representative production users.
**Depends on**: Phase 94 (LLM-05 percentile narration requires PCTL-02 emission)
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07
**Success Criteria** (what must be TRUE):

  1. The endgame-insights API payload exposes per-metric p-values, confidence interval bounds, and percentile fields on the v1.17 statistical-rigor metric set, additive and non-breaking alongside existing `zone` + `sample_quality` fields.
  2. The endgame-insights system prompt teaches the LLM to reason explicitly over CIs and percentiles in narration (e.g. "your value sits at X with 95% CI [Y, Z], top P% of all players") without re-licensing the small-but-significant narration pattern from `feedback_llm_significance_signal`.
  3. The `feedback_llm_significance_signal` tension is explicitly resolved with the chosen strategy (tighter cohort bands vs. raw-stat passthrough with prompt guardrails) recorded in the phase decision log, with both alternatives considered.
  4. At least Section 1 Endgame Score Gap & Achievable Score Gap, Section 2 ΔES Score Gap family, and Time Pressure score-curve verdicts narrate visibly differently — and better — than under `endgame_v35`, verified via UAT against short-history, sparse-section, and full-history production users.
  5. The endgame prompt version bumps cleanly from `endgame_v35` and prior cached reports remain valid until their `_PROMPT_VERSION` cache key naturally invalidates.

**Plans**: TBD

<details>
<summary>✅ v1.18 Import Pipeline Hardening (Phases 90-92) — SHIPPED 2026-05-22</summary>

- [x] Phase 90: Import Pipeline Memory Leak Fix + Resilience (3/3 plans, PR #130) — completed 2026-05-20
- [x] Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain (8/8 plans, PR #137) — completed 2026-05-21
- [x] Phase 92: Custom date range filter (from/to dates replace closed Recency union) (6/6 plans, PR #138) — completed 2026-05-22

</details>

<details>
<summary>✅ v1.17 Endgame Stats Card Redesign (Phases 84-88.4) — SHIPPED 2026-05-19</summary>

- [x] Phase 84: Data plumbing — mirror-rate audit (1/1 plan, PR #95) — completed 2026-05-13
- [x] Phase 85: Section 1 — Games with vs without Endgame / 3-card composite (5/5 plans) — shipped 2026-05-14
- [x] Phase 85.1: Hypothesis tests + 95% CIs for Endgame Score Differences (4/4 plans; INSERTED) — shipped 2026-05-14
- [x] Phase 86: Section 2 — Endgame Metrics 4-card layout (5/5 plans) — shipped 2026-05-14
- [x] Phase 87: Section 3 — Per-type Endgame Type Breakdown cards (3/3 plans) — shipped 2026-05-15
- [x] Phase 87.1: Per-span ΔES metric for endgame types (4/4 plans, PR #97; INSERTED) — completed 2026-05-15
- [x] Phase 87.2: Section 2 — eval-based ΔES Score Gap bullets (4/4 plans, PR #98; INSERTED) — completed 2026-05-16
- [~] Phase 87.3: Endgame Skill v2 — Conv+Parity percentile composite (INSERTED) — **superseded** by Phase 87.4 (PR #102)
- [x] Phase 87.4: Drop Endgame Skill — Conversion ELO timeline (3/3 plans, PR #104; INSERTED) — completed 2026-05-16
- [x] Phase 87.5: Rebuild Endgame ELO on Endgame Score Gap (3/3 plans, PR #105; INSERTED) — completed 2026-05-17
- [x] Phase 87.6: Endgame ELO via logistic stretch around Actual ELO (3/3 plans, PR #106; INSERTED) — completed 2026-05-18
- [x] Phase 88: Time Pressure stats rework with hypothesis tests + CIs (15/15 plans, PR #107; INSERTED) — completed 2026-05-18
- [x] Phase 88.3: Endgame Stats viz refinements — inactivity-gap annotations + Overall Performance card (4/4 plans, PR #108; INSERTED) — completed 2026-05-18
- [x] Phase 88.4: Time Pressure card layout refactor (3/3 plans, PR #109; INSERTED) — completed 2026-05-19
- [→] Phase 89: Polish — popovers, gating decisions, automation rules, 375px parity — **dropped from scope** 2026-05-19 (not needed)

See [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.16 Stockfish Eval Analyses (Phases 80, 80.1, 81, 82, 83) — SHIPPED 2026-05-11</summary>

- [x] Phase 80: Opening stats: middlegame-entry eval and clock-diff columns (6/6 plans) — completed 2026-05-05 (PR #80)
- [x] Phase 80.1: Include transpositions in Move Explorer and Opening Insights stats (4/4 plans) — completed 2026-05-07 (PR #82)
- [x] Phase 81: Endgame Start vs End — twin-tile section above the WDL table (5/5 plans) — completed 2026-05-09 (PR #85)
- [x] Phase 82: LLM prompt awareness of Endgame Start vs End metrics (4/4 plans) — completed 2026-05-10 (PR #86)
- [x] Phase 83: Stockfish-baseline predicted endgame score (5/5 plans) — completed 2026-05-11 (PR #88)

See [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2024-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2024-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2024-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2024-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2024-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2024-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2024-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2024-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2024-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2024-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2024-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2024-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2024-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2024-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2024-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2024-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2024-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2024-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2024-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2024-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2024-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2024-03-21

</details>

<details>
<summary>✅ v1.3 Project Launch (Phases 20-23) — SHIPPED 2026-03-22</summary>

- [x] Phase 20: Rename & Branding (2/2 plans) — completed 2026-03-21
- [x] Phase 21: Docker & Deployment (2/2 plans) — completed 2026-03-21
- [x] Phase 22: CI/CD & Monitoring (2/2 plans) — completed 2026-03-21
- [x] Phase 23: Launch Readiness (4/4 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.4 Improvements (Phase 24) — SHIPPED 2026-03-22</summary>

- [x] Phase 24: Web Analytics (2/2 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.5 Game Statistics & Endgame Analysis (Phases 26-33) — SHIPPED 2026-03-28</summary>

- [x] Phase 26: Position Classifier & Schema (2/2 plans) — completed 2026-03-23
- [x] Phase 27: Import Wiring & Backfill (2/2 plans) — completed 2026-03-24
- [x] Phase 27.1: Optimize game_positions columns (via quick tasks) — completed 2026-03-26
- [x] Phase 28: Engine Analysis Import (2/3 plans, 28-03 deferred) — completed 2026-03-25
- [x] Phase 28.1: Import lichess analysis metrics (1/1 plan) — completed 2026-03-26
- [x] Phase 29: Endgame Analytics (3/3 plans) — completed 2026-03-26
- [x] Phase 31: Endgame classification redesign (2/2 plans) — completed 2026-03-26
- [x] Phase 32: Endgame Performance Charts (3/3 plans) — completed 2026-03-27
- [x] Phase 33: Homepage, README & SEO Update (3/3 plans) — completed 2026-03-28

</details>

<details>
<summary>✅ v1.6 UI Polish & Improvements (Phases 34-39) — SHIPPED 2026-03-30</summary>

- [x] Phase 34: Theme Improvements (2/2 plans) — completed 2026-03-28
- [x] Phase 35: WDL Chart Refactoring (2/2 plans) — completed 2026-03-28
- [x] Phase 36: Most Played Openings (1/1 plan) — completed 2026-03-28
- [x] Phase 37: Openings Reference Table & Redesign (3/3 plans) — completed 2026-03-28
- [x] Phase 38: Opening Statistics & Bookmark Rework (2/2 plans) — completed 2026-03-29
- [x] Phase 39: Mobile Opening Explorer Sidebars (1/1 plan) — completed 2026-03-30

</details>

<details>
<summary>✅ v1.7 Consolidation, Tooling & Refactoring (Phases 40-43) — SHIPPED 2026-04-03</summary>

- [x] Phase 40: Static Type Checking (2/2 plans) — completed 2026-04-01
- [x] Phase 41: Code Quality & Dead Code (4/4 plans) — completed 2026-04-02
- [x] Phase 41.1: Import Speed Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 42: Backend Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 43: Frontend Cleanup (1/1 plan) — completed 2026-04-03

</details>

<details>
<summary>✅ v1.8 Guest Access (Phases 44-47) — SHIPPED 2026-04-06</summary>

- [x] Phase 44: Guest Session Foundation — completed 2026-04-06
- [x] Phase 45: Guest Frontend — completed 2026-04-06
- [x] Phase 46: Email/Password Promotion — completed 2026-04-06
- [x] Phase 47: Google SSO Promotion — completed 2026-04-06

</details>

<details>
<summary>✅ v1.9 UI/UX Restructuring (Phases 49-51) — SHIPPED 2026-04-10</summary>

- [x] Phase 49: Openings Desktop Sidebar (1/1 plan) — completed 2026-04-09
- [x] Phase 50: Mobile Layout Restructuring (2/2 plans) — completed 2026-04-10
- [x] Phase 51: Stats Subtab, Homepage & Global Stats (4/4 plans) — completed 2026-04-10

See [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.10 Advanced Analytics (Phases 48, 52-55, 57, 57.1, 59-62) — SHIPPED 2026-04-19</summary>

- [x] Phase 48: Conversion & Recovery Persistence Filter (2/2 plans) — completed 2026-04-07
- [x] Phase 52: Endgame Tab Performance (3/3 plans) — completed 2026-04-11
- [x] Phase 53: Endgame Score Gap & Material Breakdown (2/2 plans) — completed 2026-04-12
- [x] Phase 54: Time Pressure — Clock Stats Table (2/2 plans) — completed 2026-04-12
- [x] Phase 55: Time Pressure — Performance Chart (2/2 plans) — completed 2026-04-12
- [~] Phase 56: Endgame ELO Backend + Breakdown Table — cancelled, subsumed by Phase 57
- [x] Phase 57: Endgame ELO Timeline Chart (2/2 plans) — completed 2026-04-18
- [x] Phase 57.1: Endgame ELO Timeline Anchor Change + Volume Bars (2/2 plans, INSERTED) — completed 2026-04-18
- [→] Phase 58: Opening Risk & Drawishness — moved to backlog as Phase 999.6
- [x] Phase 59: Fix Endgame Conv/Parity/Recov per-game stats (3/3 plans) — completed 2026-04-13
- [x] Phase 60: Opponent-based Baseline for Endgame Conv/Recov (2/2 plans) — completed 2026-04-14
- [x] Phase 61: Test Suite Hardening & DB Reset (3/3 plans) — completed 2026-04-16
- [x] Phase 62: Admin User Impersonation (5/5 plans) — completed 2026-04-17

See [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.11 LLM-first Endgame Insights (Phases 63-68) — SHIPPED 2026-04-24</summary>

- [x] Phase 63: Findings Pipeline & Zone Wiring (5/5 plans) — completed 2026-04-20
- [x] Phase 64: `llm_logs` Table & Async Repo (3/3 plans) — completed 2026-04-20
- [x] Phase 65: LLM Endpoint with pydantic-ai Agent (6/6 plans) — completed 2026-04-21
- [x] Phase 66: Frontend EndgameInsightsBlock & Beta Flag (5/5 plans) — completed 2026-04-22
- [~] Phase 67: Validation & Beta Rollout — descoped, replaced by public rollout for all users (commit c91478e)
- [x] Phase 68: Endgame Score Timeline (dual-line + shaded gap) (4/4 plans) — completed 2026-04-24

See [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Phase 69) — SHIPPED 2026-04-26</summary>

- [x] Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline (6/6 plans) — completed 2026-04-26 via PR #65 — INFRA-01..03, INGEST-01..06

See [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.13 Opening Insights (Phases 70, 71, 71.1) — SHIPPED 2026-04-27</summary>

- [x] Phase 70: Backend opening insights service (5/5 plans) — completed 2026-04-26 via PR #66 — INSIGHT-CORE-01..09
- [x] Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` (6/6 plans) — completed 2026-04-27 via PR #67 — INSIGHT-STATS-01..06
- [x] Phase 71.1: Openings subnav layout refactor — match Endgames pattern (3/3 plans, INSERTED) — completed 2026-04-27 via PR #68
- [~] Phase 72: Frontend Moves subtab — inline weakness/strength bullets — descoped 2026-04-27 (covered by MoveExplorer row tint via `getArrowColor`)
- [~] Phase 73: Meta-recommendation aggregate finding (stretch) — descoped 2026-04-27 (per-finding cards in Phase 71 already deliver actionable signal)
- [~] Phase 74: Bookmark-card weakness badge (stretch) — descoped 2026-04-27 (alert-fatigue concern with existing nav notification dots)

See [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.14 Score-Based Opening Insights (Phases 75, 76, 77) — SHIPPED 2026-04-29</summary>

- [x] Phase 75: Backend — score metric and confidence annotation (4/4 plans) — completed 2026-04-28 (PR #69)
- [x] Phase 76: Frontend — score-based coloring, confidence badges, label reframe (8/8 plans) — completed 2026-04-28 (PR #70; inline confidence-mute hotfix PR #71)
- [x] Phase 77: Troll-opening watermark on Insights findings (4/4 plans) — completed 2026-04-28 (PR #72)

See [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.15 Eval-Based Endgame Classification (Phases 78, 79) — SHIPPED 2026-05-03</summary>

- [x] Phase 78: Stockfish-Eval Cutover for Endgame Classification (6/6 plans) — completed 2026-05-03 (PR #78) — ENG-01..03, FILL-01..04, IMP-01..02, REFAC-01..05, VAL-02 (VAL-01 rescinded)
- [x] Phase 79: Position-phase classifier and middlegame eval (4/4 plans) — completed 2026-05-03 (PR #78) — CLASS-01..02, SCHEMA-01..02, PHASE-IMP-01..02, PHASE-FILL-01..03, PHASE-VAL-02..03, PHASE-INV-01 (PHASE-VAL-01 rescinded)

See [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md) for full details.

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-10. v1.0 phases | v1.0 | 36/36 | Complete | 2024-03-15 |
| 11-16. v1.1 phases | v1.1 | 14/14 | Complete | 2024-03-18 |
| 17-19. v1.2 phases | v1.2 | 5/5 | Complete | 2024-03-21 |
| 20-23. v1.3 phases | v1.3 | 10/10 | Complete | 2026-03-22 |
| 24. Web Analytics | v1.4 | 2/2 | Complete | 2026-03-22 |
| 26-33. v1.5 phases | v1.5 | 18/19 | Complete (28-03 deferred) | 2026-03-28 |
| 34-39. v1.6 phases | v1.6 | 11/11 | Complete | 2026-03-30 |
| 40-43. v1.7 phases | v1.7 | 11/11 | Complete | 2026-04-03 |
| 44-47. v1.8 phases | v1.8 | N/A | Complete | 2026-04-06 |
| 49-51. v1.9 phases | v1.9 | 7/7 | Complete | 2026-04-10 |
| 48, 52-62. v1.10 phases | v1.10 | 28/28 | Complete | 2026-04-19 |
| 63-68. v1.11 phases | v1.11 | 23/23 | Complete (Phase 67 descoped) | 2026-04-24 |
| 69. Benchmark DB Infra & Ingestion | v1.12 | 6/6 | Complete (follow-on phases → SEED-006) | 2026-04-26 |
| 70-71.1. v1.13 phases | v1.13 | 14/14 | Complete (Phases 72/73/74 descoped) | 2026-04-27 |
| 75-77. v1.14 phases | v1.14 | 16/16 | Complete (INSIGHT-UI-04 descoped) | 2026-04-29 |
| 78-79. v1.15 phases | v1.15 | 10/10 | Complete (VAL-01 / PHASE-VAL-01 rescinded) | 2026-05-03 |
| 80-83. v1.16 phases | v1.16 | 24/24 | Complete | 2026-05-11 |
| 84-88.4. v1.17 phases | v1.17 | ~54/~54 | Complete (89 dropped, 87.3 superseded) | 2026-05-19 |
| 90-92. v1.18 phases | v1.18 | 17/17 | Complete | 2026-05-22 |
| 93. Global Percentile Benchmark Artifact | v1.19 | 2/2 | Complete    | 2026-05-22 |
| 94. Backend & Frontend Percentile Annotations | v1.19 | 3/3 | Complete   | 2026-05-23 |
| 95. LLM Endgame-Insights Statistical-Reasoning Rework | v1.19 | 0/TBD | Not started | - |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 5/6 plans executed

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.5: Hybrid Stockfish Eval for Conversion/Recovery (BACKLOG)

**Goal:** Use Stockfish eval (`eval_cp`) as the advantage/disadvantage signal for conversion/recovery classification when available, falling back to material imbalance + 4-ply persistence for games without eval. Stockfish eval is the gold standard (no persistence filter needed since eval handles transient trades natively). Currently only ~15% of Lichess games have eval data and chess.com has 0%, but this improves automatically as more games get server-analyzed. Validated in `docs/endgame-conversion-recovery-analysis.md`: persistence closes 50-70% of the gap to Stockfish for pawn/mixed endgames, but a hybrid approach would eliminate the remaining 5-8pp offset for eval-available games.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.4: Position-Based Most Played Openings via game_positions (BACKLOG)

**Goal:** Redesign "Most Played Openings" to count how many games *passed through* each opening position (via `game_positions` Zobrist hash matching) instead of counting final opening name classifications from chess.com/lichess. Currently "1. e4" shows ~75 games (only games *classified* as "King's Pawn Game") while obscure specific lines rank higher. Position-based counting would show all ~2000+ games that played 1. e4, consistent with FlawChess's core Zobrist hash architecture. Requires JOIN from `openings` reference table to `game_positions` on FEN or precomputed hash, then `COUNT(DISTINCT game_id)`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.6: Opening Risk & Drawishness (BACKLOG)

**Goal:** Risk and drawishness metrics per position in the move explorer.
**Requirements:** TBD
**Plans:** 0 plans
**Context:** Moved from v1.10 Advanced Analytics — v1.10 is an endgame-focused milestone and opening risk metrics are a better fit for the upcoming Opening Insights milestone (discovering weaknesses in most-played opening lines). Re-evaluate scope at that time.

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
