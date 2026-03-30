---
phase: 34-theme-improvements
verified: 2026-03-28T12:49:42Z
status: gaps_found
score: 8/10 must-haves verified
gaps:
  - truth: "All theme-relevant constants are centralized in theme.ts and CSS variables — no ad-hoc color values scattered across components"
    status: partial
    reason: "Phase 34 introduced two new ad-hoc hex values (#171717 and #262626) in toggle.tsx and FilterPanel.tsx during visual iteration. These inactive-button background colors are not registered as CSS variables in index.css nor defined in theme.ts. The charcoal-hover CSS variable (#262220) already exists but is a different value. The REQUIREMENTS.md 'Pending' marker for THEME-01 reflects this: it was never checked off."
    artifacts:
      - path: "frontend/src/components/ui/toggle.tsx"
        issue: "Line 13: bg-[#171717] hover:bg-[#262626] hardcoded — introduced in commit 4779b05 during phase 34 visual iteration"
      - path: "frontend/src/components/filters/FilterPanel.tsx"
        issue: "Lines 138, 164: bg-[#171717] hover:bg-[#262626] hardcoded — introduced in commit bec9ee3 during phase 34 visual iteration"
    missing:
      - "Add --inactive-bg: #171717 and --inactive-bg-hover: #262626 CSS variables to :root in index.css"
      - "Register --color-inactive-bg and --color-inactive-bg-hover in @theme inline block"
      - "Replace bg-[#171717] with bg-inactive-bg and bg-[#262626] with bg-inactive-bg-hover in toggle.tsx and FilterPanel.tsx"
      - "Update REQUIREMENTS.md to check THEME-01, THEME-03, THEME-04 as Complete"
  - truth: "REQUIREMENTS.md tracking reflects actual completion state"
    status: failed
    reason: "REQUIREMENTS.md shows THEME-01, THEME-03, THEME-04 as '[ ] Pending' and 'Pending' in the tracking table, but the phase has completed THEME-03 and THEME-04 fully, and THEME-01 partially. The summary frontmatter claims requirements-completed: [THEME-01, THEME-03, THEME-04, THEME-05] but REQUIREMENTS.md was never updated."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 12-16: THEME-01, THEME-03, THEME-04 still show [ ] / Pending status"
    missing:
      - "Update REQUIREMENTS.md: mark THEME-03 as [x] Complete (filter button layout fully implemented)"
      - "Update REQUIREMENTS.md: mark THEME-04 as [x] Complete (Recharts corners added per D-07/D-08 scope)"
      - "Update REQUIREMENTS.md: mark THEME-01 as [x] Complete after resolving the #171717/#262626 gap"
      - "Update tracking table entries from 'Pending' to 'Complete' for THEME-03 and THEME-04"
---

# Phase 34: Theme Improvements Verification Report

