# Phase 19: Mobile UX Polish + Install Prompt - Research

**Researched:** 2026-03-20
**Domain:** React mobile UX, touch events, PWA install prompts, CSS sticky positioning
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hide `MobileHeader` on the Openings page only — other pages keep the header for context
- Chessboard sticks to top of viewport on mobile (sticky positioning)
- Below the sticky board: board controls, then compact move list, then collapsible filters section, then Moves/Games/Statistics tabs with scrollable content
- Filters collapsed by default on mobile, expandable via accordion/collapsible
- Position bookmarks remain as a collapsed accordion section below filters (same pattern as now)
- Save/Suggestions buttons stay inline within the bookmarks section
- Try to fix drag-and-drop on touch devices (reversal of Phase 17 decision to disable drag) — investigate react-chessboard v5 touch support
- Fix click-to-move: tapping a square should trigger `onSquareClick` — currently not firing on touch devices
- Selected piece feedback: yellow highlight (existing `rgba(255, 255, 0, 0.5)` logic) — no additional legal move indicators needed
- If drag-and-drop fix proves infeasible, fall back to disabling drag on touch and relying on click-to-move only
- Fix-as-you-go approach: address 44px touch targets and overflow issues on each page while working on other Phase 19 tasks
- No separate audit pass — fix what's encountered during chessboard and layout work
- Filter controls (toggle groups, selects): increase tap target height to min 44px on mobile, keep inline/wrapping layout (not vertical stacking)
- Baseline test width: 375px (iPhone SE)

### Claude's Discretion
- Exact sticky positioning CSS approach (sticky vs fixed + offset)
- How to conditionally hide MobileHeader on Openings page (route check vs prop)
- react-chessboard drag-and-drop fix approach — investigate what causes the black screen
- Which specific elements need 44px adjustments (discovered during implementation)
- Overflow fix specifics per component

### Deferred Ideas (OUT OF SCOPE)
- Install prompts (PWA-04, PWA-05) — In scope for Phase 19 but discussion deferred until after user tests chessboard and layout fixes
- Action buttons in Openings tab — User wants to discuss layout of action buttons after testing the mobile layout changes
- Legal move indicators on mobile — Showing dots on legal destination squares when piece is selected; decided against for now but could revisit
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | All interactive elements (buttons, filters, controls) meet 44x44px minimum touch target | Tailwind `min-h-11` pattern; shadcn Button size="icon" is 36px by default and needs override |
| UX-02 | No page shows horizontal scroll at 375px viewport width | GlobalStats uses `p-6` without `max-w` cap + `overflow-x-hidden` on body; filter buttons use `py-0.5` which creates sub-44px targets |
| UX-03 | Chessboard drag-and-drop and click-to-click moves work correctly on mobile devices | react-chessboard v5.10.0 includes TouchSensor natively; `onSquareClick` has onTouchEnd handling but calls `e.preventDefault()` — need investigation |
| UX-04 | Sidebar (chessboard + filters) and main content (Moves/Games/Statistics) are both usable on mobile without excessive scrolling | Sticky board requires `sticky top-0 z-10` with correct scroll container; MobileHeader hide via `useLocation` route check |
| PWA-04 | User sees an in-app install prompt on Chromium browsers after engagement | `beforeinstallprompt` event; deferred to post-testing discussion |
| PWA-05 | iOS users see manual "Add to Home Screen" instructions since beforeinstallprompt is unavailable | Detect standalone mode + iOS UA; deferred to post-testing discussion |
</phase_requirements>

---

## Summary

Phase 19 is a pure frontend polish phase targeting mobile UX on an existing React 19 + Tailwind CSS 4 app. The three core technical problems are: (1) react-chessboard v5 touch interaction, (2) Openings page mobile layout with sticky board, and (3) 44px touch targets and horizontal overflow fixes across pages.

react-chessboard v5.10.0 (installed) uses `@dnd-kit` internally, which includes a `TouchSensor` — meaning drag-and-drop touch support is already in the library's sensor stack. The "black screen" issue previously encountered is likely from the `DragOverlay` component rendering with `position: fixed; touchAction: none` which can freeze the viewport on some browsers. The `onSquareClick` handler in v5.10.0 has explicit `onTouchEnd` handling that calls `e.preventDefault()` before firing the callback — this should prevent ghost-click double-firing. Whether `onSquareClick` currently fires on touch requires physical device testing, but the code path exists.

