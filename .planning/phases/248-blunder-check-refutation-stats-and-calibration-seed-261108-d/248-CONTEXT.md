# Phase 248: Blunder-Check Refutation Stats and Calibration (SEED-261108-dk0) - Context

**Gathered:** 2026-11-09 (distilled from the SEED-261108-dk0 design review with the owner, not a discuss-phase run)
**Status:** Ready for planning

<domain>
## Phase Boundary

Blunder check (SEED-261108-dk0) selects "face-palm" blunders by asking: would a player of the user's rating spot the
punishment if they checked? This phase stores the data for that test and measures the selection on prod, so the next
phase (selection service) builds on fixed, measured constants. Deliverables:

1. Schema: two typed nullable columns on `game_flaws` for Maia's view of the opponent's punishing reply, plus a
   completion signal that works for games already stamped by Phase 247.
2. Go-forward scoring through the Phase 247 shared post-commit scorer.
3. Correct behaviour under flaw reclassification (mirror Phase 247 D-08/D-09).
4. A backfill (extending the Phase 247 script pattern), run on prod to completion and coverage-verified.
5. A read-only calibration report on prod data with recommended constants and a hand spot-check sample.

No selection service, API, UI, leaderboard or session logic is built here.

</domain>

<decisions>
## Implementation Decisions

### Stored data (owner, 2026-11-09)
- **D-01: Columns.** `game_flaws.maia_refutation_prob` REAL and `game_flaws.maia_refutation_rank` SMALLINT, nullable,
  no default (metadata-only ALTER). NULL = not scored. Rank uses the Phase 247 definition: 1 + the number of legal moves
  with strictly higher Maia probability (1 = Maia's top choice; ties share a rank).
- **D-02: The refutation is Stockfish's best move in the position after the blunder** (opponent to move). The
  researcher must establish which stored field holds it: `game_positions.best_move` / `game_positions.pv` at which ply
  (eval_cp has two ply conventions: lichess post-move vs entry-lane aligned, see project memory and
  `.planning/notes/eval-completion-columns.md`), or the first node/move of `allowed_pv_lines` / the PV at flaw_ply+1
  that the tactic detector uses. Prove it on real rows (dev DB) before building on it.
- **D-03: Scope = every user-side blunder.** `severity = 2` and ply parity matches `games.user_color` (use
  `is_opponent_expr` / the query_utils single source, never inline `ply % 2`). Misses included, so the scorer needs no
  miss classification. Not mistakes, not opponents' blunders (an opponent who is also a FlawChess user has their own
  import). About 2.3M rows on prod.
- **D-04: Elo** = the blunderer's (user's) rating at game time via `pinned_elo_for_mover`, fed as both `elo_self` and
  `elo_oppo` (Phase 247 D-03 parity), even though Maia plays the opponent's side. The question is "would a player of
  your level find this reply", so the real opponent rating does not enter.
- **D-05: Exact positions only:** the post-blunder board comes from the replayed game (in-memory boards in the shared
  scorer, `games.pgn` replay in the backfill), never from `game_flaws.fen`.
- **D-06: No concreteness columns** (owner: not reliably measurable). No material-swing, PV-depth or tactic-gate
  fields. Selection rests on findability alone.

### Write paths (mirror Phase 247)
- **D-07: Go-forward** extends the Phase 247 shared post-commit scorer (its D-13), so every path that scores flaws
  today (local drain, remote atomic submit, tier-4 `/flaw-blob-submit` re-score, backfill) also writes the refutation
  pair. One extra Maia inference per user-side blunder.
- **D-08: Reclassification** follows Phase 247 D-08/D-09: a Maia-loaded apply re-scores; a no-Maia reclassify keeps
  surviving values by omission in `_classify_and_fill_oracle`, inserts new rows NULL, and clears whatever completion
  signal D-09 defines so the backfill picks the game up again.
- **D-09: Completion signal must be new.** Games already carry Phase 247's stamp, so the refutation pair needs its own
  completion signal (a separate stamp column, or a stamp version that Phase 247 stamping also satisfies going
  forward). Planner chooses, but the backfill selector must terminate (stamp games with zero user-side blunders too)
  and the `is_maia_available()` guardrail applies (never stamp without a loaded Maia session).

### Backfill and completion
- **D-10: Backfill** extends `scripts/backfill_maia_flaws.py` (or a sibling mode of it): local run against prod over
  the tunnel, `md5(game_id) % num_shards` sharding, checkpointed, resumable, re-runnable as the only catch-up path. The
  orchestrator runs it detached (setsid nohup + Monitor), never inside an executor subagent.
- **D-11: The phase is done only after** (1) go-forward ships to prod (deploy is the owner's call: the plan pauses for
  a go-ahead), (2) the full prod backfill and a catch-up re-run, (3) coverage verification: at least 99% of user-side
  blunders in fully evaluated games carry `maia_refutation_prob`, with the NULL remainder explained by reason bucket,
  and (4) the calibration report is written and committed.
- **D-12: Interaction with Phase 247's open plan 07** (its prod backfill): calibration of missed punishments needs
  247's `maia_best_*` at >=99% coverage. Don't run both backfills against prod at once unless the planner shows the
  tunnel and DB can take it; finishing 247-07 first is acceptable.

### Calibration report (read-only on prod)
- **D-13: Miss classification** is computed in the report, not stored. `ES_ref` = user's expected score before the
  opponent's previous move; `ES_played` = after the user's blunder. Allowed = `is_miss` false; pure miss = `is_miss`
  true and `ES_played >= ES_ref - INACCURACY_DROP`; mixed = `is_miss` true otherwise. Expected score = the flaw
  pipeline's own ES function (same one `INACCURACY_DROP` applies to), with the correct per-row ply convention.