**Phase Goal:** Users see a visually consistent, polished UI with centralized theme management across all pages
**Verified:** 2026-03-28T12:49:42Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All theme constants centralized — no ad-hoc hex colors scattered in components | PARTIAL | #171717 and #262626 hardcoded in toggle.tsx:13 and FilterPanel.tsx:138,164; introduced by this phase |
| 2 | Content containers have charcoal background with SVG feTurbulence noise texture | VERIFIED | charcoal-texture class defined with feTurbulence in index.css; used on Dashboard (4x), Openings (9x), Endgames (8x), Import (2x) |
| 3 | Filter buttons span full sidebar width with even spacing | VERIFIED | grid grid-cols-4 (Time Control), grid grid-cols-2 (Platform), w-full + flex-1 on ToggleGroups |
| 4 | WDL charts (custom and Recharts) share identical corner rounding and theme colors on bars | VERIFIED | Custom WDLBar: overflow-hidden rounded container; Recharts WDLBarChart: radius={[4,4,0,0]}/{[0,0,4,4]}; both use WDL_WIN/WDL_DRAW/WDL_LOSS constants |
| 5 | Active subtab is clearly highlighted | VERIFIED | TabsList variant="brand" in Openings (desktop line 529, mobile line 744) and Endgames (desktop line 270, mobile line 322); brand variant = charcoal-texture bar + bg-brand-brown-active! active state |
| 6 | Desktop nav header has no bottom border and active tab has lighter background | VERIFIED | border-b border-border removed from App.tsx NavHeader; active tab uses 'font-medium bg-white/10 text-foreground' |
| 7 | Logo and FlawChess text link to homepage on both desktop and mobile | VERIFIED | NavHeader: Link to="/" data-testid="nav-home" wraps img+span (line 83); MobileHeader: Link to="/" data-testid="nav-home-mobile" (line 131) |
| 8 | Collapsible sections are unified charcoal containers (header + content in one block) | VERIFIED | Dashboard, Openings, Endgames all wrap Collapsible in charcoal-texture rounded-md div |
| 9 | PRIMARY_BUTTON_CLASS uses CSS variable-based Tailwind utilities, not hardcoded hex | VERIFIED | theme.ts line 20: PRIMARY_BUTTON_CLASS = 'bg-brand-brown hover:bg-brand-brown-hover text-white' |
| 10 | Brand brown and charcoal CSS variables registered as Tailwind utilities | VERIFIED | index.css: --brand-brown, --charcoal, --brand-brown-active, --charcoal-hover in :root; --color-brand-brown etc. in @theme inline |

**Score:** 9/10 truths verified (Truth 1 is partial)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/index.css` | CSS variables for brand-brown, charcoal, sidebar-bg; charcoal-texture class | VERIFIED | --brand-brown: #8B5E3C, --charcoal: #161412, --sidebar-bg: #171513; .charcoal-texture with feTurbulence SVG data URI at line 149 |
| `frontend/src/lib/theme.ts` | PRIMARY_BUTTON_CLASS using bg-brand-brown utility | VERIFIED | Line 20: bg-brand-brown hover:bg-brand-brown-hover; no bg-[# hex brackets |
| `frontend/src/components/ui/tabs.tsx` | Brand variant with charcoal-texture bar and brand-brown active trigger | VERIFIED | Line 34: brand: "charcoal-texture gap-0"; line 71: brand active state with !important |
| `frontend/src/components/filters/FilterPanel.tsx` | Grid-based full-width filter button layout | VERIFIED (with gap) | Lines 126/152: grid grid-cols-4/grid-cols-2; lines 188/211: className="w-full" on ToggleGroups; BUT lines 138/164 introduce bg-[#171717] hardcoded |
| `frontend/src/components/charts/WDLBarChart.tsx` | Rounded corners on outermost stacked WDL bars | VERIFIED | Line 109: radius={[4,4,0,0]}; line 111: radius={[0,0,4,4]}; comment explaining approach |
| `frontend/src/App.tsx` | Nav header: active tab bg-white/10, no border, logo link | VERIFIED | Line 80: no border-b; line 96: bg-white/10; lines 83/129-135: Link to="/" on both headers |
| `frontend/src/pages/Dashboard.tsx` | Collapsibles in charcoal-texture containers | VERIFIED | Lines 297, 412, 439: three charcoal-texture rounded-md wrappers; additional nested charcoal-texture at 348 |
| `frontend/src/pages/Openings.tsx` | Collapsibles in charcoal-texture; TabsList variant="brand" | VERIFIED | 9 charcoal-texture instances; variant="brand" at lines 529 (desktop) and 744 (mobile) |
| `frontend/src/pages/Endgames.tsx` | Content sections in charcoal-texture; TabsList variant="brand" | VERIFIED | 8 charcoal-texture instances; variant="brand" at lines 270 (desktop) and 322 (mobile) |
| `frontend/src/pages/Import.tsx` | Import cards with charcoal-texture | VERIFIED | Lines 183, 226: charcoal-texture rounded-md on platform import cards |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/index.css` | `frontend/src/lib/theme.ts` | bg-brand-brown in PRIMARY_BUTTON_CLASS references --color-brand-brown CSS variable | WIRED | theme.ts:20 uses bg-brand-brown; index.css:124 registers --color-brand-brown: var(--brand-brown) |
| `frontend/src/index.css` | `frontend/src/components/ui/tabs.tsx` | bg-charcoal Tailwind utility in brand variant | WIRED | tabs.tsx:34 uses charcoal-texture class; index.css:149 defines .charcoal-texture with var(--charcoal) |
| `frontend/src/pages/Endgames.tsx` | `frontend/src/components/ui/tabs.tsx` | TabsList variant="brand" | WIRED | Endgames.tsx:270 uses variant="brand"; Endgames.tsx:322 uses variant="brand" (mobile) |
| `frontend/src/pages/Dashboard.tsx` | `frontend/src/index.css` | charcoal-texture CSS class | WIRED | Dashboard.tsx lines 297, 412, 439 all use charcoal-texture; class defined in index.css:149 |
| `frontend/src/pages/Openings.tsx` | `frontend/src/components/ui/tabs.tsx` | TabsList variant="brand" | WIRED | Openings.tsx:529 desktop + 744 mobile both use variant="brand" |

