---
id: SEED-006
status: dormant
planted: 2026-04-26
planted_during: v1.12 Benchmark DB & Population Baselines (executing, Phase 69 mid-ingest)
trigger_when: full benchmark DB ingest completes (operational task started after v1.12 closes)
scope: milestone
---

# SEED-006: Benchmark population baselines & rating-bucketed zone recalibration

## 2026-04-30 Amendments (post-ingest reality check)

The benchmark DB has been populated (~991 users, 4M games, 295M positions across 4 TC × 5 ELO cells) and a first-pass `/benchmarks` report was produced (`reports/benchmarks-2026-04-29.md`). Three corrections to the seed below before this milestone materializes:

1. **Schema reality vs SEED-002 proposal.** SEED-002 proposed a separate `game_position_evals` table; reality is that evals are inline on `game_positions` as `eval_cp` (smallint) and `eval_mate` (smallint). All Phase 70/71/72 SQL must target those columns, not a separate eval table.

2. **TC-pooling bias direction in the Phase 70 pre-discuss note is wrong.** The note warns that a TC-pooled offset estimate is bullet-dominated. Eval coverage in the populated DB is heavily classical-skewed:

   | TC | total games | with evals | % |
   |---|---|---|---|
   | bullet | 1,963,898 | 99,096 | 5.0% |
   | blitz | 1,467,180 | 212,709 | 14.5% |
   | rapid | 466,907 | 123,269 | 26.4% |
   | classical | 100,422 | 41,286 | 41.1% |

   So TC-pooling biases the offset estimate toward longer-TC behavior, not bullet. The supplementary TC-stratified offset table mandated in the original note is still the right safety net; only the bias-direction sentence needs correcting during Phase 70 discuss.

3. **Phase 73 scope additions.** The skill upgrade in Phase 73 must produce more than rating-bucketed zone constants. It must first emit a **Cohen's d collapse verdict per metric × dimension** that determines whether each metric needs cell-specific zones at all, or collapses on TC, ELO, or both. Only metrics that fail to collapse on a given axis get bucketed zones. Methodology is captured in `.planning/notes/benchmark-skill-v2-design.md` (verdict thresholds 0.2 / 0.5 hard-coded; per-metric output shape: 20-cell grid + TC marginal + ELO marginal + heatmap + verdict block; top-axis summary table).

   This expansion does not change Phase 73's deliverables; it constrains the calibration choice. If a metric's TC and ELO axes both collapse (`max |d| < 0.2`), the existing global gauge constant stands and no rating/TC-bucketed variant is shipped.

4. **Pre-SEED-006 calibration cleanup is split out.** The 2026-04-29 report surfaced four findings that don't depend on eval data, rating-bucketing, or skill v2: (a) Endgame Skill upper bound 0.55→0.57, (b) per-endgame-class conv/recov neutral zones, (c) clock-pressure per-TC thresholds, (d) time-pressure-vs-performance per-TC display. These are tracked in **SEED-009** and may ship before this milestone opens, OR fold into Phase 73 if the user prefers a single coordinated PR.

## Why This Matters

This seed captures the **applied analytics** half of what was originally planned as v1.12 — the work that consumes the populated benchmark DB to validate the material-vs-eval classifier at scale, surface rating-stratified offsets, validate the Parity proxy, and recalibrate the Conversion / Recovery / Endgame Skill gauge zones per rating bucket.

**Why this is a separate milestone now.** The original v1.12 roadmap bundled infrastructure (Phases A/69) and applied analytics (Phases B-E/70-73) into a single milestone. The actual data-population step — running the ingestion pipeline against a Lichess monthly dump — takes days of wall-clock time on Adrian's machine and is operationally separate from any code-shipping activity. Treating it as a milestone gate blocked unrelated work (notably v1.13 opening insights, which has no dependency on this data) for the duration of the ingest.

The split reframes the original v1.12 scope as:
- **v1.12 (shipped)** — Benchmark DB Infrastructure & Ingestion Pipeline. Pipeline correctness verified by smoke test. Population is operational, not a milestone gate.
- **This seed (v1.14 candidate)** — Applied analytics over the populated DB.

