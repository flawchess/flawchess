---
phase: 50
plan: 01
subsystem: frontend/openings-mobile
tags: [mobile, layout, openings, sticky-header, backdrop-blur, touch-targets]
requirements: [MMOB-01]
dependency_graph:
  requires:
    - frontend/src/components/board/BoardControls.tsx (existing vertical prop)
    - frontend/src/components/layout/SidebarLayout.tsx (visual reference only, unchanged)
    - Existing state in Openings.tsx (boardCollapsed, filters, bookmarks, drawer handlers)
  provides:
    - Openings mobile unified control row (data-testid="openings-mobile-control-row")
    - BoardControls conditional vertical button sizing (h-12 w-12 when vertical)
  affects:
    - frontend/src/pages/Openings.tsx (md:hidden branch only)
    - frontend/src/components/board/BoardControls.tsx (all 4 rendered buttons)
tech_stack:
  added: []
  patterns:
    - bg-background/80 backdrop-blur-md (adopted from desktop SidebarLayout)
    - Conditional button sizing via template literal on vertical prop
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/board/BoardControls.tsx
decisions:
  - "Unified control row sits outside the grid-rows collapse region so it stays visible when board is collapsed (D-03)"
  - "Left-to-right order: Tabs | Color | Bookmark | Filter (D-02)"
  - "Info popover stays inside BoardControls.infoSlot in the vertical column (not relocated)"
  - "Plain flex TabsList, no overflow-x-auto, no carousel (D-04)"
metrics:
  duration: ~15m
  completed: 2026-04-10
---

# Phase 50 Plan 01: Restructure Openings Mobile Sticky Wrapper Summary

Delivers MMOB-01 by lifting the Moves/Games/Stats subtabs, color toggle, bookmark button, and filter button into a single unified control row that sits outside the board collapse region — so collapsing the board no longer hides those four controls. Sticky wrapper adopts translucent backdrop-blur, vertical board-action column shrinks from 8 to 5 items with enlarged touch targets, collapse handle bumped from a ~4px sliver to a 44px tappable strip.

## What Changed

### `frontend/src/components/board/BoardControls.tsx`

Replaced the hardcoded `h-8 w-8 hover:bg-accent` className on all 4 rendered buttons (Reset, Back, Forward, Flip) with a template literal that switches on the existing `vertical` prop:

```tsx
className={`${vertical ? 'h-12 w-12' : 'h-8 w-8'} hover:bg-accent`}
```

Desktop horizontal usage keeps the original 32×32 sizing (vertical omitted or false). Mobile vertical usage grows to 48×48 — larger than the 44px touch-target minimum. Icons stay `h-4 w-4`. No other changes to the file; no prop added; no import changes.

### `frontend/src/pages/Openings.tsx` (md:hidden branch only)

Restructured the sticky top wrapper subtree into three direct siblings of the sticky div:

1. **Collapsible board region** — unchanged `grid transition-[grid-template-rows]` mechanism, but now contains only the board + a 5-item vertical column holding `<BoardControls vertical>` with the InfoPopover as its `infoSlot`. The old inner `<div className="mt-1 flex flex-col gap-1">` wrapper holding color/filter/bookmark triggers was removed from this column.
2. **Unified control row** (new, `data-testid="openings-mobile-control-row"`) — `<div className="flex items-center gap-2 h-11 px-1 mt-1">` containing `TabsList` (flex-1 h-full) + color toggle (h-11 w-11 shrink-0) + bookmark button (h-11 w-11 shrink-0) + filter button (h-11 w-11 shrink-0). Left-to-right order exactly matches UI-SPEC D-02.
3. **Collapse handle** — enlarged from `py-0.5` sliver (~4px) to `h-11` (44px) with `bg-white/5 border-t border-white/10`, `h-5 w-5` ChevronDown. Touch handlers, onClick, aria-label, data-testid unchanged.

