---
id: SEED-039
status: dormant
planted: 2026-06-07
planted_during: v1.24 (Library Page), Phase 109 shipped
trigger_when: when extending the flaw-tag taxonomy with a cause-of-error / "tactic" family, or when building motif-level blunder explanations
scope: medium
---

# SEED-039: Tactic family — cause-of-error flaw tags

Add a future **tactic family** to the flaw-tag taxonomy that labels *why* a
move was bad in tactical terms — the orthogonal "what went wrong" axis that the
existing families (severity / tempo / opportunity / impact / phase) deliberately
do not cover. `.planning/notes/flaw-tag-definitions.md` already reserves
cause-of-error naming for this family (see the `unrushed` rename rationale:
"cause-of-error naming is reserved for the future tactic family").

**What it labels:** for each flaw row, tag the tactical cause as the single
**`allowed` motif** — the tactic that *refuted* the bad move. The motif is
detected in the **refutation line** (the best reply to the flawed move), NOT on
the flawed move itself.

> **Design pivot (2026-06-07, opponent-flaw materialization):** the earlier
> motif × direction model (two columns: motif + allowed/missed) collapses to **one
> `tactic_motif` column** once both player AND opponent flaws are materialized in
> `game_flaws` (see "Storage & integration"). See "Tag structure" for why.

## Tag structure: one motif column, direction implied

Two dimensions exist conceptually, but only one needs storing:

- **Motif** (WHAT tactic): `fork`, `pin`, `skewer`, `back-rank`, `mate`,
  `hanging-capture` (hung piece), ... — **stored** as `tactic_motif`.
- **Direction** (which side of it you were on) — **NOT stored**; derived:
  - `allowed-X` = a flaw row whose `tactic_motif = X` (you walked into X). This is
    what every row carries directly.
  - `missed-X` = an **opponent** `allowed-X` row at ply *n* adjacent to a **player**
    flaw at *n+1* with `is_miss = true` (the opportunity tag already computed). I.e.
    the opponent left X on the board and you failed to punish. A **join**, not a
    stored tag.

This works because with opponent flaws materialized, "you missed a fork" and "the
opponent allowed a fork that you didn't punish" are the same event from two POVs.
So one `allowed` motif per row + the existing `is_miss` adjacency reconstructs the
missed view for free. It also **halves the engine cost**: only the refutation line
is ever searched (one PV per flaw), never a separate "what should I have played"
line.

