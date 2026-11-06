---
quick_id: 261106-peq
status: complete
commit: f6b9c5833
---

# Quick 261106-peq: Fix the Translate crash and filter the CSP reports

- `installDomMutationGuard` (frontend/src/lib/domMutationGuard.ts), called from main.tsx before
  `createRoot`, wraps `Node.prototype.insertBefore` and `removeChild`. A mismatched insert goes before
  the direct child holding the reference, else appends; a mismatched remove takes the node from its real
  parent when that parent is inside `this`, else no-ops. Each mismatch leaves a Sentry breadcrumb.
- Sentry setting (outside the repo): Security Headers > CSP > Additional ignored sources =
  `translate.google.com`, `fonts.gstatic.com`, `www.gstatic.com`. Read back after a page reload; "Use
  default ignored sources" still on. Recorded in the deploy/Caddyfile comment.
- Tests: 9 in `frontend/src/lib/__tests__/domMutationGuard.test.tsx`, including a React repro. Unguarded
  control runs throw on both insert and remove, guarded runs don't.
- Mutation check: a no-op install fails 6 of 9 tests (the other 3 are the 2 controls and the
  normal-calls test), restored = 9/9.
- Real browser: headless Chrome on the dev app (main.tsx wiring included). A nested insert gave
  `B,FONT`, a detached insert `B,FONT,I`, and a detached remove returned the node, with no throw.
- Gate: eslint, build (tsc -b), knip green. Only the new test file was run, not the full vitest suite;
  the full pre-merge gate was not run, per the small-direct-main-commit rule.

## Not verified

- Real Google Translate was not run, so the cause stays a strong inference from FLAWCHESS-BS/BV.
- Not deployed. The guard reaches users and FLAWCHESS-BV can only be judged after the next release.

## Known limit

- Text that Translate has replaced can stay on screen stale: React updates or removes its detached
  original node, not the `<font>` copy. The app no longer crashes, but a translated label can lag.
- The guard also swallows these mismatches for a real React bug, leaving only the breadcrumb.
- `ignoreErrors` in instrument.ts still lists the Chrome wording. Left as is.
