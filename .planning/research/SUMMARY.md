# Project Research Summary

**Project:** FlawChess v1.5 — Game Statistics & Endgame Analysis
**Domain:** Chess analytics platform — per-position metadata enrichment and endgame tab
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

FlawChess v1.5 adds endgame analytics (game phase, material classification, endgame type W/D/L) on top of an existing production platform. The research confirms no new libraries are needed — every required capability (material counting, PGN eval parsing, NAG annotations) is available in the already-installed python-chess 1.11.2. The core implementation is a new `position_classifier.py` service that slots into the existing import pipeline at zero additional cost: the board is already constructed at each ply for Zobrist hash computation, so classification runs in the same loop with no extra I/O or PGN re-parses.

The recommended approach has a strict sequential dependency: schema migration first (nullable columns, instant in PostgreSQL 18), then import pipeline wiring, then a background backfill of existing games from stored PGN (no re-download required), then new indexes, and finally the Endgames tab backend and frontend. The core W/D/L endgame statistics require no engine analysis and will work for 100% of imported games — a meaningful competitive advantage over lichess Insights and chess.com Insights, which only show phase accuracy for previously-analyzed games. Engine accuracy import (chess.com accuracy float, lichess per-move evals) is a lower-priority follow-on; P1 is the analysis-free endgame analytics.

The top risks are: (1) the backfill triggering OOM on the 3.7 GB Hetzner server if not batched at 10 games at a time, (2) chess.com accuracy absent for 95%+ of games — all accuracy columns must be nullable with graceful UI fallback, and (3) material signature non-canonicalization causing split statistics if the normalization convention is not enforced at compute time. All three are preventable with disciplined schema design and unit tests before any deployment.

## Key Findings

### Recommended Stack

No new dependencies are required for v1.5. The entire feature set — game phase detection, material signature computation, endgame classification, eval extraction from PGN, and accuracy import — is covered by the existing stack. python-chess provides `board.pieces()` for material counting, `node.eval()` for centipawn extraction from PGN annotations, and `node.nags` for move quality. The only API-level changes are adding `evals=True` and `accuracy=True` params to the lichess client, and extracting the existing `accuracies` field from chess.com game JSON.

**Core technologies:**
- **python-chess 1.11.2**: Material counting via `board.pieces()`, PGN eval via `node.eval()`, NAG annotations via `node.nags` — all stable since 1.x, no version upgrade needed
- **SQLAlchemy 2.x + Alembic**: Add 4 nullable `SmallInteger`/`String` columns to `game_positions`; ADD COLUMN DEFAULT NULL is metadata-only in PostgreSQL 18 (instant, no table rewrite)
- **PostgreSQL 18**: Composite partial index `(user_id, endgame_class) WHERE endgame_class IS NOT NULL` covers the primary endgame query; temporary partial index on `WHERE game_phase IS NULL` drives the backfill scan efficiently
- **FastAPI + existing router/service/repository pattern**: New `endgames.py` router, service, and repository follow the established 3-layer architecture with no deviation

### Expected Features

**Must have (P1 — v1.5 launch):**
- Game phase computed per position at import (opening/middlegame/endgame integer stored in `game_positions`) — foundational for all analytics
- Material signature per position (canonical string e.g. `KQRBNPkrbnpp`) — enables endgame class derivation and future drill-down
- Endgame class derived from material signature (6 categories: pawn, rook, minor_piece, queen, complex/mixed, pawnless)
- Material imbalance per position (signed integer in pawn units) — enables conversion/recovery statistics
- Endgames tab: W/D/L breakdown by endgame type with time control / color / recency filters
- Conversion stats: W/D/L when materially up vs. down, broken out by game phase

**Should have (P2 — after v1.5 validation):**
- Engine accuracy import from chess.com (`accuracies.white/black` float, game-level only)
- Per-move eval import from lichess (`evals=True` param, only for analyzed games)
- Material configuration drill-down UI (KRP vs KR level within a rook endgame bucket)
- Phase label / material class badge in the existing Move Explorer

**Defer to v2+:**
- Per-phase accuracy for chess.com games (not in public API; requires local Stockfish or paid partnership)
- Endgame training module (crosses into training product, outside analytics scope)
- Opponent endgame scouting (natural follow-on to existing opponent scouting, separate milestone)