The Openings page sticky board layout requires hiding `MobileHeader` on the openings route (to recover screen space), making the board `sticky top-0 z-10`, and reordering the mobile single-column content as: board → board controls → move list → collapsed filters → tabs. The PWA install prompt tasks (PWA-04, PWA-05) are deferred until after the user tests the UX fixes.

**Primary recommendation:** Start with the chessboard touch fix (highest user impact, unblocks testing), then Openings sticky layout, then fix-as-you-go touch targets and overflow.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-chessboard | 5.10.0 | Chessboard with touch/drag | Already installed; v5 uses @dnd-kit with TouchSensor |
| Tailwind CSS | 4.2.x | Utility-first responsive CSS | Already installed; `sm:` breakpoint at 640px established |
| shadcn/ui (Radix) | 1.4.3 | Collapsible, Button, ToggleGroup | Already installed; Collapsible pattern already used |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-router-dom | 7.13.x | `useLocation` for route detection | Hide MobileHeader on `/openings` routes |
| vite-plugin-pwa | 1.2.0 | PWA hooks (workbox) | Already configured; `beforeinstallprompt` handling is plain JS |

### No New Dependencies Needed
All required functionality is achievable with installed packages. No new npm installs for this phase.

---

## Architecture Patterns

### Recommended Mobile Layout Order (Openings Page)

```
Mobile single-column (md:hidden):
├── [MobileHeader HIDDEN on /openings/*]
├── sticky board wrapper (sticky top-0 z-10 bg-background)
│   └── ChessBoard component
├── BoardControls
├── MoveList (compact, fixed height h-18)
├── Collapsible: "More filters" (collapsed by default on mobile)
│   └── FilterPanel
├── Collapsible: "Position bookmarks" (collapsed by default on mobile)
│   └── PositionBookmarkList + Save/Suggest buttons
└── Tabs: Moves | Games | Statistics
    └── Tab content (scrollable)
```

### Pattern 1: Hide MobileHeader on Openings Route

Use `useLocation` inside `ProtectedLayout` to conditionally suppress `MobileHeader`:

```typescript
// In App.tsx ProtectedLayout
function ProtectedLayout() {
  const { token } = useAuth();
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const isOpenings = location.pathname.startsWith('/openings');

  if (!token) return <Navigate to="/login" replace />;
  return (
    <>
      <NavHeader />
      {!isOpenings && <MobileHeader />}
      <main className={cn('pb-16 sm:pb-0', isOpenings && 'sm:pt-0')}>
        <Outlet />
      </main>
      <MobileBottomBar onMoreClick={() => setMoreOpen(true)} />
      <MobileMoreDrawer open={moreOpen} onOpenChange={setMoreOpen} />
    </>
  );
}
```

**Why route check in ProtectedLayout vs prop:** `ProtectedLayout` already uses `useLocation` indirectly through child components and doesn't need a prop threading. Route check is self-contained and keeps `OpeningsPage` unaware of header suppression.

### Pattern 2: Sticky Board on Mobile

The board must stick to the top of the **viewport** (not scroll container) as the user scrolls the page content below it:

```typescript
// In Openings.tsx mobile section — wrap ChessBoard
<div className="sticky top-0 z-10 bg-background pt-2">
  <ChessBoard ... />
</div>
```

**Critical constraint:** `sticky` only works if no ancestor has `overflow: hidden` or `overflow: auto`. The current `<main>` in App.tsx does not have overflow set — `sticky` will work. The Openings `<main>` wrapper uses `min-h-0 flex-1 flex-col` with no overflow — also fine.

**Bottom bar clearance:** The mobile bottom bar is `fixed bottom-0` with `pb-safe`. Sticky board at `top-0` needs no offset on the mobile breakpoint since MobileHeader is hidden on openings. On non-openings pages with MobileHeader (~53px), sticky is not applied.

### Pattern 3: 44px Touch Targets

