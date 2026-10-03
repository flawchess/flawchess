---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 04
subsystem: train
tags: [react, typescript, vitest, guest-activation, bot-copy]

# Dependency graph
requires:
  - phase: 224-guest-activation-welcome-removal-and-guest-train
    provides: "Train open to every zero-game account (Plan 01) and hasImportedGames(profile), the shared zero-game predicate (Plan 02)"
provides:
  - "TrainCopyAudience ({ hasGames, isGuest }) and audienceKey, the single D-03 resolver threaded through trainBotCopy.ts's intro/warm-up/verdict/score-bubble copy"
  - "GUEST_SIGNUP_ASK_SCORE — the S-3 sign-up ask replacing the warm-up reminder ask for guests on the score bubble"
  - "resolveScheduleCardVisibility — D-13's guest-aware visibility resolver hiding the reminder block and phone/QR section for guests on the Train landing settings card"
affects: [224-05-guest-lifecycle-purge-and-promotion, 224-06-signup-ask]

# Actuals (#2632)
actuals:
  tokens: 16025
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Audience-keyed Record<CopyAudienceKey, string> copy tables (mirrors the existing ReminderAsk keyed-record shape) with a single module-private audienceKey resolver, so hasGames/isGuest never leak into ad hoc ternaries at each call site"
    - "Visibility resolved by a single module-level function (resolveScheduleCardVisibility) that returns all four booleans, keeping isGuest branching out of a complexity-capped component body"

key-files:
  created: []
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "TrainScheduleSettings gained isGuest in Task 2 (declared + void'd), one task ahead of Task 3's own resolver — the plan's own task split has Task 2 pass isGuest to a component whose props don't accept it yet until Task 3, which fails npm run build mid-plan; fixed by declaring the prop in Task 2 (mirroring Plan 01's void-isGuest precedent) so each task's own <verify> stays independently green"
  - "ReturnPhraseInput.audience and ScoreBubbleInput.audience are required (non-optional) fields, not optional like the interfaces' other fields — both call sites always have a real audience object, and a required field forces every call site (including tests) to state its audience explicitly rather than silently defaulting"
  - "GUEST_SIGNUP_ASK_SCORE branches on input.audience.isGuest directly (not audienceKey), matching the plan's literal action text: a guest WITH games still gets the sign-up ask on a warm-up (caught-up) session, since S-3's reminder-ask replacement is unconditional on isGuest, while the four D-03 copy strings key off hasGames-wins-over-isGuest instead"

patterns-established:
  - "TrainCopyAudience threading: pages build the audience object once from useUserProfile()-derived flags and pass it down as props/fields; presentational components never read useUserProfile themselves"

requirements-completed: [GUESTACT-09, GUESTACT-15]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Every branched Train string (intro welcome, intro warm-up, verdict warm-up return tail, score-bubble warm-up clause) resolves per audience in a pure function; the has_games audience is byte-identical to today's strings"
    requirement: "GUESTACT-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#introCopy / introSteps — D-03 games-less audience branch (Phase 224)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#returnPhrase — D-03 games-less warm-up tail audience branch (Phase 224)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#scoreBubbleCopy — D-03/S-3 games-less warm-up audience branch (Phase 224)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A zero-game guest reads import first, sign up second, in every branched string; a registered zero-game account reads import-only copy with no sign-up ask; an account with games keeps today's strings verbatim"
    requirement: "GUESTACT-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts (import-before-sign-up ordering assertions across all three new describe blocks)"
        status: pass
    human_judgment: false
  - id: D3
    description: "hasGames/isGuest thread from Train.tsx (built via hasImportedGames(profile) and useUserProfile().data) into TrainStartScreen, both TrainSolveScreen render sites and TrainScoreScreen as props; TrainScoreScreen never imports useUserProfile itself"
    requirement: "GUESTACT-09"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx (updated fixtures, all passing)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx (updated fixtures, all passing)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx (updated fixtures, all passing)"
        status: pass
      - kind: other
        ref: "grep -q useUserProfile frontend/src/components/train/TrainScoreScreen.tsx returns no match"
        status: pass
    human_judgment: false
  - id: D4
    description: "A guest sees no reminder toggle, hour picker or QR/install block anywhere under /train, including the Train landing settings card; a registered user's card is unchanged; the weekday/puzzles-per-session controls stay for both"
    requirement: "GUESTACT-15"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx#TrainScheduleSettings — D-13 guest visibility (Phase 224)"
        status: pass
    human_judgment: false
  - id: D5
    description: "No complexity ceiling moved and no new baseline entry was added to eslint.config.js"
    verification:
      - kind: other
        ref: "git diff --stat frontend/eslint.config.js (empty)"
        status: pass
      - kind: other
        ref: "npm run lint (whole-project, respects inline eslint-disable) — clean"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-17
