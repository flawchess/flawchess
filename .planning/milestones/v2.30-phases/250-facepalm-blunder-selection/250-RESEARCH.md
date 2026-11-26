# Phase 250: Facepalm-Blunder Selection - Research

**Researched:** 2026-11-13
**Domain:** Brownfield backend integration: Maia post-apply scorer, pure line-material count, logistic score, SQL selection, sharded resumable backfill, blunder-check composition
**Confidence:** HIGH for code integration (every claim below was read in the code this session); MEDIUM for the fit procedure and the D-14 level helper (design recommendations, no owner decision yet)

<user_constraints>
## User Constraints (from CONTEXT.md)

`250-CONTEXT.md` (revised 2026-11-13, commit 5b4d117ca adds D-18 and the new Status) is the coverage contract. Its
decisions are copied here in substance; the planner must read the file itself for the exact wording.

### Status (verbatim)
"Un-parked (owner, 2026-11-13): plan and build now, including the prod backfill. Nothing in this phase waits for the
short-stored-line repair (Phase 252). Instead the line-dependent values are recomputed once that repair has finished
on prod (D-18): the line losses, the mate ply and `facepalm_score`. Until then they are computed from the lines as
stored, and the score coefficients are the fit on those lines."

### Locked Decisions
- **D-01** One `facepalm_score` in [0, 1] per user blunder at the mover's level; qualifies when `>= FACEPALM_SCORE_MIN`.
  No special case for missed punishments; replaces 249 D-06 and overturns 249 D-08. Logistic regression on the owner
  labels; coefficients are named constants in app code; the fit lives in a re-runnable script under
  `scripts/blunder_check/`. Inputs: `ln(maia_played_prob + 0.01)`, reply spread (= `exp(entropy)` of the FULL Maia
  policy at ply+1 at the blunderer's pinned Elo, the `maia_effective_moves` formula one ply later, no truncation), and
  the line material loss at `LINE_DEPTH` (3), capped (5), mate within depth = large loss (+5). Provisional
  coefficients (old count, truncated spread): -0.71 / -0.69 / +0.32, placeholders, must be refit; compare against raw
  played probability with a binary "loses >= 2 or mate" input. Starting threshold 0.7, final value set after the
  refit on repaired lines. A ranking, not a probability: no copy may present it as a share of peers.
- **D-02** Material count = `capture_loss` in `temp/blunder-check/refine.py`, rewritten as tested app code: values
  1/3/3/5/9, captures only (promotions are not material), the blunder's own capture counts for the blunderer, the
  blunderer's recapture at depth + 1 counts, an opponent capture of a piece the blunderer's previous line move placed
  without capturing is ignored, a line ending on an opponent capture before depth + 1 gets a static-exchange
  recapture credit, no stored line = NULL score (does not qualify).
- **D-03** False alarms are worse than misses; tune for share fair among passers.
- **D-04** Named constants next to the blunder-check selection constants: `FACEPALM_SCORE_MIN`, coefficients,
  `LINE_DEPTH`, material cap, mate value. One depth for all ratings.
- **D-05** Store raw facts + derived score on `game_flaws`, nullable (NULL = not scored): `maia_reply_spread` REAL;
  net line loss at depths 1, 3, 5, 7, 9 (five SMALLINT) and the mate ply (SMALLINT, NULL = no mate); a depth the line
  does not reach is NULL unless the mate or recapture-credit rule settles it; `facepalm_score` REAL. The predicate
  must stay a plain SQL filter on `game_flaws`.
- **D-06** Scope: user-side blunders only (severity blunder, mover = game's user).
- **D-07** No Stockfish, no worker lane: reply spread is one Maia inference at ply+1 in `score_game_flaws_after_apply`;
  line loss is a pure replay of the stored line.
- **D-08** Backfill script for ~2.3M user blunders, `scripts/backfill_maia_flaws.py` pattern, same scorer as the hook.
- **D-09** Selection swap in `blunder_check_candidates.py` and `blunder_check_repository.py`; other 249 decisions
  stand (Good bar, eval band, no repeats) except supply order and composition.
- **D-10** Re-run calibration and spot-check on prod; report supply per rating band, own and foreign (+-150).
- **D-11** Keep `maia_played_prob`, drop the other nine Maia columns once the new selection is live and checked on
  prod; drop is the last plan; stop computing them in the hook at the same time; check SEED-261110-cqk first.
- **D-12** Window source drawn independently per window, one third each: herring / own blunder / foreign blunder;
  probabilities are named constants; replaces 249 D-09 and D-11.
- **D-13** Foreign blunders: mover's rating at game time within `FOREIGN_RATING_BAND` (150) of the user's level;
  rating only, no TC match.
- **D-14** User level = lichess-blitz-normalised pinned Elo of the user's most-played time control; reuse
  `EloSourceRow`; planner to confirm it fits.
- **D-15** No own supply (no analysed games, or own unserved supply used up) -> foreign in place of own, same path.
- **D-16** Herrings follow the same own/foreign ratio as blunders; fall back to foreign without own supply.
- Own vs foreign stays recorded per window; copy never says "your move" on a foreign game.
- **D-17** A sequence is shown to a user once. The false-alarm exception is removed: a blunder window that ended on a
  false alarm before the blunder no longer returns to the pool. This phase removes that code path.
- **D-18** Line-only recompute pass once Phase 252's prod pv repair is complete: recompute line losses (all depths),
  mate ply and `facepalm_score` for every scored user blunder and score blunders that had no stored line before.
  `maia_played_prob` and `maia_reply_spread` are not recomputed. Backfill = two separable passes (Maia pass: reply
  spread; line pass: line losses, mate ply, score). The line pass needs no Maia/engine and must be re-runnable over
  rows that already hold values. The refit is part of D-18 (refit, update constants and `FACEPALM_SCORE_MIN`, then
  run the line pass). The first prod backfill may overlap the 252 repair; keep both runs under ~25 operator
  connections (max_connections 50). D-18 and the D-11 drop are the last, separately runnable, human-gated steps.
  Long prod runs are run by the orchestrator, not a backgrounded executor.

### Claude's Discretion
- Column names for the line-loss values and where the scorer module lives.
- Whether the line loss is computed in the same hook as reply spread or at flaw-classification time.
- Backfill shard count and pacing (prod RAM and DB are the binding constraints, not CPU).

### Deferred Ideas (OUT OF SCOPE)
- Library side-panel range filter on the facepalm score.
- Refit from drill answers (only requirement now: the served flaw is identifiable per drill item; Phase 249
  persistence already does this).
- Rating-dependent line depth.
- Short stored engine lines investigation (Phase 252; this phase only handles them with the D-02 recapture credit).
- Stockfish-based legs (expected loss, reply loss, practical loss, worker lane).
- A fresh blind label set; labels above 2000.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs; the coverage contract is D-01..D-18.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Facepalm score, logistic, named constants, re-runnable fit | Pattern 3 (Python + SQL twin), Pattern 6 (numpy IRLS fit), Q6 |
| D-02 | Material count rewritten as app code | Pattern 2, "Reference `capture_loss`" walkthrough, fixture table |
| D-03 | Tune for precision | Fit script reports fair/unfair among passers per threshold (Q6) |
| D-04 | Named constants | Constant placement in Pattern 3 |
| D-05 | Storage shape | Schema section (Q5), NULL rules in Pattern 2 |
| D-06 | User blunders only | `_is_user_blunder` reuse (Q1) |
| D-07 | Spread from the existing ply+1 inference | Q1: zero extra inference in the hook |
| D-08 | Backfill | Q5 + D-18 two-pass design |
| D-09 | Selection swap | Q3 |
| D-10 | Calibration re-run | Q7 |
| D-11 | Drop nine columns | Q8 reader inventory, Pitfall 8 |
| D-12 | Window mix | Q3, Pattern 5 |
| D-13 | Foreign +-150 | Q3 |
| D-14 | User level | Q4 (gap: no most-played-TC helper exists) |
| D-15 | No own supply | Q3 fallback |
| D-16 | Herring origin ratio | Q3 (note: blunder check does NOT use `herring_pool`) |
| D-17 | No false-alarm exception | Q3: `served_for_games` prompted query |
| D-18 | Line-only recompute | Q5 two-pass design, Q9 sequencing, hook catch-up analysis |
</phase_requirements>

## Summary

Everything this phase needs already has a seam. The post-apply Maia hook (`app/services/maia_flaw_scoring.py`)
already runs one `full_policy` call on the post-blunder board for every scorable user blunder (Phase 248's
refutation pair), at the blunderer's pinned Elo. The reply spread is `_effective_moves()` (`maia_flaw_stats.py:97-100`,
`2 ** entropy_bits`, identical to `exp(entropy_nats)`) applied to that same policy, so the hook needs **no extra
inference**; only the guard order changes (spread must be computed even when the refutation UCI is missing or
illegal). The refutation line is already joined by the hook's fingerprint SELECT (`gp_next`, the
`game_positions` row at `ply + 1`), so the line facts need no extra query either. New `game_flaws` columns survive
reclassification by omission exactly like the Phase 247/248 columns, as long as `flaw_record_to_row` never emits
them and `clear_maia_flaws_completed` clears the new stamps.

Selection is game-first, judged in Python (`blunder_check_selection.py`): own games are random picks of fully
evaluated games; foreign games come from `TABLESAMPLE SYSTEM (2%)` with a raw-rating prefilter and an exact pinned-Elo
band. The facepalm predicate drops into `load_blunder_flaws` as a SQL `WHERE facepalm_score >= :min` (plain filter on
`game_flaws`, satisfying D-05) and into an `EXISTS` on the game picks so blunder slots only load games that hold a
qualifying blunder. No new index is needed: the EXISTS rides `ix_game_flaws_game_id`. The D-17 change is one query
(`served_for_games` counts a blunder as served only once its ply was prompted). D-12 replaces the "own first, foreign
fallback" composition with a per-slot draw of source and origin. D-14 has a real gap: the existing `EloSourceRow`
helper is a median over the last 50 games of any time control with no rated/human filter; there is no
most-played-time-control helper.

