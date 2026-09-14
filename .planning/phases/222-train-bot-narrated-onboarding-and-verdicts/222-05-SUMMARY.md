---
phase: 222-train-bot-narrated-onboarding-and-verdicts
plan: 05
subsystem: frontend (train, ui, personas)
tags: [react, typescript, train, chat-bubble, spaced-repetition, tdd]

requires:
  - phase: 222-01
    provides: "TrainBotBubble.tsx presentational component; trainBotCopy.ts's scoreBubbleCopy/pickBot/ScoreBubbleInput; useTrainOnboarding hook + trainApi.stampOnboarding; SolvedResult TS type extended with source/item_status/due_date"
  - phase: 222-02
    provides: "POST /train/onboarding/{step} endpoint; TrainSettingsResponse.sr_explained_at; SolvedResult.source/item_status/due_date populated server-side on the resume path"
provides:
  - "useTrainSession.solvedOutcomes: SolvedResult[] — the live per-solve outcome accumulator, seeded from solved_results on compose/resume and appended live from each SolveResponse (RESEARCH Finding C)"
  - "TrainScoreScreen's bot bubble stating what returns and when, before the Remind me ask (D-25, SC4), with the four D-25 copy variants wired to real session data"
  - "the sr_explained_at one-shot stamp, fired only when the full explanation variant actually renders (D-12)"
affects: [222-06]

actuals:
  tokens: 7055
  tasks: 2
  commits: 3

# Measured (#3968) — git rev-list --count against the pre-plan ledger base.
commits: 3
plan_head_before: f98ed81173d8bbee04c72adba4fbdb9f4be0bfc5

tech-stack:
  added: []
  patterns:
    - "A component-level D-12 stamp gate mirrors the pure copy resolver's own precedence (isWarmup / missedCount===0 win over isFirstCompletedSession) rather than trusting the caller's raw flag — computed once as a boolean (showsFullExplanation) and used both to gate the effect and as its dependency, so an explanation that never actually rendered can never be stamped."
    - "Live accumulator + server-seed pairing for a value that must survive both a straight-through session and a reload/resume/handoff: seed unconditionally in the compose mutation's onSuccess (reseed, never accumulate — same discipline as the pre-existing solvedPositions clear), append unconditionally in the solve mutation's onSuccess from the live response, never re-derived."

key-files:
  created: []
  modified:
    - frontend/src/hooks/useTrainSession.ts
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/hooks/__tests__/useTrainSession.test.ts
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx

key-decisions:
  - "showsFullExplanation (firstExplanation && !isWarmup && missedCount > 0) is computed locally in TrainScoreScreen rather than inferred from scoreBubbleCopy's returned lines — the pure resolver returns only string[] with no variant discriminator, so mirroring its own precedence chain at the call site is the only way to know which variant actually rendered without changing that module's return shape (out of scope: trainBotCopy.ts is not in this plan's files list)."
  - "The stamp-fire ref is read inside a useEffect body, not passed into a plain function call — unlike plan 04's TrainSolveScreen finding (which had to drop a ref guard because react-hooks/refs flags a ref-reading closure passed to an ordinary function during render), a ref read directly inside its own effect is the standard, unflagged pattern, so this plan keeps the ref guard the task explicitly asked for."
  - "train-score-bubble-returns wraps the WHOLE copy body (all of scoreBubbleCopy's lines), not just a single isolated 'returns' sentence — the pure resolver interleaves the return-count phrase into different combined sentences per variant (nothing-missed, later-session, first-completed), so there is no single line to carve out without duplicating that resolver's internal logic at the render site."
  - "expiresOn is threaded as its own prop distinct from the pre-existing nextSessionDate, even though both currently read the same TrainSessionResponse.expires_on value — the two props serve different call sites (the existing 'Next session:' line vs. the new bubble copy's day-arithmetic input) per the plan's own explicit instruction."

