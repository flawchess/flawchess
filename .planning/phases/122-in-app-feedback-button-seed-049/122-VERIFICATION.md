---
phase: 122-in-app-feedback-button-seed-049
verified: 2026-06-15T20:07:03Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "iOS safe-area in installed PWA mode"
    expected: "The FeedbackButton's pb-safe utility clears the home indicator on an actual iOS device in PWA standalone mode (env(safe-area-inset-bottom) applies)"
    why_human: "env(safe-area-inset-bottom) only resolves in a real Safari/iOS WebKit context — jsdom cannot simulate it"
  - test: "Real mobile drawer/overlay collision"
    expected: "Opening the Openings filter drawer, bookmark drawer, or Library filter drawer actually hides the FeedbackButton in a real browser (MutationObserver fires on radix portal insertion of [data-slot='drawer-content'])"
    why_human: "MutationObserver + DOM-presence requires a real browser DOM with radix portaling; jsdom vitest tests mock the hook rather than exercise the real observer"
  - test: "Live Sentry cohort-tag ping"
    expected: "Submitting feedback on prod causes a Sentry event to appear in the flawchess project tagged source=feedback, platform=<user's platform>, elo_bucket=<user's ELO bucket or unknown>"
    why_human: "Sentry capture_message is called in app/services/feedback_service.py with the correct static message and tags, but confirming it arrives tagged correctly in the Sentry dashboard (https://flawchess.sentry.io) requires a live prod submission"
  - test: "FeedbackButton position on MobileBottomBar boundary"
    expected: "bottom-[4.5rem] clears the 4rem MobileBottomBar without overlap; the button is visually accessible above the bar on a narrow mobile viewport"
    why_human: "CSS layout rendering and visual overlap require a real browser at a mobile viewport size — cannot be asserted via class-string inspection alone"
---

# Phase 122: In-App Feedback Button (SEED-049) Verification Report

**Phase Goal:** A low-friction in-app feedback channel so users (guests included) can submit likes / dislikes / suggestions tied to the exact page they were on. A global floating button (bottom-right, auto-hides on scroll-down, yields to open drawers/modals, iOS safe-area aware) opens a modal with required freeform text + an optional coarse sentiment rating. Submissions persist to a new `feedback` table and also fire a Sentry signal (tagged with username / ELO bucket / platform) so feedback pings the team instead of rotting in a table nobody reads.
**Verified:** 2026-06-15T20:07:03Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | An authenticated user (full OR guest) can POST /api/feedback with text + optional sentiment + page_url and a row is persisted | VERIFIED | `app/routers/feedback.py` calls `feedback_repository.create_feedback(session, user.id, data)` using `current_active_user` (which accepts guests). Tests `TestFeedbackPersist` and `TestFeedbackGuest` cover 201 for full + guest users. |
| 2 | Each submission emits a non-exception Sentry signal tagged source=feedback + platform + elo_bucket, with NO variable data in the message string | VERIFIED | `app/services/feedback_service.py:82` — `sentry_sdk.capture_message("feedback submitted", level="info")` is a static literal. Tags set via `set_tag("source","feedback")`, `set_tag("platform",...)`, `set_tag("elo_bucket",...)`. No f-string in the message. |
| 3 | Empty text yields 422; text over the max-length cap yields 422; over-rate yields 429 | VERIFIED | `FeedbackCreate` uses `Field(min_length=1, max_length=2000)`. `TestFeedbackValidation` covers empty→422, over-max→422. `TestFeedbackRateLimit.test_sixth_submission_returns_429` covers the 429 path. |
| 4 | The feedback row's user_id is derived from the authenticated user, never from the request body | VERIFIED | `FeedbackCreate` schema has no `user_id` field. Router passes `user.id` from `current_active_user` directly to `create_feedback(session, user.id, data)`. Test `test_create_feedback_user_id_from_argument_not_data` verifies this. |
| 5 | A bottom-right floating feedback button is present on every authenticated page; icon-only, secondary weight, 44x44 tap target, data-testid + aria-label | VERIFIED | `FeedbackButton.tsx`: `variant="secondary"`, `className="h-11 w-11"` (44px), `data-testid="btn-feedback-open"`, `aria-label="Send feedback"`. Mounted in `ProtectedLayout` in `App.tsx:461`. |
| 6 | The button hides on scroll-down and when ANY overlay is open, shows on scroll-up / at top | VERIFIED | `FeedbackButton.tsx:28` — `const visible = direction === 'up' && !overlayOpen;`. `useScrollDirection` returns 'up'/'down' via passive scroll+rAF. `useOverlayOpen` uses MutationObserver watching `[role="dialog"], [data-slot="dialog-content"], [data-slot="drawer-content"]`. When hidden: `opacity-0 translate-y-2 pointer-events-none`. Tests cover all three visibility states. |
| 7 | Clicking the button opens a modal with a required freeform textarea + optional 3-point sentiment; submit disabled until text is non-empty | VERIFIED | `FeedbackModal.tsx`: `<textarea data-testid="feedback-text" aria-required="true">`. Three `<button type="button" aria-pressed>` with testids `feedback-sentiment-negative/neutral/positive`. `disabled={!isSubmitEnabled}` where `isSubmitEnabled = text.trim().length > 0 && !isPending`. Tests `submit button is disabled when text is empty` and `enabled once non-empty` pass. |
| 8 | Submitting POSTs {text, sentiment?, page_url} to /api/feedback with page_url from useLocation(), shows success toast, and closes | VERIFIED | `FeedbackModal.tsx:58-74` — `const page_url = loc.pathname + loc.search; mutate({ text: text.trim(), sentiment, page_url }, { onSuccess: () => { toast('Thanks for the feedback!'); onOpenChange(false); ... } })`. Test `fires mutation with correct payload on submit` asserts the full payload including `page_url: '/openings'`. |
| 9 | The button sits at z-20, clears the mobile bottom bar, and respects iOS safe-area via tailwindcss-safe-area | VERIFIED (code) | `FeedbackButton.tsx`: `'fixed right-4 z-20'`, `'bottom-[4.5rem] sm:bottom-4'`, `'pb-safe'`. `tailwindcss-safe-area` is in `frontend/package.json` dependencies and imported in `frontend/src/index.css:4`. Visual rendering on real iOS device requires human verification (see Human Verification section). |