### Architecture Approach

The architecture is a clean extension of the existing 3-layer pattern (router → service → repository). A new `position_classifier.py` service computes all position metadata from `chess.Board` in a single pass and integrates into `zobrist.py`'s existing per-ply loop. The existing `game_positions` table gains 4 nullable columns (instant migration); a new optional `game_engine_analysis` table handles per-game accuracy data separately to avoid column pollution on `games`. A background `backfill_service.py` re-parses stored PGN from `games.pgn` to populate new columns on existing rows — no API re-fetching needed. The Endgames tab follows an identical structure to the existing Openings tab: `FilterPanel` for standard filters, new `EndgameTypeFilter` for endgame class, `COUNT(DISTINCT game_id)` aggregation to avoid double-counting position rows.

**Major components:**
1. `position_classifier.py` — pure-Python service: computes game_phase (material threshold), material_signature (canonical string), material_imbalance (signed int), endgame_class (6-bucket string) from `chess.Board`
2. `backfill_service.py` — background asyncio task: reads `games.pgn`, replays moves, batch-UPDATEs `game_positions` at 10 games / ~400 rows per commit
3. `endgames_repository.py` + `endgames_service.py` + `routers/endgames.py` — standard 3-layer stack for the new `/endgames/stats` endpoint
4. `frontend/src/pages/Endgames.tsx` + `components/endgames/` — new page reusing FilterPanel, TanStack Query hook `useEndgames`, TypeScript type mirrors

### Critical Pitfalls

1. **chess.com accuracy absent for most games** — `accuracies` field is only present for user-reviewed games (free users: 1 review/day). Always null-guard with `game.get("accuracies", {})`. Store as `FLOAT NULL`. Design UI to show "n/a" not 0%. Do not advertise accuracy import as a core feature.

2. **Backfill OOM risk on 3.7 GB server** — Production was previously OOM-killed at batch_size=50. Backfill must process 10 games (~400 position rows) per commit batch, run as a standalone script (not inside an Alembic migration), and support resume via `WHERE game_phase IS NULL`. Always run `VACUUM game_positions` after backfill to clear dead tuples from MVCC row versions.

3. **Non-canonical material signatures split statistics** — Without an explicit normalization convention, `KRP_KR` and `KR_KRP` both appear depending on which color the user played, halving query counts. Enforce: stronger side (higher material value) first; if equal, lexicographic. Write a unit test: rotating board colors must produce the same canonical string.

4. **Game phase boundary inconsistency** — A single material threshold causes early queen trades to incorrectly classify 50 subsequent moves as "endgame". Use a tapered phase score (Q=4, R=2, B=1, N=1 weights; max 24; endgame < 8) and a ply floor (never label "endgame" before ply 10). Document the formula for users.

5. **COUNT(*) instead of COUNT(DISTINCT game_id)** — A game entering a rook endgame at ply 30 produces ~50 position rows all with `endgame_class='rook'`. Every endgame aggregation query must use `COUNT(DISTINCT game_id)` to avoid 50x inflated statistics.

## Implications for Roadmap

Based on research, the hard sequential dependency chain dictates a 4-phase structure with an optional 5th phase for engine accuracy:

### Phase 1: Schema + Position Classifier
**Rationale:** Everything else depends on the schema existing and the classifier being correct. Write and unit-test it in isolation first, then integrate. Schema migration is instant (nullable columns); classifier is pure Python with no DB dependency.
**Delivers:** `position_classifier.py` with unit tests covering edge cases (early queen trade, symmetric endgames, canonical signature); Alembic migration adding 4 columns to `game_positions`; updated `bulk_insert_positions` chunk_size (8 → 12 columns = 2730 rows max).
**Addresses:** Game phase detection, material signature, endgame class, material imbalance (all P1 features from FEATURES.md)
**Avoids:** Phase boundary inconsistency (pitfall 5), non-canonical signatures (pitfall 4), chunk_size miscalculation (architecture pitfall)

### Phase 2: Import Pipeline Wiring + Backfill
**Rationale:** New imports must populate new columns immediately on deploy. Existing rows need backfill from stored PGN. Both must be correct before analytics queries can return meaningful results.
**Delivers:** Modified `zobrist.py` / `import_service.py` wiring classifier into per-ply loop; standalone `scripts/backfill_position_metadata.py` with batch_size=10, resume support (`WHERE game_phase IS NULL`), and post-backfill VACUUM step; temporary backfill index (created before, dropped after).
**Avoids:** Backfill OOM (pitfall 3), dead tuple bloat (pitfall 6), backfill non-idempotency (pitfall 8), non-batched UPDATE (performance trap)

