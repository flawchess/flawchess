---
phase: 62-admin-user-impersonation
plan: 05
subsystem: frontend
tags: [frontend, header, mobile-parity, impersonation, theme, aria]

requires:
  - phase: 62-admin-user-impersonation
    plan: 03
    provides: IMPERSONATION_PILL_BG/FG/BORDER theme tokens, isImpersonating helper, ImpersonationContext type, UserProfile.impersonation field
  - phase: 62-admin-user-impersonation
    plan: 04
    provides: App.tsx Admin route + SuperuserRoute guard + conditional nav established

provides:
  - frontend/src/components/admin/ImpersonationPill.tsx — pill component with IMPERSONATION_PILL_* theme tokens + useAuth().logout
  - App.tsx NavHeader renders ImpersonationPill when profile.impersonation is non-null; Logout button hidden
  - App.tsx MobileHeader renders ImpersonationPill (narrower cap) when impersonating; mobile parity
  - App.tsx MobileMoreDrawer hides Logout + divider when impersonating; single logout via pill ×

affects: []

tech-stack:
  added: []
  patterns:
    - "Pill uses inline style from theme.ts oklch tokens (not Tailwind color classes) — enforces CLAUDE.md theme constant rule"
    - "emailMaxWidthClass prop pattern for responsive truncation — desktop 12rem, mobile 8rem via caller-side prop"
    - "isImpersonating(profile) guard on every logout control for single-logout UX (D-20)"

key-files:
  created:
    - frontend/src/components/admin/ImpersonationPill.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "Logout button hidden (not just visually demoted) during impersonation — pill × is the sole logout control per D-20 and RESEARCH.md recommendation"
  - "Divider above drawer Logout wrapped inside same !isImpersonating conditional — prevents a trailing empty divider in the drawer when impersonating"
  - "MobileHeader now calls useUserProfile() to access profile.impersonation — small hook cost, required for mobile parity (CLAUDE.md mobile rule)"

requirements-completed: [D-10, D-11, D-20, D-21, D-22]

duration: 8min
completed: 2026-04-17
---

# Phase 62 Plan 05: Impersonation Header Pill Summary

**Impersonation pill rendering in both desktop and mobile headers with D-20 single-logout UX — orange oklch pill displays "Impersonating {email} ×", × calls useAuth().logout, standalone Logout buttons hidden on desktop and mobile drawer during active impersonation sessions.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-17T18:01Z
- **Completed:** 2026-04-17T18:09Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Created `ImpersonationPill` component using `IMPERSONATION_PILL_BG/FG/BORDER` oklch tokens from `theme.ts` — no hardcoded Tailwind color classes (D-21, CLAUDE.md).
- `role="status"` + `aria-live="polite"` for screen reader announcement of impersonation state.
- `aria-label="End impersonation session"` on icon-only × button (CLAUDE.md Browser Automation Rule 3).
- `data-testid="impersonation-pill"` on container, `data-testid="btn-impersonation-pill-logout"` on × button.
- `emailMaxWidthClass` prop defaults to `max-w-[12rem]` (desktop); callers pass `max-w-[8rem]` for mobile.
- `type="button"` on × prevents accidental form submission.
- NavHeader right-side cluster: pill renders conditionally on `profile?.impersonation`; Logout button wrapped in `!isImpersonating(profile)` so it disappears during impersonation (D-20).
- MobileHeader extended with `useUserProfile()` hook call; pill renders in a flex wrapper with `min-w-0` so `truncate` fires correctly inside the flex container (T-62-16 mitigation).
- MobileMoreDrawer: Logout button AND the `<div className="my-2 border-t border-border" />` divider both wrapped inside `!isImpersonating(profile)` conditional — no trailing empty divider when impersonating (mobile parity, D-20).

## Task Commits

Each task committed atomically:

1. **Task 1: Build ImpersonationPill component** — `819f3e4`
2. **Task 2: Render pill in NavHeader + MobileHeader; hide Logout when impersonating** — `ecbd423`