Apple HIG and WCAG 2.5.5 specify 44x44px minimum. Current violations discovered in code review:

| Element | Current Size | Fix |
|---------|-------------|-----|
| FilterPanel time control buttons | `py-0.5` (~24px height) | `min-h-11 py-2` on mobile |
| FilterPanel platform buttons | `py-0.5` (~24px height) | `min-h-11 py-2` on mobile |
| Board control buttons (size="icon") | shadcn default 36px | Add `sm:size-icon size-11` or `className="h-11 w-11 sm:h-9 sm:w-9"` |
| ToggleGroupItem (size="sm") | ~32px height | Add `min-h-11 sm:min-h-0` |
| MoveList move buttons | `py-0.5` (~24px) | These are compact by design; keep as-is since they're not primary controls |

**Pattern:** Use Tailwind responsive modifier to apply 44px only on mobile:
```typescript
className="min-h-11 sm:min-h-8 px-2 py-2 sm:py-0.5"
```

### Pattern 4: Horizontal Overflow Fix

At 375px viewport, potential overflow sources:

| Page | Issue | Fix |
|------|-------|-----|
| GlobalStats | `p-6` = 24px padding each side, leaves 327px for content | Add `overflow-x-hidden` or reduce to `px-4` |
| FilterPanel ToggleGroups | Longer labels may overflow | Already `flex-wrap gap-1` — should be fine |
| MoveExplorer table/grid | Unknown — investigate | Use `overflow-x-auto` wrapper if needed |
| ChessBoard | `boardWidth` capped at `containerWidth` | Already responsive via ResizeObserver |

Global safety net: Add `overflow-x: hidden` to `body` in `index.css` — prevents all horizontal scroll without hiding intentional scroll areas (since body scroll is never intentional horizontally).

### Pattern 5: react-chessboard Touch Interaction

**What the library does (v5.10.0, verified from dist source):**

1. Uses `@dnd-kit` with `TouchSensor`, `MouseSensor`, `KeyboardSensor`, and `RightClickCancelSensor`
2. `onSquareClick` is handled via both `onClick` (mouse) and `onTouchEnd` (touch) on each square
3. On `onTouchEnd`, it calls `e.preventDefault()` to prevent double-fire, then fires `onSquareClick` if `isTouchEndWithinSquare` is true
4. The `DragOverlay` renders pieces during drag with `position: fixed; touchAction: none`

**The "black screen" issue:** The `DragOverlay` with `touchAction: none` on the dragging piece prevents default touch scroll behavior globally during a drag. On some Android Chrome versions, this causes a visual artifact (black flash or frozen frame) if the browser compositor gets confused. This is a known @dnd-kit issue with `DragOverlay` on mobile.

**Fix strategy (in order of preference):**
1. Test if touch drag works acceptably in current v5.10.0 — the library explicitly lists "Mobile support" as a feature
2. If black screen persists, set `allowDragging: false` on the `Chessboard` options to disable drag entirely and rely solely on click-to-move (which uses `onTouchEnd` and should work)
3. Do NOT set `allowDragging` conditionally based on JS touch detection — use the prop directly in options

**Click-to-move:** The `onSquareClick` with `onTouchEnd` handling is in the library. The reported issue "onSquareClick not firing on touch" may be because: (a) the `isClickingOnMobile` state is reset when a drag starts, or (b) the touch event's `isTouchEndWithinSquare` check fails if the user's finger moved slightly. This requires physical device testing to confirm.

**If click-to-move doesn't work after library investigation:** Add a custom `onPointerUp` handler via `squareRenderer` as a fallback — this fires on both mouse and touch and can call `onSquareClick` directly.

### Pattern 6: PWA Install Prompt (Deferred — for reference when ready)

**Android (PWA-04):** `beforeinstallprompt` event fires when Chrome determines the app is installable. Capture it, show custom UI, call `.prompt()` when user clicks:

```typescript
// Hook pattern
const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
useEffect(() => {
  const handler = (e: Event) => {
    e.preventDefault();
    setDeferredPrompt(e as BeforeInstallPromptEvent);
  };
  window.addEventListener('beforeinstallprompt', handler);
  return () => window.removeEventListener('beforeinstallprompt', handler);
}, []);
```