The intervening milestone (v1.13 Opening Insights, see SEED-005) runs while the full ingest completes in the background.

## When to Surface

**Trigger:** Full benchmark DB ingest completes.

This seed should be presented during `/gsd-new-milestone` when:
- The full ingest has produced a populated benchmark DB (verified by row counts on `games` / `game_positions` and per-cell sample counts via `mcp__flawchess-benchmark-db__query`).
- AND the user signals readiness to take on validation/calibration work.
- OR the milestone scope mentions "classifier validation", "zone recalibration", "population baselines", "rating-stratified offsets", "gauge thresholds at scale".

Do NOT surface while v1.13 is active unless the full ingest has completed AND v1.13 is winding down. The ordering preference is v1.12 → v1.13 → this milestone, but if v1.13 finishes before the ingest does, just hold this seed dormant until the ingest is ready.

## Prior Work (Do Not Re-Derive)

The original v1.12 roadmap content (`.planning/milestones/v1.12-ROADMAP.md` as it existed before the 2026-04-26 split) contained detailed phase decompositions for Phases 70-73 with goals, dependencies, and success criteria. That content is preserved below verbatim so the future milestone can lift it without re-deriving anything. Phase numbering is kept as 70-73 for continuity with the prior planning artifacts and SEED-002 references.

### Phase 70: Classifier Validation Replication at Scale (GATE)

**Goal:** Re-run the 2026-04-07 material-vs-eval validation against the benchmark DB with 10-100x more samples per (endgame_type) cell, document the offset estimates and confidence intervals, and emit a documented PASS/FAIL gate verdict that authorizes or pauses subsequent phases.

**Depends on:** Populated benchmark DB
**Requirements:** VALID-01, VALID-02

**Pre-discuss note — TC-pooling bias toward bullet (added 2026-04-26):** The 2026-04-07 report pooled across time controls; this phase mirrors that structure. Bullet players contribute roughly 30x more games per user than classical players over the 36-month window, so a TC-pooled per-(endgame_type) offset table is effectively a bullet-dominated estimate. This is consistent with the 2026-04-07 baseline (so the head-to-head comparison is fair), but it means the validated offset propagated into Phase 71/72 may mask TC-specific behavior (e.g., noisier `[%eval]` at endgame entry under bullet time pressure, different endgame-class mixes). Mitigation is cheap and belongs in this phase: add a supplementary TC-stratified offset table (4 TC buckets × 6 endgame types) alongside the pooled one. The **Gate Verdict stays on the pooled cells** — the TC-stratified table is informational, surfaced so Phase 71 can decide whether to also stratify by TC. Per-cell zone calibration in Phase 73 is unaffected because each (rating × TC) cell is independent.

**Success Criteria:**
1. A report exists at `reports/classifier-validation-benchmark-YYYY-MM-DD.md` whose section structure parallels `reports/endgame-conversion-recovery-analysis.md` (sections 1-4: threshold comparison, persistence comparison, eval validation head-to-head, decision), so side-by-side comparison is trivial.
2. The report contains a per-(endgame_type) offset table comparing the new benchmark-DB point estimates against the 2026-04-07 estimates AND against the 2026-04-07 95% CI bounds, for both Conversion and Recovery, on the t=100 + 4-ply configuration.
3. The report ends with an explicit `## Gate Verdict` section that states PASS or FAIL on each of Pawn / Rook / Minor cells using the locked rule: FAIL only if (a) the new point estimate falls outside the 2026-04-07 95% CI for that cell AND (b) |Δ| > 2pp absolute.
4. The Gate Verdict section concludes with a single overall verdict line: either "Phases 71-73 authorized to proceed" or "Phases 71-73 paused for offset re-investigation". The verdict is persisted in `.planning/STATE.md` and PR-reviewed before downstream phases start.
5. Sample size in the benchmark replication for Pawn / Rook / Minor / Mixed cells is at least 10x the 2026-04-07 cell sizes (Pawn: ~1k → ≥10k; Rook: ~3k → ≥30k; Minor: ~2.5k → ≥25k; Mixed: ~28k → ≥280k); Queen sample reaches at least 1k (vs 28-40 in the original report).