### Data-Flow Trace (Level 4)

Not applicable — this phase is CSS/component styling only. No data fetching, state, or API connections were modified.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frontend build compiles without errors | `npm run build` | "built in 4.38s" | PASS |
| All 38 frontend tests pass | `npm test` | "38 passed" | PASS |
| PRIMARY_BUTTON_CLASS uses CSS utility (no hex) | `grep 'bg-brand-brown' frontend/src/lib/theme.ts` | Line 20 matches | PASS |
| charcoal-texture class present with feTurbulence | `grep 'feTurbulence' frontend/src/index.css` | Line 160 matches | PASS |
| Recharts WDL bar has rounded corners | `grep 'radius' frontend/src/components/charts/WDLBarChart.tsx` | Lines 109, 111 match | PASS |
| Tabs brand variant defined | `grep 'brand.*charcoal-texture' frontend/src/components/ui/tabs.tsx` | Line 34 matches | PASS |
| Nav header has no border | `grep 'border-b border-border' frontend/src/App.tsx` | No output (removed) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| THEME-01 | 34-01 | All visual constants centralized in theme.ts and CSS variables | PARTIAL | Brand brown migrated; charcoal registered as CSS var. BUT #171717/#262626 hardcoded in toggle.tsx + FilterPanel.tsx, introduced during phase 34 iteration. REQUIREMENTS.md still shows Pending. |
| THEME-02 | 34-02 | Content containers with charcoal background and SVG feTurbulence noise texture | VERIFIED | charcoal-texture class implemented and applied across all 5 target pages. REQUIREMENTS.md correctly shows [x] Complete. |
| THEME-03 | 34-01 | Filter buttons span full sidebar width | VERIFIED | grid-cols-4/grid-cols-2 layout, w-full ToggleGroups. REQUIREMENTS.md incorrectly shows Pending — needs update. |
| THEME-04 | 34-01 | Consistent WDL chart corner rounding across all chart types | VERIFIED | Recharts radius props added per D-07/D-08 scope (corners only, not glass). Custom WDLBar uses overflow-hidden rounded container. REQUIREMENTS.md incorrectly shows Pending — needs update. |
| THEME-05 | 34-01, 34-02 | Active subtab clearly highlighted | VERIFIED | TabsList variant="brand" on Openings and Endgames; active state = bg-brand-brown-active!. REQUIREMENTS.md correctly shows [x] Complete. |

**Orphaned requirements from REQUIREMENTS.md:** None — all 5 THEME requirements are claimed by plans 34-01 and 34-02.

