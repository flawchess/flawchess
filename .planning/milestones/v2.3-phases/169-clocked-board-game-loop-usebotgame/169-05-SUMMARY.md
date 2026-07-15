---
phase: 169-clocked-board-game-loop-usebotgame
plan: 05
subsystem: frontend-ui
tags: [react, tailwind, radix-dialog, shadcn, chess-clock, theme]

requires:
  - phase: 169 (plan 01)
    provides: "chessClock.ts pure formatting/threshold helpers (formatClockLabel, isLowTime, LOW_TIME_THRESHOLD_MS)"
  - phase: 169 (plan 04)
    provides: "useBotGame(settings) state contract (whiteClockMs/blackClockMs, isBotThinking, moveHistory, liveGamePly, viewedPly, drawOfferPending, canOfferDraw, resign/offerDraw/viewPly/returnToLive callbacks) these components render"
provides:
  - "ClockDisplay — one side's clock card: tabular-nums digits, active-side --secondary tint, brand-brown thinking dot (D-06), theme-sourced low-time destructive-red urgent state (D-07)"
  - "MoveListPanel — linear SAN move list with a live-ply brand-brown highlight, click + guarded arrow-key view-only scroll-back, and an always-visible Return-to-live-position affordance (D-13)"
  - "GameControls — two-step resign confirm (Dialog), cooldown-throttled draw offer with tooltip, aria-labeled mute toggle (D-04/D-10)"
  - "CLOCK_LOW_TIME_URGENT theme constant (theme.ts)"
affects: [169-06-bots-page-assembly, 170-localstorage-resume]

tech-stack:
  added: []
  patterns:
    - "Presentational-only components consuming useBotGame's state/callbacks directly — no local game logic, no re-derivation of clock/formatting math (all delegated to chessClock.ts)"
    - "HorizontalMoveList's shared shell extended with an optional activeItemClassName override so a caller's design system (brand-brown here) can replace the default bg-primary current-row highlight without touching existing callers (Openings MoveList, TacticLineExplorer)"

key-files:
  created:
    - frontend/src/components/bots/ClockDisplay.tsx
    - frontend/src/components/bots/MoveListPanel.tsx
    - frontend/src/components/bots/GameControls.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/components/board/HorizontalMoveList.tsx

key-decisions:
  - "CLOCK_LOW_TIME_URGENT set to the exact shadcn --destructive oklch value (oklch(0.577 0.245 27.325)) rather than a new hand-picked red, so the urgent clock state reads consistently with the app's other destructive surfaces (resign confirm button)"
  - "Live-ply highlight always tracks liveGamePly, never viewedPly — the UI-SPEC explicitly reserves the brand-brown active-ply tint for the actual game position, not the view-only scroll-back cursor; the board itself (Plan 06/04) is the surface that shows the scrolled-back position"
  - "Extended HorizontalMoveList.tsx with an optional activeItemClassName prop (default unchanged: bg-primary text-primary-foreground hover:bg-primary/90) instead of duplicating the shared shell or hardcoding brand-brown into it — the UI-SPEC requires a brand-brown low-alpha highlight here, which the existing bg-primary (grayscale) default doesn't satisfy; this keeps the Openings MoveList.tsx and TacticLineExplorer callers byte-identical"
  - "GameControls' resign trigger Button is rendered as a sibling of <Dialog>, not nested inside it — Dialog (radix Root) provides no implicit trigger slot without a DialogTrigger export (this codebase's dialog.tsx omits one); mirrors the existing FeedbackButton/FeedbackModal controlled open/onOpenChange split already used elsewhere in the app"
  - "Draw-offer disabled state is drawOfferDisabled = !canOfferDraw || drawCooldownActive — the plan's two separate props (a general accept-gate and the D-04 cooldown) are ORed rather than treated as mutually exclusive, since either alone should disable the button"

requirements-completed: [PLAY-03, PLAY-07, PLAY-08]

