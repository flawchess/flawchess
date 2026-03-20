# Phase 18: Mobile Navigation - Research

**Researched:** 2026-03-20
**Domain:** React mobile navigation — bottom bar, bottom sheet drawer, safe-area insets, Tailwind CSS v4
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Navigation pattern**
- Bottom navigation bar (not hamburger-only) — matches chess.com/lichess mobile pattern
- 3 direct tab buttons: Import, Openings, Global Stats (icon + label below)
- 4th button: "More" (hamburger icon + "More" label) — opens bottom sheet drawer
- Bottom bar visible only for authenticated users — login page has no nav
- Active route highlighted in bottom bar

**Bottom sheet drawer (More)**
- Slide-up half-sheet from bottom when "More" is tapped
- Content: username/email at top, all nav links (for discoverability), separator, Logout button
- Tapping any nav link closes the sheet and navigates
- Dimmed backdrop behind sheet; tap backdrop to dismiss

**Context-sensitive bottom bar (experimental)**
- On the Openings page, consider replacing bottom bar nav buttons with chessboard controls (reset, previous move, next move, flip board)
- Implement standard bottom bar first, then experiment with contextual actions
- If contextual controls are used, the "More" button should remain for navigation access

**Mobile header**
- On mobile (<640px): simplified header with "Chessalytics" brand left-aligned + current page title
- Page title shows top-level name only (e.g., "Openings" not "Openings > Moves")
- Desktop header (≥640px): unchanged horizontal nav bar with all links

**Breakpoint**
- 640px (Tailwind `sm`) — below this gets mobile layout (bottom bar + simplified header), above gets desktop layout (horizontal nav in header)

**Safe-area insets**
- `viewport-fit=cover` already set in index.html (Phase 17)
- Apply `env(safe-area-inset-*)` CSS for header top padding and bottom bar bottom padding
- Prevents overlap with notch/Dynamic Island on iPhones in standalone PWA mode

### Claude's Discretion
- Bottom bar animation style and transition timing
- Exact icons for each bottom bar tab (Lucide icon choices)
- Bottom sheet implementation approach (shadcn Sheet vs custom)
- Safe-area inset CSS implementation details
- Whether to use shadcn Drawer component or custom bottom sheet

### Deferred Ideas (OUT OF SCOPE)
- Context-sensitive board controls in bottom bar (Openings page) — experiment during or after Phase 18 base implementation
- UX-F01 from REQUIREMENTS.md is now superseded — bottom bar is being implemented in Phase 18 instead of deferred
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAV-01 | User sees a hamburger menu on mobile screens that opens a slide-in drawer with all nav links and logout | shadcn Drawer component (vaul-based) with `direction="bottom"` handles slide-up sheet, backdrop, dismiss gesture |
| NAV-02 | Drawer closes on link tap and highlights the active route | Controlled `open` state prop on Drawer + React Router `useLocation` for active detection; same pattern as existing `NavHeader` |
| NAV-03 | App content respects safe-area insets on notched iPhones in standalone PWA mode | `viewport-fit=cover` already set; apply `padding-bottom: env(safe-area-inset-bottom)` to bottom bar and `padding-top: env(safe-area-inset-top)` to header via `tailwindcss-safe-area` plugin or inline CSS |
</phase_requirements>

---

## Summary

Phase 18 adds a mobile navigation layer beneath the existing desktop `NavHeader`. The desktop layout (≥640px) remains completely unchanged. On mobile (<640px) the header simplifies to brand + page title, and a fixed bottom bar with 3 direct tabs plus a "More" button replaces the top nav links. Tapping "More" opens a bottom sheet drawer (the shadcn Drawer component, backed by vaul) containing the full nav link list, user info, and logout.

The shadcn `Drawer` component is already available via `shadcn add drawer` (adds `vaul` as a peer dep; generates `src/components/ui/drawer.tsx`). It supports `direction="bottom"`, a dimmed overlay backdrop, swipe-to-dismiss, and controlled open state — exactly what the spec calls for. No custom bottom sheet is needed.

