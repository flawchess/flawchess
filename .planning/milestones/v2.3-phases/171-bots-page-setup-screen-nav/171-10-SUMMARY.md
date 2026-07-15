---
phase: 171-bots-page-setup-screen-nav
plan: 10
subsystem: ui
tags: [react, tailwind, bot-play, mobile, gap-closure]

# Dependency graph
requires:
  - phase: 171
    plan: 09
    provides: "Current state of SetupScreen.tsx and Bots.tsx (both touched by 171-08's handleAnalyze param and 171-09's lastMove wiring) that this plan builds its diff against"
provides:
  - "SetupScreen.tsx and Bots.tsx's BotsGame root both carry pb-20 sm:pb-4 bottom-nav clearance, matching the app-wide established pattern"
  - "chipStyles.ts's CHIP_BASE_CLASS at the 40px floor (h-10), not 44px (h-11) — shared by TC/color/play-style chips"
  - "SetupScreen's TC bucket sub-headers render inline beside their chip grids instead of stacked above, with the WR-06 derived gridTemplateColumns invariant intact"
  - "SetupScreen's Start button at h-12 (48px) — the tallest control on the screen"
  - "SEED-105 — the still-unfixed App.tsx:567 safe-area-composition gap, flagged per this plan's scope fence"
affects: [bots]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Descendant arbitrary-variant scoping ([&_[data-slot=slider]]:min-h-10) to override a shared primitive's touch-target height on ONE screen only, without editing the primitive itself"

key-files:
  created: []
  modified:
    - frontend/src/components/bots/SetupScreen.tsx
    - frontend/src/components/bots/chipStyles.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/__tests__/SetupScreen.test.tsx

key-decisions:
  - "Kept Task 1 (clearance) and Task 2 (density) as independently revertable commits per the plan's explicit instruction"
  - "Slider height override applied via a scoped [&_[data-slot=slider]]:min-h-10 descendant selector on the SetupScreen root, not by editing the shared ui/slider.tsx primitive's min-h-11 (app-wide 44px contract stays untouched everywhere else)"
  - "Could not independently browser-verify the slider override's computed height in this environment (no browser tooling available to the executor) — applied it because CSS specificity analysis (attribute-selector descendant rule beats a single utility class) supports it working, and its correctness is covered by the plan's own mandatory real-device human-check for the whole density pass"

patterns-established: []

requirements-completed: [PLAY-02]

coverage:
  - id: D1
    description: "SetupScreen's root and BotsGame's root both carry pb-20 sm:pb-4 bottom-nav clearance (144px total with App.tsx's pb-16), matching the app's established Endgames.tsx/GamesTab.tsx/FlawsTab.tsx pattern that these two screens were previously the only ones omitting."
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — bottom-nav clearance (171 UAT gap 3, Task 1) > the setup-screen root carries pb-20 sm:pb-4 so the fixed bottom nav never occludes Start"
        status: pass
      - kind: manual_procedural
        ref: "Plan verification note: real phone / installed PWA / URL-bar-subtracted DevTools emulation required — jsdom performs no layout"
        status: unknown
    human_judgment: true
    rationale: "jsdom performs no layout; the class-presence test is mutation-proof but cannot prove the Start button is actually on-screen and unobstructed on a real device, which is the actual bug being closed."
  - id: D2
    description: "Density pass: chips 44px -> 40px floor (chipStyles.ts), TC sub-headers moved inline beside their chip grids (3 groups preserved, WR-06 gridTemplateColumns invariant intact), root gap-4 -> gap-3, sliders scoped to 40px on this screen only, Start button grown 32px -> 48px (h-12) so it is the tallest control on the screen."
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#mobile density (171 UAT gap 3, Task 2) — 3 tests (h-12 Start, h-10-not-h-11 chip, 3 surviving TC groups)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx — unchanged, still green against the new h-10 CHIP_BASE_CLASS"
        status: pass
      - kind: manual_procedural
        ref: "Plan verification note: real phone / installed PWA required to confirm Start is above the fold and is the visually largest control, chips/sliders still comfortably tappable, labels don't truncate"
        status: unknown
    human_judgment: true
    rationale: "Fold position, touch-target comfort, label truncation, and grid alignment are layout- and device-dependent; jsdom cannot render real layout to prove the CTA is on-screen."

# Metrics
duration: ~7min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 10: Bots setup screen bottom-nav clearance + density pass Summary

