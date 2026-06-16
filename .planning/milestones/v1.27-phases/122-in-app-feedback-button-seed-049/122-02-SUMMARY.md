---
phase: 122-in-app-feedback-button-seed-049
plan: 02
subsystem: frontend
tags: [react, typescript, tanstack-query, tailwind, shadcn, vitest, tdd, radix, lucide]

requires:
  - phase: 122-01
    provides: "POST /api/feedback endpoint with FeedbackCreate/FeedbackResponse + Sentiment Literal"

provides:
  - "Sentiment/FeedbackRequest/FeedbackResponse TS types (frontend/src/types/feedback.ts)"
  - "feedbackApi.submit() wired to POST /feedback (frontend/src/api/client.ts)"
  - "useFeedback() TanStack mutation hook (no double Sentry capture)"
  - "useScrollDirection() hook: 'up'|'down', rAF-debounced, threshold-based"
  - "useOverlayOpen() hook: MutationObserver DOM-presence signal for overlay detection"
  - "FeedbackButton: fixed bottom-right floating trigger, z-20, safe-area, hide-on-scroll/overlay"
  - "FeedbackModal: Dialog form with required text, 3-point sentiment toggle-off, page_url from router"
  - "Global mount in ProtectedLayout (App.tsx)"
  - "pb-20 bottom scroll padding on GamesTab, FlawsTab, Endgames main"

affects:
  - App.tsx (FeedbackButton mounted in ProtectedLayout)
  - frontend/src/api/client.ts (feedbackApi added)
  - frontend/src/pages/library/GamesTab.tsx (pb-20 on mainContent)
  - frontend/src/pages/library/FlawsTab.tsx (pb-20 on mainContent)
  - frontend/src/pages/Endgames.tsx (pb-20 on main element)

tech-stack:
  added: []
  patterns:
    - "useScrollDirection: passive scroll listener + requestAnimationFrame debounce + threshold guard"
    - "useOverlayOpen: MutationObserver on document.body watching radix data-slot overlay selectors"
    - "useFeedback: useMutation<FeedbackResponse, Error, FeedbackRequest> — no onError Sentry (global MutationCache covers it)"
    - "FeedbackModal: Dialog form with controlled textarea + sentiment segmented control (toggle-off)"
    - "FeedbackButton: transition-all opacity/translate for smooth hide/show on scroll and overlay events"

key-files:
  created:
    - frontend/src/types/feedback.ts
    - frontend/src/hooks/useScrollDirection.ts
    - frontend/src/hooks/useOverlayOpen.ts
    - frontend/src/hooks/useFeedback.ts
    - frontend/src/components/feedback/FeedbackButton.tsx
    - frontend/src/components/feedback/FeedbackModal.tsx
    - frontend/src/hooks/__tests__/useScrollDirection.test.ts
    - frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx
    - frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx
  modified:
    - frontend/src/api/client.ts (feedbackApi.submit added)
    - frontend/src/App.tsx (FeedbackButton mounted in ProtectedLayout)
    - frontend/src/pages/Endgames.tsx (pb-20 on main)
    - frontend/src/pages/library/GamesTab.tsx (pb-20 on mainContent)
    - frontend/src/pages/library/FlawsTab.tsx (pb-20 on mainContent)
    - CHANGELOG.md (unreleased entry)

decisions:
  - "useOverlayOpen uses DOM-presence MutationObserver (A3 from RESEARCH) rather than zustand store — no per-drawer wiring needed; radix data-slot selectors cover all existing overlays"
  - "useScrollDirection uses rAF + ticking boolean (not rafId) to avoid synchronous-mock assignment race; tests stub requestAnimationFrame to call synchronously"
  - "Bottom scroll padding applied to GamesTab/FlawsTab mainContent and Endgames main — NOT to global App main (plan spec: don't blanket-apply); MoveList has fixed height so no padding needed there"
  - "FeedbackButton renders as opacity-0 + pointer-events-none (not unmounted) for smooth transitions; useOverlayOpen hides it even when its own modal is open (harmless, expected per UI-SPEC)"
  - "No @testing-library/user-event (not in lockfile) — tests use fireEvent.change/click from @testing-library/react"

metrics:
  duration: 29min
  started: "2026-06-15T21:33:00Z"
  completed: "2026-06-15T22:02:00Z"
  tasks: 3
  files_modified: 14
---

# Phase 122 Plan 02: Frontend Feedback Vertical Slice Summary

**Floating feedback trigger (FeedbackButton) + submit modal (FeedbackModal) wired to POST /api/feedback via useMutation, with two new no-analog hooks (useScrollDirection, useOverlayOpen) handling hide-on-scroll and yield-to-overlay behavior, mounted globally in ProtectedLayout**

