---
phase: 122-in-app-feedback-button-seed-049
reviewed: 2026-06-15T20:30:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - app/models/feedback.py
  - app/schemas/feedback.py
  - app/repositories/feedback_repository.py
  - app/services/feedback_service.py
  - app/core/feedback_rate_limiter.py
  - app/routers/feedback.py
  - app/main.py
  - alembic/env.py
  - alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py
  - frontend/src/types/feedback.ts
  - frontend/src/api/client.ts
  - frontend/src/hooks/useFeedback.ts
  - frontend/src/hooks/useOverlayOpen.ts
  - frontend/src/hooks/useScrollDirection.ts
  - frontend/src/components/feedback/FeedbackButton.tsx
  - frontend/src/components/feedback/FeedbackModal.tsx
  - frontend/src/App.tsx
  - frontend/src/pages/Endgames.tsx
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 122: Code Review Report

**Reviewed:** 2026-06-15T20:30:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 122 implements an in-app feedback button: a floating FAB, a modal with sentiment selection,
a POST /api/feedback endpoint, per-user sliding-window rate limiting, and a Sentry push signal.

The implementation is substantially correct and follows project conventions well. Auth gating,
user_id injection, FK constraints, Pydantic field validation, and Sentry grouping rules are all
handled properly. No security blockers were found: the endpoint is correctly gated behind
`current_active_user`, user_id is never taken from the request body, `page_url`/`text` are
length-capped, and the sentiment field uses a `Literal` type with database-level length cap.

Three warnings were found: a missing `min_length=1` on `page_url` (API boundary gap), an ARIA
conformance mismatch in the sentiment picker (radiogroup + aria-pressed is self-contradictory),
and a button variant convention violation in `FeedbackButton` (`variant="secondary"` is reserved
for neutral gray chips/toggles per CLAUDE.md; a floating action button should use `brand-outline`
or `outline`). Two info items cover a pending `requestAnimationFrame` not cancelled on unmount
and a mismatch between the `role="radiogroup"` container label ("How do you feel?") and the
displayed option labels ("Suggestion" for neutral).

---

## Warnings

### WR-01: `page_url` accepts empty string at the API boundary

**File:** `app/schemas/feedback.py:23`

**Issue:** `page_url` has `max_length=_MAX_PAGE_URL_LEN` but no `min_length=1`. A direct API
caller (e.g. a test script, a malformed client) can submit `""` for `page_url`. The field is
`NOT NULL` in the database and in the ORM model, but PostgreSQL accepts an empty string as a
valid non-null value, so this would persist without error. The frontend always sends
`loc.pathname + loc.search` which is at least `"/"`, but the API boundary has no guard.
The comment on the `text` field explicitly calls out that `min_length=1` prevents empty text
from yielding a 422 — the same rationale applies to `page_url`.

**Fix:**
```python
# app/schemas/feedback.py
page_url: str = Field(min_length=1, max_length=_MAX_PAGE_URL_LEN)
```

---

### WR-02: ARIA conformance — `role="radiogroup"` children must use `role="radio"` + `aria-checked`, not `aria-pressed`

**File:** `frontend/src/components/feedback/FeedbackModal.tsx:118-143`

**Issue:** The sentiment picker declares `role="radiogroup"` on the container (line 118), which
signals to screen readers that the children are radio buttons. However, the individual sentiment
buttons use `aria-pressed` (line 131), which is the toggle-button pattern. These two patterns are
mutually exclusive: a `radiogroup` expects children with `role="radio"` and `aria-checked`; a set
of toggle buttons expects no parent `radiogroup`. Screen readers (NVDA, VoiceOver) will announce
the children incorrectly, potentially reading "radio button" from the parent role while seeing
`aria-pressed` on the child, producing confusing or no output.

**Fix — option A (radio pattern, matches the single-selection semantics):**
```tsx
<div
  role="radiogroup"
  aria-label="How do you feel? (optional)"
  data-testid="feedback-sentiment"
  className="flex gap-2"
>
  {SENTIMENT_OPTIONS.map(({ value, label, Icon }) => {
    const isSelected = sentiment === value;
    return (
      <button
        key={value}
        type="button"
        role="radio"
        aria-checked={isSelected}
        data-testid={`feedback-sentiment-${value}`}
        onClick={() => handleSentimentClick(value)}
        disabled={isPending}
        // ... className unchanged
      >
```

**Fix — option B (toolbar of toggle buttons, if deselect-all is intended):**
Remove `role="radiogroup"` from the container and keep `aria-pressed` on each button.

Option A is preferred since the current single-selection behavior with toggle-off matches radio
semantics.

---

### WR-03: `FeedbackButton` uses `variant="secondary"` — reserved for neutral gray chips/toggles

**File:** `frontend/src/components/feedback/FeedbackButton.tsx:46`

**Issue:** CLAUDE.md explicitly prohibits `variant="secondary"` for secondary action buttons:
"Do NOT use `variant="secondary"` for secondary actions — that variant is reserved for neutral
gray chips/toggles." The floating feedback trigger is a supporting action button, not a chip or
toggle. The correct variant per CLAUDE.md for supporting/low-emphasis interactive controls is
`brand-outline` (brown outline) or `outline` (neutral border).

