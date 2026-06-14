---
status: resolved
trigger: "Recurring Sentry errors FLAWCHESS-5F (127384361) + FLAWCHESS-5Y (127898283): Maximum update depth exceeded on /library/games, despite 2 prior fix attempts"
created: 2026-06-14
updated: 2026-06-14
root_cause: "EvalChart slider controlled to derived value={activePly}=hoverPly??sliderPly; a sticky hoverPly (set by chart mousemove the (pointer:coarse) guard misclassified as fine on Android desktop-site/hybrid devices) pinned the input, fighting onChange into Maximum update depth exceeded."
fix: "Option C — (1) value={sliderPly} decouples the slider from hoverPly so a sticky hover can never pin it (loop structurally impossible on all devices); (2) useIsCoarsePointer also checks (any-pointer: coarse) and navigator.maxTouchPoints so any touchscreen makes the chart inert (touch scrub via overlay only sets sliderPly)."
verification: "npm run lint clean; npx tsc -b --noEmit exit 0; vitest 924/924 pass; npm run knip clean. Production verification pending deploy (intermittent, hybrid-pointer-device-specific — not reproducible in jsdom)."
files_changed: "frontend/src/components/library/EvalChart.tsx"
---

# Debug: EvalChart "Maximum update depth exceeded" (recurring)

## Symptoms

- Two Sentry issues, **same underlying bug**:
  - **FLAWCHESS-5F** (127384361) — `Maximum update depth exceeded`, culprit `/library/games`, 4 occurrences, substatus **regressed**, last seen 2026-06-14. Mechanism: `auto.browser.global_handlers.onerror`. Most-relevant first-party frame = minified `D` = `EvalChart.handleSliderChange`.
  - **FLAWCHESS-5Y** (127898283) — same error, commit-phase manifestation (error surfaces during radix Tooltip ref-cleanup inside the card). componentStack decodes to: `GamesTab`(H3) → `LibraryGameCardList`(Dye) → `LibraryGameCard`(R3) → … → Tooltip.
- Both events: same session — CH, Chrome Mobile 149 on **Android 10**, device "Generic_Android / K", both at 2026-06-14T20:37. A **touch device**.

## Root Cause (FOUND)

`frontend/src/components/library/EvalChart.tsx`. The native range slider is controlled to the **derived** active ply:

```
value={activePly}            // activePly = hoverPly ?? sliderPly   (line 933, 550)
onChange={handleSliderChange} // clears hoverPly, sets sliderPly
```

Meanwhile the chart surface sets `hoverPly` on `onMouseMove` (line 736 → `handlePointerMove`) and clears it only on `onMouseLeave`.

The chart is made inert on touch (`pointer-events-none` + a touch-scrub overlay) **only when `useIsCoarsePointer()` returns true**. That guard uses `window.matchMedia('(pointer: coarse)')`, which reports **fine** on hybrid / desktop-site-mode Android (the affected device). When misdetected as fine:

1. Chart stays hover-interactive. A finger touch makes Chrome synthesize `mousemove` → `setHoverPly(p)`. No `mouseleave` fires on touch-end → `hoverPly` goes **sticky**.
2. Slider `value` is now pinned to `hoverPly`. Dragging the slider fires `onChange` but the controlled value can't move; React keeps resetting the DOM value, re-firing change.
3. The slider handler clears `hoverPly`, but the chart's continuous synthesized `mousemove` **re-arms it within the same commit** → setState↔re-render fight → >50 updates → `Maximum update depth exceeded`.

## Why the 2 prior fixes failed

- `d9b88846` (2026-06-08) memoized chart data — addressed recharts hover reset, not the controlled-value pin.
- `afa0aa59` (2026-06-12) cleared `hoverPly` in the slider handlers (`handleSliderEngage` / `handleSliderChange`) — **can't win**: as long as the chart remains hover-interactive (isTouch=false), `onMouseMove` re-sets `hoverPly` faster than the handler clears it.

Both fixes are detection-dependent / handler-based. The loop is structurally possible whenever the slider's controlled value depends on `hoverPly`.

## Fix options

- **A — robust touch detection**: also treat `(any-pointer: coarse)` / `navigator.maxTouchPoints > 0` as touch in `useIsCoarsePointer`. Makes the chart inert on any touchscreen → `hoverPly` never set from touch. Still detection-dependent; flips touchscreen-laptops to touch-mode.
- **B — structural decouple (recommended)**: set slider `value={sliderPly}` (not `activePly`). Crosshair/tooltip/active-dot still follow `activePly`; only the thumb no longer sweeps with mouse hover. A controlled input can never be pinned by hover → loop impossible on **every** device, independent of pointer detection.
- **C — both** A + B (defense in depth).

## Current Focus

hypothesis: Slider controlled `value={activePly}` is pinned by a sticky `hoverPly` (set by chart mousemove the coarse-pointer guard misclassified), causing the setState/re-render storm.
next_action: Confirm fix approach with user (UX trade-off in B), then apply + verify + reference both issues in commit.
