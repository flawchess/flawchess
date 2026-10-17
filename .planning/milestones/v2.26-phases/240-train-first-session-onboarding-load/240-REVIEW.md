---
phase: 240-train-first-session-onboarding-load
reviewed: 2026-10-15T00:00:00Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - alembic/versions/20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py
  - app/models/train_settings.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/train_scheduler.py
  - scripts/reset_train_state.py
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
  - frontend/src/components/train/TrainBotBubble.tsx
  - frontend/src/components/train/TrainBotStepper.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainRevealActionBar.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainTourOverlay.tsx
  - frontend/src/components/train/TrainVerdictStrip.tsx
  - frontend/src/components/train/trainBubbleState.ts
  - frontend/src/hooks/useTrainOnboarding.ts
  - frontend/src/hooks/useTrainWalkthrough.ts
  - frontend/src/index.css
  - frontend/src/lib/mobileBoardControls.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/Train.tsx
  - frontend/src/types/train.ts
findings:
  critical: 0
  warning: 1
  info: 5
  total: 6
status: issues_found
---

# Phase 240: Code Review Report

**Reviewed:** 2026-10-15
**Depth:** standard
**Files Reviewed:** 29 source files (the CLAUDE.md files were read as context, not reviewed)
**Status:** issues_found

## Summary

I attacked the six claims from the brief against the code. All six hold, and I found no correctness
bug or security issue. One warning (copy length against the score-screen fold) and five info items
remain.

Verification run: `uv run ty check app/ scripts/` passes, `check_function_size.py app/ --fail-over-depth 4`
reports no breaches, and `tsc -b`, `npm run knip` and eslint on the touched frontend files are clean.

Claim-by-claim result:

1. **Forward-only, race-safe stage advance: holds.** `_advance_reveal_tour_stage` issues
   `UPDATE ... WHERE user_id = :u AND reveal_tour_stage = :target - 1`
   (`train_repository.py:722-728`). A replay (stage already N), an out-of-order POST (stage < N-1) and
   a concurrent duplicate (Postgres READ COMMITTED re-evaluates the WHERE after the row lock) all match
   zero rows. The router (`routers/train.py:583`) only forwards the step to the repository and never
   writes the column. The `OnboardingStep` Literal 422s the retired `reveal_walkthrough` name. The CHECK
   (0..3) bounds the column at the database. The two lookup dicts partition `OnboardingStep`, so there
   is no `getattr` or SQL interpolation.
2. **Migration: holds.** There is a single head: only this revision lists `778c806092fb` as its
   `down_revision`. The upgrade adds the column NOT NULL with server default 0 and the CHECK, backfills
   stage 3 `WHERE reveal_walkthrough_seen_at IS NOT NULL` before the drop, then drops the column. The
   downgrade re-adds the nullable column, stamps `now()` for stage 3, drops the constraint and then the
   column. The order is valid. The lossy collapse of stages 1 and 2 and the lost completion instants
   are documented and owner-accepted (D-10). The server default `"0"` and the CHECK name match the model.
   No other runtime code in `app/`, `scripts/` or the frontend still reads `reveal_walkthrough_seen_at`.
3. **First-ever ordering: holds.** `_order_first_ever_session` runs only on the fresh-composition path,
   after `_resolve_existing_session` has returned None. The resumed, completed-in-window and
   IntegrityError-resume paths never reach it. The discarded untouched-and-resized row is deleted with a
   plain `session.execute(delete(...))` earlier in the same transaction, so the `exists()` check does
   not see it and the recomposed session is still first-ever (D-13). Positions are frozen into
   `drill_solves.position` after the reorder, so a resume reads the same order. `surviving_sr_keys` and
   `is_warmup` are set-valued and survive the reorder. The blob query is scoped with
   `GameFlaw.user_id == user_id` (no cross-user read) and is keyed `(game_id, ply)` like
   `_answer_keys_by_position`. The type derivation goes through the same `answer_key_for`, so slot 0 and
   the verdict classify alike. I traced `_first_session_order` for 0, 1 and 2 puzzles, no sharp puzzle,
   no several puzzle, and a several puzzle only at index >= 3. There is no out-of-range access and the
   rest keeps its order.
