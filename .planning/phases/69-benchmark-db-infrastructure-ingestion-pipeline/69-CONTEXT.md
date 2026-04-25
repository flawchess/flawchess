# Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up an isolated `flawchess-benchmark` PostgreSQL 18 instance (same canonical schema and Alembic migrations as dev/prod/test, no benchmark-only schema additions), wire a third read-only MCP server `flawchess-benchmark-db` to it, add the canonical `eval_depth` + `eval_source_version` columns to the `games` table, and build a resumable ingestion pipeline that selects ~500 distinct Lichess players per (rating × time_control) cell from one monthly Lichess dump and imports each selected user's full eval-bearing + non-eval game history (last 36 months, capped at 20k games) via the existing FlawChess Lichess import pipeline.

Population-pooled rates (for Phase 70-72 classifier validation) and per-user-rate distributions (for Phase 73 zone calibration) are both supported by this sample because per-user histories are preserved.

Phase boundary excludes any analysis or zone-calibration logic — those are Phase 70-73 scope. Phase 69 ends when (a) the benchmark DB is queryable via MCP, (b) the eval_depth/source migration has shipped to all envs, (c) one full ingestion run has populated stratified per-cell samples, and (d) ingest is verified resumable.

</domain>

<decisions>
## Implementation Decisions

### Cheat contamination handling

- **D-01:** No cheat-filtering logic in Phase 69. Document residual upward bias in 2000+ rating buckets in the ingestion script header AND in the Phase 70 / Phase 73 reports. Phase 70's gate verdict (keyed on Pawn / Rook / Minor cells) is the safety net — those cells are dominated by 1200-2000 ratings where cheat contamination is minimal. Bans-list cross-reference is a v1.13+ candidate if Phase 71 rating-stratified analysis flags 2000+ baselines as anomalous.

### Storage scope and retention

- **D-02:** Ingest selection scan uses one recent Lichess monthly dump. Per-user history then comes from Lichess API (not multi-month dumps). If selection cells are under-quota with one month of selection signal, expand to two months — but do not pre-emptively scan multiple dumps.
- **D-03:** Delete the selection-scan dump after ingest completes successfully (row counts verified). Re-ingest = re-download from `database.lichess.org`.

### Sampling strategy (Lichess monthly dump → users → import pipeline)

- **D-04 (supersedes earlier random-game framing):** Sample unit is **distinct players**, not games. Per (rating × time_control) cell, target ~500 distinct players (planning-time tunable per D-15) selected from one monthly dump scan. Selection bucket = the player's median Elo + modal TC across their games in the snapshot month.
- **D-05:** Per-game player-side bucketing for analytics queries is preserved (per INGEST-03). A single game contributes White's stats to White's Elo bucket and Black's stats to Black's Elo bucket. Selection is at the user level; bucketing for analytics is at the per-game-side level.
- **D-10:** Selection assigns each user to one (rating × TC) cell at selection time, but their FULL imported history is stored regardless of within-history bucket drift. Per-user-rate analytics queries filter to a target (rating × TC) range at query time. A single user can produce stats in multiple cells if their history spans them. Cohort drift is accepted; it is a feature, not a bug.

### Ingestion pipeline (U1 — reuse existing import pipeline)