## Performance

- **Duration:** 29 min
- **Started:** 2026-06-15T21:33:00Z
- **Completed:** 2026-06-15T22:02:00Z
- **Tasks:** 3 (Tasks 1 and 2: TDD with RED/GREEN commits; Task 3: full gate)
- **Files modified:** 14

## Accomplishments

- Two new no-analog hooks: `useScrollDirection` (rAF-debounced passive scroll listener, threshold-based) and `useOverlayOpen` (MutationObserver on document.body watching radix data-slot selectors)
- `feedbackApi.submit()` added to api/client.ts; `useFeedback()` wraps it with useMutation (no double Sentry capture per CLAUDE.md)
- `FeedbackModal`: required textarea, 3-point sentiment segmented control (single-select toggle-off), page_url from useLocation(), success toast + close, error copy for 429/422/network
- `FeedbackButton`: z-20, `bottom-[4.5rem]` on mobile / `bottom-4` on `sm:`, `pb-safe` for iOS PWA, `h-11 w-11` 44px touch target, `variant="secondary"` (not brand-brown), 150ms opacity/translate transition
- Globally mounted in `ProtectedLayout` (App.tsx) next to `InstallPromptBanner`
- Bottom scroll padding (`pb-20`) applied to GamesTab, FlawsTab mainContent, and Endgames main element
- 9 new tests across 3 test files; full suite green (84 files, 953 tests)
- ESLint and knip clean

## Task Commits

Each task was committed atomically (TDD tasks have multiple commits):

1. **Task 1: useScrollDirection + useOverlayOpen** (TDD RED/GREEN)
   - `c63ffecd` test(122-02): add failing tests for useScrollDirection hook
   - `6dd19907` feat(122-02): implement useScrollDirection and useOverlayOpen hooks

2. **Task 2: Types, api, useFeedback, FeedbackModal, FeedbackButton + mount + scroll padding** (TDD RED/GREEN)
   - `c53b84bd` test(122-02): add failing tests for FeedbackButton and FeedbackModal
   - `08aa560f` feat(122-02): implement feedback types, api, hooks, and components

3. **Task 3: Full frontend gate**
   - `ea7582cd` chore(122-02): full frontend gate - fix lint and update test assertions

## Files Created/Modified

- `frontend/src/types/feedback.ts` - Sentiment | FeedbackRequest | FeedbackResponse types (mirrors backend contract)
- `frontend/src/hooks/useScrollDirection.ts` - Passive scroll listener + rAF debounce returning 'up'|'down'
- `frontend/src/hooks/useOverlayOpen.ts` - MutationObserver DOM-presence check for radix overlays
- `frontend/src/hooks/useFeedback.ts` - useMutation wrapper (no Sentry double-capture)
- `frontend/src/components/feedback/FeedbackButton.tsx` - Floating trigger with scroll+overlay visibility
- `frontend/src/components/feedback/FeedbackModal.tsx` - Dialog form with sentiment control + error handling
- `frontend/src/api/client.ts` - Added feedbackApi.submit()
- `frontend/src/App.tsx` - Mounted FeedbackButton in ProtectedLayout
- `frontend/src/pages/Endgames.tsx` - Added pb-20 to main content element
- `frontend/src/pages/library/GamesTab.tsx` - Added pb-20 to mainContent div
- `frontend/src/pages/library/FlawsTab.tsx` - Added pb-20 to mainContent div
- `frontend/src/hooks/__tests__/useScrollDirection.test.ts` - 6 tests for scroll direction
- `frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx` - 4 tests for button visibility + modal open
- `frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx` - 9 tests for form behavior + mutation

## Decisions Made