Sticky wrapper className changed from `sticky top-0 z-20 bg-background shadow-[0_6px_20px_rgba(0,0,0,0.8)]` to `sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border` — matching the desktop `SidebarLayout` panel pattern. No other file or branch touched.

## Key Decisions Implemented

| Decision ID | Implementation |
|-------------|----------------|
| D-01 | Color toggle + bookmark + filter buttons lifted from vertical column into unified row |
| D-02 | Row order: Tabs \| Color \| Bookmark \| Filter |
| D-03 | Unified row placed OUTSIDE the grid-rows collapse region, inside the sticky wrapper — stays visible when board is collapsed |
| D-04 | Plain flex `TabsList`; no `overflow-x-auto`, no carousel |
| D-06 | Vertical board-action column shrunk to 5 items (Reset, Back, Forward, Flip, Info) via `BoardControls` |
| D-07 | Vertical column `w-12` (48px) with `gap-1` between items — same width as current, buttons grow from h-8 to h-12 |
| D-08 | Sticky wrapper uses `bg-background/80 backdrop-blur-md` matching `SidebarLayout.tsx:112` |
| D-09 | Old `shadow-[0_6px_20px_rgba(0,0,0,0.8)]` removed; replaced with `border-b border-border` |
| D-11 | Collapse handle position unchanged (bottom of sticky region) |
| D-12 | Collapse handle enlarged to `h-11` (44px) with `h-5 w-5` ChevronDown |
| D-15, D-16, D-17, D-18, D-19 | Scope limits respected: no filter/bookmark panel content changes, no drawer changes, no MobileBottomBar changes, no desktop changes, no Games subtab content changes |

**Info popover:** stayed inside `BoardControls.infoSlot` in the vertical column per UI-SPEC's explicit "stay in the vertical column" decision. Not relocated.

## Preserved data-testid Audit

Grep counts on `frontend/src/pages/Openings.tsx` (each expected exactly 1):

| data-testid | count |
|-------------|-------|
| `openings-mobile-control-row` (new) | 1 |
| `openings-tabs-mobile` | 1 |
| `tab-move-explorer-mobile` | 1 |
| `tab-games-mobile` | 1 |
| `tab-stats-mobile` | 1 |
| `btn-toggle-played-as` | 1 |
| `btn-open-bookmark-sidebar` | 1 |
| `btn-open-filter-sidebar` | 1 |
| `bookmarks-notification-dot-mobile` | 1 |
| `filters-notification-dot-mobile` | 1 |
| `btn-board-collapse-handle` | 1 |
| `chessboard-info-mobile` (as InfoPopover testId prop) | 1 |

All 11 preserved testids present exactly once; the new `openings-mobile-control-row` added.

## Structural Validation (from final read of lines 912-1037)

- Sticky wrapper (line 916) has exactly 3 direct-child siblings: collapse grid (line 918), unified control row (line 954), collapse handle (line 1027).
- Unified row (line 954) is NOT nested inside the `grid transition-[grid-template-rows]` element — confirmed by JSX indentation.
- Vertical board-action column (line 931) contains ONLY `<BoardControls vertical …/>` — no Tooltip-wrapped trigger buttons inside.
- When `boardCollapsed === true` the unified row and collapse handle remain rendered because they are siblings of the collapse grid, not descendants. Phase 50's core ergonomic win verified by inspection.

## Deviations from Plan

None. The plan executed exactly as written. Every JSX block matches the UI-SPEC Interaction Contract and the Task 2 Action section verbatim. No auto-fixes were applied. No architectural surprises. No authentication gates. No pre-existing unrelated warnings surfaced.

## Verification Output

### Tooling gates (all exit 0)

```
$ cd frontend && npm run lint
> frontend@0.0.0 lint
> eslint .
(no output — clean)
exit=0

$ cd frontend && npx tsc --noEmit
(no output — clean)
exit=0

$ cd frontend && npm run knip
> frontend@0.0.0 knip
> knip
(no output — no dead exports)
exit=0
```