**iOS (PWA-05):** No `beforeinstallprompt`. Detect iOS + not in standalone mode:
```typescript
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
const showIOSBanner = isIOS && !isStandalone;
```

**Persistence:** Use `localStorage` to track dismissed state so banner doesn't re-appear after dismissal.

**When to trigger:** Show after meaningful engagement (e.g., user has viewed the Openings page at least once, or has games imported). Do not show on first load.

### Anti-Patterns to Avoid
- **Using JS touch detection to conditionally set CSS classes:** Causes hydration-like mismatches on first paint. Use Tailwind `sm:` breakpoints instead.
- **Setting `overflow-x: hidden` on intermediate containers:** Can break `sticky` positioning — only apply to `body` or outermost wrapper.
- **Wrapping board in a container with fixed height:** The board uses `ResizeObserver` to set `boardWidth` — any fixed height on the wrapper will clip the board.
- **Using `position: fixed` for the sticky board:** Fixed positioning takes the element out of document flow and causes layout shifts. `sticky` keeps it in flow and stacks correctly with the bottom bar.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Touch drag on chessboard | Custom pointer event handler | react-chessboard v5 TouchSensor | Library handles @dnd-kit touch natively |
| Sticky scroll position | JS scroll listener + transform | CSS `sticky` | Zero JS, hardware-accelerated, no jank |
| iOS install detection | Complex UA parsing | Single navigator.userAgent check + matchMedia | Standard pattern; no library needed |
| Collapsible filters | Custom accordion | shadcn `Collapsible` | Already in use for bookmarks/filters |

---

## Common Pitfalls

### Pitfall 1: Sticky Board Breaks Due to Ancestor Overflow
**What goes wrong:** Board stops being sticky; scrolls away with content
**Why it happens:** Any ancestor element with `overflow: hidden`, `overflow: auto`, or `overflow: scroll` creates a new stacking context that confines `sticky` to it — if that ancestor is smaller than viewport, sticky effectively doesn't work
**How to avoid:** Verify the DOM chain from `<body>` to the sticky element has no `overflow` set on any ancestor. The current App.tsx `<main>` has no overflow — safe.
**Warning signs:** Board scrolls off screen immediately when user scrolls down

### Pitfall 2: MobileHeader Space Causes Double Padding on Openings
**What goes wrong:** After hiding MobileHeader on openings, there's either too much or too little top padding on mobile
**Why it happens:** The `<main>` tag in ProtectedLayout has no top padding set, but the MobileHeader occupies ~53px. When hidden, the page starts directly at the board.
**How to avoid:** On openings mobile, the sticky board at `top-0` is the de facto top boundary. No padding adjustment needed because the board itself provides visual top spacing.
**Warning signs:** Content appears cut off at the top or has excessive blank space

### Pitfall 3: onTouchEnd preventDefault Breaks Scroll
**What goes wrong:** Page scroll stops working after touching the chessboard
**Why it happens:** react-chessboard calls `e.preventDefault()` on `onTouchEnd` for squares. If this prevents the browser's scroll gesture, the page becomes unscrollable.
**How to avoid:** The library calls `preventDefault()` only on `touchend` events for squares (not `touchmove`), so scroll (which listens to `touchmove`) should still work. Monitor on physical device.
**Warning signs:** User can't scroll the page when initiating scroll gesture on a chess square

### Pitfall 4: 44px Touch Targets on ToggleGroupItem Break Desktop Layout
**What goes wrong:** Desktop filter controls become unnecessarily tall
**Why it happens:** Applying `min-h-11` globally (not responsive)
**How to avoid:** Always use `sm:min-h-0` or `sm:h-auto` to reset on desktop:
```typescript
className="min-h-11 sm:min-h-0"
```

