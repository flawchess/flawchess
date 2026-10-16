# Phase 240: Train First-Session Onboarding Load - Context

**Gathered:** 2026-10-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Cut first-session Train abandonment by lightening the tutorial around puzzle 1, following the
locked SEED-200 design (guiding rule: **the user acts within one or two taps, and reads later**):

- Intro shrinks from 5-6 bubbles to 2 (welcome, then the merged closing prompt with the guess buttons).
- The "only one / several" vocabulary is taught after the first move, not before it.
- The practice rationale moves to the first completed session's score screen.
- The warm-up notice leaves the intro.
- The 6-step reveal tour is split into three parts spread over consecutive reveals.
- Backend: the first-ever session opens on a sharp puzzle and has a "several" puzzle at position 2 or 3.
- Added in discuss: the score screen drops the "N come back next session / in X days" counts.

SEED-200 is the design source. This file records the open points it left for discuss, plus refinements
where the code contradicted the seed. Where they differ, this file wins.

</domain>

<decisions>
## Implementation Decisions

### Intro (puzzle 1, before the first move)
- **D-01:** Intro = 2 bubbles: the welcome (`INTRO_WELCOME_COPY`, all 4 audience variants **kept
  verbatim**), then the existing closing prompt ("Decide first, then play. Your turn. {promptCopy}")
  carrying the guess buttons. `INTRO_QUESTION`, `INTRO_VOCABULARY`, `INTRO_PRACTICE` and
  `INTRO_WARMUP_COPY` retire from the intro. `introStepCount` no longer varies with warm-up (2 always);
  `IntroStep` narrows accordingly.
- **D-02:** The warm-up notice is **dropped without relocation**. In a warm-up session every puzzle is a
  filler or herring, so the puzzle-1 verdict tail already says "That one was a warm-up, so it won't
  come back…" (`WARMUP_TAIL_COPY`, audience-aware), and the warm-up score bubble repeats it
  (`WARMUP_SCORE_CLAUSE`). No new warm-up copy.

### Vocabulary lesson (puzzle 1 reveal)
- **D-03:** The vocabulary lives in **tour part 1's result bubble** (the Hilda stepper overlay, shown on
  every device), NOT in the verdict text. On phones the verdict is a one-line strip and the full
  feedback only opens on a tap, so verdict text would be missed. Verdict copy (`verdictCopy`,
  `verdictStripLine`) stays unchanged.
- **D-04:** The result bubble explains what the call meant **for this position, per answer type**: a
  "only one" variant (sharp) and a "several" variant (soft SR item or herring). The several variant is
  needed because part 1 can land on a herring or soft puzzle (own-games first session with no sharp
  puzzle, or an abandoner whose first reveal comes in a later session, see D-13).
- **D-05:** The scoring explanation ("a point for the right call and up to two for the move") is
  **dropped** from the tour: the strip and verdict already show `[+1]`/`[+2]`. Tour part 1 stays at 2
  steps: result + vocabulary, then Next.

### Reveal tour split
- **D-06:** Three parts (as in the seed): **P1** = result/vocabulary + Next; **P2** = chips + stepping
  through lines; **P3** = sidelines/rewind, "understand, don't memorize", Analyze. Chips stay visible but
  unexplained on P1 (no variant reveal screen). Every step stays within `STEPPER_COPY_MAX_CHARS` (145),
  shortened not concatenated. Merged-chip and per-device copy variants from Phase 237 carry over.
- **D-07:** **Trigger = the next reveal after the previous part was completed**, account-scoped, at most
  one part per reveal. It is not tied to puzzle 2/3 of session 1: someone who quits after P1 gets P2 on
  their first reveal next session.