requirements-completed: [TRAINBOT-04, TRAINBOT-05]

coverage:
  - id: D1
    description: "useTrainSession exposes solvedOutcomes: SolvedResult[], correct for a session played straight through (live append), a resumed one (server seed), and the restored-reveal-to-score path (a fresh compose against a COMPLETED session returns populated solved_results via _resume_session) — with no double-counting on a landing-screen reseed."
    requirement: TRAINBOT-04
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainSession.test.ts#useTrainSession — solvedOutcomes accumulator (Phase 222 D-17/D-18) (4 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The score screen opens with a bot bubble (random smart host, D-04) stating what returns and when, positioned above the Remind me / Done row (SC4) — the <h1>Session complete</h1> heading is gone, every pre-existing testid (train-score-screen, train-score-badge, train-score-total, btn-train-done) survives unchanged."
    requirement: TRAINBOT-05
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx#the score bubble (D-25) (8 tests) + the pre-existing 22 tests in the file, all still green"
        status: pass
    human_judgment: false
  - id: D3
    description: "The full spaced-repetition explanation renders exactly once (gated on sr_explained_at === null AND the full-explanation variant actually winning scoreBubbleCopy's own precedence over warm-up/nothing-missed), stamps POST /train/onboarding/sr_explained exactly once, and never stamps when the one-liner, warm-up, or nothing-missed variant renders instead."
    requirement: TRAINBOT-05
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx (full-explanation-stamps-once, one-liner-never-stamps, warm-up-never-stamps, nothing-missed-never-stamps)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Returns are stated as counts grouped by when, never per-position identifiers; a mastered outcome is excluded from the 'comes back' counts; no position number, game id or ply ever appears in the rendered bubble text."
    requirement: TRAINBOT-04
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx#the score bubble (D-25) (mastered-excluded test, no-identifiers test)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-13
status: complete
---

# Phase 222 Plan 5: Score-Screen Bot Bubble — What Returns, When, and Why (D-25/SC4) Summary

**The Train score screen now opens on a bot-narrated recap of what returns and when — backed by a new live per-solve outcome accumulator in `useTrainSession` that makes the recap truthful for a session played straight through in one sitting, not just a resumed one.**

## Performance