**REQUIREMENTS.md documentation gap:** THEME-01, THEME-03, THEME-04 show as Pending in REQUIREMENTS.md but were completed (THEME-03, THEME-04 fully; THEME-01 partially). This is a tracking failure.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/ui/toggle.tsx` | 13 | `bg-[#171717] hover:bg-[#262626]` hardcoded hex in component | WARNING | Contradicts THEME-01 goal of centralized constants; introduced during phase 34 visual iteration |
| `frontend/src/components/filters/FilterPanel.tsx` | 138, 164 | `bg-[#171717] hover:bg-[#262626]` hardcoded hex | WARNING | Same as above — matches toggle.tsx values but neither are in CSS variables |
| `frontend/src/components/charts/WDLBarChart.tsx` | 98-100 | `text-green-600`, `text-gray-400`, `text-red-600` in tooltip | INFO | Pre-existing before phase 34; tooltip uses approximate Tailwind colors instead of WDL_WIN/WDL_LOSS theme constants. Not introduced by this phase. |
| `.planning/REQUIREMENTS.md` | 12-16, 46-50 | THEME-01, THEME-03, THEME-04 still marked Pending | WARNING | Documentation tracking failure — phase declared these complete in summary frontmatter but REQUIREMENTS.md was not updated |

**Anti-pattern assessment:** The #171717 and #262626 values in toggle.tsx and FilterPanel.tsx are rendered as interactive button backgrounds. They are non-trivial visual constants that should follow the same CSS-variable pattern established in this phase. No data-fetching stubs. No empty implementations.

### Human Verification Required

#### 1. Charcoal Texture Visual Quality

**Test:** Open `npm run dev` and navigate to `/openings`. Inspect the sidebar collapsible sections and the main content area.
**Expected:** Content containers have a distinctly darker charcoal background (#161412) with a subtle noise texture overlay. The sidebar itself (`#171513`) should look slightly different from the charcoal containers.
**Why human:** SVG feTurbulence noise texture cannot be verified programmatically — it requires visual inspection to confirm the effect is visible and not too strong/subtle.

#### 2. Active Subtab Brown Highlight

**Test:** Navigate to `/openings` or `/endgames`, click between subtabs (e.g., Moves/Games/Openings on the Openings page).
**Expected:** The active subtab shows a clear brand brown (#6C4328) background with white text. Inactive tabs show the charcoal background. Switching tabs updates the highlight.
**Why human:** Requires browser interaction to confirm the !important override on brand variant active state actually displays correctly.

#### 3. Filter Button Full-Width Layout

**Test:** Open the Openings or Endgames page on desktop. Inspect the sidebar filter panel.
**Expected:** Time Control buttons (4 columns) and Platform buttons (2 columns) span the full sidebar width with equal column widths. The Rated and Opponent toggle groups also fill the full width.
**Why human:** Visual layout verification — grid width behavior depends on container size.

#### 4. Mobile Responsive Behavior

**Test:** Resize browser to <640px or use DevTools mobile emulation. Navigate between pages.
**Expected:** Charcoal containers, filter buttons, and tab highlighting all work correctly on narrow screens. Logo links to homepage on mobile header.
**Why human:** Responsive breakpoints require visual testing at multiple widths.

### Gaps Summary

Two gaps prevent marking this phase as fully complete:

**Gap 1 (WARNING): Ad-hoc hex values introduced during visual iteration**
During Phase 34's iterative visual verification, commits `4779b05` and `bec9ee3` introduced `bg-[#171717]` and `hover:bg-[#262626]` for inactive button backgrounds in `toggle.tsx` and `FilterPanel.tsx`. These values are not registered in `index.css` as CSS variables and are not in `theme.ts`. The existing `--charcoal-hover` variable is `#262220`, a different value. This directly contradicts THEME-01's success criterion of "no ad-hoc color values scattered across components."

Fix: Add `--inactive-bg: #171717` and `--inactive-bg-hover: #262626` to `:root` in `index.css`, register them in `@theme inline`, and replace the hardcoded bracket syntax in both files.

**Gap 2 (INFO): REQUIREMENTS.md tracking not updated**
THEME-01, THEME-03, and THEME-04 remain marked as `[ ]` Pending in `REQUIREMENTS.md` and "Pending" in the tracking table, even though the phase summaries declare them complete. THEME-03 (filter layout) and THEME-04 (WDL chart rounding) are fully done and should be checked off. THEME-01 should be checked off after Gap 1 is resolved.

This is a documentation gap only — the functional implementations are in place.

---

_Verified: 2026-03-28T12:49:42Z_
_Verifier: Claude (gsd-verifier)_