Safe-area insets are straightforward: `viewport-fit=cover` is already set in `index.html`. Adding `padding-bottom: env(safe-area-inset-bottom)` on the bottom bar and `padding-top: env(safe-area-inset-top)` on the mobile header prevents content from hiding behind the notch or Dynamic Island. This can be done via the `tailwindcss-safe-area` plugin (adds `pb-safe`, `pt-safe` utility classes) or inline CSS `style` props.

**Primary recommendation:** Use `shadcn add drawer` for the bottom sheet, `tailwindcss-safe-area` v1.3.0 for safe-area utility classes, Tailwind `sm:` breakpoint for responsive switching, and extract `MobileBottomBar` + `MobileMoreDrawer` as separate components alongside the existing `NavHeader`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vaul (via shadcn Drawer) | 1.1.2 | Bottom sheet drawer primitive | Emil Kowalski's drawer; used by shadcn as the official Drawer; swipe-to-dismiss, backdrop, controlled state, focus trap included |
| tailwindcss-safe-area | 1.3.0 | `pb-safe`, `pt-safe` utility classes using `env(safe-area-inset-*)` | Idiomatic Tailwind CSS v4 approach; single `@import` in index.css; no plugin config needed |
| lucide-react | 0.577.0 (already installed) | Icons for bottom bar tabs | Already in project; project-standard icon library per components.json |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React Router `useLocation` | already installed | Active route detection in bottom bar | Same pattern already used in `NavHeader` |
| `useAuth` hook | project-internal | Conditional render (auth-only bottom bar) + logout action | Already established pattern in `ProtectedLayout` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| shadcn Drawer (vaul) | Custom div + CSS transitions | Drawer handles focus trap, ESC key, backdrop click, swipe-to-dismiss — don't hand-roll |
| tailwindcss-safe-area plugin | Inline `style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}` | Inline style works but isn't Tailwind-idiomatic; plugin adds `pb-safe` utilities that compose naturally with other Tailwind classes |
| tailwindcss-safe-area plugin | Manual `@theme` CSS variable | Manual approach works but requires writing the same boilerplate the plugin handles |

**Installation:**
```bash
# From frontend/ directory
node node_modules/.bin/shadcn add drawer   # adds vaul dep + generates drawer.tsx
npm install tailwindcss-safe-area
```

**Version verification (run before implementing):**
```bash
npm view vaul version           # verified: 1.1.2
npm view tailwindcss-safe-area version  # verified: 1.3.0
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── App.tsx                    # Refactor NavHeader + add MobileBottomBar, MobileMoreDrawer
├── components/
│   └── ui/
│       └── drawer.tsx         # NEW — shadcn add drawer generates this
```

All navigation components stay in `App.tsx` (following the existing pattern) unless they grow large enough to extract into `src/components/` — that's Claude's discretion.

### Pattern 1: Responsive Layout Switch via Tailwind `sm:` Breakpoint

**What:** Show/hide components by viewport width using `hidden sm:flex` / `flex sm:hidden`. No JavaScript media queries needed.

**When to use:** Any time a component is exclusively desktop or exclusively mobile.

**Example:**
```tsx
// Source: Tailwind CSS docs — responsive prefixes
// Desktop nav: hidden on mobile, flex on sm+
<nav className="hidden sm:flex ...">...</nav>

// Mobile bottom bar: visible on mobile, hidden on sm+
<nav className="fixed bottom-0 inset-x-0 flex sm:hidden z-40 ...">...</nav>
```

### Pattern 2: shadcn Drawer as Controlled Bottom Sheet

**What:** Pass `open` and `onOpenChange` props to `Drawer` so the "More" button controls it and nav link taps close it.

**When to use:** Any bottom sheet with programmatic open/close (nav links must close the sheet on tap).

**Example:**
```tsx
// Source: vaul docs + shadcn drawer.tsx generated code
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle,
  DrawerClose
} from '@/components/ui/drawer';

function MobileMoreDrawer({ open, onOpenChange }: Props) {
  const navigate = useNavigate();

  const handleNavClick = (to: string) => {
    onOpenChange(false);   // close drawer first
    navigate(to);
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
      <DrawerContent data-testid="mobile-more-drawer">
        {/* username at top, nav links, separator, logout */}
      </DrawerContent>
    </Drawer>
  );
}
```

