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
- ✅ **v1.19 Endgame Percentiles** — Phases 93, 94, 94.1, 94.2, 94.3, 94.4 (shipped 2026-05-27; Phase 95 split out before milestone close) — see [milestones/v1.19-ROADMAP.md](milestones/v1.19-ROADMAP.md)
- ✅ **v1.20 Import Pipeline Hardening Follow-Up and Readiness** — Phases 95, 96 (shipped 2026-05-29) — see [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md)
- 🔄 **v1.21 Time-Control-Aware Endgame Metrics** — Phases 97, 98, 99 (Phases 97, 98 shipped; 99 not started)
- 🔄 **v1.22 LLM Statistical Reasoning** — Phase 100 (not started)

## Phases

*v1.20 (Phases 95, 96) shipped 2026-05-29 — archived to [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md); see the collapsed block below.*

- [x] **Phase 97: Endgame Metrics by Time Control** *(v1.21)* — Replace the aggregated Conversion/Parity/Recovery gauge cards in the Endgame Metrics section with TC-specific cards (bullet/blitz/rapid/classical), mirroring the Time Pressure section's per-TC pattern. Conversion/Recovery gauges get TC-specific neutral bands (benchmark TC d≈0.9); Parity and Score Gap keep the shared global band (both collapse on TC). No aggregated cards remain; cards self-suppress below a min-games floor. Per-TC conversion/recovery percentile badges deferred to Phase 99. — shipped 2026-05-29 (PR #160; rating-anchor follow-up #158/#159).
- [x] **Phase 98: Per-TC Collapsible Endgame Type Cards** *(v1.21)* — Restructure the Endgame Type Breakdown from a 3-col grid of 5 per-type cards into **one full-width collapsible card per time control** (bullet/blitz/rapid/classical), chevron in the header, **most-active TC expanded by default**, the rest collapsed. Inside each TC card: a **2×2 grid of 4 type tiles** (rook/minor_piece/pawn/queen — **Mixed dropped** as the least-actionable catch-all). This is the TC-honest way to bring back the Conv/Recov gauges removed 2026-05-29: each tile shows that TC's own per-(class × TC) band (**no TC-mix blending** — supersedes the blended-band approach). **Score Gap is banded per-TC too, for visual consistency** — statistically it's TC-flat (d≈0.13) so the four bands will be near-identical, but it conceptually belongs to the type tile alongside Conv/Recov and gets one consistent card grammar (the known redundancy is chosen, not a bug). Per-TC sparsity suppression (a TC card / tile self-suppresses below the games floor, à la Lichess Tutor's 30-games-per-speed model). Applies the mode-3 "collapsible TC cards" pattern. See [notes/endgame-tc-disclosure-pattern.md](notes/endgame-tc-disclosure-pattern.md). — shipped 2026-05-30 (PR #163; deployed via release PR #164).
- [x] **Phase 99: Percentile Badges for Conversion, Parity, and Recovery** *(v1.21)* — Add peer-relative percentile chips (the v1.19 `PercentileChip` primitive) to the per-TC Conversion, Parity, and Recovery rate cards delivered in Phase 97. Deferred from Phase 97 because it requires new per-(metric, TC) cohort CDF materialization in `user_benchmark_percentiles` (today only ΔES score-gap percentiles exist there). Mirrors the Phase 94.3 Time Pressure per-TC chip pattern: 3 metric families × 4 TCs computed via pooled-per-user methodology parameterised by TC, cohort-matched on rating anchor, 4-bullet disclosure tooltip per `feedback_percentile_chip_tooltip_disclosure`. (completed 2026-05-30)
- [ ] **Phase 99.1: Move Cohort CDF Out of Source into a DB Table** *(v1.21)* — Refactor `app/services/global_percentile_cdf.py` (3.1 MB / 130k lines, of which only ~250 are logic) by moving the generated `COHORT_PERCENTILE_CDF` registry into a `benchmark_cohort_cdf` DB table. The lookup is background-only (`compute_stage_a/b`, ~32 calls per import), so `interpolate_cohort_percentile` becomes `async` and queries the table directly (no in-memory cache). The generator emits a compact seed file to `app/data/` instead of rewriting the `.py`; a manual idempotent seed script (`scripts/seed_cohort_cdf.py`, `ON CONFLICT DO UPDATE`, modeled on `seed_openings.py`) loads it, wired into `bin/run_local.sh`. Module shrinks to ~250 lines (keeps `CdfMetricId`, `CdfTable`, interpolation math). Also unlocks SQL analysis of the breakpoints. See [notes/phase-99-1-cdf-db-refactor.md](notes/phase-99-1-cdf-db-refactor.md).
- [ ] **Phase 100: LLM Endgame-Insights Statistical-Reasoning Rework** *(v1.22)* — Payload extension (p-values, CI bounds, percentiles) + prompt rewrite reasoning over CIs/percentiles with guardrails, prompt version bump from `endgame_v35`, UAT pass

## Phase Details

### Phase 97: Endgame Metrics by Time Control

**Goal**: Restructure the Endgame Metrics section of the Endgames page into per-time-control cards (bullet/blitz/rapid/classical), mirroring the existing `EndgameTimePressureSection` per-TC card pattern. Each TC card renders the Conversion/Parity/Recovery gauge trifecta plus WDL and Score Gap charts scoped to that time control. The single aggregated Conversion/Parity/Recovery cards are removed entirely (no aggregated cards on top). Conversion and Recovery gauges use **TC-specific neutral bands** (benchmark Cohen's d ≈ 0.9 on the TC axis — they genuinely differ per TC; bands sourced from `reports/benchmark/benchmarks-latest.md` §3.2.1 per-TC p25/p75); Parity keeps the shared global band and Score Gap keeps the shared global band (both collapse on the TC axis, d < 0.15, so a single band is correct for every TC). Cards self-suppress below a minimum-games floor because Conversion/Recovery are conditional rates with thin per-TC denominators. Requires a new backend aggregation path that computes per-TC conversion/recovery/parity rate values (only per-TC ΔES score-gap percentiles exist today) and a new TC-keyed band structure in `app/services/endgame_zones.py` regenerated into `frontend/src/generated/endgameZones.ts`. Per-TC conversion/recovery **percentile badges are deferred** to a follow-up phase (they would require new per-(metric, TC) CDF materialization in `user_benchmark_percentiles`).
**Depends on**: none (builds on the v1.19 per-TC percentile/anchor pipeline + v1.17 Endgame Metrics section)
**Requirements**: standalone — no requirement IDs (endgame stats UX refinement)
**Success Criteria** (what must be TRUE):

  1. The Endgame Metrics section renders one card per time control the user has sufficient games in (fixed order bullet/blitz/rapid/classical), with no aggregated Conversion/Parity/Recovery cards remaining.
  2. Each TC card shows the Conversion/Parity/Recovery gauge trifecta plus WDL and a Score Gap chart, all scoped to that time control.
  3. Conversion and Recovery gauge neutral bands are TC-specific (distinct per bullet/blitz/rapid/classical, calibrated from the latest benchmark per-TC p25/p75); Parity and Score Gap bands are the shared global bands on every card.
  4. Cards self-suppress below a minimum-games floor; the floor is chosen deliberately for conditional rates and validated against dev-DB distributions during planning.
  5. Per-TC conversion/parity/recovery rate values are computed by the backend and exposed via the endgame overview response; the TC-keyed bands are threaded to the frontend via the regenerated `endgameZones.ts` (CI drift gate green).
  6. Desktop and mobile layouts both render the per-TC cards responsively (mirroring `EndgameTimePressureSection`).
  7. Backend (`pytest`, `ty`, `ruff`) and frontend (`lint`, `test`, `knip`) gates all pass.

**Plans**: 4 plans
**Wave 1**

- [x] 97-01-PLAN.md — TC-keyed bands (`TC_METRIC_BANDS`) in `endgame_zones.py` + codegen into `endgameZones.ts`
- [x] 97-02-PLAN.md — Backend per-TC rate aggregation (`_compute_per_tc_metric_cards`) + `endgame_metrics_cards` overview field

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 97-03-PLAN.md — Frontend per-TC section + card (gauge/WDL/ΔES/percentile trifecta) wired into Endgames page

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 97-04-PLAN.md — Remove aggregated Metrics section + blended chip fields; knip-clean (Overall Performance chips preserved)

### Phase 98: Per-TC Collapsible Endgame Type Cards

**Goal**: Restructure the **Endgame Type Breakdown** section so time control is a per-card *view dimension* instead of either a pooled band or a TC-mix blend. Today `EndgameTypeBreakdownSection` renders a 3-col grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) of five per-type `EndgameTypeCard`s. Replace that with **one full-width collapsible card per time control** (bullet/blitz/rapid/classical), each with a chevron in its header, the **user's primary TC expanded by default** (primary = most coarse time spent: `games_in_bucket × NOMINAL_DURATION[bucket]`, no recency weighting; see the note) and the rest collapsed. Inside each TC card render a **2×2 grid of four endgame-type tiles** — rook, minor_piece, pawn, queen — with **Mixed dropped** (it's the least-actionable catch-all material bucket and its WDL tends to track the overall endgame number; pawnless stays hidden). This is the TC-honest replacement for the SUPERSEDED TC-mix-weighted-band plan: because each card is a single TC, the Conversion and Recovery gauges removed on 2026-05-29 return showing **that TC's own per-(class × TC) benchmark band** (the d≈1.2–1.7 metrics finally judged against the right reference) with **no TC-mix weighting math and no per-(class×TC) eligible-count payload weighting**. **Score Gap (ΔES) is banded per-TC as well, for visual consistency** (decided 2026-05-30): statistically it's TC-flat (per-class ΔES TC d≈0.13) so the four per-TC bands will be near-identical, but Score Gap conceptually belongs to the type tile alongside the TC-varying Conv/Recov gauges, and giving it a per-(class × TC) band keeps one consistent card grammar rather than a single hoisted band breaking the per-TC cohesion — the redundancy is known and chosen, do not "fix" it back to one band. A TC card (or an individual tile) **self-suppresses** when that TC lacks enough games, mirroring Lichess Tutor's 30-games-per-speed model so sparse speeds simply don't render rather than showing noise. This applies the **mode-3 "collapsible TC cards"** disclosure pattern; the full-width-stacked layout is a hard constraint (collapsibles in a multi-column grid go ragged). The Endgame ELO Timeline (mode 2) and Endgame Metrics by TC (Phase 97) sections are out of scope. See [notes/endgame-tc-disclosure-pattern.md](notes/endgame-tc-disclosure-pattern.md) for the full pattern and the Lichess Tutor research; [notes/endgame-typecard-tcmix-gauges.md](notes/endgame-typecard-tcmix-gauges.md) is SUPERSEDED but retains the accurate benchmark facts.
**Depends on**: Phase 97 (reuses `EndgameGauge`, the `endgameZones.ts` codegen, and the per-(class × TC) rate aggregation path)
**Requirements**: standalone — no requirement IDs (endgame stats UX refinement)
**Open planning inputs** (resolve during plan-phase, not blockers):

  - **Tile contents.** Decide what each of the four type tiles carries (WDL bar + Conv gauge + Recov gauge + Score/Score-Gap bullet) and whether the 2×2 cell has room for all of it on mobile, or whether per-tile content thins on small screens.
  - **Score Gap band generation.** Decided to band Score Gap per-TC for visual consistency (see goal). Confirm `endgame_zones.py` / `endgameZones.ts` can emit per-(class × TC) ΔES bands (today it has a single per-class `achievable_score_gap` band), and accept that the four bands will be near-identical given d≈0.13.
  - **Accordion state.** The default-expanded TC is decided: the **primary TC** = argmax of coarse time spent `games_in_bucket × NOMINAL_DURATION[bucket]` (fixed per-bucket duration constants, no per-game lookup, no recency weighting), taken only over TCs that pass the games floor, computed over the currently-filtered game set (see [notes/endgame-tc-disclosure-pattern.md](notes/endgame-tc-disclosure-pattern.md)). Remaining open: the exact `NOMINAL_DURATION` constants, where the shared util lives (so the timeline can later align), and whether manual expand/collapse state persists across filter changes.
  - **Backend grouping.** Confirm the `/stats` breakdown can return per-(class × TC) rates + counts grouped for per-TC rendering (Phase 97 already established the per-(class × TC) path).

