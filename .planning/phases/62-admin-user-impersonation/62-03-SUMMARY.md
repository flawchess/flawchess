---
phase: 62-admin-user-impersonation
plan: 03
subsystem: frontend
tags: [frontend, auth, types, shadcn, theme, tdd]

requires:
  - phase: 62-admin-user-impersonation
    plan: 01
    provides: ImpersonateResponse backend shape (access_token, token_type, target_email, target_id), POST /api/admin/impersonate/{user_id} endpoint, ImpersonationContext schema
  - phase: 62-admin-user-impersonation
    plan: 02
    provides: GET /api/admin/users/search endpoint and UserProfileResponse.impersonation field
provides:
  - shadcn Command + Popover primitives (plus transitive input-group + textarea)
  - IMPERSONATION_PILL_BG/FG/BORDER theme tokens (oklch hue ~40)
  - frontend/src/types/admin.ts — ImpersonationContext, ImpersonateResponse, UserSearchResult
  - UserProfile.impersonation field matching backend response shape
  - useAuth.impersonate(userId) method on AuthState context
  - isImpersonating(profile) pure helper with 4 passing vitest unit tests
affects: [62-04-frontend-admin-page, 62-05-frontend-pill-header]

tech-stack:
  added:
    - "cmdk ^1.1.1 (transitively via shadcn add command)"
  patterns:
    - "Token-swap ordering mirrors login() — localStorage.setItem BEFORE queryClient.clear AFTER setToken LAST (preserves the bug-fix comment about refetches picking up the new token)"
    - "Pure-helper testing (option b) — no @testing-library/react introduced; component render paths deferred to manual QA per phase testing strategy"
    - "Theme tokens as oklch() strings colocated in frontend/src/lib/theme.ts alongside existing WDL/gauge/zone constants (no hard-coded semantic colors in components)"

key-files:
  created:
    - frontend/src/components/ui/command.tsx
    - frontend/src/components/ui/popover.tsx
    - frontend/src/components/ui/input-group.tsx
    - frontend/src/components/ui/textarea.tsx
    - frontend/src/types/admin.ts
    - frontend/src/lib/impersonation.ts
    - frontend/src/lib/impersonation.test.ts
  modified:
    - frontend/src/hooks/useAuth.ts
    - frontend/src/types/users.ts
    - frontend/src/lib/theme.ts
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Used the shadcn CLI with piped 'n' answers so the overwrite prompts for existing button.tsx, input.tsx, dialog.tsx, popover.tsx are declined (project-specific variants like brand-outline on button.tsx must be preserved). Popover.tsx was created fresh since it did not exist."
  - "Accepted transitive deps input-group.tsx and textarea.tsx as necessary for command.tsx to compile (CommandInput wraps InputGroup). Not an overreach — these are required for the Plan 04 combobox."
  - "Reworked the 4th unit test to use Record spread + delete instead of destructuring with an underscore-prefixed discard, since the project ESLint config flags underscore-prefixed unused vars."

patterns-established:
  - "Pure-helper unit tests for frontend testable units (option b) — 4 test cases cover object/null/undefined/missing-field branches, tested via vitest without DOM environment."
  - "Impersonation theme tokens as IMPERSONATION_PILL_* oklch constants in theme.ts rather than inline Tailwind — mirrors WDL_WIN/LOSS/DRAW pattern."

requirements-completed: [D-09, D-12, D-13, D-22]

duration: 20min
completed: 2026-04-17
---

# Phase 62 Plan 03: Frontend Foundation Summary

**Frontend foundation for admin impersonation — shadcn Command + Popover primitives installed, theme tokens for the header pill added, UserProfile extended with the impersonation field from Plan 02, useAuth.impersonate(userId) wired against Plan 01's endpoint, and a pure isImpersonating helper backed by 4 passing vitest unit tests (no DOM testing framework introduced).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-17T17:20Z
- **Completed:** 2026-04-17T17:25Z
- **Tasks:** 3
- **Files modified:** 12 (7 created, 5 modified)

## Accomplishments

- Installed shadcn Command + Popover (plus transitive input-group + textarea); cmdk ^1.1.1 added to dependencies. Existing info-popover.tsx (uses radix-ui Popover directly) preserved — both coexist without conflict.
- Added IMPERSONATION_PILL_BG/FG/BORDER oklch tokens to theme.ts (hue ~40, deliberately distinct from amber Guest badge at hue ~80 and WDL_LOSS at hue ~25).
- Created frontend/src/types/admin.ts with ImpersonationContext, ImpersonateResponse, UserSearchResult matching the Plan 01/02 backend schemas.
- Extended UserProfile with `impersonation: ImpersonationContext | null` (D-22).
- Added useAuth.impersonate(userId) method to AuthState — POSTs to /api/admin/impersonate/{userId}, stores the token in localStorage BEFORE queryClient.clear (bug-fix ordering mirrors login), then updates token + user state.
- Extracted isImpersonating(profile) pure helper to frontend/src/lib/impersonation.ts — centralizes the truthiness check and handles undefined profile (TanStack Query loading) + backward-compat responses missing the field.
- 4 vitest unit tests (TDD — RED before GREEN) cover object/null/undefined/missing-field branches. Regression guard: full suite went from 73 to 77 tests, all passing.