Key props:
- `direction="bottom"` — slide up from bottom
- `open` / `onOpenChange` — controlled state; backdrop click and swipe-down auto-call `onOpenChange(false)`
- `dismissible` — defaults to `true`; swipe down to dismiss

### Pattern 3: Safe-Area Insets via tailwindcss-safe-area

**What:** After `npm install tailwindcss-safe-area`, add one `@import` to `index.css`. Then use `pb-safe` and `pt-safe` utility classes.

**When to use:** Bottom bar bottom padding and mobile header top padding.

```css
/* index.css — add after existing @import lines */
@import "tailwindcss-safe-area";
```

```tsx
// Bottom bar — padding-bottom covers home indicator / Dynamic Island gesture area
<nav className="fixed bottom-0 inset-x-0 flex sm:hidden pb-safe bg-background border-t ...">

// Mobile header — padding-top covers notch on iPhone X+
<header className="sm:hidden pt-safe px-4 ...">
```

### Pattern 4: Active Route Highlighting in Bottom Bar

**What:** Reuse the existing `isActive()` logic from `NavHeader`. Extract it or duplicate it in the bottom bar component.

**Example:**
```tsx
// Same logic already in NavHeader — reuse verbatim
const isActive = (to: string) =>
  to === '/openings'
    ? location.pathname.startsWith('/openings')
    : location.pathname === to;

// Apply to bottom bar button
<button
  className={cn(
    'flex flex-col items-center gap-1 p-2',
    isActive(to) ? 'text-primary' : 'text-muted-foreground'
  )}
>
  <Icon className="h-5 w-5" />
  <span className="text-xs">{label}</span>
</button>
```

### Anti-Patterns to Avoid

- **`useEffect` + `window.innerWidth`** for responsive switching — Tailwind CSS classes are the right tool; JavaScript media queries cause flash-of-wrong-layout on hydration.
- **`document.body.style.overflow = 'hidden'`** for drawer backdrop — vaul handles scroll lock internally; double-locking causes bugs on iOS.
- **`position: fixed` without `z-index`** — bottom bar must be `z-40` minimum (above page content), drawer must be `z-50` (above bottom bar).
- **`bottom: 0` without safe-area padding** — on iPhone X+ in standalone PWA, the home indicator overlaps a bottom bar that doesn't add `pb-safe`.
- **Page content not padded for bottom bar** — the main `<Outlet />` in `ProtectedLayout` needs `pb-16 sm:pb-0` (or equivalent) so content doesn't hide behind the fixed bottom bar on mobile.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bottom sheet with swipe-to-dismiss | Custom `div` with `onTouchStart`/`onTouchEnd` | shadcn Drawer (vaul) | Touch handling, velocity-based dismiss, spring animation, scroll lock, focus trap — all non-trivial edge cases |
| Backdrop click-to-dismiss | Manual `onClick` on overlay div | vaul built-in | vaul's overlay handles pointer events correctly including when drawer content scrolls |
| Focus trapping in drawer | `tabIndex` manipulation | vaul built-in | Accessibility requirement; vaul is Radix-backed and handles ARIA correctly |
| Safe-area pixel values | Hard-coded `pb-[34px]` | `env(safe-area-inset-bottom)` | Hard-coded values break across iPhone models; the env variable returns 0 on non-notched devices |

**Key insight:** The vaul-backed Drawer solves a deceptively complex problem — mobile gesture physics, scroll lock interaction, focus management, and animation all at once. The shadcn Drawer wrapper adds zero overhead since it's just thin Tailwind styling around vaul primitives.

---

## Common Pitfalls

### Pitfall 1: Bottom Bar Overlaps Page Content

**What goes wrong:** Page content scrolls underneath the fixed bottom bar on mobile; last list items, buttons, or footer content is permanently hidden.

**Why it happens:** `position: fixed` elements don't participate in document flow. The main layout outlet has no awareness of the bottom bar's height.

