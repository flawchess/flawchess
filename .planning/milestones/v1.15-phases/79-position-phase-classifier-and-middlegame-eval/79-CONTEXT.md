# Phase 79: Position-phase classifier and middlegame eval — Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a per-position `phase` SmallInteger column (0=opening, 1=middlegame, 2=endgame) to `game_positions`, computed by a Python port of lichess [Divider.scala](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) using the existing `piece_count`, `backrank_sparse`, and `mixedness` columns. Extend Phase 78's import-time eval pass and `scripts/backfill_eval.py` so the **middlegame entry** position (`MIN(ply)` of `phase=1` rows per game) is also evaluated with Stockfish at depth 15, with results written into the existing `eval_cp` / `eval_mate` columns. Run the combined Phase 78 + Phase 79 backfill against benchmark first, then prod, then merge the two phases together to `main` and deploy.

This phase ships **data plumbing only**. No frontend, no middlegame metrics, no aggregations on `phase=1` data. The endgame repository queries are NOT moved to read `phase` instead of `endgame_class` — they keep their existing key. Phase 79 also closes out Phase 78's deferred operational steps (FILL-03, FILL-04, VAL-01, VAL-02, deploy) inside its scope.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**13 requirements are locked.** See `79-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `79-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- New `phase` SmallInteger column on `game_positions` (Alembic migration, nullable; backfill closes it out)
- Python port of lichess Divider.scala `isEndGame` / `isMidGame` predicates inside `app/services/position_classifier.py`
- `classify_position` returning a `phase: Literal[0, 1, 2]` field (no recomputation of inputs)
- Import-path population of `phase` for every inserted row (intermediate plies + final position)
- Import-time middlegame entry Stockfish eval (one extra engine call per typical game)
- Backfill script extension: phase column population + middlegame entry NULL-eval backfill
- Combined three-round operational rollout (dev smoke → benchmark + VAL-01 → prod) using the Phase 78 runbook
- Combined merge of Phase 78 + Phase 79 PRs to `main` and a single `bin/deploy.sh` deploy
- Closeout of the Phase 78 deferred operational steps (FILL-03, FILL-04, VAL-01, VAL-02) inside this phase
- Divider parity test fixture in `tests/test_position_classifier.py`

**Out of scope (from SPEC.md):**
- Refactoring endgame repository queries to read `phase` instead of `endgame_class`
- Middlegame conv/parity/recov metrics or any new aggregations on `phase=1` data
- Frontend display of `phase` in any panel, gauge, chart, or debug view
- Deprecating or removing `piece_count`, `backrank_sparse`, `mixedness`, `material_count`, `material_signature`, `material_imbalance`, or `endgame_class`
- Re-evaluating any position that already has a populated `eval_cp` or `eval_mate` (lichess `%eval` preservation)
- Tuning Divider thresholds (port lichess defaults verbatim: 10 / 10 / 6)
- Eval coverage outside endgame span entries and the single middlegame entry per game
- Adding new schema columns beyond `phase` (`eval_cp` / `eval_mate` reused as-is)
- A reversible cutover, dual-writing both classifiers, or feature-flagging the new `phase` column

</spec_lock>

<decisions>
## Implementation Decisions

### Phase column backfill execution

- **D-79-01 — Batched SQL `CASE` UPDATE inside `scripts/backfill_eval.py`, no Python row loop.** The phase value is a pure function of three columns already on `game_positions` (`piece_count`, `backrank_sparse`, `mixedness`), so the backfill is a SQL one-liner and does not need PGN replay. Use a single `UPDATE game_positions SET phase = CASE WHEN piece_count <= {ENDGAME_PIECE_COUNT_THRESHOLD} THEN 2 WHEN (piece_count <= {MIDGAME_MAJORS_AND_MINORS_THRESHOLD} OR backrank_sparse OR mixedness >= {MIDGAME_MIXEDNESS_THRESHOLD}) THEN 1 ELSE 0 END WHERE phase IS NULL AND id BETWEEN :lo AND :hi` parameterised over `id` ranges of 10 000 rows; COMMIT per chunk for resumability and lock-friendliness on prod's ~5M+ rows. Idempotent on re-run via `WHERE phase IS NULL`. Threshold constants are interpolated from the Python module so SQL and Python share one source of truth.
- **D-79-02 — Phase backfill runs FIRST inside the script, before any engine work.** Order inside `run_backfill`: (1) phase-column UPDATE pass (cheap, ~SQL-bound), (2) endgame span-entry eval pass (existing Phase 78 work), (3) middlegame entry eval pass (new). Order matters because step 3 needs `phase=1` rows populated by step 1; it does not need step 2 to have run. Each pass is independently idempotent on re-run.