**Success Criteria** (what must be TRUE):

  1. The Endgame Type Breakdown renders as **full-width, vertically stacked collapsible cards, one per time control** (only TCs with sufficient games appear), replacing the previous 3-col grid of per-type cards.
  2. The user's **primary TC card is expanded by default** — primary = argmax of coarse time spent (`games_in_bucket × NOMINAL_DURATION[bucket]`, no per-game lookup, no recency weighting), over TCs passing the games floor; the others are collapsed behind a chevron and expand on click. Expand/collapse is keyboard-accessible with `data-testid`s on each header.
  3. Each expanded TC card shows a **2×2 grid of four type tiles** (rook, minor_piece, pawn, queen). **Mixed is no longer shown** as a type tile; pawnless stays hidden.
  4. Each tile's **Conversion and Recovery gauges are back**, banded against **that card's own per-(class × TC) benchmark IQR** — no TC-mix-weighted blend, no pooled-across-TC band.
  5. **Score Gap is banded per-(class × TC)** like the other tile metrics (forced per-TC for visual consistency despite being TC-flat); each TC card shows its own Score Gap band even though the four will be near-identical.
  6. Per-(class × TC) conversion/recovery bands are generated into `frontend/src/generated/endgameZones.ts` via `app/services/endgame_zones.py` + `scripts/gen_endgame_zones_ts.py`, CI drift gate green. (No eligible-count weighting payload is added — that was the superseded approach.)
  7. A TC card and/or its tiles **self-suppress** below the existing games floor (`MIN_GAMES_FOR_RELIABLE_STATS` / the per-TC floor Phase 97 established); a user concentrated in one TC sees only that TC's card.
  8. The backend `/stats` endgame breakdown exposes per-(class × TC) rates and games counts grouped for per-TC rendering; the LLM insights path (`_findings_conversion_recovery_by_type` / `assign_per_class_zone`) is unaffected (response shape preserved or additively extended).
  9. Desktop and mobile both render the collapsible per-TC cards and 2×2 tile grid responsively (full-width on both; no ragged multi-column collapsibles).
  10. Backend (`pytest`, `ty`, `ruff`) and frontend (`lint`, `test`, `knip`) gates pass; `EndgameTypeBreakdownSection` / `EndgameTypeCard` tests are updated for the new layout (the locked `grid-cols-*` assertions and Mixed-tile assertions must change); a `CHANGELOG.md` `[Unreleased]` entry records the restructure and the Conv/Recov re-introduction.