**How to avoid:** Add `pb-16 sm:pb-0` (or `pb-20` if using safe-area offset) to the main content wrapper inside `ProtectedLayout`. The `sm:pb-0` removes it on desktop where the bottom bar is hidden.

**Warning signs:** When scrolling to the bottom of any page, the last ~64px is invisible.

### Pitfall 2: Safe-Area Ignored Because `viewport-fit=cover` Not Set

**What goes wrong:** `env(safe-area-inset-bottom)` returns `0` and the bottom bar still overlaps the home indicator.

**Why it happens:** Browsers only expose non-zero safe-area values when `viewport-fit=cover` is in the viewport meta.

**How to avoid:** Confirm `index.html` has `viewport-fit=cover` (it does — set in Phase 17). Then test on a real iPhone in standalone PWA mode; Safari browser adds its own chrome so safe-area looks fine in browser, but standalone mode is where it matters.

**Warning signs:** `env(safe-area-inset-bottom)` evaluates to `0px` in DevTools computed styles.

### Pitfall 3: Drawer Doesn't Close on Navigation

**What goes wrong:** User taps a nav link in the drawer, the route changes, but the drawer stays open and overlays the new page.

**Why it happens:** React Router `<Link>` just changes the URL; the Drawer's `open` state is unaffected unless explicitly set to `false`.

**How to avoid:** Use a controlled `open`/`onOpenChange` pattern. In the click handler: call `onOpenChange(false)` before or alongside navigation. If using `<Link>` directly inside the drawer, use `<DrawerClose asChild><Link to={...}>` so vaul's close mechanism fires on click.

**Warning signs:** Drawer is open after tapping a nav link.

### Pitfall 4: Bottom Bar Hidden Behind Keyboard on Android

**What goes wrong:** When the software keyboard opens (e.g., search input), the bottom bar repositions to above the keyboard, overlapping content.

**Why it happens:** `position: fixed` elements reposition when `visualViewport` shrinks on Android Chrome.

**How to avoid:** This is a known Android Chrome issue with fixed bottom bars. Mitigation: use `env(keyboard-inset-height, 0)` CSS or hide the bottom bar when an input is focused using a React `onFocus`/`onBlur` handler. For Phase 18, flag this as a known limitation — it's out of scope since none of the 3 direct nav tabs involve text input.

**Warning signs:** Bottom bar floats above the keyboard when an input is focused.

### Pitfall 5: Desktop Nav Broken After Refactor

**What goes wrong:** Refactoring `NavHeader` to add mobile header variant accidentally removes desktop nav links.

**Why it happens:** `NavHeader` currently renders both brand + nav links in one component. Splitting to mobile/desktop variants risks missing cases.

**How to avoid:** Keep the desktop-only nav rendering behind `hidden sm:flex` (or equivalent), not guarded by JavaScript. Add a visual regression check: verify desktop nav still shows all 3 nav links + logout after changes.

**Warning signs:** `data-testid="nav-import"` (etc.) not found in DOM at ≥640px viewport.

---

## Code Examples

Verified patterns from official sources:

### tailwindcss-safe-area CSS Import (Tailwind v4)
```css
/* Source: tailwindcss-safe-area README — Tailwind v4 usage */
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@import "tailwindcss-safe-area";   /* ADD this line */
@import "@fontsource-variable/geist";
```

