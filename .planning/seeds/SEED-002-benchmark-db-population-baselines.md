---
id: SEED-002
status: dormant
planted: 2026-04-19
planted_during: v1.10 Advanced Analytics (executing, post-Phase 57.1)
trigger_when: milestone v1.12 opens (after v1.11 Insights)
scope: milestone
---

# SEED-002: Benchmark database for population baselines and rating-stratified validation

## Why This Matters

FlawChess's endgame analytics are currently **self-referential**: a user's Conversion, Parity, and Recovery rates are compared against the rates their specific opponents achieved in the same games. This works structurally because matchmaking ensures opponents ≈ peers at the same rating, but it has three consequences that a population-stratified dataset would resolve:

1. **No absolute benchmarks.** "You're 6pp better than your opponents" doesn't tell the user whether 6pp is exceptional or typical for their rating cohort. Some users want the absolute framing; some coaching signals require it.
2. **Rating-specific zone thresholds are unavailable.** The current 50/70/... Conversion thresholds, 15/35 Recovery thresholds, and 40/60 Endgame Skill thresholds were calibrated against FlawChess users (predominantly 1400-1800 on chess.com). They don't adapt to a 2200 classical player or a 900 bullet player — both of whom might land in "typical" when the thresholds were set for the middle of the distribution.
3. **No peer-trajectory comparisons.** "You're improving 2x faster than typical 1500 players" requires a cohort of other users' trajectories over time. Self-referential can't produce this.

A secondary but important motivation: the existing Stockfish-eval validation of the material proxy (`reports/endgame-conversion-recovery-analysis.md`, 2026-04-07) was based on small samples (n=28-311 per endgame type × conversion/recovery cell). The offsets it reported are directionally right but imprecise. A benchmark DB with 10-100x more eval-annotated games would tighten the confidence intervals and extend the validation to rating-bucketed cells (not currently covered) and Parity (added after the report).

## When to Surface

**Trigger:** Milestone v1.12 opens

This seed should be presented during `/gsd-new-milestone` when:
- The user starts planning v1.12
- OR the milestone scope mentions "population baselines", "benchmark data", "peer comparison", "rating-stratified", "lichess bulk ingestion", "engine eval validation"
- OR the roadmap references replacing self-referential baselines with population data

Do NOT surface during v1.11. v1.11 is the Insights milestone (SEED-001) which consumes the self-referential baselines as they are. Insights and benchmarks should not be built in parallel; insights first validates what findings the current data can support, then benchmarks upgrades the data without changing the insights API.

## Prior Work (Do Not Re-Derive)

**`reports/endgame-conversion-recovery-analysis.md` (2026-04-07)** — the foundational validation report. Key results that SEED-002 work should treat as established and extend rather than re-derive:

- **Current configuration is t=100 centipawn threshold + 4-ply persistence.** This was selected over t=300 (higher accuracy but ~6x fewer samples) and over pure Stockfish eval (higher accuracy but 0% chess.com coverage, 14.7% Lichess coverage).
- **Material proxy passes validation against Stockfish eval** with a *systematic* offset:
  - Conversion: proxy under-reads eval by 2-8pp (material includes hopeless-but-up-material positions).
  - Recovery: proxy over-reads eval by 4-6pp (material counts compensated positions as recovery opportunities).
  - Offset direction is consistent across endgame types → relative rankings preserved. Proxy is valid for trend, comparison, and identification purposes.