- MutationObserver + radix data-slot DOM-presence for overlay detection (A3 from RESEARCH). Lower wiring than zustand store (no per-drawer wiring needed). Covers all existing radix Dialog/Drawer surfaces automatically.
- `useScrollDirection` uses a `ticking` boolean ref (not a rafId ref) to avoid the synchronous-mock assignment race: `rafId = requestAnimationFrame(cb)` after a synchronous-mock's `cb()` would overwrite the `null` set inside `cb`. The `ticking` pattern avoids the issue.
- Bottom scroll padding applied to `GamesTab`/`FlawsTab` `mainContent` and `Endgames` `<main>` — not blanket-applied to App's `<main>`. The plan explicitly says not to double-apply to `<main>`.
- `FeedbackButton` renders visible/hidden via `opacity-0 pointer-events-none` (not `display: none`) so the smooth transition works and React state (modal open) is preserved.
- No `@testing-library/user-event` (not in lockfile per CLAUDE.md memory note: no Prettier, no user-event). Tests use `fireEvent.change`/`fireEvent.click` from `@testing-library/react`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] rAF mock race condition in useScrollDirection tests**
- **Found during:** Task 1 (GREEN phase, tests failing)
- **Issue:** `rafId.current = requestAnimationFrame(cb)` — with a synchronous rAF mock, `cb()` runs and sets `rafId.current = null` inside the callback, then the outer assignment `rafId.current = 0` (the mock's return value) overwrites it. On the next scroll event, `if (rafId.current !== null) return` would fire erroneously.
- **Fix:** Replaced `rafId.current` pattern with a `ticking` boolean ref: `ticking.current = true` before rAF call, `ticking.current = false` as the first line inside the callback. Tests stub `requestAnimationFrame` to call `cb` synchronously so direction updates are immediate.
- **Files modified:** `frontend/src/hooks/useScrollDirection.ts`, `frontend/src/hooks/__tests__/useScrollDirection.test.ts`

**2. [Rule 3 - Blocking] @testing-library/user-event not in lockfile**
- **Found during:** Task 2 (FeedbackButton.test.tsx import resolution)
- **Issue:** The plan referenced `userEvent` for typing interactions, but `@testing-library/user-event` is not installed in `frontend/package.json`.
- **Fix:** Replaced `userEvent.type()` with `fireEvent.change(el, { target: { value: ... } })` and `userEvent.click()` with `fireEvent.click()`. No new package needed.
- **Files modified:** `frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx`, `frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx`

**3. [Rule 2 - Missing] FeedbackButton test needs router + useFeedback mocks**
- **Found during:** Task 2 (FeedbackButton test run; FeedbackModal inside FeedbackButton uses useLocation)
- **Issue:** FeedbackButton renders FeedbackModal which calls `useLocation()`. The test didn't mock `react-router-dom` or `useFeedback`. Rendered inside `FeedbackButton`, the modal needs both mocks to mount without a Router context or QueryClientProvider.
- **Fix:** Added `vi.mock('react-router-dom', ...)` and `vi.mock('@/hooks/useFeedback', ...)` to `FeedbackButton.test.tsx`.
- **Files modified:** `frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx`

## Known Stubs

None. All data is wired: text+sentiment+page_url POSTed to the real backend endpoint. No hardcoded empty values or placeholder data in the feedback components.

## Threat Surface Scan

No new network endpoints beyond the plan's POST /api/feedback (wired from Plan 01). Threat mitigations from the plan's threat_model are all in place:
- T-122-F1 (Tampering, textarea injection): React default-escapes JSX text; no `dangerouslySetInnerHTML`
- T-122-F2 (Spoofing, page_url): `useLocation()` captures router state, not user-typed; user_id from JWT on backend
- T-122-F3 (Sentry double-capture): no `Sentry.captureException` in FeedbackModal or useFeedback; global MutationCache.onError is the single capture point

## Manual Verification Still Outstanding

These require a real browser/device and cannot be covered by automated tests:

1. **iOS safe-area** — verify `pb-safe` clears the home indicator in installed PWA mode on an actual iOS device. The `tailwindcss-safe-area` plugin is imported in `index.css:4` and should apply, but env(safe-area-inset-bottom) requires a real Safari/iOS environment.
2. **Real mobile drawer collision** — verify that opening the Openings filter/bookmark drawers or the Library filter drawer actually hides the FeedbackButton in the browser (MutationObserver fires on radix portal, which adds `[data-slot="drawer-content"]` to document.body).
3. **Sentry cohort-tag ping** — submit feedback on prod and verify the Sentry event arrives with the correct `source=feedback`, `platform`, and `elo_bucket` tags (Plan 01 backend concern, but the frontend trigger must fire).
4. **FeedbackButton position on MobileBottomBar boundary** — confirm visually on a mobile viewport that `bottom-[4.5rem]` clears the 4rem MobileBottomBar without overlap.

## Self-Check: PASSED

Files created/verified:
- frontend/src/types/feedback.ts: FOUND
- frontend/src/hooks/useScrollDirection.ts: FOUND
- frontend/src/hooks/useOverlayOpen.ts: FOUND
- frontend/src/hooks/useFeedback.ts: FOUND
- frontend/src/components/feedback/FeedbackButton.tsx: FOUND
- frontend/src/components/feedback/FeedbackModal.tsx: FOUND
- frontend/src/hooks/__tests__/useScrollDirection.test.ts: FOUND
- frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx: FOUND
- frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx: FOUND

Commits verified:
- c63ffecd: FOUND
- 6dd19907: FOUND
- c53b84bd: FOUND
- 08aa560f: FOUND
- ea7582cd: FOUND

---
*Phase: 122-in-app-feedback-button-seed-049*
*Completed: 2026-06-15*