- **Duration:** 55 min (approx.)
- **Started:** 2026-09-13T~16:40:00Z (approx., following 222-04's close)
- **Completed:** 2026-09-13T16:37:11Z (approx.)
- **Tasks:** 2 completed (T-222-05-01, T-222-05-02)
- **Files modified:** 5

## Accomplishments

- Added `solvedOutcomes: SolvedResult[]` to `useTrainSession` (RESEARCH Finding C): seeded from `data.solved_results` in the session mutation's `onSuccess` (covers resume/reload/phone-handoff and the restored-reveal-to-score path, since a fresh compose against a completed session already returns populated `solved_results` via `_resume_session`), and appended live in the solve mutation's `onSuccess` from each `SolveResponse` (covers a session composed and completed in one sitting, where the server's own `solved_results` is empty — exactly the first-time-user population this phase serves).
- Threaded `solvedOutcomes`, `session_date`, `expires_on` and `is_warmup` from `Train.tsx` into `TrainScoreScreen`.
- Replaced `TrainScoreScreen`'s `<h1>Session complete</h1>` with a `<TrainBotBubble>` hosted by a random smart bot (D-04, memoised once per mount), whose copy comes from plan 01's `scoreBubbleCopy` — the four D-25 variants (warm-up, nothing-missed, first-completed-session with the full SR explanation, later one-liner) now render from real session data instead of being unreachable pure-function code.
- The full spaced-repetition explanation stamps `POST /train/onboarding/sr_explained` exactly once, gated on a local `showsFullExplanation` boolean that mirrors `scoreBubbleCopy`'s own precedence (warm-up and nothing-missed both win over the full explanation) — so an explanation that was never actually shown is never stamped, per D-12.
- The bubble renders above the Remind me / Done row, satisfying SC4: state what returns and when before asking for the reminder.

## Task Commits

Each task was committed atomically:

1. **T-222-05-01: The live per-solve outcome accumulator, seeded from the server** — `ddf067932` (feat)
2. **T-222-05-02: The score bubble — what returns, when, and why, before the reminder ask** — `e53040c1b` (feat)

A third commit, `7e18e639f` (test), added one more component-level test for the nothing-missed variant on a first completed session (a `<behavior>` bullet from task 2 not covered by the task's own explicit `<acceptance_criteria>` list) before this SUMMARY was written.

**Plan metadata:** committed after this SUMMARY (see final commit below).

## Files Created/Modified

- `frontend/src/hooks/useTrainSession.ts` — `solvedOutcomes` state, seed + live append
- `frontend/src/pages/Train.tsx` — threads `solvedOutcomes`/`session_date`/`expires_on`/`is_warmup` into `TrainScoreScreen`
- `frontend/src/components/train/TrainScoreScreen.tsx` — the bot bubble, `showsFullExplanation` gate, `scoreBubbleCopy` wiring
- `frontend/src/hooks/__tests__/useTrainSession.test.ts` — 4 new tests (fresh-session empty, live append shape, completed-session-resume seed, reseed-not-accumulate)
- `frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx` — updated `renderScoreScreen` helper + new `useTrainSettings`/`useTrainOnboarding` mocks (this suite deliberately stays free of a `QueryClientProvider`), 9 new tests under "the score bubble (D-25)"

## Decisions Made

See frontmatter `key-decisions` for the full rationale on: computing `showsFullExplanation` locally rather than changing `scoreBubbleCopy`'s return shape, why the stamp ref is safe here (unlike plan 04's `TrainSolveScreen` finding), the `train-score-bubble-returns` testid wrapping the whole copy body, and threading `expiresOn` as its own prop alongside the pre-existing `nextSessionDate`.

## Deviations from Plan

None — plan executed exactly as written. The one addition beyond the plan's literal `<acceptance_criteria>` list (the nothing-missed variant test, committed separately as `7e18e639f`) was already an explicit `<behavior>` bullet in the plan itself, not a deviation from it.

## Known Stubs

None. Every new code path (accumulator seed/append, bubble rendering, stamp gate) is wired to real hooks/data — no hardcoded empty value flows to rendering.

## Threat Flags

None. All entries in this plan's threat register (T-222-05-01 through T-222-05-04, T-222-05-SC) are discharged by construction exactly as the plan's own threat model states: `SolvedResult` carries no `position`/`game_id`/`ply`/best move and an acceptance-criteria test asserts none of the fixture's identifiers appear in the rendered text (T-222-05-01); both outcome sources are attempt-scoped — `solved_results` only contains rows with a non-null `solved_at`, and the live append only fires from a successful solve response (T-222-05-02); the stamp fires from an effect gated on the actually-rendered variant, guarded by a single-fire ref, with a test asserting zero calls for every non-full-explanation variant (T-222-05-03); the score screen only mounts behind `Train.tsx`'s `isGuest` early return and the endpoint 403s guests regardless (T-222-05-04). Supply-chain gate: `git diff --exit-code -- frontend/package.json frontend/package-lock.json pyproject.toml uv.lock frontend/eslint.config.js` exits 0 — no package installed.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 06 (first-reveal walkthrough) can proceed independently — this plan touched only the score screen and `useTrainSession`, not `TrainReveal.tsx` or the walkthrough machinery plan 01 already built.
- Full frontend suite green: 263 test files / 4119 tests passing after this plan's changes (up from 4107 at plan 04's close). `npm run lint`, `npm run knip`, `npm run build` (tsc -b) all pass with zero findings.
- No blockers.

---
*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Completed: 2026-09-13*

## Self-Check: PASSED
