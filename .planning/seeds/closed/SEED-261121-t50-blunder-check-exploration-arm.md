---
id: SEED-261121-t50
status: closed
closed: 2026-11-22
closed_reason: implemented as Phase 261 (20% exploration draw without the score cut, serve-time snapshot on blunder_check_windows, avatar feedback, calibration script); merged to main 2026-11-22, not yet released
promoted_to: Phase 261 (2026-11-22)
planted: 2026-11-21
planted_during: Phase 259 execution (facepalm first-principles refit), /gsd-explore session with the owner
trigger_when: after the Phase 259 switch release is live on prod and the prod backfill of loss, missed and the best-reply probability is complete (rows without them are unscored)
scope: medium. One phase. A drill-selection change, new columns on blunder_check_windows, one constant change, an analysis script
---

# SEED-261121-t50: Blunder-check exploration arm (20% of blunder windows, random draw with no score cut) beside a 70% main cut

Serve about 20% of blunder windows from a random draw with no facepalm-score cut, flagged as
exploration windows. The other 80% keep the main cut of 0.70, which Phase 259 sets.

**Promoted 2026-11-22 to Phase 261** (`.planning/ROADMAP.md`).

## Why This Matters

- The drill only serves blunders at or above `FACEPALM_SCORE_MIN`. User answers can therefore
  never validate or refit the facepalm score below the cut (range restriction). The score is fitted
  on 268 owner labels that the owner calls "very subjective" (259 D-01).
- Phase 259 CONTEXT lists both parts as deferred: "Blunder-check sequences with any facepalm score"
  and "A fit on user blunder-check answers".
- Separately, the leaderboard score % shows the drill is a bit too hard. The owner wants it easier,
  and expects a 0.70 cut to help.

## Owner Decisions (2026-11-21)

1. **Main arm:** `FACEPALM_SCORE_MIN` goes from 0.50 to 0.70, in units of the Phase 259 score.
   Purpose: lower drill difficulty. **The owner raises it in Phase 259,** at the D-15 checkpoint
   (final word, 2026-11-21, reversing "in this phase" from earlier in the same session). This
   phase does not change the cut; it assumes 0.70 is live when it starts.
2. **Exploration arm:** about 20% of blunder windows (the owner's first proposal; 10% was considered
   in the session and dropped for the faster collection).
3. **The draw is random, with no score threshold** (decided by the owner at the end of the
   session: "the random drawn data would still be valid" when the score changes). The exploration
   arm is then a plain sample of what the drill would serve with no cut, usable for any future
   score without weights, and it answers "what would the caught rate be at cut X under model Y"
   directly. A draw by score band was considered and rejected; see "Random draw or bands" under
   Evidence.
4. **Exploration windows count as normal:** points, streaks, medals, leaderboard. No marker the
   user can see.
5. **The avatar feedback (score, type line, "hard to catch" line) is part of this phase,** not
   shipped ahead of it. It reads the serve-time snapshot, and the window wire schema changes once.
6. **Both origins:** the exploration arm applies to own and foreign blunder slots alike, one coin
   flip of 20% per blunder slot. The score is meant to rank a player's own blunders too; the draw
   uses own blunders below the cut that the main arm never serves; `is_own` is already stored on
   the window for a split in the analysis. When the picked game has several eligible blunders, the
   exploration draw chooses among them at random, never by score.
7. **The arm runs indefinitely for now.** No review gate and no stop rule (the orchestrator had
   proposed reviews at about 500 and 2,000 exploration answers; the owner declined). The share is
   one named constant, so lowering or stopping it later is a constants change.

## Design Points (recommended in the session; the first two follow from owner decisions 5 and 6)

- **Randomise per blunder window,** not per user, so every user contributes to both arms and the
  comparison can be made within users.
- **Record at serve time on `blunder_check_windows`:** the arm, the sampling probability,
  and a snapshot of the score inputs (after 259: `loss`, `missed`, `maia_played_prob`,
  `maia_best_prob`, the best-reply probability), or at least the score. The score is a query-time
  expression that changes with every refit, and a deleted foreign game leaves the window with a
  NULL `game_id`, so a later join to `game_flaws` is not reliable.