### Frontend tests

```
$ cd frontend && npm test
Test Files  5 passed (5)
     Tests  73 passed (73)
  Duration  167ms
exit=0
```

### Diff scope

```
$ git diff --stat main... -- frontend/src/pages/Openings.tsx frontend/src/components/board/BoardControls.tsx
 frontend/src/components/board/BoardControls.tsx | 8 ++--
 frontend/src/pages/Openings.tsx | 158 +++++++++++++---------
```

Only the two files in scope were modified. No other frontend file touched.

### Desktop `hidden md:` branches untouched

```
$ git diff HEAD~2 HEAD -- frontend/src/pages/Openings.tsx | grep -E '^[+-]' | grep 'hidden md:' | wc -l
0
```

Zero added or removed lines containing `hidden md:` — desktop branches byte-identical to pre-change state.

### Structural grep checks (Task 2 acceptance criteria, all pass)

```
data-testid="openings-mobile-control-row"                      : 1
className="flex items-center gap-2 h-11 px-1 mt-1"             : 1
className="flex-1 h-full" data-testid="openings-tabs-mobile"   : 1
sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b   : 1
shadow-[0_6px_20px                                             : 0 (removed)
sticky top-0 z-20 bg-background shadow                         : 0 (removed)
flex flex-col gap-1 w-12                                       : 1
mt-1 flex flex-col gap-1                                       : 0 (removed)
h-11 w-11 shrink-0                                             : 3 (color, bookmark, filter)
h-9 w-9 !bg-toggle-active                                      : 0 (removed)
h-9 w-9 bg-toggle-active                                       : 0 (removed)
overflow-x-auto                                                : 0
py-0.5 touch-none bg-white/15                                  : 0 (removed)
h-11 touch-none bg-white/5 border-t border-white/10            : 1
```

### BoardControls checks (Task 1 acceptance criteria, all pass)

```
vertical ? 'h-12 w-12' : 'h-8 w-8'   : 4 (one per button)
h-8 w-8 hover:bg-accent (hardcoded)  : 0
h-4 w-4 (icon sizes)                 : 4 (unchanged)
data-testid="board-btn-               : 4 (all preserved)
{infoSlot}                            : 1 (unchanged)
```

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `3b30786` | `feat(50-01): add conditional vertical button sizing to BoardControls` |
| 2 | `3bef00a` | `feat(50-01): restructure Openings mobile sticky wrapper with unified control row` |

## Success Criteria Check

- [x] BoardControls.tsx renders buttons at `h-12 w-12` when `vertical` is true and `h-8 w-8` otherwise.
- [x] Openings.tsx mobile sticky wrapper restructured per UI-SPEC with unified control row outside the collapse grid.
- [x] All 11 preserved data-testid values appear exactly once in the file.
- [x] New `openings-mobile-control-row` testid present exactly once.
- [x] No `shadow-[0_6px_20px_rgba(0,0,0,0.8)]` remains in the file.
- [x] No `overflow-x-auto` introduced anywhere in Openings.tsx.
- [x] Desktop `hidden md:` branches byte-identical to pre-change state (git diff confirms).
- [x] `npm run lint && npx tsc --noEmit && npm run knip` all exit 0.
- [x] MMOB-01 satisfied: subtabs relocated out of the board collapse region into a unified control row that stays visible when the board collapses.

## Known Stubs

None. No placeholder components, no hardcoded empty arrays or stub text. All data flows unchanged from pre-change state — the plan only relocates and restyles existing, wired-up controls.

## Self-Check: PASSED

- FOUND: `frontend/src/components/board/BoardControls.tsx`
- FOUND: `frontend/src/pages/Openings.tsx`
- FOUND: `.planning/phases/50-mobile-layout-restructuring/50-01-SUMMARY.md`
- FOUND: commit `3b30786` (Task 1)
- FOUND: commit `3bef00a` (Task 2)
