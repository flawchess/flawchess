# Requirements: FlawChess v1.12 Benchmark DB & Population Baselines

**Defined:** 2026-04-25
**Source:** `.planning/seeds/SEED-002-benchmark-db-population-baselines.md`
**Goal:** Replace self-referential endgame baselines with a Lichess-derived population dataset stratified by rating × time control, validate the material-vs-eval classifier at 10–100x larger scale, and recalibrate gauge zones per rating bucket.

## v1.12 Requirements

### Benchmark DB Infrastructure (INFRA)

- [ ] **INFRA-01**: Separate `flawchess-benchmark` PostgreSQL 18 instance, deployed via `docker-compose.benchmark.yml`, isolated from dev/prod
- [ ] **INFRA-02**: Benchmark DB uses the **same canonical schema and Alembic migrations** as dev/prod/test — no schema fork, no benchmark-only tables. Lichess `[%eval` annotations populate the existing `game_positions.eval_cp` and `game_positions.eval_mate` columns
- [ ] **INFRA-03**: Read-only MCP server `flawchess-benchmark-db` configured and documented in `CLAUDE.md` §Database Access alongside the existing two MCP DB servers

### Ingestion Pipeline (INGEST)

- [ ] **INGEST-01**: Bulk ingestion script reads Lichess monthly PGN dumps from `database.lichess.org`, with eval-presence pre-filter via streaming text scan (zgrep or equivalent) BEFORE python-chess game-tree parsing — so the ~85% of dump games without `[%eval` headers never reach the structural parser. Eval values populate the existing `game_positions.eval_cp` / `game_positions.eval_mate` columns (no schema additions)
- [ ] **INGEST-02**: Stratified subsampling on (rating_bucket × time_control) only — 5 rating buckets (800–1200, 1200–1600, 1600–2000, 2000–2400, 2400+) × 4 TCs (bullet/blitz/rapid/classical), uniformly at random within each cell, preserving natural endgame-type incidence
- [ ] **INGEST-03**: Player-side bucketing — separate `WhiteElo` and `BlackElo` headers determine each side's rating bucket independently; aggregations over `game_position_evals` never roll up by a single game-level rating field
- [ ] **INGEST-04**: Resumable ingest — checkpoint table keyed by `(dump_filename, byte_offset_or_game_index)`, idempotent inserts via existing `(platform, platform_game_id)` unique constraint, SIGINT-safe batch flush, per-batch skip / insert / error logging
- [ ] **INGEST-05**: Storage target 50–100 GB for v1.12 MVP; per-cell game count clears the rarest endgame type's (queen, ~2%) min-sample threshold (10 games per `docs/endgame-analysis-v2.md` §5) by a comfortable margin
- [ ] **INGEST-06**: Centipawn convention (signed from white's POV, units = centipawns vs pawn-units) verified against a known sample before scaling; verification documented in the ingestion script or a one-off validation note

### Classifier & Parity Validation (VALID)

- [ ] **VALID-01**: Replicated material-vs-eval classifier validation against the benchmark DB matching the 2026-04-07 methodology (t=100 centipawn threshold + 4-ply persistence vs Stockfish eval u=100); report written to `reports/classifier-validation-benchmark-YYYY-MM-DD.md` with structure parallel to the original report so side-by-side comparison is trivial
- [ ] **VALID-02**: Quantitative checkpoint gate — per-(endgame_type) offset is materially different from the 2026-04-07 result when (a) the point estimate falls outside the prior 95% CI AND (b) |Δ| > 2pp absolute. Both must hold on Pawn / Rook / Minor cells to trigger pause-and-investigate. Gate-pass authorizes Phases C–E to proceed
- [ ] **VALID-03**: Rating-stratified offset analysis — per-(rating_bucket × endgame_type) offset table; informs whether the `t=100 + 4-ply` proxy needs a rating-dependent correction
- [ ] **VALID-04**: Parity proxy validation — agreement between "even material at endgame entry" and "Stockfish eval ∈ [-0.5, +0.5] at endgame entry"; agreement rate and any systematic offset documented; composite Endgame Skill formula reassessed if Parity has its own offset

### Population Baselines & Zone Calibration (BENCH)

- [ ] **BENCH-01**: Upgraded `/benchmarks` skill queries the benchmark DB and produces per-(rating_bucket × TC × platform × endgame_type) population baselines for Conversion, Parity, Recovery, composite Endgame Skill, average clock at endgame entry, and timeout rates — replacing the current FlawChess-user-based baselines as the primary reference
- [ ] **BENCH-02**: Skill computes rating-specific zone thresholds (Conversion 50/70, Recovery 15/35, Endgame Skill 40/60 are currently global) using the median-user-at-rating-on-warning/success-boundary rule, per rating bucket
- [ ] **BENCH-03**: Rating-bucketed zone-threshold updates land in `frontend/src/lib/theme.ts` (or wherever the constants ultimately live); milestone is INCOMPLETE until the constants ship in code and are reviewed in PR. If rating-bucketed thresholds need larger UI plumbing than a constants edit (e.g., user-rating-aware lookup at render time), split into a follow-up phase via mid-milestone discuss
- [ ] **BENCH-04**: `/db-report` skill extended with benchmark-DB coverage so DB-health reports describe both prod and benchmark databases

## Future Requirements (v1.13+)

Deferred from SEED-002. Tracked but not in v1.12 scope.

- **PERC-01**: Percentile badges in the Endgame tab UI (e.g., "top 20% Parity at your rating") — motivational flavor; population infrastructure (this milestone) is the prerequisite
- **TRAJ-01**: Per-user peer-trajectory comparisons ("you're improving 2x faster than typical 1500 players") — needs longitudinal cohort data, not just snapshot baselines
- **CHESS-COM-BL-01**: chess.com population baselines — option (b) from the seed: reuse Lichess baselines via an explicit Lichess→chess.com rating-conversion formula (e.g., ChessGoals equivalence tables). v1.12 explicitly defers chess.com to self-referential only (option (c)); v1.13 decides on (b) vs continued (c)
- **HYBRID-CLASS-01**: Hybrid classifier (material + simple positional heuristics: king safety, pawn structure, piece activity) — only pursue if Phase B/C surfaces gaps that matter at the UI level
- **CHESS-COM-EVAL-01**: chess.com engine analysis via local Stockfish — weeks of compute per million games; out of scope unless a specific question requires it
- **EVAL-DEPTH-01**: Per-row eval-depth and source-version tracking (`eval_depth`, `eval_source_version`) added to the canonical `game_positions` schema via a uniform Alembic migration — only worth pursuing if Phase B/C analyses surface a need to filter by depth or re-derive across analyzer versions

## Out of Scope

Explicitly excluded for v1.12. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Replacing self-referential analysis in the UI | Population is layered ON TOP of self-referential, not a replacement. Self-referential remains the primary headline (rating-scale invariant, no cohort-bias issues, no privacy surface). |
| Live prod→benchmark-DB queries / prod-side lookup table | Population baselines computed in the `/benchmarks` skill; results land in code/config as constants. No runtime cross-DB connection. |
| Real-time baseline updates | Baselines are snapshots; refresh cadence (quarterly vs event-driven on new dumps) is an open question for the discuss phase |
| Per-user move-accuracy metrics | Different feature, different data pipeline |
| Stratifying ingestion by endgame type | Endgame-type incidence preserved at natural population rate so the DB is a valid population sample for any cross-cutting analysis |
| Percentile badges in the UI | Motivational flavor — deferred to v1.13+ |
| chess.com Lichess-rating-mapped baselines | Naive reuse holds a 1400 chess.com user to a 1700–1800 Lichess standard; deferred to v1.13 with explicit conversion |
| VAL-01 retrofit (v1.11 insights snapshot test) | Separate concern from population baselines; promote via `/gsd-quick` rather than bundling into v1.12 |

## Traceability

Filled by `gsd-roadmapper` when ROADMAP.md is generated.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | TBD | Not started |
| INFRA-02 | TBD | Not started |
| INFRA-03 | TBD | Not started |
| INGEST-01 | TBD | Not started |
| INGEST-02 | TBD | Not started |
| INGEST-03 | TBD | Not started |
| INGEST-04 | TBD | Not started |
| INGEST-05 | TBD | Not started |
| INGEST-06 | TBD | Not started |
| VALID-01 | TBD | Not started |
| VALID-02 | TBD | Not started |
| VALID-03 | TBD | Not started |
| VALID-04 | TBD | Not started |
| BENCH-01 | TBD | Not started |
| BENCH-02 | TBD | Not started |
| BENCH-03 | TBD | Not started |
| BENCH-04 | TBD | Not started |

**Coverage:** 17 requirements total (3 INFRA, 6 INGEST, 4 VALID, 4 BENCH)

---
*Last updated: 2026-04-25 — milestone open*