### Middlegame entry row enqueueing

- **D-79-03 — Sibling `_build_middlegame_entry_stmt` function, not a UNION ALL extension of `_build_span_entry_stmt`.** The two queries have different shapes — span-entry is keyed on `(user_id, game_id, endgame_class, island_id) → MIN(ply)`; middlegame entry is keyed on `(game_id, phase=1) → MIN(ply)` with no class and no island concept (per SPEC: at most one middlegame entry per game; later `phase=1` stretches after an endgame are NOT re-evaluated). Both stmts return the same `(id, game_id, ply, pgn)` row shape so the existing eval+write loop in `run_backfill` processes both row sets uniformly. The middlegame stmt selects `WHERE phase = 1 AND eval_cp IS NULL AND eval_mate IS NULL AND ply = (SELECT MIN(ply) FROM game_positions gp2 WHERE gp2.game_id = game_positions.game_id AND gp2.phase = 1)`, with the same optional `--user-id` filter and `--limit` cap.
- **D-79-04 — Same per-row Sentry skip-and-continue behaviour as Phase 78.** Reuse the `skipped_no_board` (PGN replay failure) and `skipped_engine_err` (engine returned `(None, None)`) counters and log lines. Bounded Sentry context (no PGN, no FEN, no user_id — same T-78-13/T-78-18 scope) plus a `set_tag("source", "backfill")` and `set_tag("eval_kind", "middlegame_entry")` so the two row sets stay distinguishable in Sentry.

### Backfill command shape

- **D-79-05 — Single `--db {dev|benchmark|prod}` invocation per round; no `--phase-only` flag.** One operator command per round runs the three passes sequentially, same UX as Phase 78. Phase backfill is cheap (SQL-bound, ~minutes), eval passes are expensive (~hours); they are naturally sequenced. The existing `--user-id`, `--dry-run`, `--limit` flags carry over unchanged. `--dry-run` reports counts for all three passes (rows with `phase IS NULL`, endgame span entries with NULL eval, middlegame entry rows with NULL eval) and exits without starting the engine — same as Phase 78.

### Import-path integration

- **D-79-06 — `phase` is computed inside `classify_position` from already-derived inputs, no second board scan.** The new `phase: Literal[0, 1, 2]` field is added to `PositionClassification` (frozen dataclass) and is filled by inline logic at the bottom of `classify_position`, reading `piece_count`, `backrank_sparse`, `mixedness` that the function has already computed. `is_endgame` is checked before `is_middlegame` so `piece_count <= 6` always wins → guarantees PHASE-INV-01 (`phase = 2 ⟺ endgame_class IS NOT NULL`) by construction.
- **D-79-07 — `PlyData` TypedDict gains a `phase: int` key; both ply loops in `zobrist.py` populate it.** The intermediate-ply loop (`for ply, node in enumerate(nodes)`) and the final-position append both copy `classification.phase` into the new `phase` field. The bulk-insert payload in `import_service.py` adds `"phase": ply_data["phase"]` to the row dict. Every imported row has a non-NULL phase from import time forward.
- **D-79-08 — Middlegame entry import-time eval is a single extra `evaluate()` call per game, sequenced inside the existing eval pass loop.** Reuse the existing `for g_id, pgn_text, plies_list in game_eval_data:` loop; before the per-class endgame inner loop, find `MIN(ply) where phase == 1` from `plies_list`, and if that ply's `eval_cp` and `eval_mate` are both NULL, call `engine_service.evaluate(_board_at_ply(pgn_text, that_ply))` and `UPDATE game_positions ... WHERE game_id = g_id AND ply = that_ply`. Skip the call when no `phase=1` ply exists in the game (game never left opening). T-78-17 lichess `%eval` preservation guard is the same `eval_cp is not None or eval_mate is not None` check used for endgame span entries.

