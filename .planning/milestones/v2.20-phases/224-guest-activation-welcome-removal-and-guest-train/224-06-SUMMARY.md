---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 06
subsystem: frontend
tags: [react, typescript, vitest, guest-activation, bot-copy, umami]

# Dependency graph
requires:
  - phase: 224-guest-activation-welcome-removal-and-guest-train
    provides: "TrainScoreScreen's hasGames/isGuest props and GUEST_SIGNUP_ASK_SCORE (Plan 04); /welcome as the four-delta page the Why? button targets (Plan 02)"
provides:
  - "SignupAskActions({ source }) — the shared Why?/Sign up free action pair (S-4), hosted in TrainBotBubble's existing actions slot on two surfaces"
  - "ImportGuestPromoBubble — the friendly-bot bubble replacing the Import page's guest Alert (S-6, D-06)"
  - "signup-cta with per-surface data-umami-event-source (train-score, import-promo) — lever B attribution (S-7, ROADMAP SC 9)"
affects: []

# Actuals (#2632)
actuals:
  tokens: 6880
  tasks: 4
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level guard components (GuardedReminderControl/GuardedReminderBelowRow) that carry exactly one guest-guard ternary each, so a guest-branch ternary's complexity is measured against a small dedicated function instead of the host component when the host is already near a complexity cap"

key-files:
  created:
    - frontend/src/components/train/SignupAskActions.tsx
    - frontend/src/components/train/__tests__/SignupAskActions.test.tsx
    - frontend/src/components/import/ImportGuestPromoBubble.tsx
    - frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx
  modified:
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/pages/Import.tsx
    - CHANGELOG.md

key-decisions:
  - "Task 1 was written test-first per the plan's TDD flag: the RED-phase commit ships an intentionally incomplete stub (returns <></>) so all 7 assertions fail on real behavior, not on a missing-module import error; GREEN then implements the real component."
  - "TrainScoreScreen's own guest-guard ternaries were reduced from 3 to 1 inline: the reminderControl/reminderBelowRow guards were extracted into two tiny module-level components (GuardedReminderControl, GuardedReminderBelowRow), each carrying exactly one ternary, so CLAUDE.md's per-function complexity cap (15) is respected without changing any rendered DOM (Fragments are transparent) or any acceptance-criteria grep (the literal ternary text still appears in the file)."
  - "The Import bubble's persona is memoised via useMemo(() => pickBot('friendly'), []), mirroring TrainScoreScreen's own pickBot('smart') memo rationale verbatim — ImportPage re-renders on every import-job poll tick."

requirements-completed: [GUESTACT-05, GUESTACT-07, GUESTACT-11]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "SignupAskActions renders the S-4 Why?/Sign up free pair for either surface, with the umami contract (Sign up free carries signup-cta + per-surface source, Why? carries none) and the promotion handoff (logoutForPromotion then a hard nav) asserted by tests"
    requirement: "GUESTACT-11"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/SignupAskActions.test.tsx#SignupAskActions (7 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A guest finishing a Train session sees the sign-up ask inside the score bubble and no reminder/QR/push surface at all; the registered screen renders exactly what it rendered before (ROADMAP SC 3)"
    requirement: "GUESTACT-05"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx#the guest branch (S-3, S-4, GUESTACT-05) (4 new tests, 35 total in file)"
        status: pass
      - kind: other
        ref: "npx eslint --no-inline-config --rule 'complexity: [\"error\", 15]' src/components/train/TrainScoreScreen.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every guest visit to the Import page shows a friendly-bot bubble with the same Why?/Sign up free pair; the old Alert and its two testids are gone; no third button or Train pitch (D-02)"
    requirement: "GUESTACT-07"
    verification:
      - kind: unit
        ref: "frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx#ImportGuestPromoBubble (4 tests)"
        status: pass
      - kind: integration
        ref: "npx vitest run src/pages/__tests__/Import.stateMachine.test.tsx src/pages/__tests__/Import.queuedState.test.tsx src/pages/__tests__/Import.pasteHandoff.test.tsx (14 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "CHANGELOG.md [Unreleased] describes both levers in product language; Phase 223's existing bullets are untouched"
    verification:
      - kind: other
        ref: "grep -c '^## \\[Unreleased\\]' CHANGELOG.md == 1; new bullets scanned for GUESTACT-/.tsx/.py/D-label/\"phase\" — none found"
        status: pass
    human_judgment: false
  - id: D5
    description: "No complexity ceiling moved and no new baseline entry was added to eslint.config.js across the whole phase"
    verification:
      - kind: other
        ref: "git diff --quiet $(git merge-base HEAD main)..HEAD -- frontend/eslint.config.js"
        status: pass
      - kind: other
        ref: "npm run lint (whole-project) — clean; npm run build — clean; npm run knip — clean; npm test -- --run — 269 files / 4327 tests passed"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-17