status: complete
---

# Phase 224 Plan 4: Games-Less Train Copy And Guest Settings Card Summary

**Every Train string that presumed a running analysis now branches on `{ hasGames, isGuest }` (import-only for a zero-game registered account, import-then-sign-up for a zero-game guest, unchanged for accounts with games), and the Train landing's schedule card hides its reminder toggle and phone/QR block from guests via a new `resolveScheduleCardVisibility` resolver.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-17T23:15:00+02:00 (approx.)
- **Completed:** 2026-09-17T23:42:33+02:00
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Added `TrainCopyAudience` (`{ hasGames, isGuest }`) and the module-private `audienceKey` resolver to `trainBotCopy.ts` (hasGames wins over isGuest, per D-03); converted `INTRO_WELCOME`, `INTRO_WARMUP`, `WARMUP_TAIL` and the warm-up score clause into three-key `Record<CopyAudienceKey, string>` tables whose `has_games` entry is character-for-character today's string
- Added `GUEST_SIGNUP_ASK_SCORE`, the S-3 sign-up ask that replaces the warm-up reminder ask on the score bubble whenever `audience.isGuest` is true (for both `hasGames` values, per the plan's literal branch condition)
- Threaded `audience` through `introSteps`/`introStepCount`/`introCopy`, `ReturnPhraseInput`/`returnPhrase` and `ScoreBubbleInput`/`scoreBubbleCopy`, with 27 new unit tests asserting: no zero-game string claims analysis is running, no `no_games` string mentions signing up, and every `no_games_guest` string reads import before sign up
- `Train.tsx` derives `hasGames` via `hasImportedGames(profile)` and passes `hasGames`/`isGuest` to `TrainStartScreen`, both `TrainSolveScreen` render sites and `TrainScoreScreen`; `TrainStartScreen` gained `WARMUP_BODY_NO_GAMES`/`WARMUP_BODY_NO_GAMES_GUEST` and a module-level `warmupBannerBody` resolver (extracted to stay under its complexity ceiling); `TrainScoreScreen` never reads `useUserProfile` itself — audience arrives as props only
- Extracted `resolveScheduleCardVisibility` in `TrainScheduleSettings.tsx`: `showReminderBlock` and `showPhoneSection` are now false whenever `isGuest` is true (D-13), while the weekday-cadence and puzzles-per-session controls stay unchanged for guests

## Task Commits

Each task was committed atomically:

1. **Task 1: Audience-branched copy in the pure layer** - `b2088b88c` (feat)
2. **Task 2: Thread the audience from Train.tsx into the three Train screens** - `263ad398e` (feat)
3. **Task 3: Hide the reminder toggle and the QR/install block from guests (D-13)** - `1087639d4` (feat)

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `frontend/src/lib/trainBotCopy.ts` - `TrainCopyAudience`, `audienceKey`, four audience-keyed copy records, `GUEST_SIGNUP_ASK_SCORE`, audience threaded through `introSteps`/`introStepCount`/`introCopy`/`returnPhrase`/`scoreBubbleCopy`
- `frontend/src/lib/__tests__/trainBotCopy.test.ts` - audience fixtures added to every existing call site; three new describe blocks (27 new tests) covering the D-03/S-3 behavior
- `frontend/src/pages/Train.tsx` - `hasGames` derived via `hasImportedGames(profile)`; both flags passed to all four child render sites
- `frontend/src/components/train/TrainStartScreen.tsx` - two new warm-up banner strings, `warmupBannerBody` resolver, `isGuest` passed to `TrainScheduleSettings` at both render sites
- `frontend/src/components/train/TrainSolveScreen.tsx` - audience built once, threaded into the intro stepper, verdict return tail and persona resolver
- `frontend/src/components/train/TrainScoreScreen.tsx` - `hasGames`/`isGuest` props passed straight into `scoreBubbleCopy`'s `audience` field
- `frontend/src/components/train/TrainScheduleSettings.tsx` - `isGuest` prop, `resolveScheduleCardVisibility` module-level function, module docstring updated with the D-13 rationale
- `frontend/src/components/train/__tests__/TrainStartScreen.test.tsx` / `TrainSolveScreen.test.tsx` / `TrainSolveScreen.restoredGameArrow.test.tsx` / `TrainScoreScreen.test.tsx` - default fixtures updated to `hasGames: true, isGuest: false`
- `frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx` - `renderWithClient` gained an `isGuest` parameter; new "D-13 guest visibility" describe block (3 tests: non-guest unchanged, guest hides everything, guest-on-mobile-install-eligible also hides the Install button)
- `frontend/src/pages/__tests__/Train.solveLoop.test.tsx` - whole-module `useUserProfile` mock extended with `hasImportedGames: () => true` (Train.tsx now imports it too)

## Decisions Made

- **TrainScheduleSettings gained `isGuest` a task early.** Task 2's own instruction ("pass `isGuest={isGuest}` to `TrainScheduleSettings` at BOTH render sites") would fail `npm run build` before Task 3 declares the prop — fixed by adding `isGuest: boolean` to `TrainScheduleSettingsProps` in Task 2 with a `void isGuest;` placeholder (mirroring Plan 01's exact `void isGuest;` precedent for `Train.tsx`), so each task's own `<verify>` block stays independently green. Task 3 then removed the `void` and wired the real resolver.
- **`audience` is a required field on `ReturnPhraseInput`/`ScoreBubbleInput`**, not optional like their other fields (whose optionality exists for a pre-206 cached-reveal degrade path). Both real call sites always build a real audience object, so making it required forces every call site — including every pre-existing test — to state its audience explicitly.
- **`GUEST_SIGNUP_ASK_SCORE` branches on `input.audience.isGuest` directly**, not through `audienceKey`. This means a guest WITH games still gets the sign-up ask on a "caught-up" warm-up session (is_warmup can fire even with games, per the existing warm-up cause split) — this matches the plan's literal action text verbatim ("for both `hasGames` values") and is a deliberate scope difference from the four D-03 copy strings, which key off `audienceKey`'s hasGames-wins rule instead.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `TrainScheduleSettingsProps.isGuest` declared one task early**
- **Found during:** Task 2 (passing `isGuest` to `TrainScheduleSettings`)
- **Issue:** Task 2's action text has `TrainStartScreen` pass `isGuest={isGuest}` to `TrainScheduleSettings`, but Task 3 is the task that adds `isGuest` to `TrainScheduleSettingsProps`. As written, Task 2's own `<verify>` (`npm run lint && npm run build`) would fail with a TypeScript error (`Property 'isGuest' does not exist`) before Task 3 ever runs.
- **Fix:** Added `isGuest: boolean` to `TrainScheduleSettingsProps` in Task 2, destructured with a `void isGuest;` placeholder and a comment naming Task 3 as the consumer — the same pattern Plan 01 used for `Train.tsx`'s `isGuest`. Also added `isGuest={false}` as the default in `TrainScheduleSettings.test.tsx`'s `renderWithClient` helper (required field, same reasoning). Task 3 removed the `void` and wired the real resolver.
- **Files modified:** `frontend/src/components/train/TrainScheduleSettings.tsx`, `frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx`
- **Verification:** `npm run build` green after Task 2's commit; Task 3 completed the wiring without re-touching the prop declaration.
- **Committed in:** `263ad398e` (Task 2), completed in `1087639d4` (Task 3)

