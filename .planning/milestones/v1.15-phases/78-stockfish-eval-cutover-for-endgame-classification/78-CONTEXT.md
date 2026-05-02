# Phase 78: Stockfish-Eval Cutover for Endgame Classification — Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the `material_imbalance + 4-ply persistence` proxy in `app/repositories/endgame_repository.py` with depth-15 Stockfish eval stored in the existing `eval_cp` / `eval_mate` columns on `game_positions`. Bake Stockfish into the backend image, expose an async-friendly engine wrapper, backfill historical span-entry rows (dev → benchmark → prod, all from operator's local machine before deploy), evaluate new span entries at import time, refactor the three endgame queries to threshold on eval after a user-color sign flip, reshape `ix_gp_user_endgame_game` to keep queries index-only, and delete the proxy. Hard cutover, no fallback.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**16 requirements are locked.** See `78-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `78-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Stockfish binary baked into the backend Docker image (pinned version)
- Async-friendly engine wrapper module under `app/` exposing a single depth-15 evaluation API
- Backfill script under `scripts/` for span-entry NULL-eval rows (benchmark first, then prod)
- Import-path integration that evaluates new span entries when lichess `%eval` did not already populate them
- Refactor of the three endgame repository queries to threshold on `eval_cp` / `eval_mate` instead of the material proxy
- Deletion of `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, and the contiguity / persistence patterns from the codebase
- Alembic migration that reshapes `ix_gp_user_endgame_game` to keep the rewritten queries index-only
- Post-backfill `/conv-recov-validation` re-run on benchmark + operator UI smoke check on prod

**Out of scope (from SPEC.md):**
- Re-evaluating positions that already have a lichess `%eval` annotation
- Adding new columns to `game_positions`
- Tuning the ±100 cp threshold or experimenting with per-class thresholds
- Removing or deprecating the `material_imbalance` column
- Eval coverage outside endgame span entries
- Tactical filters or per-ply eval timeline data
- Classifier validation replication at scale (deferred to SEED-002 / SEED-006)
- A reversible cutover, dual-writing both proxies, or feature-flagging the new classifier

### SPEC drift to surface during planning

**FILL-02 hash-dedup requirement should be relaxed.** SPEC says the backfill "dedupes evaluations by `full_hash` so identical positions are not re-evaluated." Operator decision during discuss: skip the cross-row hash cache. Endgame span-entry positions are effectively unique across games (each game arrives at its endgame through a distinct path), so cross-row cache hits are astronomically rare and the dedup lookup costs more than re-evaluating. Keep row-level idempotency only: skip rows where `eval_cp` OR `eval_mate` is already populated (this still satisfies FILL-04's "lichess values never overwritten"). Planner should ack this drift in PLAN.md or update SPEC.md FILL-02 wording.

</spec_lock>

<decisions>
## Implementation Decisions

### Engine wrapper concurrency

- **D-01 — Single shared UCI process per backend worker, asyncio.Lock serialization.** The wrapper holds one long-lived `chess.engine.popen_uci()` process per Python process. An `asyncio.Lock` serializes `evaluate()` calls so concurrent imports queue cleanly. Backfill (separate process) holds its own engine. Matches ENG-01 literally and keeps memory predictable on a 7.6 GB swap-bound box.
- **D-02 — Engine lifecycle in FastAPI lifespan handler.** Engine starts in `app/main.py` lifespan startup, terminates on shutdown. Engine is ready before first request, gracefully cleaned up on container stop. Tests pass `Stockfish` on PATH; fixture starts/stops the engine per test session, not per test.
- **D-03 — Stockfish UCI options: `Hash=64 MB`, `Threads=1`.** Configured inside the wrapper module (single source of truth per ENG-03). Modest RAM footprint, avoids stealing CPU from uvicorn workers, comfortable depth-15 wall-clock (~50–100 ms typical endgame position).
- **D-04 — Wrapper API: `async def evaluate(board: chess.Board) -> tuple[int | None, int | None]` returning `(eval_cp, eval_mate)`.** White-perspective sign convention matching `app/services/zobrist.py:170-220`. Mate scores return `eval_mate` non-NULL, `eval_cp` NULL. The wrapper does NOT flip signs by user color — sign flip happens at read time inside the endgame queries.
- **D-05 — Defensive per-eval timeout.** Wrap each `evaluate()` in `asyncio.wait_for(..., timeout=2.0)`. Depth 15 is typically <100 ms but a wedged UCI process is unbounded. On timeout, restart the engine before the next eval (engine state may be in a bad state).

### Stockfish install & version pin

- **D-06 — Pinned official Stockfish Linux binary in the backend Dockerfile (Claude's discretion).** apt's `stockfish` package is too stale; building from source is overkill. Download the official `stockfish-ubuntu-x86-64-avx2` binary from `github.com/official-stockfish/Stockfish/releases` at a pinned tag (e.g. `sf_17`), verify by checksum, install to `/usr/local/bin/stockfish`. Version is locked alongside the wrapper so eval results are reproducible across deploys. Wrapper reads engine path from env var with a sensible default; `STOCKFISH_PATH=/usr/local/bin/stockfish` in the Docker image. Local dev installs Stockfish via `apt` (or homebrew on macOS) and exports `STOCKFISH_PATH` if needed; runbook documents this prerequisite.

### Backfill execution & batching

- **D-07 — Backfill runs from operator's local machine in three rounds: dev → benchmark → prod (in that order, before phase deploy).**
  - Round 1 (dev DB at `localhost:5432`): correctness check on a tiny seeded dataset.
  - Round 2 (benchmark DB at `localhost:5433`): full benchmark backfill, then `/conv-recov-validation` re-run, operator sign-off (VAL-01 hard gate per FILL-03).
  - Round 3 (prod DB via `bin/prod_db_tunnel.sh` → `localhost:15432`): full prod backfill **before** phase merge + deploy. At cutover time, prod's eval columns are already populated; the new code reads ready data with no broken-classification window.
  - Stockfish runs locally for all three rounds (binary installed on operator's host). Wrapper module is the single source of engine config (ENG-03).
- **D-08 — Script CLI: `--db {dev|benchmark|prod}` (or env-var-driven DB target), `--user-id <int>` (optional), `--dry-run` (count without writing), `--limit <int>` (cap rows for testing).** Per-user filter enables targeted eval runs (e.g. for one test account on prod). Default = all users.
- **D-09 — Sequential, single engine, COMMIT every 100 evals.** One engine, one row at a time. Resume = `SELECT WHERE eval_cp IS NULL AND eval_mate IS NULL` over span-entry rows; previously-committed rows are naturally skipped on rerun. ~70 ms/eval × 100 = ~7s per batch → progress visible at small granularity. Avoids the `asyncio.gather` parallel-engines complication and respects CLAUDE.md's "no asyncio.gather on same AsyncSession".
- **D-10 — No cross-row hash dedup.** See SPEC drift note above. Row-level idempotency only.

### Import-path failure handling

- **D-11 — On engine error or timeout during import-time eval: skip the row (leave `eval_cp` / `eval_mate` NULL), capture exception to Sentry with context (`game_id`, `ply`, `endgame_class`), continue importing the rest of the game and job.** The endgame queries already tolerate NULL-eval rows (they fall out of conv/recov classification by being neither ≥100 nor ≤-100, defaulting to parity). A future backfill pass can repair gaps. Hard-failing the import for a transient engine hiccup is a worse trade than tolerating sparse NULLs.

### Index INCLUDE shape (REFAC-04)

- **D-12 — `ix_gp_user_endgame_game` migrated to `INCLUDE(eval_cp, eval_mate)`.** Drops `material_imbalance` from INCLUDE — the conv/recov path no longer reads it (REFAC-05 keeps the column itself in the table, just stops carrying it on this index). Smallest viable INCLUDE; confirms index-only scans on the rewritten queries via `EXPLAIN (ANALYZE, BUFFERS)` showing Heap Fetches near zero. Planner should grep for any other consumer of this index path and bump `INCLUDE` only if a real query depends on it.

### Claude's Discretion

- Stockfish install method (D-06) was not user-selected; Claude chose pinned official binary in the Dockerfile after the user skipped it from the gray-areas multiselect.
- Defensive per-eval timeout value (D-05): 2 seconds is a defensive default — planner can revise after timing instrumentation if depth 15 reliably finishes in <500 ms on representative positions.
- Wrapper API exact return type (D-04): tuple chosen for symmetry with existing `eval_cp` / `eval_mate` column pair; planner can switch to a small dataclass if the wrapper ends up needing to surface metadata (depth reached, principal variation, etc.) during validation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements (locked)
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md` — Locked requirements, boundaries, acceptance criteria. MUST read before planning.
- `.planning/REQUIREMENTS.md` — v1.15 milestone requirements (ENG / FILL / IMP / REFAC / VAL groups + traceability matrix).
- `.planning/ROADMAP.md` — Phase 78 entry, milestone scope.

