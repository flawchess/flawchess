---
id: SEED-261126-g8b
status: promoted
promoted_to: Phase 264 (2026-11-26)
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

**Promoted 2026-11-26 to Phase 264** (`.planning/ROADMAP.md`, Active Phases; decisions in
`.planning/phases/264-avatar-game-blunder-sentence/CONTEXT.md`).

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

## Possible Sentences And Their Conditions (Phase 264, confirmed by the owner 2026-11-26)

> Amended 2026-11-26 (Phase 264 D-19): the shipped line starts with the move and its quality
> icon instead of the label, "Ne7 ???: allowed fork in 2." Read every "Game move:" below that
> way; the label remains only as the fallback without a SAN.
> Amended 2026-11-28 (D-21): a hanging-piece tag suppresses the material type part on the same
> side, like the checkmate rule ("allowed hanging-piece in 1." alone).
> Amended 2026-11-28 (D-22): "missed a chance to win material" and "missed checkmate" (past
> tense) replace "misses ..." below.

This list reflects the decisions taken on 2026-11-26 during promotion and supersedes "Proposed
Shape" above where the two differ (neutral subject, tags in the strip's form, no facepalm wording,
one swing rule for both surfaces). `CONTEXT.md` of the phase holds the decisions (D-01 to D-18); this list is the reference for the
copy.

The comment is one line of additional info in the avatar's speech bubble, set off from the
verdict by a horizontal divider (owner, 2026-11-26). It starts with the label "Game move:" and
lists up to two parts, separated by commas: a **tag part** and a **type part**. Either can be
absent. With both absent there is no divider and no line.

### Below the divider (personalized puzzle)

In this order, each line only when it exists; the divider shows when any of them does:

1. the "Game move:" line (this seed);
2. "Also fine, e.g. Nf3, Qe2" (existing);
3. the return tail, moved down from under the verdict, wording unchanged: "Back next session." /
   "Back in 4 days." / "Two in a row, so this one is retired." / "This one keeps slipping, so it
   is parked for now." / "A red herring, so it won't come back." / "From a similarly rated
   player's game, so it won't come back."

### Label

| Surface | Label | Condition |
|---|---|---|
| Personalized puzzle | Game move: | own or foreign puzzle (never "your") |
| Blunder check | Game move: | a caught or missed blunder window (same line and divider as the puzzle) |
| either | no line | red herring; blunder-check false alarm or "all good" window |

### Tag part

Form: `Game move: <tag>[, <tag>].` Each tag is written as on the analysis move strip:
`missed|allowed <motif>[ in <N>]`.

A tag is shown when all of these hold:

