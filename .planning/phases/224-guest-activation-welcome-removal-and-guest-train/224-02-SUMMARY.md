---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 02
subsystem: frontend
tags: [react-router, vitest, tanstack-query, guest-activation]

# Dependency graph
requires:
  - phase: 224-guest-activation-welcome-removal-and-guest-train
    provides: "Train open to every zero-game account (Plan 01) — this plan's hasImportedGames helper is shared with the Train copy branch Plan 04 consumes"
provides:
  - "hasImportedGames(profile) — the single definition of the zero-game test, exported from useUserProfile.ts"
  - "Home.tsx sends every authenticated account, guest or registered, to /library/games or /library/import — no /welcome branch"
  - "welcomeDismissal.ts deleted; the welcome_dismissed localStorage flag is fully removed from the decision path"
  - "/welcome rewritten as a four-delta explanation page with a guest-only Sign up free button and a universal Back affordance"
affects: [224-04-games-less-train-copy]

# Actuals (#2632)
actuals:
  tokens: 6034
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hasImportedGames(profile) as the single shared zero-game predicate, exported next to useUserProfile so both Home and Train import the same definition instead of re-deriving the game-count sum"

key-files:
  created:
    - frontend/src/pages/__tests__/Home.redirect.test.tsx
  modified:
    - frontend/src/hooks/useUserProfile.ts
    - frontend/src/pages/Home.tsx
    - frontend/src/pages/Welcome.tsx
    - frontend/src/pages/__tests__/Welcome.test.tsx
    - frontend/src/lib/botGameSnapshot.ts
  deleted:
    - frontend/src/lib/welcomeDismissal.ts

key-decisions:
  - "The plan's literal acceptance criterion `grep -c \"welcome\" frontend/src/pages/Home.tsx returns 0` and its matching <verify> `! grep -in \"welcome\" ...` are unsatisfiable as written — three pre-existing, unrelated prose lines (\"Contributions and feedback are welcome\", \"feature requests are welcome on\") already contained the plain English word before this plan touched the file. Did not reword that unrelated prose to force the grep to pass; verified the functionally equivalent, actually-intended checks instead (no @/lib/welcomeDismissal import, no <Navigate to=\"/welcome\">, exactly one <Navigate> in the authenticated branch) — all pass."
  - "Registered visitor to /welcome renders the same four deltas with no redirect and no sign-up button (Claude's Discretion in 224-CONTEXT.md, resolved as documented in the file's own comment) — a dead-end redirect on a page reachable only by a typed URL is worse than an honest explanation."

requirements-completed: [GUESTACT-01, GUESTACT-08]

coverage:
  - id: D1
    description: "hasImportedGames(profile) is the single definition of the zero-game test, shared by Home and (later) Train"
    requirement: "GUESTACT-01"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Home.redirect.test.tsx#HomePage redirect (Phase 224 S-1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every authenticated account, guest or registered, leaves the home CTA for /library/games or /library/import; no code path navigates to /welcome"
    requirement: "GUESTACT-01"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Home.redirect.test.tsx#zero-game guest resolves to /library/import"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Home.redirect.test.tsx#zero-game registered account resolves to /library/import"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Home.redirect.test.tsx#guest with games resolves to /library/games"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Home.redirect.test.tsx#never produces a /welcome destination for any profile fixture"
        status: pass
    human_judgment: false
  - id: D3
    description: "/welcome renders four deltas and one Sign up free button (guests only); the comparison table and dismissal checkbox are gone; a Back affordance is present for everyone"
    requirement: "GUESTACT-08"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Welcome.test.tsx#renders the page container and exactly four delta items"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Welcome.test.tsx#guest fixture renders the Sign up free button with signup-cta umami attrs"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Welcome.test.tsx#registered fixture renders no Sign up free button"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Welcome.test.tsx#renders the Back affordance for both fixtures with no umami attribute"
        status: pass
      - kind: unit
        ref: "frontend/src/pages/__tests__/Welcome.test.tsx#has no dismissal checkbox"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-17
status: complete
---

# Phase 224 Plan 2: Home Redirect Unification and /welcome Rewrite Summary

**One redirect rule sends every zero-game account (guest or registered) to `/library/import`, the `welcome_dismissed` localStorage gate is deleted, and `/welcome` is now a four-delta explanation page reachable only by choice.**

## Performance

- **Duration:** 40 min
- **Tasks:** 2
- **Files modified:** 6 (1 deleted, 1 created)

## Accomplishments

- Added `hasImportedGames(profile)` to `useUserProfile.ts` as the single shared definition of the zero-game test
- `Home.tsx` now has exactly one `<Navigate>` in its authenticated branch: `/library/games` (has games) or `/library/import` (zero games), for guest and registered accounts alike
- `welcomeDismissal.ts` deleted; every importer and prose reference updated or removed
- `/welcome` rewritten from a ten-row comparison table + dismissal checkbox into a four-delta explanation with a guest-only Sign up free button and a universal Back affordance