status: complete
---

# Phase 224 Plan 6: Signup Ask Bubbles (Score Screen + Import Page) Summary

**One shared `SignupAskActions` component (Why? / Sign up free) now hosts the sign-up ask inside `TrainBotBubble`'s actions slot on both the guest Train score screen and a new friendly-bot bubble on the Import page, replacing the reminder ask and the old Alert respectively, each attributed via its own `signup-cta` umami source.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-17T21:28:00Z (approx.)
- **Completed:** 2026-09-17T22:23:09Z
- **Tasks:** 4
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments

- `SignupAskActions({ source: 'train-score' | 'import-promo' })` — a bare two-`Button` fragment copied from `BotDrawOfferActions`'s shape: "Why?" (`brand-outline`, navigates to `/welcome`, no umami attribute) then "Sign up free" (`default`, `logoutForPromotion()` then a hard nav to `/login?tab=register`, `data-umami-event="signup-cta"` + `data-umami-event-source={source}`). Built test-first (RED: stub returning nothing, 7 failing assertions; GREEN: real implementation, all 7 pass).
- `TrainScoreScreen.tsx`: the bubble now receives `actions={isGuest ? <SignupAskActions source="train-score" /> : undefined}` (registered users get `undefined`, so `TrainBotBubble`'s `actions !== undefined` guard renders nothing new — byte-identical registered DOM, ROADMAP SC 3); the reminder control and below-row content are both suppressed for a guest via two module-level guard components that keep `TrainScoreScreen`'s own cyclomatic complexity at 14 (cap 15).
- `ImportGuestPromoBubble` (`frontend/src/components/import/`, new directory): a `pickBot('friendly')`-hosted `TrainBotBubble` (`state="prompt"`) carrying the D-06 import-specific copy (`IMPORT_GUEST_SIGNUP_COPY`, exported) and `SignupAskActions source="import-promo"`. `Import.tsx`'s guest branch now renders this component instead of an inline `Alert`; the `import-guest-promo-info`/`-link` testids and the now-unused `DoorOpen`/`useAuth` imports are gone.
- `CHANGELOG.md` `[Unreleased]` gained one `Added` bullet (Train open to everyone) and four `Changed` bullets (welcome-page skip, bot-voiced sign-up prompt, hidden guest reminders, 30-day Train-state purge), all in product language with no internal identifiers; Phase 223's bullets are untouched.

## Task Commits

Each task was committed atomically (Task 1 as a TDD RED/GREEN pair):

1. **Task 1 RED: failing test for SignupAskActions** — `beaec930f` (test)
2. **Task 1 GREEN: implement SignupAskActions** — `fec5fb764` (feat)
3. **Task 2: guest score screen asks for sign-up, drops the reminder surface** — `c822992c3` (feat)
4. **Task 3: Import page guest promo becomes a friendly-bot bubble** — `8c98b4bc4` (feat)
5. **Task 4: changelog entry** — `449285ca1` (docs)

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `frontend/src/components/train/SignupAskActions.tsx` - the shared Why?/Sign up free action pair
- `frontend/src/components/train/__tests__/SignupAskActions.test.tsx` - umami contract + promotion-handoff coverage for both sources
- `frontend/src/components/train/TrainScoreScreen.tsx` - guest branch: bubble `actions`, guarded reminder row (2 new module-level helpers)
- `frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx` - new "the guest branch" describe block (4 tests)
- `frontend/src/components/import/ImportGuestPromoBubble.tsx` - new component + exported `IMPORT_GUEST_SIGNUP_COPY`
- `frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx` - new test file, new directory
- `frontend/src/pages/Import.tsx` - guest `Alert` replaced with `<ImportGuestPromoBubble />`; unused imports removed
- `CHANGELOG.md` - five new `[Unreleased]` bullets across `Added`/`Changed`

## Decisions Made

- TDD RED phase for Task 1 shipped a deliberately incomplete stub component (`return <></>`) rather than skipping straight to the real implementation, so the RED commit's 7 failing assertions are genuine behavior failures, not import-resolution errors.
- Extracted `GuardedReminderControl`/`GuardedReminderBelowRow` (module-level, one ternary each) rather than inlining all three of Task 2's guest-guard ternaries in `TrainScoreScreen`'s own JSX — see Deviations below.
- `ImportGuestPromoBubble`'s persona uses `useMemo(() => pickBot('friendly'), [])`, matching `TrainScoreScreen`'s own memo rationale (poll-driven re-renders must not recast the bot mid-read).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - CLAUDE.md complexity cap, precedence over the plan's literal "nothing else" instruction] TrainScoreScreen's three inline guest-guard ternaries breached the complexity cap**
- **Found during:** Task 2, post-implementation verification
- **Issue:** The plan's literal action text has three ternaries land directly in `TrainScoreScreen`'s JSX (`actions={isGuest ? ... }`, `{isGuest ? null : reminderControl}`, `{isGuest ? null : reminderBelowRow}`) and asserts "the component has two branches of headroom against the un-baselined cap of 15." Measured baseline (pre-Task-2, via `git show HEAD:...` + an isolated eslint probe) was complexity 13, not the ~12 the plan's headroom claim implies — three new ternaries land at complexity 16, one over CLAUDE.md's hard "must be fixed, not baselined" cap of 15 for new code.
- **Fix:** Kept the `actions` ternary inline (complexity 13→14). Extracted the two reminder-row guard ternaries into `GuardedReminderControl`/`GuardedReminderBelowRow`, tiny module-level components whose complexity (2 each) is measured independently of `TrainScoreScreen`'s. Fragments are transparent in the DOM, so no rendered markup changed, and the literal ternary text (`{isGuest ? null : reminderControl}` / `{isGuest ? null : reminderBelowRow}`) still appears in the file — the plan's own acceptance-criteria greps (file-wide, not location-scoped) still pass.
- **Files modified:** `frontend/src/components/train/TrainScoreScreen.tsx`
- **Verification:** `npx eslint --no-inline-config --rule 'complexity: ["error", 15]' src/components/train/TrainScoreScreen.tsx` — clean (only the pre-existing, unrelated `react-hooks/exhaustive-deps` warning); all 35 tests in `TrainScoreScreen.test.tsx` pass unchanged; `npm run lint`/`npm run build` clean.
- **Committed in:** `c822992c3` (Task 2)

### Documented Criterion Mismatches (no code change; verified via the actual intent instead)

**1. Task 3's literal complexity-probe threshold predicted a drop that didn't happen**
- **Found during:** Task 3 verification
- **Issue:** The plan's action text states `ImportPage` "goes from complexity 29 to 28" after replacing the inline `Alert` block with `<ImportGuestPromoBubble />`. Measured baseline (pre-Task-3) was already exactly 29, and stayed exactly 29 after the change — the removed `onClick` arrow function was its own separately-measured function (ESLint's `complexity` rule scores nested functions independently), not a branch counted against `ImportPage` itself, so removing it could never lower `ImportPage`'s own score.
- **Resolution:** The actual acceptance criterion — `npx eslint --no-inline-config --rule 'complexity: ["error", 29]' src/pages/Import.tsx` reports no complexity error — is satisfied (29 does not exceed the 29 cap). No code change was needed or made; the plan's specific numeric prediction was simply inaccurate, matching the pattern already documented in 224-02-SUMMARY.md and 224-04-SUMMARY.md for other literal-but-inaccurate verification text in this phase.
- **Precedent:** Identical pattern to 224-02-SUMMARY.md's "welcome" grep mismatch and 224-04-SUMMARY.md's two documented mismatches.

