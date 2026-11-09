# Phase 248: Blunder-Check Refutation Stats and Calibration - Research

**Researched:** 2026-11-09
**Domain:** Maia-3 post-commit flaw scoring (extension of Phase 247), operator backfill over the prod tunnel, read-only calibration report
**Confidence:** HIGH for code paths and the refutation source (proven on dev rows); MEDIUM for prod NULL budget and run time (extrapolated, no prod probe this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Stored data (owner, 2026-11-09)
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

#### Write paths (mirror Phase 247)
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

#### Backfill and completion
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

#### Calibration report (read-only on prod)
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

#### Out of scope
- **D-19:** selection service, session/scoring API, drill UI, Train schedule integration, leaderboards, cross-mode
  cooldown, spaced repetition, any concreteness test, the Flaws-tab face-palm filter, benchmark-DB run.

### Claude's Discretion
- Completion-signal shape (D-09), migration shape, partial indexes for the selector.
- Whether the refutation pass lives inside the existing scorer function or a sibling called from the same hook.
- Report script location (`scripts/` vs `analysis/`, which has its own venv), sampling rates, and how per-ply ES is
  pulled efficiently over the tunnel (sample-based is fine where exact counts aren't needed).
- Edge cases default like Phase 247: guest flaws scored like everyone else; no legal reply (mate/stalemate after the
  blunder) or missing refutation move leaves the pair NULL with a counted reason; the game is still marked complete.

### Deferred Ideas (OUT OF SCOPE)
- Cheap beginner fallback if the spot-check shows positional blunders reaching low ratings: require the punishing
  reply to be a capture, check or mate at low ratings only (move type, no line evaluation). Decide after the spot-check.
- Whether missed punishments stay in at all: owner discusses with GM Noel Studer; the cap assumption holds meanwhile.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs; the coverage contract is CONTEXT D-01..D-19.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Two nullable typed columns | §Migration shape; 247 migration precedent (metadata-only `add_column`) |
| D-02 | Refutation = Stockfish best move after the blunder | §Q1: `game_positions.best_move` at `flaw_ply + 1`, proven legal 800/800 on dev |
| D-03 | Scope = user-side blunders | §Q2: `_SEVERITY_INT["blunder"]` + `mover_is_white_at_ply` (Python twin of `is_opponent_expr`) |
| D-04 | Elo = blunderer's rating, symmetric feed | §Q2: reuse the pre-push board's `board.turn` rating, never the post-push board's |
| D-05 | Exact post-blunder board | §Q2: `pre_board.copy(stack=False)` + `push_uci(played)`; never `game_flaws.fen` |
| D-06 | No concreteness columns | Nothing to build |
| D-07 | Go-forward via the shared scorer | §Q8: one change in `score_game` covers drain, atomic submit, blob submit, backfill |
| D-08 | Reclassify semantics | §Q8/§Pitfall 3: preserve by omission (keys never in `flaw_record_to_row`), clear both stamps in `clear_maia_flaws_completed` |
| D-09 | New completion signal | §Q3: separate `games.maia_refutation_completed_at` column (recommended) |
| D-10 | Backfill mode | §Q4: `--mode {full,refutation}` on `scripts/backfill_maia_flaws.py` |
| D-11 | Done = deploy + backfill + catch-up + ≥99% coverage + report | §Q4 runbook, §Coverage SQL, §Open Question 1 (NULL budget risk) |
| D-12 | Ordering vs 247-07 | §Q5: sequential; connection budget forbids overlap |
| D-13..D-18 | Calibration report | §Q6, §Q7, §Pattern 5 |
| D-19 | Out of scope | Respected |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend: FastAPI, Python 3.14, uv, SQLAlchemy 2.x async `select()` API, asyncpg, Alembic, Pydantic v2. PostgreSQL only.
- `routers/` HTTP only; `services/` logic; `repositories/` DB access ("no SQL in services"). Note: `maia_flaw_scoring.py` already holds its fingerprint `select()` (Phase 247 accepted); keep the refutation join next to it rather than doing an unscoped move.
- Never `asyncio.gather` on one `AsyncSession`; no session open during Maia inference (247 D-13 pattern).
- No native PG ENUM; SMALLINT/REAL on high-cardinality tables; no JSONB for these columns.
- No magic numbers (named constants: Elo bucket edges, grid values, hazard constants, sample rates, exit codes).
- `Literal[...]` for fixed sets (reasons, modes, cases, `--db`); `Sequence[...]` for covariant params; explicit return types; ty zero errors on `app/ tests/ scripts/`; `# ty: ignore[rule]` with reason only.
- Nesting depth ≤ 4 in `app/` (gated); ~100 logic lines / cognitive complexity ≤ 15 soft. `_derive_flaw_stats` must be split, not grown.
- Sentry: `capture_exception` in non-trivial `except` in services/routers; no variables in messages; `set_context`/`set_tag`.
- Comment bug fixes at the fix site.
- Pre-merge gate (ruff format/check, ty ×2, function-size gate, `pytest -n auto -x`, frontend gate) before the squash-merge; CHANGELOG `[Unreleased]` bullet when the phase merges.
- `bin/deploy.sh` only deploy path; deploy is the owner's call. `bin/reset_db.sh` forbidden without permission.
- GSD scope discipline: nothing outside the phase; flag, don't build.
- Project memory traps that bind this phase: prod `max_connections=30` (≤ 9 operator connections in total across all scripts); executor subagents die on long DB runs (orchestrator runs prod operations inline, detached); Python 3.14 log buffering (watch DB counts, not the log); `pkill -f` from a Bash call that contains the pattern kills the caller; commit same-day reports before a re-run; fresh worktree needs `uv sync --group maia-inference`.

## Summary

The refutation move is `game_positions.best_move` at `ply = flaw_ply + 1`. `best_move` is decision-ply keyed (the best move FROM that row's position) for both eval populations; only `eval_cp` carries the post-move +1 shift. On 800 dev user-side blunders (400 engine-analyzed, 400 lichess-eval), the ply+1 `best_move` was legal in the replayed post-blunder board 800/800 and legal in the pre-blunder board 0/800; the flaw-ply `best_move` showed the mirror image. The first token of `game_positions.pv` at `flaw_ply + 1` (the tactic detector's refutation PV) agrees with it on 99.7% of engine rows; the 29 disagreements on dev all sit in the opening dedup region (ply ≤ 20), where `best_move` comes from the opening cache. When the blunder is the game's last move, `best_move` at ply+1 is NULL (the terminal row is never searched for a best move), but engine games still carry `pv` there (68 of 69 on dev), so a `COALESCE(best_move, pv[0])` fallback is worth having.

The shared scorer (`app/services/maia_flaw_scoring.py`) needs three additions: (1) load `games.user_color`, `game_flaws.severity` and the ply+1 refutation UCI (outer join on a second `GamePosition` alias, included in the fingerprint); (2) in `score_game`, for user-side blunders only, push the played move onto a copy of the pre-push board and run one more `full_policy` at the blunderer's Elo; (3) write 10 Maia keys per flaw and stamp both completion columns. Because all four live lanes and the backfill call this one function, D-07 needs no call-site edits. D-08 needs one edit: `clear_maia_flaws_completed` clears both stamps (all five reclassify call sites already go through it).

Recommended completion signal: a separate nullable `games.maia_refutation_completed_at`, no index. The backfill gains `--mode refutation`: it selects games with flaws whose base stamp is set and refutation stamp is NULL, runs inference only for user-side blunders (~2.3M instead of re-scoring ~7.6M flaws), and writes only the 2 columns plus the new stamp. Expected wall time about 8-10 h at 9 processes. It cannot overlap Phase 247-07: 247-07's third run (9 shards since 08:08 UTC today) was at about 404k of 603k games at 18:34 UTC, ETA around 23:30 UTC, and two 9-shard runs would exceed prod's 27 usable connections and saturate the 8 physical cores of the dev box.

**Primary recommendation:** Extend the shared scorer in place (full mode writes all 10 values and both stamps), add a separate refutation stamp plus a `--mode refutation` backfill, run it only after 247-07 and its catch-up finish, then write `scripts/blunder_check_calibration.py` (main venv, read-only engine) that reuses `_run_all_moves_pass` for per-ply ES/severity, and probe the prod NULL budget before locking the 99% bar.

## Answers to the Orchestrator's Questions (with evidence)

### Q1. Which stored field holds Stockfish's best move after the user's blunder? (D-02)

**`game_positions.best_move` at `ply = game_flaws.ply + 1`, for both eval populations.** Fallback: first token of `game_positions.pv` at the same row when `best_move` is NULL.

Code evidence:
- Ply indexing: `game_flaws.ply` is the ply of the position before the flawed move, and the flaw move is played from row `ply`. `_run_all_moves_pass` documents "`positions[N].eval_cp = eval AFTER move N was played`", "`ES_before = _ply_to_es(positions[N-1], mover)  # board before mover plays move N`" [VERIFIED: app/services/flaws_service.py:382-385]. `replay_flaw_boards` snapshots `found[ply] = (board.copy(stack=False), node.move.uci())` BEFORE `board.push(node.move)` [VERIFIED: app/services/maia_flaw_scoring.py:252-255].
- `best_move` is not shifted: "Convention: a row stores the eval of the position AFTER its move (post-move) ... write row k's eval from `pos_eval[k + 1]` via `_post_move_eval` — the single +1 shift site. best_move stays decision-ply-keyed (best move FROM row k's position), so it is NOT shifted." [VERIFIED: app/services/eval_apply.py:686-691]. Model comment: "PV[0] UCI best move for every evaluated position" ... "safe because best_move is a property of the pre-move position" [VERIFIED: app/models/game_position.py:162-167].
- Lichess-eval games get `best_move` from our engine too: "is_lichess_eval_game=True: lichess %evals are already post-move and authoritative — NEVER shifted or overwritten. Only best_move (engine-supplied; lichess lacks it) is written" [VERIFIED: app/services/eval_apply.py:693-697, read via Bash this session]. So the eval_cp two-convention problem does not apply to `best_move`.
- `pv` at ply+1: "~12-ply UCI refutation line (space-joined), stored only at the position AFTER each flawed move (ply = flaw_ply + 1). This is the refutation line consumed by the tactic-motif classifier." [VERIFIED: app/models/game_position.py:168-171]. `_write_flaw_pvs` writes pv at "ply N+1 = the refutation line from the post-blunder board" from `engine_result_map` at its own ply [VERIFIED: app/services/eval_apply.py:1397-1433, read via Bash].
- `allowed_pv_lines` is NOT a move source: blob nodes carry `b`, `bm`, `s`, `sm`, `su` (evals plus the second-best UCI), no best-move UCI [VERIFIED: app/models/game_flaw.py:128-135, read via Bash; 247-RESEARCH Q1].

Dev-DB evidence (read-only, `PGOPTIONS=-c default_transaction_read_only=on`, user-side blunders by parity in fully evaluated games):

| Population | User blunders | `best_move` at ply+1 | `pv` at ply+1 | bm = pv[0] | bm ≠ pv[0] |
|---|---|---|---|---|---|
| engine (`lichess_evals_at IS NULL`) | 9,981 | 9,912 | 9,964 | 9,867 | 29 (all ply+1 ≤ 20, dedup region) |
| lichess-eval | 7,071 | 1,709 | 1,709 | 1,709 | 0 |

(Dev lichess-eval games mostly never ran the MultiPV pass: only 1,763 have `full_pv_completed_at`. Prod ran the unified lichess-eval backfill, see Phase 247 S3: `best_null 706` of 77,166 sampled flaws at the flaw ply.)

PGN-replay legality probe (scratchpad script, `replay_flaw_boards` + `push_uci(played)`, 400 random rows per population with `best_move` at ply+1 present):

| Check | engine | lichess |
|---|---|---|
| fen matched replay | 400/400 | 400/400 |
| ply+1 `best_move` legal in POST-blunder board | **400** | **400** |
| ply+1 `best_move` legal in PRE-blunder board (control) | 0 | 0 |
| ply+1 `pv[0]` legal in post board | 400 | 400 |
| flaw-ply `best_move` legal in pre board / in post board (control) | 400/400 · 0 | 378/378 · 0 |
| post board game over | 0 | 0 |
| refutation is a capture | 173 | 179 |

Why `best_move` is NULL at ply+1 (dev):

| Population | `full_pv_completed_at` | bm NULL | of which terminal row (`move_san IS NULL`) | non-terminal | terminal rows with `pv` |
|---|---|---|---|---|---|
| engine | set | 69 | 69 | 0 | 68 of 69 |
| lichess | NULL | 5,308 | 53 | 5,255 (MultiPV pass never ran) | 0 |
| lichess | set | 54 | 16 | 38 | 0 |

Terminal case = the user's blunder was the last move of the game (opponent resigned, flagged, abandoned, or the user resigned on the opponent's turn). The drain never searches a best move for the terminal row: `if not target.is_terminal: best_move_by_ply[target.ply] = best_move` [VERIFIED: app/services/eval_apply.py:717-718, read via Bash], but the terminal donor's PV is written at N+1 by `_write_flaw_pvs` for engine games.

**Recommendation:** refutation UCI = `COALESCE(gp_next.best_move, NULLIF(split_part(gp_next.pv, ' ', 1), ''))` with `gp_next.ply = game_flaws.ply + 1`. Prefer `best_move` (same source as 247's `maia_best_*`, consistent across both populations); the pv fallback only fires where `best_move` is NULL. Count fallback use as an informational counter (`refutation_from_pv`), not a NULL reason.

### Q2. Scorer structure and the cleanest way to add the refutation pair

Structure [VERIFIED: app/services/maia_flaw_scoring.py, Read this session]:
- `FlawMaiaInput(ply, fen, best_uci, second_uci)` (lines 85-90); fingerprint = `frozenset((f.ply, f.fen, f.best_uci, f.second_uci) ...)` (93-94); `GameMaiaInputs` holds ratings, platform, TC bucket, `is_correspondence`, flaws (97-110).
- `_flaw_fingerprint_select` (127-154): one SELECT used both for the load and the in-lock re-read; outer-joins `GamePosition` at `GamePosition.ply == GameFlaw.ply` and extracts `missed_pv_lines -> '0' ->> 'su'`.
- `boards_from_targets` (211-222) gives `ply -> (pre-push board, played UCI)` from the drain's in-memory targets; `replay_flaw_boards` (225-256) does the same from `games.pgn`.
- `_derive_flaw_stats` (264-299): ply/fen guards, `raw_rating = inputs.white_rating if board.turn == chess.WHITE else inputs.black_rating`, `pinned_elo_for_mover(...)`, one `full_policy(board.fen(), elo)`, `MaiaInferenceUnavailableError` on None, `compute_maia_flaw_stats`.
- `score_game` (325-343): every flaw yields a row with all keys (None for unscorable) so a re-score never leaves stale values.
- `write_game_maia_scores` (385-428): ascending advisory locks, fingerprint re-read, `require_unstamped` check, `bulk_update_flaw_maia_stats` + `mark_maia_flaws_completed`.
- `score_game_flaws_after_apply` (436-475): `is_maia_available()` guard, read session closed, `asyncio.to_thread(score_game, ...)`, write session, Sentry on failure, never raises.

Recommended additions (inside the same module, same hook; no sibling hook):
1. `FlawMaiaInput` gains `severity: int` and `refutation_uci: str | None`; the fingerprint tuple grows to `(ply, fen, best_uci, second_uci, severity, refutation_uci)` so a concurrent reclassify or ply+1 `best_move` change between load and write produces `fingerprint_changed`.
2. `_flaw_fingerprint_select` adds `GameFlaw.severity` and the refutation expression over `gp_next = aliased(GamePosition)` joined on `(game_id, user_id, ply = GameFlaw.ply + 1)`.
3. `GameMaiaInputs` gains `user_color: Literal["white", "black"]` (load `Game.user_color`).
4. User-side test in Python: `flaw.severity == _SEVERITY_INT["blunder"] and mover_is_white_at_ply(flaw.ply) == (inputs.user_color == "white")`. `_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}` [VERIFIED: app/repositories/game_flaws_repository.py:30]; `mover_is_white_at_ply` returns `ply % 2 == _PLY_EVEN_MOVER_WHITE` and is documented as "Mirrors the SQL convention in is_opponent_expr" [VERIFIED: app/repositories/query_utils.py:61-68, read via Bash] with `_PLY_EVEN_MOVER_WHITE = 0  # ply % 2 == 0 means white moved` [VERIFIED: app/repositories/query_utils.py:21]. SQL-side selectors and status/coverage queries built in Core use `is_opponent_expr(GameFlaw.ply, Game.user_color)` [VERIFIED: query_utils.py:71-99, read via Bash].
5. Split `_derive_flaw_stats`: extract `_mover_elo(inputs, pre_board) -> float | None` (the existing rating/pin code) and add `_derive_refutation(pre_board, played_uci, elo, refutation_uci)`; the Elo MUST come from the pre-push board's mover (the blunderer), never `post_board.turn` (that is the opponent).
6. Pure helper in `maia_flaw_stats.py`: `compute_refutation_stats(probs, refutation_uci)` reusing `_rank` (`RANK_BASE + sum(1 for p in probs.values() if p > own)`) and `RANK_BASE: int = 1` [VERIFIED: app/services/maia_flaw_stats.py:29, 78-81].
7. Extend `MaiaReason` (currently `"played_not_legal", "no_rating", "pgn_unparseable", "invalid_root", "ply_beyond_mainline", "fen_mismatch", "best_missing", "best_not_legal", "second_missing", "second_not_legal", "second_equals_best", "single_legal_move"` [VERIFIED: app/services/maia_flaw_stats.py:37-50]) with three refutation reasons (names are a recommendation [ASSUMED]): `"no_legal_reply"`, `"refutation_missing"`, `"refutation_not_legal"`.

Cost: one extra `full_policy` per user-side blunder (D-07). Check `refutation_uci` legality on the post board before inference so missing/illegal refutations cost nothing.

### Q3. Completion signal (D-09): recommendation = separate stamp column

| Option | Backfill selector | Refutation-only backfill cost | Reclassify (D-08) | Verdict |
|---|---|---|---|---|
| **A. `games.maia_refutation_completed_at` TIMESTAMPTZ NULL** | `maia_refutation_completed_at IS NULL AND maia_flaws_completed_at IS NOT NULL AND EXISTS(flaws)` | ~2.3M inferences, 2-column writes | `clear_maia_flaws_completed` sets both NULL in one UPDATE | **Recommended** |
| B. Stamp version (`maia_flaws_version SMALLINT`, v2 = with refutation) | `version IS DISTINCT FROM 2` | Either re-score all 7.6M flaws (≈4x cost), or encode "v1 base is current" in the selector, which is option A in disguise | Clear sets version NULL | Rejected: more migration/semantics churn (existing timestamps need a backfilled version) and no benefit |

Details for option A:
- Migration: one revision adding `game_flaws.maia_refutation_prob REAL`, `game_flaws.maia_refutation_rank SMALLINT`, `games.maia_refutation_completed_at TIMESTAMPTZ`, all nullable, no default/CHECK/index, mirroring `a7d3f1c9e247` (whose docstring: "Deliberately metadata-only: no server_default, no CHECK constraint, no index and no data UPDATE") [VERIFIED: alembic/versions/20261108_120000_a7d3f1c9e247_phase_247_maia_flaw_stats.py, read via Bash]. Column name `maia_refutation_completed_at` is a recommendation [ASSUMED].
- No partial index: the 247 stamp is "No index on purpose" [VERIFIED: app/models/game.py:267]; the selector runs once per shard at start (a seq scan of `games`, ~4.3 GB, as in 247), and a partial index on a nearly-all-NULL column would need `CREATE INDEX CONCURRENTLY` outside the migration transaction for no gain.
- Stamping rules: full mode (go-forward lanes, blob submit, backfill `--mode full`) stamps BOTH columns after writing all 10 values; refutation mode stamps only the new column. Both decided by `is_maia_available()` and pass completion, never row counts (247 D-05). Zero-user-blunder games get stamped too (selector terminates).
- `clear_maia_flaws_completed(session, game_id) -> bool` becomes: `UPDATE games SET maia_flaws_completed_at = NULL, maia_refutation_completed_at = NULL WHERE id = :id AND (maia_flaws_completed_at IS NOT NULL OR maia_refutation_completed_at IS NOT NULL) RETURNING id`. All five reclassify sites already call it (§Q8), so none change.
- Remote-worker lanes: no worker change. Remote workers never run Maia; the server's post-commit hook does (eval_remote.py:1096, :1484).
- Why refutation mode requires the base stamp: a game with a NULL base stamp is picked up by `--mode full`, which writes all 10 values and both stamps. So "run full, then refutation" leaves every game with both stamps, and refutation mode never has to clear stale out-of-scope values (only a reclassify creates those, and a reclassify always clears the base stamp too).

### Q4. Backfill script: how it works and how to extend it

Current behaviour [VERIFIED: scripts/backfill_maia_flaws.py, Read this session]:
- Selector `_SELECT_SHARD_SQL` (99-109): `games g JOIN users u ... WHERE g.maia_flaws_completed_at IS NULL AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id) AND {SHARD_RESIDUE_SQL} % :num_shards = :shard`, ordered `u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC`. `SHARD_RESIDUE_SQL = "('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint"` (96).
- One id snapshot per shard (`select_shard_game_ids`, 126-149), batches of `DEFAULT_BATCH_GAMES = MAX_GAMES_PER_WRITE_TXN` (= 50), each batch: short read (`load_game_maia_inputs`), `score_game(inputs, None)` (PGN replay), one write txn with `require_unstamped=True`; per-game retry on batch failure; `MAX_CONSECUTIVE_BATCH_FAILURES = 5` ends the shard with `EXIT_SHARD_FAILED = 4`; `EXIT_MAIA_UNAVAILABLE = 3` (76-88).
- Processes: spawn context, one per shard, `start_maia(intra_op_num_threads=1)`, `pool_size=1, max_overflow=0` engine per shard (396-399, 434-475). JSON shard report in `finally`; parent prints a combined `total:` line; SIGTERM forwarded.
- `--status`: four SELECT-only counts (555-579).

Extension (recommended):
- `--mode {full,refutation}` (`Literal["full", "refutation"]`), default `full` so the 247 reminder command keeps working and now writes both.
- Mode-specific selector: refutation adds `AND g.maia_flaws_completed_at IS NOT NULL` and tests `g.maia_refutation_completed_at IS NULL` instead of the base stamp.
- Mode-specific scoring: `score_game(inputs, boards, mode)`. In refutation mode, skip PGN replay when the game has no user-side blunder (still stamp it), replay only the blunder plies, run inference only for them, emit rows with only `user_id, game_id, ply, maia_refutation_prob, maia_refutation_rank` for in-scope rows (one `update(GameFlaw)` executemany needs uniform keys).
- `write_game_maia_scores(..., mode=...)`: `require_unstamped` checks the mode's own stamp; the fingerprint check is identical for both modes.
- Report: `refutations_scored`, `refutations_null`, `refutations_from_pv`, refutation reasons in the same `reasons` dict. Report file name should carry the mode (`{db}-{mode}-{run_stamp}-shard{n}.json`) so 247 and 248 reports never collide.
- `--status --mode refutation`: `refutation_stamped_games`, `refutation_unstamped_games_with_flaws` (base stamped), `user_blunders_with_refutation`, `user_blunders_total` (Core query with `is_opponent_expr`, not inline parity).

Cost estimate [ASSUMED, extrapolated]: 247-07 runs at ~8.8 flaws/s per shard with 9 shards (prod log, 2026-11-09 18:34 UTC: `shard 4/9: 45000/66770 games ... (8.8 flaws/s)`). The 247 seed puts 4.59M blunders on prod (1.78M misses) and the context says ~2.3M user-side; ~2.3M inferences / (9 × ~8.8/s) ≈ 8.1 h, plus per-game overhead for ~1.03M selected games (read + replay; no inference for games without user blunders) ≈ 0.5-1.5 h. **Budget 8-10 h wall, 9 shards.** Measure on a bounded prod slice (one shard, `--limit 50`) first, as 247-07 Task 1 did.

### Q5. Phase 247 plan 07 status and ordering (D-12)

Evidence from artifacts (read-only inspection, 2026-11-09 19:34 CET = 18:34 UTC):
- Task 1 (tracer slice) DONE and committed (`27e0fcb17 docs(247-07): prod backfill tracer slice report`; `reports/maia-flaws-backfill/prod-coverage.md` has only the "Slice" section).
- Full run in progress, third attempt. `temp/maia-flaws-backfill/prod-full.log`:
  - run 1, 9 shards, started 2026-11-08 21:17 UTC, stopped ~06:07 UTC: `total: games_selected=1025332 games_scored=339050 games_stamped=339050 ... flaws_scored=2456314 flaws_null=17352 reason_best_missing=23285 reason_no_rating=17349 ...`
  - run 2, 14 shards, 06:08-08:08 UTC: `games_stamped=83500 ... flaws_scored=604852`. Stopped because 14 shards exhausted prod connections (project memory: `max_connections=30`, 27 usable, Sentry FLAWCHESS-D8 TooManyConnections).
  - run 3, 9 shards, started 08:08 UTC (parent PID 3148890 still alive), each shard at about 45,000 of ~67,000 selected games at 18:34 UTC, 8.8 flaws/s per shard. Remaining ≈ 9 × 22k ≈ 199k games at ~4.3k games/h/shard ≈ 5 h, **ETA ≈ 23:30 UTC 2026-11-09**.
- Not done: Task 2 write-up, Task 3 catch-up + coverage SQL + Health, `247-07-SUMMARY.md`. STATE.md still says "Plan: 6 of 7".

Implications for ordering:
1. **No overlap.** Two 9-shard runs need 18 connections next to the app's ~11 + umami 1 + MCP 1 (> 27), and Maia saturates the dev box's 8 physical cores (`lscpu`: 8 cores, 2 threads/core) so overlap gives no speed-up anyway (project memory: 14 shards gave "zero speed gain").
2. **Code work can proceed now** (schema, scorer, backfill mode, report script, tests on dev). It touches no prod resource. Do it in a dedicated worktree or branch without disturbing the main checkout's running backfill (spawned children already imported their modules, so file edits do not affect them, but keep the main checkout stable anyway).
3. **Deploy 248 after 247-07's full run ends** (owner go-ahead). Reasons: the migration's `ALTER TABLE game_flaws/games` needs a brief ACCESS EXCLUSIVE lock that queues behind the backfill's write transactions; and once 248 is live, 247's catch-up can run as `--mode full` and produce both stamps in one pass.
4. Then: 248 refutation backfill (8-10 h) → catch-up (`--mode full` then `--mode refutation`) → both coverage checks (247's `maia_played_prob`/`maia_best_prob`, 248's `maia_refutation_prob`) → calibration report (needs both at ≥ 99%).
5. If 247-07's catch-up/coverage is done before 248 deploys, 248 just inherits it; if 248 deploys first, the 247 catch-up must use the new script (it writes both).

### Q6. Calibration report: ES function, per-ply evals, denominator, query strategy, location

**ES function (D-13):** the flaw pipeline uses `_ply_to_es(pos, mover_color)`: mate → `MATE_CP_EQUIVALENT if pos.eval_mate > 0 else -MATE_CP_EQUIVALENT` then `eval_cp_to_expected_score(cp_equiv, mover_color)`, else `eval_cp_to_expected_score(pos.eval_cp, mover_color)` [VERIFIED: app/services/flaws_service.py:196-212]; `MATE_CP_EQUIVALENT: int = 1000` [VERIFIED: flaws_service.py:57]. `eval_cp_to_expected_score` is `1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))` with `sign = 1 if user_color == "white" else -1` [VERIFIED: app/services/eval_utils.py:82-83] and `LICHESS_K: float = 0.00368208` [VERIFIED: eval_utils.py:58]. **No Elo or TC input.** Project memory (Expected-score refit, SEED-203): move-quality uses must stay on `LICHESS_K`; the per Elo × TC refit is only for actual-vs-expected comparisons. `INACCURACY_DROP: float = 0.05` [VERIFIED: flaws_service.py:47].

**Per-ply convention:** inside games with `full_evals_completed_at IS NOT NULL`, every row is post-move for both lichess %evals and our full drain: "This post-move convention is uniform across ALL sources ... so no per-source branch is needed here." [VERIFIED: flaws_service.py:387-389]. The "aligned" population from project memory is the entry lane (`app/services/eval_entry.py`: snapshots the pre-push board at ply i and writes row i), which only touches sparse midgame/endgame-entry plies of games not yet fully evaluated; the full drain overwrites those rows (local drain `preserve_existing_evals=False`). Residual risk: an entry-lane value surviving on a hole row of an engine game. The report reuses exactly the classifier's convention, so its judgement of "Good" agrees with how the stored flaws were produced, and a control (below) detects drift.

**Recommended computation:** import `_run_all_moves_pass` from `app.services.flaws_service` (precedent: `scripts/remote_eval_worker.py:71` imports it). It returns `{n: (mover, severity, es_before, es_after)}` [VERIFIED: flaws_service.py:378-411] with severity from the same ladder the classifier used (cp drops and the mate ladder). Then, for a user blunder at ply `p` (user = mover at `p`):
- `ES_played` = `all_moves[p][3]` (es_after of the blunder, user POV).
- `ES_ref` = user-POV ES of row `p-2` = `_ply_to_es(positions[p-2], user_color)` (eval after the user's previous move = before the opponent's move `p-1`). Equivalent to `1 - all_moves[p-1][2]`, since the sigmoid is symmetric in sign.
- Case: `is_miss` false → allowed; `is_miss` true and `ES_played >= ES_ref - INACCURACY_DROP` → pure miss; else mixed. If `ES_ref` is unavailable (row `p-2` hole), report as `unclassified`.
- Judged user move at ply `q` is **Good** iff `q in all_moves` and `all_moves[q][1] is None` (no inaccuracy/mistake/blunder; inaccuracies excluded, matching "ES drop below INACCURACY_DROP" for cp transitions and the mate ladder for mate transitions). Its pre-move ES = `all_moves[q][2]` (for the eval band).
- **Control (must be ~100%):** on the sample, the plies where `_run_all_moves_pass` yields mistake/blunder must equal the stored `game_flaws` plies and severities. A mismatch rate above ~1% means a convention or staleness problem; report it.

**Coverage denominator (D-11):** user-side blunders in games with `full_evals_completed_at IS NOT NULL` (source-agnostic, includes lichess %eval games), per `.planning/notes/eval-completion-columns.md` and 247 Pattern 6. Do not use `has_engine_full_evals`.

**Query/sampling strategy over the tunnel:**
1. Game sample by md5 residue (deterministic, same idiom as the backfill): `SELECT ... FROM games g WHERE g.full_evals_completed_at IS NOT NULL AND ('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint % 1000 < :permille`. Include games without flaws (herring supply needs them). 2-3% of ~1.1M games ≈ 25-35k games, ≈ 50-70k user blunders (≥ 1-2k in 2400+).
2. Per batch of ~500 game ids: positions via ORM `select(GamePosition).options(load_only(GamePosition.eval_cp, GamePosition.eval_mate)).where(GamePosition.game_id.in_(ids)).order_by(game_id, ply)` (hits `ix_game_positions_game_id`, yields real `GamePosition` objects that `_run_all_moves_pass` accepts, ty-clean); flaws with `severity, is_miss, maia_*` columns; game metadata (`user_color`, ratings, platform, TC bucket, `time_control_str`, `lichess_evals_at IS NOT NULL`, `platform_url`, user `is_guest`).
3. Exact cheap aggregates server-side: user-side blunder counts per user and per Elo bucket (Core query with `is_opponent_expr`), fully evaluated game counts per user (for supply extrapolation).
4. PGN only for the spot-check sample and the arrow-oddness sample.
5. Read-only by construction: `create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0, connect_args={"server_settings": {"default_transaction_read_only": "on", "statement_timeout": ...}})`. One prod connection; run only when no backfill is running.

**Supply per user (D-16):** exact per-user counts × per-bucket pass rates from the sample (label as an estimate). Usable blunder windows per user = non-pure qualifying + `min(pure_qualifying, MAX_MISS_SHARE / (1 - MAX_MISS_SHARE) × non_pure_qualifying)`, then × the hazard-weighted window-fit share. Split everything by provenance (`lichess_evals_at IS NOT NULL` vs NULL) and exclude guest users from per-user supply.

**Hazard model numbers** (computed this session, h = 0.265, L uniform {3,4,5}): herring share 0.301; P(blunder at position k) = 0.265, 0.1948, 0.1432, 0.0701, 0.0258 (sum 0.699); normalized over blunder windows: **0.379, 0.279, 0.205, 0.100, 0.037**. Report the per-position fit share and the weighted average with these weights.

**Location:** `scripts/blunder_check_calibration.py` in the main venv, not `analysis/` (that venv has no `app` service deps or onnxruntime: its `pyproject.toml` lists marimo, polars, plotly, kaleido, psycopg, pydantic-settings, python-dotenv, numpy [VERIFIED: analysis/pyproject.toml, read via Bash]; the report needs `flaws_service`, `pinned_elo_for_mover`, `maia_engine.full_policy`). Outputs: `reports/blunder-check/blunder-check-calibration-YYYY-MM-DD.md` and `reports/blunder-check/spot-check-YYYY-MM-DD.md` (directory is new [ASSUMED name per D-18 suggestion]). Existing report convention: dated markdown under topic folders (`reports/maia-flaws-backfill/`, `reports/noel/`, `reports/misc/`).

### Q7. Arrow-oddness diagnostic inside a script (D-17)

- Lifecycle as in the backfill: `await maia_engine.start_maia(intra_op_num_threads=1)`, then check `maia_engine.is_maia_available()` and exit with a clear message if False (`scripts/backfill_maia_flaws.py:434-438`); `full_policy` is sync and returns None without a session [VERIFIED: app/services/maia_engine.py `full_policy`, read via Bash]; `await maia_engine.stop_maia()` at the end. Requires `uv sync --group maia-inference` (onnxruntime 1.29.0, numpy 2.5.2 present on the dev box this session).
- Good moves: sample judged Good user moves (from the windows the report already builds), replay the PGN to the pre-push board, Elo = `pinned_elo_for_mover(raw_rating=<user's rating at that ply's mover>, platform=..., time_control_bucket=..., is_correspondence=is_correspondence_time_control(time_control_str))` [VERIFIED: best_move_candidates.py:79-122, read via Bash], `probs = full_policy(board.fen(), elo)`, record `probs[played]` and rank.
- Blunders: use the stored `maia_played_prob` / `maia_played_rank` (same function, same Elo feed, written by 247), no inference needed.
- Size: e.g. 1,500 Good moves per Elo bucket × 6 ≈ 9k inferences × ~77 ms ≈ 12 min single process. Report per bucket: median and quartiles of played prob, share at rank 1, and AUC = P(a random Good move has higher played prob than a random qualifying blunder). AUC near 0.5 = no leak; near 1 = the arrow gives the answer away.

### Q8. Every apply path reaching flaw classification/scoring

| Path | Location | Scores? | What 248 needs |
|---|---|---|---|
| Local drain | `eval_drain.py:1582` `score_game_flaws_after_apply(..., targets=targets, source="full_eval_drain")` | Yes, post-commit | Nothing at the call site; `score_game` full mode writes 10 values + both stamps |
| Remote atomic submit | `eval_remote.py:1484` (`source="remote_eval_worker"`) | Yes | Same |
| Tier-4 `/flaw-blob-submit` | `eval_remote.py:1096` (`targets=None`, PGN replay, only `if blob_map:`) | Yes (re-score) | Same; re-scores the refutation too (one extra inference per user blunder; acceptable, keeps one write path) |
| Backfill | `scripts/backfill_maia_flaws.py` | Yes | `--mode full` (both) and `--mode refutation` |
| Reclassify inside apply | `eval_apply.py:2968` → `_classify_and_fill_oracle` → `clear_maia_flaws_completed` at `eval_apply.py:1149` | Clears stamp, then the lane's post-commit scorer re-stamps when Maia is loaded | Extend the clear helper to both stamps |
| `backfill_flaws.py --oracle-gap` | `scripts/backfill_flaws.py:185` → `_classify_and_fill_oracle` | No Maia | Covered by the helper |
| `backfill_flaws.py` default (delete + insert) | `scripts/backfill_flaws.py:404-417` (`delete_flaws_for_game`, `bulk_insert_game_flaws`, `clear_maia_flaws_completed`) | No Maia | Covered by the helper; delete+insert drops refutation values, correct because the stamp is cleared |
| `opening_cache_repair.py` rederive | `scripts/opening_cache_repair.py:2045` (classify) and `:2080` (GameNotAnalyzed clear) | No Maia | Covered by the helper; its propagate step rewrites opening `best_move` rows (`:1379`), which can change a ply+1 refutation, and the clear makes the backfill re-score |
| Entry lane | `eval_entry.py:579-593` (`classify_game_flaws` + `bulk_insert_game_flaws`, `ON CONFLICT DO NOTHING`) | No | Nothing: runs at import before any Maia stamp; the later full/MultiPV pass reclassifies and scores |
| `retag_flaws.py` | tactic columns only | No | Nothing (flaw set and best moves unchanged) |

The only other `best_move` writers are `apply_full_eval` (always followed by classify) and `opening_cache_repair` propagate (followed by rederive) [grep this session: `SET best_move` occurs only at eval_apply.py:457 and opening_cache_repair.py:1379]. `format_maia_backfill_reminder` needs no change if `--mode full` (the default) writes both.

### Q9. Pitfalls

See §Common Pitfalls (preserve-by-omission set, mate/stalemate after the blunder, missing refutation, guest games, Elo side, board mutation, fingerprint, connection budget, NULL budget vs the 99% bar).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Refutation columns + refutation stamp | Database / Storage | — | Typed nullable columns, metadata-only Alembic revision |
| Refutation stats derivation (prob, rank, reasons) | API / Backend (pure `maia_flaw_stats.py`) | — | Pure, no I/O, unit-testable with the fake policy |
| Post-blunder board + inference | API / Backend (`maia_flaw_scoring.py`) | — | Same off-thread, session-free pass as 247 |
| Go-forward scoring | API / Backend (drain, atomic submit, blob submit post-commit hooks) | Database | No call-site change |
| Reclassify unstamp | API / Backend (`clear_maia_flaws_completed`) | Database | One helper, five callers |
| Refutation backfill | Operator script (dev box) | Database (prod via tunnel) | CPU locally, writes over the tunnel, ≤ 9 connections |
| Coverage verification | Database (read-only SQL via MCP) | Operator | Orchestrator runs it |
| Calibration report | Operator script (read-only) | Database (prod via tunnel) | Reads sample, runs Maia locally, writes markdown |

No browser/frontend involvement.

## Standard Stack

### Core (all already in the repo; nothing to install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| onnxruntime | 1.29.0 (verified `uv run` this session) | Maia-3 inference | Pinned; owner forbids bumps (project memory) |
| numpy | 2.5.2 (verified) | ORT feeds | maia-inference group |
| python-chess | 1.11.2 (verified) | PGN replay, legal moves, push | Project standard |
| SQLAlchemy async + asyncpg | repo versions | Reads/writes, `aliased`, `load_only`, ORM bulk update by PK | Project standard |
| Alembic | repo version | Metadata-only migration | Project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `best_move` at ply+1 | `pv[0]` at ply+1 only | pv is NULL for dedup-transplanted opening plies and exists only at flaw-adjacent rows; `best_move` is the 247-consistent source. Use pv only as fallback |
| Separate stamp | Stamp version | See Q3 |
| `scripts/` report | `analysis/` marimo notebook | analysis venv lacks onnxruntime and app service deps |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 eval lanes (drain / atomic submit / blob submit)        backfill --mode full|refutation
        | commit flaws + evals + best_move                  | md5 shard, batch of 50 games
        v                                                   v
 score_game_flaws_after_apply ---------------------> load_game_maia_inputs (short read session)
                                                      games: pgn, ratings, platform, TC, user_color
                                                      flaws: ply, fen, severity, best@ply, su,
                                                             refutation = COALESCE(best@ply+1, pv0@ply+1)
                                                            |
                                                            v   (no session open, asyncio.to_thread)
                                         boards: in-memory targets  OR  PGN replay (D-05)
                                                            |
                         per flaw: fen guard -> mover Elo (pre-push board.turn, pinned)
                              |                                   |
                              v                                   v  only if severity=2 AND user-side
                     full_policy(pre fen)                post = copy(pre); push(played)
                     -> 8 base values                    no legal moves? -> NULL, no_legal_reply
                     (full mode only)                    refutation NULL/illegal? -> NULL, reason
                                                         full_policy(post fen, same Elo) -> prob, rank
                                                            |
                                                            v
                         write session: advisory locks (ascending) -> fingerprint re-read
                           -> mode check (own stamp) -> bulk update by PK -> stamp(s) -> commit

 reclassify (no Maia): _classify_and_fill_oracle diff/upsert (Maia keys omitted) -> clear BOTH stamps
                                                            |
                                                            v
                                         next backfill run re-scores (full mode)

 calibration script (read-only): md5 game sample -> positions/flaws -> _run_all_moves_pass
   -> case (allowed/pure/mixed) -> findability grid -> eval band -> hazard window fit
   -> herring runs -> supply extrapolation -> Maia on sampled Good moves -> markdown + spot-check
```

### Recommended Project Structure
```
alembic/versions/2026111x_..._phase_248_maia_refutation.py   # 2 game_flaws cols + games stamp
app/models/game_flaw.py           # maia_refutation_prob / maia_refutation_rank
app/models/game.py                # maia_refutation_completed_at
app/services/maia_flaw_stats.py   # compute_refutation_stats, reasons
app/services/maia_flaw_scoring.py # inputs, fingerprint, refutation pass, modes
app/repositories/game_flaws_repository.py  # MAIA_REFUTATION_COLUMNS, mark/clear stamps
scripts/backfill_maia_flaws.py    # --mode, selector, status, report fields
scripts/blunder_check_calibration.py       # new, read-only report
tests/services/test_maia_flaw_stats.py, test_maia_flaw_scoring.py, test_full_eval_drain.py
tests/test_eval_worker_endpoints.py, tests/scripts/test_backfill_maia_flaws.py
tests/scripts/test_blunder_check_calibration.py               # pure-function tests
reports/blunder-check/                     # dated report + spot-check sample
```

### Pattern 1: Refutation derivation (sketch)
```python
# Source: extends app/services/maia_flaw_scoring.py (Phase 247) — names marked [ASSUMED] are proposals
def _is_user_blunder(inputs: GameMaiaInputs, flaw: FlawMaiaInput) -> bool:
    if flaw.severity != _SEVERITY_INT["blunder"]:
        return False
    return mover_is_white_at_ply(flaw.ply) == (inputs.user_color == "white")


def _derive_refutation(
    pre_board: chess.Board, played_uci: str, elo: float, refutation_uci: str | None
) -> tuple[MaiaRefutationStats, MaiaReason | None]:
    post = pre_board.copy(stack=False)   # never mutate the drain's in-memory target board
    post.push_uci(played_uci)
    if not any(post.legal_moves):        # the blunder stalemated (or mated) the opponent
        return null_refutation_stats(), "no_legal_reply"
    if refutation_uci is None:
        return null_refutation_stats(), "refutation_missing"
    if chess.Move.from_uci(refutation_uci) not in post.legal_moves:
        return null_refutation_stats(), "refutation_not_legal"   # no inference wasted
    probs = full_policy(post.fen(), elo)  # elo = blunderer's pinned Elo (pre-push board.turn)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
    return compute_refutation_stats(probs, refutation_uci)
```
Note `chess.Move.from_uci` raises `InvalidMoveError` on a malformed string; wrap or validate (the column is `String(5)` UCI, so practically safe, but a defensive guard keeps a bad row from failing the whole game).

### Pattern 2: Fingerprint select with the ply+1 join
```python
# Source: extends _flaw_fingerprint_select (maia_flaw_scoring.py:127-154)
gp_next = aliased(GamePosition)
refutation_uci = sa.func.coalesce(
    gp_next.best_move,
    sa.func.nullif(sa.func.split_part(gp_next.pv, REFUTATION_PV_SEPARATOR, 1), ""),
)
stmt = (
    sa.select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.fen, GameFlaw.severity,
              GamePosition.best_move, second_uci, refutation_uci)
    .select_from(GameFlaw)
    .outerjoin(GamePosition, sa.and_(GamePosition.game_id == GameFlaw.game_id,
                                     GamePosition.user_id == GameFlaw.user_id,
                                     GamePosition.ply == GameFlaw.ply))
    .outerjoin(gp_next, sa.and_(gp_next.game_id == GameFlaw.game_id,
                                gp_next.user_id == GameFlaw.user_id,
                                gp_next.ply == GameFlaw.ply + 1))
    .where(GameFlaw.game_id.in_(list(game_ids)))
    .order_by(GameFlaw.game_id, GameFlaw.ply)
)
```
`REFUTATION_PV_SEPARATOR = " "` (pv is "space-joined" per game_position.py:168). To distinguish a pv-fallback hit for the report counter, also select `gp_next.best_move` raw (or count fallback as `best is NULL and refutation is not NULL`).

### Pattern 3: Write modes
- `ScoringMode = Literal["full", "refutation"]` [ASSUMED name].
- Full: row keys = PK + `MAIA_FLAW_COLUMNS` + `MAIA_REFUTATION_COLUMNS` for every flaw (refutation None out of scope, which also wipes any stale value left on a survivor that was downgraded from blunder); stamp both.
- Refutation: row keys = PK + `MAIA_REFUTATION_COLUMNS` for in-scope rows only; stamp the refutation column only.
- Both: ascending advisory locks, fingerprint equality, `require_unstamped` on the mode's own stamp, `MAX_GAMES_PER_WRITE_TXN = 50`.

### Pattern 4: Operator runbook (orchestrator inline, never an executor)
1. After 247-07's full run ends: owner go-ahead → merge → deploy (`bin/deploy.sh`), migration applies; verify 3 new columns via MCP and the startup log line "Maia ONNX session loaded".
2. Live-lane proof: a game analyzed after the deploy shows both stamps within seconds of `full_evals_completed_at` (247-06 could not prove this because only guest games were pending; check again).
3. Tracer slice: `--db prod --mode refutation --shard 0 --num-shards 9 --limit 50` in the foreground, verify via MCP.
4. Full run detached: `setsid nohup bash -c 'PYTHONUNBUFFERED=1 uv run python -u scripts/backfill_maia_flaws.py --db prod --mode refutation --workers 9 --report-dir temp/maia-refutation-backfill; echo EXIT=$?' >> temp/maia-refutation-backfill/prod-full.log 2>&1 < /dev/null & disown`; Monitor polls `--status --mode refutation` and `kill -0 <python3 PID>` / `EXIT=` (never `pgrep -f` with the pattern inside the monitor).
5. Catch-up: `--mode full` (games unstamped meanwhile) then `--mode refutation`.
6. Coverage SQL (below) via MCP; bucket the NULL remainder; commit reports.
7. Calibration report run (one connection, after all backfills), commit report and spot-check file.

### Coverage SQL (D-11)
```sql
WITH b AS (
  SELECT f.maia_refutation_prob, f.maia_played_prob,
         g.maia_refutation_completed_at AS stamp,
         g.full_pv_completed_at IS NULL AS pv_pending,
         CASE WHEN f.ply % 2 = 0 THEN g.white_rating ELSE g.black_rating END AS mover_rating,
         gp1.best_move, gp1.pv, gp1.move_san
  FROM game_flaws f
  JOIN games g ON g.id = f.game_id
  LEFT JOIN game_positions gp1
    ON gp1.user_id = f.user_id AND gp1.game_id = f.game_id AND gp1.ply = f.ply + 1
  WHERE g.full_evals_completed_at IS NOT NULL
    AND f.severity = 2
    AND CASE WHEN f.ply % 2 = 0 THEN g.user_color = 'white' ELSE g.user_color = 'black' END
)
SELECT count(*) AS denom,
  count(*) FILTER (WHERE maia_refutation_prob IS NOT NULL) AS scored,
  round(100.0 * count(*) FILTER (WHERE maia_refutation_prob IS NOT NULL) / NULLIF(count(*), 0), 3) AS pct_scored,
  count(*) FILTER (WHERE maia_refutation_prob IS NULL AND stamp IS NULL) AS null_unstamped,
  count(*) FILTER (WHERE maia_refutation_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NULL) AS null_no_rating,
  count(*) FILTER (WHERE maia_refutation_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NOT NULL
                     AND best_move IS NULL AND pv IS NULL AND move_san IS NULL) AS null_terminal_no_pv,
  count(*) FILTER (WHERE maia_refutation_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NOT NULL
                     AND best_move IS NULL AND pv IS NULL AND move_san IS NOT NULL AND pv_pending) AS null_pv_pending,
  count(*) FILTER (WHERE maia_refutation_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NOT NULL
                     AND (best_move IS NOT NULL OR pv IS NOT NULL)) AS null_other
FROM b;
```
The inline parity mirrors `is_opponent_expr` (acceptable for an ad-hoc MCP query, as 247 Pattern 6 did; code uses the helper). Split `null_other` with the shard reports' reason counters (`no_legal_reply`, `refutation_not_legal`, `fen_mismatch`, `ply_beyond_mainline`, `pgn_unparseable`, `played_not_legal`). Expect a long-running seq scan of `game_flaws` (11 GB); run once, off-peak.

### Anti-Patterns to Avoid
- **Adding refutation keys to `flaw_record_to_row` or `FLAW_BLOB_AND_TACTIC_COLUMNS`:** breaks preserve-by-omission (D-08). Keep a separate `MAIA_REFUTATION_COLUMNS` tuple.
- **Elo from the post-push board:** `post.turn` is the opponent; D-04 wants the blunderer's rating.
- **Pushing onto the target's own board:** `boards_from_targets` hands out the drain's live `t.board` objects; always `copy(stack=False)` first.
- **Reading the refutation from `game_positions` at the flaw ply** (that is the user's best move, i.e. `maia_best_*`) or deriving the post-blunder position from `game_flaws.fen` (board_fen only).
- **Inline `ply % 2` in app code or the selector:** use `mover_is_white_at_ply` / `is_opponent_expr`.
- **Running the 248 backfill while 247-07 runs** or raising shards above 9 (prod connection budget).
- **Running the report on prod with a read-write engine:** set `default_transaction_read_only` on the connection.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Expected score / Good judgement | own sigmoid or drop threshold | `_run_all_moves_pass` (+ `_ply_to_es`) | Same severity ladder (incl. mate ladder) the stored flaws came from |
| Elo conversion | own normalization | `pinned_elo_for_mover` | Board parity, 247 D-03 |
| Legal-move softmax | own masking | `maia_engine.full_policy` / `mask_and_softmax` | Parity-verified |
| Rank | new rank code | `maia_flaw_stats._rank` / `RANK_BASE` | Same tie semantics as 247 (D-01) |
| User-side test | `ply % 2` | `mover_is_white_at_ply`, `is_opponent_expr` | Single source; a prior off-by-one lived there |
| Per-game write serialization | row locks | `_lock_games_ascending` + fingerprint re-read | Existing, deadlock-free |
| Shard split | rank windows / Python `hash()` | `SHARD_RESIDUE_SQL` md5 residue | Stable under table growth |
| DB URLs | DSNs in code | `db_url_for_target` | `.env` single source, never printed |

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | prod `game_flaws` ~2.3M user-side blunders need 2 values; prod `games` (~1.03M with flaws) need the new stamp; 247's `maia_flaws_completed_at` being filled by 247-07 right now | Migration + `--mode refutation` backfill after 247-07; catch-up both modes |
| Live service config | none (go-forward gated by Maia availability) | none |
| OS-registered state | the running 247-07 backfill (setsid process group, parent PID 3148890) and its Monitor | Do not start 248 prod runs until it exits; don't `pkill -f` |
| Secrets/env vars | `DATABASE_URL_PROD` etc. in `.env` (secret-read hook; never read or print) | none; scripts use `db_url_for_target` |
| Build artifacts | prod image already has the maia-inference group; benchmark-lane backend on :8001 runs the main checkout (needs `bin/benchmark_db.sh start` before restart after the migration) | Deploy; note for benchmark lane |

## Common Pitfalls

### Pitfall 1: The 99% coverage bar may be unreachable with `best_move` alone
**What goes wrong:** the NULL remainder exceeds 1%. **Why:** (a) terminal-ply blunders have no `best_move` at ply+1 (dev: 0.7% of engine-game and 1.0% of lichess-game user blunders); lichess terminal rows have no pv either; (b) mover rating NULL (prod 247 S4: 32,113 of 7,611,640 flaws, 0.42%); (c) lichess games whose MultiPV pass has not run (`full_pv_completed_at IS NULL`) have no ply+1 `best_move`; 247 S3 found `best_null` on 0.9% of sampled flaws at the flaw ply. Sum can reach ~1.5-2%. **How to avoid:** use the pv fallback; run the Wave-0 prod probe (Open Question 1) BEFORE locking the bar; if structural NULLs exceed 1%, ask the owner whether the denominator excludes them (terminal-without-PV, no rating) or the bar is restated. **Warning sign:** `null_terminal_no_pv + null_no_rating + null_pv_pending` > 1% of denom.

### Pitfall 2: Elo from the wrong side
**What goes wrong:** Maia is conditioned on the opponent's rating. **Why:** the post-blunder board has the opponent to move. **How to avoid:** compute Elo once from the pre-push board (existing `_derive_flaw_stats` logic) and pass it in; test with different white/black ratings and a spy on `full_policy`'s `elo` argument for both user colors.

### Pitfall 3: Preserve-by-omission set (D-08)
**What goes wrong:** a no-Maia reclassify nulls refutation values on surviving rows, or survivors keep stale values forever. **Why:** `flaw_record_to_row` must never emit Maia keys; the 4-way diff/upsert leaves absent keys untouched (247-03 mutation proof). **How to avoid:** separate `MAIA_REFUTATION_COLUMNS` tuple, never added to `flaw_record_to_row` or `FLAW_BLOB_AND_TACTIC_COLUMNS`; `clear_maia_flaws_completed` clears both stamps; full mode writes refutation None for every out-of-scope row (clears a survivor downgraded from blunder to mistake). **Warning sign:** `maia_refutation_prob IS NOT NULL AND (severity <> 2 OR opponent-side)` rows after a catch-up.

### Pitfall 4: Mate or stalemate after the blunder
**What goes wrong:** inference on a position with no legal moves (`mask_and_softmax` returns `{}` [VERIFIED: app/services/maia_encoding.py:195-196, read via Bash]). Mate cannot be a user blunder, but stalemating a won position is one. **How to avoid:** `not any(post.legal_moves)` → pair NULL, reason `no_legal_reply`, game still stamped. **Warning sign:** dev probe saw 0 of 800 such cases; expect a tiny count on prod.

### Pitfall 5: Missing or illegal refutation
**What goes wrong:** `best_move` NULL (terminal row, pending MultiPV pass, engine hole) or illegal in the post board (stale opening-cache transplant). **How to avoid:** pv fallback, legality check before inference, counted reasons, game still stamped (selector terminates). Never fall back to Maia's own top move or any engine call.

### Pitfall 6: Guest games
**What goes wrong:** none in scoring (guests scored like everyone else, CONTEXT discretion). **Report:** exclude guests from per-user supply (`users.is_guest`, model line 38), keep them in coverage (they are in the denominator only if fully evaluated, which guests mostly are not).

### Pitfall 7: Fingerprint blind to the new inputs
**What goes wrong:** a concurrent apply changes severity or the ply+1 `best_move` between read and write and the stale pair is written and stamped. **How to avoid:** add `severity` and `refutation_uci` to the fingerprint; test with a mid-flight ply+1 `best_move` change → `fingerprint_changed`.

### Pitfall 8: Concurrent backfills / connection exhaustion
**What goes wrong:** TooManyConnections in the app (happened 2026-11-09 with 14 shards). **How to avoid:** never overlap with 247-07; ≤ 9 operator connections total, including the report and `--status` polls (each `--status` opens one more connection briefly).

### Pitfall 9: Report misreads per-ply evals
**What goes wrong:** ES off by one ply, or Good judged differently from the stored flaws. **How to avoid:** reuse `_run_all_moves_pass` on rows ordered by ply from 0 with no gaps; run the stored-vs-recomputed flaw control; restrict to fully evaluated games; split results by provenance.

### Pitfall 10: Python 3.14 stdout buffering and long runs
Use `PYTHONUNBUFFERED=1 ... python -u`, watch `--status` counts, setsid + Monitor, commit same-day reports before a re-run (the report filename must include the mode so it never overwrites 247's).

## Code Examples

### Pure refutation stats
```python
# Source: pattern of compute_maia_flaw_stats (app/services/maia_flaw_stats.py:112-150)
class MaiaRefutationStats(TypedDict):
    maia_refutation_prob: float | None
    maia_refutation_rank: int | None


def compute_refutation_stats(
    probs: Mapping[str, float], refutation_uci: str | None
) -> tuple[MaiaRefutationStats, MaiaReason | None]:
    if not probs:
        return null_refutation_stats(), "no_legal_reply"
    if refutation_uci is None:
        return null_refutation_stats(), "refutation_missing"
    if refutation_uci not in probs:
        return null_refutation_stats(), "refutation_not_legal"
    return (
        MaiaRefutationStats(
            maia_refutation_prob=float(probs[refutation_uci]),
            maia_refutation_rank=int(_rank(probs, refutation_uci)),
        ),
        None,
    )
```

### Miss case (report)
```python
# Source: D-13; INACCURACY_DROP from app/services/flaws_service.py:47
MissCase = Literal["allowed", "pure_miss", "mixed", "unclassified"]

def miss_case(is_miss: bool, es_ref: float | None, es_played: float) -> MissCase:
    if not is_miss:
        return "allowed"
    if es_ref is None:
        return "unclassified"
    return "pure_miss" if es_played >= es_ref - INACCURACY_DROP else "mixed"
```

### Read-only report engine
```python
engine = create_async_engine(
    db_url_for_target(db), pool_size=1, max_overflow=0,
    connect_args={"server_settings": {"default_transaction_read_only": "on"}},
)
```
(`server_settings` is asyncpg's connect option for session GUCs [ASSUMED from asyncpg knowledge; verify with a dev smoke that an INSERT fails].)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Face-palm test (a): cap the played move's Maia probability | Findability of the punishment: refutation prob/rank at the user's rating | Seed review 2026-11-09 | This phase stores the refutation pair |
| Runtime Maia per drill window | Precomputed columns + SQL selection | Owner 2026-11-09 | Backfill + go-forward |
| Raw mover rating in the calibration probe | `pinned_elo_for_mover` buckets | D-14 | Report recomputes buckets |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Names `maia_refutation_completed_at`, `ScoringMode`, reasons `no_legal_reply` / `refutation_missing` / `refutation_not_legal`, `MAIA_REFUTATION_COLUMNS` | Q2, Q3 | Cosmetic; planner may rename |
| A2 | Refutation backfill ≈ 8-10 h wall at 9 shards | Q4 | Scheduling only; measure on the tracer slice |
| A3 | Prod user-side blunder NULL budget ~1.5-2% without pv fallback (extrapolated from dev and 247 S3/S4) | Pitfall 1 | Could make the D-11 99% bar fail; probe first |
| A4 | 247-07 run 3 ETA ≈ 23:30 UTC 2026-11-09 (linear extrapolation of shard progress) | Q5 | Ordering only |
| A5 | asyncpg `server_settings` makes the report engine read-only | Code Examples | Verify with a dev smoke |
| A6 | Report directory `reports/blunder-check/` and file names | Q6 | Cosmetic |
| A7 | Supply per user by extrapolating per-bucket pass rates onto exact per-user counts is acceptable to the owner | Q6 | Owner may want exact per-user supply on a user sample instead |
| A8 | The `pv[0]` fallback counts as "Stockfish's best move after the blunder" for D-02 | Q1 | If the owner rejects it, terminal-ply engine blunders stay NULL (~0.7% of engine-game user blunders) |

## Open Questions

1. **Can the 99% bar be met?**
   - What we know: dev buckets (terminal 0.7-1.0%, MultiPV-pending lichess games, no rating 0.42% of all prod flaws).
   - What's unclear: prod shares for user-side blunders specifically.
   - Recommendation: Wave-0 read-only MCP probe on prod (orchestrator; 2% `TABLESAMPLE SYSTEM` of `game_flaws` joined to `games` and `game_positions` at ply+1): shares of user-side blunders in fully evaluated games with (a) mover rating NULL, (b) ply+1 terminal (`move_san IS NULL`) without `best_move`, split by pv present, (c) non-terminal `best_move` NULL split by `full_pv_completed_at`. If (a)+(b without pv)+(c) > 1%, take it to the owner before the plan locks D-11's denominator.
2. **pv fallback (A8):** recommend yes; owner may confirm in planning.
3. **Report refresh after the selection phase changes constants:** out of scope; the script should be re-runnable with `--date`/report-dir flags.
4. **Tier-4 blob submit re-scoring the refutation:** acceptable cost; if the owner wants to avoid it, a `mode="base_only"` would be needed, which complicates the stamp semantics. Recommend not optimizing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev Postgres (docker `flawchess-dev-db-1`, :5432) | tests, dev smoke | ✓ | PG 18, alembic head `a7d3f1c9e247` | — |
| Benchmark DB (:5433) | not needed (D-19) | ✓ | — | — |
| Prod tunnel (:15432) | backfill, report | ✓ (listening; in use by 247-07) | — | `bin/prod_db_tunnel.sh` |
| onnxruntime / numpy / python-chess | scorer, report | ✓ | 1.29.0 / 2.5.2 / 1.11.2 | — |
| Dev CPU | backfill | 8 physical cores (16 threads) | — | none; serialize runs |
| flawchess-prod-db MCP | coverage SQL, probes | not available to subagents (project memory) | — | orchestrator runs them |

**Missing dependencies with no fallback:** none. **Blocking:** the CPU and connection budget is occupied by 247-07 until it ends.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist), real PostgreSQL per worker (`tests/conftest.py` template clone) |
| Config file | `pyproject.toml` / `tests/conftest.py` |
| Quick run command | `uv run pytest tests/services/test_maia_flaw_stats.py tests/services/test_maia_flaw_scoring.py tests/scripts/test_backfill_maia_flaws.py -x` |
| Full suite command | `uv run pytest -n auto -x` (plus one serial run before release, project memory) |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-01 | columns REAL/SMALLINT/TIMESTAMPTZ nullable, no default | migration + schema test | `uv run alembic upgrade head && uv run alembic check`; extend `test_schema_maia_columns_typed_nullable` | ✅ extend |
| D-01 | rank ties / strict-greater | unit | `pytest tests/services/test_maia_flaw_stats.py -k refutation` | ✅ extend |
| D-02 | refutation from ply+1 `best_move`, pv fallback when NULL, illegal → reason | DB unit with `fake_full_policy` | `pytest tests/services/test_maia_flaw_scoring.py -k refutation` | ✅ extend |
| D-03 | only user-side blunders scored (opponent blunder, user mistake stay NULL), both user colors | DB unit | same | ✅ extend |
| D-04 | `full_policy` elo arg = blunderer's pinned Elo (spy), white and black users | DB unit | same | ✅ extend |
| D-05 | post board from replay/targets (castling/ep exact), target board not mutated | DB unit | same | ✅ extend |
| D-07 | drain, atomic submit, blob submit write refutation + both stamps | integration | `pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k maia` | ✅ extend tracers |
| D-07 | exactly flaws + user_blunders `full_policy` calls | DB unit | `-k one_full_policy_call` | ✅ extend |
| D-08 | no-Maia reclassify keeps survivor refutation, new rows NULL, both stamps cleared; mutation: add key to `flaw_record_to_row` must fail it | DB unit | `pytest tests/services/test_maia_flaw_scoring.py -k reclassify` | ✅ extend |
| D-09 | Maia absent → neither stamp; zero-user-blunder game stamped; fingerprint change on ply+1 best_move → skip | DB unit | `-k stamp or fingerprint` | ✅ extend |
| D-10 | `--mode refutation` selector (base stamped only), writes only 2 cols + new stamp, rerun selects nothing, shard partition, status counts | script test | `pytest tests/scripts/test_backfill_maia_flaws.py` | ✅ extend |
| D-11 | prod coverage ≥ 99.000 with buckets | manual SQL (orchestrator) | Coverage SQL via MCP | n/a |
| D-13..D-16 | miss case boundaries at `INACCURACY_DROP`, hazard weights (0.379/0.279/0.205/0.100/0.037), herring run counting, window fit, cap math | unit (pure) | `pytest tests/scripts/test_blunder_check_calibration.py` | ❌ Wave 0 |
| D-13 | stored-vs-recomputed flaw control ≥ 99% agreement | dev smoke | `uv run python scripts/blunder_check_calibration.py --db dev ...` | ❌ Wave 0 |
| D-17 | arrow-oddness runs with real ORT on a few positions | smoke | dev run with small `--oddness-sample` | ❌ |
| D-18 | report + spot-check written | dev smoke, then prod run | file exists, committed | ❌ |

### Sampling Rate
- **Per task commit:** the quick run command for touched modules.
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) before the squash-merge; prod coverage SQL and committed report before phase completion.

### Wave 0 Gaps
- [ ] `tests/scripts/test_blunder_check_calibration.py`: pure functions of the report (no DB).
- [ ] Prod NULL-budget probe (Open Question 1), orchestrator via MCP.
- [ ] Test fixtures: games with a user blunder as the final move (terminal, pv only), a stalemating blunder, white and black user colors with distinct ratings, opponent blunder at the adjacent ply. Use a new unique `_TEST_USER_ID` (e.g. `248_001`, grep for collisions) and `finally` cleanup (tier-3 lottery isolation, project memory); scope backfill tests with `--user-id`.
- [ ] Mutation proofs per 247 practice: drop the user-side check, use `post.turn` for Elo, drop `refutation_uci` from the fingerprint, add a refutation key to `flaw_record_to_row`, clear only the base stamp; each must fail a test.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no (no new endpoint; existing hooks only) | — |
| V5 Input Validation | yes (worker-supplied `best_move`/`pv` are used as dict keys into a server-computed legal policy) | legality check against `post.legal_moves` before use; malformed UCI guarded |
| V6 Cryptography | no | md5 only as a non-security shard hash |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Concurrent writers overwrite each other | Tampering | per-game advisory locks + fingerprint re-read (existing) |
| Operator script writes to the wrong DB | Tampering | `--db` choices, banner prints `current_database()`/server, URL never printed (existing) |
| Report script writes to prod | Tampering | read-only session setting on the report engine |
| App starved of DB connections | Denial of service | ≤ 9 operator connections; no overlapping runs |
| Event loop starvation in lanes | Denial of service | inference in `asyncio.to_thread` with no session open (existing) |

## Sources

### Primary (HIGH confidence)
- Codebase, read this session: `app/services/maia_flaw_scoring.py`, `scripts/backfill_maia_flaws.py` (Read tool, full); `app/services/flaws_service.py`, `app/services/eval_utils.py`, `app/repositories/query_utils.py`, `app/repositories/game_flaws_repository.py`, `app/models/game_position.py`, `app/models/game.py`, `app/services/maia_flaw_stats.py`, `app/services/eval_apply.py` (Read for quoted ranges, Bash for surrounding context); `app/services/maia_engine.py`, `app/services/eval_entry.py`, `app/services/best_move_candidates.py`, `app/routers/eval_remote.py`, `app/services/eval_drain.py`, alembic 247 migration (Bash).
- Dev DB (read-only psql and a scratchpad replay probe using `replay_flaw_boards`): refutation coverage, legality, NULL causes.
- Phase 247 artifacts: CONTEXT, RESEARCH (Q1, Pattern 6), SUMMARY 01-06, PLAN 07; `temp/maia-flaws-backfill/prod-full.log` and shard JSONs; `reports/maia-flaws-backfill/prod-coverage.md`.
- `.planning/notes/eval-completion-columns.md`; seed SEED-261108-dk0.

### Secondary (MEDIUM confidence)
- Project memory files (prod max_connections, eval_cp conventions, long operator runs, expected-score refit).

### Tertiary (LOW confidence)
- Run-time and NULL-budget extrapolations (Assumptions A2-A4).

## Metadata

**Confidence breakdown:**
- Refutation source (D-02): HIGH, proven on 800 dev rows across both populations with controls.
- Scorer/backfill design: HIGH, follows the 247 code read this session.
- Completion signal: HIGH (design reasoning over verified code).
- Prod NULL budget, run time, 247-07 ETA: MEDIUM/LOW (extrapolated).
- Calibration methodology: MEDIUM-HIGH (functions verified; sampling choices are recommendations).

**Research date:** 2026-11-09
**Valid until:** 2026-11-23 (247-07 status changes within hours; code facts stable)
