---
id: SEED-261126-g8b
status: dormant
planted: 2026-11-26
planted_during: ad-hoc design discussion after the 2026-11-26 release (no active phase)
trigger_when: next round of Train feedback work, or when the Phase 252 line repair finishes (the tag coverage below should be re-measured then)
scope: small-to-medium phase (reveal schema field, one shared copy resolver, two surfaces, owner spot-check of the copy)
---

# SEED-261126-g8b: The avatar comments on the game blunder (tactic tag + what it cost)

After a personalized puzzle or a blunder-check window, the avatar should say what the blunder in
the game actually was, when we know: the tactic it allowed or missed, and whether it gave away
material or passed up winning material. The analysis board's move strip already shows this for a
flaw (`frontend/src/lib/moveInfo.ts`, `frontend/src/lib/explainBar.ts`).

## Why This Matters

The puzzle verdict today says only "Several moves work here, just not your game move." and
points at the lines ("Step through the lines to see why."). The reveal response carries one fact
about the game move, the `game_move_facepalm` boolean, which only switches the badge to "???".
The user has to work out from the engine lines why their move was a blunder, while the same
`game_flaws` row already holds the answer in words.

## Where The Two Surfaces Stand

| | Tactic tag | Material / mate line |
|---|---|---|
| Blunder check solution | missing | shipped in Phase 261 (`BlunderFeedback.type_line`) |
| Personalized puzzle reveal | missing | missing |

Blunder check already says "The blunder loses material." / "allows checkmate." / "misses a chance
to win material." / "misses checkmate." (`TYPE_LINE_COPY` in
`frontend/src/lib/blunderCheckSolution.ts`), decided by `blunder_feedback` in
`app/services/blunder_check_feedback.py`.

## Proposed Shape

One shared "game blunder sentence", built from two parts and used by both surfaces:

- **Tactic tag** from the flaw row (`allowed_tactic_*`, `missed_tactic_*`), through the same
  visibility rule as the move strip (`resolveVisibleTactic`: confidence >= 70, visible family,
  decided-lost suppression). A spoken sentence is a stronger claim than a chip, so no looser gate.
- **Type line** for every blunder, facepalm or not: reuse `blunder_feedback` and its copy table.
  The floor is the existing `TYPE_LINE_MIN_SWING = 2`, applied to the material swing in piece
  points at the deepest settled depth of the stored line (a lost pawn gets no line, a lost
  exchange does). It is NOT applied to the stored decaying means `material_loss` /
  `material_missed`. The floor also stops the type rule's default: a blunder with no material in
  either line is typed "missed win", so without the floor the avatar would claim a missed win
  where nothing material happened.
- Both present: one sentence, "Your game move allowed a fork in 2 and gave away material."
- A facepalm blunder (score >= 70%) changes the wording of that sentence, it is not its own
  branch.
- Neither present: the avatar adds nothing. No filler sentence.
- Words, never numbers, for material.

Per surface:

- **Blunder check** gains the tag in its existing feedback paragraph. Subject stays "The
  blunder".
- **Personalized puzzle** gains both. Subject is "Your game move" for an own puzzle
  (`source === 'sr_item'`) and "The game move" for a foreign one. Red herrings get no sentence
  (there is no blunder). When the sentence points at a line it replaces "Step through the lines
  to see why." instead of adding to it. On phones the collapsed strip line stays as it is, the
  sentence shows in the expansion only.
- The reveal response needs a small flaw block (both motifs with depth, type line, facepalm
  score); it would replace `game_move_facepalm`. Blunder check snapshots the type-line facts when
  the window is served; the puzzle reveal would compute them for its one row at reveal time by
  walking the stored lines.

## Coverage (prod, 2026-11-26)

Own-blunder pool: 6,587 `drill_items` joined to `game_flaws`, games played from 2026-01-01 only
(the Phase 252 line repair has not finished for older games). All rows are blunders.

| Signal | Share |
|---|---|
| Missed tactic tag (confidence >= 70, visible family) | 7.7% |
| Allowed tactic tag (same gate) | 20.4% |
| Either tag | 27.5% |
| Facepalm score present | 96.2% |
| Facepalm blunder (score >= 70%) | 28.2% |
| Tag or facepalm blunder | 42.7% |
| Allowed mate in the stored line (`line_mate_ply`) | 3.4% |
| Missed mate in the stored line (`best_line_mate_ply`) | 0.7% |
| Proxy: decaying-mean loss or missed >= 2 | 33.9% |
| Proxy: tag, or decaying mean >= 2, or mate | 45.0% |

The 15,128 served-and-solved own puzzles give near-identical figures (26.4% either tag, 26.3%
facepalm blunder). Foreign puzzles had 7 solved rows, too few to read.

Limits of these numbers:

- The tag shares do not apply the decided-lost suppression, so they are slightly high.
- The material rows use the stored decaying means, a proxy. The real rule (swing at the deepest
  settled depth) is not a column and was not measured.
- The missed tag is rare (under 8%). Not established whether that is the detector or an
  unfinished backfill; re-measure after the Phase 252 repair.

## Considered And Dropped

- **"Same move as in the game"**: the chip already says "Move = Game" (owner, 2026-11-26).
- **Difficulty in words from `maia_best_prob`** ("rarely found at your rating"): the column is
  the probability of the single engine-best move, while a puzzle accepts any good move. Valid
  only for sharp puzzles; not worth a branch.
- **"A common mistake at your rating" from `maia_played_prob`**: already a main input of the
  facepalm score, would say the same thing twice.
- **Words for a low facepalm score on puzzles** ("an easy one to miss"): no trusted reading
  without labels. Blunder check keeps its own "hard to catch" line, which is about the catch
  task and does not carry over to puzzles.
- **Clock context**: already in the reveal's game footer, not duplicated in the bubble.
- **Cross-game patterns** ("your fourth missed fork this month"): a different size of work, own
  seed if wanted.

## Open Points

- Exact copy for the combined sentence and its facepalm variant: owner spot-check before merge.
- Whether the missed tag leads on sharp puzzles (it names the solution's idea) or the allowed tag
  always leads; at 8% coverage the question is small.
- Reveal-time cost of walking the stored lines for one row (expected trivial, not measured).
