---
phase: 240-train-first-session-onboarding-load
verified: 2026-10-15T21:30:00Z
status: passed
score: 6/6 must-haves verified
covered_files:
  - ".planning/phases/240-train-first-session-onboarding-load/240-01-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-01-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-02-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-02-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-03-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-03-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-04-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-04-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-05-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-05-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-06-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-06-SUMMARY.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-07-PLAN.md"
  - ".planning/phases/240-train-first-session-onboarding-load/240-07-SUMMARY.md"
  - "alembic/versions/20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py"
  - "app/models/train_settings.py"
  - "app/repositories/train_repository.py"
  - "app/routers/train.py"
  - "app/schemas/train.py"
  - "app/services/train_scheduler.py"
  - "frontend/src/App.test.tsx"
  - "frontend/src/App.tsx"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/train/TrainBotBubble.tsx"
  - "frontend/src/components/train/TrainBotStepper.tsx"
  - "frontend/src/components/train/TrainLineChips.tsx"
  - "frontend/src/components/train/TrainMoveTreeList.tsx"
  - "frontend/src/components/train/TrainReveal.tsx"
  - "frontend/src/components/train/TrainRevealActionBar.tsx"
  - "frontend/src/components/train/TrainScoreScreen.tsx"
  - "frontend/src/components/train/TrainSolveScreen.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/components/train/TrainTourOverlay.tsx"
  - "frontend/src/components/train/TrainVerdictStrip.tsx"
  - "frontend/src/components/train/trainBubbleState.ts"
  - "frontend/src/hooks/useTrainOnboarding.ts"
  - "frontend/src/hooks/useTrainWalkthrough.ts"
  - "frontend/src/index.css"
  - "frontend/src/lib/mobileBoardControls.ts"
  - "frontend/src/lib/theme.ts"
  - "frontend/src/lib/trainBotCopy.ts"
  - "frontend/src/pages/Train.tsx"
  - "frontend/src/types/train.ts"
  - "scripts/reset_train_state.py"
covered_digest: "v3:sha256:d700a3c40dc3e612732cb18b32ee8cd6cc567d3a2ff30547e340edd5461c7a75"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "Human verification: WR-01 375x667 warm-up score fold, and desktop tour parts 2-3 plus reduced-motion glow"
    reason: "Owner marked UAT complete after squash-merge (d9e944d52). WR-01 accepted as is (guest variant already shortened in 83645579b; registered has-games variant not re-measured). Desktop parts 1-3 were walked by the orchestrator on 2026-10-15; reduced motion was not visually emulated, the static CSS override is present."
    accepted_by: "owner (Adrian Imfeld)"
    accepted_at: "2026-10-16"
human_verification:
  - test: "Owner decision on WR-01 / the 375x667 UAT gap: accept the current warm-up first-completed score bubble, or trim it"
    expected: "At 375x667 a guest's first warm-up session (green or red band) shows the 'Points: N/N' line (train-score-total) above the fixed bottom nav. Recommended fix (reviewer's, ~1 line in scoreBubbleCopy): drop 'Those were warm-ups.' from the first-completed warm-up note, plus a test capping lines[0] length for every audience x band."
    why_human: "D-16 made 'score stays above the fold at 375x667' a UAT acceptance condition. The end-of-phase browser walkthrough measured the points line at y 607-635 under the nav (y 605-666) for this variant. Whether to accept or trim is a copy and UX call; no code defect."
  - test: "Desktop (1280) walk of tour parts 2 and 3 plus the score screen; visual check of reduced-motion static glow"
    expected: "Parts 2 and 3 on desktop show the chips-row, move-list, board-row, lines and Analyze glows; the chips-row glow does not clash with the active chip's ring; with prefers-reduced-motion the glow is static."
    why_human: "The orchestrator walkthrough covered the desktop opening and part 1 only, and did not visually emulate reduced motion (the CSS override exists). Unit tests cover the logic, not the look."
---

# Phase 240: Train First-Session Onboarding Load Verification Report

**Phase Goal:** Cut first-session Train abandonment by lightening the tutorial around puzzle 1 (SEED-200): 2-bubble intro, first verdict teaches the vocabulary, practice rationale on the session-1 score screen, warm-up notice out of the intro, reveal tour spread over puzzles 1-3 with per-step stamps, and backend first-session composition (sharp puzzle first, several puzzle at slot 2-3).
**Verified:** 2026-10-15
**Status:** passed (owner override for the two human-verification items, 2026-10-16)
**Re-verification:** No, initial verification

## Goal Achievement