coverage:
  - id: D1
    description: "ClockDisplay renders a tabular-nums clock card sourcing all formatting/threshold logic from chessClock.ts, with an active-side tint, a brand-brown thinking dot, and a theme-sourced low-time urgent state"
    requirement: "PLAY-08"
    verification:
      - kind: unit
        ref: "npx tsc -b && npm run lint (frontend/src/components/bots/ClockDisplay.tsx)"
        status: pass
    human_judgment: true
    rationale: "No component test exists for ClockDisplay in this plan (presentational-only, no logic to unit-test beyond the already-tested chessClock.ts helpers it delegates to) — visual states (thinking pulse, low-time red/ring, active tint) need a human/real-device check once Plan 06 assembles the board; tsc+lint prove structural correctness (imports, no reimplemented formatting, no hard-coded color) only."
  - id: D2
    description: "MoveListPanel shows a linear SAN list with a live-ply highlight, click + guarded arrow-key view-only scroll-back, and an always-visible Return-to-live-position affordance"
    requirement: "PLAY-03"
    verification:
      - kind: unit
        ref: "npx tsc -b && npm run lint (frontend/src/components/bots/MoveListPanel.tsx, frontend/src/components/board/HorizontalMoveList.tsx)"
        status: pass
    human_judgment: true
    rationale: "No component test exists for MoveListPanel in this plan — the arrow-key guard and return-to-live conditional rendering are structurally verified via grep + type/lint checks, but the actual scroll-back UX (does the list visually communicate the viewed-vs-live distinction well) needs a human/real-device check once Plan 06 assembles the board."
  - id: D3
    description: "GameControls gives a two-step destructive resign confirm (brand-outline trigger, destructive confirm inside the existing Dialog), a cooldown-disabled draw offer with tooltip, and an aria-labeled mute toggle"
    requirement: "PLAY-07"
    verification:
      - kind: unit
        ref: "npx tsc -b && npm run lint (frontend/src/components/bots/GameControls.tsx)"
        status: pass
    human_judgment: true
    rationale: "No component test exists for GameControls in this plan — button variants/testids/copy are grep-verified against the UI-SPEC Copywriting Contract, but the actual dialog open/close flow and tooltip hover behavior need a human/real-device check once Plan 06 wires it to useBotGame's live resign()/offerDraw() callbacks."

duration: 10min
completed: 2026-07-12
status: complete
---

# Phase 169 Plan 05: Clock/Move-List/Game-Controls UI Summary

**Three presentational components — `ClockDisplay` (tabular-nums clock + thinking dot + low-time urgent), `MoveListPanel` (SAN list + view-only scroll-back), `GameControls` (two-step resign + throttled draw offer + mute) — plus the new `CLOCK_LOW_TIME_URGENT` theme constant, all rendering `useBotGame` state per the 169-UI-SPEC contract.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-12T19:58:20Z
- **Completed:** 2026-07-12T20:07:30Z
- **Tasks:** 3
- **Files modified:** 5 (3 new, 2 modified)

## Accomplishments
- `theme.ts` gains `CLOCK_LOW_TIME_URGENT`, matching the shadcn `--destructive` value exactly so the clock's urgent red is consistent with the app's other destructive surfaces.
- `ClockDisplay.tsx` — single-side clock card (Card bg, 16px padding): side label at text-sm/font-medium, digits at text-xl/font-bold/tabular-nums via `formatClockLabel` (never reimplemented), `--secondary` tint when active, a brand-brown `animate-pulse` thinking dot with an `aria-live` "Bot is thinking" region when `isThinking`, and `CLOCK_LOW_TIME_URGENT` digit color + `ring-2 ring-destructive/40` when `isLowTime(remainingMs)`.
- `MoveListPanel.tsx` — reuses `MoveList.tsx`'s SAN-item mapping (`move-${ply}` testid, ariaLabel) near-verbatim; the live-position row (not the scroll-back cursor) always carries the brand-brown highlight; click and guarded (`INPUT`/`TEXTAREA`/`SELECT`-excluded) `ArrowLeft`/`ArrowRight` step a separate `viewedPly`; a `data-testid="btn-return-live"` link appears whenever `viewedPly !== liveGamePly`.
- `HorizontalMoveList.tsx` gains an optional `activeItemClassName` prop (default unchanged) so `MoveListPanel` can override the current-row highlight with `bg-brand-brown/10` instead of the shared shell's default `bg-primary` — existing callers (`board/MoveList.tsx`, `TacticLineExplorer`) are unaffected.
- `GameControls.tsx` — Resign is `variant="brand-outline"` at rest, opening the existing `ui/dialog` `Dialog` with the exact UI-SPEC copy ("Resign this game?" / "You'll lose this game against the bot.") whose confirm button is `variant="destructive"`; Offer draw is `brand-outline`, disabled (with the cooldown `Tooltip`) when `!canOfferDraw || drawCooldownActive`; Mute is an icon-only `ghost` Button swapping `Volume2`/`VolumeX` with the matching `aria-label`. All three actions carry the spec'd `data-testid`s.