**`SetupScreen.tsx` and `Bots.tsx`'s in-game root both gained the app's established `pb-20 sm:pb-4` bottom-nav clearance, and the setup screen was tightened by ~112px net (40px chip floor, inline TC sub-headers, tighter gaps, scoped 40px sliders) while growing the Start button to 48px — the tallest control on the screen instead of the shortest.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-07-14T17:12:50+02:00
- **Completed:** 2026-07-14T17:18:13+02:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `SetupScreen.tsx`'s root and `Bots.tsx`'s `BotsGame` root both carry `pb-20 sm:pb-4` — the two screens that were the only ones in the app omitting the established bottom-nav clearance pattern now match `Endgames.tsx`/`GamesTab.tsx`/`FlawsTab.tsx`
- `chipStyles.ts`'s `CHIP_BASE_CLASS` moved from `h-11` (44px) to the documented 40px floor (`h-10`), shared by every chip on the screen (TC, color, `PlayStyleControl`'s Human/Engine presets)
- `TcBucketGroup`'s sub-header ("Blitz"/"Rapid"/"Classical") now renders inline to the left of its chip grid instead of stacked above it — the single biggest density win (~72px), with the 3-group structure and the WR-06 derived `gridTemplateColumns` invariant both fully preserved
- Start button grown from the default 32px to `h-12` (48px) — now the tallest control on the screen, correcting the previous backwards sizing where the primary CTA was the shortest element
- ELO/Play-style sliders scoped to a 40px hit target on this screen only via `[&_[data-slot=slider]]:min-h-10` on the `SetupScreen` root — the shared `ui/slider.tsx` primitive's app-wide `min-h-11` (44px) contract is untouched
- SEED-105 planted documenting the still-open `App.tsx:567` safe-area-composition gap, per the plan's explicit scope-fence instruction (not fixed in this plan)

## Task Commits

Each task was committed atomically (TDD RED → GREEN per task):

1. **Task 1: Bottom-nav clearance**
   - `03870e62` test(171-10): add failing test for setup-screen bottom-nav clearance
   - `09116704` feat(171-10): add bottom-nav clearance to setup screen and bot board
2. **Task 2: Density pass — shrink the controls, GROW the Start button**
   - `d498b1a5` test(171-10): add failing tests for setup screen density pass
   - `96d2842f` feat(171-10): density pass — shrink controls, grow Start button

**Plan metadata:** `fb3b701a` docs: plant seed — App.tsx bottom-nav clearance not safe-area-composed (SEED-105, required by plan verification step 9)

_Note: both tasks are TDD — test commit written and confirmed red (verified via `npm test`) before the implementation commit._

## Files Created/Modified
- `frontend/src/components/bots/SetupScreen.tsx` — root gains `pb-20 sm:pb-4` (Task 1) then `gap-3` + `[&_[data-slot=slider]]:min-h-10` (Task 2); `TcBucketGroup` restructured to an inline `flex items-center gap-2` row (`w-20 shrink-0` label + `flex-1` grid), `mb-2` → `mb-1`; Start `Button` gains `h-12`
- `frontend/src/components/bots/chipStyles.ts` — `CHIP_BASE_CLASS` `h-11` → `h-10`, doc comment updated to name the 40px floor as a deliberate, documented deviation
- `frontend/src/pages/Bots.tsx` — `BotsGame`'s root gains the same `pb-20 sm:pb-4` clearance
- `frontend/src/components/bots/__tests__/SetupScreen.test.tsx` — two new `describe` blocks: bottom-nav clearance (1 test) and mobile density (3 tests)
- `.planning/seeds/SEED-105-safe-area-composed-bottom-nav-clearance.md` — new seed (plan verification step 9)

## Decisions Made
- Task 1 and Task 2 kept as separate, independently revertable commits per the plan's explicit instruction
- Slider 40px override scoped via a descendant arbitrary variant on `SetupScreen`'s own root rather than editing the shared `ui/slider.tsx` primitive — keeps the app-wide 44px hit-target contract intact everywhere else
- Could not independently browser-verify the slider override's computed height in this execution environment (no browser tooling available to the executor); applied it on CSS-specificity grounds (an attribute-selector descendant rule outranks a single utility class regardless of source order) and left final confirmation to the plan's own mandatory real-device human-check, which already covers slider tappability as part of the whole density pass

## Deviations from Plan

None — plan executed exactly as written, including both TDD RED→GREEN cycles and the required SEED-105 capture.

## Issues Encountered

None. `npx tsc -b`, `npm run lint`, `npm run knip`, and the full frontend suite (`npm test -- --run`, 164 files / 2153 tests) all pass.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

**Human verification required before this gap can be marked fully closed** — this plan changes only CSS classes, and jsdom performs no layout, so the automated tests can pin the classes but cannot prove the Start button is actually visible above the fold and unobstructed by the bottom nav / Feedback FAB on a real device. Per the plan's own verification note, a bare 390x844 DevTools emulation does NOT reproduce the original bug (no URL bar, no safe-area inset) — verification needs a real phone, the installed PWA, or a DevTools emulation with the URL-bar height subtracted and a non-zero safe-area inset.

This is the last of the 171-08/09/10 gap-closure plans from the UAT diagnosis session (`.planning/phases/171-bots-page-setup-screen-nav/171-UAT.md`). All three gaps have code fixes committed; real-device confirmation of gap 3 (this plan) remains outstanding.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All created/modified files exist on disk and all 6 task/metadata commit hashes (`03870e62`, `09116704`, `d498b1a5`, `96d2842f`, `fb3b701a`, `31d74fda`) resolve in `git log`.