**The one case this does NOT cover** (defer to a later phase): a tactic available
for several moves where the opponent did not *newly* blunder to allow it (no
adjacent opponent `allowed` row). True standalone `missed-*` would need its own
detection (motif in the player's own PV) and a second column. Defer until data
shows it's common enough to matter.

**Family decision: ONE `tactic` family, single `tactic_motif` per flaw,** at most
one, chosen by salience (largest ES swing) when a refutation contains more than one
motif. Cards read "you allowed a fork"; the missed framing is an aggregate/join
concern, not a card tag.

## Why This Matters

The current taxonomy tells a player *how bad* a move was and *under what
conditions* (clock, swing, phase), but never *what kind of mistake* it was. "You
blundered in the middlegame, unrushed" is far less actionable than "you hung a
piece to a fork." Motif-level cause tags turn the flaw list into a coaching
signal: players can see their recurring tactical weaknesses (always walking into
forks, repeatedly missing back-rank mates) and train them. This is the natural
next layer on top of the shipped Phase 106 flaw cards.

## When to Surface

**Trigger:** when extending the flaw-tag taxonomy with a cause-of-error family,
or when a milestone scopes motif-level blunder explanations / tactical-weakness
analytics.

This seed will surface during `/gsd-new-milestone` when the milestone scope
matches.

## Scope Estimate

**Medium** — a phase or two. **Requires a DB migration**: `game_flaws` is a
materialized table (SEED-038), so the tactic tag is a new `tactic_motif` column
(plus the `is_opponent` column for opponent-flaw materialization). The effort is
in the per-flaw Stockfish PV capture, the reimplemented cook detectors, and their
validation — not in plumbing. (Correcting an earlier draft of this seed that
claimed "computed on the fly, no migration" — that was wrong; see "Storage &
integration".)

## Reference Implementations

- **Primary (SPEC/reference):** `ornicar/lichess-puzzler`, file `tagger/cook.py`
  (**AGPL-3.0**). The gold-standard, engine-verified motif classifier (depth-2
  forced-line confirmation), battle-tested on millions of Lichess puzzles,
  actively maintained. **Read it to learn the heuristics; reimplement in our own
  English code. Do NOT copy AGPL source** — heuristics/ideas aren't
  copyrightable, and reimplementing sidesteps the copyleft viral-over-network
  issue (FlawChess is a hosted service). Repo: https://github.com/ornicar/lichess-puzzler
- **Secondary crib:** `aslyamov/chess_detect` (MIT) — a clean but unverified,
  single-ply geometric detector. Useful as a second reference for the same
  motifs; do not adopt as a dependency (see Rejected below).

## cook.py methodology & motif inventory

**cook.py's method = "name the pattern in a forcing line from one side's POV"**
(`puzzle.mainline`, `puzzle.pov`). It does NOT detect a tactic on a static
position — it tags a *line*. For the `allowed` axis (the one we store):

- **`allowed-X`** → run the detectors on the **refutation line** (best reply to
  the flawed move), POV = the refuting side. This is the only search we need.
- (`missed-X` is a join over adjacent rows — no separate search; see "Tag structure".)

**Integration corrections (verified against the codebase 2026-06-07):**

1. **It's the PV line we lack, not the eval.** `game_positions.eval_cp/eval_mate`
   and `game_flaws.es_before/es_after` already exist; severity is already derived.
   What is stored **nowhere** is the principal variation. There is no `pv` /
   `multipv` / `bestmove` column anywhere. The new Stockfish work = capturing the
   PV (several plies) for each flagged flaw. Detector cost scales with PV depth
   (the tiering below).
2. **cook consumes a line + POV, not a FEN.** Build a synthetic `(board, line,
   pov)` and run the reimplemented detectors over it. "Run the FEN through cook"
   does not match the methodology.
3. **The stored `fen` column is unusable for the engine.** `game_flaws.fen` is
   `board_fen()` — piece placement only, no side-to-move / castling / en-passant.
   Fine for the miniboard, **not a legal FEN for Stockfish.** Reconstruct the full
   position by PGN replay.
4. **Integrate in the eval-drain / classify pass, not as a `fen`-column reader.**
   `classify_game_flaws` (called from `eval_drain.py`) already replays the PGN
   (`_recompute_fen_map`) and has a live `python-chess` Board, and
   `_run_all_moves_pass` already classifies BOTH colors. That is the natural place
   to run the PV search and emit `tactic_motif` into the materialized row.
5. **`severity = blunder only` is a fine MVP cost-control, but a tunable** — make
   it a threshold constant, not a hardcoded assumption. `game_flaws` holds
   mistakes too, and a missed fork can be only mistake-sized.

### Tiered by PV depth (build order)

**Tier 1 — 1-ply PV (cheap, reliable; MVP):** `fork`, `pin` (pin-prevents-attack
/ pin-prevents-escape via `board.pin()`), `hanging-piece` (= our `hung-piece` /
`missed-capture`), `double-check` (trivial: `len(checkers) > 1`).

**Tier 2 — 2-ply PV (nearly-free adds):** `skewer`, `back-rank-mate` / `mate` /
`mate-in-N` (line ends in `is_checkmate()`), `capturing-defender` (= removing the
defender), `discovered-attack` / `discovered-check`, `trapped-piece`.

**Tier 3 — 3+-ply PV (complex, more fragile heuristics):** `deflection`,
`interference` / `self-interference`, `attraction`, `intermezzo` (zwischenzug),
`x-ray`, `clearance`, `sacrifice`.

**Named-mate bonus (full mate line, geometric king-box patterns):**
`smothered`, `anastasia`, `hook`, `arabian`, `boden`, `double-bishop`, `dovetail`.

The MVP (Tier 1 + the mate/back-rank parts of Tier 2) is almost exactly the
short list below, plus `double-check` and `capturing-defender` as cheap extras.

### Caveats from reading cook.py

- **`overloading()` is a stub** (`return False`) — not implemented despite being
  in the tag list; `deflection` partially covers it. Don't expect it for free.
- **Skip the non-motif tags:** endgame-type tags (`pawnEndgame`, `rookEndgame`,
  `queenRookEndgame`, …) — we already classify endgame type; and the eval/length
  buckets (`crushing`/`advantage`/`equality`, `oneMove`/`short`/`long`) — these
  are puzzle metadata, not tactical causes.
- **Move-type descriptors** (`promotion`, `en-passant`, `castling`, `quiet-move`,
  `defensive-move`, `advanced-pawn`) are mostly not cause-of-error motifs; defer.
- cook.py's edge over `chess_detect` is exactly this: the *line* is the engine
  verification, so the detector only has to *name* the pattern, not prove it works.

## Storage & integration (game_flaws materialization)

`game_flaws` (SEED-038) is a **derived materialization table**, one row per M+B
flaw, keyed `(user_id, game_id, ply)`, that already persists `severity`, `tempo`,
`phase`, the opportunity bools (`is_miss`, `is_lucky_escape`), the impact bools,
and the display payload (`es_before`, `es_after`, `move_san`, `fen`). Tags are
**not** computed on the fly — they are columns. The tactic family adds to this.

**New columns:**
- `tactic_motif` (nullable SmallInteger enum) — the `allowed` motif refuting this
  flaw; NULL when no motif detected or below the severity gate.
- `is_opponent` (bool) — distinguishes the player's flaws from the opponent's, so
  both sides' M+B are materialized (see below). Note it is *derivable* from ply
  parity + the player's color (mover color ≠ player color); storing it is a
  query-convenience denormalization that avoids a `games` join. Could store mover
  color instead.

**Opponent-flaw materialization is nearly free.** `_run_all_moves_pass` already
classifies **every ply for both colors** (required for `is_miss` /
`is_lucky_escape` adjacency). Today the player-only filter happens before upsert.
Materializing opponent rows = "drop the filter + set `is_opponent`"; the eval work
is already done. Only the **tactic enrichment** (the PV search per flaw) adds new
engine cost. PK `(user_id, game_id, ply)` still holds — players alternate plies,
so player and opponent rows never collide.

**Per-user duplication caveat:** opponent flaws are materialized once *per user who
faced that opponent*. Correct for per-user "my opponents' frequencies". For any
global/population tactic stat, **dedupe by `(game_id, ply)`** or shared games
double-count.

**Engine-cost flag (OOM history).** Even one PV search per flaw adds Stockfish
load during the eval drain, and the project has repeated OOM history (FLAWCHESS-3Q:
Stockfish pool + import memory pressure). Do NOT add a second independent engine
pass. Preferred: capture the PV inside the **existing** `_run_all_moves_pass`
search for plies that come back as flaws. Or run a **separate bounded backfill**
(à la `scripts/backfill_eval.py`) off the import hot path, capped depth, shared
engine pool. The `allowed`-only model (one search/flaw, no missed search) is the
cheap path.

## Aggregate stats / opponent comparison

Primary product goal driving this design: **compare the player's vs their
opponents' frequencies of tactic tags and tag-combinations** (e.g. "you allow
forks 2× more than your opponents do", "your back-rank lapses cluster in the
endgame under time pressure"). The flat materialized columns make this a
`GROUP BY (is_opponent, tactic_motif, …)`.

- **Compare rates, not raw counts.** The player and their opponent pool face
  different numbers of blunders and games. Normalize (per game, per 100 blunders,
  or as a fraction of that side's flaws) before comparing.
- **Reuse the project's Wilson-based significance util** — "does this player allow
  forks more than their opponents" is a proportion comparison, exactly what the
  existing chess-score method handles. Do NOT invent a parallel test.
- **Tag-combinations = co-occurrence over the materialized columns**
  (`tactic_motif` × `tempo`, × `phase`, × severity). Another reason to keep ONE
  motif column rather than packing direction into it — clean group-bys.

## Key Design Constraints

- **Gate on our existing Stockfish eval.** We already compute eval per half-move.
  Only run motif detection on moves Stockfish already flagged as
  mistakes/blunders (by Expected-Score drop). This eliminates the false-positive
  problem that plagues standalone geometric detectors, and reuses work we
  already pay for instead of a redundant independent pass.
- **Start with the high-value amateur short list (as `allowed` motifs):** `fork`,
  `pin`, `skewer`, `hanging-capture` (hung piece), `back-rank` / `mate`. Most are
  cheap with python-chess (`attackers`, `pin`, `is_attacked_by`).
- **Materialized, not on-the-fly.** `game_flaws` is a SEED-038 materialization
  table; the tactic tag is a stored `tactic_motif` column written at classify
  time, **requiring a migration** (plus `is_opponent`). This corrects the original
  seed draft.
- **Orthogonal axis.** This family answers "why was it bad" / "what went wrong";
  existing families answer "how bad" and "under what conditions". One
  `tactic_motif` per flaw (same single-tag-per-family rule as the rest).

## Rejected Alternatives

- **Adopt `chess_detect` as a dependency** — rejected. Abandoned (~4 months no
  activity, half its motifs unbuilt), Russian internal docstrings/comments, no
  engine verification (single-ply geometric → unknown false-positive rate), and
  wrong axis (it annotates *every* move good or bad; we need cause-of-error on
  the refutation). Keep only as an MIT secondary crib.
- **ChessGrammar** — rejected. Closed, hosted, paid API. Wrong shape for our
  bulk-import scale (per-call cost over millions of positions), adds an external
  dependency, and raises privacy concerns.

## Breadcrumbs

- `.planning/notes/flaw-tag-definitions.md` — current taxonomy; reserves
  cause-of-error naming for this family.
- `.planning/notes/flaw-tag-naming.md` — authoritative naming taxonomy.
- `app/services/flaws_service.py` — shipped flaw classifier. Key fns:
  `classify_game_flaws` (kernel), `_run_all_moves_pass` (classifies BOTH colors —
  the opponent-flaw + PV-capture hook), `_recompute_fen_map` (live PGN replay —
  full-FEN source), `_build_tags`. The tactic pass integrates here.
- `app/models/game_flaw.py` — `GameFlaw` materialization table (SEED-038); add
  `tactic_motif` + `is_opponent` columns here. Note `fen` is `board_fen()`
  (placement only — NOT engine-usable).
- `app/services/eval_drain.py` — calls `classify_game_flaws` (~line 534); where
  the PV search / engine-cost concern lands.
- `app/repositories/game_flaws_repository.py` — upserts flaw rows; the player-only
  filter to drop for opponent materialization.
- `app/models/game_position.py` — `eval_cp` / `eval_mate` scalars (no PV stored).
- `scripts/backfill_eval.py` — model for a bounded off-hot-path backfill.
- `app/services/eval_utils.py` — Expected-Score sigmoid + eval; the gating signal.
- Phase 106 / SEED-038 — shipped flaw cards + materialization (the surface this
  extends).

## Notes

Captured 2026-06-07 from a repo-evaluation discussion of `aslyamov/chess_detect`.
Per project convention this is a forward-looking seed only — no roadmap phase was
created. Enrich or promote when a milestone scopes tactical cause tagging.