**Plans**: 2 plans
**Wave 1**

- [x] 98-01-PLAN.md — Backend: per-(class × TC) zone registry + codegen + categories_by_tc aggregation (LLM path unaffected)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 98-02-PLAN.md — Frontend: primaryTc util + restored 5-element tile + collapsible per-TC accordion section + test updates + CHANGELOG

### Phase 99: Percentile Badges for Conversion, Parity, and Recovery

**Goal**: Add peer-relative percentile chips (the v1.19 `PercentileChip` primitive) to the per-TC Conversion, Parity, and Recovery rate cards delivered in Phase 97. This is the deferred badge work called out in Phase 97 ("Per-TC conversion/recovery percentile badges are deferred to a follow-up phase") — it requires new per-(metric, TC) cohort CDF materialization in `user_benchmark_percentiles`, since today only the ΔES score-gap family has stored percentiles there. Mirrors the Phase 94.3 Time Pressure per-TC chip pattern: the 3 rate families × 4 TCs are computed via the pooled-per-user methodology in `canonical_slice_sql.py` parameterised by TC, cohort-matched on the per-(user, TC) rating anchor, and surfaced with the 4-bullet disclosure tooltip per `feedback_percentile_chip_tooltip_disclosure`. Conversion and Recovery are conditional rates with thin per-TC denominators, so the inclusion floor and sparse-cell suppression carry over from Phase 97's per-TC cards.
**Depends on**: Phase 97 (consumes the per-TC Conversion/Parity/Recovery rate aggregation + TC card layout); Phase 94.3 (per-TC pooled CDF + chip pattern)
**Requirements**: standalone — no requirement IDs (endgame stats UX refinement)
**Success Criteria** (what must be TRUE):

  1. Each per-TC card (bullet/blitz/rapid/classical) from Phase 97 renders a percentile chip on its Conversion, Parity, and Recovery rates, gated on the per-(metric, TC) inclusion floor — below floor, no chip renders.
  2. 12 new metrics (`{conversion_rate, parity_rate, recovery_rate}_{bullet, blitz, rapid, classical}`) are added to the `user_benchmark_percentiles` ENUM and computed via the shared `canonical_slice_sql.py` pooled-per-user builder parameterised by TC — drift between CDF construction and per-user lookup remains structurally impossible.
  3. The cohort CDFs are generated into `app/services/global_percentile_cdf.py` (or the cohort-CDF sibling) under the existing per-(metric, ELO anchor, TC) sliding-window protocol, with the regen report archived.
  4. Chips are cohort-matched on the per-(user, TC) rating anchor and carry the 4-bullet disclosure tooltip per `feedback_percentile_chip_tooltip_disclosure`, with the first two bullets TC-scoped.
  5. The backfill script populates the 12 new metrics on dev (and prod via tunnel after sign-off); desktop + mobile parity; backend + frontend gates pass.