### Pitfall 5: Filters Collapsible Default State on Desktop
**What goes wrong:** Filters collapsed by default on desktop too
**Why it happens:** The `moreFiltersOpen` state starts as `false`, which collapses filters everywhere
**How to avoid:** Initialize `moreFiltersOpen` based on viewport — but to avoid JS detection, use the pattern where mobile starts collapsed and desktop doesn't use the Collapsible at all. The current code uses the same `sidebar` variable for both mobile and desktop. The Collapsible is visible in both layouts. Solution: either (a) initialize `moreFiltersOpen` to `true` (keeps desktop expanded) and accept that mobile starts expanded too, but the CONTEXT.md says collapsed by default on mobile — OR (b) restructure so the mobile layout uses a separate `mobileFiltersOpen` state initialized to `false`.

**Recommended:** Use a separate `mobileFiltersOpen` state (default `false`) for the mobile Collapsible trigger. The desktop sidebar can render FilterPanel directly (not in a Collapsible) or keep the existing Collapsible with its own state.

---

## Code Examples

### Sticky Board Wrapper
```typescript
// In Openings.tsx mobile section
{/* Mobile: sticky board at top */}
<div className="md:hidden">
  <div className="sticky top-0 z-10 bg-background pb-2">
    <ChessBoard
      position={chess.position}
      onPieceDrop={chess.makeMove}
      flipped={boardFlipped}
      lastMove={chess.lastMove}
      arrows={boardArrows}
    />
  </div>
  <BoardControls ... />
  <MoveList ... />
  <Collapsible open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
    {/* "More filters" trigger + FilterPanel */}
  </Collapsible>
  <Collapsible open={positionBookmarksOpen} onOpenChange={setPositionBookmarksOpen}>
    {/* Position bookmarks */}
  </Collapsible>
  <Tabs ...>
    {/* Moves / Games / Statistics */}
  </Tabs>
</div>
```

### Hide MobileHeader on Openings
```typescript
// In App.tsx ProtectedLayout
const location = useLocation();
const isOpeningsRoute = location.pathname.startsWith('/openings');
// ...
{!isOpeningsRoute && <MobileHeader />}
```

### 44px Touch Target on Filter Buttons
```typescript
// In FilterPanel.tsx — time control buttons
className={cn(
  'rounded border px-3 min-h-11 sm:min-h-0 sm:py-0.5 py-2 text-xs transition-colors',
  isTimeControlActive(tc) ? '...' : '...',
)}
```

### 44px on ToggleGroupItem
Shadcn `ToggleGroupItem` with `size="sm"` is approximately 32px. Override with:
```typescript
<ToggleGroupItem
  value="white"
  data-testid="filter-played-as-white"
  className="min-h-11 sm:min-h-0"
>
```

### Disable Drag as Fallback
```typescript
// In ChessBoard.tsx if drag causes black screen
<Chessboard
  options={{
    ...existingOptions,
    allowDragging: false, // fallback if touch drag causes black screen
  }}
/>
```