### Minimal Bottom Bar Skeleton
```tsx
// Source: Tailwind CSS responsive prefix docs + project patterns
const BOTTOM_NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: LayoutIcon },
  { to: '/global-stats', label: 'Global Stats', Icon: BarChartIcon },
] as const;

function MobileBottomBar({ onMoreClick }: { onMoreClick: () => void }) {
  const location = useLocation();

  const isActive = (to: string) =>
    to === '/openings'
      ? location.pathname.startsWith('/openings')
      : location.pathname === to;

  return (
    <nav
      aria-label="Mobile navigation"
      data-testid="mobile-bottom-bar"
      className="fixed bottom-0 inset-x-0 flex sm:hidden z-40 bg-background border-t border-border pb-safe"
    >
      {BOTTOM_NAV_ITEMS.map(({ to, label, Icon }) => (
        <Link
          key={to}
          to={to}
          data-testid={`mobile-nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
          className={cn(
            'flex flex-1 flex-col items-center gap-1 py-2',
            isActive(to) ? 'text-primary' : 'text-muted-foreground'
          )}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
          <span className="text-xs">{label}</span>
        </Link>
      ))}
      <button
        onClick={onMoreClick}
        data-testid="mobile-nav-more"
        aria-label="More navigation options"
        className="flex flex-1 flex-col items-center gap-1 py-2 text-muted-foreground"
      >
        <MenuIcon className="h-5 w-5" aria-hidden="true" />
        <span className="text-xs">More</span>
      </button>
    </nav>
  );
}
```

### Controlled Drawer Pattern for More Sheet
```tsx
// Source: vaul docs + shadcn drawer.tsx generated structure
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle
} from '@/components/ui/drawer';
import { DrawerClose } from '@/components/ui/drawer';

