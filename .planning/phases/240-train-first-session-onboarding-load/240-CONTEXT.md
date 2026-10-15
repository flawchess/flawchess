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

### Claude's Discretion
- All new/rewritten copy (P1 sharp/several result bubbles, P2/P3 regrouped steps, score-screen
  rationale), within the 145-char budget and Phase 237 D-09's "describe only what is on screen". Owner
  reviews at UAT. Whether the P1 bubble refers to the user's own guess is also Claude's call.
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

- P1 result bubble draft (sharp, phone): "This strip is your result. Here there was only one good move:
  anything else was a mistake. Tap the strip for the details." P1 step 2: "Next takes you to the next
  puzzle."
- Score line 1 draft: "{opener} Practice teaches you when to calculate and when a quick good move is
  enough."
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