1. the flaw row has a motif on that side (`missed_tactic_*` or `allowed_tactic_*`);
2. its confidence is at least 70;
3. the position before the move was not already decided lost for the mover;
4. the motif belongs to a visible family (the strip's rule);
5. the depth shown is 5 or less, or the motif is a checkmate (any depth).

With both sides visible, both are shown, missed first.

| # | Condition | Sentence |
|---|---|---|
| T1 | only an allowed tag | Game move: allowed fork in 2. |
| T2 | only a missed tag | Game move: missed fork in 2. |
| T3 | both tags | Game move: missed fork in 2, allowed pin in 3. |
| T4 | tag without a stored depth | Game move: allowed fork. |
| T5 | allowed checkmate at depth 7 (kept by rule 5) | Game move: allowed checkmate in 7. |
| T6 | allowed fork at depth 6 (dropped by rule 5) | no tag part |

Motif words, exactly as the strip shows them: fork, pin, skewer, hanging-piece, checkmate (every
named mate reads "checkmate"), double-check, discovered-check, discovered-attack, trapped-piece,
x-ray, deflection, intermezzo, interference, capturing-defender, attraction, sacrifice,
en-passant, under-promotion, promotion. Each can follow "missed" or "allowed".

### Type part (one rule for both surfaces)

Conditions, the rule blunder check shipped with in Phase 261:

- **side**: allowed loss when `material_loss > 0` and `material_loss >= material_missed`,
  otherwise missed win;
- **mate**: the stored Stockfish line on that side reaches a mate (the line after the blunder
  for an allowed loss, the best line for a missed win);
- **swing**: else the material change at the deepest settled point of that line is at least 2
  points (replayed under the quiet rule, no decay).

Blunder check takes these facts when the window is served and stores them. The puzzle computes
them with the same server code when the reveal is requested.

| # | Side | Condition | Sentence |
|---|---|---|---|
| P1 | allowed loss | swing >= 2, no mate | Game move: loses material. |
| P2 | allowed loss | mate reached | Game move: allows checkmate. |
| P3 | missed win | swing >= 2, no mate | Game move: misses a chance to win material. |
| P4 | missed win | mate reached | Game move: misses checkmate. |
| P5 | either | neither | no type part |
| P6 | unknown (`material_loss` is NULL) | | no type part |

On blunder check this line replaces the four type sentences of its feedback paragraph ("The
blunder loses material." and the others). The hard-to-catch line stays in that paragraph, above
the divider, blunder check only: "Well spotted! This was one of the
tough ones we mix in on purpose." (caught) / "This one was hard to catch. We mix in a few tough
ones on purpose." (missed), when the snapshotted score is below 50%.

### Both parts together

The type part follows the tags after a comma, as one more item of the list.

| # | Condition | Sentence |
|---|---|---|
| C1 | allowed tag + P1 | Game move: allowed fork in 2, loses material. |
| C2 | allowed tag + P2 | Game move: allowed fork in 2, allows checkmate. |
| C3 | missed tag + P3 | Game move: missed fork in 2, misses a chance to win material. |
| C4 | missed tag + P4 | Game move: missed fork in 2, misses checkmate. |
| C5 | missed tag + P1 (sides differ) | Game move: missed fork in 2, loses material. |
| C6 | allowed tag + P3 (sides differ) | Game move: allowed fork in 2, misses a chance to win material. |
| C7 | both tags + P1 | Game move: missed fork in 2, allowed pin in 3, loses material. |
| C8 | allowed checkmate tag + P2 (checkmate rule) | Game move: allowed checkmate in 2. |
| C9 | missed checkmate tag + P4 (checkmate rule) | Game move: missed checkmate in 3. |
| C10 | allowed checkmate tag + P1 (checkmate rule) | Game move: allowed checkmate in 4. |
| C10b | missed checkmate tag + P1 (sides differ, both shown) | Game move: missed checkmate in 3, loses material. |
| C11 | tag dropped by depth + P1 | Game move: loses material. |
| C12 | blunder check, allowed tag + P1 | Game move: allowed fork in 2, loses material. |
| C13 | blunder check, allowed tag, no type part | Game move: allowed fork in 2. |
| C14 | no tag part, no type part | (the avatar adds nothing) |

Score part (Phase 264 D-23, owner 2026-11-28): C14 is no longer empty for a scored blunder.
With no tag and no type part the line says how hard the blunder was to spot, with its score:
"Ne7 ??: hard to spot (facepalm score 23%)." below 50%, "fairly easy to spot (...)" from 50% to
69%, "Ne7 ???: easy to spot (facepalm score 84%)." from 70%. Blunder check drops the band word
when its "hard to catch" line is shown: "Ne7 ??: facepalm score 23%." Only an unscored blunder
with nothing else known still gets no line. A tap on the icon opens the facepalm popover. D-25
(owner, same day): the band and the score close every scored line, as their own sentence after
a tag or a type part: "e6 ??: allowed fork in 1, loses material. Hard to spot (facepalm score
14%)." The resolver's test table carries these rows.

Checkmate rule: a checkmate tag suppresses the type part on the same side (allowed checkmate
with an allowed-loss type part, missed checkmate with a missed-win type part), so checkmate is
never said twice and never paired with "loses material" for the same side.

When the line is present on a puzzle it replaces "Step through the lines to see why." in the
verdict paragraph.

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
