---
phase: 233-train-puzzle-timing-telemetry
reviewed: 2026-10-05T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py
  - app/models/drill_solve.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - CHANGELOG.md
  - frontend/src/api/client.ts
  - frontend/src/components/train/TrainLineStepper.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/hooks/useInstallPrompt.ts
  - frontend/src/hooks/useTrainFreePlay.ts
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - frontend/src/lib/deviceClass.ts
  - frontend/src/lib/trainRevealCache.ts
  - frontend/src/lib/trainTelemetry.ts
  - frontend/src/lib/visibleStopwatch.ts
  - frontend/src/pages/Privacy.tsx
  - frontend/src/types/train.ts
  - tests/routers/test_train.py
  - tests/schemas/test_train_telemetry_parity.py
  - tests/schemas/test_train_telemetry_schema.py
  - frontend/src/api/__tests__/client.test.ts
  - frontend/src/components/train/__tests__/TrainLineStepper.test.tsx
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/hooks/__tests__/useTrainFreePlay.test.ts
  - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
  - frontend/src/lib/__tests__/deviceClass.test.ts
  - frontend/src/lib/__tests__/trainRevealCache.test.ts
  - frontend/src/lib/__tests__/visibleStopwatch.test.ts
  - frontend/src/pages/__tests__/Privacy.test.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 233: Code Review Report

**Reviewed:** 2026-10-05
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Summary

Reviewed the phase diff (`f492f2b0a..HEAD`) across backend, frontend and tests. Mechanical gates were also run against the tree: `ruff check`, `ruff format --check`, `ty check app/ tests/`, `check_function_size.py --fail-over-depth 4`, `npm run knip` and `eslint` on the touched frontend files are all clean, and the 53 telemetry/review backend tests pass.

The areas called out for scrutiny hold up:

- **JSONB merge / NULL handling:** `_merged_telemetry` (`coalesce(telemetry, '{}'::jsonb) || patch`) is a single atomic UPDATE in both writers. `record_solve` omits the column when there is no patch, and the column type is `JSONB(none_as_null=True)`, so "no telemetry" stays SQL NULL. Both routers use `model_dump(exclude_none=True)`, so no JSON null reaches the merge. The review patch always carries `v` and `exit`, so it is never empty.
- **Owner scoping / auth:** `merge_solve_telemetry` filters on `user_id` from `current_active_user`, requires `solved_at IS NOT NULL`, and returns 404 for missing, unsolved and foreign rows (no existence oracle). Path params are bounded (`session_id` int4, `position` smallint). There is no IDOR.
- **Keepalive transport:** the Authorization header is attached, the 401 interceptor is bypassed on purpose, only 5xx is captured to Sentry, and the message is constant with variable data in `contexts` (CLAUDE.md grouping rule).
- **React effect ordering, StrictMode, listener cleanup:** the `keyRef` reset, `aliveRef` plus microtask unmount flush, `nextFlushedRef` and `hiddenFlushedRef` guards, and the reveal-cache mirror all trace correctly. The Analyze round trip, the Next flush then unmount no-op, and the hidden-then-pagehide dedupe behave as the tests claim.
- **Cap parity:** the TS constants are plain integer literals, regex-locked by the parity test.

No blockers. Two warnings (one irreversible data-quality defect, one lost-flush path) and four info items follow. Everything stored is collected go-forward only and cannot be regenerated, so the warnings are worth fixing before the deploy.

## Warnings

### WR-01: `client` classifies every iPad as "desktop" (irreversible mislabelled data)

**File:** `frontend/src/lib/deviceClass.ts:13-15`
**Issue:** `isMobileUserAgent()` tests `/Android|iPhone|iPad|iPod/i` against `navigator.userAgent`. Since iPadOS 13, Safari (and Chrome on iOS) send a desktop-class UA (`Macintosh; Intel Mac OS X ...`) by default, so the regex never matches an iPad and `telemetryClient()` returns `"desktop"`. D-09's `client` key exists to separate phone/touch use from desktop use, and this cohort (tablet users) is silently merged into desktop in every `drill_solves.telemetry` row from day one. The data cannot be re-derived later, and the Privacy copy ("whether you trained on a phone or a computer") promises a distinction the code does not make for tablets. The gate is shared with `useInstallPrompt` (D-06 says keep it verbatim there), so the fix must not change the install-prompt behavior.
**Fix:** keep `isMobileUserAgent` as-is for the install prompt and give telemetry its own check that also catches iPadOS:
```ts
function isIpadOsDesktopUa(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    /Macintosh/i.test(navigator.userAgent) &&
    navigator.maxTouchPoints > 1
  );
}

export function telemetryClient(): TelemetryClient {
  return isMobileUserAgent() || isIpadOsDesktopUa() ? 'mobile' : 'desktop';
}
```
Add a `deviceClass.test.ts` case for a Macintosh UA with `maxTouchPoints = 5`. If the owner prefers to leave tablets in `desktop`, document that on the `client` key and in the Privacy line instead.

### WR-02: Next-path review flush is a plain XHR and its "flushed" guard is set before success, so a lost Next flush is never retried and corrupts the D-07 derivation

