# Phase 264: The avatar comments on the game blunder (SEED-261126-g8b)

Status: **locked, 2026-11-26**. All decisions (D-01 to D-18) are confirmed by the owner. Ready
for the plan and the implementation.

Branch: `phase/264-avatar-game-blunder-sentence`. Seed:
`.planning/seeds/SEED-261126-g8b-avatar-game-blunder-sentence.md` (coverage numbers and the ideas
already ruled out live there and are not reopened here).

## Goal

After a personalized puzzle or a blunder-check window, the avatar's speech bubble shows one line
of additional info below a divider that says what the game blunder was: the tactic it allowed or
missed, and whether it loses material or misses winning material. One shared line for both
surfaces, for example "Game move: allowed fork in 2, loses material."

## Locked decisions

- **D-01 One type rule on both surfaces: swing >= 2** (owner, 2026-11-26, final after weighing
  a threshold on the stored decaying mean and rejecting a second rule). The puzzle uses the
  shipped blunder-check rule and the same server code:
  - side: `facepalm_type_of(material_loss, material_missed)` of the flaw row;
  - facts: `type_line_facts` replays the stored Stockfish lines of that one blunder (the line
    after the blunder for an allowed loss, the best line for a missed win) under the quiet rule
    and reads the material swing at the deepest settled depth, plus whether the line reaches a
    mate;
  - decision: a mate gives the mate line, else a swing of at least `TYPE_LINE_MIN_SWING = 2`
    gives the material line, else no type line.
  Shown for every blunder that passes, facepalm or not. A row without `material_loss` has no
  side and gets no type line.
  Where it runs: blunder check keeps its snapshot, taken when the window is served. The puzzle
  has no snapshot, so the reveal computes it for its one row: it already has the PGN and the
  flaw row and additionally reads the two stored lines (`game_positions.pv` and `best_move` at
  the flaw ply, `pv` at ply + 1). No migration.
  Why: one rule and one set of four lines for both surfaces; the undecayed swing separates "how
  much" from "how early", which the stored mean cannot.
- **D-02 Tactic tag.** Same visibility as the analysis move strip: server gate
  `tactic_slot_visible` (confidence >= 70, decided-lost suppression, no filters) plus the client
  family guard `resolveVisibleTactic(..., anchored = false)`. No looser gate.
  Why: a spoken sentence is a stronger claim than a chip.
- **D-03 Surfaces.** Blunder check gains the tag. The personalized puzzle gains tag and type line.
- **D-04 Neutral label "Game move:"** (owner, 2026-11-26; replaces the brief's "Your game move"
  / "The game move"). The line never says "your move" or "your game". Puzzle, own or foreign:
  "Game move: ...". Red herring: no line.
  Why: fillers come from other players' games and blunder check serves about 50% foreign games,
  so a neutral label is right everywhere and needs no ownership branch. The existing verdict
  line "Several moves work here, just not your game move." is ownership-gated already and is not
  touched by this phase.
- **D-05 Nothing known.** No tag and no type line: the avatar adds nothing. No filler, and never
  numbers for material.
- **D-06 "Hard to catch"** stays blunder-check only.
- **D-07 Reveal schema.** The puzzle reveal gets a small flaw block that replaces
  `game_move_facepalm`.
- **D-08 Placement: additional info under a divider** (owner, 2026-11-26). The line sits in the
  avatar's speech bubble below a horizontal divider, apart from the verdict. No line, no
  divider. From the brief: when the line is present it replaces "Step through the lines to see
  why."; on phones the collapsed strip line stays as it is and the line shows in the expansion
  only.
- **D-14 The return tail moves below the divider too** (owner, 2026-11-26). The puzzle bubble
  already has a divider block (`train-verdict-extras` in `TrainVerdictDetails.tsx`, today only
  "Also fine, e.g. ..."). Below the divider, in this order: the "Game move:" line, "Also fine,
  e.g. ...", then the return tail ("Back in 4 days.", "Back next session.", and the mastered,
  parked, herring and foreign tails, wording unchanged). Above the divider only the verdict
  paragraph remains. The divider shows when any of the three lines exists. Blunder check has no
  return tail.