D-18 changes the backfill from a single "stamp IS NULL" pass to two separable passes: a Maia pass (spread, plus line
facts and score since it replays the board anyway) checkpointed by a new NULL stamp, and a re-runnable line pass
checkpointed by a cutoff timestamp (`stamp IS NULL OR stamp < :cutoff`). The prod Maia pass has a measured analogue:
Phase 248's refutation backfill did one inference per user blunder over 2,293,321 blunders in about 8 hours on 9
shards (8.4 to 8.8 per second per shard).

**Primary recommendation:** compute spread, line facts and score inside the existing hook from the inference and
`gp_next` row it already has; put the line count and the score (Python plus SQL twin) in two new pure modules; filter
selection with `facepalm_score >= FACEPALM_SCORE_MIN` in SQL; build the backfill as `--mode spread` (NULL stamp) and
`--mode line --cutoff <ts>` in `scripts/backfill_maia_flaws.py`; fit with numpy IRLS (no new dependency).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reply spread (Maia at ply+1) | API / Backend (post-commit hook, server Maia) | Operator script (backfill on dev box over tunnel) | D-07: server-side Maia, never workers |
| Line material count | API / Backend (pure function) | Operator script | Pure replay of stored pv; no engine |
| Facepalm score | API / Backend (Python at write) | Database (SQL twin for refit UPDATE) | Refit must be a plain UPDATE (D-05) |
| Qualifying predicate | Database (SQL WHERE on `game_flaws`) | Backend (pure re-check in `_blunder_candidate`) | D-05 "plain SQL filter" |
| Window mix / composition | API / Backend (`blunder_check_selection`) | — | Per-session RNG, server-side answer key (249 D-16) |
| User level (D-14) | API / Backend (repository + pure resolver) | — | Reads the user's games |
| Fit | Operator script (`scripts/blunder_check/`) | — | Offline; output becomes code constants |
| Calibration / spot-check | Operator script (read-only) | — | Existing pattern |

No frontend tier: no API schema or frontend type changes (checked: `app/schemas/blunder_check.py` and
`frontend/src/types/blunderCheck.ts` carry no Maia field; `is_own` already exists end to end).

## Standard Stack

No new packages. Everything is in the lockfile.

| Library | Version (verified) | Purpose | Note |
|---------|-------------------|---------|------|
| python-chess | lockfile (`chess>=1.10.0`) | Board replay, legal moves, SEE | Already used by the scorer |
| onnxruntime | 1.29.0 (`uv run python -c ...` this session) | Maia inference | `maia-inference` group, pinned exactly; never bump (memory) |
| numpy | 2.5.2 (this session) | Logistic fit (IRLS) | `maia-inference` group; also in `analysis/` |
| SQLAlchemy 2 async + Alembic | lockfile | Migration, SQL twin | Existing |

**Not present:** scikit-learn, scipy, statsmodels (`grep -c` over `uv.lock` and `analysis/uv.lock`: 0 each).
Recommendation: do not add them. A 4-parameter logistic regression with 10-fold CV on 163 rows is about 30 lines of
numpy Newton-Raphson (IRLS); run the fit script with `uv run --group maia-inference` (numpy is only in that group).

## Package Legitimacy Audit

No external packages are installed by this phase. Nothing to audit.

**Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## Answers to the planner's questions

### Q1. Scorer and hook (`app/services/maia_flaw_scoring.py`)

Flow today [VERIFIED: maia_flaw_scoring.py:653-692, 509-548, 405-435, 347-383]:
1. `score_game_flaws_after_apply(session_maker, game_id, targets=..., source=...)` returns early unless
   `maia_engine.is_maia_available()`; short read session -> `load_game_maia_inputs`; `asyncio.to_thread(score_game,
   inputs, boards)`; short write session -> `write_game_maia_scores(..., require_unstamped=False)`; never raises
   (Sentry capture, `StaleDataError` logged as expected).
2. `score_game` (full mode) builds one row per flaw via `_flaw_row` -> `_derive_flaw_values`: `_flaw_context` guards
   (`ply_beyond_mainline`, `fen_mismatch`, `no_rating`), one `full_policy(board.fen(), elo)` for the base stats, then
   for a user blunder `_derive_refutation(board, played_uci, elo, refutation_uci)`.
3. `_derive_refutation` copies the pre-board, pushes the played move, returns the null pair before inference on
   `played_not_legal`, `no_legal_reply`, `refutation_missing`, `refutation_not_legal`; otherwise
   `probs = full_policy(post.fen(), elo)` and `compute_refutation_stats(probs, refutation_uci)`. `elo` is the
   BLUNDERER's pinned Elo from the pre-board mover (`_mover_elo`, `board.turn` based, :326-337).
4. `_is_user_blunder` [VERIFIED: :340-344] = `flaw.severity != _SEVERITY_INT["blunder"]` false-guard and
   `mover_is_white_at_ply(flaw.ply) == (inputs.user_color == "white")`. With
   `_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}` [VERIFIED: game_flaws_repository.py:30].

`maia_effective_moves` [VERIFIED: maia_flaw_stats.py:31-32, 97-100]: `_ENTROPY_LOG_BASE: float = 2.0`;
`entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)`; returns `2.0 ** entropy_bits`. This equals
`exp(-sum p ln p)` used in the exploratory `mech.eff`. The policy from `full_policy` covers all legal moves.

**Where the new computation slots in (recommendation):**
- Reply spread: inside the post-blunder branch, from the SAME `probs` the refutation pair uses. Restructure
  `_derive_refutation` into a `_derive_post_blunder(...)` that (a) pushes the move, returns NULL spread on
  `played_not_legal` / `no_legal_reply`, (b) runs `full_policy` once, (c) computes `spread = _effective_moves(probs)`
  always, and (d) computes the refutation pair only if the reply UCI is usable (until the D-11 drop). Spread must no
  longer be blocked by `refutation_missing` / `refutation_not_legal`. Make `_effective_moves` public (or wrap it as
  `reply_spread(probs)`), since D-01 says reuse that formula.
- Line facts: pure function of (pre-board, played UCI, pv at ply+1). The pv is already in the fingerprint SELECT's
  `gp_next` join [VERIFIED: :171-203]; add `gp_next.pv` to the selected columns and a `refutation_pv: str | None`
  field to `FlawMaiaInput`. Compute in the same per-flaw step (pure, no inference).
- Score: pure function of `maia_played_prob` (from the base stats in the same row), spread, line facts.
- Recommendation on the Discretion item: compute everything in the hook, not at classification time. Classification
  (`_classify_and_fill_oracle`) has the pv in memory but not the spread, the score needs both, and one write path with
  one fingerprint is simpler than two writers of one row.

**Reclassification (the 4-way diff/upsert) and why new columns survive** [VERIFIED: eval_apply.py:1126-1209,
1285-1342; game_flaws_repository.py:45-129, 165-195, 344-367]: `_diff_upsert_flaw_rows` builds every row with
`flaw_record_to_row`, which never emits Maia keys, so the UPDATE buckets never SET them (preservation by omission);
new plies insert with them NULL; deleted plies vanish. Then `clear_maia_flaws_completed(session, game.id)` clears
`maia_flaws_completed_at` and `maia_refutation_completed_at` so the next hook/backfill re-scores. What must change:
1. Keep `flaw_record_to_row` free of the new keys; add a `FACEPALM_COLUMNS` tuple next to `MAIA_REFUTATION_COLUMNS`
   with the same "never emit" comment.
2. `clear_maia_flaws_completed` must also clear the two new stamps (single choke point for every reclassifier).
3. Full-mode rows must carry the new keys for EVERY flaw (None out of scope) so a row downgraded from blunder loses a
   stale score (the D-08 precedent: `_flaw_row` docstring :449-452).
4. Extend `FlawFingerprint` with the ply+1 pv (Pitfall 2). Today it is
   `tuple[int, str, str | None, str | None, int, str | None]` = (ply, fen, best_move, missed_pv su, severity,
   refutation UCI) [VERIFIED: :80-82]; the refutation UCI is only the FIRST pv token, and Phase 252 pins the repaired
   pv to the stored best move, so a repaired pv keeps the same first token and would not change the fingerprint.

Hook call sites [VERIFIED: grep]: `app/services/eval_drain.py:1440` (tier-4 blob drain, `blobs_written > 0`) and
`:1736` (full drain), `app/routers/eval_remote.py:988` (`/flaw-blob-submit`, `blobs_written > 0`) and `:1386`
(atomic submit). All call with full mode.

### Q2. Stored line and the reference `capture_loss`

**Storage** [VERIFIED: app/models/game_position.py:168-171; app/services/engine.py:107-109;
maia_flaw_scoring.py:96-98]: `game_positions.pv` is "~12-ply UCI refutation line (space-joined), stored only at the
position AFTER each flawed move (ply = flaw_ply + 1)"; `PV_CAP_PLIES: int = 12`; separator
`REFUTATION_PV_SEPARATOR: str = " "`. It is written by `_write_flaw_pvs` in the classify transaction at ply N and N+1
for every flaw (deduped by ply; the pv at a ply is always the line from that position, so a collision between one
flaw's N and another's N+1 is the same line) [VERIFIED: eval_apply.py:1424-1483]. Read today by the scorer (first
token as refutation fallback), by `blunder_check_selection._refutation_uci` (:414-422) and by the tactic detector.
Depth 9 needs 10 tokens, inside the 12-ply cap.

Dev DB probe (this session, read-only): 17,052 user blunders in fully evaluated games; 11,673 have a pv at ply+1
(median length 12, 2,665 shorter than 4 plies, 8,670 with 10 or more). Prod per the seed: ~7% of sampled user
blunders had no stored line before the 252 repair. Dev coverage is lower than prod, so dev pass rates are not
calibration evidence.