- **Sample-size gaps in the existing report** that SEED-002 should fill:
  - Queen endgames: n=28-40 per cell. Offset estimates (+16.7pp conversion, -14.3pp recovery) are noise-dominated.
  - No rating-bucket breakdown. Offset averaged across all ratings.
  - Parity not validated (added after the report).
  - All FlawChess prod data, not a clean random sample (biased toward FlawChess's user base).
- **Gauge zones** calibrated post-t=100 shift: Conversion 0/50/70/100, Recovery 0/15/35/100, Endgame Skill 0/40/60/100 (Endgame Skill at the time was 0.7·Conv + 0.3·Rec; Parity added later changes the composite formula).
- **Persistence at 4 plies is sufficient.** 5 or 6 plies gains <1pp at the cost of 2-3% samples. Do not re-explore the persistence axis.

**`docs/endgame-analysis-v2.md`** — overall endgame analytics spec, §5 covers the min-sample-size convention and material threshold rationale.

## Scope Estimate

**Milestone** — expected to span 5-7 phases. Decomposition:

### Phase A: Benchmark ingestion pipeline

- New PostgreSQL instance (`flawchess-benchmark`) with identical schema to prod + one additional table `game_position_evals` (game_position_id, eval_cp, mate_in_n, eval_depth, eval_source_version) keyed to `game_positions`.
- New MCP server `flawchess-benchmark-db` parallel to existing two, so `/benchmarks` and classifier-validation skills can query it.
- Bulk ingestion mode that reads Lichess monthly PGN dumps from `database.lichess.org` (not per-username API fetches — lichess monthly dumps cover the whole population naturally).
- Filter for `%eval` presence during ingestion; skip games without evals.
- Stratified subsampling: target ~25K-50K games per (rating_bucket × TC) cell on first pass. Rating buckets: 800-1200, 1200-1600, 1600-2000, 2000-2400, 2400+ (5). TC: bullet, blitz, rapid, classical (4). Grid: 20 cells.
- Storage target for v1.12 MVP: 20-50 GB. Scale to 200 GB if tighter CIs are needed post-validation.
- Parse `%eval` tags via python-chess; centipawn vs pawn-units convention verified against known sample before scaling.

### Phase B: Replication of 2026-04-07 classifier validation at large scale

- Re-run the material-vs-eval agreement analysis from `reports/endgame-conversion-recovery-analysis.md` against the benchmark DB.
- Same methodology: t=100 + 4-ply persistence vs Stockfish eval u=100 on the same game subset, per endgame type.
- Report format: write to `reports/classifier-validation-benchmark-YYYY-MM-DD.md`. Structure should parallel the 2026-04-07 report so side-by-side comparison is trivial.
- **Replication check**: do the systematic-offset estimates (conversion +2-8pp, recovery -4-6pp) hold when sample sizes are 10-100x larger? If yes, the existing conclusion is confirmed with much higher confidence. If no, investigate why small-sample estimates drifted.

### Phase C: Rating-stratified validation (new analysis)

- Extend the classifier-validation analysis with rating-bucket breakdown that the 2026-04-07 report lacked.
- Does the material-vs-eval offset vary by rating? Hypothesis: low-rated games have more material-captured positions (offset smaller); high-rated games have more positional compensation (offset larger).
- Output: per-(rating × endgame_type) offset table. Informs whether the `t=100 + 4-ply` proxy needs rating-dependent correction.

### Phase D: Parity validation

- Parity (score from even material endgames) was added to the composite skill after the 2026-04-07 report. Validate it against Stockfish eval at the benchmark DB scale.
- Does the proxy of "even material at endgame entry" correspond to "eval is in [-0.5, +0.5] at endgame entry"? What's the agreement rate, and is there a systematic offset analogous to Conversion/Recovery?
- If Parity has a systematic offset of its own, document it and reassess the composite skill formula (current: `(Conv + Par + Rec) / 3` or similar, verify).

### Phase E: Population baseline tables

- Pre-compute per-(rating_bucket × TC × platform × endgame_type) baseline rates: Conversion, Parity, Recovery, composite Endgame Skill, average clock at endgame entry, timeout rates, and any other metrics that currently use self-referential comparison.
- Store as a lookup table (`endgame_population_baselines`) in the prod DB, refreshed quarterly from the benchmark DB.
- Baselines are shipped as static data, not computed live — prod doesn't query the benchmark DB.

### Phase F: Rating-specific zone thresholds

- Current zone thresholds (Conversion 50/70, Recovery 15/35, Endgame Skill 40/60) are global. With population baselines, they become rating-specific.
- Calibration target: median user at their rating lands at the warning/success boundary (same rule the 2026-04-07 report used for recalibrating the global thresholds). Apply per rating bucket.
- Update frontend gauge components to look up zone thresholds by the user's current rating for the active filter combo, not from hard-coded constants.

### Phase G: `/benchmarks` skill upgrade + optional population overlay UI

- `/benchmarks` queries the benchmark DB directly when admin/dev. Output reflects real population data instead of FlawChess-user-biased data.
- Frontend (optional for v1.12, could defer): a secondary "peer comparison" overlay on the Endgame Metrics table. "Your Conversion is 72%; your opponents' 64% (self-referential); peers at your rating 66% (population)." Opt-in or passive display, not replacing the self-referential primary.
- Percentile badges (e.g., "top 20% Parity at your rating") deferred to v1.13+ — motivational flavor, not core to the milestone.

### Optional (defer unless validation surfaces a need)

- **Hybrid classifier experiment.** Test whether material + simple positional heuristics (king safety, pawn structure, piece activity) closes more of the eval gap than pure material. Only pursue if Phase B/C validation surfaces gaps that matter at the UI level. The 2026-04-07 report's conclusion was "good enough, accept the offset" — treat this as the null hypothesis.
- **chess.com engine eval via local Stockfish.** chess.com PGNs don't carry evals. Running Stockfish locally on chess.com games is weeks of compute per million games. Defer unless there's a specific cross-platform question only this can answer.

## Design Decisions (Already Brainstormed)

The full design discussion happened in the conversation on 2026-04-19 preceding this seed. Preserve these decisions through the `/gsd-discuss-phase` for each v1.12 phase.

### Architecture

- **Lichess-only ingestion for v1.12.** Chess.com has 0% eval coverage; adding it requires local Stockfish analysis which is out of scope for the milestone. The "can't directly compare chess.com population baselines" limitation is a documented v1.12 gap, not a blocker.
- **Monthly PGN dumps, not per-username fetches.** `database.lichess.org` publishes all rated games monthly. Sampling from dumps is naturally population-distributed and avoids sampling selection effects from curated username lists.
- **Benchmark DB is separate infra, not co-located with prod.** Different data lifecycle (refreshed quarterly, no user-generated rows), different query patterns (aggregation-heavy, not per-user), and different privacy considerations (lichess data is CC0; FlawChess user data is not).
- **Baselines shipped as static tables to prod, not computed live.** Prod reads `endgame_population_baselines` as a simple lookup. No live connection from prod to benchmark DB.
- **Self-referential stays primary; population is secondary overlay.** This is not a replacement — it's augmentation. Users still see "your rate vs your opponents' rate" as the headline; population context is an optional layer. See the 2026-04-19 design discussion for the full rationale.

### Hybrid vs replacement

The discussion explicitly rejected replacing self-referential with population baselines. Reasons:

- Self-referential is rating-scale invariant (opponents rise with the user as they improve). Population-anchored comparisons shift as users change cohorts, which can misread as "you got worse."
- Self-referential automatically cohort-drifts with matchmaking pool changes. Population baselines require explicit periodic recomputation.
- Self-referential has no cohort bias. FlawChess user-base baselines would inherit whatever sampling bias the FlawChess population has; Lichess benchmark baselines inherit a different bias but a known one.
- Self-referential has zero privacy surface; population aggregation has some.

Population is layered on for:
- Absolute framing ("your Conversion ranks at peer-62nd-percentile")
- Rating-specific zone thresholds (currently global)
- Peer-trajectory comparisons (not in v1.12 scope but enabled by this infra)
- Validated Parity/Conversion/Recovery offsets at the rating-bucket level

### Data volume and sampling

- **First pass: 20-50 GB, ~500K-1M games with evals.** Enough for 20-cell stratification with 25K-50K games per cell. Validates the pipeline end-to-end before committing to larger storage.
- **Expansion to 200 GB deferred unless needed.** If Phase C (rating stratification) surfaces tight-CI cells that need more data, pull additional months of Lichess dumps. Most cells will likely be adequately populated at 50 GB.
- **Stratify on ingestion, not post-hoc.** Random sampling from raw dumps would over-weight the dense middle (1400-1800 blitz) and under-weight the tails. Subsample to per-cell targets during ingest.
- **Eval depth consistency.** Lichess runs analysis at depth ~18-20 (verify during implementation). Store `eval_depth` and `eval_source_version` alongside the eval value so future analyses can filter or re-derive.

### Schema additions

```python
# New table, benchmark DB only (not in prod)
class GamePositionEval(Base):
    __tablename__ = "game_position_evals"
    game_position_id: Mapped[int] = mapped_column(
        ForeignKey("game_positions.id", ondelete="CASCADE"), primary_key=True
    )
    eval_cp: Mapped[int | None]         # centipawns, signed from white's POV
    mate_in_n: Mapped[int | None]       # None unless forced mate detected
    eval_depth: Mapped[int | None]
    eval_source_version: Mapped[str]    # e.g., "lichess-sf-15-depth18"

# New table, prod DB (populated from benchmark DB quarterly)
class EndgamePopulationBaseline(Base):
    __tablename__ = "endgame_population_baselines"
    rating_bucket: Mapped[str] = mapped_column(primary_key=True)  # "1200-1599"
    time_control: Mapped[str] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(primary_key=True)       # "lichess" only for v1.12
    endgame_type: Mapped[str] = mapped_column(primary_key=True)
    conversion_rate: Mapped[float]
    parity_rate: Mapped[float]
    recovery_rate: Mapped[float]
    endgame_skill: Mapped[float]
    median_clock_at_entry_pct: Mapped[float]
    timeout_rate: Mapped[float]
    games_in_sample: Mapped[int]
    baseline_version: Mapped[str]       # snapshot date, for cache invalidation
```

### Open Questions for v1.12 Discuss Phase

- **Rating bucket granularity.** 400-wide buckets (800-1200, 1200-1600, ...) are coarse; 200-wide would be finer but thin at the tails. 500-wide the benchmarks skill already uses. What's the right width for population baselines?
- **Quarterly refresh cadence.** Rating inflation, meta drift, engine prep trickling down — baselines need recomputation. Is quarterly right, or should it be event-driven (e.g., when new Lichess dumps land)?
- **Freshness vs stability trade-off.** If baselines refresh, user-facing gauge zones shift. Communicate the version somehow (tooltip: "baseline version 2026-Q2")?
- **Storage lifecycle.** Keep raw PGN dumps after ingestion, or discard and retain only the parsed `games` + `game_positions` + `game_position_evals` rows? Saves significant disk but loses reproducibility.
- **Population-overlay UX placement.** Added to the Endgame Metrics table, or a new "Peer comparison" section? SEED-001 insights architecture has room for this as a `role=corroboration` cross-section finding with the population baseline as `ref_value`.
- **Should classifier-validation replication (Phase B) be a gate before Phase C-G proceed?** If the benchmark-scale validation surfaces a material-vs-eval offset that differs significantly from the 2026-04-07 small-sample estimates, downstream work assumes a shifted foundation. Probably yes — Phase B should be a checkpoint.
- **chess.com baselines — eventual, and how?** Options: (a) run local Stockfish on chess.com games (weeks of compute), (b) assume chess.com and lichess distributions are close enough to reuse lichess baselines for both, (c) accept chess.com has no population baseline and only self-referential analysis. (b) is probably wrong but cheapest; worth investigating in v1.13.
- **Hybrid classifier: experiment or skip?** The 2026-04-07 report concluded material is good enough. If Phase C validation surfaces consistent rating-dependent errors, a hybrid classifier might help; otherwise skip. Decide mid-milestone.

### Not in Scope

- **Per-user peer trajectory comparisons.** "You improved faster than typical 1500 players." Needs longitudinal cohort data, not just baselines. Defer to v1.13+.
- **Percentile badges on the Endgame tab.** Motivational flavor, out of scope for v1.12 — population baseline infrastructure is the primary deliverable. Easy follow-up in v1.13.
- **chess.com engine analysis via local Stockfish.** Weeks of compute per million games. Out of scope unless a specific v1.12 question requires it.
- **Replacing self-referential analysis.** Explicitly kept — population is an overlay, not a replacement.
- **Per-game move-accuracy metrics.** "You played 92% Stockfish-accurate moves." Different feature, different data pipeline, defer.
- **Real-time baseline updates.** Baselines are quarterly snapshots. Live per-game baseline queries against the benchmark DB are out of scope.

## Breadcrumbs

### Prior work to preserve

- **`reports/endgame-conversion-recovery-analysis.md` (2026-04-07)** — foundational material-vs-eval validation. **Read before starting any v1.12 phase.** Establishes the current configuration (t=100 + 4-ply persistence), documents the systematic offset, and calibrates the current gauge zones. SEED-002 work extends rather than re-derives.
- **`docs/endgame-analysis-v2.md`** — endgame analytics spec, including §5 min-sample-size convention (10 games).
- **`.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md`** — Endgame Skill composite decisions; note that Parity was added here after the 2026-04-07 report, so the current composite formula differs from the report's `0.7·Conv + 0.3·Rec`.

### Services and modules that will change

- `app/services/endgame_service.py` — current self-referential computations; will add population-overlay queries via the new `endgame_population_baselines` lookup.
- `app/services/stats_service.py` — rating cohort determination for lookup key.
- `app/repositories/query_utils.py` — `apply_game_filters()` pattern extends to benchmark DB queries.
- `app/data/`, `scripts/` — new ingestion scripts for Lichess monthly dumps; new tables in benchmark DB migrations.
- `frontend/src/components/charts/EndgameScoreGapSection.tsx`, `EndgamePerformanceSection.tsx` — add optional population-overlay rendering; rating-aware zone threshold lookups.
- `frontend/src/lib/theme.ts` — if zone threshold constants are currently hard-coded here (verify), move them to a runtime lookup.
- Skills: `/benchmarks` (significant upgrade to use benchmark DB), `/db-report` (add benchmark DB coverage).

### Infra additions

- New `docker-compose.benchmark.yml` for the benchmark DB (PostgreSQL 18, similar config to dev).
- New MCP server config for `flawchess-benchmark-db` read-only user (parallel to existing two MCP DB servers).
- Lichess dump download + staging directory (benchmark-only, local-only).
- Updates to `CLAUDE.md` §Database Access (MCP) listing the third DB server.

### Related planning artifacts

- `.planning/seeds/SEED-001-endgame-tab-insights-section.md` — the Insights milestone (v1.11). SEED-002 should not start before SEED-001 lands, so insights consume the current self-referential data first, then population baselines enhance the same underlying findings in v1.12.
- `.planning/phases/52-endgame-tab-performance/` through `57.1-endgame-elo-timeline-polish/` — the endgame analytics work that defined Conversion, Parity, Recovery, composite skill, and the ELO projection. SEED-002 validates and extends this foundation, does not rewrite it.

### Project conventions the Benchmark feature must follow

- `CLAUDE.md` §Critical Constraints — async SQLAlchemy, httpx (not requests), Standard-variant-only filtering.
- `CLAUDE.md` §Database Design Rules — FK constraints mandatory, unique constraints for natural keys, appropriate column types.
- `CLAUDE.md` §Error Handling & Sentry — benchmark ingestion batch failures should capture once at the top level (retry loops skip per-attempt capture).
- `CLAUDE.md` §Coding Guidelines — type safety, ty compliance, Literal types for enum-like strings, explicit return annotations.

## Notes

- **Do not start before v1.11 Insights (SEED-001) lands.** Insights should ship against the current self-referential data first. Layering population baselines onto an unshipped insights pipeline creates too many moving parts — two milestones sequentially is safer than one entangled milestone.
- **Reference chat context:** full design discussion spans two threads on 2026-04-19 — (1) critique of the self-referential approach and the Diff%-is-arithmetically-identical-to-Rec-Diff% finding, which reframed the statistical basis of the existing endgame analysis; (2) the benchmark DB proposal covering Lichess-only ingestion, monthly-dump-based sampling, schema additions, milestone decomposition, and the clarification that the 2026-04-07 report already performed the first-pass classifier validation (so v1.12 work extends rather than initiates this validation).
- **Ground-truth prior**: the 2026-04-07 validation report's findings (systematic offset, relative-ranking preservation, pawn best, queen worst due to small samples) are the null hypothesis that Phase B replicates. Budget for the possibility that large-sample replication confirms the existing conclusions with minimal new information — this would be a successful outcome of Phase B, not a failure mode, and would let Phases C-G proceed without methodology changes.
- **Phase B is a checkpoint.** If large-sample validation surfaces materially different offsets from the small-sample 2026-04-07 report, pause Phases C-G and investigate. If confirmed, proceed without further validation debate.
- **Diff%-redundancy cleanup is a separate, earlier fix.** The 2026-04-19 discussion surfaced that `Conversion Diff%` and `Recovery Diff%` in the Endgame Metrics table are algebraically identical (both equal `Player Conv% + Player Rec% - 1`). This is a presentation-level bug that can ship independently of SEED-002, possibly as a v1.10 cleanup or a v1.11 tweak. It does not require the benchmark DB. Flag this in v1.11 backlog rather than bundling with v1.12.
- **The `/benchmarks` skill is currently FlawChess-user-based.** After Phase E, it should query the benchmark DB as the authoritative population source, relegating FlawChess-user baselines to a comparison axis (useful for understanding how biased the FlawChess user base is, but not the primary reference).
- **Revisit SEED-001 after Phase B completes.** If Phase B's rating-bucketed classifier validation surfaces differences that matter at the insights-narrative level, the insights pipeline's `Zone` thresholds and `PlayerArchetype` signature criteria may need rating-dependent variants. Add this as an explicit v1.12 cross-reference in SEED-001.