- **D-14: Findability tests measured on a threshold grid,** by Elo bucket (<800, 800-1199, 1200-1599, 1600-1999,
  2000-2399, 2400+, rating = `pinned_elo_for_mover`) and by case: allowed uses `maia_refutation_prob` >= R or
  `maia_refutation_rank` = 1; pure miss uses `maia_best_prob` >= X′ or `maia_best_rank` = 1; mixed passes if either.
- **D-15: Eval band:** measure candidate pre-move ES bounds (skip completely won or lost positions) on blunders and on
  every judged move of herring windows.
- **D-16: Window fit under the hazard model** (seed constants: `HAZARD` = 0.265, window length L uniform over 3-5 user
  moves, `LEAD_IN_PLIES` = 3): for blunder positions 1-5, the share of qualifying blunders whose preceding judged user
  moves are all Good (ES drop below `INACCURACY_DROP`, inaccuracies excluded, from per-ply evals) and inside the eval
  band; herring supply (L consecutive Good, in-band user moves); supply per user after all filters, including the
  `MAX_MISS_SHARE` = 0.30 cap on pure misses as a share of blunder windows. Report how game eval provenance (our full
  evals vs lichess evals) affects supply.
- **D-17: Arrow-oddness diagnostic:** on a sample, Maia's played-move probability (user's rating) for judged Good
  moves vs qualifying blunders. A large gap means the arrow's oddness gives the answer away. Maia runs inside the
  report script for this (not stored).
- **D-18: Outputs:** a dated markdown report under `reports/` (suggested `reports/blunder-check/`), with recommended
  constants (R, X′, eval-band bounds) as a recommendation only; and an exported spot-check sample of about 20 windows
  per Elo bucket, readable by a human (game link, lead-in and judged moves, the answer and the refutation) for the
  owner and possibly GM Noel Studer. No constants are wired into app code in this phase.

### Out of scope
- **D-19:** selection service, session/scoring API, drill UI, Train schedule integration, leaderboards, cross-mode
  cooldown, spaced repetition, any concreteness test, the Flaws-tab face-palm filter, benchmark-DB run.

### Claude's Discretion
- Completion-signal shape (D-09), migration shape, partial indexes for the selector.
- Whether the refutation pass lives inside the existing scorer function or a sibling called from the same hook.
- Report script location (`scripts/` vs `analysis/`, which has its own venv), sampling rates, and how per-ply ES is
  pulled efficiently over the tunnel (sample-based is fine where exact counts aren't needed).
- Edge cases default like Phase 247: guest flaws scored like everyone else; no legal reply (mate/stalemate after the
  blunder) or missing refutation move leaves the pair NULL with a counted reason; the game is still marked complete.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`: the feature design, all owner decisions, the
  2026-11-09 calibration probe and prod measurements (tactic tags on only 22% of non-miss blunders, PV on ~93%)
- `.planning/seeds/SEED-261108-zkp-maia-stats-on-game-flaws.md`: Phase 247 design, Maia cost measurements, gotchas
- `.planning/phases/247-maia-stats-on-game-flaws/247-CONTEXT.md` and its `247-0*-SUMMARY.md` files: the shared
  scorer, stamp, reclassify semantics and backfill script this phase extends; `247-07-PLAN.md` for the prod-run pattern
- `.planning/notes/eval-completion-columns.md`: what "fully evaluated / analyzed by us" means (coverage denominator)

</canonical_refs>

<code_context>
## Existing Code Insights

- `app/services/maia_flaw_scoring.py`: Phase 247's shared post-commit scorer (sole writer of the `maia_*` columns).
- `app/services/maia_flaw_stats.py`, `app/services/maia_engine.py` (`full_policy`, `is_maia_available`),
  `app/services/best_move_candidates.py` (`pinned_elo_for_mover`).
- `scripts/backfill_maia_flaws.py`: the sharded, stamp-checkpointed backfill to extend.
- `app/models/game_flaw.py` (Maia columns, `allowed_pv_lines`, tactic columns), `app/models/game_position.py`
  (`best_move`, `pv`), `app/models/game.py` (stamps).
- `app/repositories/query_utils.py`: `is_opponent_expr` (ply parity single source).
- `app/services/flaws_service.py`: `_is_miss` (opponent's previous move was a mistake or blunder), ES helpers and
  severity thresholds; `app/services/train_pool.py` `_vetted_move` for the second-best safety precedent.
- `app/services/eval_apply.py`: `_classify_and_fill_oracle` 4-way diff/upsert (preserve-by-omission set).

</code_context>

<specifics>
## Specific Ideas

- Project memory traps that apply: eval_cp two ply conventions (repair/interpret per row, validate with a control);
  asyncpg JSONB null vs SQL NULL (not relevant for REAL/SMALLINT but don't introduce JSONB); long operator runs
  (Bash 10-min cap, setsid + Monitor, log buffer looks frozen under Python 3.14, watch DB progress instead);
  benchmark/prod DB not static (hash sharding); executor subagents die on long DB-heavy runs (run those inline).
- The calibration report should include a short "how to read this" section and state its sample sizes.

</specifics>

<deferred>
## Deferred Ideas

- Cheap beginner fallback if the spot-check shows positional blunders reaching low ratings: require the punishing
  reply to be a capture, check or mate at low ratings only (move type, no line evaluation). Decide after the spot-check.
- Whether missed punishments stay in at all: owner discusses with GM Noel Studer; the cap assumption holds meanwhile.

</deferred>

---

*Phase: 248-blunder-check-refutation-stats-and-calibration*
*Context gathered: 2026-11-09*