- **U1 approach locked.** For each selected user: create a stub `User` row in the benchmark DB and trigger the existing `app/services/import_service.run_import(platform=lichess, username=...)`. The existing `app/services/lichess_client.py` handles streaming via `/api/games/export/{username}?evals=true`, the existing `app/services/position_classifier.py` handles classification, and existing per-user resumability handles checkpoints inside one user's import.
- **D-08 (replaces earlier `is_benchmark` flag idea):** No `is_benchmark` flag on `User` table. Benchmark DB instance isolation (INFRA-01) handles separation — every User row in the benchmark DB is a benchmark user by definition. The prod User table never sees these rows.
- **D-09:** No per-user game cap as a primary constraint. Use the time window (D-13) and outlier hard-skip (D-14) instead. Per-user game counts are logged during ingest for sanity inspection.
- **D-11:** Per selected user, ingest **full game history (eval-bearing AND non-eval)** within the time window (D-13). Eval columns NULL for non-eval games — same handling as chess.com imports. Phase 70-72 classifier-validation queries filter to `eval_cp IS NOT NULL` at query time.
- **D-12:** Selection threshold filter — pick users from the dump scan who have **≥ K eval-bearing games** in the snapshot month (start with K=5, planning-time tunable). Filters out one-off players, biases the sample toward Lichess accounts that have opted into analysis (eval availability is sticky per account).
- **D-13:** Per-user history bounded via Lichess API `since=` parameter set to **36 months back** from the selection-month dump end. Eval-bearing and non-eval games both ingested within window.
- **D-14:** Hard skip (NOT warning) on any single user whose window-bounded ingest would exceed **20k games**. Logged with username + count for audit. 20k games in 36 months is >18/day — almost certainly a bot or eval-spam account.
- **D-15 (revised 2026-04-25):** Ingestion is **staged via a `--per-cell N` flag** on the orchestrator script, not run once at a fixed N. Stages:
  1. **Smoke stage** — `--per-cell 3` (60 users total) to verify the pipeline end-to-end on real data.
  2. **Interim milestone** — `--per-cell 100` (2000 users total) is the v1.12 Phase 69 completion target. Top-up only (idempotent re-run brings each cell from 3 → 100).
  3. **Decision gate** — after the 100/cell run completes, inspect per-cell game-count distributions, storage footprint, and any tail thinness for Phase 73's per-user-rate analytics. Then decide whether to push toward 500/cell (the original D-15 target) or hold at 100/cell. That decision is **out of Phase 69 scope** — Phase 69 ends when the 100/cell run is verified.
  4. INGEST-05's 50-100 GB target very likely holds at 100/cell. If a future top-up pushes N higher, storage budget gets revisited at that decision point.
- **D-15a (incremental top-up mechanics):** Selection-scan output is persisted once as a username list per cell (not regenerated per run). The orchestrator counts distinct users already imported per cell in the benchmark DB on startup, draws `N - current` additional usernames from the persisted pool, and imports them. Per-game `(platform, platform_game_id)` unique constraint makes already-imported games no-op on re-run. Per-user outer-loop checkpoint records "user X completed" so an interrupted run resumes mid-pool without re-counting.

### Schema migration scope (INGEST-06)

- **D-06:** Existing prod `games` rows leave `eval_depth` + `eval_source_version` as NULL forever after the migration. No backfill via reimport. Reasoning: Phase 70+ queries the benchmark DB, not prod; prod's per-user analysis doesn't currently use depth.
- **D-07:** For Lichess imports, populate `eval_depth` from the API per-game where the metadata is surfaced; fallback NULL otherwise. `eval_source_version` is a constant string per source (e.g. `"lichess-pgn"`), with verification of the actual API surface during Phase 69 implementation. chess.com imports leave both NULL (chess.com has 0% eval coverage).

### Claude's Discretion

- Exact zgrep / streaming pre-filter tool for the dump selection scan (zgrep, ripgrep, pure Python with zstd, etc.). Performance constraint: must scan a ~30-50 GB compressed monthly dump in a few hours on dev hardware.
- Centipawn convention verification format (script self-test vs. one-off validation note). INGEST-06 only requires that it be documented somewhere.
- MCP server local port (e.g. 5433 vs 5434), Postgres user / password setup for the read-only role, and exact `docker-compose.benchmark.yml` structure (likely paralleling `docker-compose.dev.yml` with a different volume + port).
- Stub User row schema strategy in benchmark DB (sentinel email format, password hash placeholder, is_active value) — must satisfy FastAPI-Users invariants but never serve auth.
- Ingestion outer-loop checkpoint structure (which selected users have completed). Existing per-user resumability handles within-user checkpoints; the new outer structure is a list of usernames and per-user state.
- Selection-scan player-bucketing algorithm details — how to handle players whose games span multiple TCs in the snapshot month (use modal TC, or admit to all TCs they played in, etc.).

### Folded Todos

None — no pending todos in `.planning/STATE.md` matched this phase's scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project / milestone scope

- `.planning/REQUIREMENTS.md` — v1.12 requirements list (INFRA-01..03, INGEST-01..06 are Phase 69 scope)
- `.planning/milestones/v1.12-ROADMAP.md` — Phase 69 success criteria (5 items, locked) and milestone-level cross-phase notes (esp. Phase 70 gate)
- `.planning/seeds/SEED-002-benchmark-db-population-baselines.md` — full design rationale, prior-work context, open questions explicitly punted to discuss-phase, and not-in-scope list