## Task Commits

Each task was committed atomically on the parallel-worktree branch (all with --no-verify to avoid pre-commit hook contention with the Plan 04 worktree; the orchestrator validates hooks once after merge):

1. **Task 1: Install shadcn Command + Popover primitives** — `c23c2b4` (feat)
2. **Task 2: Theme tokens + types/admin.ts + UserProfile.impersonation + pure helper (TDD)** — `58c317d` (feat)
3. **Task 3: useAuth.impersonate(userId) method** — `83c6558` (feat)

## Files Created/Modified

### Created

- `frontend/src/components/ui/command.tsx` — shadcn Command primitive wrapping cmdk (CommandInput, CommandList, CommandItem, CommandEmpty, CommandGroup, CommandSeparator, CommandShortcut, CommandDialog).
- `frontend/src/components/ui/popover.tsx` — shadcn Popover primitive wrapping radix-ui Popover (Popover, PopoverTrigger, PopoverContent, PopoverAnchor, PopoverHeader, PopoverTitle, PopoverDescription).
- `frontend/src/components/ui/input-group.tsx` — transitive shadcn dep, used by CommandInput to render the search icon slot.
- `frontend/src/components/ui/textarea.tsx` — transitive shadcn dep of input-group.
- `frontend/src/types/admin.ts` — ImpersonationContext, ImpersonateResponse (with target_id), UserSearchResult types.
- `frontend/src/lib/impersonation.ts` — isImpersonating(profile) helper.
- `frontend/src/lib/impersonation.test.ts` — 4 vitest unit tests (TDD).

### Modified

- `frontend/src/hooks/useAuth.ts` — added ImpersonateResponse import; extended AuthState interface with `impersonate: (userId: number) => Promise<void>`; added impersonate useCallback implementation; wired impersonate into context value.
- `frontend/src/types/users.ts` — imported ImpersonationContext from '@/types/admin'; added `impersonation: ImpersonationContext | null` field to UserProfile.
- `frontend/src/lib/theme.ts` — appended IMPERSONATION_PILL_BG/FG/BORDER oklch tokens.
- `frontend/package.json` + `frontend/package-lock.json` — cmdk ^1.1.1 added.

## Decisions Made

- **Piped 'n' to shadcn CLI overwrite prompts** rather than using --overwrite. The project's button.tsx defines a brand-outline variant that is load-bearing for the "secondary button" pattern (CLAUDE.md: `variant="brand-outline"` is the secondary action). Overwriting would have silently regressed every Save/Suggest/Reset Filters button. Input.tsx and dialog.tsx were also preserved for the same reason.
- **Accepted transitive deps input-group.tsx + textarea.tsx.** CommandInput imports InputGroup for its search-icon slot, and input-group depends on textarea. Not adding them would break command.tsx compilation. Flagged in key-files so the verifier is not surprised.
- **Test pattern for "missing field" case:** the obvious destructuring `const { impersonation: _impersonation, ...partial }` triggers @typescript-eslint/no-unused-vars because the project's ESLint config does not exempt underscore-prefixed vars. Switched to Record spread + delete with a dual cast (`as unknown as UserProfile`) to achieve the same "backward-compat shape without the new field" simulation, without a lint error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ESLint no-unused-vars error on the 4th test case**
- **Found during:** Task 2, Step G (regression gates)
- **Issue:** The plan's sample test code used `const { impersonation: _impersonation, ...partial } = base;` to simulate a profile without the impersonation field. Project ESLint flags `_impersonation` as unused.
- **Fix:** Switched to `const partial: Record<string, unknown> = { ...base }; delete partial.impersonation;` with a dual cast when passing to `isImpersonating`.
- **Files modified:** `frontend/src/lib/impersonation.test.ts`
- **Commit:** Included in 58c317d (no separate commit — fix applied before the Task 2 commit)

**2. [Rule 3 - Blocking] shadcn CLI prompted to overwrite existing files**
- **Found during:** Task 1
- **Issue:** The shadcn CLI prompts interactively to overwrite button.tsx, input.tsx, dialog.tsx when adding command. The plan assumed a non-interactive add.
- **Fix:** Piped `yes n` to answer 'no' to every overwrite prompt, preserving project-specific variants (especially brand-outline on button.tsx). popover.tsx was new so it was created cleanly.
- **Files modified:** None (this is a CLI invocation change)
- **Commit:** Included in c23c2b4

