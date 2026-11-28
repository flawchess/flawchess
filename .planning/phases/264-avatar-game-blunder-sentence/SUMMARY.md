# Phase 264 Summary: The avatar comments on the game blunder

Status: **done, merged to `main` 2026-11-28** (owner approved the spot-check, AC-13). Not deployed.
Branch `phase/264-avatar-game-blunder-sentence`. Written 2026-11-26, updated 2026-11-28 for
D-23 and D-25 (the facepalm score) and D-24 ("Also fine" in the verdict).

## What shipped

One line of additional info in the avatar's speech bubble, below a horizontal divider, on the
personalized puzzle reveal and on the blunder-check solution. It starts with the game move and
its quality icon and says what the blunder was:

> **e6** ??: allowed fork in 1, loses material. Hard to spot (facepalm score 14%).

The "??" / "???" badge opens the facepalm popover, as in the move list and the analysis move
strip (D-23). Every scored line ends with how hard the blunder was to spot and its score, in three
bands at the existing 50% and 70% cuts, as its own sentence after a tag or a type part (D-25) and
as the only item otherwise:

> **Qd7** ??: hard to spot (facepalm score 14%).

"fairly easy to spot" covers 50% to 69%, "easy to spot" 70% and up (the "???" cut). The score is
spoken only while the Game chip's grade is pending or a blunder, so text and glyph agree. Blunder
check drops the band word when its "hard to catch" line already shows ("Rab8 ??: facepalm score
26%."). Only an unscored blunder with nothing else known gets no line. Red herrings, false alarms
and "all good" windows never get one. "Also fine, e.g. ..." closes the puzzle's verdict paragraph
instead of sitting below the divider (D-24).

- **Backend.** The puzzle reveal's `game_move_facepalm` is replaced by a `flaw` block
  (`facepalm_score`, `facepalm_type`, `type_line`, `allowed_tactic`, `missed_tactic`; `null` for
  a herring, present for foreign puzzles). The score is the library's live
  `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` for a blunder, the type `facepalm_type_expr()`, both
  null when unscored; the client derives "???" with `isFacepalmBlunder` (the same 70% cut as
  `FACEPALM_STATS_MIN`). Blunder check's `feedback` gains `facepalm_type` from the snapshotted
  inputs, next to the snapshotted score. The reveal computes the type line for its one row from the stored lines with
  the function blunder check uses (`stored_type_line` / `stored_type_line_facts` in
  `app/services/blunder_check_feedback.py`); the type decision (`type_line_of`) no longer needs a
  facepalm score. The tag slots pass the analysis strip's gate through one new helper,
  `visible_tactic_slots` (`app/repositories/library_repository.py`). The blunder-check solution
  gains the two tag slots, read live from `game_flaws`. No migration.
- **Frontend.** One resolver (`frontend/src/lib/gameBlunderSentence.ts`) and one component
  (`frontend/src/components/train/GameMoveLine.tsx`) for both bubbles; the tag text is the
  strip's own function (`tacticSlotsText`, exported from `explainBar.ts`) in the strip's two
  colours. Puzzle: below the divider, in order, the line, "Also fine, e.g. ...", the return
  tail; the line replaces "Step through the lines to see why.". Blunder check: the four type
  sentences left the feedback paragraph, the hard-to-catch line stays above the divider.
- **Score sources (D-23, accepted).** Blunder check shows the serve-time snapshot of the score,
  the puzzle and the analysis show the live score. They agree today (both lambdas are 1.0) and
  can drift after a refit.
- **Cut pin.** `FACEPALM_HARD_TO_SPOT_BELOW = 50` (`lib/facepalm.ts`) is pinned to the backend
  `HARD_TO_CATCH_SCORE_BELOW` by `test_hard_to_catch_cut_is_the_frontend_hard_to_spot_cut`,
  like the 70% cut.

## Acceptance criteria

| # | Status | Evidence |
|---|---|---|
| AC-1 | pass | `frontend/src/lib/__tests__/gameBlunderSentence.test.ts`, "the seed table (AC-1)": 26 rows T1-T6, P1-P6, C1-C14 incl. C10b; D-21 rows in "a hanging-piece tag covers the material type part"; D-23/D-25 rows in "the facepalm score part" (all three bands and their edges 0.499 / 0.5 / 0.699 / 0.7, the band word dropped, a depth-cut tag leaving the score, the score as its own capitalized sentence after tags and type parts, always last). |
| AC-2 | pass, amended by D-23 | Same file, "nothing known and no numbers (AC-2)" (unscored input) and "an unscored blunder with nothing else known still gives no line". The score part carries the score's digits by design; there are still no numbers for material. |
| AC-3 | pass | Same file, "the depth cut (AC-3, D-10)"; `explainBar.test.ts` is unedited (`git diff main...HEAD --stat` does not list it) and green. |
| AC-4 | pass | Same file, "the strip is the source of the tag text": parts compared with `explainHeadline(...).tactics`. The score never changes the tag or type wording: "the score never changes the tag or type parts (AC-4)" (5 shapes x 4 scores x band word on/off; the score part is always last and the parts before it equal the unscored result). |
| AC-5 | pass | `tests/services/test_blunder_check_feedback.py`: `test_stored_line_swing_of_one_gives_no_line_and_two_the_material_line`, `test_stored_line_reaching_mate_gives_the_mate_line`, `test_stored_line_needs_a_known_loss_and_a_usable_line`, `test_type_line_of_needs_no_score`, `test_reveal_and_blunder_check_give_the_same_type_line`; `tests/routers/test_train.py::test_reveal_type_line_follows_the_swing_rule` (4 cases, unscored row). |
| AC-6 | pass | `test_reveal_key_set_excludes_stored_answer_key_fields` and the cross-user herring test (key set has `flaw`, herring `null`); `test_reveal_game_move_facepalm_score_and_type` (both sides of the cut, both types, mistake and unscored give nulls, no `facepalm` key); `test_reveal_foreign_facepalm_reads_owner_flaw` (the stranger's score and type); `test_solution_missed_and_caught_carry_the_snapshot_feedback` / `test_solution_feedback_mate_and_hard_to_catch` (`facepalm_type`); `grep -rn game_move_facepalm app frontend/src` is empty; `npm run build` and `npm run knip` clean. |
| AC-7 | pass | `tests/routers/test_train.py::test_reveal_tactic_slots_pass_the_strip_gate` (confidence 69 / 70 / decided lost); resolver test "a family-less motif produces no sentence". |
| AC-8 | pass, wording amended | `tests/routers/test_train_foreign.py::test_reveal_foreign_carries_the_flaw_block_without_the_game`; `TrainReveal.test.tsx` "a foreign puzzle gets the same neutral line"; resolver test "neutral subject". The line starts with the move, not "Game move:" (D-19); no line contains "your". The label assertions live in `gameBlunderSentence.test.ts` and the component tests, not in `trainBotCopy.test.ts` (that module holds none of this copy). |
| AC-9 | pass | `tests/routers/test_blunder_check_solution.py`: `test_solution_carries_the_gated_tactic_slots`, `test_solution_tactic_slots_are_live_not_snapshotted`, `test_solution_herring_and_false_alarm_carry_no_tactic_slots`; `blunderCheckSolution.test.ts` "solutionCopy feedback"; `BlunderCheckSolution.test.tsx` "avatar feedback paragraph". |
| AC-10 | pass, amended by D-24 | `TrainVerdictDetails.test.tsx` (17 tests) and `TrainReveal.test.tsx` "Phase 264" block; the strip line is untouched (`verdictStripLine`, existing tests green). D-24: "'Also fine' sits in the verdict paragraph before the look-closer line" and the extras order `game-move-line`, `train-bot-return-tail`. |
| D-23 badge | pass | `TrainVerdictDetails.test.tsx` "a scored blunder's icon opens the facepalm popover; without score or type it is plain" (aria-label, strip alignment class, four plain cases); `BlunderCheckSolution.test.tsx` opens the popover with a click and finds "Facepalm score 43%", and keeps a plain glyph without `facepalm_type`; `TrainReveal.test.tsx` "reports '???' to the board owner from the flaw block's score" (0.7 / 0.699). |
| AC-11 | pass, on 12 rows | See "Reveal cost". 4 -> 5 statements per reveal, about +4 ms. |
| AC-12 | pass | See "Browser UAT" (2026-11-26, and the D-23/D-24 re-run 2026-11-28). Screenshots in `temp/phase-264/shots/` (`d23-*`, `d24-*` for the re-run). |
| AC-13 | pass (owner approved, 2026-11-28) | `temp/phase-264/spot-check.md`: the same 30 rows with the line column regenerated (matched by FEN and move, 0 unmatched; a score column added), plus 9 score-only rows, 3 per band; regenerated again for D-25. |

## Measurements

### Share of puzzles with a line (prod, 2026-11-26, read-only)

2,000 `drill_items` rows (md5-ordered sample of the own-blunder pool), run through the reveal's
own functions and the frontend resolver (`temp/phase-264/sample_prod.py`, `sentences.ts`):

| | Rows | Share |
|---|---|---|
| Type line from the swing rule (server) | 1,064 | 53.2% |
| of which allowed material / missed material / allowed mate / missed mate | 635 / 355 / 65 / 9 | |
| A line is shown | 1,165 | 58.3% |
| Type part only | 640 | 32.0% |
| Tag and type part | 214 | 10.7% |
| Tag only | 311 | 15.6% |
| of which a type part covered by a hanging-piece tag (D-21) | 145 | 7.3% |
| A server tag cut by the depth rule (D-10) | 21 | 1.1% |
| Unscored rows / rows without `material_loss` | 49 / 33 | 2.5% / 1.7% |

So about 42% of puzzles show no line and keep the look-closer sentence. The owner's own rows
(n = 270) read 53.3% with a line.

Re-measured 2026-11-28 after D-23 (`sample_prod.py` extended to read the reveal's own score and
type expressions, read-only over the prod tunnel; a fresh md5-ordered draw of the same size, so
the counts move slightly; run through the bundled resolver):

| | Pool (n = 2,000) | Owner (n = 270) |
|---|---|---|
| A line is shown | 1,951 (97.5%) | 267 (98.9%) |
| Tag only / type part only / both | 309 / 643 / 213 (15.4% / 32.1% / 10.7%) | 37 / 75 / 32 |
| Score only (new) | 786 (39.3%) | 123 (45.6%) |
| of which hard to spot / fairly easy / easy | 646 / 76 / 64 | 106 / 12 / 5 |
| The badge opens the popover (score and type) | 1,918 (95.9%) | 267 (98.9%) |
| No facepalm score (unscored or no material) | 82 (4.1%) | 3 |

Expected effect met: lines go from 58% to 97.5% of puzzles; only unscored blunders get none. Of
the score-only lines 82% are "hard to spot": a blunder with no tag and no swing of 2 is mostly a
subtle one, so "hard to spot (facepalm score N%)" becomes the most common single line.

After D-25 (same sample, same resolver run): 1,918 lines (95.9%) carry the score, as the only
item on 786 and as a closing sentence on 1,132. Bands over all scored lines: hard to spot 1,136
(56.8%), fairly easy 223 (11.2%), easy 559 (27.9%); owner rows 181 / 28 / 58. Line length
including the icon, in characters: p10 41, median 58, p90 78, max 132, so a line with a tag or a
type part takes two lines on desktop.

### Reveal cost (dev DB, AC-11)

`temp/phase-264/time_reveal.py`: `reveal_for_puzzle` on every solved own puzzle of the dev DB
(12 rows; the dev DB has no more, so not the 20 the criterion names), 7 repeats each, median per
row, arms interleaved over 3 rounds:

| Round | Before (28b518593) | After | Statements |
|---|---|---|---|
| 1 | 3.65 ms | 13.76 ms | 4 -> 5 |
| 2 | 10.39 ms | 14.22 ms | 4 -> 5 |
| 3 | 10.44 ms | 14.62 ms | 4 -> 5 |

One extra query (three `game_positions` rows by primary key) plus the PGN replay. Rounds 2 and
3 give about +4 ms; round 1's "before" ran in a faster CPU state and is the outlier. Every
reading is under the 20 ms bound.

## Browser UAT (AC-12)

Run by Claude on the dev build, same-origin iframes at 1280x800 and 375x647, dev user 28.

| Scenario | 1280x800 | 375x647 |
|---|---|---|
| Own puzzle, tag and type line | line below the divider, look-closer gone | line in the expansion only, strip line unchanged (52 px) |
| Own puzzle, checkmate tag | "allowed checkmate in 3", no type part, "???" | |
| Own puzzle, nothing known | no line, look-closer shown | same |
| Foreign puzzle | neutral line, no Analyze, tail "From a similarly rated player's game..." | same |
| Herring | divider with "Also fine" and the tail, never a placeholder | same |
| Blunder check, caught | line below the divider, "Your call was right +2 ..." | same |
| Blunder check, missed | "Your call was wrong +0 ...", line below | same |
| Blunder check, all good | no divider, no line | |

D-23 / D-24 re-run (2026-11-28, dev sessions 369 and 370, blunder-check session of 12 windows):

| Scenario | 1280x800 | 375x647 |
|---|---|---|
| Own puzzle, tag and type, 30% | "e6 ??: allowed fork in 1, loses material.", tap opens the popover ("Facepalm score 30%"), bubble 175 px before and after | |
| Own puzzle, score only, 14% | "Qd7 ??: hard to spot (facepalm score 14%).", look-closer gone, bubble 151 px from verdict to settled | one line (25 px) in the expansion, popover opens, box 118 px before and after, no horizontal overflow |
| Own puzzle, "???" with hanging piece, 95% | | "c4 ???: allowed hanging-piece in 1.", `data-facepalm=true`, popover opens |
| Own puzzle, missed tag and type | | "g6 ??: missed fork in 1, missed a chance to win material." wraps to two lines (49 px, the known phone limit) |
| Blunder check caught, 91% | "Rdc1 ???: loses material.", popover opens, panel 604 px before and after | |
| Blunder check missed, hard to catch, 10% | "gxf5 ??: loses material." under the hard-to-catch line | |
| Blunder check missed, score only, 26% | "Rab8 ??: facepalm score 26%." (band word dropped under the hard-to-catch line) | |
| Blunder check caught, score only, 74% | | "Ne4 ???: easy to spot (facepalm score 74%).", two lines in the expansion; the solution renders at once, so nothing jumps |
| Herring (D-24) | "... Also fine, e.g. b6, Ne7, Be7, h6." in the verdict, divider with the tail alone | |
| Own soft puzzle (D-24) | "... played the best one +2. Also fine, e.g. Bf5, b6.", below the divider the line and the tail; bubble 171 px from verdict to settled | same text in the expansion |
| D-25, tag and score (dev session 371) | "Nh5 ???: allowed hanging-piece in 1. Easy to spot (facepalm score 94%).", two lines (42 px), bubble 191 px from verdict to settled with the two-line slot | |
| D-25, type and score, soft puzzle | "Nxb5 ???: loses material. Easy to spot (facepalm score 90%)." The bubble flickered 171 -> 190.5 -> 171 -> 190.5 px: the live "Also fine" list (D-24) crossed a line break and dropped back. Fixed with the never-shrink ratchet; probe: forcing a wrap grows 125 -> 145 px and restoring the text stays at 145 | |
| D-25, score only, 86% | "Kc2 ???: easy to spot (facepalm score 86%).", 171 px from the placeholder to settled (one spare line held) | |
| D-25, chip graded "?" (stored blunder, 1%) | no line: the score is not spoken next to "?"; 171 px steady | |
| Another soft puzzle, list "Qe3" -> "Qe3, Kb1" -> "Qe3" -> "Qe3, Qf3" -> "Qe3, Kb1, Qf3" within 2.3 s | the list stayed on one line, 191 px steady | |
| After the second review (dev session 372), score only | placeholder from 541 ms, "Ba4 ??: hard to spot (facepalm score 16%)." appears complete with its icon at 2,185 ms when the grade lands; 191 px throughout | |
| After the second review, tag, type and score | placeholder from 426 ms, "Kd2 ??: allowed discovered-attack in 3, loses material. Fairly easy to spot (facepalm score 55%)." at 2,095 ms, two lines; 171 px throughout | |

Bubble height when the reveal lands (desktop card, measured with a MutationObserver): 151 px
while pending, 151 px with the line, 151 px when the icon arrives 2.8 s later. An earlier build
read 173 -> 174.5 px (the bold mono move makes the line box taller than plain text); the
placeholder is now built like the real line.

The foreign and herring puzzles were produced by editing unsolved `drill_solves` rows of dev
sessions (source, herring pool id); user 28 has too many own blunders to get them naturally.

## Independent review

`/code-review medium` on `main...HEAD` (fresh reviewer, 2026-11-26), 8 findings:

| Finding | Outcome |
|---|---|
| A timed-out blunder read "Your call was wrong" (no call was made) | **Fixed.** The solution carries `timed_out`; the verdict reads "Time ran out before your call +0". Proven by reverting: `test_solution_says_whether_the_blunder_timed_out` and `blunderCheckSolution.test.ts` "a timed-out blunder is not called a wrong call" fail without the fix. |
| `visible_tactic_slots_at` filters `game_flaws` without `user_id` | **No change.** Prod EXPLAIN ANALYZE: index scan on `ix_game_flaws_game_id`, 0.52 ms. |
| Placeholder reserves one line; a two-tag line wraps on phones | **Accepted, documented** in `useHeightLatch`: reserving the worst case leaves blank room on most puzzles. See deviations. |
| Latched min-height stays after a rotation or resize | **Fixed:** the latch is dropped on window resize. |
| Old clients lose "???" (`game_move_facepalm` removed) | **No change:** accepted in CONTEXT.md ("Old clients"). |
| Empty icon box when the game-move search fails | **Fixed:** the glyph falls back to the stored severity (blunder; prod pool is 6,778 blunders and 1 mistake) when the chip's search failed or the move has no UCI. |
| Icon (client grade) and text (stored flaw) can disagree | **No change:** the icon follows the Game chip on purpose (D-19), so line, chip and board badge agree. |
| Look-closer held back during the reveal's retry | **Fixed:** the line stops counting as pending after the first failed attempt. |

`/code-review medium` on `95520d9af..129bf1d3d` (the D-23 / D-24 diff, fresh reviewer,
2026-11-28), 5 findings:

| Finding | Outcome |
|---|---|
| A score-only line could follow a "?" glyph: the text took the score whatever the Game chip's grade, the badge only for a blunder ("Ne7 ?: easy to spot (facepalm score 84%).") | **Fixed.** The puzzle speaks the score only while the chip grade is pending or a blunder. Proven by reverting: `TrainReveal.test.tsx` "a score-only line follows the Game chip's grade: mistake" fails without the gate. |
| A score-only line replaces "Step through the lines to see why." | **No change, owner question.** D-08 makes every line replace it. Keeping both would grow the bubble when the reveal lands (one line is reserved). Recorded in STATE.md. |
| The band reads the floored percent, blunder check's hard-to-catch the raw score | **No change.** Rounding is monotone: no score below 0.5 multiplies to 50 or more, so floor(score x 100) < 50 exactly when score < 0.5. |
| The popover badge's box sits on a different element than the plain glyph's | **No change.** The UAT bubble heights span the moment the glyph swaps and did not move (151 px, 171 px). |
| `_FACEPALM_CUT = 0.7` duplicated in a test | **Fixed:** imports `FACEPALM_STATS_MIN`. |

`/code-review medium` on `39c576637..9c8df96e7` (the D-25 diff, fresh reviewer, 2026-11-28),
6 findings:

| Finding | Outcome |
|---|---|
| With D-25 the score sentence could show while the Game chip was still grading and vanish ~3 s later when the grade landed as "?", now on every scored line | **Fixed.** A scored line stays a reserved placeholder until the grade settles, then appears once, complete. Proven by reverting: `TrainReveal.test.tsx` "a scored line waits for the Game chip's grade and appears once, complete" fails without it. |
| The never-shrink ratchet had no test (the setup's ResizeObserver stub never fires) | **Fixed:** `TrainVerdictDetails.test.tsx` "only grows during a verdict" with a firing stub; fails when the ratchet overwrites instead of raising. |
| A window resize dropped the latch and nothing re-took it (a phone toolbar hiding fires `resize` without a size change) | **Fixed** (pre-existing, one line): the resize handler re-measures at the new width. "a window resize re-measures at the new width" fails without it. |
| `useHeightLatch`'s doc sat on top of `ratchet`'s | **Fixed.** |
| A comment in `blunderCheckSolution.ts` still described D-23 | **Fixed.** |
| SUMMARY's AC-4 row named a renamed test | **Fixed.** |

## Deviations from CONTEXT.md

- **Look-closer sentence** (owner, 2026-11-28, answering the D-23 review): a score-only line
  replaces "Step through the lines to see why." like every other line (D-08 unchanged).

- **D-23 and D-24** (owner, 2026-11-28): the facepalm score behind the badge and as the line of
  an otherwise empty line, in three bands (the owner chose bands over a bare "Facepalm score
  23%", which the brief had named, and over hiding the score); "Also fine" into the verdict
  paragraph. Recorded in CONTEXT.md under "Amendments during implementation".
- **The score part is not `nowrap`**, unlike the strip's "Facepalm score 76%": the band text is
  longer and would overflow at 375 px.
- **D-25** (owner, 2026-11-28): the score sentence on every scored line, not only on an otherwise
  empty one. A scored puzzle line now appears when the Game chip's grade lands (about 1 to 3 s
  after the reveal), not when the reveal lands; the reserved slot covers the wait. Consequences: the reveal's reserved slot is two lines (a score-only line leaves one
  spare line, about 39% of puzzles), and the verdict body never shrinks during a verdict, a
  ratchet added after the UAT showed the live "Also fine" list (D-24) flickering the bubble
  height. A line with two tags, a type part and the score can still wrap to a third line on
  phones.

- **D-21** (owner, spot-check 2026-11-28): a hanging-piece tag suppresses the material type part
  on the same side. Hanging piece was the tag in 145 of the 359 sampled tag-plus-type lines, so
  this is the rule's biggest single effect on the copy.
- **D-19 and D-20** (owner, during UAT): the subject is the move and its icon, and blunder
  check's verdict says "Your call was right / wrong" without naming the blunder. Recorded in
  CONTEXT.md under "Amendments during implementation".
- **A long line can still grow the bubble on phones.** Two lines are reserved since D-25 (one
  before); a line with two tags, a type part and the score wraps to a third line at 375 px and
  the bubble grows by one line when it lands. Reserving the worst case would leave more blank
  room on most puzzles.
- **The reserved slot costs a spare line when the line is shorter.** While the reveal loads,
  the bubble reserves the line's slot and latches that height (`useHeightLatch`). A score-only
  line (about 39% of puzzles) fills one of the two lines, and no line (about 2.5%) fills none;
  the rest stays as blank space at the bottom of the bubble unless the look-closer sentence
  wraps into it. That is the price of "must not jump".
- **AC-11 on 12 rows**, not 20 (see above).
- **One existing test narrowed.** `BlunderCheckSolution.test.tsx` forbade the words "you
  played" anywhere on a foreign solution. D-20's "and you played a good move, Nc3" is about the
  user's own better move, so the test now forbids that claim about the game move ("you played
  Nf3", "your move", "your blunder").
- **The reveal reads three `game_positions` rows, not two**: the row at ply - 1 carries the
  pre-move eval the decided-lost gate needs. Still one query.

## Learned

- The swing rule gives a type line for about half of the pool, far more than tags do (26%); the
  type part carries the feature.
- A slot reserved with plain text is not the height of a line with a bold mono span and an
  inline icon box. Build the placeholder from the real component.
- Dev sessions are compose-or-resume per clock day: composing at a later dev-clock offset
  expires the earlier open session, so set up UAT rows only on the latest one.

- A spoken claim needs the same gate as its badge: text and glyph of one line came from two
  sources (the stored flaw, the client's grade) and could disagree; the review caught it, the
  tests had not.

## Deferred

- Blunder-check windows with nothing known no longer name the blunder in the bubble text
  (D-20). If that turns out to be missed, a bare "Qe5 ??" line is the obvious follow-up.
- The puzzle verdict still says "you missed it +0" about the best move; untouched here.
- Re-measuring tag coverage and quality after Phase 252 (seed trigger).
