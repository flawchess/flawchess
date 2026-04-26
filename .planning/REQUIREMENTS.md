# Requirements: FlawChess v1.12 Benchmark DB Infrastructure & Ingestion Pipeline

**Defined:** 2026-04-25
**Scope-down:** 2026-04-26 — VALID-* and BENCH-* moved to a future milestone (SEED-006). See "Deferred to Future Milestone" below.
**Source:** `.planning/seeds/SEED-002-benchmark-db-population-baselines.md`
**Goal (v1.12, scoped):** Ship the benchmark DB infrastructure (separate Postgres instance, MCP server, eval-metadata migration) and a resumable Lichess monthly-dump ingestion pipeline stratified by rating × time control. Pipeline correctness verified by smoke test; populating the DB at full scale is operational, not a milestone gate.
**Goal (deferred to SEED-006):** Validate the material-vs-eval classifier at 10–100x larger scale, surface rating-stratified offsets, validate the Parity proxy, and recalibrate gauge zones per rating bucket.

## v1.12 Requirements

### Benchmark DB Infrastructure (INFRA)

- [ ] **INFRA-01**: Separate `flawchess-benchmark` PostgreSQL 18 instance, deployed via `docker-compose.benchmark.yml`, isolated from dev/prod
- [ ] **INFRA-02**: Benchmark DB uses the **same canonical analytical schema and Alembic migrations** as dev/prod/test — no fork or benchmark-only variant of the games / game_positions tables. Lichess `[%eval` annotations populate the existing `game_positions.eval_cp` and `game_positions.eval_mate` columns. Benchmark-only **ops tables** (currently `benchmark_selected_users`, `benchmark_ingest_checkpoints`) that exist solely to drive the ingest orchestrator are exempt: they live only in the benchmark DB, are created via `Base.metadata.create_all()` against the benchmark engine on first invocation, and are never touched by dev/prod/test. Decision rationale: RESEARCH.md §15 Q3, plans 69-04 / 69-05.
- [ ] **INFRA-03**: Read-only MCP server `flawchess-benchmark-db` configured and documented in `CLAUDE.md` §Database Access alongside the existing two MCP DB servers

### Ingestion Pipeline (INGEST)