**Score:** 9/9 truths verified (4 require human confirmation for the device/environment aspects)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/feedback.py` | Feedback ORM with user_id FK ondelete=CASCADE, page_url, text, sentiment, created_at | VERIFIED | `class Feedback(Base)`, FK with `ondelete="CASCADE"`, `index=True`, all columns present |
| `app/schemas/feedback.py` | FeedbackCreate + FeedbackResponse + Sentiment Literal + length constants | VERIFIED | `Sentiment = Literal["negative", "neutral", "positive"]`, `_MAX_FEEDBACK_LEN=2000`, `_MAX_PAGE_URL_LEN=500`, `FeedbackCreate` with `min_length=1` guard on text and page_url |
| `app/repositories/feedback_repository.py` | `create_feedback(session, user_id, data)` using flush() | VERIFIED | `await session.flush()` — no `session.commit()` |
| `app/services/feedback_service.py` | `elo_bucket()` helper + `push_sentry_signal()` | VERIFIED | Both functions present with explicit return types, static Sentry message, correct ELO boundary logic |
| `app/core/feedback_rate_limiter.py` | `feedback_limiter` singleton (5/3600s, keyed by user_id) | VERIFIED | Imports `_SlidingWindowRateLimiter`, `_FEEDBACK_MAX_REQUESTS=5`, `_FEEDBACK_WINDOW_SECONDS=3600` |
| `app/routers/feedback.py` | Thin POST /feedback router with rate guard | VERIFIED | `APIRouter(prefix="/feedback")`, `@router.post("")`, rate check first, calls repository then service |
| `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py` | Creates feedback table + FK + ix_feedback_user_id only | VERIFIED | Creates only the `feedback` table with FK (`ondelete="CASCADE"`) + `ix_feedback_user_id`; no unrelated index changes |
| `frontend/src/types/feedback.ts` | Sentiment / FeedbackRequest / FeedbackResponse types mirroring backend | VERIFIED | Types match backend contract exactly |
| `frontend/src/hooks/useScrollDirection.ts` | Returns 'up' | 'down', rAF-debounced, threshold-based | VERIFIED | Passive listener + rAF ticking bool + `SCROLL_DELTA_THRESHOLD=8` + `AT_TOP_THRESHOLD=4` |
| `frontend/src/hooks/useOverlayOpen.ts` | MutationObserver DOM-presence signal | VERIFIED | `OVERLAY_SELECTOR` covers `[role="dialog"], [data-slot="dialog-content"], [data-slot="drawer-content"]`; observer on `document.body` |
| `frontend/src/hooks/useFeedback.ts` | useMutation wrapper, no double Sentry | VERIFIED | No `Sentry.captureException` in onError; relies on global `MutationCache.onError` |
| `frontend/src/components/feedback/FeedbackButton.tsx` | Floating trigger with all required attributes | VERIFIED | All required classes, testid, aria-label, z-20, safe-area, 44px target |
| `frontend/src/components/feedback/FeedbackModal.tsx` | Dialog form with required text + 3-point sentiment | VERIFIED | `role="group"` (not `radiogroup` — corrected in review fix 3bd1685e), `aria-pressed` toggles, `variant="default"` submit, `variant="ghost"` cancel |
| `tests/test_feedback_repository.py` | 4 repository-level tests | VERIFIED | Covers id populated, sentiment Literal, None sentiment, V4 access control |
| `tests/test_feedback_router.py` | 14 router tests + elo_bucket boundary tests | VERIFIED | 201/422/429/401, guest 201, elo_bucket 7 boundary tests |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/main.py` | `app.routers.feedback.router` | `include_router(feedback.router, prefix="/api")` | VERIFIED | `main.py:20` imports `feedback`; `main.py:151` registers it |
| `app/routers/feedback.py` | `feedback_repository.create_feedback` | Direct call in handler | VERIFIED | `fb = await feedback_repository.create_feedback(session, user.id, data)` |
| `app/services/feedback_service.py` | `sentry_sdk.capture_message` | Non-exception push signal | VERIFIED | `capture_message("feedback submitted", level="info")` — static string, no f-string |
| `frontend/src/App.tsx` | `FeedbackButton` | Global mount in ProtectedLayout | VERIFIED | `App.tsx:21` import, `App.tsx:461` render inside ProtectedLayout |
| `frontend/src/components/feedback/FeedbackModal.tsx` | `useFeedback` / `/api/feedback` | `useMutation` + `useLocation` | VERIFIED | `mutate({ text, sentiment, page_url })` where `page_url = loc.pathname + loc.search` |
| `frontend/src/components/feedback/FeedbackButton.tsx` | `useScrollDirection` + `useOverlayOpen` | Visibility guard | VERIFIED | `const visible = direction === 'up' && !overlayOpen;` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `FeedbackModal.tsx` | `text`, `sentiment`, `page_url` | User input + `useLocation()` | Yes — `useLocation()` returns real router state; text/sentiment from controlled state | FLOWING |
| `feedback_repository.create_feedback` | `Feedback` ORM row | `session.flush()` on real DB insert | Yes — FK-constrained INSERT followed by flush; PK populated by DB | FLOWING |
| `push_sentry_signal` | ELO bucket | `fetch_anchors_for_user(session, user_id=user.id)` | Yes — real DB query for user's anchor ratings | FLOWING |