### PWA Install Prompt Hook (for deferred PWA-04/05)
```typescript
// frontend/src/hooks/useInstallPrompt.ts
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export function useInstallPrompt() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [isDismissed, setIsDismissed] = useState(
    () => localStorage.getItem('install-prompt-dismissed') === 'true'
  );

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setPromptEvent(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const triggerPrompt = async () => {
    if (!promptEvent) return;
    await promptEvent.prompt();
    setPromptEvent(null);
  };

  const dismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('install-prompt-dismissed', 'true');
  };

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;

  return {
    showAndroidPrompt: !!promptEvent && !isDismissed,
    showIOSBanner: isIOS && !isStandalone && !isDismissed,
    triggerPrompt,
    dismiss,
  };
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTML5 DnD for chess drag | @dnd-kit with TouchSensor | react-chessboard v5 | Touch drag works on iOS/Android without native events |
| `arePiecesDraggable` prop (v4) | `allowDragging` prop (v5) | react-chessboard v5 API | Different option name; no boolean UA check needed |
| Tailwind v3 `sm:` config | Tailwind v4 CSS-first config | Tailwind 4.x | No config file; breakpoints set via CSS `@theme` |

**Deprecated/outdated:**
- `arePiecesDraggable`: Removed in react-chessboard v5 — use `allowDragging` (verified in dist source)
- HTML5 Drag-and-Drop API: react-chessboard v5 does NOT use HTML5 DnD; uses @dnd-kit pointer/touch events

---

## Open Questions

1. **Does onSquareClick actually fire on touch in v5.10.0 without code changes?**
   - What we know: Library has `onTouchEnd` → `onSquareClick` code path; `e.preventDefault()` is called to suppress ghost click
   - What's unclear: Whether `isTouchEndWithinSquare` check passes on all mobile browsers; whether the dnd-kit drag initiation resets `isClickingOnMobile` before the tap ends
   - Recommendation: Test on physical device first. If broken, add `onPointerUp` fallback via `squareRenderer`.

2. **Does touch drag cause a black screen on current react-chessboard v5.10.0?**
   - What we know: Library uses @dnd-kit `DragOverlay` with `position: fixed; touchAction: none`; this is a known source of visual glitches on some Android Chrome builds
   - What's unclear: Whether v5.10.0 has mitigations; whether the specific device/browser combos used in this project are affected
   - Recommendation: Test on Android Chrome. If black screen occurs, set `allowDragging: false` immediately and document as a library limitation.

3. **Does the sticky board need `top-0` offset adjustment when browser UI retracts on scroll?**
   - What we know: Mobile browsers retract the address bar on scroll, changing the viewport height; CSS `top-0` tracks the visual viewport, not the layout viewport
   - What's unclear: Whether the sticky board will correctly stick to the visual viewport top
   - Recommendation: `sticky top-0` tracks the layout viewport (not visual), so the board will appear to sink slightly below the hidden address bar. This is standard browser behavior and acceptable — no action needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only) — no frontend test framework |
| Config file | No pytest.ini; uses `uv run pytest` defaults |
| Quick run command | `uv run pytest -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | 44px touch targets | manual | Manual: measure on device at 375px | N/A |
| UX-02 | No horizontal scroll at 375px | manual | Manual: Chrome DevTools 375px viewport | N/A |
| UX-03 | Chessboard touch interaction | manual | Manual: physical iOS Safari + Android Chrome | N/A |
| UX-04 | Openings sidebar + content usable on mobile | manual | Manual: test at 375px with scroll | N/A |
| PWA-04 | Android install prompt | manual | Manual: Android Chrome engagement trigger | N/A |
| PWA-05 | iOS install banner | manual | Manual: iOS Safari standalone detection | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (backend regression guard)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full backend suite green + manual mobile verification before `/gsd:verify-work`

### Wave 0 Gaps
- No frontend test infrastructure exists. All UX requirements are inherently manual-only (visual layout, touch events, device-specific behavior). This is expected for a UI polish phase.
- Backend tests are unchanged in this phase — existing infrastructure is sufficient.

---

## Sources

### Primary (HIGH confidence)
- react-chessboard v5.10.0 dist source (`/frontend/node_modules/react-chessboard/dist/index.esm.js`) — verified TouchSensor usage, onSquareClick touch handling, allowDragging prop, DragOverlay positioning
- App.tsx source — verified MobileHeader unconditional render, `sm:` breakpoint at 640px, bottom bar fixed positioning
- Openings.tsx source — verified current mobile layout structure (lines 527-546), sidebar composition
- ChessBoard.tsx source — verified boardWidth ResizeObserver, handleSquareClick logic, squareStyles
- FilterPanel.tsx source — verified small button heights (`py-0.5`)
- BoardControls.tsx source — verified shadcn Button `size="icon"` usage (36px default)

### Secondary (MEDIUM confidence)
- React Chessboard README (v5.10.0) — confirms "Mobile support" as a listed feature; references @dnd-kit usage
- MDN Web Docs pattern for `beforeinstallprompt` and iOS standalone detection — standard browser APIs, well-documented

### Tertiary (LOW confidence)
- @dnd-kit `DragOverlay` black screen behavior on Android — known community report but not verified against this specific version combination

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from installed node_modules and source
- Architecture: HIGH — all patterns derived from reading actual source files, not documentation assumptions
- Touch interaction: MEDIUM — code path verified, but actual device behavior requires physical testing
- Pitfalls: HIGH for CSS pitfalls (verified from source), MEDIUM for touch behavior (requires device)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (react-chessboard v5 API is stable; CSS sticky is evergreen)