### Foundational prior work (MUST read before classifier replication)

- `reports/endgame-conversion-recovery-analysis.md` (2026-04-07) — material-vs-eval validation report; defines the t=100 + 4-ply persistence config, documents the systematic offset (Conv +2-8pp, Rec -4-6pp), and is the null hypothesis Phase 70 replicates against
- `docs/endgame-analysis-v2.md` §5 — min-sample-size convention (10 games per cell)
- `reports/benchmarks-2026-04-25.md` — current `/benchmarks` skill output, useful as the "before" reference for Phase 73's upgrade

### Code touch-points (existing modules the new pipeline reuses)

- `app/services/import_service.py` — orchestrates per-user import; `_BATCH_SIZE = 10` is the OOM-safe constant from the 2026-03-22 production incident
- `app/services/lichess_client.py` — streams `/api/games/export/{username}` NDJSON; supports `since=`, `evals=true`
- `app/services/position_classifier.py` — material classification, endgame_class, material_signature; runs at import time per-position
- `app/services/zobrist.py` — Zobrist hashes (white/black/full) computed at import
- `app/models/game.py` — canonical `games` table; INGEST-06 adds `eval_depth` (SmallInteger nullable) + `eval_source_version` (String nullable)
- `app/models/game_position.py` — canonical `game_positions`; existing `eval_cp` (SmallInteger) and `eval_mate` (SmallInteger) populate from Lichess `[%eval` annotations
- `app/repositories/query_utils.py` — shared `apply_game_filters()` used by all stat queries; benchmark queries from `/benchmarks` will extend this same pattern

### Infrastructure

- `docker-compose.dev.yml` — analog for `docker-compose.benchmark.yml` (different volume name, port, project name)
- `deploy/init-dev-db.sql` — analog for benchmark DB user/role/grants init
- `CLAUDE.md` §Database Access (MCP) — third MCP server `flawchess-benchmark-db` documented here on completion (per INFRA-03)
- `CLAUDE.md` §Critical Constraints — async SQLAlchemy, httpx, Standard-variant-only filtering apply uniformly to ingestion
- `CLAUDE.md` §Database Design Rules — FK constraints mandatory, unique constraints for natural keys, appropriate column types
- `CLAUDE.md` §Error Handling & Sentry — retry loops capture once at top level; never per-attempt during ingest

### External

- `https://database.lichess.org/` — Lichess monthly PGN dump source (compressed `.pgn.zst`, ~30-50 GB per month)
- Lichess `/api/games/export/{username}` — public endpoint, supports `since=` (epoch ms), `until=`, `evals=true`, NDJSON streaming

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`import_service.run_import`** — the entire per-user import pipeline. U1 calls this directly per selected username. Reused as-is, no fork.
- **`lichess_client`** — already streams `/api/games/export/{username}` with eval support and parses Lichess PGN. Just needs the `since=` parameter wired through (verify the existing arg surface).
- **`position_classifier`** — runs per-position during import, computes material_signature, endgame_class, etc. Works identically for benchmark-DB ingestion.
- **`zobrist`** — Zobrist hash computation runs unchanged.
- **Alembic migration chain** — adding `eval_depth` + `eval_source_version` columns is one new migration applied uniformly to dev/prod/test/benchmark.

### Established Patterns

- **`_BATCH_SIZE = 10` games per commit** is the OOM-safe constant per the 2026-03-22 production incident. Benchmark ingestion must respect this; do not bump for "perceived" speed gains.
- **`(platform, platform_game_id)` unique constraint on `games`** makes per-game inserts idempotent. Re-runs no-op on already-imported games — gives D-04/D-13 resume semantics for free at the per-game level.
- **Async SQLAlchemy session-per-coroutine rule** (CLAUDE.md Critical Constraints): never `asyncio.gather` on the same `AsyncSession`. Per-user imports stay sequential within one orchestrator process.
- **httpx async only** — no `requests`, no `berserk`. All Lichess API access through existing `lichess_client`.
- **Sentry capture only at outer error boundary** — retry loops do not capture per-attempt; the orchestrator captures once on terminal failure.