## Task Commits

Each task was committed atomically:

1. **Task 1: theme.ts CLOCK_LOW_TIME_URGENT + ClockDisplay (D-06/D-07)** - `16c58d9f` (feat)
2. **Task 2: MoveListPanel — linear SAN list + view-only scroll-back (D-13, PLAY-03)** - `71722c83` (feat)
3. **Task 3: GameControls — resign confirm, throttled draw offer, mute toggle (D-04/D-10, PLAY-07/08)** - `d28f4700` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/lib/theme.ts` - new `CLOCK_LOW_TIME_URGENT` constant
- `frontend/src/components/bots/ClockDisplay.tsx` - single-side clock card
- `frontend/src/components/bots/MoveListPanel.tsx` - linear SAN move list + view-only scroll-back
- `frontend/src/components/board/HorizontalMoveList.tsx` - additive `activeItemClassName` override prop
- `frontend/src/components/bots/GameControls.tsx` - resign/draw/mute control row

## Decisions Made
- `CLOCK_LOW_TIME_URGENT` matches the shadcn `--destructive` oklch value exactly, not a new hand-picked red.
- The live-ply highlight always tracks `liveGamePly`, never `viewedPly`, per the UI-SPEC's explicit "actual current game position, not the scroll-back cursor" wording.
- `HorizontalMoveList.tsx` extended with an optional `activeItemClassName` override (default preserved) rather than duplicating the shared shell, since its hardcoded `bg-primary` default doesn't satisfy the UI-SPEC's brand-brown requirement here.
- `GameControls`'s resign trigger Button is a sibling of `<Dialog>`, not nested inside it, mirroring the existing `FeedbackButton`/`FeedbackModal` controlled `open`/`onOpenChange` split (this codebase's `dialog.tsx` has no `DialogTrigger` export).
- `drawOfferDisabled = !canOfferDraw || drawCooldownActive` — the two plan props are ORed, not treated as mutually exclusive.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `HorizontalMoveList.tsx`'s hardcoded `bg-primary` current-row style doesn't satisfy the UI-SPEC's brand-brown active-ply highlight requirement**
- **Found during:** Task 2 (MoveListPanel)
- **Issue:** The plan told me to reuse `HorizontalMoveList`'s shared item renderer "near-verbatim," but the UI-SPEC explicitly requires the live-ply row to get a brand-brown low-alpha tint (`bg-brand-brown/10`), while the shared component's `isCurrent` styling is hardcoded to the grayscale `bg-primary`/`text-primary-foreground`. Using it unmodified would have shipped the wrong highlight color, contradicting a stated UI-SPEC requirement (CLAUDE.md theme-constant/semantic-color rule).
- **Fix:** Added an optional `activeItemClassName` prop to `HorizontalMoveListProps` (default `'bg-primary text-primary-foreground hover:bg-primary/90'`, i.e. byte-identical to the prior hardcoded behavior for every existing caller), and pass `activeItemClassName="bg-brand-brown/10 text-foreground hover:bg-brand-brown/15"` from `MoveListPanel`.
- **Files modified:** frontend/src/components/board/HorizontalMoveList.tsx, frontend/src/components/bots/MoveListPanel.tsx
- **Verification:** `npx tsc -b && npm run lint` clean; existing `board/MoveList.tsx` and any `TacticLineExplorer` callers pass no `activeItemClassName`, so their rendered classes are unchanged.
- **Committed in:** 71722c83 (Task 2 commit)

**2. [Rule 3 - Blocking] `dialog.tsx` has no `DialogTrigger` export**
- **Found during:** Task 3 (GameControls)
- **Issue:** The plan's action text implied a conventional `<Dialog><Trigger/><Content/></Dialog>` composition, but this codebase's `components/ui/dialog.tsx` only exports `Dialog`/`DialogContent`/`DialogHeader`/`DialogFooter`/`DialogTitle`/`DialogDescription` — no `DialogTrigger`. Nesting a plain `Button` inside `<Dialog>` alongside `<DialogContent>` would not render a working trigger (Radix's `Dialog.Root` provides only context, not implicit trigger wiring for arbitrary children).
- **Fix:** Rendered the resign trigger `Button` as a sibling of `<Dialog open={...} onOpenChange={...}>`, controlling `open` via local `useState` — the same controlled-dialog pattern this codebase already uses for `FeedbackButton`/`FeedbackModal`.
- **Files modified:** frontend/src/components/bots/GameControls.tsx
- **Verification:** `npx tsc -b && npm run lint` clean.
- **Committed in:** d28f4700 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking).
**Impact on plan:** Both fixes were necessary for the plan's own stated UI-SPEC requirements (brand-brown highlight) and for the component to actually function (Dialog trigger wiring) — no scope creep beyond what Task 2/3's own acceptance criteria demanded.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All three components' prop contracts (`sideLabel`/`remainingMs`/`isActive`/`isThinking` for `ClockDisplay`; `moveHistory`/`liveGamePly`/`viewedPly`/`onViewPly`/`onReturnToLive` for `MoveListPanel`; `canOfferDraw`/`drawCooldownActive`/`muted`/`onResignConfirmed`/`onOfferDraw`/`onToggleMute` for `GameControls`) match the plan's artifact contract exactly and map 1:1 onto `useBotGame`'s (Plan 04) state/callback shape — Plan 06 (`Bots.tsx` assembly) can wire them directly with no adapter layer.
- No frozen engine file was touched; only `theme.ts`, the three new `components/bots/*` files, and the additive `HorizontalMoveList.tsx` extension.
- Coverage gaps flagged in this SUMMARY's `coverage:` block (`human_judgment: true` on all three deliverables) are the expected shape for a purely presentational plan with no unit-test task — the real functional/visual verification (thinking pulse, low-time red/ring, scroll-back UX, resign dialog flow, draw-offer tooltip, mute swap) happens once Plan 06 assembles `Bots.tsx` and wires these to the live hook, at end-of-phase human-verify UAT.

## Self-Check: PASSED

- `[ -f frontend/src/components/bots/ClockDisplay.tsx ]` → FOUND
- `[ -f frontend/src/components/bots/MoveListPanel.tsx ]` → FOUND
- `[ -f frontend/src/components/bots/GameControls.tsx ]` → FOUND
- `[ -f frontend/src/lib/theme.ts ]` → FOUND (modified)
- `[ -f frontend/src/components/board/HorizontalMoveList.tsx ]` → FOUND (modified)
- `git log --oneline --all | grep -E "16c58d9f|71722c83|d28f4700"` → all three commits FOUND
- Acceptance criteria re-verified for all three tasks (grep checks for `CLOCK_LOW_TIME_URGENT`, `formatClockLabel`/`isLowTime` imports, no `text-xs`, no hard-coded low-time color literal, `tabular-nums`, `move-${ply}` testid, `btn-return-live`, arrow-key `INPUT`/`TEXTAREA`/`SELECT` guard, `brand-outline`/`destructive` variants, all `board-btn-*` testids, verbatim resign copy) — all PASS.
- Plan-level verification re-run: `cd frontend && npx tsc -b` clean; `npm run lint` clean (only pre-existing unrelated `coverage/` generated-file warnings).
- `git diff --name-only` across all three task commits shows only `frontend/src/lib/theme.ts`, `frontend/src/components/bots/ClockDisplay.tsx`, `frontend/src/components/bots/MoveListPanel.tsx`, `frontend/src/components/board/HorizontalMoveList.tsx`, `frontend/src/components/bots/GameControls.tsx` — no frozen engine file touched.

---
*Phase: 169-clocked-board-game-loop-usebotgame*
*Completed: 2026-07-12*