### Phase 71: Rating-Stratified Offset Analysis

**Goal:** Extend the classifier validation with the rating-bucket breakdown the 2026-04-07 report lacked: produce per-(rating_bucket × endgame_type) material-vs-eval offset tables for both Conversion and Recovery, and surface whether the t=100 + 4-ply proxy needs a rating-dependent correction.

**Depends on:** Phase 70 (gate-pass)
**Requirements:** VALID-03

**Success Criteria:**
1. A report extension (either appended to the Phase 70 report or written as `reports/classifier-validation-rating-stratified-YYYY-MM-DD.md`) contains a 5×6 offset table (5 rating buckets × 6 endgame types) for both Conversion and Recovery, populated from the benchmark DB.
2. Each cell reports point estimate AND 95% CI, with a flag where CI width ≥ 5pp (sample-quality marker for the eventual baseline use).
3. The report concludes with an explicit verdict on the hypothesis "the t=100 + 4-ply offset varies materially by rating": either (a) "no rating-dependent correction needed; offsets are within ±2pp across all rating buckets for at least Pawn / Rook / Minor", or (b) "rating-dependent correction recommended for ", with the affected cells named.
4. If verdict (b) fires, the report names the concrete remediation paths (rating-bucketed offset adjustment in zone calibration vs deferring to a later hybrid classifier) without committing to one in this phase.

### Phase 72: Parity Proxy Validation

**Goal:** Validate the Parity proxy ("even material at endgame entry" → Stockfish eval in [-50, +50]cp at endgame entry) at benchmark-DB scale, document any systematic offset analogous to the Conversion / Recovery offsets, and reassess the composite Endgame Skill formula if Parity has its own offset.

**Depends on:** Phase 70 (gate-pass) — independent of Phase 71 in principle, but the SEED-002 ordering keeps it after rating stratification.
**Requirements:** VALID-04

**Success Criteria:**
1. A report (extension of Phase 70 report or `reports/parity-validation-benchmark-YYYY-MM-DD.md`) documents the agreement rate between "material imbalance in [-100, +100]cp at endgame entry" and "Stockfish eval in [-50, +50]cp at endgame entry", per endgame type, with sample size and 95% CI per cell.
2. The report names any systematic Parity offset (proxy over- or under-reads vs eval) per endgame type, in the same format as the Conversion / Recovery offset tables in the 2026-04-07 report.
3. The report explicitly reassesses the composite Endgame Skill formula: either confirms the current `(Conv + Par + Rec) / 3` (or the actual current formula, verified during the phase) is sound under the measured offsets, OR proposes a re-weighting and documents the rationale.
4. If a re-weighting is proposed, the report names the affected zone constants and which subsequent Phase 73 step they depend on (so Phase 73 can carry the change through to `theme.ts`).

### Phase 73: `/benchmarks` Skill Upgrade & Zone Re-Calibration

**Goal:** Upgrade the `/benchmarks` skill to query the benchmark DB and produce per-(rating_bucket × TC × platform × endgame_type) population baselines for Conversion / Parity / Recovery / composite Endgame Skill / clock-at-entry / timeout rates, compute rating-specific zone thresholds using the median-user-at-warning/success-boundary rule, AND ship those rating-bucketed zone constants in `frontend/src/lib/theme.ts` (PR-reviewed, deployed). Extend the `/db-report` skill so DB-health reports cover the benchmark database alongside dev/prod.

**Depends on:** Phase 70 (gate-pass), Phase 71 (rating offsets), Phase 72 (parity verdict).
**Requirements:** BENCH-01, BENCH-02, BENCH-03, BENCH-04
**UI hint:** yes