- **D-08:** A part counts as complete when the user leaves its last step (same as today's walkthrough).
  A part left halfway replays on the next reveal.

### Stamp storage
- **D-09:** **Stage counter**: one `SmallInteger` column on `train_settings` (e.g. `reveal_tour_stage`,
  0-3, `CHECK` 0..3, default 0). It only moves forward and is idempotent on replay: advance to N only
  from N-1, the same first-write-wins spirit as `stamp_onboarding_step`'s guarded `IS NULL` UPDATE.
  — **Reversibility:** one-way — needs an Alembic migration plus a column drop (D-10); undoing restores data only from the counter.
- **D-10:** **Retire `reveal_walkthrough_seen_at`**: the migration backfills `reveal_tour_stage = 3`
  wherever it is non-null, then drops the column. Remove it from `TrainSettingsRow`,
  `TrainSettingsResponse`, `_ONBOARDING_COLUMNS`, `OnboardingStep`, and the frontend types/hooks.
  — **Reversibility:** one-way — dropped column; the completion timestamp is lost (owner accepted).
- **D-11:** **Hard cut, no compat shim.** A stale PWA tab that POSTs `/train/onboarding/reveal_walkthrough`
  gets a 422 and may replay the old tour until it reloads. Accepted given the traffic.
- **D-12:** Users who are mid-onboarding at deploy (intro seen, old tour not finished) start the new
  split tour from part 1. Intro gating (`intro_seen_at`) is unchanged.

### First-session composition (backend)
- **D-13:** The reorder applies to the **first-ever session only**: the user has no earlier
  `drill_sessions` row of any status. A recomposed untouched/resized first session
  (`_discard_if_untouched_and_resized`) still counts as first-ever; the researcher verifies the
  discarded row is gone before the check runs. The reorder runs **after** the D-09 seeded shuffle in
  `_assemble_session_items` and stays deterministic. Later sessions keep the plain shuffle, so the only
  herring leak is "slot 0 of session 1 is never a herring".
- **D-14:** "Sharp" for slot 0 = **answer-key type `sharp`**, the same classification the verdict uses
  (`answer_key_for` / `classify_puzzle_type` on the live blob for SR items; sharp fillers are always
  sharp). Not a source proxy, since SR items can be soft. Answer keys are attached after materialize
  today (`_attach_answer_keys`), so composition may need the type earlier; the researcher checks the
  cost and picks the seam. If no sharp puzzle exists (own-games session), keep the random order.
- **D-15:** Puzzle 2 or 3 (index 1-2) of the first-ever session holds **any "several" puzzle** (herring or
  soft SR item, the first one in shuffled order). If none is there already, swap it in (seeded
  choice between index 1 and 2). If none exists, leave the order alone. Default sessions are 6
  puzzles with 1 herring (`HERRING_SHARE` 0.25); warm-up sessions have no soft puzzles.

### Score screen
- **D-16:** The practice rationale is **shortened and merged into line 1** (after the session opener)
  of the score bubble. The bubble stays at 2 lines; UAT confirms the score stays above the fold at
  375x667 (the Phase 222 round 6 regression). Draft direction: "Practice teaches you when to calculate
  and when a quick good move is enough." (final copy at Claude's discretion).
- **D-17:** The rationale shows on the **first completed session** (`isFirstCompletedSession`, which
  can be session 2 for an abandoner), in all three `scoreBubbleCopy` branches: regular, perfect
  ("Nothing got away today"), and warm-up.
- **D-18 (added by owner in discuss):** **Remove the returning-counts sentence from the score screen for
  every session** (`returningCountsSentence`: "2 come back next session, 1 in 3 days." / "Nothing else
  is coming back yet."). It is clutter. The per-puzzle verdict return tails (`returnPhrase`, e.g. "Let's
  see if you remember this in 3 days") **stay**; they are where spaced-repetition timing is shown.
  Clean up whatever `ScoreBubbleInput` fields only that sentence used (`outcomes`, `session_date`,
  `expires_on` if nothing else reads them).

### Copy sheet
- **D-19:** The copy sheet in `<specifics>` below is the **owner-reviewed starting draft** for every
  step and conditional variant. Planner and executor implement it verbatim. Small wording fixes found
  at UAT are fine, but every bubble stays within 145 chars and no step is added. This includes the
  warm-up shortening on the first completed session (line 1 drops "nothing to bring back yet").

### Tour spotlight styling
- **D-20:** The element a tour step explains gets a **more salient highlight**: the flaw-fixed card's
  border (`FLAW_FIXED_GLOW` in `frontend/src/components/train/TrainFlawFixedBanner.tsx`:
  `rgba(205,127,50,0.85)`, the homepage "brand glow". The owner calls it gold; it is the bronze brand
  color, so reuse that exact value) plus a **pulsating glow** of the same color. This replaces today's
  scattered `ring-2 ring-brand-brown` spotlights (`TrainReveal.tsx` verdict/tree/lines,
  `TrainSolveScreen.tsx` board, the action bar) with **one shared class/constant** used by every tour
  target. It applies to all three tour parts.
  - Pulse = a new `@keyframes` in `frontend/src/index.css` animating the `box-shadow` glow (alpha/blur),
    looping while the step is active, next to the existing `arrow-pulse` / `row-highlight-pulse`.
  - `prefers-reduced-motion`: static glow, no pulse.
  - The highlight must not shift layout (border width compensated, or `outline`/`box-shadow` only) and
    must not be clipped by `overflow` parents (the board row, the fixed phone action bar).
  - Phase 237 UAT left the chips row un-ringed because the active chip's own ring already marked it.
    With the new glow the **chips row container does get the highlight** (salience is the goal, and
    the glow reads differently from a chip's selection ring). Recheck at UAT that the two don't clash.

### Post-research owner decisions (plan-phase, 2026-10-15)
- **D-21:** **`sr_explained` stamps whenever the first-completed variant renders, in any branch**
  (regular, perfect, warm-up), replacing today's `firstExplanation && !isWarmup && missedCount > 0`
  gate in `TrainScoreScreen.tsx`. Prevents a zero-game guest (all warm-ups) from seeing the rationale
  every session. Accepted side effect: a user whose first completed session was a warm-up never sees
  the later "Reminders build the habit…" line. Flip the affected `TrainScoreScreen.test.tsx` cases.
- **D-22:** The landing reminder ask (`TrainStartScreen.tsx`) unlocks only when the **whole tour is
  done** (`reveal_tour_stage >= 3`, via a named constant), same meaning as today.
- **D-23:** The tour overlay's "n / m" counter counts **per part** (e.g. "1 / 2"), not globally.

### Claude's Discretion
- Copy beyond D-19's sheet (none expected). Whether the P1 bubble refers to the user's own guess: no,
  per the sheet.
- Onboarding endpoint shape for the stage advance (e.g. `POST /train/onboarding/reveal_tour` with the
  target stage, or step literals mapping to stages), keeping the fixed-dict / no-`getattr` rule from
  T-222-02-03.
- How the reveal decides which part to show (from `reveal_tour_stage` in the settings query).
- Phase 233 D-13 telemetry: keep `review_walkthrough: true` on any reveal where a tour part ran.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source
- `.planning/seeds/SEED-200-train-first-session-onboarding-load.md`: locked design, funnel data, the
  measurement SQL, and pitfalls (Phase 222/237 UAT split history, step-count assertions, herring leak).
- `.planning/ROADMAP.md` § Phase 240: goal, guardrails, measure.

### Prior onboarding / tour decisions
- `.planning/milestones/v2.24-phases/237-train-reveal-chips-move-tree/237-CONTEXT.md`: D-09 (6-step tour,
  145 budget, on-screen-only copy), D-10 (stepper bubble stacked above the strip, scroll allowed during
  the tour only), D-11 (UAT viewports 390x844, 375x667, desktop).
- `.planning/milestones/v2.23-phases/233-train-puzzle-timing-telemetry/233-CONTEXT.md` D-13:
  `review_walkthrough` telemetry flag.
- Phase 222 (intro stepper, D-11/D-12 stamps, D-21/D-24 walkthrough, UAT rounds 3/5/6): comments in
  `frontend/src/lib/trainBotCopy.ts` and `app/models/train_settings.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/trainBotCopy.ts`: `introSteps`/`introStepCount`/`introCopy`, `walkthroughCopy`
  (+ `WALKTHROUGH_STEP_COUNT`, `WalkthroughStep`, `WalkthroughContext`, `TOUR_ICON_TOKEN`),
  `scoreBubbleCopy`/`returningCountsSentence`, `STEPPER_COPY_MAX_CHARS`, `audienceKey`.
- `frontend/src/components/train/TrainBotStepper.tsx`: intro and tour bubble (Hilda avatar). Reuse it
  for all three tour parts so the overlay reads as Hilda.
- `frontend/src/hooks/useTrainOnboarding.ts`, `frontend/src/hooks/useTrainWalkthrough.ts`: stamp
  posting and walkthrough-active state.
- `app/repositories/train_repository.py` `stamp_onboarding_step` + `_ONBOARDING_COLUMNS`: the guarded
  first-write-wins UPDATE pattern the stage advance should mirror.
- `app/services/train_pool.py` `answer_key_for` / `classify_puzzle_type`: the sharp/soft/herring type
  (D-14).

### Established Patterns
- Onboarding stamps: nullable timestamps, first-write-wins, `POST /train/onboarding/{step}` with a
  `Literal` step validated at the path (`app/schemas/train.py:723` `OnboardingStep`,
  `app/routers/train.py:554`).
- Session composition: `_assemble_session_items` → D-09 `random.Random(f"{user_id}:{today}")` shuffle →
  `is_warmup` from surviving SR keys → `_materialize_session_rows` → `_attach_answer_keys`.
- Low-volume domain columns: SmallInteger/TEXT + `CHECK`, no native ENUM (CLAUDE.md).

### Integration Points
- `frontend/src/components/train/TrainSolveScreen.tsx` / `TrainReveal.tsx`: tour gating per reveal.
- `frontend/src/components/train/TrainScoreScreen.tsx`: score bubble lines (D-16..D-18).
- `frontend/src/components/train/TrainStartScreen.tsx`: reads `reveal_walkthrough_seen_at` today
  (must switch to the stage).
- Tests that assert counts or the old field: `Train.solveLoop.test.tsx`, `TrainSolveScreen.test.tsx`,
  `TrainStartScreen.test.tsx`, `TrainScoreScreen.test.tsx`, `TrainReminderButton.test.tsx`, plus
  the trainBotCopy budget tests and the backend onboarding/composition tests.

</code_context>

<specifics>
## Specific Ideas

### Copy sheet (D-19)

"Unchanged" = today's string in `frontend/src/lib/trainBotCopy.ts`. `{back}`/`{forward}`/`{rewind}` are
`TOUR_ICON_TOKEN`s rendered as icons. Char counts measured with tokens as text (all ≤ 145).

**Intro (puzzle 1, before the first move): 2 steps**

- **I-1 Welcome** (unchanged, `INTRO_WELCOME_COPY` per audience):
  - has_games: "Welcome to FlawChess Train! You will improve by solving puzzles created from your own games."
  - has_games_guest: "Welcome to FlawChess Train! Sign up free and you will improve by solving puzzles created from your own mistakes."
  - no_games: "Welcome to FlawChess Train! Import your games and you will improve by solving puzzles created from your own mistakes."
  - no_games_guest: "Welcome to FlawChess Train! Import your games and sign up, and you will improve by solving puzzles created from your own mistakes."
- **I-2 Closing prompt + guess buttons** (unchanged): "Decide first, then play. Your turn. You play {white|black}. Is there only one good move, or several?"
- Retired: `INTRO_QUESTION`, `INTRO_VOCABULARY`, `INTRO_PRACTICE`, `INTRO_WARMUP_COPY`.

**Warm-up verdict tail** (unchanged, carries the warm-up notice per D-02): "That one was a warm-up, so it
won't come back." + has_games "Your own positions will." / has_games_guest "Sign up free and your own
positions will." / no_games "Import your games and your own positions will." / no_games_guest "Import
your games, then sign up, and your own positions will."

**Tour part 1 (first reveal): 2 steps**

- **P1-1 Result + vocabulary** (new, spotlight `verdict`), by device × answer type (sharp = key type
  `sharp`; several = `soft` or `herring`):
  - phone + sharp (124): "This strip is your result. Here only one move was good, every other move was a mistake. Tap the strip for the full feedback."
  - phone + several (117): "This strip is your result. Here several moves were fine, so any good move works. Tap the strip for the full feedback."
  - desktop + sharp (102): "Your result is in the highlighted bubble. Here only one move was good, every other move was a mistake."
  - desktop + several (95): "Your result is in the highlighted bubble. Here several moves were fine, so any good move works."
- **P1-2 Next** (new, spotlight `bar`): "Next takes you to the next puzzle."

**Tour part 2 (next reveal after part 1): 2 steps**

- **P2-1 Chips** (unchanged, spotlight `chips`): "The Move, Best, and Game chips are the lines, one per
  move. Tap one to focus it on the board." + only when shown: ' "Move = Best" means you found the best
  move.' / ' "Move = Game" means you played the game move.' (max 139)
- **P2-2 Stepping** (unchanged, spotlight `tree`):
  - phone (90): "Step through the focused line with {back} {forward} in the bar, or tap a move in the list."
  - desktop (116): "Step through the focused line with {back} {forward} under the board, the arrow keys, or a tap on a move in the list."

**Tour part 3 (next reveal after part 2): 3 steps**

- **P3-1 Sidelines** (unchanged, spotlight `board`):
  - phone (124): "Move a piece to try your own idea: it branches off as a sideline. {rewind} in the bar takes you back to the puzzle position."
  - desktop (121): "Move a piece to try your own idea: it branches off as a sideline. {rewind} or Home takes you back to the puzzle position."
- **P3-2 Understand** (unchanged, spotlight `lines`, 127): "Understanding why a move works or fails by analyzing the lines is what makes the pattern stick. Don't just memorize the answer."
- **P3-3 Analyze** (changed: the Next sentence moved to P1-2; spotlight `bar`):
  - analyzeOpens = game (102): "The Analyze button opens the whole game one move before the mistake, so you can see how you got there."
  - analyzeOpens = position (61): "The Analyze button opens this position on the analysis board."

**Score screen** (`scoreBubbleCopy`). `{rationale}` = "Practice teaches you when to calculate and when a
quick good move is enough." (76), first completed session only (D-17). The returning-counts sentence is
gone from every branch (D-18).

| Branch | Line 1 | Line 2 |
|---|---|---|
| Regular, first completed | `{opener} {rationale}` | "Reminders build the habit that makes Train work." + `{reminder ask}` |
| Regular, later | `{opener} See you tomorrow.` | none |
| Perfect, first completed | "Nothing got away today." + `{rationale}` | "Reminders build the habit that makes Train work." + `{reminder ask}` |
| Perfect, later | "Nothing got away today." | `{reminder ask}`; if reminders already on: "Remember to analyze why the moves work or fail, not just memorize the best move." |
| Warm-up, first completed | `{opener} {rationale} Those were warm-ups. {warm-up clause}` (shortened, ~180 max) | guest: `GUEST_SIGNUP_ASK_SCORE`; has_games: `WARMUP_REMINDER_ASK_COPY`; no_games: none |
| Warm-up, later | `{opener} Those were warm-ups, nothing to bring back yet. {warm-up clause}` (unchanged) | same as above |

- `{opener}` (unchanged): green "Strong session." / yellow "Solid session, with a few that got away." /
  red "Tough session. That is exactly what Train is for." / no band "Session done."
- `{reminder ask}` (unchanged `REMINDER_ASK_COPY`): remind_me "Turn on Remind me and let the next session
  find you." / scan_qr "Train works best on your phone: scan the code below to install FlawChess there
  and turn on reminders." / none "Yours are already on, so the next session will find you."
- `{warm-up clause}` (unchanged `WARMUP_SCORE_CLAUSE`): has_games "Once your games are analyzed, your own
  mistakes take over." / has_games_guest "Guest games are not analyzed automatically, so your own
  mistakes are not here yet." / no_games "Import your games and your own mistakes take over." /
  no_games_guest "Import your games, then sign up, and your own mistakes take over."

### Measurement
- Measurement: re-run the SEED-200 clean-cohort funnel (split guest-origin vs registered) before and
  after. "Never finished the tour" becomes `reveal_tour_stage < 3` (or `= 0` for "never finished
  part 1"). Commit a "before" snapshot during the phase; the "after" read is a post-deploy follow-up,
  not a phase gate.

</specifics>

<deferred>
## Deferred Ideas

None. The one addition raised in discuss (removing the score-screen returning counts) was folded in as
D-18.

### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-08-29-variation-tree-nested-button.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`:
  matched only on generic keywords, unrelated to Train onboarding.

</deferred>

---

*Phase: 240-train-first-session-onboarding-load*
*Context gathered: 2026-10-15*