## Files Created/Modified

### Created

- `frontend/src/components/admin/ImpersonationPill.tsx` — Pill component; imports IMPERSONATION_PILL_* from `@/lib/theme`, ImpersonationContext from `@/types/admin`, useAuth from `@/hooks/useAuth`; renders "Impersonating {email} ×" with proper ARIA + data-testid.

### Modified

- `frontend/src/App.tsx` — Added `ImpersonationPill` and `isImpersonating` imports; updated NavHeader right-side cluster; extended MobileHeader with `useUserProfile` + pill; wrapped drawer Logout + divider in `!isImpersonating` conditional.

## Decisions Made

- **Hide desktop Logout button during impersonation** (not keep both). Keeping both would give the admin two ways to end the session, which is slightly noisy UX. RESEARCH.md §"Hiding desktop Logout" recommends hiding; plan commits to it.
- **Wrap divider inside the same isImpersonating conditional as drawer Logout.** The divider is visually tied to the logout item; showing an orphan divider when the item below it is absent looks broken. Wrapping them together is cleaner and the plan explicitly calls this out.
- **MobileHeader hooks pattern.** MobileHeader previously had no data dependencies. Adding `useUserProfile()` here is a small cost (hook already cached by TanStack Query — same data, no extra request) required for mobile parity per CLAUDE.md.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — pill renders from live `profile.impersonation` data populated by Plan 02's `get_impersonation_context` dep on `/users/me/profile`. No hardcoded or mock data flows to the UI.

## Threat Flags

No new surface beyond what the plan's threat model covers.

- T-62-16 (UX robustness): Long email truncation implemented — `max-w-[8rem]` on mobile pill, `max-w-[12rem]` on desktop; `min-w-0` on MobileHeader flex wrapper so `truncate` fires correctly inside flex containers.
- T-62-17 (operational): Pill × uses `useAuth().logout` — same path used by the drawer Logout button exercised daily. Regression guard: 77/77 tests green.

## Self-Check: PASSED

Verified files exist:
- `frontend/src/components/admin/ImpersonationPill.tsx` — FOUND
- `frontend/src/App.tsx` — FOUND (modified)

Verified commits exist:
- `819f3e4` — FOUND (feat(62-05): add ImpersonationPill component with theme tokens + aria)
- `ecbd423` — FOUND (feat(62-05): render impersonation pill in headers; hide logout when impersonating)

Verified gates:
- `cd frontend && npx tsc -b --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 errors (3 pre-existing coverage/ warnings)
- `cd frontend && npm run knip` — clean
- `cd frontend && npm test -- --run` — 77/77 passed

Verified acceptance checks:
- `grep -q "export function ImpersonationPill"` — FOUND
- `grep -q "IMPERSONATION_PILL_BG"` — FOUND
- `grep -q "IMPERSONATION_PILL_FG"` — FOUND
- `grep -q "IMPERSONATION_PILL_BORDER"` — FOUND
- `grep -q 'data-testid="impersonation-pill"'` — FOUND
- `grep -q 'data-testid="btn-impersonation-pill-logout"'` — FOUND
- `grep -q 'aria-label="End impersonation session"'` — FOUND
- `grep -q "import { ImpersonationPill }" App.tsx` — FOUND
- `grep -q "import { isImpersonating }" App.tsx` — FOUND
- ImpersonationPill present in NavHeader (line 145) — FOUND
- ImpersonationPill present in MobileHeader (line 182) — FOUND
- `emailMaxWidthClass="max-w-[8rem]"` in App.tsx — FOUND
- `!isImpersonating(profile)` guards on nav-logout + drawer-logout — FOUND
- No hardcoded bg-orange classes in ImpersonationPill.tsx — CONFIRMED

---
*Phase: 62-admin-user-impersonation*
*Plan: 05*
*Completed: 2026-04-17*
