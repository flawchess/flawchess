# Phase 79: Position-phase classifier and middlegame eval - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 79-position-phase-classifier-and-middlegame-eval
**Areas discussed:** Phase column backfill strategy, Middlegame entry row selection, Backfill command shape, Combined PR / branch mechanics

---

## Phase column backfill strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pure SQL CASE UPDATE batched in chunks | No Python replay needed since `piece_count` / `backrank_sparse` / `mixedness` are already columns; chunks of 10k rows committed per batch keep lock duration tight on prod's ~5M+ rows. Idempotent on rerun via `WHERE phase IS NULL`. | ✓ |
| Python row loop reading rows and updating | Reuses the existing PGN-replay-style loop pattern but pulls every row into Python memory just to derive a value already computable in SQL — significantly slower and memory-pressured on prod. | |
| Single unbatched UPDATE | Fastest by raw throughput but holds a long row-lock on prod; risk of blocking app writes during deploy window. | |

**User's choice:** Empty multi-select response in auto mode → Claude's recommended option (batched SQL CASE UPDATE).
**Notes:** Threshold constants are interpolated from the Python `position_classifier.py` module via f-string when building the SQL, so SQL and Python share one source of truth for the 10 / 10 / 6 Divider thresholds. PHASE-INV-01 SQL invariant catches divergence post-backfill.

---

## Middlegame entry row selection

| Option | Description | Selected |
|--------|-------------|----------|
| Sibling `_build_middlegame_entry_stmt` + same eval+write loop | Two query builders with the same `(id, game_id, ply, pgn)` row shape; the existing eval+write loop processes both row sets uniformly. Cleaner test surface, easier to reason about each query independently. | ✓ |
| Extend `_build_span_entry_stmt` with UNION ALL of phase=1 MIN(ply) rows | One query yields both row sets in a single trip; conceptually unifies "rows to evaluate" but mixes two different keys (`endgame_class + island_id` vs `phase=1`) into one statement. | |

**User's choice:** Empty multi-select response in auto mode → Claude's recommended option (sibling function).
**Notes:** Middlegame entry has no class and no island concept — at most one middlegame entry per game per SPEC; later phase=1 stretches after an endgame are NOT re-evaluated (mirrors lichess Divider's single transition return). The two queries have different shapes; keeping them separate keeps each one readable.

---

## Backfill command shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single `--db {target}` invocation runs three passes sequentially | Phase column UPDATE → endgame eval pass → middlegame eval pass, all in one command per round. Same operator UX as Phase 78. All passes idempotent on rerun. | ✓ |
| `--phase-only` flag forcing two operator commands per round | Operator runs `--db benchmark --phase-only` first, then `--db benchmark` for evals. More explicit but more steps to remember. | |
| `--passes` flag listing which passes to run | More flexible (`--passes phase,middlegame_eval`) but extra surface area for an internal tool used by one operator. | |

**User's choice:** Empty multi-select response in auto mode → Claude's recommended option (single invocation).
**Notes:** Phase backfill is cheap (SQL-bound, ~minutes), eval passes are expensive (~hours). They are naturally sequenced. `--dry-run` reports three counts (phase-NULL rows + endgame span-entry NULL-eval rows + middlegame-entry NULL-eval rows) and exits without starting the engine.

---

## Combined PR / branch mechanics for 78 + 79

| Option | Description | Selected |
|--------|-------------|----------|
| Rebase Phase 79 branch onto Phase 78 branch + single combined PR → main | Phase 79 history contains all Phase 78 commits as base; one squash-merge yields one commit on main. Single review/deploy cycle. | ✓ |
| Stack Phase 79 PR on top of Phase 78 PR | Two PRs reviewed in sequence; merge 78 first, then 79 onto main. Decouples reviews but doubles the deploy mental model. | |
| Two separate PRs merged back-to-back | Two reviews, two merges, two deploys (or one deploy after both merges). More moving parts, more chances for an interim deploy to land Phase 78 alone — explicitly forbidden by SPEC. | |

**User's choice:** Empty multi-select response in auto mode → Claude's recommended option (rebase + single combined PR).
**Notes:** SPEC pins "Combined PR. Phase 78 and Phase 79 ship as one merge to `main` and one deploy. No interim deploy of Phase 78 alone." Rebase keeps history linear and review focused.

---

## Claude's Discretion

- All four gray areas resolved via Claude's recommended option after an empty multi-select response in auto mode. The user can revise any of these in the next planning step; the SPEC's 13 locked requirements are the binding contract, not these specific implementation choices.
- Chunk size of 10 000 rows for the SQL UPDATE pass is a defensive default; the planner can tune it after `EXPLAIN (ANALYZE)` on benchmark.
- Single-contiguous-middlegame-entry interpretation per SPEC; later `phase=1` re-entries after an endgame are intentionally not re-evaluated.
- PHASE-INV-01 invariant exposed as a manual operator check after each round; promotable to an automated post-backfill assertion if the planner wants harder enforcement.

## Deferred Ideas

- Middlegame conversion / parity / recovery metrics — Phase 79 captures the data, not the metric. UI / aggregation belong to a later milestone.
- Frontend display of `phase` — out of scope for Phase 79.
- Refactor of endgame repository queries to read `phase` instead of `endgame_class` — separate exercise, needs its own evaluation.
- Per-ply middlegame eval timeline — ~30× the engine calls; no UI surface motivates it.
- Divider threshold tuning — port lichess defaults verbatim per SPEC.
- Cross-row eval hash dedup — same Phase 78 D-10 stance, not worth the cache complexity.
- Backfill ETA / progress bar — current COMMIT-boundary logging is enough.
- Promoting PHASE-INV-01 to an automated assertion — planner's call.