- **D-09 One resolver.** One pure frontend function builds the comment for both surfaces from
  (subject, tag slots, type line). Neither surface keeps its own copy table for these lines.
- **D-10 Deep tactics are not commented** (owner, 2026-11-26). A tag at depth 6 or more is left
  out of the avatar's comment, unless it is a checkmate. Read as the number the user sees ("in
  6"), which is the stored 0-based depth + 1 in the strip's unanchored display. The strip itself
  is unchanged. A blunder whose only tag is dropped this way still gets its type line.
- **D-11 No facepalm wording** (owner, 2026-11-26). The "???" icon already says it. The facepalm
  flag only picks the badge, as today, and never changes the avatar's text.
- **D-12 Tags in the strip's form, not in sentences** (owner, 2026-11-26). The tags appear as the
  move strip writes them: "missed fork in 2, allowed pin in 3", every visible tag, missed first,
  in the strip's two colours. No articles, no per-family verb phrases.
  Why: full sentences need hand-written wording per family and still read badly for several.

- **D-15 Copy** (owner, 2026-11-26). The full list of lines with their conditions is the seed's
  section "Possible Sentences And Their Conditions" (IDs T1 to T6, P1 to P6, C1 to C14); it is
  the reference for the resolver's table-driven test.
  - Form: `Game move: <item>[, <item>].` Items are the visible tags in the strip's form (after
    the D-10 depth cut, missed first), then the type part.
  - Type part: "loses material", "allows checkmate", "misses a chance to win material", "misses
    checkmate".
  - Examples: "Game move: allowed fork in 2, loses material." / "Game move: loses material." /
    "Game move: missed fork in 2, allowed pin in 3."
- **D-16 Blunder check uses the same line** (owner, 2026-11-26). Its solution bubble gets the
  same divider and the same "Game move:" line from the same component. The shipped type
  sentences ("The blunder loses material." and the three others) are removed from its feedback
  paragraph. The hard-to-catch line stays in that paragraph, above the divider, wording
  unchanged (D-06). False alarms and "all good" windows get no line.
- **D-17 A checkmate tag suppresses the type part on the same side** (owner, 2026-11-26). An
  allowed checkmate tag drops an allowed-loss type part (material or mate), a missed checkmate
  tag drops a missed-win type part. Tags and type parts on different sides are both shown.
  Why: avoids "allowed checkmate in 2, allows checkmate" and "allowed checkmate in 4, loses
  material".
- **D-18 Tag order** (owner, 2026-11-26). With both tags visible, both are shown, missed first,
  as the strip does. Nothing depends on the puzzle type.

- **D-13 Games before 2026: no gate** (owner, 2026-11-26). No date gate; the comment accepts the same exposure the blunder-check type line has.

Measured on prod, 2026-11-26, own-blunder pool (`drill_items`):

| Game played | Rows | Refutation line <= 2 plies | Best line <= 2 plies |
|---|---|---|---|
| before 2026 | 179 (2.6%) | 1.7% | 0.6% |
| 2026 | 6,587 | 3.2% | 0.5% |

- Pre-2026 games are 2.6% of the pool, and their stored lines are not shorter than those of 2026
  games.
- The type-line rule already degrades safely on a short line: nothing settled gives no line, and
  a mate counts only when the stored line reaches it.
- The move strip shows the same tags for the same games today.
- A cut-off date would be a constant to remove again once Phase 252 finishes.

What this does not show: line length says nothing about whether a tag derived before the repair
is stale. That needs the Phase 252 retag (plan 252-07), for games of any date. Not measured.

## Amendments during implementation (owner, 2026-11-26, in the UAT session)