4. **`useTrainWalkthrough` latch: holds.** The latch is set once per reveal and cleared by `reset()` on
   every puzzle transition. `liveVerdict` is paired with `lastSolvedPosition` (the FLAWCHESS-64 fix), so
   the new puzzle's render never sees the previous verdict. The latch therefore cannot be taken from a
   stale `hasVerdict` render. The leave stamp's `setQueryData` cannot switch the part mid-reveal.
   `isRestored` returns null, so a restored reveal never starts a part. `leave()` is gated on
   `isLastStep && part !== null` and is wired into both Next and Analyze before the puzzle advances or
   unmounts. A stale latch can only replay a part, because the server no-ops the duplicate advance.
5. **`spotlight` threading: holds.** The flag is in the interface, the destructure, the `setPayload`
   object and the effect deps. `renderBoardControlsBar` reads it. It is deliberately absent from
   `NOOP_PAYLOAD`, so undefined means no glow. `TrainSolveScreen` derives it from `walkthroughTarget`,
   and the memo lists that as a dep. It clears when the tour ends (the payload republishes with false)
   and on unmount or leaving the page (`setPayload(null)` in the effect cleanup). `onNext` presence
   selects this bar, so a spotlighted payload cannot reach another bar branch.
6. **`TrainScoreScreen` stamp: holds.** The stamp fires when
   `bubbleCopy !== null && firstExplanation`, once through `stampedRef`, which is also correct under
   StrictMode. It is independent of branch (warm-up, perfect and regular all render the rationale) and
   never fires when `sr_explained_at` was already non-null at mount (the latch is false). A failed POST
   is not retried within the mount, which is acceptable since it replays next session.

## Warnings

### WR-01: Warm-up first-completed score bubble exceeds the copy sheet's own length cap (fold regression risk)

**File:** `frontend/src/lib/trainBotCopy.ts:884-896`
**Issue:** D-19 limits the shortened warm-up first-completed line 1 to "~180 max", and D-16 requires the
score to stay above the fold at 375x667 (the Phase 222 round 6 regression was a 5-line bubble pushing
the score down). I rendered `scoreBubbleCopy` for every audience and band with `isWarmup: true` and
`isFirstCompletedSession: true`. Line 1 reaches 230 characters (has_games_guest, red band) and 221 for
yellow. The whole bubble (line 1 + line 2) peaks at 367 characters, about 50 more than the previous
warm-up first variant (317). The only test bound is `lines.length <= 2`, so nothing pins the character
budget. The population that sees this variant is zero-game and still-analyzing users, who are also the
funnel's highest-abandonment cohort. The sheet's 180 estimate was wrong, so this is a copy/UAT risk,
not a coding error.
**Fix:** Confirm at UAT on 375x667 that the score badge stays above the fold for the longest warm-up
variant (has_games_guest/no_games_guest, red band). If it does not, shorten the first-completed warm-up
note. For example, drop "Those were warm-ups." there, since the warm-up clause already says the same:
```ts
const warmupNote = first ? `${PRACTICE_RATIONALE} ` : 'Those were warm-ups, nothing to bring back yet. ';
```
Add a test that asserts a character cap on `lines[0]` for the first-completed warm-up variant in all
audience x band combinations, so a future copy change cannot silently regress it.

## Info

### IN-01: Out-of-order onboarding responses can overwrite the settings cache with an older snapshot

**File:** `frontend/src/hooks/useTrainOnboarding.ts:34-37`
**Issue:** `onSuccess` writes whatever snapshot the response carries into `['train','settings']`.
Phase 240 makes two stamp POSTs possible within milliseconds: `reveal_tour_N` on the last puzzle's Next,
then `sr_explained` when the score screen mounts (any session whose last puzzle completes a tour part).
Each response is a snapshot taken after its own commit, so if the older snapshot arrives last it regresses
the cache (for example `sr_explained_at` back to null, or the stage back by one). Impact is limited: the
score screen latches its variant at mount, the server stays correct, and a regressed stage can only
replay a part. It is also narrow, because it needs `puzzles_per_session` small enough that a part
completes on the last puzzle.
**Fix:** In `onSuccess`, only apply the response if it is not older than the cached value. For example,
keep a per-field max (`reveal_tour_stage`) and a non-null-wins merge for the two timestamps, or
invalidate the query instead of `setQueryData` when another mutation is in flight.