### Combined Phase 78 + Phase 79 ship mechanics

- **D-79-09 — Phase 79 branch is rebased onto the Phase 78 branch; one combined PR `→ main`.** Phase 79 work branches from `gsd/phase-78-stockfish-eval-cutover-for-endgame-classification` so its history contains all Phase 78 commits as base. After Phase 79 code is complete, the operator opens a single combined PR `gsd/phase-79-position-phase-classifier-and-middlegame-eval → main` that bundles both phases. Squash-merge yields one commit on main; both phase branches close after merge.
- **D-79-10 — Three-round combined backfill runs from the operator's local machine, in the same shape as Phase 78 D-07.** Round 1 (dev DB at `localhost:5432`, on user 28 again) → Round 2 (benchmark DB at `localhost:5433`, full backfill, then `/conv-recov-validation` re-run as VAL-01 hard gate ≥ 99% agreement) → Round 3 (prod DB via `bin/prod_db_tunnel.sh` on `localhost:15432`, full backfill). Every round runs the combined script (phase column + endgame eval + middlegame eval) in one invocation. After Round 3 succeeds, the combined PR is merged to `main` and deployed via `bin/deploy.sh`. VAL-02 live-UI smoke check on 3–5 representative test users runs post-deploy.
- **D-79-11 — Alembic migration adds `phase SmallInteger NULL` with no embedded backfill.** The migration body is `op.add_column(...)` only. Backfill happens via `scripts/backfill_eval.py`, run from the operator's local machine in three rounds. Down-migration is `op.drop_column('game_positions', 'phase')` — clean and reversible. Migration is applied during deploy by `deploy/entrypoint.sh` for prod; operator applies it manually on benchmark via `BACKFILL_BENCHMARK_DB_URL=... uv run alembic upgrade head` (or equivalent) before running the benchmark backfill.

### Validation

- **D-79-12 — Divider parity test fixture lives in `tests/test_position_classifier.py`, expected values sourced from Divider.scala (NOT from the Python implementation under test).** ≥ 10 hand-curated assertions covering the three phases plus boundary conditions: starting position (phase=0), KQR-vs-KQR (phase=2 because `piece_count = 4 ≤ 6`), KR-vs-KR (phase=2), KQ-vs-KQ + 8 pawns each (phase=2 because `piece_count = 2`), `piece_count = 11` mid-development (phase=0 unless backrank-sparse / mixedness fires), `piece_count = 10` (phase=1 by majors-and-minors threshold), backrank-sparse position with high piece_count (phase=1), high-mixedness position with high piece_count (phase=1), `mixedness = 9` boundary (NOT phase=1 unless other criteria fire), `mixedness = 10` boundary (phase=1).
- **D-79-13 — PHASE-INV-01 SQL invariant check is run after Round 2 (benchmark) and after Round 3 (prod), not gated only at the end.** `SELECT COUNT(*) FROM game_positions WHERE (phase = 2) <> (endgame_class IS NOT NULL)` must return 0 on both DBs. Run as a one-liner via `mcp__flawchess-benchmark-db__query` and `mcp__flawchess-prod-db__query` (read-only) immediately after each round completes — this catches divergence before VAL-01 / deploy if it occurred.

### Claude's Discretion