**2. Task 4's literal changelog `<verify>` grep scans the whole (multi-year) file, not just the new bullets**
- **Found during:** Task 4 verification
- **Issue:** `! grep -nE 'GUESTACT-|\.tsx|\.py' CHANGELOG.md` is written as a whole-file check, but `CHANGELOG.md` has years of prior release entries that legitimately reference `.py` scripts, file paths, and the word "phase" (e.g. `scripts/backfill_flaws.py`, `(Phase 113 Plan 01)`). The command necessarily fails against pre-existing, unrelated history.
- **Resolution:** Verified the actual intent — the acceptance criterion's own prose ("No new bullet contains a file path, a `GUESTACT-` id, a `D-` decision label or the word 'phase'") — by scanning only the five newly-added bullets (lines under `[Unreleased]`). None contain any of the forbidden patterns. Did not reword decades of unrelated changelog history to force a file-wide grep to pass.
- **Precedent:** Identical pattern to 224-02-SUMMARY.md's documented "welcome" grep mismatch.

---

**Total deviations:** 1 auto-fixed (Rule 1, CLAUDE.md complexity cap), 2 documented verification-criterion mismatches (no code changed for either).
**Impact on plan:** All functional and behavioral intent fully met and test-covered. No scope creep — the one fix was required to keep `npm run lint` clean per CLAUDE.md's mandatory complexity rule; both documented mismatches were literal-but-inaccurate `<verify>` text, not gaps in the implementation.

