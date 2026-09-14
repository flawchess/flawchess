---
phase: 222-train-bot-narrated-onboarding-and-verdicts
reviewed: 2026-09-13T00:00:00Z
depth: standard
files_reviewed: 43
files_reviewed_list:
  - alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py
  - app/models/train_settings.py
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - CHANGELOG.md
  - docs/activity-dashboard.md
  - frontend/src/api/client.ts
  - frontend/src/components/train/__tests__/TrainBotBubble.test.tsx
  - frontend/src/components/train/__tests__/trainBubbleState.test.ts
  - frontend/src/components/train/__tests__/TrainReveal.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/TrainBotBubble.tsx
  - frontend/src/components/train/TrainBotStepper.tsx
  - frontend/src/components/train/trainBubbleState.ts
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/hooks/__tests__/useMediaQuery.test.ts
  - frontend/src/hooks/__tests__/useTrainSession.test.ts
  - frontend/src/hooks/useMediaQuery.ts
  - frontend/src/hooks/useTrainOnboarding.ts
  - frontend/src/hooks/useTrainSession.ts
  - frontend/src/index.css
  - frontend/src/lib/personas/personaRegistry.ts
  - frontend/src/lib/personas/__tests__/personaRegistry.test.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainGuessLabels.ts
  - frontend/src/pages/activity/ActivityPage.tsx
  - frontend/src/pages/activity/render.js
  - frontend/src/pages/Home.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/types/activity.ts
  - frontend/src/types/train.ts
  - scripts/reset_train_state.py
  - tests/repositories/test_train_repository.py
  - tests/routers/test_train.py
  - tests/scripts/test_reset_train_state.py
  - tests/test_admin_activity_stats.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 222: Code Review Report

**Reviewed:** 2026-09-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 43
**Status:** issues_found

## Summary

Phase 222 adds bot-narrated Train onboarding (first-session intro stepper, first-reveal
walkthrough, score-screen SR explanation) plus three new `train_settings` "seen" watermark
columns, one new router endpoint (`POST /train/onboarding/{step}`), and a new activity-dashboard
funnel card. Verification performed beyond reading: `uv run ty check` (clean), `uv run ruff
check` (clean), `scripts/check_function_size.py` (no breaches), the full backend test subset
(241 passed), `npx eslint`/`tsc -b`/`npm run knip` (all clean), and the full frontend test subset
for touched files (332 passed). The backend column additions, the first-write-wins onboarding
stamp, and the `_resume_session` solved-results widening are all well-guarded and covered by
dedicated tests (including the orphaned-`drill_items` degrade case).

The one BLOCKER is a real, unhandled failure mode in `TrainSolveScreen`: a persistent
`GET /train/settings` error (not just "still loading") permanently blocks the guess UI on every
session's first puzzle, with no error indicator — the exact anti-pattern `frontend/CLAUDE.md`
calls out ("Always handle `isError`... never let errors fall through"). The two WARNINGs are
duplicated/discarded copy-generation logic and a metric-vs-documentation precision gap in the new
admin funnel query; both are drift risks rather than currently-observable bugs.

## Critical Issues

### CR-01: Persistent `/train/settings` fetch failure permanently blocks the first puzzle's guess UI