### Validation report (the source signal)
- `reports/conv-recov-validation-2026-05-02.md` — Validation report that opened v1.15. Documents the ~81.5% proxy/Stockfish agreement on the populated subset and the per-class shortfalls (queen, pawnless). VAL-01 references this report and produces a sibling `conv-recov-validation-2026-05-XX.md` after benchmark backfill.

### Code contracts the implementation must respect
- `app/repositories/endgame_repository.py` — The three queries to refactor: `query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_endgame_elo_timeline_rows`. Constants to delete: `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`. Index-only-scan comments at `:177` and `:302`.
- `app/services/zobrist.py:170-220` — Existing white-perspective sign convention for `eval_cp` / `eval_mate` from lichess `%eval` ingest. Wrapper output MUST match this convention byte-for-byte.
- `app/models/game_position.py:27` — `ix_gp_user_endgame_game` index definition; the Alembic migration in REFAC-04 reshapes its `INCLUDE` clause.
- `app/services/import_service.py` — Background async import orchestrator (`asyncio.create_task`, `_BATCH_SIZE = 10`); IMP-01 hooks the engine call into this path.
- `scripts/reclassify_positions.py` — Reference pattern for a resumable script that replays SAN; the new backfill script borrows its CLI shape and resume strategy.

### Operational
- `CLAUDE.md` — async-only stack, no `requests` / `berserk`, no `asyncio.gather` on same `AsyncSession`, prod is 4 vCPU / 7.6 GB RAM + 2 GB swap, prod runbook patterns.
- `bin/prod_db_tunnel.sh` — SSH tunnel for prod DB on `localhost:15432`; required for D-07 round 3.
- `Dockerfile` — Backend image; Stockfish install + version pin lands here per D-06.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/reclassify_positions.py`**: Resumable PGN-replay script with `--all` / `--user-id` / `--yes` CLI, COMMIT batching, prod-runbook docstring (`docker compose exec backend /app/.venv/bin/python ...`). The new backfill script copies this skeleton and swaps the per-ply replay for span-entry-only evaluation. CLI shape is the operator's existing muscle memory.
- **`app/services/zobrist.py:170-220`**: PGN replay + `eval_cp` / `eval_mate` clamping (`EVAL_CP_MAX_ABS`, `EVAL_MATE_MAX_ABS`) for SMALLINT-overflow defense. The new engine path can reuse the same clamps when writing wrapper output to the DB — keeps wire format consistent.
- **`python-chess`'s `chess.engine.popen_uci()`**: Native async API, already part of the stack (no new dependency). Returns an engine handle with `analyse(board, chess.engine.Limit(depth=15))` — the exact API D-04 wraps.

### Established Patterns
- **Pre-push classification + ply-numbered iteration** (`zobrist.py`): the canonical replay loop. New code can call the wrapper at the same point classification happens for span-entry rows.
- **Sentry context tagging on import errors**: `sentry_sdk.set_context()` + `sentry_sdk.set_tag()` (CLAUDE.md). D-11 follows this pattern: `set_context("eval", {"game_id": ..., "ply": ...})` then `capture_exception()`.
- **Prod script invocation**: `docker compose exec backend /app/.venv/bin/python scripts/...` (per `reclassify_positions.py` docstring). For backfill, this is the in-server fallback if local-machine round-3 backfill is impractical (e.g. tunnel speed). Default plan is local-machine per D-07.

### Integration Points
- **`app/main.py` lifespan handler** — D-02 hooks engine startup/shutdown here.
- **`app/services/zobrist.py` per-ply replay** — IMP-01 inserts the engine call after `endgame_class` is computed (line ~203). Only span-entry rows of each `(game_id, endgame_class)` group call `evaluate()`; non-span-entry plies skip the engine entirely.
- **`app/repositories/endgame_repository.py`** — REFAC-01..03 rewrites the three queries to read `eval_cp` / `eval_mate` at `MIN(ply)` of each `(user_id, game_id, endgame_class)` group with `count(ply) ≥ ENDGAME_PLY_THRESHOLD`. The user-color sign flip stays at read time (REFAC-02).
- **`alembic/versions/`** — A new revision drops + recreates `ix_gp_user_endgame_game` with the new `INCLUDE` shape (D-12).

</code_context>

<specifics>
## Specific Ideas

- **Cutover ordering is operator-specific:** the user wants prod backfilled BEFORE phase merge + deploy, so the deployed code reads ready eval data with zero broken-classification window. Plan must order tasks: implement → local dev test → benchmark backfill + VAL-01 → operator sign-off → prod backfill from local → merge + deploy → live UI smoke check (VAL-02).
- **Stockfish on operator's local host:** Required for rounds 1, 2, 3 of D-07. Documented as a setup prereq in the runbook. macOS: `brew install stockfish`; Linux: `apt install stockfish` (acceptable locally — version drift between local and Docker image won't change classification because the column-write side and the column-read side both read the same DB column; the only consumer of "same engine version" is reproducibility of the *backfill* itself, and a single operator running a single backfill round per DB satisfies that).
- **Per-user backfill (`--user-id`):** Operator wants this for targeted runs. Useful for test accounts during VAL-02 smoke check, and as an escape hatch if a single user's data lands in a weird state post-deploy.

</specifics>

<deferred>
## Deferred Ideas

- **Backfill progress reporting / ETA dashboard** — current plan logs at COMMIT boundaries; a richer progress bar / ETA is nice-to-have, not blocking. Plan can include lightweight `tqdm` or simple log-line counters.
- **Wrapper return-type richness** — if VAL-01 surfaces edge cases needing depth/PV metadata, the tuple in D-04 can grow into a dataclass in a follow-up. Not part of this phase.
- **Per-class threshold tuning, parity validation, rating-stratified offset analysis** — explicitly out of scope per SPEC.md; deferred to SEED-002 / SEED-006 (gated on full benchmark ingest).
- **Eval coverage for opening / middlegame positions** — out of scope; SEED-010 Library milestone.
- **Bumping `INCLUDE` of `ix_gp_user_endgame_game` for non-conv/recov consumers** — only do this if the planner actually finds another query that walks this index path and projects more columns. Don't add columns speculatively.

</deferred>

---

*Phase: 78-stockfish-eval-cutover-for-endgame-classification*
*Context gathered: 2026-05-02*