### No architectural deviations

## Known Stubs

None — this plan intentionally ships a foundation. All new exports (ImpersonateResponse, UserSearchResult, IMPERSONATION_PILL_BG/FG/BORDER, useAuth.impersonate, isImpersonating) are consumed by Plans 04 and 05. Knip currently flags command.tsx, popover.tsx, input-group.tsx, textarea.tsx, and cmdk as unused — this is expected and documented in the plan (Task 1). Plan 04 will import Command + Popover from ImpersonationSelector; Plan 05 will import the theme tokens and isImpersonating helper.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced beyond what the plan's threat model already covered. The useAuth.impersonate method calls the endpoint from Plan 01 whose threat register was fully captured there.

## Issues Encountered

- Shadcn CLI interactivity (resolved via piped `yes n`). Not a bug in the CLI — the project just has some pre-existing shadcn components and the CLI correctly asks before overwriting.
- ESLint's no-unused-vars rule on underscore-prefixed destructured vars (resolved by changing the test pattern). Not project-specific unusual — tseslint's default is to flag all unused names regardless of prefix.

## User Setup Required

None — no external service configuration, no manual browser steps. Plan 05 will need a superuser account for manual QA of the pill rendering, but that's out of scope here.

## Next Phase Readiness

Plan 04 (Admin page + ImpersonationSelector) can now:
- Import `Command`, `CommandInput`, `CommandList`, `CommandItem`, `CommandEmpty` from `@/components/ui/command`.
- Import `Popover`, `PopoverTrigger`, `PopoverContent` from `@/components/ui/popover`.
- Import `UserSearchResult`, `ImpersonateResponse` from `@/types/admin`.
- Call `useAuth().impersonate(userId)` to trigger the token swap.
- Use `isImpersonating(profile)` to gate conditional UI.

Plan 05 (header pill) can import `IMPERSONATION_PILL_BG/FG/BORDER` from `@/lib/theme` and `isImpersonating` from `@/lib/impersonation` directly.

No blockers. Once Plan 04 lands, the knip "unused" warnings resolve automatically.

## Self-Check: PASSED

Verified files exist:
- frontend/src/components/ui/command.tsx — FOUND
- frontend/src/components/ui/popover.tsx — FOUND
- frontend/src/components/ui/input-group.tsx — FOUND
- frontend/src/components/ui/textarea.tsx — FOUND
- frontend/src/components/ui/info-popover.tsx — PRESERVED (not deleted)
- frontend/src/types/admin.ts — FOUND
- frontend/src/lib/impersonation.ts — FOUND
- frontend/src/lib/impersonation.test.ts — FOUND
- frontend/src/hooks/useAuth.ts — FOUND (modified)
- frontend/src/types/users.ts — FOUND (modified)
- frontend/src/lib/theme.ts — FOUND (modified)

Verified commits exist (via `git log --oneline -5`):
- c23c2b4 — FOUND (feat(62-03): install shadcn Command + Popover primitives)
- 58c317d — FOUND (feat(62-03): add impersonation theme tokens, admin types, UserProfile field, isImpersonating helper)
- 83c6558 — FOUND (feat(62-03): add useAuth.impersonate(userId) method)

Verified gates:
- `cd frontend && npm test -- --run impersonation` — 4 passed
- `cd frontend && npm test` — 77 passed (no regressions from 73)
- `cd frontend && npx tsc -b --noEmit` — TSC_EXIT=0
- `cd frontend && npm run lint` — clean (no errors)

Verified acceptance grep checks:
- command.tsx + popover.tsx: FOUND
- CommandInput in command.tsx: PRESENT
- PopoverContent in popover.tsx: PRESENT
- cmdk in package.json: PRESENT
- IMPERSONATION_PILL_BG/FG/BORDER in theme.ts: PRESENT (all three)
- ImpersonationContext, UserSearchResult, ImpersonateResponse exported from types/admin.ts: PRESENT
- `impersonation: ImpersonationContext | null` in types/users.ts: PRESENT
- `export function isImpersonating` in lib/impersonation.ts: PRESENT
- `impersonate: (userId: number) => Promise<void>` method sig in useAuth.ts: PRESENT
- `const impersonate = useCallback` in useAuth.ts: PRESENT
- `/admin/impersonate/` URL in useAuth.ts: PRESENT
- `import type { ImpersonateResponse }` in useAuth.ts: PRESENT
- Token-swap ordering (localStorage.setItem BEFORE queryClient.clear BEFORE setToken): PRESERVED

---
*Phase: 62-admin-user-impersonation*
*Plan: 03*
*Completed: 2026-04-17*
