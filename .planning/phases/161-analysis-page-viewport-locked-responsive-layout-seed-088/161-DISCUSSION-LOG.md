# Phase 161: Analysis page viewport-locked responsive layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 161-analysis-page-viewport-locked-responsive-layout-seed-088
**Areas discussed:** Breakpoint strategy, Board size ceiling, Short-screen fallback, Threshold target

---

## Breakpoint strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Raise threshold, hard stack | Bump 3-column to a higher breakpoint; below it fall straight to the mobile stack. No intermediate UI. | ✓ |
| Staged collapse (chess.com) | Intermediate stage with narrower / icon-collapsed side columns before dropping to the stack. | |
| Fluid side columns | Keep 3-column from lg but make side columns fluid (clamp/minmax) instead of fixed 360px. | |

**User's choice:** Raise threshold, hard stack
**Notes:** No intermediate staged-collapse. Simplest — one breakpoint move.

---

## Board size ceiling

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 600px | Board only shrinks (to ~420) on short screens, never grows past today's 600px. | ✓ |
| Grow past 600 (chess.com) | Board grows to fill height on tall/large screens, capped only by middle-column width. | |

**User's choice:** Cap at 600px
**Notes:** `clamp(420, min(widthBudget, heightBudget), 600)`. Avoids the board dominating large monitors.

---

## Short-screen fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Strict lock, inner scroll | Always 100dvh-locked on lg+; once the board floors, the middle column scrolls internally. | |
| Page-scroll below min height | Viewport-lock only while it fits; below ~560px height, release the lock and let the page scroll. | ✓ |

**User's choice:** Page-scroll below min height
**Notes:** Refines the seed's "always locked" — adds a safety valve for extreme-short windows (two behavior modes).

---

## Threshold target (follow-up: keep the reported small laptop in desktop layout)

| Option | Description | Selected |
|--------|-------------|----------|
| As low as viable (~1200) | Threshold near the minimum where 3 columns still fit with the fluid board; keeps 1280/1366 laptops in desktop. | ✓ |
| I'll give the exact width | User supplies the reported laptop's viewport width; threshold set just below it. | |
| Planner decides from math | Defer exact px to planning; lock only the intent (small laptops stay desktop). | |

**User's choice:** As low as viable (~1200)
**Notes:** Raised by Claude — a threshold set too high (~1300) would push the reported small laptop into the mobile stack, which is worse than the bug being fixed. Because the middle board is now fluid, 3-column stays viable down to ~1190px. Intent locked: small laptops stay desktop, board shrinks fluidly.

---

## Claude's Discretion

- Exact breakpoint px for the ~1200 threshold (must keep 1280/1366 laptops in desktop).
- Exact min-height px for the page-scroll fallback (~560 working figure).
- Height-budget accounting (nav / player rows / eval chart / gaps → board `heightBudget`) — seed open item #2.
- Mechanism for making ChessBoard height-aware (JS measurement vs. CSS `min()`/`clamp()`).

## Deferred Ideas

- Top-bar → left-sidebar nav (~40px height reclaim) — touches the global shell, its own phase.
- Intermediate staged-collapse stage — considered and rejected for this phase; could revisit if hard-stack proves too coarse.