The code delivers all six numbered design points and every decision D-01..D-23. Nothing is FAILED. The status is `human_needed` solely because of the open UAT gap and WR-01 (same defect, see below), which needs an owner call, and one small unwalked UAT leg.

### Observable Truths (ROADMAP design points, the roadmap contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Intro shrinks to 2 bubbles (welcome, merged closing prompt with guess buttons); `INTRO_QUESTION`/`INTRO_VOCABULARY` retired | VERIFIED | `trainBotCopy.ts:284-340`: `IntroStep = 0 \| 1`, `INTRO_STEP_COUNT = 2`, `introSteps()` returns exactly welcome + `Decide first, then play. Your turn. ${promptCopy}`. Welcome strings are the four audience variants verbatim. `grep INTRO_QUESTION\|INTRO_VOCABULARY\|INTRO_PRACTICE\|INTRO_WARMUP_COPY frontend/src` returns nothing. `introStepCount(isWarmup)` is gone. Browser walkthrough: exactly two bubbles. |
| 2 | First verdict teaches "only one"/"several" for this position | VERIFIED | `tourStepCopy('result')` + `tourAnswerKind` (`sharp` vs `soft`/`herring` -> `several`), four device x kind variants identical to the D-19 sheet (`trainBotCopy.ts:640-700`). Per D-03 it lives in tour part 1's Hilda overlay, not verdict text; `verdictCopy`/`verdictStripLine` untouched. |
| 3 | Practice rationale moves to session-1 score screen | VERIFIED | `PRACTICE_RATIONALE` in line 1 of `scoreBubbleCopy` for regular, perfect and warm-up first-completed branches (`trainBotCopy.ts:880-925`). `returningCountsSentence` and the `outcomes`/`session_date`/`expires_on` inputs removed everywhere (D-18); props `sessionDate`/`expiresOn` dropped from `TrainScoreScreen`. `sr_explained` stamps in any branch once `bubbleCopy !== null && firstExplanation` (D-21). |
| 4 | Warm-up notice leaves the intro | VERIFIED | `INTRO_WARMUP_COPY` removed, intro length never varies with warm-up. Notice carried by the unchanged `WARMUP_TAIL_COPY` verdict tail (D-02, no relocation). |
| 5 | Reveal tour spreads over reveals 1-3, each step once per account, per-step stamps/counter | VERIFIED | `TOUR_PARTS` {0:[result,next], 1:[chips,stepping], 2:[sidelines,understand,analyze]}; `useTrainWalkthrough` latches `tourPartForStage(reveal_tour_stage)` once per reveal, stamps `reveal_tour_{part+1}` only when leaving from the last step (D-08), restored reveals never start a part. Backend: `_advance_reveal_tour_stage` is `UPDATE ... WHERE reveal_tour_stage = target-1` (forward-only, idempotent). Chips stay visible but unexplained on P1. Overlay is Hilda (`personaForId(HILDA_ID)`, `TrainSolveScreen.tsx:1022`). Per-part counter "n / m" (D-23). Browser walkthrough: stage 0->1->2->3 across reveals 1-3, none on reveals 4-6. |
| 6 | Backend session composition: first puzzle of first-ever session is sharp, a several puzzle at slot 2-3; no herring leak later | VERIFIED | `_first_session_order` + `_order_first_ever_session` (`train_repository.py:2018-2146`), wired at `:2709` after `_assemble_session_items` (D-09 shuffle) and before `_materialize_session_rows`. Gate `_is_first_ever_session` = no `drill_sessions` row of any status; resized-untouched recompose still counts (discard DELETE runs earlier, tested). Type via `answer_key_for` on the live blob (user-scoped query), so slot 0 and the verdict classify alike. No sharp puzzle -> shuffled order kept; later sessions untouched. Seeded, deterministic. Tests: 12+ `test_first_session_*` cases pass. |

**Score:** 6/6 truths verified, 0 behavior-unverified. The forward-only/idempotent stage advance is behavior-dependent and has passing tests: `test_onboarding_reveal_tour_out_of_order_is_noop`, `..._replay_never_moves_backwards`, `..._advances_in_order`. The first-ever composition has passing integration tests against the real DB.