**Fix:**
```tsx
<Button
  variant="outline"   // or "brand-outline" for a warmer brand accent
  className="h-11 w-11"
  aria-label="Send feedback"
  data-testid="btn-feedback-open"
  onClick={() => setOpen(true)}
>
```

---

## Info

### IN-01: `requestAnimationFrame` callback not cancelled on unmount in `useScrollDirection`

**File:** `frontend/src/hooks/useScrollDirection.ts:26-46`

**Issue:** The cleanup function at lines 51-54 removes the scroll event listener and resets
`ticking.current = false`, but does not cancel a pending `requestAnimationFrame`. If the
component using this hook unmounts between a scroll event queuing an rAF and the rAF callback
executing, the callback still runs, calls `setDirection` on a closed-over state setter, and
mutates `prevScrollY.current`. In React 18 this is a no-op rather than a crash (React suppresses
state updates on unmounted components), but it is wasted CPU and leaves a dangling rAF in flight
until the next frame.

**Fix:**
```ts
useEffect(() => {
  let rafId: number | null = null;

  const handleScroll = () => {
    if (ticking.current) return;
    ticking.current = true;
    rafId = requestAnimationFrame(() => {
      ticking.current = false;
      rafId = null;
      // ... rest of callback unchanged
    });
  };

  window.addEventListener('scroll', handleScroll, { passive: true });

  return () => {
    window.removeEventListener('scroll', handleScroll);
    ticking.current = false;
    if (rafId !== null) cancelAnimationFrame(rafId);
  };
}, []);
```

---

### IN-02: Sentiment option label "Suggestion" does not match the `role="radiogroup"` prompt "How do you feel?"

**File:** `frontend/src/components/feedback/FeedbackModal.tsx:26`

**Issue:** The `neutral` sentiment option is labelled `"Suggestion"` (line 26), while the
container is labelled `"How do you feel? (optional)"`. A suggestion is not an emotional valence
— it is a distinct feedback type. This creates a conceptual mismatch: users choosing "Suggestion"
are categorizing their intent, not their sentiment. This may cause misclassified data in Sentry
tags (sentiment=neutral for all feature requests). Consider either relabelling the container to
"Feedback type" or renaming `neutral` to `idea`/`suggestion` in both the UI and the sentiment
literal (if the backend Sentry signal distinction matters).

**Fix (minimal — no schema change):** rename the group label:
```tsx
<div
  role="radiogroup"
  aria-label="Feedback type (optional)"
  ...
>
```
Or if "How do you feel?" is intentional, rename the button to `"Neutral"` for semantic
consistency with the other two options.

---

## Findings not raised

The following areas were checked and found clean:

- **Auth scope (D-08):** `current_active_user` (not `current_verified_user`) correctly allows
  both full and guest users, matching the spec decision.
- **Rate limiter keying:** keyed by `str(user.id)` (not IP), so a user rotating IPs cannot
  bypass the 5/hour limit. The in-process singleton is acknowledged as restart-reset, acceptable
  for single-process Uvicorn (A5).
- **SQL injection / injection risk:** all DB writes go through SQLAlchemy ORM with parameterized
  values; no raw SQL in the repository.
- **PII in Sentry:** `text` (the raw feedback body) is correctly excluded from `set_context`.
  Only `user_id`, `page_url`, and `sentiment` are sent. `send_default_pii=False` is set globally
  in `main.py`.
- **Sentry grouping:** `capture_message` uses a static string literal — no f-string variable
  embedding that would fragment issue grouping.
- **FK ondelete policy:** `ondelete="CASCADE"` on `user_id`, matching the DB rules in CLAUDE.md.
- **ELO bucket logic:** the Python `elo_bucket()` implementation correctly mirrors the SQL
  `CASE WHEN` expression in `canonical_slice_sql.elo_bucket_expr`.
- **MutationObserver cleanup:** `useOverlayOpen` correctly disconnects the observer in the
  `useEffect` cleanup.
- **`data-testid` / `aria-label` coverage:** all interactive elements in `FeedbackButton` and
  `FeedbackModal` have `data-testid` and, where icon-only, `aria-label`.
- **`text-sm` floor:** no `text-xs` usage in the new components (only in existing
  `MobileBottomBar` nav labels which are pre-existing).
- **`pb-20` padding:** correctly applied mobile-only via `md:pb-6` override on Endgames; on
  FlawsTab and GamesTab the outer layout provides the desktop clipping.
- **No `asyncio.gather` on shared session:** the router calls `feedback_repository` then
  `feedback_service` sequentially on the same session.
- **Duplicate Sentry capture:** `useFeedback` correctly omits a component-level
  `Sentry.captureException`; the global `MutationCache.onError` in `queryClient.ts` covers it.
- **Router prefix convention:** `router = APIRouter(prefix="/feedback", ...)` with `@router.post("")`
  — no prefix duplication.
- **`router.include_router` in main.py:** `app.include_router(feedback.router, prefix="/api")`
  matches the pattern of all other routers.
- **Migration downgrade:** `downgrade()` drops the index before dropping the table, preventing
  a constraint-removal ordering error.

---

_Reviewed: 2026-06-15T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