- **Sequencing:** settled by owner decision 1. The cut goes to 0.70 with Phase 259, so nothing
  below 0.70 is served between the Phase 259 release and this phase. The owner accepts that gap
  for the easier drill; the random arm covers the whole range again once it ships.
- **Supply:** a 0.70 cut shrinks the qualifying pool, so more own slots convert to foreign slots.
  The pool size per user is checked at the Phase 259 D-15 checkpoint.
- **Analysis:** "caught" is not the owner's label. It depends on the user and on the blunder's
  position in the window, and a false alarm before the blunder ends the window unobserved. A fit on
  answers needs per-user terms. First deliverable: a calibration check (caught rate by score band
  with intervals), run whenever the owner wants it; no fixed date (owner decision 7). A refit
  only once a few thousand answers exist.
- **Free first check:** rescore the answers collected so far under the Phase 259 model and compare
  the old and the new score against the outcomes (limited to an old score of 0.50 or more).

## Avatar Feedback (owner idea, 2026-11-21)

After the answer, the avatar in the solution view shows the facepalm score and a line on the type:

- "The blunder allows a material loss" / "The blunder allows checkmate"
- "The blunder misses a material win" / "The blunder misses checkmate"
- **"Hard to catch" line (owner decision, 2026-11-21):** shown when the snapshotted score is below
  50% (a named constant, in Phase 259 score units, re-checked on the new score when the phase
  starts). Missed: "This one was hard to catch." Caught: "Well spotted, this one was hard to
  catch." It is tied to the score, never to the arm, and shows together with the score and the
  type line when there is one.

Notes from the session:

- The low-score line only fires in the exploration arm, since the main arm serves 0.70 and above.
  It is the fairness mitigation for counting exploration windows as normal. It comes after the
  answer, so it does not bias that answer; users may learn that subtle blunders appear and flag a
  little more.
- **One classification:** the solution view already receives `window_case` (allowed, pure miss,
  mixed). The comment should read the facepalm type (allowed loss, missed win), the rule the score
  and the library stats use, not a second one.
- **Type line rule (owner decision, 2026-11-21):**
  - Side: the facepalm type (allowed loss or missed win).
  - A line shows only if that side's real material swing in the engine line is at least 2 points
    (piece values 1 / 3 / 3 / 5 / 9), or the line ends in mate. A lost pawn gets no line; a lost
    exchange (2) does.
  - Mate: "The blunder allows checkmate" / "The blunder misses checkmate".
  - Otherwise no type line. This covers positional blunders and pawn-sized swings.
  - Source: the stored `loss` and `missed` are decaying means (a knight lost from depth 3 on is
    1.45), so the floor is not applied to them. For the one blunder a window serves, the drill
    walks the stored engine lines with Phase 259's quiet-point rule at serve time and stores the
    swing and the mate fact on the window, next to the score snapshot. No new `game_flaws` column,
    and no dependency on Phase 259 keeping the mate-ply columns.
  - To check at planning: the engine line of the best move must still be stored after Phase 259,
    not only the refutation line.
- **Unreached blunders:** the solution view never reveals the case of a blunder the user did not
  reach (249 D-10, a false alarm earlier in the window). Score and type lines show only when the
  blunder was caught or missed.
- **Deferred (owner decision, 2026-11-21): a one-tap "unfair" flag on the feedback.** Not in this
  phase. Reasons: thin and biased data at about 30 active users (mostly taps after a miss); many
  raters at different ratings are not the owner's label ("should score above 70%"); extra control,
  field and copy. Revisit if the caught rate tracks the score poorly even on the random sample.
- The score shown is the serve-time snapshot (Design Points), so it stays stable across refits.
- Copy stays neutral about whose blunder it is: many served blunders are from other users' games.
- Code: `frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx`
  (`SolutionVerdict`), `app/schemas/blunder_check.py` (the window wire schema carries no score
  today).

## Evidence (prod, 2026-11-21, pre-259 score, orders of magnitude only)

- 233 answered blunder windows from 29 users since 2026-11-19, about 80 a day. At 20% that is
  about 16 exploration answers a day, about 480 a month.
- Caught rate among reached blunders, by score:

| Score | n | Caught | False alarm before the blunder |
|---|---|---|---|
| 0.5 to 0.6 | 42 | 39% | 6 |
| 0.6 to 0.7 | 30 | 50% | 4 |
| 0.7 to 0.8 | 34 | 29% | 6 |
| 0.8 to 0.9 | 29 | 59% | 0 |
| 0.9 to 1.0 | 99 | 69% | 9 |

- Overall caught rate 55%; 59% at 0.7 and above, 44% in 0.5 to 0.7. The 0.70 cut alone makes the
  drill only modestly easier. If the leaderboard still looks too hard afterwards, look at the
  herring share, the window length or the timing.
- Natural distribution of scored blunders (1% sample, 44,209 rows): below 0.3 42.3%, 0.3 to 0.5
  13.7%, 0.5 to 0.7 12.1%, 0.7 and above 31.8%. A random draw puts 56% of the exploration
  windows below 0.5 and about 12% in 0.5 to 0.7.
- **Random draw or bands** (20% of about 80 blunder windows a day, old-score distribution):

| | Random, no threshold | Random below 0.7 | Three equal bands below 0.7 |
|---|---|---|---|
| Answers per day below 0.3 | 6.8 | 9.9 | 5.3 |
| Answers per day in 0.3 to 0.5 | 2.2 | 3.2 | 5.3 |
| Answers per day in 0.5 to 0.7 | 1.9 | 2.8 | 5.3 |
| Answers per day at 0.7 and above | 5.1 | 0 | 0 |
| Share of all blunder windows below 0.3 | 8.5% | 12.4% | 6.7% |
| Share of all blunder windows below 0.5 | 11.2% | 16.4% | 13.3% |

  The random draw with no threshold is about 2.5 times slower in 0.3 to 0.7 than the bands. In
  return it does not depend on the serve-time score: the score has been refit several times, bands
  would leave windows drawn under different strata after each refit, and a band sample needs
  reweighting by the recorded sampling probability. Fairness is about the same, since a third of
  the random draw lands at 0.7 and above. A random draw cut at 0.7 is the worst of the three: it
  depends on the score and serves the most low-score blunders.
- "Random" means random within the drill's selection (game-first, one window per game), so the
  sample represents what the drill serves, not every blunder in the database.

## When to Surface

**Trigger:** after the Phase 259 switch release is live on prod and the prod backfill is complete.

## Scope Estimate

**Medium**, one phase: the exploration draw in `app/services/blunder_check_selection.py` and
`app/repositories/blunder_check_repository.py`, a migration for the window columns, the constant,
a calibration script under `scripts/blunder_check/`.

## For the Discuss Step

The owner decisions above were taken on 2026-11-21. Left for `/gsd-discuss-phase` and planning:

- **Scope boundary:** the phase delivers the arm, the recording, the avatar feedback
  and the calibration script; the analysis itself runs later, on demand. Acceptance criteria are
  still to write, e.g. the served exploration share against the 20% target.
- **Draw mechanics:** selection is game-first today (a SQL probe for any unserved blunder at or
  above the cut, then a Python judge). The random draw is that probe without the score cut, on
  scored rows only (the inputs must exist to be snapshotted). Its prod cost and its fit with the
  covering index Phase 259 builds (259 D-17) are unexamined.
- **Served-once rule:** exploration windows use up a user's low-score own blunders.
- **Re-measure first:** every number under Evidence is from the pre-259 score. Pool
  sizes and the caught-rate table are redone on the new score before the discuss step.

## Breadcrumbs

- `.planning/phases/259-facepalm-first-principles-refit/259-CONTEXT.md` (Deferred Ideas, D-15)
- `app/services/blunder_check_rules.py` (`FACEPALM_SCORE_MIN`, `draw_slot_plan`)
- `app/repositories/blunder_check_repository.py` (`_unserved_qualifying_blunder_exists`)
- `app/services/blunder_check_candidates.py` (the score gate in the judge)
- `app/models/blunder_check.py` (`BlunderCheckWindow`, `WindowOutcome`)
- Related seeds: SEED-261121-tau, SEED-261117-hfb, SEED-261120-bzq