### Integration Points

- New `docker-compose.benchmark.yml` parallels `docker-compose.dev.yml` (different volume, different port — likely 5433, project name `flawchess-benchmark`).
- New MCP server entry in user-level `~/.claude.json` parallels existing `flawchess-db` and `flawchess-prod-db` entries; documented in `CLAUDE.md` §Database Access (MCP) per INFRA-03.
- New scripts in `scripts/`: `select_benchmark_users.py` (one-shot dump scan + cell-stratified selection), `import_benchmark_users.py` (orchestrator over selected users → existing import pipeline), and possibly `seed_benchmark_db.py` (one-shot bootstrap of stub User rows).
- Alembic migration adds `eval_depth` (SmallInteger nullable) + `eval_source_version` (String nullable) to `games`. Applied to all envs uniformly.

</code_context>

<specifics>
## Specific Ideas

- **Selection scan uses zgrep-style streaming text filter on `[%eval` presence + header extraction** before any python-chess parsing — same principle as INGEST-01 mandates, even though the role of pre-filter has shifted (selection signal rather than direct ingest pipeline).
- **Player-side bucketing is the canonical bucketing rule** (INGEST-03). Selection picks users by their median Elo + modal TC across snapshot-month games; analytics queries bucket per-game-side via `WhiteElo` / `BlackElo`.
- **Phase 70 gate is the safety net for cheat contamination** (D-01) — keyed on Pawn / Rook / Minor cells, dominated by 1200-2000 ratings where contamination is minimal.
- **Phase 70-72 use population-pooled rates** (random-sample friendly), Phase 73 uses per-user-rate distributions (full-history friendly). U1 supports both because per-user histories are preserved.
- **No `is_benchmark` schema flag** — benchmark DB instance isolation does the work. Adding a column that's always-TRUE in benchmark and always-FALSE in prod is dead schema noise.
- **No per-user game cap; instead a 36-month time window + 20k hard-skip outlier rule.** Time window gives uniform per-user data depth; outlier rule catches bot accounts without truncating real heavy players.
- **Storage budget is a soft target, not a contract.** INGEST-05's 50-100 GB may relax to 150-250 GB at N=500 players per cell over 36 months. Pilot first, then resize N. Document final storage in the phase's verification report.

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 69 scope (deferred or scoped to other phases)

- **Bans-list cross-reference for cheat filtering** — v1.13+ candidate. Trigger: Phase 71 rating-stratified analysis flags 2000+ buckets as anomalous vs prior data.
- **Hybrid two-tier sampling (random-game stratum + per-user stratum)** — considered and rejected as overbuilt for v1.12 MVP. U1 covers both stat types from one stratum.
- **CPL-based outlier rejection for cheat detection** — requires per-move Stockfish eval which we don't have for non-eval games. v1.13+ if a hybrid-classifier experiment lands.
- **Phase 69 split into 69 + 69.1** — not split. The roadmap's note about possibly splitting INFRA from INGEST mid-milestone via `/gsd-insert-phase` is preserved as an option if planning surfaces a real effort delta. With U1 reusing the existing import pipeline, the INGEST half is smaller than the original game-level sampling plan implied, so split is less likely needed.
- **Refresh cadence (manual / scripted / scheduled)** — belongs in Phase 73 (skill upgrade) not Phase 69. Phase 69 just builds the ingestion script; cadence is operational policy decided when `/benchmarks` lands.
- **Multi-month dump scan ingestion (U2)** — rejected in favor of U1 for code reuse and per-user history depth.
- **Backfill of `eval_depth` / `eval_source_version` for existing prod games via reimport** — out of scope (D-06).
- **chess.com population baselines** — explicitly v1.13+ per REQUIREMENTS.md "Future Requirements" (`CHESS-COM-BL-01`).
- **`is_benchmark` User flag** — rejected in favor of DB instance isolation.
- **Per-user game cap** — rejected in favor of time-window + 20k outlier skip.

### Reviewed Todos (not folded)

None — no pending todos in `.planning/STATE.md` were within scope.

</deferred>

---

*Phase: 69-benchmark-db-infrastructure-ingestion-pipeline*
*Context gathered: 2026-04-25*