### Phase 3: Endgames Backend + API
**Rationale:** Data is populated; backend can now aggregate it. Build the service layer and endpoints before touching the frontend so they can be validated independently via Swagger.
**Delivers:** `endgames_repository.py` (W/D/L by endgame class, conversion/recovery stats), `endgames_service.py`, `routers/endgames.py`, `schemas/endgames.py`, permanent indexes (`ix_gp_user_endgame_class` partial, `ix_gp_user_game_phase` partial); backfill progress indicator endpoint.
**Avoids:** COUNT(*) inflation (always COUNT DISTINCT), serving incomplete data before backfill completes (anti-pattern 4)

### Phase 4: Endgames Frontend Tab
**Rationale:** API is stable; now build the UI. Reuse existing patterns (FilterPanel, TanStack Query, W/D/L display components from Openings tab) to minimize novel frontend work.
**Delivers:** `Endgames.tsx` page, `EndgamesStats.tsx`, `EndgameTypeFilter.tsx`, `MaterialPhaseStat.tsx`, `useEndgames.ts` hook, navigation wiring (`/endgames` route, bottom bar + More drawer), empty states for users with no endgame data, "—" display for NULL evals.
**Avoids:** Null eval displayed as 0 (UX pitfall), no empty state for new users (UX pitfall), missing mobile layout (CLAUDE.md requirement — check both desktop sidebar and mobile variants)

### Phase 5 (Optional): Engine Accuracy Import
**Rationale:** P2 feature, independent of the core endgame analytics. Defer until user demand for accuracy data is validated. Separate optional `game_engine_analysis` table avoids polluting the `games` table with columns that are NULL for 95%+ of rows.
**Delivers:** chess.com `accuracies` field extraction in normalizer; lichess `evals=True` + `accuracy=True` param addition; optional `game_engine_analysis` table migration.
**Avoids:** chess.com accuracy absent for most games (pitfall 1 — all columns nullable, graceful UI fallback), lichess eval absent for non-analyzed games (pitfall 2), annotated PGN breaking downstream parsing (pitfall 7)

### Phase Ordering Rationale

- Schema before pipeline: column migration must exist before the import loop can write to the new columns
- Classifier before integration: correctness must be unit-tested in isolation (pure Python, no DB) before touching the live import loop
- Backfill before analytics: returning silently incomplete statistics after deploy erodes user trust; backfill progress must be tracked and surfaced
- Backend before frontend: enables API validation without UI noise; Swagger UI proves the contract before any React code is written
- Engine accuracy last: P2 feature with well-understood additional pitfalls (conditional API fields); safest to implement after the P1 pipeline is proven stable

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Backfill):** Production memory constraints require careful validation. Recommend testing the backfill script against a production DB snapshot with `docker stats` monitoring before deploying. Also review `EXPLAIN ANALYZE` on the backfill query against actual table row counts to confirm the partial index is used.
- **Phase 5 (Engine Accuracy):** The ARCHITECTURE.md finding that lichess bulk export omits analysis data (only individual game export includes it) means inline import is not feasible. The enrichment job design — when to trigger it, how to surface status to users — needs explicit design decisions before implementation.

Phases with standard patterns (skip additional research):
- **Phase 1 (Schema + Classifier):** All python-chess APIs confirmed from official docs. PostgreSQL ADD COLUMN behavior confirmed from official docs. Well-documented patterns.
- **Phase 3 (Backend API):** Follows identical pattern to existing `analysis_repository.py` / `analysis_service.py` / `routers/analysis.py`. No novel patterns.
- **Phase 4 (Frontend):** Reuses existing FilterPanel, TanStack Query hooks, W/D/L display components from Openings tab. Standard React/TypeScript work.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | python-chess APIs confirmed from official docs; PostgreSQL column-add behavior confirmed from official docs; no new libraries needed |
| Features | HIGH (P1) / MEDIUM (P2) | P1 W/D/L features are analysis-free and unambiguous; P2 accuracy features depend on conditional API fields with confirmed platform-specific limitations |
| Architecture | HIGH | Based on direct codebase inspection of all affected modules; extension points are unambiguous; 10-step build order documented |
| Pitfalls | HIGH (API limits, backfill OOM) / MEDIUM (phase boundaries, eval coverage) | chess.com API limits confirmed by moderator; backfill OOM confirmed by production history (CLAUDE.md); phase boundary heuristic and lichess eval coverage rate are community-sourced estimates |