---

### Behavioral Spot-Checks

Tests were run as part of the execution phase (full suite green: 2671 backend tests, 953 frontend tests per SUMMARY). Individual named tests were confirmed to exist and cover the phase's behaviors:

| Behavior | Test | Status |
|----------|------|--------|
| POST /api/feedback returns 201 for authenticated user | `TestFeedbackPersist.test_create_returns_201_with_response` | VERIFIED (code confirms test exists and covers the path) |
| Guest can submit feedback → 201 | `TestFeedbackGuest.test_guest_can_submit_feedback` | VERIFIED |
| Empty text → 422 | `TestFeedbackValidation.test_empty_text_returns_422` | VERIFIED |
| Over-rate → 429 | `TestFeedbackRateLimit.test_sixth_submission_returns_429` | VERIFIED |
| elo_bucket 800 boundary | `TestEloBucket.test_elo_bucket_800_boundary` | VERIFIED |
| Submit button disabled until text non-empty | `FeedbackModal: submit button is disabled when text is empty` | VERIFIED |
| Sentiment toggle-off | `FeedbackModal: selecting a sentiment then tapping again clears it` | VERIFIED |
| Button hidden on scroll-down | `FeedbackButton: is not visible when scroll direction is down` | VERIFIED |

---

### Requirements Coverage

Requirements were declared inline in each PLAN frontmatter (SEED-049 parent, D-01 through D-08). No REQUIREMENTS.md file exists at `.planning/REQUIREMENTS.md` — requirements for this phase live in the SEED file and CONTEXT.md decisions.

| Requirement | Plan | Status | Evidence |
|-------------|------|--------|----------|
| SEED-049 (feedback channel) | 01+02 | SATISFIED | Full vertical slice implemented end-to-end |
| D-04 (persistence + access control) | 01 | SATISFIED | `user_id` from JWT, row persisted via flush(), DB FK enforced |
| D-05 (Sentry signal) | 01 | SATISFIED | Static `capture_message` + `set_tag` source/platform/elo_bucket |
| D-07 (rate limit + length cap) | 01 | SATISFIED | 5/3600s per-user limiter → 429; Pydantic `max_length=2000` → 422 |
| D-08 (guests accepted) | 01 | SATISFIED | `current_active_user` (includes guests); guest test passes |
| D-01 (discoverable trigger) | 02 | SATISFIED | FeedbackButton mounted globally in ProtectedLayout |
| D-02 (non-intrusive, safe-area, z-index) | 02 | SATISFIED (code) | z-20, pb-safe, h-11 w-11, opacity transition, bottom-[4.5rem] mobile offset |
| D-03 (required text, optional sentiment) | 02 | SATISFIED | `min_length=1`, disabled submit until non-empty, 3-point toggle-off sentiment |
| D-06 (page URL from router) | 02 | SATISFIED | `loc.pathname + loc.search` captured at submit time via `useLocation()` |