- **D-19 The line starts with the move and its quality icon**, replacing the fixed "Game move:"
  label of D-04, D-08, D-15 and D-16: "Ne7 ???: allowed fork in 2, loses material." The icon is
  the Game chip's glyph ("??", or "???" for a facepalm blunder), aligned like the badge of the
  analysis move strip. D-04's point stands: the line never says "your". "Game move:" remains
  only as the fallback when the move's SAN is unknown. Wherever this file or the seed's sentence
  list writes "Game move: ...", read "<move> <icon>: ...".
- **D-20 Blunder check's verdict no longer names the blunder.** "Qe5 was a blunder. You missed
  it +0 and found the best move, Re5 +1." became "Your call was wrong +0 and you found the best
  move, Re5 +1." (caught: "Your call was right +2 ..."). Why: with the blunder named below the
  divider the first sentence is redundant, and "You missed it" next to that line read as if
  "it" were something other than the call.
  Consequence: a window with nothing known (no tag, no type line) has no line, so its bubble
  names the blunder only through the heading and the Game chip.

- **D-21 A hanging-piece tag suppresses the material type part on the same side** (owner,
  2026-11-28, spot-check). "allowed hanging-piece in 1, loses material" becomes "allowed
  hanging-piece in 1", "missed hanging-piece in 1, misses a chance to win material" becomes
  "missed hanging-piece in 1". Why: the tag already says the piece goes, and a hanging piece is
  hardly a tactic worth a second clause. Same shape as D-17: different sides are both shown, and
  a mate type part ("allows checkmate") is kept because it says something new.

- **D-22 Missed-win type parts in the past tense** (owner, 2026-11-28): "missed a chance to win
  material" and "missed checkmate" instead of "misses ...", to match the tags' "missed".
  ("missed checkmate" never meets a "missed checkmate in N" tag: D-17 drops the type part then.)
  The allowed side stays present tense on purpose: "lost material" / "allowed checkmate" would
  claim it happened in the game, while the line only says what the move allows. A missed win did
  happen: the move missed it.

- **D-23 The facepalm score: behind the icon, and the line's text when nothing else is**
  (owner, 2026-11-28; partly reverses D-11).
  - The "??" / "???" icon at the start of the line is the move list's `FacepalmGlyphBadge`. A tap
    opens the facepalm popover (score and type in words), as in the move list and the analysis
    move strip, with the strip's alignment. Without a score or a type, or when the Game chip
    grades the move other than a blunder, the icon stays the plain glyph. One popover testId,
    `train-game-move-facepalm-popover`, for both surfaces (the Umami target).
  - A line with no tag and no type part says how hard the blunder was to spot, in three bands
    at the app's two existing cuts, with the score: "hard to spot (facepalm score 23%)" below
    50% (blunder check's `HARD_TO_CATCH_SCORE_BELOW`), "fairly easy to spot (...)" from 50% to
    69%, "easy to spot (...)" from the 70% "???" cut (`FACEPALM_STATS_MIN`). Percent floored
    (`toFacepalmPct`); the bands read the floored percent. With a tag or a type part the score
    stays behind the icon, never in the text, and it never changes the tag or type wording.
  - Blunder check drops the band word when its "hard to catch" line is shown above the divider
    (same 50% cut, pinned across stacks by test): "facepalm score 23%".
  - Why: the owner wants the score visible. The popover reuses the analysis surface instead of
    a new one. A bare "Facepalm score 23%" is jargon in a speech bubble, so the avatar says what
    it means, in words the popover already uses ("easy to see", "probably hard to see"). The
    bands add no new threshold. The words are needed only on a line that would otherwise be
    empty; next to a tag or a type part they would crowd it.
  - Wire: the puzzle reveal's flaw block carries `facepalm_score` (raw 0..1, the library's live
    `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`, blunders only) and `facepalm_type` instead of
    `facepalm: bool`; the client derives "???" with `isFacepalmBlunder` (the same 70% cut).
    Blunder check's `feedback` gains `facepalm_type` from the snapshotted inputs, next to the
    snapshotted `score`. So blunder check shows the serve-time snapshot, the puzzle and the
    analysis the live score. They agree today (both lambdas are 1.0) and can drift after a
    refit; accepted.
  - Amends: D-05 now reads "nothing known and no score: no line"; AC-2's "no digit other than a
    tag depth" excludes the score part (still no numbers for material); AC-4's "the facepalm
    flag never changes the comment" holds for the tag and type parts.