**Overall confidence:** HIGH

### Gaps to Address

- **Backfill performance on real production data:** The OOM risk is concrete (prior production incident), but the exact row count in `game_positions` is unknown. Run the backfill against a production DB snapshot to validate batch_size=10 is sufficient. Reduce to 5 if needed.
- **Game phase boundary tuning:** The tapered phase score thresholds (opening >= 18, endgame < 8) match Stockfish conventions adapted for user-facing categories. They may need empirical tuning after seeing real data. Adjusting the thresholds later requires a backfill re-run — not a schema change — so this is low-cost to revise.
- **lichess eval coverage rate:** Estimated at "many casual games have no analysis." Actual coverage rate for the existing user base is unknown. The UI must communicate clearly how many games have accuracy data to avoid user confusion.
- **COUNT DISTINCT performance at scale:** `COUNT(DISTINCT game_id)` with a JOIN on `game_positions` requires an `EXPLAIN ANALYZE` against a representative dataset before shipping. If the partial index scan + distinct is too slow, a covering index on `(user_id, endgame_class, game_id)` may be needed.

## Sources

### Primary (HIGH confidence)
- [python-chess 1.11.2 Core docs](https://python-chess.readthedocs.io/en/latest/core.html) — `board.pieces()`, material counting, piece type constants
- [python-chess 1.11.2 PGN docs](https://python-chess.readthedocs.io/en/latest/pgn.html) — `node.eval()`, `node.eval_depth()`, `node.nags`, `node.clock()`
- [python-chess changelog](https://python-chess.readthedocs.io/en/latest/changelog.html) — 1.11.2 released Feb 2025; `eval()` off-by-one fix in 1.11.1
- [lichess-org/api OpenAPI YAML](https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/tags/games/api-games-user-username.yaml) — `evals` and `accuracy` query parameters confirmed
- [chess.com Published-Data API documentation](https://gist.github.com/andreij/0e3309200c0a6bb26308817a168203f3) — `accuracies.white/black` field confirmed, absent when not analyzed
- [chess.com forum: no per-move evals in API (moderator)](https://www.chess.com/forum/view/general/can-i-download-pgn-with-score-and-clock-using-api) — evals/game-review data confirmed not available via public API
- [postgresql.org: ALTER TABLE ADD COLUMN performance](https://www.postgresql.org/docs/current/ddl-alter.html) — ADD COLUMN DEFAULT NULL is metadata-only in PG 11+
- [postgresql.org: Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)
- Direct codebase inspection: `app/models/game_position.py`, `app/services/import_service.py`, `app/services/zobrist.py`, `app/repositories/game_repository.py`, `frontend/src/pages/Openings.tsx`

### Secondary (MEDIUM confidence)
- [Chessprogramming wiki: Game Phases](https://www.chessprogramming.org/Game_Phases) — material-based phase detection rationale, tapered eval pattern
- [Chessprogramming wiki: Tapered Eval](https://www.chessprogramming.org/Tapered_Eval) — piece phase weights for phase score
- [lichess forum: accuracy in API](https://lichess.org/forum/lichess-feedback/trying-to-find-accuracy-from-the-api) — `players.*.accuracy` field in NDJSON, consistent with spec
- [Chess endgame — Wikipedia](https://en.wikipedia.org/wiki/Chess_endgame) — endgame categories, approximate frequency statistics
- [Rook endings frequency paper](https://centaur.reading.ac.uk/65694/4/URE.pdf) — ~10% of games reach rook endgame

### Tertiary (LOW confidence)
- [chess.com forum: phase accuracy not in API](https://www.chess.com/forum/view/site-feedback/insight-data-in-public-apis) — community post; consistent with API inspection but not official documentation
- [Aimchess feature description](https://eliteai.tools/tool/aimchess) — third-party summary of Aimchess features (conversion/resourcefulness metrics)

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