- [ ] **INGEST-01**: Bulk ingestion script reads Lichess monthly PGN dumps from `database.lichess.org`, with eval-presence pre-filter via streaming text scan (zgrep or equivalent) BEFORE python-chess game-tree parsing — so the ~85% of dump games without `[%eval` headers never reach the structural parser. Eval values populate the existing `game_positions.eval_cp` / `game_positions.eval_mate` columns (no schema additions)
- [ ] **INGEST-02**: Stratified subsampling on (rating_bucket × time_control) only — 5 rating buckets (800–1200, 1200–1600, 1600–2000, 2000–2400, 2400+) × 4 TCs (bullet/blitz/rapid/classical), uniformly at random within each cell, preserving natural endgame-type incidence
- [ ] **INGEST-03**: Player-side bucketing — separate `WhiteElo` and `BlackElo` headers determine each side's rating bucket independently; aggregations over `game_positions` never roll up by a single game-level rating field
- [ ] **INGEST-04**: Resumable ingest — checkpoint table keyed by `(dump_filename, byte_offset_or_game_index)`, idempotent inserts via existing `(platform, platform_game_id)` unique constraint, SIGINT-safe batch flush, per-batch skip / insert / error logging
- [ ] **INGEST-05**: Per-cell user-pool sizing is parameterized at ingestion time via the `--per-cell` flag (default 500 distinct users per (rating × TC) cell), with per-player eval-bearing-game floor of K (default 10, per D-12). Storage and aggregate-sample-size targets are operational guidance for the actual ingest run, not v1.12 milestone gates — they become entry criteria for SEED-006 phases that consume the populated DB. (Original target language — 50–100 GB storage, ≥1k queen-endgame samples per cell — was dropped in the 2026-04-26 scope-down after the per-cell sample-unit pivoted from games-per-endgame-type to distinct-users-per-cell.)
- [x] **INGEST-06**: Centipawn convention (signed from white's POV, centipawns vs pawn-units) verified by `tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white` — asserts `[%eval 2.35]` → +235 cp, `[%eval -0.50]` → -50 cp, `[%eval #4]` → mate=4, all from white's POV via `pov.white().score()` / `.mate()`. Runs in CI on every commit. (Original scope also added `eval_depth` and `eval_source_version` columns to `games`; both dropped on 2026-04-26 after the smoke ingest revealed Lichess's `/api/games/user` endpoint emits bare `[%eval cp]` annotations with no depth field, leaving both columns dead. Position-level eval presence is filterable via `game_positions.eval_cp IS NOT NULL`. If a future eval source needs a discriminator, reintroduce a column at that point.)

## Deferred to Future Milestone (SEED-006)

Moved out of v1.12 in the 2026-04-26 scope-down. These 8 requirements remain tracked and surface when the full benchmark DB ingest completes — see `.planning/seeds/SEED-006-benchmark-population-zone-recalibration.md`.

### Classifier & Parity Validation (VALID)

- [ ] **VALID-01**: Replicated material-vs-eval classifier validation against the benchmark DB matching the 2026-04-07 methodology (t=100 centipawn threshold + 4-ply persistence vs Stockfish eval u=100); report written to `reports/classifier-validation-benchmark-YYYY-MM-DD.md` with structure parallel to the original report so side-by-side comparison is trivial
- [ ] **VALID-02**: Quantitative checkpoint gate — per-(endgame_type) offset is materially different from the 2026-04-07 result when (a) the point estimate falls outside the prior 95% CI AND (b) |Δ| > 2pp absolute. Both must hold on Pawn / Rook / Minor cells to trigger pause-and-investigate. Gate-pass authorizes downstream phases to proceed
- [ ] **VALID-03**: Rating-stratified offset analysis — per-(rating_bucket × endgame_type) offset table; informs whether the `t=100 + 4-ply` proxy needs a rating-dependent correction
- [ ] **VALID-04**: Parity proxy validation — agreement between "even material at endgame entry" and "Stockfish eval ∈ [-0.5, +0.5] at endgame entry"; agreement rate and any systematic offset documented; composite Endgame Skill formula reassessed if Parity has its own offset

### Population Baselines & Zone Calibration (BENCH)

- [ ] **BENCH-01**: Upgraded `/benchmarks` skill queries the benchmark DB and produces per-(rating_bucket × TC × platform × endgame_type) population baselines for Conversion, Parity, Recovery, composite Endgame Skill, average clock at endgame entry, and timeout rates — replacing the current FlawChess-user-based baselines as the primary reference
- [ ] **BENCH-02**: Skill computes rating-specific zone thresholds (Conversion 50/70, Recovery 15/35, Endgame Skill 40/60 are currently global) using the median-user-at-rating-on-warning/success-boundary rule, per rating bucket
- [ ] **BENCH-03**: Rating-bucketed zone-threshold updates land in `frontend/src/lib/theme.ts` (or wherever the constants ultimately live); SEED-006 milestone is INCOMPLETE until the constants ship in code and are reviewed in PR. If rating-bucketed thresholds need larger UI plumbing than a constants edit (e.g., user-rating-aware lookup at render time), split into a follow-up phase via mid-milestone discuss
- [ ] **BENCH-04**: `/db-report` skill extended with benchmark-DB coverage so DB-health reports describe both prod and benchmark databases

## Future Requirements (post-SEED-006)

Deferred from SEED-002. Tracked but not in v1.12 scope.

- **PERC-01**: Percentile badges in the Endgame tab UI (e.g., "top 20% Parity at your rating") — motivational flavor; population infrastructure (this milestone) is the prerequisite
- **TRAJ-01**: Per-user peer-trajectory comparisons ("you're improving 2x faster than typical 1500 players") — needs longitudinal cohort data, not just snapshot baselines
- **CHESS-COM-BL-01**: chess.com population baselines — option (b) from the seed: reuse Lichess baselines via an explicit Lichess→chess.com rating-conversion formula (e.g., ChessGoals equivalence tables). v1.12 explicitly defers chess.com to self-referential only (option (c)); v1.13 decides on (b) vs continued (c)
- **HYBRID-CLASS-01**: Hybrid classifier (material + simple positional heuristics: king safety, pawn structure, piece activity) — only pursue if Phase B/C surfaces gaps that matter at the UI level
- **CHESS-COM-EVAL-01**: chess.com engine analysis via local Stockfish — weeks of compute per million games; out of scope unless a specific question requires it

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

Filled by `gsd-roadmapper` 2026-04-25; updated 2026-04-26 for the Phase 70-73 deferral.

| Requirement | Phase | Milestone | Status |
|-------------|-------|-----------|--------|
| INFRA-01 | Phase 69 | v1.12 | In progress |
| INFRA-02 | Phase 69 | v1.12 | In progress |
| INFRA-03 | Phase 69 | v1.12 | In progress |
| INGEST-01 | Phase 69 | v1.12 | In progress |
| INGEST-02 | Phase 69 | v1.12 | In progress |
| INGEST-03 | Phase 69 | v1.12 | In progress |
| INGEST-04 | Phase 69 | v1.12 | In progress |
| INGEST-05 | Phase 69 | v1.12 | In progress |
| INGEST-06 | Phase 69 | v1.12 | In progress |
| VALID-01 | Phase 70 | Deferred (SEED-006) | Not started |
| VALID-02 | Phase 70 | Deferred (SEED-006) | Not started |
| VALID-03 | Phase 71 | Deferred (SEED-006) | Not started |
| VALID-04 | Phase 72 | Deferred (SEED-006) | Not started |
| BENCH-01 | Phase 73 | Deferred (SEED-006) | Not started |
| BENCH-02 | Phase 73 | Deferred (SEED-006) | Not started |
| BENCH-03 | Phase 73 | Deferred (SEED-006) | Not started |
| BENCH-04 | Phase 73 | Deferred (SEED-006) | Not started |

**Coverage:**
- v1.12 (active): 9 requirements (3 INFRA, 6 INGEST)
- Deferred to SEED-006: 8 requirements (4 VALID, 4 BENCH)
- Total tracked: 17

---
*Last updated: 2026-04-26 — Phase 70-73 deferral; VALID-* and BENCH-* moved to Deferred section pointing at SEED-006.*