- **D-24 "Also fine, e.g. ..." is part of the verdict paragraph** (owner, 2026-11-28; amends
  D-14). On the personalized puzzle and the herring the sentence closes the verdict paragraph
  above the divider ("... played the best one +2. Also fine, e.g. Bf5, b6."), before the
  look-closer sentence when that shows, so it never moves when the reveal decides the
  look-closer. Below the divider only the game-move line and the return tail remain; the
  divider shows when either exists. Test id `train-reveal-also-fine` unchanged.
  Why: the alternatives answer the verdict ("several moves work here"), they are not
  additional info about the game blunder.

- **D-25 The score sentence on every scored line** (owner, 2026-11-28; amends D-23). The band
  and the score close every line of a scored blunder, as their own sentence after a tag or a
  type part: "e6 ??: allowed fork in 1, loses material. Hard to spot (facepalm score 14%)." Alone
  they stay the line's only item ("Qd7 ??: hard to spot (facepalm score 14%)."). Blunder check
  still drops the band word under its hard-to-catch line ("gxf5 ??: loses material. Facepalm
  score 10%."). The score never changes the tag or type wording; it is spoken only while the
  Game chip's grade is pending or a blunder (review fix of D-23).
  Consequences: a line with a tag or a type part now wraps to two lines on desktop (prod sample:
  median 58 characters, p90 78, max 132), so the reveal's reserved slot is two lines instead of
  one; a score-only line then leaves one spare line. The verdict body also never shrinks during
  a verdict (a ratchet), because the live "Also fine" list (D-24) can cross a line break and drop
  back while the engine reports alternatives. A score-only line replaces the look-closer
  sentence like every other line (owner, 2026-11-28; D-08 unchanged).

## Consequences of the decisions

- **Facepalm on the wire** (D-11, superseded by D-23): first a boolean for the badge only;
  since D-23 the raw score and the type (see D-23).
- **Flaw block shape** (puzzle reveal, `None` for a herring): `facepalm_score`, `facepalm_type`, `type_line`
  (`TypeLine | None`), `allowed_tactic` and `missed_tactic` (each `{motif, depth}` or `None`,
  already nulled by the server gate).
- **Unscored blunders** (3.8% of the pool) still get a type line when `material_loss` is known.
  `blunder_feedback` returns nothing without a score today, so its type decision is split out
  into a function both callers share; the score keeps driving only "hard to catch".
- **Shared replay helper.** `_board_before_ply` and `_type_line_facts_for` live in
  `blunder_check_selection.py` and take that module's batch object. The reveal needs the same
  step for a single row, so the core moves to a small function both call. No behaviour change
  for blunder check.
- **Coverage is not measured.** The swing is not a column, so the share of puzzles that get a
  type line is unknown until the code runs; the phase reports it in `SUMMARY.md` from a sample
  of prod rows.
- **Foreign puzzles** get the line too. Motif, depth and type line identify nobody; the game
  id stays withheld and `has_tactic_lines` stays false.
- **Old clients.** A frontend loaded before the deploy reads `game_move_facepalm`, which is gone,
  and shows "??" instead of "???" until it reloads. Accepted, no compatibility field.
- **Layout.** The reveal query resolves after the verdict is on screen. The line and its divider appear
  then, so the bubble must not change height when it arrives
  (`frontend/CLAUDE.md`, reserved slots).

## Deferred

- Re-measuring tag coverage and tag quality after Phase 252 (seed trigger).
- Cross-game patterns ("your fourth missed fork this month"): own seed if wanted.
- Everything under "Considered And Dropped" in the seed.

## Acceptance criteria

Each maps to a test or a named manual check. Test names are targets, to be created in this phase.

1. **AC-1** The resolver returns the agreed line for every row of the seed's sentence list
   (T, P and C rows, including the D-17 checkmate rows C8 to C10). Test: `frontend/src/lib/__tests__/gameBlunderSentence.test.ts`, table-driven.
2. **AC-2** No visible tag and no type line gives no comment; no comment ever contains a digit
   other than a tag depth. Test: same file.
3. **AC-3** Depth cut (D-10): a non-mate tag shown as "in 5" is kept and "in 6" is dropped, a
   checkmate tag is kept at any depth, and a dropped tag leaves the type line in place. The
   analysis strip's own output is unchanged. Tests: same file, and `explainBar.test.ts` stays
   green without edits.
4. **AC-4** The tag text of the comment equals the strip's text for the same slots (one shared
   function, asserted against `explainTactics`), and the facepalm flag never changes the
   comment. Test: same file.