**Pre-discuss note — per-analysis `min_games_per_user` filter (added 2026-04-26):** The Phase 69 selection threshold (`DEFAULT_EVAL_THRESHOLD = 10` eval-bearing games in the snapshot month) is a 1-month signal and does NOT guarantee 36-month activity, so the benchmark DB will contain a long tail of low-game users (some with <20 games over the full window). This is intentional — pre-filtering at selection or import would lock one threshold for all analyses and waste data that is still valid for pooled estimates. The `/benchmarks` skill must apply a **per-analysis** `min_games_per_user` filter at query time: stricter thresholds for per-user rate distributions (Conversion / Recovery / Endgame Skill — start at 50), looser for clock/timeout analytics (start at 20), and NO user-level filter for per-game pooled estimates (Phase 70/71 classifier validation already pools games across users). Mirror the 20k hard-skip rule (D-14) on the upper tail; lower tail is also a query-time concern, not an ingestion concern. Sweep the threshold (e.g. 20/50/100) once during calibration to confirm the median-user rates are stable before locking the zone constants.

**Success Criteria:**
1. Running the upgraded `/benchmarks` skill produces a report containing population baselines for Conversion / Parity / Recovery / composite Endgame Skill / clock at endgame entry / timeout rates, broken down per (rating_bucket × time_control × platform × endgame_type), with sample size and 95% CI per cell, AND a rating-bucketed zone-threshold table covering Conversion (warn/succ), Recovery (danger/warn, warn/succ), and Endgame Skill (warn/succ).
2. The rating-bucketed zone-threshold values from the skill report land in `frontend/src/lib/theme.ts` (or the equivalent constants location) and are reviewed in a merged PR — the milestone is INCOMPLETE until the constants ship in code, not just the report.
3. The shared zone registry (`app/services/endgame_zones.py`) and its Python→TypeScript codegen are updated consistently with the new rating-bucketed values, and the CI drift guard still passes (no narrative-vs-chart drift introduced by the recalibration).
4. Running `/db-report` returns a single output describing both prod and benchmark databases (table counts, row counts, last-updated timestamps), so DB-health checks are unified.
5. If Phase 72 proposed a composite-formula re-weighting, the new formula is reflected in the skill output, the zone registry, and `theme.ts`; otherwise the existing `(Conv + Par + Rec) / 3` (or current actual) formula stands unchanged.

## Requirements Carried Over

From the original v1.12 REQUIREMENTS.md, these 8 requirements move with this seed:

- **VALID-01** — replicated material-vs-eval classifier validation (Phase 70)
- **VALID-02** — quantitative checkpoint gate (Phase 70)
- **VALID-03** — rating-stratified offset analysis (Phase 71)
- **VALID-04** — Parity proxy validation (Phase 72)
- **BENCH-01** — `/benchmarks` skill queries benchmark DB (Phase 73)
- **BENCH-02** — rating-specific zone thresholds (Phase 73)
- **BENCH-03** — thresholds shipped in `theme.ts` (Phase 73)
- **BENCH-04** — `/db-report` extended for benchmark DB (Phase 73)

## Open Questions

These should be resolved during `/gsd-discuss-phase` for the relevant phase, NOT pre-committed in the milestone roadmap when this seed materializes:

1. **Cheat contamination at 2000+.** Phase 69 D-01 deliberately deferred cheat filtering. Phase 70 gate-pass on Pawn / Rook / Minor is the safety net. If Phases 71/73 surface unusual rating-dependence at 2000+ that's plausibly contamination-driven, decide whether to add a post-hoc filter or document and accept.
2. **Refresh cadence.** Quarterly vs event-driven on new dumps vs one-and-done. SEED-002 deferred this; revisit when zones first ship.
3. **chess.com baseline derivation.** The original v1.12 explicitly deferred chess.com to self-referential only. CHESS-COM-BL-01 (Lichess→chess.com rating-conversion mapping) decision belongs here.
4. **Engine-eval vs material proxy in production gauges.** If Phase 70 gate fails, the response could either restore engine-eval as the production classifier (where coverage allows) or accept a degraded confidence interval on the material proxy. Decide at gate-fail time.

## Out of Scope

- Continued ingestion of new dumps (operational, not milestone work).
- Changing the canonical schema (locked in v1.12; benchmark DB uses identical schema).
- v1.13 opening insights (separate seed, SEED-005, structurally independent).
