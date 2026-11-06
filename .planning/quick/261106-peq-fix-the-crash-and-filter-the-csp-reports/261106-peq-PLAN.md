---
quick_id: 261106-peq
mode: quick
type: execute
autonomous: true
files_modified:
  - frontend/src/lib/domMutationGuard.ts
  - frontend/src/lib/__tests__/domMutationGuard.test.tsx
  - frontend/src/main.tsx
  - deploy/Caddyfile
  - CHANGELOG.md
---

# Quick 261106-peq: Fix the Translate crash and filter the CSP reports

Planned and run inline by the orchestrator (small task, no subagents).

## Evidence

- FLAWCHESS-BV: unhandled `NotFoundError: The object can not be found here.` from React's
  `insertBefore`, caught by the ErrorBoundary. Same iPhone (Chrome iOS 18.7.8, locale `ru`, Podgorica)
  and same minute as FLAWCHESS-BS, a CSP report for `translate.google.com/gen204?...tl=ru`.
  Google Translate replacing text nodes under React is a strong inference, not proven.
- FLAWCHESS-BR/BS/BT: CSP reports for `fonts.gstatic.com`, `translate.google.com`, `www.gstatic.com`.
  The policy is report-only, so nothing is blocked. Browsers post these directly to Sentry's security
  endpoint, so the SDK's `ignoreErrors`/`beforeSend` cannot filter them.

## Task 1: DOM mutation guard

Files: `frontend/src/lib/domMutationGuard.ts`, its test, `frontend/src/main.tsx`.

`installDomMutationGuard()` wraps `Node.prototype.insertBefore` and `removeChild`, called before
`createRoot`. Only mismatched calls change behaviour:

- `insertBefore`, reference not a child: insert before the child of `this` that contains the
  reference (keeps order when wrapped), else append. The node is never dropped.
- `removeChild`, child not a direct child: remove it from its real parent when that parent is inside
  `this`, else no-op. Returns the child.
- Each mismatch leaves a Sentry breadcrumb, so a later error still shows the guard fired.

Verify: a React integration test reproduces both crashes by swapping a text node for `<font>`. An
unguarded control must throw, the guarded run must not. Mutation check: drop the install call and
confirm the guarded tests fail.

Commands: `npm test -- --run src/lib/__tests__/domMutationGuard.test.tsx`, `npm run lint`,
`npm run build`, `npm run knip` (from `frontend/`).

## Task 2: CSP report filter

Sentry project setting: Project Settings > Security Headers > CSP > Additional ignored sources, adding
`translate.google.com`, `fonts.gstatic.com`, `www.gstatic.com`. Record it in the comment above the CSP
header in `deploy/Caddyfile`, since this setting lives outside the repo.

Verify: read the saved setting back in the Sentry UI.

## Task 3: Changelog

Add a user-facing bullet under `## [Unreleased]`.
