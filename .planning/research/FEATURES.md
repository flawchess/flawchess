# Feature Research — v1.30 Forcing-Line Tactic Gate

**Domain:** Chess tactic tagger — forcing-line validity gate modeled on lichess-puzzler
**Researched:** 2026-06-29
**Confidence:** HIGH (all constants and logic verified directly against lichess-puzzler source at `/home/aimfeld/Projects/Python/lichess-puzzler`, version 50)

> **AGPL boundary.** All findings below are described in original prose. No lichess-puzzler
> source is copied. Citations name the file, function, and line for traceability only.

---

## How the lichess-puzzler gate works end to end

This section is the core deliverable: a code-mappable spec of every constant and rule, with
FlawChess unit translations. Each subsection maps to one of the four design-note claims.

---

### (1) The only-move margin — verified constant 0.00368208, translation to +0.35

**What lichess does.**
`generator/generator.py::is_valid_attack` (line 60) accepts a solver move as uniquely best if the
lila win-chances of the best move exceeds the win-chances of the second-best move by more than 0.7,
where lila win-chances lives in the range minus-1 to plus-1. The exact condition in prose:

    w(best) > w(second) + 0.7   [lila −1..+1 space]

The `win_chances` converter (`generator/util.py`, lines 44-54) uses the multiplier constant
`MULTIPLIER = -0.00368208` (line 53, sourced from the lila pull request noted in the comment).
For a centipawn score `cp`, it returns `2 / (1 + exp(-0.00368208 * cp)) - 1`, a sigmoid centered
at 0 in −1..+1 space.

A move also passes the validity gate if: the position has no legal second move (forced); the pair
is a tablebase pair carrying a unique tablebase winner; or the position is a mate-in-one where the
unique-mate-in-one sub-check passes (`is_valid_mate_in_one`, line 36). The +0.7 threshold is only
reached when two scored moves exist.

**Exact constant.**
`MULTIPLIER = -0.00368208` in `generator/util.py:53`. This is the coefficient in the argument to
`exp`, making it the decay rate of the sigmoid. The sign convention differs between the two
codebases (lichess uses a negative multiplier in the exponent; FlawChess uses a positive `K`
multiplied by a sign flip), but the magnitude is identical.

**Translation to FlawChess units.**
FlawChess stores `LICHESS_K = 0.00368208` (same magnitude) in
`app/services/eval_utils.py:41`, used as: `win_prob = 1 / (1 + exp(-LICHESS_K * sign * eval_cp))`,
which returns a probability in 0..1 rather than the lila −1..+1 range.

The two functions are related by: `w_lila = 2 * win_prob - 1`. Substituting into the gate:

    2*p(best) − 1 > 2*p(second) − 1 + 0.7
    p(best) − p(second) > 0.35

The FlawChess gate is therefore `p(best) − p(second) > 0.35`, computed with
`eval_cp_to_expected_score` using the existing `LICHESS_K`. No new constant is introduced;
the translation is exact. Factor out as a named constant `ONLY_MOVE_WIN_PROB_MARGIN = 0.35`.
Treat 0.35 as the starting margin for the user-28 experiment, not as a fixed rule.

**Mate handling.**
`win_chances` in lichess-puzzler returns exactly +1 for a positive mate and −1 for a negative
mate (`generator/util.py:48-50`). In FlawChess, `eval_mate_to_expected_score` returns 0.0 or 1.0
for mate rows (`app/services/eval_utils.py:69-97`). Use it instead of `eval_cp_to_expected_score`
for nodes where `best_mate` is non-null in the JSONB blob.

A best-is-mate / second-is-cp combination always passes the gate (1.0 − any_finite_value > 0.35).
A best-is-cp / second-is-mate never passes (finite − 1.0 < −0.35). A both-mates case needs care:
if both are mates for the solver, the gate fails — this is a known false-negative edge case (see
section 4 below).

---