- The empty multi-select response from the user during discuss-phase was treated as "use your recommendations on all four areas" per auto mode policy; D-79-01, D-79-03, D-79-05, and D-79-09 reflect Claude's recommended option in each case. Planner can revise any of them with rationale; the SPEC requirements (13 reqs) are the binding contract, not these specific implementation choices.
- D-79-01 chunk size of 10 000 rows is a defensive default; the planner can tune up or down based on `EXPLAIN (ANALYZE)` of the UPDATE on benchmark (~1.5M rows) or prod (~5M+ rows). Smaller chunks → tighter lock duration but more transaction overhead; bigger chunks → faster but higher lock contention.
- D-79-08 chooses the "single contiguous middlegame entry per game" interpretation per SPEC; if a game re-enters `phase=1` after a brief endgame, that re-entry is intentionally NOT re-evaluated (mirrors lichess Divider's single `Division(midGame, endGame)` transition return). Reconsider only if a future analytical use case actually needs per-stretch middlegame eval.
- D-79-13 names the SQL invariant as a manual operator check; the planner can promote it into an automated post-backfill assertion inside `run_backfill` (raise on count > 0) if it wants harder enforcement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements (locked)
- `.planning/milestones/v1.15-phases/79-position-phase-classifier-and-middlegame-eval/79-SPEC.md` — Locked requirements (13), boundaries, acceptance criteria. MUST read before planning.
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md` — Phase 78 SPEC; T-78-17 lichess preservation rule and FILL-02 row-level idempotency rule both apply unchanged here.
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md` — Phase 78 implementation decisions; D-04 (white-perspective sign convention), D-09 (COMMIT-every-100), D-10 (row-level idempotency), D-11 (Sentry skip-and-continue) carry over to Phase 79.
- `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-06-SUMMARY.md` — Phase 78 cutover plan ran with slimmed scope (dev-DB smoke for user 28 only); the deferred operational items (Round 2, Round 3, VAL-01, VAL-02, deploy) are folded into Phase 79.
- `.planning/REQUIREMENTS.md` — v1.15 milestone requirements (ENG / FILL / IMP / REFAC / VAL groups + traceability matrix).
- `.planning/ROADMAP.md` — Phase 79 entry, milestone scope.
- `.planning/STATE.md` — current-state snapshot; Phase 78 code-complete + 78 ops deferred to combined run.

### External algorithm spec
- `https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala` — source-of-truth for `isEndGame` / `isMidGame` predicates. Port verbatim with the lichess default thresholds (10 / 10 / 6); no FlawChess-specific tuning.

### Code contracts the implementation must respect
- `app/services/position_classifier.py` — `PositionClassification` dataclass + `classify_position()` function; CLASS-01 / CLASS-02 add the `phase` field and `is_endgame` / `is_middlegame` predicates here. Existing constant `ENDGAME_PIECE_COUNT_THRESHOLD` is reused.
- `app/services/zobrist.py:32-66` — `PlyData` TypedDict; SCHEMA-02 adds the `phase: int` key. Lines `:170-256` — both ply loops (intermediate + final) populate `phase` from `classification.phase`.
- `app/services/import_service.py:497-522` — Bulk-insert payload; SCHEMA-02 adds `"phase": ply_data["phase"]`. Lines `:528-615` — Phase 78 import-time eval pass; PHASE-IMP-01 extends this loop to also evaluate the middlegame entry.
- `app/models/game_position.py:75-99` — Existing position metadata columns (`material_*`, `piece_count`, `backrank_sparse`, `mixedness`, `eval_cp`, `eval_mate`, `endgame_class`). SCHEMA-01 adds a sibling `phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` column following the same pattern.
- `scripts/backfill_eval.py` — Phase 78 backfill driver; PHASE-FILL-01 (phase column UPDATE pass) + PHASE-FILL-02 (middlegame entry eval pass) both extend this script. `_build_span_entry_stmt` (lines 136-231) is left intact; a sibling `_build_middlegame_entry_stmt` is added; `run_backfill` (lines 234-362) gains a phase-column-UPDATE pass before the eval phase, and a second eval pass over the middlegame entry rows.
- `app/services/engine.py` — async UCI wrapper (Phase 78 ENG-02). Reused unchanged. Same depth 15, same white-perspective sign convention, same `evaluate(board) -> tuple[int | None, int | None]` API, same lifespan handler.
- `app/repositories/endgame_repository.py` — Three queries already on `eval_cp` / `eval_mate` after Phase 78 REFAC-01..03. NOT touched in Phase 79 (out-of-scope per SPEC).
- `tests/test_position_classifier.py` — Existing test module for the three Divider input metrics; PHASE-VAL-01 adds a `TestPhaseClassification` class in the same file.
- `alembic/versions/` — A new revision adds the `phase` SmallInteger column. No data backfill embedded; migration body is `op.add_column` + `op.drop_column` only.

### Operational
- `CLAUDE.md` — async-only stack, no `requests` / `berserk`, no `asyncio.gather` on same `AsyncSession`, prod is 4 vCPU / 7.6 GB RAM + 2 GB swap; commit-message conventions; no `--no-verify` on commits.
- `bin/prod_db_tunnel.sh` — SSH tunnel for prod DB on `localhost:15432`; required for D-79-10 round 3.
- `bin/deploy.sh` — CI-driven deploy; runs after the combined PR is merged to `main`.
- `deploy/entrypoint.sh` — Runs `alembic upgrade head` automatically on backend container startup; the new `phase` column migration ships through this path on prod.
- `reports/conv-recov-validation-2026-05-02.md` — Pre-Phase-78 baseline validation report (~81.5% agreement); VAL-01 produces a sibling `reports/conv-recov-validation-2026-05-XX.md` after Round 2 with ≥ 99% agreement on the populated subset.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app/services/engine.py`** (Phase 78 ENG-02) — single shared UCI process, depth 15, async-friendly `evaluate()` API, asyncio.Lock-serialised, defensive 2 s timeout, lifespan-bound in `app/main.py`. Reused unchanged for the new middlegame eval call.
- **`scripts/backfill_eval.py` `_board_at_ply`** (lines 112-133) — PGN replay to a target ply (pre-push), returns `chess.Board | None`. Reused verbatim for the middlegame entry eval pass.
- **`app/services/position_classifier.py` `_compute_piece_count`, `_compute_backrank_sparse`, `_compute_mixedness`** — Divider's three input metrics already exist. Phase 79 only adds the phase classification step that consumes them. `ENDGAME_PIECE_COUNT_THRESHOLD = 6` is already defined and reused.
- **`app/services/zobrist.py` `EVAL_CP_MAX_ABS` / `EVAL_MATE_MAX_ABS` clamping** (lines 111-112) — defensive SMALLINT-overflow clamps for ingest-side `%eval` data. Engine outputs from the wrapper module are already clamped inside the wrapper (Phase 78); middlegame entry eval inherits that same clamp without any code change.

### Established Patterns
- **Pre-push classification + ply-numbered iteration** (`zobrist.py`) — canonical replay loop. New `phase` field is computed inside `classify_position` and copied into `PlyData` at the same point as `piece_count` / `backrank_sparse` / `mixedness`.
- **Sentry context tagging on engine errors** (`backfill_eval.py:308-320`, `import_service.py:583-593`) — `set_context("eval", {...})` + `set_tag("source", ...)` + `capture_message(level="warning")`. Middlegame eval reuses this with an extra `set_tag("eval_kind", "middlegame_entry")` so the two backfill row sets stay distinguishable.
- **Three-round operator runbook** (`78-CONTEXT.md` D-07) — dev → benchmark + VAL-01 → prod, all from local machine, before phase merge. Phase 79 reuses this verbatim and folds in Phase 78's deferred ops.
- **COMMIT-every-N batching with `WHERE` resume predicate** (`backfill_eval.py:332-340`, D-09 / D-10) — same pattern applied to the new phase-column UPDATE (chunked by `id` range, COMMIT per chunk, `WHERE phase IS NULL` predicate for resumability) and the new middlegame eval pass (same `WHERE eval_cp IS NULL AND eval_mate IS NULL` predicate, COMMIT every 100 evals).

### Integration Points
- **`PositionClassification` dataclass** (`position_classifier.py:86-99`) — gains a `phase: Literal[0, 1, 2]` field; `classify_position` returns the eight fields (existing seven + phase). Frozen dataclass invariants preserved.
- **`PlyData` TypedDict** (`zobrist.py:32-54`) — gains `phase: int`. Both producers (intermediate ply loop, final-position append) populate it from `classification.phase`.
- **`game_position.py` model** (line 88, after `mixedness`) — new `phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` column. Comment notes that nullability is transient: import-time code always populates it; nullability exists only for the migration window before the backfill closes it out.
- **`import_service.py` bulk-insert payload** (lines 502-521) — `"phase": ply_data["phase"]` added.
- **`import_service.py` eval pass** (lines 528-615) — extended to evaluate the middlegame entry row in addition to per-class endgame span entries; same per-row Sentry skip-and-continue behaviour.
- **`scripts/backfill_eval.py` `run_backfill`** (lines 234-362) — gains a phase-column UPDATE pass before the eval phase, and a second eval pass over middlegame entry rows from the new sibling stmt.
- **Alembic migration** under `alembic/versions/` — adds `phase` column; no embedded backfill body.
- **`tests/test_position_classifier.py`** — gains a `TestPhaseClassification` class with ≥ 10 Divider-sourced assertions.

</code_context>

<specifics>
## Specific Ideas

- **Single source of truth for thresholds:** The SQL CASE expression in `scripts/backfill_eval.py` interpolates the Python-defined constants (`MIDGAME_MAJORS_AND_MINORS_THRESHOLD = 10`, `MIDGAME_MIXEDNESS_THRESHOLD = 10`, `ENDGAME_PIECE_COUNT_THRESHOLD = 6`) via f-string when building the SQL, so changing a threshold in `position_classifier.py` automatically propagates to the backfill. PHASE-VAL-01 unit tests catch divergence on the Python side; PHASE-INV-01 SQL invariant catches divergence on the SQL side.
- **Operator UX parity with Phase 78:** Same `--db {dev|benchmark|prod}` CLI, same `--user-id` filter, same `--dry-run` flag, same `--limit` cap. The only operator-visible delta is that `--dry-run` now reports three counts instead of one (phase-NULL rows + endgame span-entry NULL-eval rows + middlegame-entry NULL-eval rows).
- **VAL-01 gate is on the COMBINED conv/recov agreement, not on a separate middlegame metric.** Because the middlegame metric does not exist yet (no UI, no aggregation), there is nothing new to agree against. The benchmark `≥ 99%` agreement signal stays exactly the Phase 78 VAL-01 signal — the conv/recov proxy ↔ engine eval agreement on populated endgame span entries.
- **Phase 78 VAL-02 closes out inside Phase 79 VAL-03.** Operator inspects 3–5 representative users' Endgames pages post-deploy. No middlegame-specific UI smoke check exists because there is no middlegame UI yet.

</specifics>

<deferred>
## Deferred Ideas

- **Middlegame conversion / parity / recovery metrics.** The middlegame eval is *captured* in Phase 79 but not yet *displayed* or *aggregated*. UI work and metric design belong in a later milestone (likely a v1.16 candidate).
- **Frontend display of `phase`** in any panel, gauge, chart, or debug view. Not Phase 79's scope.
- **Refactor of endgame repository queries** to read `phase` instead of `endgame_class`. Phase 78 already cut over to eval-based thresholds; moving endgame analytics from `endgame_class` to `phase` is a separate exercise that needs its own evaluation (the `endgame_class` granularity buys per-class analytics that `phase` alone does not).
- **Per-ply middlegame eval timeline.** Phase 79 evaluates exactly one middlegame entry per game. A per-ply eval timeline through the middlegame would require ~30× the engine calls and is not motivated by any existing UI surface.
- **Tuning the Divider thresholds (10 / 10 / 6) or experimenting with FlawChess-specific phase boundaries.** Out of scope per SPEC; port the lichess defaults verbatim. Threshold tuning becomes interesting only if a downstream metric (middlegame conv/recov, opening-vs-middlegame transition stats) shows a calibration gap.
- **Cross-row hash dedup for engine cache hits.** Same Phase 78 D-10 stance: middlegame entries across games are effectively unique paths, so the cost of a cache lookup exceeds the cost of a re-eval at the rare collision rate.
- **Promoting the PHASE-INV-01 SQL invariant into an automated assertion in `run_backfill`.** Currently a manual operator check after each round; the planner can promote it if it wants harder enforcement.
- **Backfill ETA / progress bar.** Same Phase 78 deferred idea — current logging at COMMIT boundaries is enough for now.

</deferred>

---

*Phase: 79-position-phase-classifier-and-middlegame-eval*
*Context gathered: 2026-05-02*