> **Resolved by the orchestrator in `bdc4a0fb4`** (same session): `resolveIntroState` now takes the query's `isError` and a failed fetch degrades to the regular prompt; regression test added and mutation-checked. WR-01/WR-02/IN-01/IN-02 remain open (advisory).

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:254-263, 682, 1449-1450`
**Issue:**
`resolveIntroState` (and its caller) only branches on `settings === undefined`, treating "still
loading" and "will never arrive because the request failed" identically:

```ts
function resolveIntroState(
  settings: TrainSettingsResponse | undefined,
  isFirstPuzzle: boolean,
  introStep: 0 | 1 | 2,
): { activeIntroStep: 0 | 1 | 2 | null; suppressPrompt: boolean } {
  if (settings === undefined) return { activeIntroStep: null, suppressPrompt: isFirstPuzzle };
  ...
}
```

`const { data: settings } = useTrainSettings();` (line 682) discards `isError`/`isPending`
entirely. TanStack Query's default `retry: 1` (`frontend/src/lib/queryClient.ts`) means a
genuinely failing request (backend 500, transient network partition during the initial page
load) eventually settles into `status: 'error'` with `data` permanently `undefined` — react-query
does not keep retrying forever. Because `isFirstPuzzle = currentPosition1Based === 1` is true for
the first puzzle of *every* session (not just a brand-new account), `suppressPrompt` stays `true`
forever whenever this happens, and `renderTrainBotBubbleBody`'s `prompt` branch returns `null`:

```ts
if (bubbleState.kind === 'prompt') {
  if (deps.suppressPrompt) return null;
  ...
}
```

The result: the bubble slot renders nothing (no prompt, no guess buttons, no error message), the
board stays locked (`handlePieceDrop` requires `guess !== null`), and the user has no way to
proceed past the very first puzzle of the session — with zero visual indication anything is
wrong. This is exactly the pattern `frontend/CLAUDE.md` prohibits: "Always handle `isError`... —
every `useQuery` result rendered with a loading/data/empty chain must include an `isError`
branch... Never let errors fall through to empty-state messages." Here it is worse than a
misleading empty-state message — nothing renders at all in the slot that should carry the primary
interactive control.

**Fix:** Thread `isError` (or `isPending`) from `useTrainSettings()` into `resolveIntroState`/the
bubble-suppression path, and fail open rather than closed — e.g. treat a settings fetch error the
same as "already seen" (skip the intro, show the regular prompt) so the guess UI is never
withheld indefinitely:

```ts
const { data: settings, isError: settingsError } = useTrainSettings();
...
function resolveIntroState(
  settings: TrainSettingsResponse | undefined,
  settingsError: boolean,
  isFirstPuzzle: boolean,
  introStep: 0 | 1 | 2,
): { activeIntroStep: 0 | 1 | 2 | null; suppressPrompt: boolean } {
  if (settingsError) return { activeIntroStep: null, suppressPrompt: false };
  if (settings === undefined) return { activeIntroStep: null, suppressPrompt: isFirstPuzzle };
  ...
}
```

## Warnings

### WR-01: Verdict clause text is computed twice by two independently-maintained implementations

**File:** `frontend/src/lib/trainBotCopy.ts:170-177` (`verdictClause`) and
`frontend/src/components/train/TrainSolveScreen.tsx:317-332` (`verdictClauseParts`)
**Issue:** `trainBotCopy.ts`'s `verdictClause(correctGuess, moveQuality)` produces the exact
"Right call [+1], right move [+2]." style sentence and is exercised by
`frontend/src/lib/__tests__/trainBotCopy.test.ts` (asserting `copy.clause`), but the actual
rendered verdict bubble in `TrainSolveScreen.tsx` never reads `opening.clause` — it calls a
second, separately-maintained function, `verdictClauseParts`, that re-derives the same
guess/move label + point mapping from scratch to build JSX pills instead of plain text. The two
implementations currently agree, but nothing enforces that: a future copy edit to one (e.g.
changing "wrong move" wording, or a new `moveQuality` branch) can drift from the other silently,
because the tested `clause` string is dead at runtime — no test exercises `verdictClauseParts`
against `verdictClause`'s output for equivalence.
**Fix:** Either derive `verdictClauseParts`'s labels from `verdictClause`'s own branch logic (e.g.
export a shared `{ guessLabel, moveLabel }` resolver from `trainBotCopy.ts` and have both
`verdictClause` and `verdictClauseParts` call it), or add a cross-check test asserting the two
outputs stay textually equivalent (modulo the `[+N]` bracket vs. pill formatting) so an edit to
one that isn't mirrored in the other fails CI instead of shipping a silent copy mismatch.

### WR-02: `fetch_train_funnel`'s "returners"/"finishers" doesn't verify the *first* session was the one completed

**File:** `app/services/activity_queries.py:337-343` (the `flags` CTE), `docs/activity-dashboard.md:117-121`
**Issue:** The dashboard doc states the return-share metric is "of everyone in the cohort who
*finished a first session*, how many came back and finished a second" — but `completed_count`
counts the user's **entire** completed-session history, not specifically whether their actual
first (cohort-defining) session reached `status='completed'`:

```sql
(SELECT count(*) FROM drill_sessions d
  WHERE d.user_id = c.user_id AND d.status = 'completed') AS completed_count
```

A user whose literal first session was abandoned/expired (never completed) but who later
completed two subsequent sessions is counted as both a `finisher` (`completed_count >= 1`) and a
`returner` (`completed_count >= 2`) under this query, even though their first session in the
funnel's own cohort definition never "finished." This is an intentional simplification per the
function's own docstring ("the same definition `fetch_train` already uses"), so it is not a
functional bug, but the public-facing doc's "who finished a first session" phrasing overstates
what the query actually verifies, which could mislead a reader of the dashboard into treating the
"finishers" percentage as more precise than it is.
**Fix:** Either tighten the query to require the cohort's own `first_session.session_id` be the
one flagged as `completed`, or soften the doc wording (`docs/activity-dashboard.md`) to say
"users who have completed at least one session" rather than "who finished a first session" so the
prose matches the SQL precisely.

## Info

### IN-01: `docs/activity-dashboard.md`'s "Query cost" note is stale after this phase's addition

**File:** `docs/activity-dashboard.md:129`
**Issue:** `build_payload()` runs ~16 sequential aggregate queries over the full tracked window`
was not updated to reflect the two additional sequential queries `fetch_train_funnel` now issues
(the windowed + all-time re-run of the same SQL), understating the actual per-refresh query count
for anyone tuning this page's latency later.
**Fix:** Bump the count (or reword to "~18") in the same sentence.

### IN-02: `useTrainOnboarding`'s `stamp` has no `isPending` guard against rapid double-invocation

**File:** `frontend/src/hooks/useTrainOnboarding.ts:29-38`, called from
`frontend/src/components/train/TrainSolveScreen.tsx:1505-1507` (`handleWalkthroughDone`)
**Issue:** `handleWalkthroughDone` calls `stamp('reveal_walkthrough')` with no check against
`isPending`, so a user double-clicking "Got it" before the first mutation's response updates the
shared settings cache can fire the POST twice. The backend's first-write-wins guarded `UPDATE`
(`stamp_onboarding_step`) makes this harmless server-side, but it's an avoidable extra network
round-trip with no functional purpose.
**Fix:** Low priority given the server-side idempotency; if worth fixing, gate the click handler
on `!isPending` the way most other Train mutation call sites already do.

---

_Reviewed: 2026-09-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