**2. [Rule 3 - Blocking] `hasImportedGames` added to the `useUserProfile` whole-module mock in `Train.solveLoop.test.tsx`**
- **Found during:** Task 2 (Train.tsx now imports `hasImportedGames` from `@/hooks/useUserProfile`)
- **Issue:** `Train.solveLoop.test.tsx` mocks the entire `@/hooks/useUserProfile` module (`vi.mock('@/hooks/useUserProfile', ...)`), providing only `useUserProfile`. Once `Train.tsx` also imports `hasImportedGames` from that module, the mock left it `undefined`, so calling it would throw at runtime.
- **Fix:** Added `hasImportedGames: () => true` to the mock, keeping this tracer on the `has_games` audience — consistent with every pre-existing assertion in the file.
- **Files modified:** `frontend/src/pages/__tests__/Train.solveLoop.test.tsx`
- **Verification:** `npx vitest run src/pages/__tests__/Train.solveLoop.test.tsx` — all tests pass.
- **Committed in:** `263ad398e` (Task 2)

### Documented Criterion Mismatches (no code change, pre-existing, verified via the actual intent instead)

**1. Task 1's literal em-dash `<verify>` command already fails on unrelated pre-existing content**
- **Found during:** Task 1 verification
- **Issue:** `! grep -n "—" frontend/src/lib/trainBotCopy.ts` fails (matches) because the file already contained 42 em-dash characters in doc comments BEFORE this plan touched it (confirmed via `git show HEAD:...`), none of them in copy strings. The acceptance criterion's actual intent — "no NEW string contains an em-dash" — is about literal copy strings, not comments (CLAUDE.md explicitly exempts comments from the em-dash rule).
- **Resolution:** Verified the intended criterion instead: none of the four new `Record<CopyAudienceKey, string>` copy tables or `GUEST_SIGNUP_ASK_SCORE` contain an em-dash (confirmed by grepping just those constant declarations). Did not reword 42 pre-existing, unrelated doc-comment em-dashes to force the blunt file-wide grep to pass.
- **Precedent:** Identical pattern to 224-02-SUMMARY.md's documented "welcome" grep mismatch.

