---
id: 260411-p1c
description: Prototype Option A mobile layout for Opening Explorer
date: 2026-04-11
branch: quick-260411-p1c-mobile-option-a
status: ready-for-visual-review
---

# Quick Task 260411-p1c: Option A Mobile Layout Prototype

## Goal

Restructure the mobile view of the Opening Explorer (`/openings/*` routes on `<lg` breakpoints) so that the board-WDL fold lifts far enough up that users can play a move on the board and see the resulting candidate-move WDL bars without scrolling.

## What Changed

### Sticky header — before

```
┌─────────────────────────┐
│                         │
│        CHESSBOARD       │ [↺]  ← board-controls column (5 × 44px)
│                         │ [<]
│                         │ [>]
│                         │ [⟲]
│                         │ [i]
└─────────────────────────┘
[ Moves | Games | Stats ] [♔] [Bm] [Fi]   ← 44px tab row + 3 settings btns
[═════════════  ⌄  ═════════════]          ← 44px chevron handle bar
```

### Sticky header — after (Option A)

```
┌─────────────────────────┐
│                         │
│        CHESSBOARD       │ [♔]  ← settings column (4 × 44px)
│                         │ [Bm]
│                         │ [Fi]
│                         │ [i]
└─────────────────────────┘
[↺][<][>][⟲] │ Moves · Games · Stats │ [⌄]   ← 36px slim row
```

**Net vertical reclaim:** ~44px (one row removed). The old 44px chevron-handle bar is gone; its collapse affordance is now a 36×36 button at the right end of the slim row. The tab row + controls are consolidated into one slim row at 36px instead of two rows at 44px.

## Files Touched

| File | Change |
|---|---|
| `frontend/src/components/ui/tabs.tsx` | New `variant="underline"` — text-only trigger with 2px active bottom border, no pill background. Does not affect the existing `brand` variant (still used on desktop). |
| `frontend/src/components/board/BoardControls.tsx` | New `size?: 'sm' \| 'md' \| 'lg'` prop. `sm = h-8 w-8` (desktop default), `md = h-9 w-9` (mobile slim row), `lg = h-11 w-11` (mobile vertical column default). Default resolves from `vertical` for backwards compatibility — all existing callsites unchanged. |
| `frontend/src/pages/Openings.tsx` | Mobile `lg:hidden` block (lines 1185-1332) rewritten. Settings column now holds played-as/bookmarks/filters/info. Slim row now holds BoardControls + underline Tabs + collapse chevron. Desktop `SidebarLayout` branch (lines 1030-1182) untouched. All notification-dot logic, data-testids, and `handleHandleTouchStart/End` swipe handlers preserved on the new collapse button. |

## Commits

- `0fb3414` — feat(quick-260411-p1c): add underline Tabs variant and size prop on BoardControls
- `b5b0c31` — feat(quick-260411-p1c): restructure Openings mobile layout (Option A prototype)

Both commits are on branch `quick-260411-p1c-mobile-option-a` (fast-forwarded from `main`).

## Verification

- `npm run build` — zero TS errors, prerender OK
- `npm run lint` — zero issues
- `npm run knip` — no dead exports / unused deps
- Desktop view (`lg:` and above) confirmed byte-identical — all diff hunks are inside the `lg:hidden` mobile block
- All required `data-testid` attributes preserved; `openings-mobile-settings-column` added per convention
- **Visual verification: PENDING** — user should open the dev server at http://localhost:5173/openings/explorer in a mobile viewport (DevTools responsive mode, ~375×800) to confirm the new layout feels right. Browser automation wasn't available to run it automatically.

## Known Concerns to Check During Visual Review

1. **36px touch targets** for Reset/Back/Fwd/Flip/Chevron and the underline tab triggers. Below the 44px "comfortable tap" guideline. Acceptable for muscle-memory controls but verify on a real phone — if thumbs miss, bump BoardControls to `size="lg"` (44px) and accept the vertical cost.
2. **BoardControls container** still uses `charcoal-texture rounded-lg` in horizontal `size="md"` mode. May look like a filled pill next to the text-only underline tabs. If it clashes visually, either (a) remove the texture/radius when `size === 'md'`, or (b) override via `className` prop from the callsite.
3. **Collapse chevron discoverability** — much smaller than the old full-width handle bar. Swipe-to-collapse still works on the chevron button but the affordance is less obvious. If users don't discover it, consider binding the swipe handlers to the entire slim row instead of just the chevron.

## Out of Scope (for future quick tasks)

- Keep the MoveList visible when the board is collapsed (addresses issue #2 from the original feedback)
- Auto-collapse on downward scroll / expand on upward scroll
- Compacting the `WDLChartRow` "Position Results played as White" header text on mobile
- Extracting the `!bg-toggle-active text-toggle-active-foreground` styling on the 3 settings buttons into a proper Button variant

## Next Step

Reload http://localhost:5173/openings/explorer in a mobile-width browser and eyeball the layout. If the three concerns above hold up, the prototype is a straight win. If not, each is a small targeted tweak from here.