function MobileMoreDrawer({
  open,
  onOpenChange
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
      <DrawerContent data-testid="mobile-more-drawer">
        <DrawerHeader>
          <DrawerTitle>More</DrawerTitle>
          {/* username / email here */}
        </DrawerHeader>
        <nav>
          {NAV_ITEMS.map(({ to, label }) => (
            <DrawerClose key={to} asChild>
              <Link
                to={to}
                data-testid={`drawer-nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
              >
                {label}
              </Link>
            </DrawerClose>
          ))}
        </nav>
        <DrawerClose asChild>
          <button data-testid="drawer-logout" onClick={logout}>Logout</button>
        </DrawerClose>
      </DrawerContent>
    </Drawer>
  );
}
```

### ProtectedLayout with Mobile Bottom Bar
```tsx
// App.tsx refactor sketch
function ProtectedLayout() {
  const { token } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);

  if (!token) return <Navigate to="/login" replace />;

  return (
    <>
      <NavHeader />                          {/* desktop: unchanged */}
      <MobileHeader />                       {/* mobile only: brand + page title */}
      <main className="pb-16 sm:pb-0">       {/* compensate for bottom bar height */}
        <Outlet />
      </main>
      <MobileBottomBar onMoreClick={() => setMoreOpen(true)} />
      <MobileMoreDrawer open={moreOpen} onOpenChange={setMoreOpen} />
    </>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hamburger → slide-in side drawer | Bottom navigation bar + "More" sheet | iOS/Android apps, ~2018+ | More thumb-reachable; matches chess.com/lichess pattern |
| `tailwind.config.js` plugin registration | `@import "tailwindcss-safe-area"` in CSS | Tailwind CSS v4 (2024) | Simpler; no config file needed |
| Custom gesture handling for sheet dismiss | vaul's built-in swipe-to-dismiss | vaul library (2023+) | Eliminates ~200 lines of touch event handling |
| Hard-coded pixel values for notch | `env(safe-area-inset-*)` | CSS Working Group spec, ~2017 | Works across all iPhone models automatically |

**Deprecated/outdated:**
- `@safe-area-inset-bottom` (old draft CSS syntax): replaced by `env(safe-area-inset-bottom)` — use the `env()` form.
- `constant(safe-area-inset-bottom)`: iOS 11.0 beta only, removed immediately. Never use `constant()`.

---

## Open Questions

1. **tailwindcss-safe-area Tailwind v4 import compatibility**
   - What we know: README documents `@import "tailwindcss-safe-area"` for v4; current version is 1.3.0
   - What's unclear: Whether the generated utilities use `@layer utilities` or `@layer base` which could interact with shadcn's CSS variable approach
   - Recommendation: Install and do a quick `npm run build` dry-run before planning; if import order matters, move it after shadcn imports

2. **`useAuth` username/email access in the More drawer**
   - What we know: `useAuth` exposes `token` and `logout`; the drawer spec shows username/email at the top
   - What's unclear: Whether `useAuth` currently exposes user profile info or only the token
   - Recommendation: Check `useAuth` hook implementation before planning — may need to fetch user profile or extend the hook

3. **Mobile header page title source**
   - What we know: Context says "Openings" not "Openings > Moves" — top-level only
   - What's unclear: Whether page title comes from route matching or from a context/prop drilled from each page
   - Recommendation: Simplest approach is a route-to-title map in `App.tsx` keyed off `useLocation().pathname` — same approach used for `isActive()`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None installed (no vitest/jest config found in `frontend/`) |
| Config file | None — Wave 0 must add `vitest.config.ts` if unit tests are desired |
| Quick run command | `npm run lint` (only automation available) |
| Full suite command | `npm run build` (TypeScript compilation + Vite build = smoke test) |

**Note:** The project has no frontend test infrastructure. For this phase, which is purely UI/CSS, the meaningful validation is:
- TypeScript compiles without errors (`npm run build`)
- ESLint passes (`npm run lint`)
- Manual device/responsive testing via `npm run dev:mobile` or Cloudflare tunnel (both set up in Phase 17)

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAV-01 | Bottom bar hidden ≥640px; visible <640px; "More" opens drawer | manual-only | `npm run build` (TS/lint gate) | N/A |
| NAV-02 | Active route highlighted in bottom bar; drawer closes on nav link tap | manual-only | `npm run build` (TS/lint gate) | N/A |
| NAV-03 | Safe-area insets applied; no overlap on notched iPhone PWA | manual-only (device required) | `npm run build` (TS/lint gate) | N/A |

**Justification for manual-only:** All three requirements are layout/visual behaviors that require a real or simulated narrow viewport. No vitest/jsdom setup exists. The TypeScript build + lint check gates functional correctness at the code level; responsive layout correctness requires Chrome DevTools device simulation or a physical iPhone in standalone PWA mode.

### Sampling Rate
- **Per task commit:** `npm run lint`
- **Per wave merge:** `npm run build`
- **Phase gate:** `npm run build` green + manual responsive check at 375px (Chrome DevTools) + manual check on iPhone PWA (optional, requires device)

### Wave 0 Gaps

None required for test infrastructure — no automated test framework is being added in this phase. The phase relies on TypeScript compilation and manual responsive verification.

If future phases add vitest, the test targets for this phase would be:
- `tests/MobileBottomBar.test.tsx` — active route highlight logic
- `tests/MobileMoreDrawer.test.tsx` — open/close controlled state

---

## Sources

### Primary (HIGH confidence)
- shadcn CLI `--view` output — exact generated `drawer.tsx` code (verified locally, 2026-03-20)
- `vaul` npm view — version 1.1.2 (verified 2026-03-20)
- `tailwindcss-safe-area` npm view — version 1.3.0 (verified 2026-03-20)
- Project `frontend/index.html` — `viewport-fit=cover` confirmed present
- Project `frontend/src/App.tsx` — existing `NavHeader`, `NAV_ITEMS`, `isActive` patterns
- Project `frontend/package.json` — confirmed `lucide-react`, `react-router-dom`, `tailwindcss` already installed

### Secondary (MEDIUM confidence)
- [shadcn Drawer docs](https://ui.shadcn.com/docs/components/components/drawer) — `direction="bottom"`, controlled open pattern
- [tailwindcss-safe-area GitHub](https://github.com/mvllow/tailwindcss-safe-area) — Tailwind v4 `@import` installation
- [CSS-Tricks: The Notch and CSS](https://css-tricks.com/the-notch-and-css/) — `env(safe-area-inset-*)` fundamentals
- [MDN: env()](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/env) — safe-area-inset specification

### Tertiary (LOW confidence)
- None — all claims verified against official sources or live project code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via npm view and shadcn dry-run
- Architecture: HIGH — patterns derived directly from existing project code (`NavHeader`, `ProtectedLayout`) and official vaul/shadcn docs
- Pitfalls: HIGH — safe-area and iOS standalone pitfalls are well-documented in official CSS specs and MDN; bottom-bar content overlap is mechanical

**Research date:** 2026-03-20
**Valid until:** 2026-06-20 (stable libraries; vaul and tailwindcss-safe-area are mature)