### Guardrails

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| Every bubble within `STEPPER_COPY_MAX_CHARS` (145), shortened not concatenated | VERIFIED | Copy matches the D-19 sheet; longest chips step 139 (merged), result bubbles 95-124. Asserted in `TrainSolveScreen.test.tsx:4303,4327` and the trainBotCopy suite (passing). |
| Step-count assertions updated (`introStepCount`, `WALKTHROUGH_STEP_COUNT`, `IntroStep`, `WalkthroughStep`) | VERIFIED | Replaced by `INTRO_STEP_COUNT`, `TourPart`/`TourStepId`, per-part step counts; old names no longer exist. |
| No herring slot leak in later sessions | VERIFIED | Reorder gated to first-ever session; test for an earlier expired/completed session blocks the gate. |
| Reveal overlay reads as Hilda | VERIFIED | See truth 5. |
| Mobile and desktop UAT | PARTIAL | Orchestrator browser UAT: phone 390x844 full first session, 375x667 score screen, desktop 1280 opening and part 1. Desktop parts 2-3 and visual reduced-motion not walked (human item 2). |
| Measure: before snapshot, adapted after-query | VERIFIED | `240-FUNNEL-BEFORE.md` holds the prod baseline (81 first sessions, 44% abandoned, guest 45% / registered 44%, 8 "1 solved, never finished tour") and the adapted SQL on `reveal_tour_stage`. The after read is a post-deploy follow-up, not a gate. |

### Decision Coverage (D-01..D-23, coverage contract)