## Issues Encountered

None beyond the three items documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `SignupAskActions` is a stable, tested, reusable primitive for any future surface that needs the S-4 sign-up ask pair.
- Full frontend suite green: 269 files, 4327 tests; `npm run lint`, `npm run build`, `npm run knip` all clean; `git diff --quiet` on `frontend/eslint.config.js` across the whole phase confirms no complexity baseline drift.
- This is the last plan of Phase 224's active plans besides 224-03 (paused at a human checkpoint, untouched by this plan) — phase-level verification and the pre-merge gate remain before merge to `main`.
- No blockers.

## Self-Check: PASSED

- `frontend/src/components/train/SignupAskActions.tsx` exports `SignupAskActions` and `SignupAskSource` (FOUND: `grep -c "export function SignupAskActions\|export type SignupAskSource"` → 2)
- `frontend/src/components/import/ImportGuestPromoBubble.tsx` exports `ImportGuestPromoBubble` and `IMPORT_GUEST_SIGNUP_COPY` (FOUND)
- Commit `beaec930f` present in `git log` (FOUND)
- Commit `fec5fb764` present in `git log` (FOUND)
- Commit `c822992c3` present in `git log` (FOUND)
- Commit `8c98b4bc4` present in `git log` (FOUND)
- Commit `449285ca1` present in `git log` (FOUND)
- `( cd frontend && npx vitest run src/components/train/__tests__/SignupAskActions.test.tsx src/components/train/__tests__/TrainScoreScreen.test.tsx src/components/import/__tests__/ImportGuestPromoBubble.test.tsx )` → 46 passed
- `( cd frontend && npm run lint && npm run build && npm run knip && npm test -- --run )` → all green, 269 files / 4327 tests
- `git diff --quiet $(git merge-base HEAD main)..HEAD -- frontend/eslint.config.js` → no drift

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-17*