### IN-02: `part` is returned from `useTrainWalkthrough` but no production code reads it

**File:** `frontend/src/hooks/useTrainWalkthrough.ts:113-114, 244`
**Issue:** `UseTrainWalkthroughResult.part` is only consumed by tests. `TrainSolveScreen` reads
`activeStep`, `stepIndex`, `stepCount` and `target`. knip does not flag it because it is an object
member, not an export. It is dead API surface.
**Fix:** Drop `part` from the result, or use it. Telemetry could carry the part number as an enumerated
literal on `review_walkthrough`, which would be genuinely useful for the post-deploy funnel read.

### IN-03: `INTRO_STEP_COUNT` can drift from `introSteps()`

**File:** `frontend/src/lib/trainBotCopy.ts:290, 329-338`
**Issue:** The step count is a separate constant (2) while `introSteps` builds the array literally,
and `IntroStep = 0 | 1` is a third copy. The old `introStepCount()` derived the count from the array.
Adding or removing a bubble now needs three coordinated edits, and the `as IntroStep` cast in
`handleIntroNext` hides a mismatch.
**Fix:** Add a unit test asserting `introSteps('white', audience).length === INTRO_STEP_COUNT` for all
four audiences (the new tests may already cover it). Alternatively derive `INTRO_STEP_COUNT` from a
`const` tuple of step builders.

### IN-04: `reveal_tour_stage` is a bare `int` on the wire while the frontend types it `0|1|2|3`

**File:** `app/schemas/train.py:767`
**Issue:** CLAUDE.md asks for a `Literal` on fixed sets. The CHECK constraint guarantees 0..3, and the
frontend narrows to `RevealTourStage`, but the Pydantic response model declares `int`. A bad value would
reach the client without a 500 and be treated as "tour done" (`>= 3`).
**Fix:**
```python
RevealTourStage = Literal[0, 1, 2, 3]
reveal_tour_stage: RevealTourStage
```
This needs `TrainSettingsRow.reveal_tour_stage` and the model's `Mapped[int]` to flow through a cast.
Alternatively keep `int` and add `Field(ge=0, le=REVEAL_TOUR_STAGE_MAX)` so the bound is declared once
from the constant.

### IN-05: The brand glow literal now exists in several places; the phone-bar glow clips at the viewport edges

**File:** `frontend/src/index.css:66-67` (and `TrainFlawFixedBanner.tsx:29`, `pages/Home.tsx`)
**Issue:** `--brand-glow` / `--brand-glow-halo` restate `rgba(205,127,50,0.85/0.35)`, which already
lives in `FLAW_FIXED_GLOW` and as Tailwind arbitrary values in `Home.tsx`. frontend/CLAUDE.md wants
semantic colors defined once in `theme.ts`. The index.css comment acknowledges the duplication, but
nothing enforces that the values stay in sync. Separately, on phones the spotlighted bar fills the fixed
bar edge to edge (`inset-x-0`, `flex-1`). The 2px ring and the halo are clipped by the viewport at the
left, right and bottom, so only the top edge of the glow shows. D-20 asks for "not clipped by overflow
parents", and viewport clipping cannot be fixed with CSS here, but it may undercut the salience the
phase wants for the Next/Analyze steps.
**Fix:** Export the two rgba strings from `theme.ts` and have `FLAW_FIXED_GLOW` reuse them (index.css
variables can be set from them once at startup, or a comment-plus-test can pin equality). At UAT on a
phone, check that the bar glow reads as a highlight. If not, inset the highlighted element a few px
inside the bar (for example `m-1`) so the full ring is visible.

---

_Reviewed: 2026-10-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