All accounted for, none superseded or deferred.

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01, D-02 | Implemented | Two-bubble intro; warm-up notice dropped, `WARMUP_TAIL_COPY` unchanged. |
| D-03..D-05 | Implemented | Vocabulary in tour part 1 result bubble; sharp/several variants; no points sentence; part 1 = 2 steps. |
| D-06..D-08 | Implemented | Three parts, one per reveal, complete on leaving last step, half-done part replays. |
| D-09..D-12 | Implemented | `reveal_tour_stage` SmallInteger NOT NULL default 0 + CHECK 0..3 (migration `5448f030de58`, single head from `778c806092fb`); backfill stage 3 where old column non-null, then drop. `reveal_walkthrough` retired from the `OnboardingStep` Literal (422, tested); only migrations and the 422 test still mention the old name. |
| D-13..D-15 | Implemented | See truth 6. |
| D-16..D-18 | Implemented | Rationale merged into line 1 in all three branches; counts sentence removed for every session; dead `ScoreBubbleInput` fields cleaned. (D-16's fold condition: see human item 1.) |
| D-19 | Implemented | Copy strings match the sheet verbatim. The one length deviation: the sheet's warm-up first line "~180 max" is actually 221-230 chars (WR-01). |
| D-20 | Implemented | One shared `TOUR_SPOTLIGHT_CLASS` (`train-tour-spotlight`): box-shadow-only bronze glow + `train-tour-spotlight-pulse` keyframes using `--brand-glow` (same rgba as `FLAW_FIXED_GLOW`), static under `prefers-reduced-motion`. Used on verdict strip/card, chips row, move list, lines region, board row, in-flow bar and the phone fixed bar (`spotlight` payload flag). Old per-target `ring-brand-brown` spotlights removed (remaining ring-brand-brown hits are the active chip and the reopen badge, intentional). |
| D-21 | Implemented | `showsFirstSessionCopy = bubbleCopy !== null && firstExplanation`. |
| D-22 | Implemented | `TrainStartScreen` gates the reminder ask on `isRevealTourDone(reveal_tour_stage)`. |
| D-23 | Implemented | `TourStepCount` per part. |

### Required Artifacts / Key Links

| Artifact / link | Status | Details |
|-----------------|--------|---------|
| Migration `5448f030de58` | VERIFIED | add column + CHECK, backfill, drop; downgrade restores; `tests/test_migration_240_reveal_tour_stage.py` passes. |
| `TrainSettings.reveal_tour_stage` -> repository -> router -> `TrainSettingsResponse` -> frontend type | WIRED | `train_repository.py:194,333,534-561,901`, `routers/train.py:487`, `types/train.ts`. |
| `POST /train/onboarding/{step}` -> `_REVEAL_TOUR_TARGET_STAGE` fixed dict | WIRED | No `getattr`, partitions the `OnboardingStep` Literal. |
| `useTrainWalkthrough` -> `useTrainOnboarding.stamp` -> settings cache -> `TrainStartScreen` gate | WIRED | `REVEAL_TOUR_STAMP` map; `leave()` called from Next and Analyze. |
| `_order_first_ever_session` -> `compose_session` | WIRED | `train_repository.py:2709`. |
| `spotlight` flag -> `mobileBoardControls` payload -> phone bar | WIRED | `TrainSolveScreen.tsx:1477`, `mobileBoardControls.ts:51-144`. |

### Data-Flow Trace (Level 4)

Stage counter: DB column -> `get_settings`/`stamp_onboarding_step` response -> `['train','settings']` query cache -> `tourPartForStage`. Real data end to end (browser walkthrough read `reveal_tour_stage` 3 from the live endpoint). Puzzle type for composition: real `game_flaws.missed_pv_lines` query; missing blob defaults to "soft" (the verdict's non-leaking default).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend onboarding, composition, migration, reset script | `uv run pytest tests/repositories/test_train_repository.py tests/routers/test_train.py tests/test_migration_240_reveal_tour_stage.py tests/scripts/test_reset_train_state.py` | 317 passed | PASS |
| Frontend copy, solve loop, score screen, start screen | `npx vitest run` on trainBotCopy, TrainSolveScreen, TrainScoreScreen, TrainStartScreen, Train.solveLoop | 382 passed | PASS |
| Full pre-merge gate (reported, at c0a001f3d; only docs commits since) | pytest 5490 passed / 19 skipped, vitest 5645, ty/ruff/lint/build/knip clean | not re-run (docs-only commits follow) | Accepted |

### Probe Execution

No probes declared. SKIPPED.

### Requirements Coverage

No REQUIREMENTS.md exists; the contract is D-01..D-23 (all covered above). `COVERAGE.md` records that no third-party API is involved. No orphaned requirements.

### Anti-Patterns Found

No TBD/FIXME/XXX debt markers or stubs found in the phase's changed files. Code review (0 critical, 1 warning, 5 info), all dispositions `open`:

| Finding | Severity | Impact on goal |
|---------|----------|----------------|
| WR-01 warm-up first-completed bubble 221-230 chars (sheet said ~180), fold risk at 375x667 | Warning | Corroborated by the UAT gap; see below. |
| IN-01 out-of-order onboarding responses can regress the settings cache | Info | Narrow race; worst case a tour part replays. Server stays correct. |
| IN-02 `part` returned from the hook, unused in production | Info | Dead API surface only. |
| IN-03 `INTRO_STEP_COUNT` can drift from `introSteps()` | Info | Maintenance; add a length-equality test. |
| IN-04 `reveal_tour_stage: int` on the wire, not `Literal[0,1,2,3]` | Info | CHECK constraint bounds it at the DB. |
| IN-05 brand-glow literal duplicated; phone-bar halo clipped at viewport edges | Info | Browser walkthrough: bar glow readable at 390x844, only the outermost bottom halo clipped. |

### Judgment: does the open UAT gap / WR-01 block the phase goal?

**No, it is a human_needed owner decision, not a blocker.** Reasoning:

- The goal is lighter tutorial load around puzzle 1. Every lever (2-bubble intro, vocabulary in the first reveal, 3-part tour, backend ordering) is implemented and verified. WR-01 touches the session-1 score screen, which is reached after the puzzle-1 drop points the phase targets.
- The defect is real but narrow: it needs a guest or registered user with a *warm-up* first completed session (zero-game or still-analyzing users) at a short 375x667 viewport. The 100% badge stays visible, and at 390x844 the points line is visible. It is a regression of about 50 characters versus the old warm-up bubble (old first-completed warm-up line was the same string as the later one, which lacked the 77-char rationale).
- It does breach the letter of D-16 ("UAT confirms the score stays above the fold at 375x667") and the D-19 "~180 max" cap for that one variant, so the owner must either accept it explicitly or trim. The fix is one line plus a length-cap test, and the reviewer already drafted it. Whether the prior copy already fit was not checked, so the regression is likely but unproven.
- I did not mark it `gaps_found`: no must-have truth fails, the copy is within its owner-reviewed draft except one estimate, and the choice between accepting and trimming is the owner's. If the owner prefers a strict reading of D-16, run `/gsd-plan-phase --gaps` for a single-task closure (shorten the first-completed warm-up note, add the cap test, re-check 375x667).

### Human Verification Required

1. **Owner decision on WR-01 / 375x667 score-screen fold.** Test: open the guest first warm-up session score screen at 375x667. Expected: "Points: N/N" above the fixed bottom nav, or an explicit owner acceptance. Why human: copy/UX call against a D-16 acceptance condition.
2. **Desktop tour parts 2-3 and reduced motion.** Test: first-ever session on desktop 1280, reveals 2 and 3; then emulate prefers-reduced-motion. Expected: correct glows per step, no clash between the chips-row glow and the active chip ring, static glow under reduced motion. Why human: visual; only part 1 and the CSS override presence were checked.

### Gaps Summary

No gaps. Phase goal achieved in code; two human items remain (one owner decision, one low-risk visual leg). The post-deploy funnel read (`240-FUNNEL-BEFORE.md` adapted query) is a follow-up, not a gate.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