**File:** `frontend/src/hooks/useTrainPuzzleTelemetry.ts:291-298` (transport at `frontend/src/api/client.ts:334-339`)
**Issue:** `flushReviewOnNext` sends through `trainApi.recordReview`, an axios XHR (not keepalive), and sets `nextFlushedRef.current = true` immediately after calling `mutate`, before any response. Two consequences:
1. A request that is in flight when the user closes the tab or the page is torn down right after pressing Next (most visible on the last puzzle, where Next navigates to the score screen) can be cancelled by the browser. The later `pagehide` and unmount flushes are then suppressed by `nextFlushedRef`, so nothing replaces it.
2. A transient failure (offline, 5xx) is only reported to Sentry by the global `MutationCache.onError`; no retry is attempted and the guard prevents a fallback.
In both cases the row ends up with the previous `exit = "pagehide"` flush (or no review keys at all). Per D-07, "puzzle N+1 was shown" is derived from puzzle N having `exit = next`, so a lost Next flush makes the next puzzle look never shown and skews the abandon analysis. The page-level `pagehide` machinery was built precisely to avoid lost flushes, but the most common path does not get it.
**Fix:** send the Next flush through the same keepalive transport (the `Authorization` header is already handled there) so it survives unload, and keep `exit: 'next'` in the body:
```ts
const flushReviewOnNext = useCallback((): void => {
  const review = reviewRef.current;
  if (nextFlushedRef.current || review === null || review.sessionId === null) return;
  const snapshot = takeReviewSnapshot();
  if (snapshot === undefined) return;
  postReviewKeepalive(review.sessionId, review.position, buildReviewTelemetry(snapshot, countersRef.current, 'next'));
  nextFlushedRef.current = true;
}, [takeReviewSnapshot]);
```
This also lets `useMutation`, `trainApi.recordReview` and the `ReviewFlushArgs` type be deleted. Trade-off: a 401 on that request no longer redirects to login (acceptable, the next authenticated call does) and 4xx are no longer captured (expected failures per frontend/CLAUDE.md). If the owner prefers to keep axios, at minimum set `nextFlushedRef` only in `onSuccess` so a failure can still fall through to the unmount/pagehide flush.

## Info

### IN-01: `v: Literal[1]` on both schemas is not covered by the parity test

**File:** `app/schemas/train.py:219` and `app/schemas/train.py:243` (test: `tests/schemas/test_train_telemetry_parity.py:28-34`)
**Issue:** The comment says `v` "Must equal TELEMETRY_SCHEMA_VERSION (a Literal cannot reference the constant)", and the parity test checks the constant against the TS file, but nothing checks the two `Literal[1]` annotations against the constant. Bumping `TELEMETRY_SCHEMA_VERSION` to 2 would turn the parity test green while the server keeps rejecting `v: 2`: review flushes would 422 and, worse, solve telemetry would be silently dropped by the wrap validator (see IN-02).
**Fix:** add a one-line test, e.g.
```python
def test_schema_version_literal_matches_constant() -> None:
    for model in (SolveTelemetry, ReviewTelemetry):
        assert get_args(model.model_fields["v"].annotation) == (TELEMETRY_SCHEMA_VERSION,)
```

### IN-02: Dropped solve telemetry is completely unobservable

**File:** `app/schemas/train.py:308-321`
**Issue:** `_drop_invalid_telemetry` swallows every `ValidationError` with no log, metric or Sentry breadcrumb. Combined with `extra="forbid"`, any frontend/backend key drift (a new client key reaching an older server during a rolling deploy, a schema-version bump, a cap mismatch) loses 100% of solve telemetry with no signal, and the data is irreplaceable. The "expected condition" reasoning holds for tampered clients but not for drift. The review route is not affected (it 422s and the failure is visible in Sentry via the frontend).
**Fix:** keep the drop (D-02), but emit a cheap signal that does not fragment grouping, for example `sentry_sdk.add_breadcrumb(category="train.telemetry", message="solve telemetry dropped", level="info")` or a rate-limited `logger.info`. Alternatively assert in a test that the serialized `buildSolveTelemetry` output validates against `SolveTelemetry` (contract test across the stack).

### IN-03: `_merged_telemetry` relies on callers to keep None out of the patch

**File:** `app/repositories/train_repository.py:2871-2883`
**Issue:** The docstring says "Never pass a patch containing JSON null values", but the repository does not enforce it; both routers happen to use `exclude_none=True`. A future caller passing `model_dump()` would write JSON null values into the column (`||` would then overwrite real keys with null, and `IS NULL` predicates would still not match the column). The memory note on asyncpg JSONB nulls shows this exact class of defect has already bitten the project once.
**Fix:** filter in the helper so the invariant is local: `patch = {k: v for k, v in patch.items() if v is not None}` before `literal(patch, JSONB)` (and return the column unchanged if the result is empty).

### IN-04: First-puzzle `guess_ms` includes the intro stepper with no flag on the row

**File:** `frontend/src/hooks/useTrainPuzzleTelemetry.ts:149-152`, `frontend/src/components/train/TrainSolveScreen.tsx:1594-1600`
**Issue:** The think stopwatch starts when the grading engine is ready, not when the guess prompt becomes available. On a user's first-ever puzzle the Phase 222 intro stepper (`suppressPrompt`, `introStep`) sits in front of the guess buttons, so `guess_ms` for that row measures intro reading time. Unlike the reveal walkthrough (D-13), no key marks this on the solve patch. The distortion is bounded (one row per user, derivable from `train_settings.intro_seen_at` against `solved_at`), so this is informational, but the speed-accuracy and within-user analyses from SEED-190 should exclude those rows. Note it in the analysis notes, or start the think timer from the moment the intro is dismissed.
**Fix:** document the exclusion rule in the SEED-190 analysis notes, or call a `restartThinkTimer()` from the intro-dismiss path.

---

_Reviewed: 2026-10-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
