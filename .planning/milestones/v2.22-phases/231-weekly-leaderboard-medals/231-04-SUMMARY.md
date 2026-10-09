---
phase: 231-weekly-leaderboard-medals
plan: 04
subsystem: frontend
tags: [frontend, react, train, medals, dialog, audio, confetti]

requires:
  - phase: 231-weekly-leaderboard-medals
    provides: "Plan 02 claim API (GET /train/medals/unclaimed, POST /train/medals/claim -> 204); Plan 03 MedalIcon, trainMedals helpers, MedalKind types"
provides:
  - "Wire types UnclaimedMedal, UnclaimedMedalsResponse, MedalKey and trainApi.getUnclaimedMedals / claimMedals"
  - "useUnclaimedMedals / useClaimMedals hooks and TRAIN_UNCLAIMED_MEDALS_QUERY_KEY"
  - "MedalClaimDialog (presentational, props-only muted/reducedMotion) that Plan 05's admin demo renders from fixtures"
  - "TrainMedalDialogHost mounted on the Train landing"
  - "lib/trainMedals.ts: CLAIM_BUTTON_LABEL, MEDAL_POP_STAGGER_MS, medalDialogTitle, medalEntryLabel, weekOfLabel, medalKeys"
  - "index.css @keyframes medal-pop and .animate-medal-pop"
affects: [231-05]

actuals:
  tokens: 11150  # chars/4 over the realized frontend diff (44610 chars, 844 inserted lines)
  tasks: 2
  commits: 3
plan_head_before: 5b8c16b9db45c83e89858a2f48f9b4a85c1e3e8b
plan_head_after: 89880c7a7ad9566213d5e7ecf536f2bf833f38ea

tech-stack:
  added: []
  patterns:
    - "Presentational dialog with a settled ref (one callback per open cycle) plus a thin fetching host with per-mount closed state"
    - "open = query.isFetchedAfterMount && non-empty, so a stale cache entry can never show an already-claimed medal"

key-files:
  created:
    - frontend/src/hooks/useTrainMedals.ts
    - frontend/src/components/train/medals/MedalClaimDialog.tsx
    - frontend/src/components/train/medals/TrainMedalDialogHost.tsx
    - frontend/src/components/train/medals/__tests__/MedalClaimDialog.test.tsx
    - frontend/src/components/train/medals/__tests__/TrainMedalDialogHost.test.tsx
  modified:
    - frontend/src/types/train.ts
    - frontend/src/api/client.ts
    - frontend/src/lib/trainMedals.ts
    - frontend/src/index.css
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
    - frontend/src/lib/__tests__/trainMedals.test.ts

key-decisions:
  - "Own close button (ghost icon Button, aria-label Close, testid) with showCloseButton false, and aria-describedby undefined on DialogContent to silence Radix's missing-description warning (no visible description is wanted)"
  - "handleClaim returns early when the settled ref is already set, so a double tap before the container closes the dialog cannot replay the chime or confetti"
  - "useClaimMedals prunes the claimed keys from the cached unclaimed list on success and never invalidates it"

patterns-established:
  - "Host never fetches for guests, under impersonation, or before the profile resolves"

requirements-completed: []

coverage:
  - id: D1
    description: "Opening the Train landing with an unclaimed medal shows one dialog ('You won N medals!'); guests, impersonating admins and an empty list show nothing and fire no GET where gated; a stale cached list never opens it"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/medals/__tests__/TrainMedalDialogHost.test.tsx (shows the dialog; guest; impersonation; waits for the profile; empty list; pre-seeded cache)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Claim and dismiss each POST the shown keys exactly once; the dialog closes and does not reopen after an invalidation in the same mount; no analytics event"
    verification:
      - kind: unit
        ref: "TrainMedalDialogHost.test.tsx (Claim posts once and does not reopen; dismiss posts once with no effects; no analytics event)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Host mounts in the empty, completed and fresh/resume branches only, with isGuest threaded; never in loading or error; no dialog during the solve loop"
    verification:
      - kind: unit
        ref: "TrainStartScreen.test.tsx 'Phase 231 D-10: medal dialog host mount'; Train.solveLoop.test.tsx (queryByTestId train-medal-dialog null on landing and in loop)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Claim tap: unlockAudio, then game-win chime once (unless muted), then confetti (unless reduced motion), then one onClaim; dismiss and Escape are silent; no second callback after Claim"
    verification:
      - kind: unit
        ref: "medals/__tests__/MedalClaimDialog.test.tsx 'Claim path' and 'dismiss path' blocks (call order via invocationCallOrder)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Entry copy and order (Gold, Points (shared); Week of Sep 28; 412 pts / 87%), title count, medal pop with 120 ms stagger omitted under reduced motion, weekOfLabel stable in a western time zone"
    verification:
      - kind: unit
        ref: "MedalClaimDialog.test.tsx 'content' and 'medal pop'; lib/__tests__/trainMedals.test.ts (TZ America/Los_Angeles)"
        status: pass
    human_judgment: false
  - id: D6
    description: "First-tap win sound and confetti on a real iPhone (cold page load), pop animation feel"
    verification:
      - kind: manual
        ref: "UAT through the Plan 05 admin demo (RESEARCH A5)"
        status: unrun
    human_judgment: true