**Plans**: 5 plans
Plans:
**Wave 1**

- [x] 99-01-PLAN.md — Wave 0 test scaffolds (rate-builder floor/parity, ENUM membership, schema field, frontend chip)
- [x] 99-02-PLAN.md — Backend contract layer: 3 rate builders + floor constant + CdfMetricId + SAEnum +12 + Alembic migration

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 99-03-PLAN.md — Stage B + regen dispatch arms; PerTcBucketStats rate field trio; endgame_service threading
- [x] 99-04-PLAN.md — Frontend: TS rate fields + title-line rate chip in shared MetricBlock (desktop + mobile)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 99-05-PLAN.md — Cohort CDF regen (benchmark) + archive report + dev backfill; prod backfill gated on sign-off (D-11)

### Phase 99.1: Move Cohort CDF Out of Source into a DB Table

**Goal**: Eliminate the source bloat in `app/services/global_percentile_cdf.py` (3.1 MB / 130,369 lines, of which ~130,119 are float literals for the generated `COHORT_PERCENTILE_CDF` dict and only ~250 are logic) by relocating the CDF breakpoint data into a `benchmark_cohort_cdf` DB table, and unlock SQL analysis of the breakpoints as a side benefit. The lookup is **not** on a request hot path — `interpolate_cohort_percentile` is called only by the `compute_stage_a` / `compute_stage_b` background tasks (~32 indexed lookups per import), so it becomes `async` and queries the table directly with no in-memory cache. The generator (`scripts/gen_global_percentile_cdf.py`) stops rewriting the `.py` between the BEGIN/END sentinels and emits a compact seed file to `app/data/` instead; a manual idempotent seed script (`scripts/seed_cohort_cdf.py`, `INSERT ... ON CONFLICT DO UPDATE`, modeled on `scripts/seed_openings.py`) loads it and is wired into `bin/run_local.sh` (count-gated, mirroring the openings block). The module shrinks to ~250 lines, retaining `CdfMetricId` (imported widely), `CdfTable`, the breakpoint constants, and the interpolation math. See [notes/phase-99-1-cdf-db-refactor.md](notes/phase-99-1-cdf-db-refactor.md) for the full decision log.
**Depends on**: Phase 99 (consumes the regenerated cohort CDF + the `interpolate_cohort_percentile` lookup and its two background callers)
**Requirements**: standalone — no requirement IDs (internal refactor / tech-debt)
**Success Criteria** (what must be TRUE):

  1. `app/services/global_percentile_cdf.py` no longer contains the generated registry; the file is ~250 lines and the BEGIN/END sentinels are gone. `CdfMetricId`, `CdfTable`, breakpoint constants, and `_interpolate_with_table` remain.
  2. A `benchmark_cohort_cdf` table (new SQLAlchemy model + Alembic migration, schema only) holds all breakpoint cells, with `snapshot_month` as an audit column (not an idempotency gate). Table layout (long vs wide) decided during planning.
  3. `interpolate_cohort_percentile` is `async`, takes a session, queries the table for the `(metric, anchor, tc)` cell, and runs the existing interpolation math in Python; both background callers (`compute_stage_a` / `compute_stage_b`) are updated and pass.
  4. `gen_global_percentile_cdf.py` emits a compact seed file to `app/data/` (no longer rewrites the module source); the regen drift test compares regenerated seed-file content rather than source bytes.
  5. `scripts/seed_cohort_cdf.py` performs an idempotent `ON CONFLICT DO UPDATE` load from the seed file (re-runnable; picks up new cells and changed values); `bin/run_local.sh` seeds on first-time local setup; dev DB is seeded and chips render unchanged end-to-end.
  6. Backend + frontend gates pass (`ruff`, `ty`, `pytest`, frontend lint/tests); chip output is byte-for-byte equivalent to pre-refactor for a representative user (pure relocation, no behavior change).

