# Phase 247: Maia Stats on game_flaws (SEED-261108-zkp) - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Store Maia-3 statistics for every mistake and blunder in `game_flaws` (both players; 7.61M rows on prod
2026-11-08, of which 27.7k belong to guests), scored at the mover's rating at game time. Deliverables:

1. Schema: eight typed nullable columns on `game_flaws` plus a per-game completion stamp on `games`.
2. Go-forward scoring in the eval-apply path, next to the best-move pass.
3. Correct behaviour under flaw reclassification, whether or not the reclassifying path has Maia.
4. A deterministic, checkpointed, resumable, re-runnable backfill script that targets prod or the benchmark DB.
5. The full prod backfill, run to completion and coverage-verified, inside this phase.

This is the data base for blunder check's face-palm selection (SEED-261108-dk0), a later face-palm filter on the
Flaws tab, and a future data story. None of those consumers are built here.

</domain>

<decisions>
## Implementation Decisions

### Locked by SEED-261108-zkp (carried forward, not re-discussed)
- **D-01: Columns.** Typed, nullable, not JSONB (NULL = not scored): `maia_played_prob` REAL,
  `maia_played_rank` SMALLINT, `maia_best_prob` REAL, `maia_best_rank` SMALLINT, `maia_second_prob` REAL,
  `maia_second_rank` SMALLINT, `maia_top_prob` REAL, `maia_effective_moves` REAL (2^H, with H the Shannon entropy in
  bits of Maia's policy over all legal moves). Rank = 1 + the number of legal moves with strictly higher Maia
  probability. "Best" = `game_positions.best_move` at the flaw ply; "second" = Stockfish's second-best move at the
  flaw ply (seed: `missed_pv_lines[0].su`; the researcher must confirm that this field is the second-best root
  move). The columns are added nullable with no default (a metadata-only ALTER on 7.6M rows).
- **D-02: No `maia_elo` column** (owner decision). The Elo is derivable via `games`. Accepted cost: a retune of the
  chess.com-to-lichess conversion means a re-run.
- **D-03: Elo** comes from `pinned_elo_for_mover` (`app/services/best_move_candidates.py`), fed symmetrically as both
  `elo_self` and `elo_oppo`, for parity with the analysis-board Maia card.
- **D-04: One inference per flaw.** A full-policy helper next to `score_move` in `app/services/maia_engine.py`
  (reuses `mask_and_softmax`) returns everything D-01 needs from one forward pass.
- **D-05: Per-game completion stamp** on `games`, mirroring `best_moves_completed_at` and its `is_maia_available()`
  guardrail: never stamp unless a Maia session was actually loaded. Stamp games with zero flaws too, so the backfill
  selector terminates.
- **D-06: Exact positions only.** The backfill rebuilds positions by replaying `games.pgn`, never from
  `game_flaws.fen` (that is `board_fen()` only; guessed castling or en-passant rights skew the legal-move softmax).
- **D-07: Out of scope:** blunder-check selection, UI and thresholds (SEED-261108-dk0); the Flaws-tab filter UI;
  Maia WDL; full-policy or top-k storage; Elo-ladder curves; Maia on non-flaw moves.

### Re-analysis semantics
- **D-08: A Maia-loaded eval-apply re-scores every flaw** in the game on each apply (new and surviving plies alike)
  and stamps the game. One write path, never stale; the cost equals the go-forward cost.
- **D-09: Reclassification without Maia** keeps surviving values. This covers `scripts/backfill_flaws.py`,
  `scripts/opening_cache_repair.py`, and an eval-apply on a backend where `is_maia_available()` is False. Rules:
  - Surviving flaw plies keep their Maia columns, preserved by omission in the 4-way diff/upsert of
    `_classify_and_fill_oracle`, the same mechanism as `FLAW_BLOB_AND_TACTIC_COLUMNS`.
  - New flaw plies are inserted with the Maia columns NULL.
  - The game's Maia stamp is cleared (set NULL), so the re-runnable backfill re-scores the whole game, including any
    `maia_best_*` or `maia_second_*` values that went stale because Stockfish's best move changed.
  - Deleted flaw plies take their values with them (the row goes).

### Benchmark DB
- **D-10: The script is ready for the benchmark DB; it runs there later.** The backfill script takes a `--db prod|benchmark` target and
  is tested against both. This phase runs it on prod only. The benchmark run (5.48M flaws, 812k games, about 12 h on
  9 processes, local writes) happens when the data story needs it. The benchmark DB gets the columns through the
  normal migration (`bin/benchmark_db.sh start` applies Alembic).

### Straggler catch-up
- **D-11: The re-runnable script is the only catch-up path.** The backfill selects games with flaws and a NULL Maia stamp,
  so re-running it is idempotent and catches anything D-09 unstamped or a crash left behind. No new drain or lottery
  tier. `backfill_flaws.py` and `opening_cache_repair.py` print a one-line reminder to run the Maia backfill when they
  unstamped games.

### Completion
- **D-12: The phase is done only after the full prod backfill.** Order: (1) go-forward scoring ships to prod (the deploy itself is the
  owner's call, so the plan pauses there for a go-ahead); (2) the orchestrator runs the full backfill against prod over
  the tunnel (detached via setsid + Monitor, not in an executor subagent); (3) a final catch-up re-run; (4) coverage
  verification on prod: at least 99% of flaws in fully evaluated games carry `maia_played_prob`, and the NULL
  remainder is explained by bucket (unreplayable PGN, missing rating, and so on).

### Claude's Discretion
- **Edge cases (defaults the owner accepted without discussion):** guest flaws are scored like everyone else (go-forward
  covers them anyway; 27.7k rows is noise). A missing Stockfish best or second move leaves only that pair NULL, while the
  played, top and effective values are still written. When the flaw ply has no second legal move, `maia_second_*` stays NULL. A game with no
  usable rating falls back to `pinned_elo_for_mover`'s own chain; if no Elo results, its flaws stay NULL. An
  unreplayable PGN, or a replay that disagrees with the stored flaw, leaves the game's flaws NULL with a counted
  reason. In every case the game is still stamped, so the selector terminates.
- Stamp column name (suggested: `games.maia_flaws_completed_at`), migration shape, and whether the selector needs a
  partial index.
- Backfill internals: process count (8-10 on the 16-core box), batch and commit size, checkpoint format, ordering
  (recently active users first, then newer games first, kept deterministic), and how prod writes are batched over the tunnel.
- Go-forward wiring: where in `apply_full_eval` the scoring runs and how it reuses the in-memory boards.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source and consumer
- `.planning/seeds/SEED-261108-zkp-maia-stats-on-game-flaws.md`: locked decisions, measurements (65-78 ms per
  position single-threaded; scale by processes, not threads or batching), storage rationale, gotchas, breadcrumbs
- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`: the consumer; how the stored values get used (the face-palm
  test, top-move safety, X/X′/Y calibration in SQL)

### Eval-completion semantics
- `.planning/notes/eval-completion-columns.md`: what "analyzed by us" means across the completion columns; needed for the
  coverage-verification denominator

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/maia_engine.py`: `score_move(fen, elo, played_uci)` (line ~151) already computes the full policy and
  keeps one move; `is_maia_available()` (line ~131) is the guardrail; `start_maia`/`stop_maia` handle session lifecycle
  (a script must call them itself).
- `app/services/maia_encoding.py`: `mask_and_softmax`, `encode_board`.
- `app/services/best_move_candidates.py`: `pinned_elo_for_mover` (line ~79).
- `app/services/eval_apply.py`: `_mark_best_moves_completed` (line ~827) is the stamp-helper pattern to mirror;
  `_build_best_move_candidates` (line ~2152) is the session-discipline pattern to follow (rating metadata read in a
  short session that closes before any Maia inference; rows UPSERTed later in the apply's own late write session).
- `scripts/backfill_flaws.py`, `scripts/retag_flaws.py`: prior-art backfill and retag scripts over the prod tunnel
  (the 2026-10 prod retag wrote 4.76M rows in 3h17m).

### Established Patterns
- **4-way diff/upsert in `_classify_and_fill_oracle`** (`eval_apply.py` ~995, ~2949): surviving rows that weren't
  freshly blobbed omit the preserved column keys from the update dict, so the SET clause never touches them. The Maia
  columns join this preserve-by-omission set on no-Maia paths (D-09); on a Maia-loaded apply they are written fresh (D-08).
- **The Maia guardrail:** `_build_best_move_candidates` returns `[]` both for "Maia ran, zero rows" and for "Maia absent",
  so the stamp decision must come from `is_maia_available()`, never from a row count.
- **Typed columns on high-cardinality tables:** SMALLINT and REAL, no JSONB (avoids asyncpg writing JSON `null`
  instead of SQL NULL).

### Integration Points
- Callers of `_classify_and_fill_oracle`: `app/services/eval_apply.py:2949` (go-forward, D-08), `scripts/backfill_flaws.py:182`
  and `scripts/opening_cache_repair.py:2040` (D-09). The planner must find every apply path that reaches
  flaw classification (local drain, remote-worker submit, tier-4b) and confirm each one scores or unstamps.
- `game_flaws` model: `app/models/game_flaw.py`; `games` stamp: `app/models/game.py`.

</code_context>

<specifics>
## Specific Ideas

- Backfill sharding: use `md5(game_id) % num_shards`, never rank windows. Prod grows while the run is in progress (the
  benchmark-sharding lesson from the project memory).
- Long operator runs: Bash caps at 10 minutes, so launch with setsid nohup and watch with Monitor. Under Python 3.14 the log
  can look frozen (128 KiB buffer); watch DB progress (stamped-game count) instead. Commit any same-day report before a
  re-run.
- The coverage report breaks the NULL remainder down by reason (unreplayable, no Elo, Maia-absent unstamped, and so on).

</specifics>

<deferred>
## Deferred Ideas

- Benchmark-DB backfill run: deferred to the data-story phase (the script is ready, per D-10).
- Automatic catch-up drain tier: rejected for now (D-11); revisit only if unstamped games pile up in practice.

</deferred>

---

*Phase: 247-maia-stats-on-game-flaws*
*Context gathered: 2026-11-08*