## Task Commits

Each task was committed atomically:

1. **Task 1: Single home redirect rule plus the shared zero-game helper and its test** - `dde5c2cf8` (feat)
2. **Task 2: Rewrite /welcome as the four-delta page and delete the dismissal module** - `1aad25b51` (feat)

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `frontend/src/hooks/useUserProfile.ts` - added exported `hasImportedGames(profile)`
- `frontend/src/pages/Home.tsx` - removed `welcomeDismissal` import and `/welcome` branch; single `<Navigate>` via `hasImportedGames`
- `frontend/src/pages/__tests__/Home.redirect.test.tsx` - new: 4 redirect cases (zero-game guest, zero-game registered, guest-with-games, no-`/welcome`-ever assertion)
- `frontend/src/pages/Welcome.tsx` - rewritten: four named-constant deltas, guest-only Sign up free button, universal Back button, `is_guest` read from `useUserProfile`
- `frontend/src/pages/__tests__/Welcome.test.tsx` - rewritten: dropped the localStorage/Proceed tests, added delta/button/back coverage
- `frontend/src/lib/welcomeDismissal.ts` - deleted
- `frontend/src/lib/botGameSnapshot.ts` - reworded its two prose mentions of the deleted module

## Decisions Made

- Registered visitors to `/welcome` see the same four deltas with no sign-up button and no redirect (documented in the file's own comment) — reachable only by a typed URL, so an honest static explanation beats a dead-end redirect.
- The Sign up button's promotion handoff (`logoutForPromotion()` then `window.location.href = '/login?tab=register'`) was lifted verbatim so the `welcome` umami source (S-7) survives unchanged.

## Deviations from Plan

### Auto-fixed Issues

None — both tasks' functional acceptance criteria were satisfied without needing a Rule 1-3 fix.

### Documented Criterion Mismatch

**1. [Verification impossible as literally stated] `grep -c "welcome" frontend/src/pages/Home.tsx` cannot return 0**
- **Found during:** Task 1 verification
- **Issue:** Task 1's acceptance criteria list `grep -c "welcome" frontend/src/pages/Home.tsx` returning 0, and the `<verify>` block runs `! grep -in "welcome" frontend/src/pages/Home.tsx` expecting no match. Three pre-existing, unrelated prose lines already contained the literal English word "welcome" before this plan touched the file: "Contributions and feedback are welcome." (x2, GitHub-issue copy) and "reports and feature requests are welcome on{' '}" (community-links copy). None of these relate to the `/welcome` route or the deleted dismissal module.
- **Resolution:** Did not reword unrelated prose purely to satisfy an overly broad string match — that would be out-of-scope content editing with no functional benefit. Verified the criteria that actually express this task's intent instead: `grep -c "@/lib/welcomeDismissal" frontend/src/pages/Home.tsx` → 0, `grep -c '<Navigate to="/welcome"' frontend/src/pages/Home.tsx` → 0, and exactly one `<Navigate` expression in the authenticated branch (confirmed by reading the file). All pass.
- **Files modified:** None (no fix applied; documented instead)
- **Verification:** Confirmed via targeted greps above and the passing `Home.redirect.test.tsx` suite (4/4)

---

**Total deviations:** 0 auto-fixed; 1 documented verification-criterion mismatch (no code change, no scope creep)
**Impact on plan:** None on functionality — the plan's actual intent (no code path forces `/welcome`) is fully met and test-covered; the mismatch was in an overly literal grep string, not in the implementation.

## Issues Encountered

None beyond the documented criterion mismatch above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `hasImportedGames(profile)` is available for Plan 04's Train games-less copy branch (D-03), which consumes it alongside `isGuest`.
- `/welcome` is a stable, reachable-by-choice page for the "Why?" buttons Plan 04/06 will wire up.
- Full frontend suite green (267 files, 4293 tests); `npm run lint`, `npm run build`, `npm run knip` all clean.
- No blockers.

## Self-Check: PASSED

- `frontend/src/hooks/useUserProfile.ts` exports `hasImportedGames` (FOUND: `grep -c "export function hasImportedGames" frontend/src/hooks/useUserProfile.ts` → 1)
- `frontend/src/lib/welcomeDismissal.ts` does not exist (FOUND, confirmed absent)
- `frontend/src/pages/__tests__/Home.redirect.test.tsx` exists (FOUND)
- Commit `dde5c2cf8` present in `git log` (FOUND)
- Commit `1aad25b51` present in `git log` (FOUND)
- `( cd frontend && npx vitest run src/pages/__tests__/Home.redirect.test.tsx src/pages/__tests__/Welcome.test.tsx )` → 10 passed
- `( cd frontend && npm test -- --run )` → 267 files, 4293 tests passed
- `( cd frontend && npm run lint && npm run build && npm run knip )` → all green
- `grep -rl "welcomeDismissal" frontend/src` → no output

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-17*