### (2) Solver-nodes-only rule — confirmed, and why branch-then-reconverge is safe

**What lichess does.**
`generator/generator.py::get_next_pair` (line 63-68) only calls `is_valid_attack` when
`node.board().turn == winner` (the solver's turn). At defender turns, the code plays the single
engine-best response via a separate `get_next_move` call without any uniqueness check. In prose:

- At **solver nodes**: uniqueness is enforced — if the second-best move's win-chance is within
  0.7 of the best, the line is rejected and the puzzle is abandoned.
- At **defender nodes**: the engine picks its single best reply and the line continues, regardless
  of how many near-equal defensive moves exist.

**Why branch-then-reconverge is safe.**
If the defender has two or three near-equal defensive moves that all reconverge to the same forcing
continuation for the solver, the gate sees no ambiguity at any solver node. It checks uniqueness
only on the SOLVER's next move after each defender reply. If the solver's continuation is unique
following each defender branch, the line is valid — the defender can pick any of their responses
and still face the same forced refutation. The "branch-then-reconverge" concern is definitively
answered: only solver-side ambiguity kills a line.

**FlawChess mapping.**
In the FlawChess PV representation, `moves[0], moves[2], moves[4], ...` (even indices) are the
solver (pov) moves, and `moves[1], moves[3], ...` (odd indices) are the defender replies (see
`tactic_detector.py::_solver_move_indices`, lines 2221-2229). The gate runs
`eval_cp_to_expected_score` on the stored second-best eval at each even-indexed node in the
`allowed_pv_lines` / `missed_pv_lines` JSONB blobs. Odd-indexed nodes need no gate check. Their
second-best evals can still be stored (for future rule options, at no extra engine cost) but are
not tested by the current gate.

---

### (3) Rejection filters — exact constants and FlawChess mapping

Four additional filters, each cutting a distinct noise class:

#### (3a) Already-winning reject — +300 cp threshold

**What lichess does.**
`generator/generator.py::analyze_position` (lines 185-189): before searching for a puzzle, two
conditions jointly reject the start position. First, if `prev_score > Cp(300)` — the position
BEFORE the blunder was already better than +300 cp for the eventual solver — AND the current score
is not a short forced mate (`score < mate_soon`, where `mate_soon = Mate(15)`), the position is
rejected. Second, separately, if `is_up_in_material(board, winner)` — the solver's side already
has more material than the opponent using P=1, N=3, B=3, R=5, Q=9 — the position is also
rejected, regardless of eval.

**FlawChess mapping.**
The flaw's `eval_cp` at `flaw_ply` (the position BEFORE the refutation PV begins) is the
equivalent of `prev_score`. The already-winning reject becomes:

    flaw_pre_eval (user's perspective, centipawns) > +300   →  skip motif tagging

Use `game_positions.eval_cp` at `flaw_ply` (white-perspective; flip sign for black pov). The
+300 cp translates directly as an integer centipawn threshold. The `mate_soon` exception (allow
forced-mate starts even from winning positions) is less relevant in practice — forced-mate PVs
already get their tactic from the mate-family detectors; the clearance/sacrifice/capturing-defender
false positives originate in non-mate positions.

Named constant: `ALREADY_WINNING_CP_THRESHOLD: int = 300`.

#### (3b) Still-winning floor — +200 cp abort

**What lichess does.**
`generator/generator.py::cook_advantage` (line 114): at each recursive step building the puzzle
line, if `pair.best.score < Cp(200)`, recursion aborts ("Not winning enough"). The solver's best
move at every node in the refutation line must produce a position with at least +200 cp advantage.
As soon as the line drops below +200 cp, the puzzle terminates and subsequent nodes are not tagged.

**FlawChess mapping.**
Walk the JSONB blob forward. At each solver node (even index), check: if `best_cp < 200` and
`best_mate` is null (no forced mate), stop walking and do not tag any motif at or beyond that
node. Named constant: `STILL_WINNING_CP_FLOOR: int = 200`.

#### (3c) Length filters — trailing-only-move strip and one-mover discard

**What lichess does.**
After `cook_advantage` returns a solution list, `analyze_position` applies two length rules
(lines 216-221):

1. **Trailing-only-move strip:** while the solution has even length OR the last pair has no
   `second`-best move (meaning the last move is forced with no alternative), trim the last element.
   This ensures the puzzle ends on a solver move where a genuine choice existed — the final move
   cannot be a trivially forced only-move.

2. **One-mover discard:** if the solution collapses to length 0 or 1 after stripping, discard.
   A single-move "solution" (just the refuting move with no continuation) is not a puzzle.

Lines 223-224 add a two-mover discard for tiers 0-2 (slow/master games only can produce
two-movers). This tier system has no FlawChess equivalent and should not be imported.

**FlawChess mapping.**
Walk the stored JSONB from the end and trim solver nodes where `second_cp` and `second_mate` are
both null (the only-move case). After trimming, if fewer than 2 solver moves remain in the trimmed
line, suppress the motif tag entirely. No tier-based two-mover filter needed.

#### (3d) Start trigger — score >= +200 cp AND win-chance jump > 0.6

**What lichess does.**
`analyze_position` (line 203): a puzzle starts only when the position after the blunder has
`score >= Cp(200)` AND `win_chances(score) > win_chances(prev_score) + 0.6` — the win-chance
jumped by more than 0.6 (in -1..+1 space) across the blundering move. This trigger threshold (0.6)
is looser than the per-node only-move gate (0.7). Lines 204-206 add a secondary guard: if the
current score is under Cp(400) AND the winner is not coming from being down in material, abort —
marginal advantages from balanced positions are excluded.

**FlawChess mapping.**
This is a puzzle-discovery trigger. FlawChess's flaw classification pipeline (Phase 105, 108)
already performs the equivalent blunder detection — existing `game_flaws` rows already represent
positions where a meaningful mistake occurred. No new start-trigger gate is needed in the re-tagger.

---

### (4) False-negative risk — "second-best close" does not always mean "not tactical"

**The structural risk.**
The gate rejects a solver node when `p(second) >= p(best) - 0.35`. In genuine tactical positions,
two moves can both win decisively:

- **Two captures of the same hanging piece:** if a hanging piece can be captured by two different
  pov pieces and both are clean wins, `p(best) - p(second)` may be near zero. The gate suppresses
  both routes even though "grab the piece" is the correct instruction.

- **Fork or simpler capture co-exist:** if the best move is a fork AND a straightforward
  hanging-piece capture is nearly as good, `p(second)` approaches `p(best)` and the fork tag is
  suppressed even though the fork is real.

- **Both-mates edge case:** if two solver moves both deliver checkmate, the second-best win-prob
  is 1.0 and the gate always fails. The mate detectors may still fire based on the final board
  being checkmate, but motifs at earlier nodes in the line are lost.

**Magnitude.**
These are false negatives (good tags killed), not false positives (noise). The user-28 experiment
must quantify both:
- How many tags are removed in total (noise reduction)?
- How many of those removed were actually correct (good tags killed)?
- Hand-check ~30 removed cases for confirmation.

**Mitigation.**
Store the second-best UCI (`"su"` field in the JSONB blob). This enables a future
"both-winning-captures" exception: if the best move and second-best move are captures of the same
piece on the same square, the gate can be waived for that node (both paths converge to the same
instruction). This is a P3 future rule; do not implement in v1.30. The 0.35 margin is a tuning
knob — if the hand-check shows excessive false negatives, raise it toward 0.40.

---

## Feature Landscape

### Table Stakes (must ship for v1.30 to be meaningful)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| MultiPV=2 engine pass + JSONB storage on `game_flaws` | Gate cannot run without second-best eval; all downstream features depend on this | HIGH | `allowed_pv_lines` / `missed_pv_lines` JSONB on `game_flaws`; schema migration + `engine.py` MultiPV=2 pass; remote-worker wiring |
| Solver-node only-move gate | The primary noise fix — clearance/sacrifice/capturing-defender on non-forced PVs is the stated milestone goal | MEDIUM | Check even-indexed nodes; use `eval_cp_to_expected_score` with `LICHESS_K`; constant `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` |
| Already-winning reject (>= +300 cp) | High-yield cheap filter; flaw pre-eval already stored in `game_positions.eval_cp` | LOW | Constant `ALREADY_WINNING_CP_THRESHOLD = 300`; flip sign for black pov; join to `game_positions` on `(game_id, flaw_ply)` |
| Still-winning floor (< +200 cp abort) | Stops PV walk at nodes where best eval drops below winning threshold; cuts deep-tail noise | LOW | Constant `STILL_WINNING_CP_FLOOR = 200`; check `best_cp` (or `best_mate`) at each solver JSONB node |
| Trailing-only-move strip | Without it, the last motif fires on a forced-only-move continuation; no genuine choice existed | LOW | Walk JSONB from end; trim solver nodes where second is null; suppress if fewer than 2 solver moves remain after trimming |
| Offline re-tagger applying the gate | Decouples expensive MultiPV engine pass from cheap gate+motif logic; enables threshold tuning without re-running engine | MEDIUM | Python-only transform over stored JSONB; runs gate + calls `detect_tactic_motif` on trimmed PV |
| User-28 A/B validation | Without measurement, the noise/false-negative tradeoff is unknown and margin tuning is blind | MEDIUM | Run old and new detector logic on same stored MultiPV data; tag diff by motif and original depth; hand-check ~30 removed cases |
| Corpus backfill + rollout | Gate has no effect until existing `game_flaws` rows are re-tagged with new logic | MEDIUM | `backfill_flaws.py`-style pipeline after MultiPV backfill completes; re-run `classify_game_flaws` with gated re-tagger |

### Differentiators (competitive advantage / future-proofing)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Second-best UCI stored in JSONB (`"su"` field per node) | Enables future "both-winning-captures" exception; enables UI showing "you could also have played X"; future defender-side ambiguity rules; zero extra engine cost since MultiPV=2 gives PV[1][0] for free | LOW (incremental) | Include `"su": "<uci>"` in every node of the blob now; not needed by the current gate but prevents a future re-engine-pass |
| Per-node second-best stored at EVERY node (solver + defender) | Future defender-side rules ("only one reasonable defense") become possible without schema change | LOW (marginal storage) | Design note recommends this for the user-28 experiment phase; optimize to solver-only later if defender data is never used |
| Tunable margin via named constant | 0.35 is a starting point; offline re-tagging means threshold can change without engine work | LOW (naming convention) | Factor out as `ONLY_MOVE_WIN_PROB_MARGIN`; wire to a `scripts/retag_tactics.py --margin` CLI arg |
| Motif depth-shift tracking in re-tagger output | Verifies the gate works as intended: surviving tags should move shallower (PV truncated to the forcing prefix) | LOW (logging / report column) | Track `original_depth` vs `gated_depth` in the validation report; include in the user-28 A/B diff |

### Anti-Features (do not build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Puzzle-grade depth-50 / 25M-node MultiPV search | Lichess-puzzler uses `Limit(depth=50, time=30, nodes=25_000_000)` per node pair (`generator/generator.py:25`) | 25M nodes per pair × ~12 nodes per flaw × millions of flaws = orders of magnitude more expensive than the current 1M-node all-ply pass; kills remote-worker throughput | Use the existing 1M-node budget (or a modest increase to ~2-3M for ordering stability) for the second-best ordering; the gate only needs a trustworthy best-vs-second ranking |
| Tablebase-based unique-winner check | Lichess-puzzler integrates Syzygy tablebases for endgame uniqueness | Adds multi-hundred-MB dependency, complex infra; almost no FlawChess real-game refutation PVs reach pure tablebase territory mid-line | The sigmoid gate + still-winning floor handles endgame-adjacent positions adequately |
| Mate-in-one uniqueness multi-pass (`count_mates` then `multipv=N+1`) | Lichess-puzzler has a special re-analyze path when two mate-in-ones exist (`is_valid_mate_in_one`) | One extra analyze call per mate-in-one position; rare in real-game PVs; false-negative risk is acceptable | Accept the false negative (both-mates suppresses the node-level tag; mate-family detectors may still fire on the final position) |
| Two-mover discard by time-control tier | Lichess applies this to enforce puzzle quality tiers (lines 223-224) | FlawChess has no tier system; two-move forced sequences in real games ARE instructive | Require at least 2 solver moves after the trailing-only-move strip; that covers the one-mover discard without a tier gate |
| Per-motif depth caps as an alternative to the gate | Simpler apparent fix: "clearance never fires past depth 4" | Fragile and not principled — misses shallow non-forced tags and allows deep forced ones at arbitrary depth cutoffs; requires per-motif tuning every time a new motif is added | Use the only-move gate; depth naturally bounds because non-forced PVs are truncated by the gate itself |

---

## Feature Dependencies

```
MultiPV=2 engine pass
    └──required by──> JSONB storage on game_flaws (allowed_pv_lines / missed_pv_lines)
                           └──required by──> Offline re-tagger with gate logic
                                                 ├──required by──> User-28 A/B validation
                                                 └──required by──> Corpus backfill + rollout

Already-winning reject
    └──reads from──> game_positions.eval_cp at flaw_ply (already populated since Phase 116)

Still-winning floor
    └──reads from──> JSONB best_cp per solver node (part of MultiPV storage)

Solver-node-only-move gate
    └──reads from──> JSONB second-best eval per solver node (part of MultiPV storage)

Second-best UCI ("su" field)
    └──free given──> MultiPV=2 pass (PV[1][0] is available at no extra engine cost)
    └──future-enables──> "both-winning-captures" exception
```

### Dependency notes

- **MultiPV storage is the load-bearing prerequisite.** Every gate rule reads from the JSONB
  blobs. Nothing else can be built until the engine pass and Alembic migration exist.
- **Already-winning reject uses existing data.** `game_positions.eval_cp` at `flaw_ply` is already
  populated since Phase 116. This filter can be applied in the re-tagger with a single join,
  without new engine work.
- **Remote-worker wiring is a parallel concern.** The MultiPV pass runs on the existing worker
  fleet (same as the current 1M-node all-ply pass) but targets flaw positions and the following
  ~6-12 PV plies, not every position.

---

## MVP Definition

### Must ship for v1.30 (gate is the milestone)

- [ ] Alembic migration adding `allowed_pv_lines` / `missed_pv_lines` JSONB columns to `game_flaws`
- [ ] `engine.py` MultiPV=2 pass over flaw PV positions (best + second eval + second UCI per node)
- [ ] Remote-worker wiring for the MultiPV pass
- [ ] Offline re-tagger applying: solver-node only-move gate, already-winning reject, still-winning floor, trailing-only-move strip, one-mover discard
- [ ] User-28 A/B validation: tag diff, noise removed, good tags killed, motif depth-shift report, manual hand-check of ~30 removed cases
- [ ] Corpus backfill of `allowed_pv_lines` / `missed_pv_lines` for all existing flaw rows
- [ ] Rollout: re-run `classify_game_flaws` with gated re-tagger across all users

### Add after validation (post-v1.30)

- [ ] "Both-winning-captures" exception using the stored `"su"` field — trigger: false-negative
  rate exceeds ~10% in the hand-check sample
- [ ] Tunable margin CLI arg (`scripts/retag_tactics.py --margin 0.35`) for threshold sweep research
- [ ] Motif depth-shift report column as an ongoing monitoring artifact

### Defer to v2+

- [ ] Defender-node ambiguity rule ("only one reasonable defense") — no evidence this noise class
  exists in the corpus; revisit after rollout telemetry
- [ ] Tablebase integration for endgame uniqueness
- [ ] Per-move tactic UI showing "you could also have played X" (requires stored `"su"` field —
  store it now, surface it later)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| MultiPV=2 engine pass + JSONB schema migration | HIGH (blocks all gate logic) | HIGH | P1 |
| Solver-node only-move gate | HIGH (primary noise fix) | MEDIUM | P1 |
| Already-winning reject (+300 cp) | HIGH (cheap, high-yield) | LOW | P1 |
| Still-winning floor (+200 cp) | MEDIUM (cuts deep-tail noise) | LOW | P1 |
| Trailing-only-move strip | MEDIUM (cuts forced-only tail) | LOW | P1 |
| Offline re-tagger | HIGH (required to apply the gate) | MEDIUM | P1 |
| User-28 A/B validation | HIGH (required to calibrate threshold) | MEDIUM | P1 |
| Corpus backfill + rollout | HIGH (gate has no effect otherwise) | MEDIUM | P1 |
| Second-best UCI in JSONB (`"su"`) | MEDIUM (future-proofing; zero extra engine cost) | LOW | P2 |
| Tunable margin constant / CLI arg | MEDIUM (threshold research) | LOW | P2 |
| "Both-winning-captures" exception | LOW (unknown prevalence before rollout) | MEDIUM | P3 |
| Defender-node ambiguity rule | LOW (speculative; no evidence of this noise class) | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.30 launch
- P2: Add when core gate is stable
- P3: Defer pending rollout telemetry

---

## Constants Reference (code-mappable)

| Constant | Value | Source in lichess-puzzler | FlawChess home |
|----------|-------|---------------------------|----------------|
| Sigmoid coefficient | 0.00368208 | `generator/util.py:53` (`MULTIPLIER = -0.00368208`) | `app/services/eval_utils.py:41` (`LICHESS_K`) |
| Only-move margin in −1..+1 space | 0.7 | `generator/generator.py:60` | Translates to `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` in 0..1 space |
| Already-winning threshold | 300 cp | `generator/generator.py:185` (`Cp(300)`) | `ALREADY_WINNING_CP_THRESHOLD: int = 300` |
| Still-winning floor | 200 cp | `generator/generator.py:114` (`Cp(200)`) | `STILL_WINNING_CP_FLOOR: int = 200` |
| Start-trigger win-chance jump | 0.6 | `generator/generator.py:203` | Not needed (flaw detection already done) |
| Puzzle-grade engine budget | depth=50, 25M nodes | `generator/generator.py:25` | Do NOT use — anti-feature |

---

## Sources

- `generator/generator.py` (lichess-puzzler, version 50): `is_valid_attack` (lines 55-61),
  `cook_advantage` (lines 103-123), `analyze_position` (lines 172-229), `get_next_pair` (lines 63-68)
- `generator/util.py` (lichess-puzzler): `win_chances` (lines 44-54), `MULTIPLIER` constant (line 53)
- `app/services/eval_utils.py`: `LICHESS_K` (line 41), `eval_cp_to_expected_score` (lines 44-66),
  `eval_mate_to_expected_score` (lines 69-97)
- `app/services/tactic_detector.py`: `_solver_move_indices` (lines 2221-2229), motif detectors
  for clearance/capturing-defender/sacrifice (the three primary false-positive sources)
- `.planning/notes/tactic-forcing-line-gate.md`: design note and original diagnosis (SEED-070)
- `.planning/notes/tactic-tagger-cook-alignment.md`: AGPL-boundary cook.py alignment work

---

*Feature research for: v1.30 Forcing-Line Tactic Gate — FlawChess*
*Researched: 2026-06-29*