**Ply conventions** (memory + code): ply index 0-based, white moves on even plies (`mover_is_white_at_ply`);
`game_flaws.ply` = the flawed move's ply; the pre-move board is position index `ply` (`replay_flaw_boards` snapshots
BEFORE the push); the `game_positions` row at `ply + 1` holds the position after the blunder, its `best_move` is the
engine's best reply and its `pv` starts with the opponent's reply. Evals are not used by the line count, so the
eval post-move shift trap does not apply, but do not reuse `eval_cp` row offsets from other code here.
`game_flaws.fen` is `board_fen()` only (no castling, en passant or side to move), so the line replay must start from
the PGN-replayed full board (as the scorer already does), never `chess.Board(flaw.fen)`. Castling inside the
refutation line needs the castling rights.

**What `capture_loss(fen_uci, pv, depth)` does** [VERIFIED: temp/blunder-check/refine.py:31-89, mech.py:34, 62-78]:
- Values `VAL = {PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9, KING: 0}`; `victim_value` = 1 for en passant, else
  the captured piece's value, 0 for a non-capture. Promotions add nothing.
- `user = board.turn` on the pre-blunder board; `loss = -victim_value(blunder)` (own capture counts in the
  blunderer's favour); push the blunder.
- Walk at most `depth + 1` pv tokens; stop at the first illegal token (n not incremented). For each legal token,
  `n += 1`; at `n == depth + 1` only a blunderer capture is taken (an opponent move or a quiet move breaks the loop;
  with odd depths token depth+1 is always the blunderer's).
- Opponent move: remember `last_opp_capture_sq` (its square if it captured, else None); add its victim value unless
  it captured on `quiet_user_sq` (the square the blunderer's previous line move went to without capturing: the
  desperado/spite rule); reset `quiet_user_sq`.
- Blunderer move: subtract its victim value; set `quiet_user_sq` to its target if quiet, else None; reset
  `last_opp_capture_sq`.
- After each push: `mated = True` if checkmate, blunderer to move, and `n <= depth`.
- `n == 0` -> None. If `n < depth + 1` and the line ended on an opponent capture with the blunderer to move and not
  mated: `loss -= max(0, best_recapture(board, last_opp_capture_sq))`.
- `best_recapture` / `see` (mech.py:62-78) use a separate table with `KING: 100` to order attackers (least valuable
  first) and return the static-exchange gain of the best recapture. Return value `(loss, mated)`.

**Fitting depths 1/3/5/7/9, mate ply and NULL into app code (recommendation):**
- One pure function, e.g. `line_facts(pre_board, played_uci, pv) -> LineFacts` returning
  `loss_by_depth: dict[int, int | None]` for `LINE_LOSS_DEPTHS = (1, 3, 5, 7, 9)` plus `mate_ply: int | None`.
  Implement as a single walk recording per-ply state, or call a `capture_loss_at(depth)` helper five times (10 plies
  each, negligible cost); the reference semantics must match byte for byte on the fixtures below.
- `mate_ply` = the first line ply n (1 = opponent's first reply) after which the blunderer is checkmated, over the
  whole line, independent of depth. "Mate within depth d" = `mate_ply is not None and mate_ply <= d`.
- NULL rule per depth (D-05): let n = legal plies walked for that depth. The value is settled when `n >= d`, or when
  mate occurs within the walked line, or when the line ended before d on an opponent capture and the recapture credit
  was applied. Otherwise NULL ("line too short to tell"). No pv, an unparseable first token, or `n == 0` -> all NULL.
- Malformed tokens: `chess.Move.from_uci` raises `ValueError` on garbage; worker-supplied strings land in
  `game_positions` (the T-248-01 precedent at maia_flaw_scoring.py:372-377). Treat a `ValueError` like an illegal
  token (stop the walk), never fail the game.

**Fixture values from the reference implementation** (computed this session by re-running the reference logic on the
cached positions in `temp/blunder-check/fens.json`, `pvs.json`, `set6-lines.json`; `n` = legal plies walked,
`cr` = recapture credit applied, `M` = mated within depth):

| # | Label | Old line-3 | d1 | d3 | d5 | d7 | d9 | Note |
|---|-------|-----------|----|----|----|----|----|------|
| 153 | unfair | 3 | 0 | 3 | 3 | 2 | 1 | still passes (piece already hanging) |
| 156 | unfair | 2 | 0 | -3 | -3 | -3 | -4 | desperado rule ignores the Rxe1 loss, credits Rxe1 recapture |
| 165 | unfair | 2 | -1 | 2 | 2 | 2 | 2 | still passes (two-move pin) |
| 170 | unfair | 5 | 0 | 0 | 0 | -9 | -4 | |
| 176 | unfair | 5 | 0 cr | 0 cr | 0 cr | 0 cr | 0 cr | 1-ply line `h7e7`, recapture credit settles every depth |
| 177 | unfair | 5 | -3 | -3 | -3 | -3 | -3 | opponent promotion not counted |
| 13 | fair | 3 | 3 | 0 | 0 | 0 | 0 | dropped by the desperado rule (Bxd2 of a quietly moved piece) |
| 35 | fair | 8 | 0 | 0 | 0 | 0 | 0 | old count was the b1=Q promotion |
| 154 | fair | 4 | 1 | 1 | 2 | 4 | 3 | |
| 184 | fair | 3 | 3 | 0 | -1 | -1 | -1 | |
| 34, 116, 182 | fair | 1 | 1 M | 1 M | ... | | | 1-ply mate-in-1 lines, mate_ply = 1 |
| 108, 162, 168 | fair | 0/-8/0 | 0 M | 0 M | ... | | | mate_ply = 1 |
| 181 | fair | -3 | -3 M | ... | | | | mate_ply = 1 |

These match the seed's statement that the refinements remove #156, #170, #176, #177 and drop #13, #35, #154, #184
from "line 3 >= 2". The positions (full FEN, played UCI, pv) are printed in the scratch run; the executor should copy
them into a committed test fixture module (the `temp/` caches are gitignored and exist on this machine only).
Example rows: #176 `8/p6R/4rkp1/3p1p2/8/P5P1/1P3PK1/8 b - - 0 34`, move `e6e7`, pv `h7e7`;
#13 `rnbqk2r/ppp3pp/4p1n1/3Ppp2/1bP5/2N2N2/P4PPP/R1BQKB1R w KQkq - 0 9`, move `c1g5`,
pv `b4c3 g5d2 c3d2 d1d2 e5e4 f3d4 e6e5 d4b5 a7a6 b5c3 e8g8 h2h4`.

Note on negative values: the count goes below zero (blunderer nets material along the line, -9 at d7 for #170). D-01
only specifies the upper cap; the lower bound is an open fit question (Open Question 2).

### Q3. Selection code

Files as on disk this session. The prompt's "uncommitted Phase 249 UAT edits" are no longer uncommitted: the working
tree is clean and those edits landed as commit 54247f3d7 "fix(blunder-check): judge missed gifts on the position
before the gift" (touches `blunder_check_candidates.py`, `blunder_check_rules.py` and two test files). Everything
below reflects that commit.

**Current constants** [VERIFIED: blunder_check_rules.py:43-80]: `HAZARD: float = 0.265`,
`WINDOW_LENGTHS: tuple[int, ...] = (3, 4, 5)`, `LEAD_IN_PLIES: int = 1`, `MAX_BLUNDER_POSITION: int = 5`,
`REFUTATION_PROB_MIN: float = 0.3`, `BEST_PROB_MIN: float = 0.2`, `ES_BAND_LOW: float = 0.10`,
`ES_BAND_HIGH: float = 0.90`, `BLUNDER_MAX_PRE_EVAL_CP: int = 300`, `BLUNDER_CHECK_SESSION_WINDOWS: int = 6`,
`SAFE_POINTS: int = 1`, `BLUNDER_POINTS: int = 3`.
[VERIFIED: blunder_check_selection.py:57-73]: `OWN_BATCH_GAMES: int = 40`, `MAX_OWN_BATCHES: int = 3`,
`FOREIGN_BATCH_GAMES: int = 40`, `FOREIGN_SAMPLE_PERCENT: float = 2.0`, `FOREIGN_ELO_BANDS: tuple[int, ...] = (100, 200)`,
`FOREIGN_RAW_PREFILTER_MARGIN: int = 500`, `REFERENCE_ELO_GAMES: int = 50`, `MAX_SHAPE_REDRAWS: int = 5`.

**How it works today:**
- Findability (249 D-06): `_blunder_candidate` (candidates.py:179-227) checks severity, user parity, `key_plies`
  (stored best move legal), `prompted_blunder_plies`, early-ply floor, classifier consistency, undecided-position
  rule, `miss_case` (drops "unclassified"), then `findable(case, FindabilityInputs(...), REFUTATION_PROB_MIN,
  BEST_PROB_MIN)` (rules.py:264-288), then window fit.
- Hazard model: `draw_window_shape` (rules.py:250-256): L uniform over `WINDOW_LENGTHS`, blunder at the first
  position whose `rng.random() < HAZARD` fires, else herring. Herring share = mean over L of 0.735^L, about 0.30
  (`hazard_position_weights`, :232-247).
- Supply order: `compose_windows` (selection.py:452-471): draw 6 shapes, `_fill_from_own` (up to 3 random own batches
  of 40 via `pick_own_game_ids`), then only for empty slots `_fill_from_foreign` (reference Elo from
  `recent_rated_games` + `reference_elo`; per band in (100, 200) a `TABLESAMPLE SYSTEM(2)` pick of 40 foreign
  games with raw owner rating within band + 500, exact pinned-Elo band check after load), then `_redraw_and_refill`
  redraws only empty slots up to 5 times over already loaded pools. `assign_windows` (candidates.py:353-378) fills
  slots rarest first, at most one window per game per session.
- No-repeat: `served_for_games` (repository.py:380-419). `prompted` = blunder plies that have an ANSWER row at
  `BlunderCheckAnswer.ply == BlunderCheckWindow.blunder_ply`; `judged_ranges` = (first_ply, last judged ply) per
  served window. Blunder candidates are excluded only via `prompted`; herring runs are excluded via ranges.
- **The false-alarm exception is exactly the `prompted` query**: a window that ended on a false alarm before the
  blunder has no answer row at the blunder ply, so the blunder stays eligible. Test
  `tests/services/test_blunder_check_selection.py::test_repeat_false_alarm_before_blunder_leaves_it_eligible`
  (line 283) asserts the old behaviour.

**What has to change:**
1. **Predicate.** `BlunderFlawRow` / `FlawLike` / `load_blunder_flaws` swap the four Maia fields for
   `facepalm_score: float | None`; `load_blunder_flaws` adds `GameFlaw.facepalm_score >= FACEPALM_SCORE_MIN` to its
   WHERE (D-05 plain SQL filter). Keep a pure re-check in `_blunder_candidate` (`score is not None and score >=
   FACEPALM_SCORE_MIN`) so unit tests cover the boundary without a DB. `findable`, `FindabilityInputs`,
   `REFUTATION_PROB_MIN`, `BEST_PROB_MIN` leave the app at the swap (the report re-exports them via
   `scripts/blunder_check/metrics.py`, so the report changes in the same or the next plan). Keep `miss_case` and the
   window case: it is still persisted (`WindowCase`: `HERRING = 0`, `ALLOWED = 1`, `PURE_MISS = 2`, `MIXED = 3`
   [VERIFIED: app/models/blunder_check.py:52-58]) and the "unclassified" drop is an ES-consistency guard, not a
   findability rule.
2. **D-12 + hazard model.** Draw per slot, independently: source herring / own blunder / foreign blunder with named
   probabilities (1/3 each). Herring origin own vs foreign with the blunders' own share (D-16), i.e.
   `OWN_BLUNDER_SHARE / (OWN_BLUNDER_SHARE + FOREIGN_BLUNDER_SHARE)` = 0.5, so overall herring-own 1/6,
   herring-foreign 1/6. Shape: herring -> `WindowShape(L, None)` with L uniform; blunder -> L uniform and the position
   drawn from the hazard model CONDITIONED on firing within L (P(k | L) proportional to h(1-h)^(k-1), k <= L). This
   keeps D-03's anti-leak property (the position comes from the hazard, never from a picked blunder) and makes the
   herring share exactly the D-12 constant instead of the hazard's ~0.30. Rejection sampling over
   `draw_window_shape` gives the same conditional distribution; closed form is deterministic and testable.
   `hazard_position_weights()["herring_share"]` stops being the session herring share; the report must use the new
   constant.
3. **Filling by origin.** Run `assign_windows` per pool on the slots of that origin; own slots that own supply cannot
   fill (after own batches and redraws) convert to foreign slots (D-15, D-16), same code path for a user with zero
   analysed games. Keep "one window per game per session" across both pools.
4. **D-13.** Replace `FOREIGN_ELO_BANDS = (100, 200)` with one `FOREIGN_RATING_BAND = 150` on the mover's pinned Elo
   (`mover_pinned_elo`, owner side). Keep the raw prefilter margin (chess.com vs lichess scale) and the exact
   pinned check after load. Pinned Elo is clamped to `MAIA_ELO_LADDER_MIN: int = 600` / `MAIA_ELO_LADDER_MAX: int =
   2600` [VERIFIED: app/services/maia_encoding.py:62-63], so users below 600 match the 600-750 clamped band.
5. **Supply yield.** With a ~20% pass rate, random game batches waste work. Add an `EXISTS (SELECT 1 FROM game_flaws
   f WHERE f.game_id = g.id AND f.facepalm_score >= :min)` option to `pick_own_game_ids` and
   `pick_foreign_game_ids` for blunder slots. Keep a plain pick for herring slots: if own qualifying blunders run out,
   own herrings must still be available, and a herring should not be biased toward games that hold a blunder.
   Index check: own pick is index-only on `ix_games_user_full_evals (user_id, id) WHERE full_evals_completed_at IS
   NOT NULL`; foreign pick is a 2% block sample; the EXISTS probes `ix_game_flaws_game_id` (a handful of rows per
   game, `facepalm_score` read from the heap). Dev index list (this session) shows no index needed beyond these.
   `facepalm_score` is NULL on every non user-blunder row, so the EXISTS needs no parity test.
6. **D-17.** In `served_for_games`, replace the answer-joined `prompted_stmt` with "every `blunder_ply` of every
   window served to this user in these games" (`BlunderCheckWindow.blunder_ply IS NOT NULL`), rename
   `prompted` -> `served_blunder_plies` (and `judge_game(prompted_blunder_plies=...)`), invert the test at line 283.
   The `ix_blunder_check_windows_user_game` index already serves it.
7. **D-16 `herring_pool` note.** Blunder check does NOT use `herring_pool` [VERIFIED: grep of
   `blunder_check_*.py` and `blunder_check_repository.py` for `herring_pool`/`HerringPool`: no match]. Its herrings
   are `_herring_runs` of Good, in-band user moves inside the same judged own or foreign games. The "about 91%
   foreign" figure describes the personalized-puzzle pool (`app/models/herring_pool.py` is cross-user). Today's
   blunder-check herrings are mostly OWN (own pool fills first), which is exactly the giveaway D-16 removes.

### Q4. User level (D-14)

What exists:
- `EloSourceRow` + `recent_rated_games` [VERIFIED: blunder_check_repository.py:427-453]: the user's 50 most recent
  games (by `played_at`) with the user-side rating not NULL. No rated/human/platform filter, no time-control grouping.
  `reference_elo` (selection.py:124-139) = median pinned Elo over those rows, all time controls mixed.
- `pinned_elo_for_mover(*, raw_rating, platform, time_control_bucket, is_correspondence)` [VERIFIED:
  best_move_candidates.py:79-125]: lichess-blitz-normalised via `normalize_to_lichess_blitz`, flawchess platform
  passes through, missing bucket or correspondence falls back to raw, then clamped to [600, 2600].
- `current_strength_service.resolve_current_strength` [VERIFIED: current_strength_service.py:41-179] picks the
  MOST RECENTLY played (platform, TC) rung with >= 20 games in 90 days (native lichess-blitz tiebreak), not the
  most-played one; its repository composes `apply_game_filters(rated=True, opponent_type="human",
  platform=None)` and documents that skipping that filter echoed FlawChess bot-game ratings (1340 for prod user 3)
  [VERIFIED: current_strength_repository.py:1-13, 97-115]. UI default only by its own docstring.

What is missing: no helper yields "the pinned Elo of the user's most-played time control". `recent_rated_games`
does not fit D-14 as is (mixes TCs, and includes unrated/bot/pasted games). Recommendation:
- Extend `recent_rated_games` (keep `EloSourceRow`, which already carries `platform`, `time_control_bucket`,
  `time_control_str`, `rating`) to compose `apply_game_filters(..., rated=True, opponent_type="human", platform=None)`
  and read a larger bounded window (e.g. `USER_LEVEL_SCAN_GAMES = 200`, served by `ix_games_user_played_at`).
- New pure resolver `user_level_elo(rows)`: group by `time_control_bucket` (pinned Elo already normalises platforms),
  pick the bucket with the most games (tie: the most recent), median pinned Elo of up to `REFERENCE_ELO_GAMES` most
  recent games in it, skipping correspondence. Fallback chain when nothing qualifies: median pinned over any recent
  rated game, then a named default (Open Question 3).
- Used for both foreign blunders and foreign herrings.

### Q5. Schema and backfill

**Model and migration pattern** [VERIFIED: app/models/game_flaw.py:98-123; alembic 20261108_120000_a7d3f1c9e247,
20261109_120000_c4e9b1d7f248]: Maia columns are `mapped_column(REAL, nullable=True)` /
`mapped_column(SmallInteger, nullable=True)`, `REAL` from `sqlalchemy.dialects.postgresql`; migrations are
metadata-only `op.add_column(..., sa.Column(name, sa.REAL(), nullable=True))` with no default, CHECK, index or data
UPDATE (instant on the 7.6M-row table, documented in the 248 migration docstring). Stamps:
`maia_flaws_completed_at`, `maia_refutation_completed_at` = `DateTime(timezone=True)`, nullable, deliberately not
indexed (game.py:271-288). Latest head on dev: `d5b8e2f1a249` (Phase 249).

Recommended new columns (Claude's discretion on names):
- `game_flaws.maia_reply_spread REAL`, `line_loss_1`, `line_loss_3`, `line_loss_5`, `line_loss_7`, `line_loss_9`
  SMALLINT, `line_mate_ply SMALLINT`, `facepalm_score REAL`.
- `games.facepalm_spread_completed_at TIMESTAMPTZ` (Maia pass checkpoint) and
  `games.facepalm_line_completed_at TIMESTAMPTZ` (line pass checkpoint). Both nullable, no index (precedent), cleared
  by `clear_maia_flaws_completed`.
- A CHECK on `facepalm_score BETWEEN 0 AND 1` is optional; the 247/248 precedent added none to keep the migration
  instant. If added, use `NOT VALID` semantics consciously; recommendation: no CHECK, test the range instead.

**Indexes for selection:** none new (Q3 item 5). A flaw-first foreign query (all users, band, score) would need the
mover's pinned Elo on `game_flaws` and an index; not needed with the game-first TABLESAMPLE design. Revisit only if
the D-10 report shows foreign starvation at the extremes.

**Existing backfill pattern** [VERIFIED: scripts/backfill_maia_flaws.py:91-135, 152-181, 590-645 of the scorer]:
`DEFAULT_WORKERS: int = 9`; shards by `SHARD_RESIDUE_SQL = "('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint"`
modulo `num_shards`; one snapshot of the shard's game ids at start (priority: recent users, newest games); batches of
`MAX_GAMES_PER_WRITE_TXN: int = 50` games; each spawned shard process has its own single-threaded ORT session and a
one-connection pool; the write takes `pg_advisory_xact_lock` per game in ascending order, re-reads the fingerprint
and stamps only unchanged games; `require_unstamped=True` skips games stamped meanwhile. Selector per mode is one of
two constants: `"full": "g.maia_flaws_completed_at IS NULL"`, `"refutation": "g.maia_refutation_completed_at IS NULL
AND g.maia_flaws_completed_at IS NOT NULL"`. Re-running is the resume.

**D-18 two-pass design (recommendation):**
- `--mode spread` (Maia pass): selector `g.facepalm_spread_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT
  NULL` plus the existing "has flaws" EXISTS. Scores only user blunders: one `full_policy` on the post-blunder board
  each, reads `maia_played_prob` from the stored row (no base re-inference; the base stamp guarantees it is current),
  and since it already replays the board it also writes line facts and score. Writes only those keys plus both new
  stamps. Same shape as `--mode refutation` (`_refutation_row`, `ScoringMode`).
- `--mode line --cutoff <ISO timestamp>` (line pass, D-18): no Maia (must not call `start_maia`, must not exit 3 when
  Maia is absent). Selector `(g.facepalm_line_completed_at IS NULL OR g.facepalm_line_completed_at < :cutoff) AND
  g.facepalm_spread_completed_at IS NOT NULL`. Reads stored `maia_played_prob` and `maia_reply_spread`, replays the
  PGN for the exact pre-board, recomputes line facts and score for every user blunder (including ones that had no
  line before), writes those keys plus `facepalm_line_completed_at = now()`. The checkpoint is the cutoff: a crash is
  resumed by re-running with the SAME cutoff (games re-stamped after it are skipped); a later full recompute uses a
  new cutoff. The write's "already stamped" outcome becomes "stamp >= cutoff". The cutoff is a required argument for
  line mode (no default), echoed in the report JSON.
- A score-only refit needs no replay: `UPDATE game_flaws SET facepalm_score = <SQL twin> WHERE maia_reply_spread IS
  NOT NULL` in batches. D-18 as written runs the line pass after the refit, which rewrites the scores anyway, so the
  SQL twin is the tool for any later coefficient-only refit and for the parity test.
- Status queries: counts of user blunders with spread / with score / with score >= threshold, unstamped games per
  stamp; mirror `_fetch_refutation_status`.
- Rename consideration: the script name says "maia"; adding a non-Maia mode is fine (precedent keeps one script),
  but the Maia gate in `_start_maia_and_run` must be mode-aware.

**Sizing (prod):** Phase 248's refutation backfill is the same cost profile (one inference per user blunder):
2,293,321 user blunders, 9 shards, about 8 h, 8.4 to 8.8 per second per shard, 1,026,584 games stamped; game_flaws
13 GB / 7.65M live rows afterwards, autovacuum kept up [CITED: 248-07-SUMMARY.md]. Expect the spread pass at about
8 h on 8-9 shards. The line pass is CPU-cheap (PGN parse + <= 10-ply walk per blunder) and DB-bound: 2-4 shards with
`--throttle-ms` is plenty. The scorer runs on the dev box (Maia locally), only reads/writes cross the tunnel, so prod
RAM is not touched by inference; prod DB load is the constraint.

**Connections:** `docker-compose.yml` sets `max_connections=50` with the app pool up to 20 and documents that a
14-shard Maia backfill exhausted the old limit of 30 (FLAWCHESS-D8) [VERIFIED: docker-compose.yml:43-53]. Each
backfill shard holds one connection; `scripts/repair_short_lines.py` holds one (`pool_size=1, max_overflow=0`,
:1078-1080) and gates itself on a connection rise of `MAX_CONNECTION_RISE: int = 10` over its baseline (:140-141).
That gate matters: starting 8-9 Phase 250 shards while the 252 repair runs will trip the repair's own connection
gate. Recommendation: start the Phase 250 spread pass first and let the 252 repair take its baseline after, or run
the spread pass at <= 8 shards and tell the 252 operator; total operator connections stay around 12 (8 shards +
repair + feeder + psql/MCP), under the ~25 budget.

**Rows whose line changes mid-run:** with the pv added to the fingerprint, a 252 write between read and write makes
the game `fingerprint_changed`: it stays unstamped for the spread pass (picked up on the next run) and keeps its old
line stamp for the line pass (re-covered by D-18). Without the pv in the fingerprint, stale line facts would be
written silently; D-18 still repairs them, but the fingerprint keeps the D-18 pass from being the only safety net.

**Does any existing path re-trigger scoring after a 252 repair?** Partly. `repair_short_lines.py` updates
`game_positions.pv` / `best_move` directly under the game advisory lock and does NOT clear any Maia stamp
[VERIFIED: :449-469, 730]. Its `feed` step NULLs re-walkable blobs (`_null_line_sql`, :1213-1226) and clears
`blobs_completed_at`; the tier-4 lane re-walks them and both blob-submit paths call `score_game_flaws_after_apply`
when `blobs_written > 0` (eval_remote.py:988, eval_drain.py:1440). Once the hook computes line facts, every game the
252 feeder re-walks is re-scored with its repaired line automatically. Not covered: repaired pv rows whose blob does
not match the re-walk predicate (`_rewalk_predicate`, :1161-1176), games the feeder has not reached, and anything the
spread pass scored from an old line while the repair runs. So the hook is an opportunistic catch-up; D-18's line pass
is the authoritative one. Do not add a stamp clear to the 252 repair script (out of scope, and D-18 already covers it).

### Q6. Score fit as code

- **Location:** `scripts/blunder_check/fit_facepalm.py` (fit, CV, report) plus a feature builder
  `scripts/blunder_check/facepalm_features.py`. The app must not import from `scripts/` (249 Discretion note); the
  scripts import the app's pure `line_facts`, `reply_spread` and `facepalm_score`.
- **Inputs:** `reports/blunder-check/leg2-labels-2026-11-11.tsv` [VERIFIED: read this session]: 180 data rows,
  columns `n set elo move link engine_drop expected_loss reply_loss practical_loss played_prob reply_spread
  line_loss3 mate3 label`; sets {1: 20, 2: 20, 3: 20, 4: 20, 5: 50, 6: 50}; labels {1: 105, 0: 68, 0.5: 7}; 12 rows
  have no `line_loss3` (no stored line). The TSV's `reply_spread` is the TRUNCATED value (top 90% / max 8) and
  `line_loss3` is the OLD count, so neither can be used as a fit input. `elo` is the raw rating (e.g. 254), not the
  pinned one. Game and ply come from the `link` column.
- **Positions:** `temp/blunder-check/fens.json` (599 entries keyed `"game_id:ply"`, value
  `"<full FEN>|<played uci>"`, covering sets 1-5 via `peer-legs.json`), `pvs.json` (599, 560 non-null),
  `set6-lines.json` (50, value `[fen|uci, pv]`). Coverage of the 180 labels: 130 in `fens.json`, 50 in set 6, 168
  with a pv. All gitignored, this machine only, and they hold the UNREPAIRED lines.
- **Recommended builder:** `facepalm_features.py --from-cache temp/blunder-check` for the provisional fit (no prod
  read; Maia locally for the full-policy spread at the mover's pinned Elo; needs the platform/TC of each game, which
  the caches lack for sets 1-5 except via `peer-legs.json` fields `rating`, `platform`, `tc_bucket`, `tc_str`), and
  `--db prod` (read-only engine from `scripts/blunder_check/sample.py:make_readonly_engine`) for D-18: reads PGN,
  pv at ply+1, stored `maia_played_prob` and `maia_reply_spread` for the labelled (game_id, ply), computes line facts
  with the app function. Writes a committed TSV (`reports/blunder-check/facepalm-features-<date>.tsv`, game links and
  numbers only), so every fit is reproducible from the repo. The fit reads that TSV.
- **Fit:** numpy IRLS (Newton-Raphson) logistic regression with intercept on the decided labels (0/1), features
  `ln(played_prob + 0.01)`, `reply_spread`, `loss_feature` (mate within `LINE_DEPTH` -> `MATE_LOSS`, else
  `min(line_loss_3, LOSS_CAP)`); rows with NULL score inputs excluded (and counted). Report: coefficients, in-sample
  and 10-fold CV AUC, fair/unfair among passers at thresholds 0.5..0.9, a train-on-sets-1-5 / test-on-set-6 split,
  and the variant D-01 asks for (raw `played_prob` with binary `loses >= 2 or mate`). Deterministic fold assignment
  (seeded). Output a ready-to-paste constants block.
- **Intercept:** CONTEXT gives three slopes but no intercept, so the provisional constants cannot be written from
  CONTEXT; the first run of the fit script produces them (Assumption A1).
- **Where the score is computed:** both. Python at write time (hook and both backfill passes), and a SQL twin
  (`facepalm_score_sql(...) -> ColumnElement[float]`) for the refit UPDATE, with a parity test. Precedent:
  `expected_score_sql` / `expected_score_for` in `app/services/train_pool.py:205-240`. Not a generated column: a
  refit would need `ALTER ... SET EXPRESSION`, a table rewrite of 13 GB.
- **Constants (D-04):** coefficients, `PLAYED_PROB_OFFSET = 0.01`, `LINE_DEPTH = 3`, `LOSS_CAP = 5`, `MATE_LOSS = 5`
  and `LINE_LOSS_DEPTHS` in a new pure module (e.g. `app/services/facepalm_score.py`); `FACEPALM_SCORE_MIN` in
  `blunder_check_rules.py` beside the other selection constants, or re-exported there. Import check: `blunder_check_rules`
  pulls `train_pool`, `flaws_service`, `eval_utils`, none of which import the scorer, so the scorer may import from
  it without a cycle; a separate module still keeps the hook light.

### Q7. Calibration re-run (D-10)

Today [VERIFIED: scripts/blunder_check_calibration.py:1-25; scripts/blunder_check/*.py outlines]: a read-only
sampler (`sample.py`, `default_transaction_read_only = on`, statement timeout) builds `BlunderRecord`s carrying
`maia_played_rank`, `maia_best_prob/rank`, `maia_refutation_prob/rank` (sample.py:176-222, 364-368, 488-552);
`render.py` writes sections "Sample", "Control", "Cases by Elo bucket", "Findability grid" (`findable` at R and X'),
"Eval band", "Window fit", "Herring supply", "Supply per user", "Provenance", "Arrow oddness" (played prob/rank of
Good moves vs blunders; the blunder side reads the STORED `maia_played_rank`, oddness.py:183), "Recommended
constants"; `spot_check.py` draws windows with `draw_window_shape` and prints the refutation or missed best move with
its Maia pair (:438-466). Results can be cached to JSON and re-rendered.

Changes:
- `BlunderRecord` / `_load_flaws`: replace the four best/refutation fields with `facepalm_score`, `maia_reply_spread`,
  `line_loss_3`, `line_mate_ply` (keep `maia_played_prob`); bump the cache version (old caches no longer load).
- "Findability grid" -> "Facepalm score": per Elo bucket, scored share (and NULL reasons: no line, line too short,
  no spread), pass share at `FACEPALM_SCORE_MIN` and at 0.5/0.6/0.8, score quartiles.
- "Supply per user" -> own supply per user AND foreign supply per rating band within +-150 (qualifying blunders of
  other users whose mover pinned Elo is in the band, scaled from the sample), with the extremes (<800, 2400+) called
  out (D-10).
- Window composition stats use the D-12 constants instead of `hazard_position_weights()["herring_share"]`.
- Spot-check: draw with the D-12 mix and print score, played prob, reply spread, line loss 3 and mate ply instead of
  the refutation/best pairs; keep "never say your move" wording rules (T-248-11).
- Arrow oddness: keep the probability AUC (`maia_played_prob` stays); the rank columns read the stored
  `maia_played_rank` and must go at the D-11 drop (or compute ranks in memory for Good moves only).
- `metrics.py` re-exports `findable` / `FindabilityInputs` from the app; remove when the app drops them.
- Tests: `tests/scripts/test_blunder_check_calibration.py` has findability tests (lines 378-398, 944) to rewrite.
- Prod run is read-only and long-ish: orchestrator runs it over the tunnel, never while the spread backfill writes
  (the existing docstring says "only when no backfill is running").

### Q8. Column cleanup (D-11) reader/writer inventory

Every file referencing the nine columns [VERIFIED: grep this session across app, scripts, tests, alembic, frontend,
stories, analysis]:

| File | Role | Columns |
|------|------|---------|
| `app/models/game_flaw.py:107-123` | model | all ten |
| `app/repositories/game_flaws_repository.py:175-195` | `MAIA_FLAW_COLUMNS`, `MAIA_REFUTATION_COLUMNS` | all ten |
| `app/services/maia_flaw_stats.py` | computes (`MaiaFlawStats`, `MaiaRefutationStats`) | all ten |
| `app/services/maia_flaw_scoring.py` | writer (hook, refutation mode, counters at :541-547) | all ten |
| `app/services/blunder_check_candidates.py:79-89, 209-215` | D-06 reader | best/refutation pairs |
| `app/repositories/blunder_check_repository.py:328-364` | D-06 loader | best/refutation pairs |
| `app/services/blunder_check_rules.py:118-124, 264-288` | `FindabilityInputs`, `findable` | (inputs) |
| `scripts/backfill_maia_flaws.py` | full + refutation modes, status (:257, :664) | refutation prob, played prob |
| `scripts/blunder_check/sample.py`, `render.py`, `spot_check.py`, `oddness.py` | calibration | played rank, best/refutation pairs |
| `tests/blunder_check_seed.py:279-282`, `tests/services/test_blunder_check_candidates.py`, `tests/repositories/test_blunder_check_repository.py`, `tests/services/maia_fakes.py`, `tests/services/test_maia_flaw_scoring.py`, `tests/services/test_maia_flaw_stats.py`, `tests/services/test_maia_engine.py:157-163`, `tests/services/test_full_eval_drain.py:3061-3136`, `tests/test_eval_worker_endpoints.py:308-312`, `tests/scripts/test_backfill_maia_flaws.py`, `tests/scripts/test_blunder_check_calibration.py` | tests | various |
| alembic 247/248 migrations | history | leave untouched |

No frontend, `stories/`, `analysis/` or API reader. **SEED-261110-cqk** (status dormant) does not mention Maia at all
[VERIFIED: grep]; no claim on `maia_best_*`. SEED-261108-zkp is closed with the reason "nine of its ten columns are
retired by Phase 250". The `games.maia_refutation_completed_at` stamp is not in the nine; it can stay (harmless) or
go with `--mode refutation`; planner's call, recommend dropping it with the mode for clarity.

### Q9. Sequencing

The old "two steps gated on 252" framing is replaced by D-18. Recommended plan/wave shape:

| Wave | Plan | Content | Gate |
|------|------|---------|------|
| 1 | P01 | Migration (new columns + two stamps), pure `line_facts` (D-02) and `facepalm_score` + SQL twin + constants, fixture tests (TDD) | none |
| 1 | P02 | Feature builder (`--from-cache`, `--db`) + numpy IRLS fit script + tests on a synthetic dataset; run `--from-cache` locally and commit the features TSV and provisional constants | depends on P01 pure functions |
| 2 | P03 | Hook: spread from the existing post-blunder inference, line facts from `gp_next.pv`, score, pv in fingerprint, new keys in full mode, stamps, `clear_maia_flaws_completed`, omission tests | P01, P02 constants |
| 2 | P04 | Backfill `--mode spread` and `--mode line --cutoff`, status, report fields, tests | P03 |
| 3 | P05 | Selection swap: predicate, D-12 draw, per-origin fill, D-13 band, D-14 level helper, D-15/16 fallback, D-17 served query; tests | P01 (column), independent of P03/P04 code |
| 3 | P06 | Calibration + spot-check rewrite (D-10) | P05 constants |
| 4 | P07 (operator, orchestrator-run) | Pre-merge gate, merge, deploy (migration runs at container start), dev backfill smoke, prod `--mode spread` (~8 h, <= 8 shards, may overlap the 252 repair), coverage SQL, prod calibration + spot-check, owner review | human go-ahead |
| 5 | P08 (D-18, human-gated, after 252's prod pv repair is complete) | `facepalm_features --db prod` on repaired lines -> refit -> update constants and `FACEPALM_SCORE_MIN` -> deploy -> `--mode line --cutoff <deploy time>` over all games -> coverage + pass-share check | 252 repair complete + owner |
| 5 | P09 (D-11, human-gated) | Stop computing the nine in the hook, remove readers (scripts, tests, `findable`), retire `--mode refutation`, drop migration | new selection live and checked on prod |

P08 and P09 are independent of each other; both last. Long prod runs (P07 spread pass, P08 line pass, calibration)
must be launched by the orchestrator (`setsid nohup` + Monitor per memory), never from a backgrounded executor
(executor-backgrounded runs die with the executor; executors also die ~40 min into long DB-heavy plans).

## Architecture Patterns

### System Architecture Diagram

```
 eval apply lanes (drain / atomic submit / tier-4 blob submit)          backfill (dev box, tunnel)
        |  commit                                                          |  --mode spread | --mode line --cutoff
        v                                                                  v
 score_game_flaws_after_apply ----> load_game_maia_inputs (games + game_flaws + gp[ply] + gp_next[ply+1] incl. pv)
        |                                       |
        v                                       v
   score_game (thread, no session) -----> per flaw: board replay / targets
        |                                   |-- base policy at ply ---------> maia_played_prob (+ nine until D-11)
        |                                   |-- user blunder? -- post-board policy --> reply spread (+ refutation pair until D-11)
        |                                   |                 `-- line_facts(pre_board, played, pv) --> loss 1/3/5/7/9, mate ply
        |                                   `-- facepalm_score(played_prob, spread, loss3, mate ply)
        v
 write_game_maia_scores: advisory lock (asc) -> re-read fingerprint (now incl. pv) -> UPDATE by PK -> stamps
        |
        v
 game_flaws.facepalm_score  ---- SQL WHERE score >= FACEPALM_SCORE_MIN ---->  blunder-check composer
                                                                               |  per slot: herring / own / foreign (1/3 each)
 user games -> D-14 level (most-played TC, pinned) --------------------------> |  foreign: TABLESAMPLE + pinned band +-150
 blunder_check_windows (served blunder plies, D-17) -------------------------> |  no-repeat
                                                                               v
                                                                        NewWindow rows (is_own recorded)
 refit: features TSV -> numpy IRLS -> constants -> deploy -> line pass (or SQL-twin UPDATE)
```

### Recommended module layout

```
app/services/line_material.py      # pure: capture walk, SEE recapture credit, LineFacts (D-02)
app/services/facepalm_score.py     # pure: constants, facepalm_score(), facepalm_score_sql() (D-01, D-04)
app/services/maia_flaw_stats.py    # expose reply_spread() (= _effective_moves)
app/services/maia_flaw_scoring.py  # hook: spread + line + score, pv in fingerprint, new modes
app/services/blunder_check_rules.py      # FACEPALM_SCORE_MIN, D-12 shares, FOREIGN_RATING_BAND, draw helpers
app/services/blunder_check_candidates.py # facepalm predicate re-check
app/services/blunder_check_selection.py  # per-origin fill, D-14 level
app/repositories/blunder_check_repository.py # SQL predicate, EXISTS picks, served blunder plies, level rows
scripts/backfill_maia_flaws.py      # --mode spread / --mode line --cutoff
scripts/blunder_check/facepalm_features.py, fit_facepalm.py
```

### Pattern 1: Preservation by omission + stamp clear (existing, extend)
New `game_flaws` columns are written only by the scorer; `flaw_record_to_row` never emits them; the reclassify path
clears the stamps. Test: reclassify a game with scored values -> survivors keep values, new plies NULL, stamps NULL
(precedent tests `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps`, test_maia_flaw_scoring.py:1264).

### Pattern 2: Line facts as one pure function with explicit NULL semantics
```python
# Shape only; values and names are recommendations [ASSUMED]
LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)

@dataclass(frozen=True, slots=True)
class LineFacts:
    loss_by_depth: Mapping[int, int | None]   # None = line too short to tell (D-05)
    mate_ply: int | None                      # first line ply after which the blunderer is mated

def line_facts(pre_board: chess.Board, played_uci: str, pv: str | None) -> LineFacts: ...
```
Never mutate `pre_board` (the drain's target boards are shared, `test_refutation_target_boards_are_never_mutated`).

### Pattern 3: Python + SQL twin for the score
```python
# Source pattern: app/services/train_pool.py:205-240 (expected_score_sql / expected_score_for)
def facepalm_score(played_prob, reply_spread, loss_3, mate_ply) -> float | None: ...
def facepalm_score_sql(played_col, spread_col, loss3_col, mate_col) -> ColumnElement[float]:
    # CASE for mate within LINE_DEPTH, LEAST(loss3, LOSS_CAP), func.ln(played + OFFSET), 1/(1+exp(-z)), NULL guards
    ...
```
Parity test: insert rows, run the SQL expression, compare to Python within REAL precision (store is float32; compare
with a tolerance such as 1e-6).

### Pattern 4: Mode-dispatched backfill with constant selector clauses
Keep `_STAMP_CLAUSE_BY_MODE` as constants, never user input; the cutoff is a bound parameter. Shards by md5 residue,
never rank windows (memory: benchmark DB is not static; same applies to prod).

### Pattern 5: Composition by origin
Draw `(source, origin, shape)` per slot with the seeded `new_session_rng()`; fill own slots from the own pool,
convert unfillable own slots to foreign, fill foreign slots; redraw only shapes (keep source and origin) for empty
slots; positions renumbered contiguously (existing). Tests monkeypatch `new_session_rng` (existing pattern).

### Pattern 6: Deterministic fit
Seeded fold assignment, IRLS with a convergence tolerance constant and an iteration cap, fail loudly on separation
(non-convergence) rather than printing nonsense coefficients.

### Anti-Patterns to Avoid
- Replaying from `game_flaws.fen` (board_fen only): castling and en passant in the line become illegal.
- Treating the first pv token as a proxy for the whole line in the fingerprint (Pitfall 2).
- Computing the score only in SQL or only in Python (a refit must be an UPDATE; write-time needs Python).
- Using `herring_share` from the hazard weights as the session herring share after D-12.
- One flat pick for herring and blunder slots with the facepalm EXISTS (starves own herrings).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Board replay with exact rights | own PGN walker | `replay_flaw_boards` / `boards_from_targets` (maia_flaw_scoring.py:273-318) | handles invalid roots, castling, ep |
| Mover Elo | own normalisation | `pinned_elo_for_mover`, `_mover_elo` | single source with the frontend |
| Entropy spread | new formula | `_effective_moves` (maia_flaw_stats.py:97) | D-01 says reuse |
| Concurrency on write | ad-hoc locks | `_lock_games_ascending` + fingerprint re-read | deadlock-free, proven by 247/248 |
| Sharding | rank windows | `SHARD_RESIDUE_SQL` | table grows during runs |
| Game filters for the level | hand-rolled WHERE | `apply_game_filters(rated=True, opponent_type="human")` | bot-rating echo bug history |
| User-side test | `ply % 2` | `mover_is_white_at_ply`, `is_opponent_expr` | single parity source |
| Logistic regression lib | adding scikit-learn | numpy IRLS (~30 lines) | 4 parameters, 163 rows; avoids a new dependency in the lockfile |

## Runtime State Inventory

(D-11 is a column retirement, so this applies to that plan.)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Prod `game_flaws`: nine Maia columns over ~7.65M rows (values dropped with the columns); `games.maia_refutation_completed_at` | Drop is a data loss by design; recomputable with Phase 247 tooling (~half a day per the seed). Decide whether the refutation stamp goes too |
| Live service config | None. No dashboard, alert or external config names these columns (checked frontend, stories, analysis) | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts / caches | `temp/blunder-check/prod-cache-2026-11-10.json` and any calibration JSON cache embed the old `BlunderRecord` fields | Bump cache version; old caches fail to load by design |

## Common Pitfalls

### Pitfall 1: Spread blocked by the refutation guards
**What goes wrong:** spread NULL whenever `refutation_missing` / `refutation_not_legal`. **Why:** `_derive_refutation`
returns before inference on those reasons. **Avoid:** compute spread from the post-board policy first, the pair only if
the reply is usable. **Warning sign:** existing tests `test_refutation_unusable_reply_leaves_null_without_inference`
and `test_refutation_call_count_is_base_plus_scorable_user_blunders` (test_maia_flaw_scoring.py:590, 633) encode the
old call count and must be updated deliberately, not "fixed" back.

### Pitfall 2: Repaired pv invisible to the fingerprint
**What goes wrong:** a 252 repair keeps the first token (D-01 of 252 pins `root_moves` to the stored best move), so
the fingerprint (first token only) does not change and stale line facts are written. **Avoid:** add `gp_next.pv` to
`_flaw_fingerprint_select` and `FlawFingerprint`.

### Pitfall 3: Line pass as an "IS NULL" pass
**What goes wrong:** D-18 recompute selects nothing because every row already has values. **Avoid:** cutoff
checkpoint; required `--cutoff`.

### Pitfall 4: Line pass requiring Maia
**What goes wrong:** `_start_maia_and_run` exits 3 when Maia is unavailable; a line pass on a box without the Maia
group refuses to run. **Avoid:** mode-aware Maia start.

### Pitfall 5: The 252 repair's connection gate
**What goes wrong:** the repair aborts on a connection rise above its baseline + 10 when 8-9 backfill shards start
mid-run. **Avoid:** coordinate start order (Q5 Connections).

### Pitfall 6: Blunders stay "served" forever only for prompted plies
**What goes wrong:** leaving `prompted_stmt` in place keeps the D-17 exception alive. **Avoid:** query
`blunder_ply` of served windows; invert the line-283 test.

### Pitfall 7: Tests that use `chess.Board(fen)` for line positions
**What goes wrong:** fixtures without castling rights or with the wrong side to move. **Avoid:** fixtures carry the full
FEN as cached (`fens.json` values are full FENs) and the played UCI; push the played move on that board.

### Pitfall 8: Dropping columns while old code runs
**What goes wrong:** migrations run at container start (`deploy/entrypoint.sh:5` `alembic upgrade head`); an old app
container mid-swap, a running backfill shard or a calibration run with the old model selecting `GameFlaw` columns can
error after the drop. **Avoid:** run the drop when no operator script is running; consider a two-release drop
(remove from model first, drop in the next deploy) if the swap window matters.

### Pitfall 9: Eval-lottery test isolation
Every non-guest `Game` insert in DB tests needs finally-cleanup (memory); the backfill selector is global, scope test
runs by `user_id` (test_backfill_maia_flaws.py header).

### Pitfall 10: Real Maia in tests
Use `tests/services/maia_fakes.fake_full_policy` (deterministic, all legal moves, weights n..1) and the
`maia_engine._session` sentinel; never the real ORT session in unit tests. A spread test can assert the exact
entropy of the fake distribution.

## Code Examples

### Existing post-blunder inference (where spread hooks in)
```python
# Source: app/services/maia_flaw_scoring.py:363-383 (verbatim excerpt)
post = pre_board.copy(stack=False)
played = chess.Move.from_uci(played_uci)
if played not in post.legal_moves:
    return null_refutation_stats(), "played_not_legal"
post.push(played)
if not any(post.legal_moves):
    return null_refutation_stats(), "no_legal_reply"
if refutation_uci is None:
    return null_refutation_stats(), "refutation_missing"
...
probs = full_policy(post.fen(), elo)
```

### Existing no-repeat query to replace (D-17)
```python
# Source: app/repositories/blunder_check_repository.py:393-401 (verbatim excerpt)
prompted_stmt = (
    select(BlunderCheckWindow.game_id, BlunderCheckAnswer.ply)
    .join(BlunderCheckAnswer, BlunderCheckAnswer.window_id == BlunderCheckWindow.id)
    .where(
        BlunderCheckWindow.user_id == user_id,
        BlunderCheckWindow.game_id.in_(game_ids),
        BlunderCheckAnswer.ply == BlunderCheckWindow.blunder_ply,
    )
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 249 D-06 findability on single-move Maia pairs | facepalm score (played prob, full reply spread, line material) | 2026-11-13 | selection swap, nine columns retired |
| Own first, foreign fallback; ~30% herrings from the hazard | independent 1/3 herring / own / foreign, herrings own/foreign 50/50 | 2026-11-13 | composition rewrite |
| False alarm returns the blunder to the pool | shown once, permanently | 2026-11-13 | one query |
| Backfill = one NULL-stamp pass | Maia pass + re-runnable cutoff line pass | 2026-11-13 (D-18) | two modes |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The provisional constants come from running the new fit script (CONTEXT has no intercept) | Q6 | Planner might try to hard-code -0.71/-0.69/+0.32 without an intercept; scores meaningless |
| A2 | Column and stamp names (`maia_reply_spread`, `line_loss_N`, `line_mate_ply`, `facepalm_spread_completed_at`, `facepalm_line_completed_at`) | Q5 | Naming only (Discretion) |
| A3 | Spread pass also writes line facts and score (not only spread) | Q5 | If owner wants strict separation, the Maia pass writes spread only and the line pass must run before selection has scores |
| A4 | D-14 = most games per TC bucket over the last ~200 rated human games, median pinned of the last 50 in it | Q4 | Level shifts by a TC choice; foreign band misplaced |
| A5 | Herring origin share = own_blunder / (own + foreign) = 0.5 | Q3 | If owner meant "herrings at the population's own/foreign ratio", composition differs |
| A6 | Blunder position for blunder windows drawn from the hazard conditional on firing within L | Q3 | Position distribution changes slightly; anti-leak preserved either way |
| A7 | Lower bound of the loss feature (unclipped vs 0) is a fit choice | Q2/Q6 | Negative values (e.g. -9) pull scores down |
| A8 | Spread pass pace ~8 h on 8-9 shards (from the 248 refutation analogue) | Q5 | Longer window overlapping the 252 repair |
| A9 | `FOREIGN_RATING_BAND` is strict; no widening at rating extremes | Q3 | Short sessions at 2400+ or <800 |

## Open Questions

1. **NULL score when line-3 is unresolved.** D-05 makes `line_loss_3` NULL for a 1-2 ply line without mate or
   credit; D-02 makes a NULL line a NULL score. The label fit used `capture_loss` values on short lines instead of
   NULL. Recommendation: score NULL (does not qualify) and exclude such rows from the fit; D-18 re-scores them after
   the repair. Confirm with owner.
2. **Lower clip of the loss feature.** Fit both unclipped and `max(loss, 0)`; pick by CV AUC and precision at 0.7.
3. **User with no rated games at all (D-15 "no imported games").** No level exists. Recommendation: a named default
   (e.g. 1500, mirroring `FREE_PLAY_DEFAULT_ELO = 1500` in `frontend/src/hooks/useMaiaEloDefault.ts:39`) or the
   `current_strength` anchor; beta-only today, so low impact. Owner call.
4. **Foreign starvation at the extremes.** Measure in the D-10 report before deciding on a widening rule.
5. **Drop `games.maia_refutation_completed_at` with D-11?** Not one of the nine; recommend yes with `--mode refutation`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev (docker `flawchess-dev-db-1`) | tests, dev backfill | yes | 18.6, max_connections 300, head `d5b8e2f1a249` | — |
| uv | everything | yes | 0.10.9 | — |
| onnxruntime + numpy (`maia-inference` group) | spread pass, feature builder, fit | yes | 1.29.0 / 2.5.2 | — |
| Maia model `frontend/public/maia/maia3_simplified.onnx` | Maia | yes | 45.7 MB | — |
| `temp/blunder-check/*.json` caches | provisional fit, fixtures | yes (this machine only, gitignored) | — | `--db prod` read-only builder |
| Prod tunnel (`bin/prod_db_tunnel.sh`) | P07/P08 operator runs, calibration | not probed (no prod access in research) | — | orchestrator |
| scikit-learn / scipy | — | no | — | numpy IRLS (recommended anyway) |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode auto), pytest-xdist |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`; per-session cloned DB (`tests/conftest.py`) |
| Quick run command | `uv run pytest tests/services/test_blunder_check_candidates.py tests/services/test_blunder_check_rules.py -x` |
| Full suite command | `uv run pytest -n auto -x` |
| Type / schema | `uv run ty check app/ tests/ scripts/`; `uv run alembic upgrade head && uv run alembic check` |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Automated Command | File Exists? |
|-----|----------|------|-------------------|-------------|
| D-02 | Line facts match the reference on #13, #35, #153, #154, #156, #165, #170, #176, #177, #184 at d1..d9 (table in Q2) | unit | `uv run pytest tests/services/test_line_material.py -x` | Wave 0 |
| D-02 | Mate fixtures (#34, #108, #116, #162, #168, #181, #182): `mate_ply == 1` | unit | same | Wave 0 |
| D-05 | NULL rules: no pv, illegal first token, malformed UCI, short quiet line -> NULL; credit and mate settle | unit | same | Wave 0 |
| D-01/D-04 | Score formula, NULL propagation, cap, mate value; Python vs SQL twin parity | unit + DB | `uv run pytest tests/services/test_facepalm_score.py -x` | Wave 0 |
| D-01 | Window 14 (game 2099808 ply 23: played prob 0.0949, truncated spread 4.4 so the full spread is at least that order, loss 0, no mate) scores below `FACEPALM_SCORE_MIN` with the fitted constants | unit | same | Wave 0 |
| D-07 | Hook: spread = entropy of `fake_full_policy` on the post board; computed when the reply is unusable; one post-board inference per scorable user blunder; line facts from `gp_next.pv`; non-user rows NULL | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -x` | extend |
| D-07 | pv change between read and write -> `fingerprint_changed` | DB | same | extend |
| D-08/D-18 | `--mode spread` selector and stamps; `--mode line --cutoff` re-runs over valued rows, skips games stamped after cutoff, runs without Maia | DB | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -x` | extend |
| reclassify | survivors keep the new values, new plies NULL, new stamps cleared | DB | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x` | extend |
| D-09 | Candidate passes at threshold, fails just below, NULL excluded; SQL loader filters | unit + DB | `uv run pytest tests/services/test_blunder_check_candidates.py tests/repositories/test_blunder_check_repository.py -x` | rewrite findability tests |
| D-12 | Seeded draws: source shares ~1/3 over many draws; herring origin 50/50; blunder position distribution = hazard conditional | unit | `uv run pytest tests/services/test_blunder_check_rules.py -x` | extend |
| D-13 | Foreign games outside +-150 pinned never selected | DB | `uv run pytest tests/services/test_blunder_check_selection.py -x` | rewrite `test_foreign_fallback_bands_by_elo_and_skips_guests` |
| D-14 | Level = most-played TC bucket median pinned; bot/unrated games ignored; fallback chain | unit + DB | same file + repository test | Wave 0 |
| D-15/D-16 | User with no analysed games gets foreign blunders and foreign herrings; own slots fall back to foreign when own supply is used up | DB | same | replace `test_own_first_never_queries_foreign` |
| D-17 | False alarm before the blunder -> blunder NOT eligible again | DB | same | invert line 283 test |
| D-10 | Report sections render from a cache; facepalm section, own/foreign supply | unit | `uv run pytest tests/scripts/test_blunder_check_calibration.py -x` | rewrite |
| D-11 | No reader left: `grep -rnE "maia_(played_rank|best_|second_|top_prob|effective_moves|refutation_)" app scripts tests` empty (migrations excepted); migration up/down | grep + `alembic upgrade head && alembic check` | P09 | — |
| fit | IRLS recovers known coefficients on a synthetic dataset; deterministic CV folds | unit | `uv run pytest tests/scripts/test_fit_facepalm.py -x` | Wave 0 |

### Sampling Rate
- Per task commit: the quick run command plus the touched test file.
- Per wave merge: `uv run pytest -n auto -x`, `uv run ty check app/ tests/ scripts/`,
  `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`.
- Phase gate: the full pre-merge gate in CLAUDE.md (backend and frontend; frontend untouched but still gated),
  and a serial full suite before release (memory: `-n auto` green is not serial-CI green).

### Wave 0 Gaps
- [ ] `tests/services/test_line_material.py` with a committed fixture module (full FEN, played UCI, pv) for the ten
  D-02 positions and the mate positions, copied from the `temp/` caches.
- [ ] `tests/services/test_facepalm_score.py` (formula, NULLs, SQL parity, Window 14).
- [ ] `tests/scripts/test_fit_facepalm.py` (synthetic recovery, determinism).
- [ ] D-14 resolver tests.

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so enabled.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no new endpoints) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | Selection and served-set queries keep `user_id` from the auth dependency (existing IDOR guard); foreign windows expose only game ids, ratings, moves (249 D-09) |
| V5 Input Validation | yes | Worker-supplied pv / best_move strings: catch `ValueError` from `Move.from_uci`, stop at illegal tokens (T-248-01 precedent) |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | Reports and the features TSV contain game links and numbers only, no usernames/emails (T-248-10/11) |

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Malformed pv crashing the scorer for a whole game | DoS | per-token validation, NULL facts, Sentry only for unexpected exceptions |
| Operator script writing prod by accident | Tampering | calibration + feature builder use `make_readonly_engine` (read-only transactions); only the backfill writes |
| SQL injection via CLI cutoff | Tampering | bound parameter, parsed as an aware datetime |
| Connection exhaustion on prod | DoS | shard cap, one connection per shard, coordinate with the 252 repair gate |

## Sources

### Primary (HIGH, read this session)
- `app/services/maia_flaw_scoring.py`, `maia_flaw_stats.py`, `eval_apply.py` (1032-1483), `eval_drain.py`, `app/routers/eval_remote.py`
- `app/repositories/game_flaws_repository.py`, `blunder_check_repository.py`, `current_strength_repository.py`
- `app/services/blunder_check_candidates.py`, `blunder_check_rules.py`, `blunder_check_selection.py`, `blunder_check_service.py`, `best_move_candidates.py`, `current_strength_service.py`, `train_pool.py` (205-240)
- `app/models/game_flaw.py`, `game.py`, `game_position.py`, `blunder_check.py`, `herring_pool.py`
- `scripts/backfill_maia_flaws.py`, `scripts/repair_short_lines.py`, `scripts/blunder_check_calibration.py`, `scripts/blunder_check/*`
- `temp/blunder-check/refine.py`, `mech.py`, `pvmat.py`, `set6.py` and caches; `reports/blunder-check/leg2-labels-2026-11-11.tsv`
- alembic 247/248 migrations, `docker-compose.yml`, `deploy/entrypoint.sh`, `pyproject.toml`, `uv.lock`
- `.planning/phases/248-*/248-07-SUMMARY.md` (prod backfill throughput), `252-CONTEXT.md`, `252-05-SUMMARY.md`
- Dev DB read-only probes (counts, indexes, pv lengths)

### Secondary
- None (no web research; brownfield phase).

## Metadata

**Confidence breakdown:**
- Code integration (hook, omission, selection, backfill): HIGH, read in full.
- Line count semantics and fixtures: HIGH, reference re-run on the cached positions.
- Fit procedure and constants: MEDIUM, intercept unknown until the script runs.
- D-14 helper and D-12 composition details: MEDIUM, design recommendations pending owner confirmation.
- Prod sizing: MEDIUM, analogue from the 248 run.

**Graph context:** not queried (codebase read directly).
**Research date:** 2026-11-13
**Valid until:** 2026-11-27 (fast-moving: Phase 252 is writing prod lines in parallel)