5. **AC-5** Puzzle type line: a swing of 1 at the deepest settled depth gives no line, a swing of
   2 the material line, a mate reached in the stored line the mate line; an unscored row with
   `material_loss` still gets its line; a row without `material_loss`, or with no usable stored
   line, gets none. For the same blunder the puzzle reveal and a blunder-check window give the
   same type line (one shared function, asserted on a fixture). Tests:
   `tests/services/test_blunder_check_feedback.py` (extended) and the backend reveal test.
6. **AC-6** The reveal response carries the flaw block for own and foreign puzzles, `None` for a
   herring, and `game_move_facepalm` no longer exists in schema, repository or frontend types.
   Test: reveal tests in `tests/` (router and repository), plus `npm run build` and `npm run knip`.
7. **AC-7** Tag gate on the reveal: confidence 69 is nulled, 70 passes, a decided-lost pre-move
   position nulls both slots, a family-less motif produces no sentence. Tests: backend reveal
   test for the server gate, resolver test for the family guard.
8. **AC-8** Foreign reveal: the flaw block is present, `game_id` is null, `has_tactic_lines` is
   false, and the line starts with "Game move:". An own puzzle's line starts the same way, and no line
   on either surface contains "your". Tests: backend reveal test and
   `trainBotCopy.test.ts`.
9. **AC-9** Blunder check: the solution carries the tag slots under the same gate, the bubble shows
   the shared "Game move:" line below a divider (D-16), the four type sentences are gone from
   the feedback paragraph, the hard-to-catch line is still shown above the divider, and false alarms and herrings show neither. Tests:
   `blunderCheckSolution.test.ts` and the blunder-check service solution test.
10. **AC-10** Puzzle verdict: with a sentence, "Step through the lines to see why." is not shown;
    without one it shows as before for the 0 and 1 point buckets; the phone strip line is
    unchanged. Test: `trainBotCopy.test.ts` and the `TrainVerdictDetails` component test.
    The return tail renders inside the divider block, below the game-move line, with its
    wording and test ids unchanged; a herring shows the divider with its tail alone. Test: same
    component test.
11. **AC-11** Reveal cost: the reveal adds one query (the two `game_positions` rows) and under
    20 ms on the dev DB. Manual check: time 20 reveals before and after on the branch, numbers
    in `SUMMARY.md`.
12. **AC-12** Browser UAT by Claude at 375x647 and 1280x800: own puzzle with tag and type line,
    own puzzle with nothing known, foreign puzzle, herring, blunder check caught and missed. The
    bubble does not change height when the reveal arrives; screenshots in `temp/phase-264/`.
13. **AC-13** Owner spot-check of the copy: about 30 real comments drawn from prod rows (mixed
    tag families, both type sides, depths on both sides of the D-10 cut), read against the
    positions before merge.
    Named manual check, result recorded in `SUMMARY.md`.
