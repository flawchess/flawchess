---
phase: 232-frontend-major-dependency-upgrades
fixed_at: 2026-10-04T14:40:00Z
review_path: .planning/phases/232-frontend-major-dependency-upgrades/232-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 232: Code Review Fix Report

**Fixed at:** 2026-10-04
**Source review:** .planning/phases/232-frontend-major-dependency-upgrades/232-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

Info findings (IN-01, IN-02, IN-03) are out of scope for `fix_scope: critical_warning` and were not touched.

## Fixed Issues

### WR-01: `dataCollection.urlQueryParams` does not scrub `event.request.url`, so the password-reset JWT still reaches Sentry

**Files modified:** `frontend/src/instrument.ts`, `frontend/src/__tests__/instrument.beforeSend.test.ts`
**Commit:** 2361acf86
**Applied fix:** `sentryBeforeSend` now replaces everything after the first `?` in `event.request.url` with a named `FILTERED_QUERY_PLACEHOLDER` (`[Filtered]`), via a new `scrubUrlQuery()` helper. It runs for every kept event, after the axios block. A comment at the fix site explains the leak: HttpContext copies `location.href` into the event, and that URL is not gated by `dataCollection`, so `/reset-password?token=<JWT>` leaked. The `urlQueryParams` comment now says it only covers fetch breadcrumbs and spans. Three tests were added: a non-axios event, a kept axios event, and a URL with no query string.
**Mutation proof:** With the scrub call disabled, the 2 scrub tests failed (29 passed). With the call restored, all 31 pass.

### WR-02: `typescript` alias range was loosened from `~6.0.3` to `^6.0.2`, but typescript-eslint caps at `<6.1.0`

**Files modified:** `frontend/package.json`, `frontend/package-lock.json`
**Commit:** cd7f70dfe
**Applied fix:** The alias is now `npm:@typescript/typescript6@~6.0.2`, matching typescript-eslint's `<6.1.0` peer cap. `npm install` updated the lockfile's root devDependencies entry. The resolved version is unchanged and the diff is one line in each file.

## Verification

Run from `frontend/` in the main checkout (not an isolated worktree), after both commits:

- `npm run lint`: exit 0
- `npm run build` (`tsc -b` + vite + PWA): exit 0
- `npm test -- --run`: 303 files, 4987 tests, all passed
- `npm run knip`: exit 0 (only the existing `.css` configuration hint)

No isolated worktree was created. The caller asked for edits on the current branch plus the frontend gates, and a fresh worktree has no `node_modules`.

---

_Fixed: 2026-10-04_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