**Plans**: 4 plans
**Wave 1**

  - [x] 99.1-01-PLAN.md — benchmark_cohort_cdf model + schema-only Alembic migration (D-01)
  - [x] 99.1-02-PLAN.md — generator emits app/data/cohort_cdf.tsv + committed seed artifact + TSV drift test (D-02, SC#4)

**Wave 2** *(blocked on Wave 1 completion)*

  - [x] 99.1-03-PLAN.md — idempotent seed script + load_cohort_cells repository (D-03/D-04) + run_local.sh seed block (SC#5)

**Wave 3** *(blocked on Wave 2 completion)*

  - [x] 99.1-04-PLAN.md — shrink global_percentile_cdf.py (sync interpolator) + wire stage A/B prefetch + byte-for-byte parity (SC#1/#3/#6)

> Planning note: SC#3's literal "interpolate_cohort_percentile becomes async" is reconciled per CONTEXT D-04 — the module stays pure/sync and takes a prefetched CdfTable; the async DB access lives in the new `benchmark_cohort_cdf_repository.load_cohort_cells` (batched prefetch, D-03).

### Phase 100: LLM Endgame-Insights Statistical-Reasoning Rework

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
<summary>✅ v1.20 Import Pipeline Hardening Follow-Up and Readiness (Phases 95-96) — SHIPPED 2026-05-29</summary>

- [x] Phase 95: asyncpg COPY for `bulk_insert_positions` (2/2 plans, PRs #148/#149) — completed 2026-05-27
- [x] Phase 96: Import Readiness Gate (3/3 plans, PR #151) — completed 2026-05-28

See [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md) for full details.

</details>

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
| 95. asyncpg COPY for bulk_insert_positions | v1.20 | 2/2 | Complete | 2026-05-27 |
| 96. Import Readiness Gate | v1.20 | 3/3 | Complete | 2026-05-28 |
| 97. Endgame Metrics by Time Control | v1.21 | 4/4 | Complete | 2026-05-29 |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 5/5 plans complete

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
