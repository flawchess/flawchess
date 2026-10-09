---
phase: 229-umami-identify-feature-events
plan: 01
subsystem: analytics
tags: [umami, identity, jwt, privacy, docker-compose, runbook, react]

requires: []
provides:
  - "distinctIdFromToken / identifyUser / identifyFromStoredToken in lib/analytics.ts (string-form Umami identify, deduped, memory-only)"
  - "Boot identify in main.tsx and ProtectedLayout identify with the guest|registered tag"
  - "useAuth logout hard-navigation invariant test (D-07)"
  - "Privacy disclosure of account-linked analytics"
  - "Umami image pinned to 3.4.0 with pull_policy missing; runbook version-pin and account-deletion sections"
affects: [229-02, 229-03, 229-04, 229-05, 229-06, 229-07, 229-08]

actuals:
  tokens: 6600
  tasks: 3
  commits: 3
plan_head_before: 8c6555593ae365d5ef203ae2b8a654ba583f10c7
plan_head_after: 20c0d8b31d7f6f4c212705ed0b38c3551df1de4f

tech-stack:
  added: []
  patterns:
    - "Tracker-absent attempts bail before recording the dedupe key so a late tracker still receives the identify"
    - "JWT payload decoded locally (base64url + padding), no jwt-decode dependency"

key-files:
  created:
    - frontend/src/hooks/__tests__/useAuth.test.tsx
  modified:
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/__tests__/analytics.test.ts
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/hooks/useAuth.ts
    - frontend/src/pages/Privacy.tsx
    - docker-compose.yml
    - docs/production-runbook.md

key-decisions:
  - "Raw users.id from the JWT sub is the Umami distinct_id (no backend change, no browser storage)"
  - "logoutForPromotion keeps caller-side navigation (no fold into the hook)"
  - "Deletion SQL splits sessions into exclusive (full delete) and shared (only this distinct_id's session_link/session_data rows, session.distinct_id nulled)"

requirements-completed: [D-07, D-08, D-09, D-10, D-11, D-16, D-17, D-18]

coverage:
  - id: D1
    description: "Stored auth token's users.id reaches window.umami.identify at boot and from ProtectedLayout (string form, deduped, never for impersonation tokens)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Logout's hard navigation is pinned as the analytics identity reset"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useAuth.test.tsx#hard-navigates to /"
        status: pass
    human_judgment: false
  - id: D3
    description: "Privacy copy, Umami 3.4.0 pin and runbook steps are accurate and usable for the release"
    verification: []
    human_judgment: true
    rationale: "Copy and operator runbook SQL need owner review; the first deploy must verify the first pageview carries the id (Plan 08 human-check)"

duration: 8min
completed: 2026-10-03
status: complete
---

# Phase 229 Plan 01: Umami identity spine Summary

**Every authenticated session (guests included) is identified in Umami with users.id taken from the JWT sub, at boot before the first pageview and again in ProtectedLayout with the account tag, with impersonation never identifying and logout's reload pinned as the reset.**

## Performance

- **Duration:** 8 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 9 (1 created, 8 modified)

## Accomplishments

- `lib/analytics.ts`: `distinctIdFromToken` (numeric JWT sub only, null for malformed or `is_impersonation` tokens), `identifyUser` (string-form identify, deduped on id|account per page load, tracker-absent attempts do not poison the dedupe key), `identifyFromStoredToken` (reads only `auth_token`, survives a throwing localStorage). `identifyAccountType` removed; `window.umami.identify` retyped to `(distinctId, data?)`.
- `main.tsx` calls `identifyFromStoredToken()` directly after `installUmamiBeforeSend()`; `index.html` loads the deferred tracker before the module bundle, so `window.umami` exists at that point and the pageview (which waits for readyState complete) follows.
- `App.tsx` ProtectedLayout identifies with `(distinctIdFromToken(token), umamiAccountType)` when both are non-null; the existing `profile.impersonation` guard is the second impersonation guard.
- `useAuth.ts`: logout comment and `logoutForPromotion` JSDoc document the reload as the analytics identity reset; new `useAuth.test.tsx` fails if the `window.location.href = '/'` assignment is removed.
- Privacy page: the "no personal data is collected" claim is replaced by the account-ID-linked disclosure.
- `docker-compose.yml`: Umami pinned to `3.4.0` with `pull_policy: missing`; runbook gains "Umami analytics" with version-pin verify steps and the per-account deletion SQL.

## Task Commits

1. Task 1 (tracer): `ee7fe76fc` feat(229-01): identify Umami sessions with users.id from the JWT sub
2. Task 2: `8b0090c5b` test(229-01): pin logout hard navigation as the analytics identity reset
3. Task 3: `20c0d8b31` feat(229-01): disclose account-linked analytics, pin Umami 3.4.0, runbook steps

## Mutation checks (guards proven by reverting)

- Removing the `is_impersonation` check in `distinctIdFromToken`: 2 red tests (`returns null for an impersonation token`, `skips an impersonation token`); restored, 28/28 green.
- Moving the `window.umami` check below the `lastIdentifyKey` assignment: 1 red test (`does not throw without a tracker and still identifies once the tracker appears`); restored.
- Deleting `window.location.href = '/'` in logout: 1 red test (`hard-navigates to / (the analytics identity reset)`); restored, 3/3 green.

## Deletion SQL schema check

`gh api repos/umami-software/umami/contents/prisma/schema.prisma?ref=v3.4.0` confirmed every table and column used: `event_data(website_event_id, website_id)`, `revenue(session_id, event_id, website_id)`, `session_replay`, `heatmap_event`, `website_event(event_id, session_id)`, `session_data(session_id, distinct_id)`, `session_link(website_id, distinct_id, session_id)`, `session(session_id, distinct_id, website_id)`. No name differed from the plan. Note beyond the plan: `session` itself also has a `distinct_id` column and `session_data` has one, so the SQL also covers `session.distinct_id` (target-set union, nulled for shared sessions) and `session_data.distinct_id`.

## Verification

- `npx vitest run` on analytics, useAuth, SignupAskActions, App tests: 104 passed.
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean (no dead export; knip also green).
- `git diff --stat -- app/ tests/`: empty (no backend change).
- Not executed: the deletion SQL (never run against any database; production is out of scope) and the live first-pageview check (post-deploy, Plan 08).

## Deviations from Plan

None - plan executed exactly as written. (Extra: the deletion SQL additionally nulls `session.distinct_id` for shared sessions and deletes `session_data` by `distinct_id`, a refinement within the plan's shared-session rule after reading the v3.4.0 schema.)

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, or schema change; the identify payload carries only the numeric sub and the account tag.

## Self-Check: PASSED

- Created `frontend/src/hooks/__tests__/useAuth.test.tsx`: FOUND
- Commits `ee7fe76fc`, `8b0090c5b`, `20c0d8b31`: FOUND
- Acceptance criteria for all three tasks re-run and passing.