---

### Anti-Patterns Found

No blocker anti-patterns found:
- No `TBD`, `FIXME`, or `XXX` markers in any phase 122 files.
- No stub returns (`return null`, `return {}`, `return []`) in production code paths.
- No double Sentry capture — `useFeedback.ts` has no `onError` handler; global `MutationCache.onError` in `queryClient.ts` is the single capture point.
- No `text-xs` in feedback components (CLAUDE.md minimum is `text-sm`).
- No magic numbers — `_MAX_FEEDBACK_LEN`, `_MAX_PAGE_URL_LEN`, `_FEEDBACK_MAX_REQUESTS`, `_FEEDBACK_WINDOW_SECONDS`, `SCROLL_DELTA_THRESHOLD`, `AT_TOP_THRESHOLD` all named.
- `user_id` is absent from `FeedbackCreate` schema — access-control V4 is satisfied by design.
- The `role="radiogroup"` false positive from code review was corrected in commit `3bd1685e` — the sentiment control uses `role="group"` (correct for deselectable toggle buttons with `aria-pressed`).
- The `variant="secondary"` on `FeedbackButton` is confirmed correct per UI-SPEC: the trigger is intentionally a neutral chip, not a brand-brown FAB.

---

### Human Verification Required

#### 1. iOS safe-area in installed PWA mode

**Test:** Install the flawchess app on an iPhone and navigate to any authenticated page. Verify the floating FeedbackButton clears the home indicator at the bottom of the screen without overlapping it.
**Expected:** The `pb-safe` utility (from `tailwindcss-safe-area`) applies `env(safe-area-inset-bottom)` correctly, pushing the button up above the home indicator.
**Why human:** `env(safe-area-inset-bottom)` resolves to 0 in all non-iOS environments; jsdom and Chrome devtools device emulation do not simulate it accurately. Requires a real iPhone in standalone (PWA install) mode.

#### 2. Real mobile drawer/overlay collision

**Test:** Open the Openings page, activate the filter sidebar drawer (or bookmark drawer). Verify the FeedbackButton disappears while the drawer is open and reappears when it closes.
**Expected:** The `MutationObserver` in `useOverlayOpen.ts` fires when radix portals the drawer content into `document.body` with `[data-slot="drawer-content"]`, setting `overlayOpen=true` and hiding the button.
**Why human:** The jsdom tests mock `useOverlayOpen` directly rather than exercising the real MutationObserver against a radix portal. Needs a real browser to confirm the selector fires on actual drawer mounts.

#### 3. Live Sentry cohort-tag ping

**Test:** Submit feedback on the production site (https://flawchess.com) while logged in as a known user with ELO data. Check the Sentry dashboard (https://flawchess.sentry.io) for an event with `source=feedback`, `platform=<user's platform>`, and `elo_bucket=<expected bucket>`.
**Expected:** The event arrives tagged correctly and is grouped under "feedback submitted" (not fragmented by user-specific message strings).
**Why human:** Production Sentry requires a live deployment and a real submission. Cannot be verified against code alone.

#### 4. FeedbackButton visual position on MobileBottomBar boundary

**Test:** Open the app on a narrow mobile viewport (e.g. 390px width, iPhone 14). Verify the FeedbackButton sits visually above the MobileBottomBar with no overlap, and below any install banner when present.
**Expected:** `bottom-[4.5rem]` (72px) clears the `h-16` (64px) MobileBottomBar; the button does not visually overlap the bar or the content above it.
**Why human:** CSS rendering and pixel-level layout require a real browser at the target viewport size. Class-string inspection confirms the CSS intent but not the rendered result.

---

### Gaps Summary

No automated gaps. All 9 must-have truths are verified by code inspection (implementation is substantive and wired). The 4 human-verification items are genuine environment-dependent checks (iOS safe-area, real MutationObserver behavior, prod Sentry, visual layout) that cannot be confirmed programmatically — they are the residual manual verification items documented in the 122-02-SUMMARY.md itself.

---

_Verified: 2026-06-15T20:07:03Z_
_Verifier: Claude (gsd-verifier)_