duration: 35min
completed: 2026-10-04
status: complete
---

# Phase 231 Plan 04: Medal claim dialog Summary

**Opening the Train landing after a week closes now shows one dialog listing every unclaimed medal; the Claim tap unlocks audio, plays the existing win chime once, throws confetti and pops the medals in, and both Claim and dismiss record the claim with a single POST.**

## Performance

- **Duration:** about 35 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 5 created, 8 modified

## Accomplishments

- Wire types, `trainApi.getUnclaimedMedals` / `claimMedals`, and the `useUnclaimedMedals` (refetchOnMount always, `enabled`) and `useClaimMedals` hooks; a successful claim prunes the cached list, with no invalidation.
- `TrainMedalDialogHost`: disabled for guests, under impersonation (T-231-16) and until the profile resolves; opens only when the list was fetched after this mount and is non-empty; per-mount closed state; ignores `leaderboard_hidden` (D-04). Mounted first in the landing container for the empty, completed and fresh/resume/warmup branches.
- `MedalClaimDialog`: presentational, settled-ref guard so Claim/Escape/close/outside-click produce one callback per open cycle; entries in server order with `MedalIcon` size-10, "Gold, Points (shared)" label and "Week of Sep 28 · 412 pts" line.
- Celebration: `unlockAudio()` then `playSound('game-win')` (once per tap, unless muted), then `fireWinConfetti()` (unless reduced motion), then `onClaim`; `animate-medal-pop` with a 120 ms stagger per medal, omitted under reduced motion, plus a `prefers-reduced-motion` CSS override.
- No `trackFeature` / `trackEvent` anywhere in the dialog, host or hooks (grep gate and a host test). `sounds.ts` and `confetti.ts` are untouched (no new audio asset or SoundEvent).

## Task Commits

1. **Task 1 (tracer): types, API, hooks, dialog, host, landing mount, tests** - `cebdcae70` (feat)
2. **Task 2 RED: celebration tests** - `e3a166c49` (test)
3. **Task 2 GREEN: sound, confetti, pop animation, double-tap guard** - `89880c7a7` (feat)

## Verification

- Task 1 verify (vitest on medals, TrainStartScreen, Train.solveLoop; lint; build; knip) passed before Task 2 began (tracer gate, auto/end-of-phase mode, automated-only verify).
- Full suite `npm test -- --run`: 302 files, 4965 tests passed. `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean (knip prints only the pre-existing `.css` configuration hint).
- Mutation check: removing `isFetchedAfterMount` from the host makes the pre-seeded-cache test fail (restored afterwards).
- Acceptance greps: `TrainMedalDialogHost` appears 5 times in `TrainStartScreen.tsx`; one `/train/medals/claim` and one `/train/medals/unclaimed` in `client.ts`; 0 `trackFeature|trackEvent` in the three files; `@keyframes medal-pop` once, `animate-medal-pop` twice in `index.css`; `playSound('game-win')` once; 0 `new Date(` in `trainMedals.ts`; empty `git diff` for `sounds.ts` and `confetti.ts`; `MedalClaimDialog.test.tsx` has 13 tests.
- Spec-less probe fallback skipped: the phase has no requirement IDs to probe (as recorded in Plan 01).

## TDD Gate Compliance

Task 1 is `type="tracer"` (feat commit with its tests). Task 2: RED `e3a166c49` failed on 4 behavior tests (Claim order, muted, reduced motion, pop class); the helper tests and dismiss tests passed at RED because Task 1 had already shipped those helpers and the dismiss path. GREEN `89880c7a7` passes all. No refactor commit. The `gsd_run check tdd-red-evidence` record was not produced; the failing assertions are the evidence, as in Plans 01 and 03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Double Claim tap replayed the chime and confetti**
- **Found during:** Task 2 GREEN review
- **Issue:** the settled ref only guarded the callback; a second tap before the container closed the dialog would run `unlockAudio`/`playSound`/`fireWinConfetti` again, breaking D-12 "exactly once per Claim tap".
- **Fix:** `handleClaim` returns early when the settled ref is set; added a test.
- **Files modified:** `MedalClaimDialog.tsx`, `MedalClaimDialog.test.tsx`
- **Commit:** `89880c7a7`

**Total deviations:** 1 auto-fixed. **Impact:** none on scope; one extra test.

## Auth Gates

None.

## Known Stubs

None. The dialog and host are wired to the real claim API.

## Threat Flags

None beyond the plan's threat model. T-231-16 (impersonation) is mitigated and tested; T-231-17 (duplicate POSTs) by the settled ref, per-mount closed state and tests; T-231-18 by the no-analytics grep gate and test.

## Notes for Plan 05

- `MedalClaimDialog` and `MedalClaimDialogProps` are exported; the production consumers today are the host and tests. The admin demo passes simulated `muted` / `reducedMotion` props. `playSound` still checks the real persisted mute preference, and the CSS media query still stops the animation under an OS reduce-motion setting, so say so in the demo helper text.
- Manual UAT still owed: first-tap win sound and confetti on a real iPhone (RESEARCH A5).

## Self-Check: PASSED

Created files exist on disk; commits `cebdcae70`, `e3a166c49`, `89880c7a7` exist; `commits: 3` measured from `git rev-list --count 5b8c16b9d..HEAD` using the persisted ledger.