**2. Task 3's literal complexity-probe `<verify>` command for `TrainScheduleSettings.tsx` fails on unrelated pre-existing lint noise**
- **Found during:** Task 3 verification
- **Issue:** `npx eslint --no-inline-config --rule 'complexity: ["error", 15]' src/components/train/TrainScheduleSettings.tsx` exits 1, but the failure is two `react-refresh/only-export-components` errors on pre-existing exported constants (`PUZZLES_PER_SESSION_PRESETS` and a sibling), each normally suppressed by an `eslint-disable-next-line` comment that `--no-inline-config` strips. Reproduced identically on the pre-Task-3 base commit (`git stash` + re-run), so this is not something Task 3 introduced. No output line contains "complexity".
- **Resolution:** Verified the real intent — no complexity error — via the project's actual `npm run lint` (which respects inline disables and passed clean, project-wide) and confirmed no "complexity" string in the isolated probe's output.

---

**Total deviations:** 2 auto-fixed (both Rule 3, blocking cross-task/cross-file compile issues), 2 documented pre-existing verification-criterion mismatches (no code changed for either).
**Impact on plan:** All functional and behavioral intent fully met and test-covered. No scope creep — every fix was either required for `npm run build`/`vitest` to pass or was a no-op documentation of an unsatisfiable literal grep/eslint invocation that predates this plan.

## Issues Encountered

None beyond the four items documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `TrainCopyAudience` and `resolveScheduleCardVisibility` are stable, tested primitives Plan 06 (the signup-ask bubble wiring) can build on directly.
- Full frontend suite green: 267 files, 4312 tests; `npm run lint`, `npm run build`, `npm run knip` all clean; `git diff --stat frontend/eslint.config.js` is empty (no new baseline entry).
- No blockers.

## Self-Check: PASSED

- `frontend/src/lib/trainBotCopy.ts` exports `TrainCopyAudience` and `GUEST_SIGNUP_ASK_SCORE` (FOUND)
- `frontend/src/components/train/TrainScheduleSettings.tsx` declares `resolveScheduleCardVisibility` (FOUND)
- Commit `b2088b88c` present in `git log` (FOUND)
- Commit `263ad398e` present in `git log` (FOUND)
- Commit `1087639d4` present in `git log` (FOUND)
- `( cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts src/components/train/__tests__ )` -> 514 tests passed
- `( cd frontend && npm run lint && npm run build && npm test -- --run )` -> all green, 267 files / 4312 tests
- `( cd frontend && npm run knip )` -> clean
- Complexity probes: `Train.tsx` (24) OK, `TrainStartScreen.tsx` (17) OK, `TrainScoreScreen.tsx` (15) OK (1 pre-existing unrelated warning), `trainBotCopy.ts` (15) OK, `TrainScheduleSettings.tsx` (15) — probe itself fails on pre-existing `--no-inline-config` lint noise (see Documented Criterion Mismatch #2); real gate (`npm run lint`) is clean

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-17*
