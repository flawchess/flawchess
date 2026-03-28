# Phase 33: Homepage, README & SEO Update - Research

**Researched:** 2026-03-27
**Domain:** Frontend content/copy, SEO meta tags, React component refactor, README documentation
**Confidence:** HIGH — all findings come from direct code inspection of the live codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Consolidate from 6 feature sections to 5, grouping related capabilities:
  1. **Interactive Opening Explorer** — combines move explorer + opponent scouting
  2. **Opening Comparison and Tracking** — weakness detection, win rate trends
  3. **System Opening Grouping** — analyzing opening systems (e.g. the London)
  4. **Endgame Analysis** — new v1.5 endgame analytics (new section)
  5. **Cross-Platform with Powerful Filters** — chess.com + lichess import, time control/color/recency filters
- **D-02:** Noun-based headings (current style), not verb-based action phrases
- **D-03:** All landscape screenshots — no portrait orientation. Simplifies the grid layout (remove conditional landscape/portrait column ratio logic)
- **D-04:** All 5 sections get fresh new screenshots (no reuse of existing screenshots)
- **D-05:** Keep the tagline ("Engines are flawless, humans play FlawChess") — it's brand identity
- **D-06:** Update the hero subtitle to broaden scope beyond openings — mention endgames and engine analysis alongside opening analysis

### Claude's Discretion

- README content and structure (no root README exists currently — only Vite boilerplate at `frontend/README.md`)
- SEO meta tags updates (title, description, OG tags, Twitter cards) — should reflect broadened feature set
- FAQ updates — add or update questions to cover endgame analytics and engine analysis
- OG image — assess whether current `og-image.jpg` needs updating
- Callout pills below hero CTA — update if needed to reflect new positioning
- Description text for each consolidated feature section

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 33 is a pure content/copy update phase — no new backend logic, no new React component architecture. The work falls into four independent streams: (1) restructuring `Home.tsx`'s FEATURES array from 6 to 5 sections with simplified landscape-only layout logic, (2) updating hero subtitle copy and callout pills, (3) updating `index.html` SEO metadata, and (4) updating the root `README.md` feature list to reflect v1.5 capabilities.

Screenshots are explicitly out of scope for implementation — D-04 says all 5 sections need fresh screenshots, but screenshots are a human-captured deliverable. The plan must include a clear handoff: code lands with placeholder screenshot paths, human takes screenshots and drops files in `frontend/public/screenshots/`. Alternatively, the plan can include a placeholder/stub task noting the screenshot dependency.

The layout simplification is mechanical: with all screenshots now landscape, the conditional `gridCols` / `gridColsFlipped` logic and the `orientation` field on the FEATURES type can be removed. All five sections use the same `lg:grid-cols-[2fr_3fr]` / `lg:grid-cols-[3fr_2fr]` pair, toggled only by `imagePosition`.

**Primary recommendation:** Implement FEATURES array changes and layout cleanup first (no screenshot files needed), then update all copy/meta in a single commit per stream. Screenshot replacement is a final manual step.

---

## Standard Stack

No new libraries required. All work uses existing tooling:

### Core (already installed)
| Library | Purpose | Notes |
|---------|---------|-------|
| React 19 + TypeScript | Component authoring | FEATURES array is statically typed |
| Lucide (already in project) | Feature section icons | 5 icons needed — check current imports |
| Tailwind CSS | Layout classes | Simplified grid cols when portrait removed |
| Vite 5 + prerender plugin | Static prerender of homepage | Already configured in `prerender.tsx` |

No `npm install` needed.

---

## Architecture Patterns

### Current FEATURES Array Structure (6 sections)

```typescript
// frontend/src/pages/Home.tsx — current shape
const FEATURES: {
  slug: string;
  icon: LucideIcon;
  heading: string;
  desc: string;
  screenshot: { src: string; alt: string; orientation: 'landscape' | 'portrait' };
  imagePosition: 'left' | 'right';
}[] = [ /* 6 entries */ ];
```

The `orientation` field drives conditional grid column ratios:
- Landscape: `lg:grid-cols-[2fr_3fr]` (40% text / 60% image)
- Portrait: `lg:grid-cols-[11fr_9fr]` (55% text / 45% image, capped width on image)

With D-03 (all landscape), this conditional logic disappears entirely.

### Target FEATURES Array Structure (5 sections)

```typescript
// Simplified — orientation field removed, always landscape ratio
const FEATURES: {
  slug: string;
  icon: LucideIcon;
  heading: string;
  desc: string;
  screenshot: { src: string; alt: string };
  imagePosition: 'left' | 'right';
}[] = [
  { slug: 'opening-explorer',    imagePosition: 'right', ... },
  { slug: 'opening-comparison',  imagePosition: 'left',  ... },
  { slug: 'system-openings',     imagePosition: 'right', ... },
  { slug: 'endgame-analysis',    imagePosition: 'left',  ... },
  { slug: 'cross-platform',      imagePosition: 'right', ... },
];
```

### Simplified Grid Logic (render section)

Current code inside the FEATURES `.map()`:
```typescript
const isLandscape = screenshot.orientation === 'landscape';
const gridCols = isLandscape ? 'lg:grid-cols-[2fr_3fr]' : 'lg:grid-cols-[11fr_9fr]';
const gridColsFlipped = isLandscape ? 'lg:grid-cols-[3fr_2fr]' : 'lg:grid-cols-[9fr_11fr]';
// ...
className={cn('grid gap-8 lg:gap-12 items-center',
  imagePosition === 'left' ? gridColsFlipped : gridCols)}
```

Simplified target (no orientation conditionals):
```typescript
// All landscape — single fixed ratio
const gridCols = imagePosition === 'left' ? 'lg:grid-cols-[3fr_2fr]' : 'lg:grid-cols-[2fr_3fr]';
// ...
className={cn('grid gap-8 lg:gap-12 items-center', gridCols)}
```

Also remove the `max-w-xs` portrait cap on image block:
```typescript
// Remove: isLandscape ? 'w-full' : 'w-full max-w-xs'
// Replace with:
className="rounded-lg border border-border shadow-md w-full"
```

### Icon Selection

Current icons used: `ArrowRightLeft, Eye, Target, Layers, SlidersHorizontal, Swords`

For 5 new sections, one icon needs to be chosen for the new "Endgame Analysis" section. Existing imports already cover the other sections. Candidates from Lucide already in the dependency tree: `BarChart2`, `TrendingUp`, `Activity`, `Layers` (already used for cross-platform). The plan should confirm the icon choice — `BarChart2` or `Activity` are natural fits for endgame stats.

---

## Existing Content Inventory

### Current 6 FEATURES sections

| Slug | Heading | Screenshot | Orientation |
|------|---------|-----------|-------------|
| move-explorer | Interactive move explorer | board-and-move-explorer.png | landscape (1200x588) |
| scout | Scout your opponents | chess-board-and-moves.png | portrait (800x1088) |
| weaknesses | Find weaknesses in your openings | win-rate-over-time.png | landscape (1200x528) |
| filters | Powerful filters | filters.png | portrait (800x858) |
| system-openings | System opening analysis | position-bookmarks.png | portrait (800x951) |
| cross-platform | Cross-platform analysis | game-import.png | landscape (1200x569) |

All 6 existing screenshots are to be replaced (D-04). None can be reused.

### Planned 5 New Sections (from D-01)

| # | Slug (recommended) | Heading | Screenshot path (to be created) | Notes |
|---|-------------------|---------|--------------------------------|-------|
| 1 | opening-explorer | Interactive Opening Explorer | /screenshots/opening-explorer.png | Merges move-explorer + scout |
| 2 | opening-comparison | Opening Comparison and Tracking | /screenshots/opening-comparison.png | Win rate trends, weakness detection |
| 3 | system-openings | System Opening Grouping | /screenshots/system-openings.png | London-style analysis |
| 4 | endgame-analysis | Endgame Analysis | /screenshots/endgame-analysis.png | New v1.5 section |
| 5 | cross-platform | Cross-Platform with Powerful Filters | /screenshots/cross-platform.png | Import page + filter UI |

New filenames avoid collision with old filenames. Old files can be deleted after new ones land.

### Screenshot Dependency

Screenshot replacement is a human task (cannot be automated). The plan must structure the work so:
1. Code changes (FEATURES array, layout simplification, copy) are committed with placeholder or temporary screenshot paths — either pointing to old files as stubs or using a clearly named placeholder.
2. Human takes fresh landscape screenshots and places them at the new paths.
3. A final cleanup task removes old screenshot files.

The simplest approach: reference the new filenames in code from the start (e.g. `/screenshots/opening-explorer.png`), noting they are pending. The site still loads if files are missing (broken image is acceptable during development).

---

## Current SEO State (index.html)

```html
<title>FlawChess — Chess Opening Analysis</title>
<meta name="description" content="Analyze your chess openings by position, not just name. Import games from chess.com and lichess to discover where you really lose." />

<!-- OG -->
<meta property="og:title" content="FlawChess — Chess Opening Analysis" />
<meta property="og:description" content="Analyze your chess openings by position, not just name. Import games from chess.com and lichess to discover where you really lose." />
<meta property="og:image" content="https://flawchess.com/og-image.jpg" />

<!-- Twitter/X -->
<meta name="twitter:title" content="FlawChess — Chess Opening Analysis" />
<meta name="twitter:description" content="Analyze your chess openings by position, not just name. Import games from chess.com and lichess to discover where you really lose." />
<meta name="twitter:image" content="https://flawchess.com/og-image.jpg" />
```

All three (title, og:title, twitter:title) currently say "Chess Opening Analysis" — too narrow for v1.5. The description copy is duplicated in three places (description, og:description, twitter:description) — all three must be updated consistently.

### Recommended Target SEO Copy

**Title:** `FlawChess — Chess Analysis for Human Players`
(or: `FlawChess — Opening & Endgame Analysis`)

**Description (<=155 chars for Google snippet):** A ~150-character description that mentions openings, endgames, cross-platform import from chess.com/lichess.

Example: `"Analyze your openings and endgames by position, not just name. Import games from chess.com and lichess to find where you really win and lose."`
(139 chars — fits)

The planner should pick exact copy; the above is a concrete starting point.

### OG Image (og-image.jpg)

Current: `1200x630` — correct dimensions for OG (standard is 1200x630). The image itself shows opening/board content. Whether to replace it is left to Claude's discretion (CONTEXT.md). Recommendation: assess the current image after viewing it — if it still represents the product accurately, keep it. If it is opening-only, a new image showing the endgame tab would be more representative. This is a medium-effort task (requires screenshot + image composition) and can be deferred if time-constrained.

---

## Current Hero Section

```
Tagline (h1): "Engines are flawless, humans play FlawChess"
Subtitle (p): "Analyze your opening positions by move, not just name. Import games from chess.com and lichess to discover where you really lose."
Callout pills: "Free to use", "Open source", "Mobile friendly"
```

Per D-05, tagline is unchanged. Per D-06, subtitle must be broadened to mention endgames and engine analysis. The callout pills are at Claude's discretion — "No credit card" could replace "Free to use" (more specific) or a fourth pill "Endgame analytics" added.

### Hero Subtitle — Recommended Target

The current subtitle is opening-focused. Broadened version:
> "Analyze your opening positions and endgames by move, not just name. Import games from chess.com and lichess — discover where you win, where you lose, and how your chess evolves."

Or more concise:
> "Import games from chess.com and lichess. Explore openings by position, track endgame performance, and find exactly where you win and lose."

The planner should draft the final copy using this guidance. Keep it under 2 sentences.

---

## Current README State

Root `README.md` exists with content. It already has:
- Logo + badges + tagline
- "What is FlawChess?" paragraph — opening-focused only
- Feature bullet list — no endgame/engine mentions
- Tech stack table
- Getting Started / Running Tests / Linting sections
- Contributing / License / Links

`frontend/README.md` — NOT inspected but CONTEXT.md notes it's "only Vite boilerplate" — can be replaced or left alone. Decision: the plan should update the root README; `frontend/README.md` can remain as-is (it's not user-facing documentation).

### README Changes Required

1. **"What is FlawChess?" paragraph** — add endgame analytics and engine analysis alongside opening analysis
2. **Feature bullet list** — add:
   - "Endgame analytics — win/draw/loss rates by endgame type, conversion and recovery statistics, performance gauges"
   - Update "Find weaknesses in your openings" to mention win rate trends
   - Consider merging "Scout your opponents" into the move explorer bullet (mirrors D-01)
3. **Screenshot** — the inline `board-and-move-explorer.png` path will break when screenshots are replaced. Either update to new filename or remove the inline screenshot from README (simpler, avoids ongoing maintenance).

---

## FAQ Section

Current 5 FAQ items: data access, free?, mobile?, feature requests, who develops it.

Per CONTEXT.md (Claude's discretion), add or update questions for endgame analytics and engine analysis. Recommendations:

**New FAQ candidate — Endgame analytics:**
> Q: What endgame analytics does FlawChess offer?
> A: FlawChess tracks your win/draw/loss rates by endgame type (rook, minor piece, pawn, queen, etc.), plus conversion rates (winning when up material) and recovery rates (surviving when down material). Statistics are filterable by time control and color.

**New FAQ candidate — Engine analysis:**
> Q: Does FlawChess use an engine to analyze my games?
> A: FlawChess imports pre-existing engine evaluations from lichess (accuracy, ACPL, mistake counts) when available for your games. It does not run Stockfish locally — analysis must already exist on lichess.

Note: ENGINE-01/02 requirements are still "Pending" per REQUIREMENTS.md — engine analysis import is not yet complete. The FAQ should reflect what is actually deployed, not what is planned. If engine import is not live by the time this phase ships, omit or softly phrase the engine FAQ. The endgame FAQ is safe to add.

---

## Prerender Considerations

`frontend/src/prerender.tsx` renders `HomePageContent` at build time for SEO. Since `HomePageContent` is a pure component (no async data), changes to FEATURES array content and hero copy will be reflected automatically in the prerendered HTML with no changes to `prerender.tsx` itself.

`index.html` meta tags are NOT injected by prerender — they are static in the HTML file. Both the prerendered HTML (for crawlers) and `index.html` (for direct browser loads) will reflect the changes after build.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Icon for endgame section | Custom SVG | Lucide icon already in dep tree |
| SEO meta tag management | Dynamic injection | Direct edit of index.html (already the pattern) |
| Screenshot optimization | Custom pipeline | Standard PNG — same as existing screenshots |

---

## Common Pitfalls

### Pitfall 1: Inconsistent copy across title/og/twitter
**What goes wrong:** Updating `<title>` but forgetting to update `og:title` and `twitter:title` in `index.html` — they are three separate attributes.
**How to avoid:** Update all three in one pass; grep for the old title string to confirm all instances are replaced.

### Pitfall 2: Old screenshot filenames left in README
**What goes wrong:** `README.md` references `frontend/public/screenshots/board-and-move-explorer.png` inline. Once that file is replaced/removed, the GitHub README shows a broken image.
**How to avoid:** Either update the path in README to match the new filename, or remove the inline screenshot from README entirely.

### Pitfall 3: data-testid mismatch after slug changes
**What goes wrong:** Feature sections use `data-testid={`feature-${slug}`}`. Renaming slugs (e.g. `move-explorer` → `opening-explorer`) changes testids. If any external tests or browser automation reference these testids, they break.
**How to avoid:** This is acceptable churn since slugs are being intentionally restructured. Note new testids in the plan for documentation.

### Pitfall 4: FAQ added for unshipped features
**What goes wrong:** Adding a "Does FlawChess analyze my games with an engine?" FAQ when ENGINE-01/02 are still Pending — misleads users.
**How to avoid:** Only add FAQ items for deployed features. Check REQUIREMENTS.md status column before drafting FAQ copy. Engine analysis FAQ should be deferred until Phase 29 ships.

### Pitfall 5: Portrait image classes not fully removed
**What goes wrong:** Removing the `orientation` field from FEATURES type but leaving the `isLandscape ? 'w-full' : 'w-full max-w-xs'` conditional in the image block render.
**How to avoid:** Search for `isLandscape` and `orientation` in `Home.tsx` after changes — both should be gone.

---

## Code Examples

### Minimal FEATURES entry (new shape)

```typescript
// Source: direct inspection of frontend/src/pages/Home.tsx
{
  slug: 'endgame-analysis',
  icon: BarChart2,            // or Activity — planner's choice
  heading: 'Endgame Analysis',
  desc: 'Track your win/draw/loss rates by endgame type. See where you convert material advantages and where you recover from deficits.',
  screenshot: { src: '/screenshots/endgame-analysis.png', alt: 'Endgame analytics showing WDL rates by endgame category' },
  imagePosition: 'left',
}
```

### Simplified grid logic (after orientation removal)

```typescript
// Replace the isLandscape / gridCols / gridColsFlipped block with:
const gridCols = imagePosition === 'left'
  ? 'lg:grid-cols-[3fr_2fr]'
  : 'lg:grid-cols-[2fr_3fr]';

// In JSX — remove orientation-conditional max-w-xs:
<img
  src={screenshot.src}
  alt={screenshot.alt}
  className="rounded-lg border border-border shadow-md w-full"
/>
```

### SEO meta update pattern

```html
<!-- index.html — update all three title locations, all three description locations -->
<title>FlawChess — Chess Analysis for Human Players</title>
<meta name="description" content="[new description]" />
<meta property="og:title" content="FlawChess — Chess Analysis for Human Players" />
<meta property="og:description" content="[new description]" />
<meta name="twitter:title" content="FlawChess — Chess Analysis for Human Players" />
<meta name="twitter:description" content="[new description]" />
```

---

## Environment Availability

Step 2.6: SKIPPED — this phase contains no external dependencies. All changes are static file edits (TypeScript, HTML, Markdown). No CLI tools, databases, or external services are required for implementation.

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (frontend, via `npm test`) |
| Config file | `frontend/vite.config.ts` (Vitest config co-located) |
| Quick run command | `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm test -- --run` |
| Full suite command | `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm test -- --run` |

### Phase Requirements → Test Map

Phase 33 has no formal REQ IDs (phase requirement IDs: null). The success criteria from the phase description are:

| Criterion | Behavior | Test Type | Automated Command | Notes |
|-----------|----------|-----------|-------------------|-------|
| SC-01 | Homepage has 5 feature sections (not 6) | unit | Check FEATURES.length === 5 in Home.tsx | Can be a snapshot or count assertion |
| SC-02 | No `orientation` field or `isLandscape` logic in Home.tsx | linting/review | `grep -c "isLandscape\|orientation" frontend/src/pages/Home.tsx` → 0 | Manual verification |
| SC-03 | Meta title/description updated in index.html | review | `grep "Opening Analysis" frontend/index.html` → 0 results | Manual verification |
| SC-04 | README features list includes endgame analytics | review | `grep -i "endgame" README.md` → match | Manual verification |
| SC-05 | Prerender still builds successfully | build | `cd frontend && npm run build` | Integration check |

These are mostly content/copy checks — not amenable to automated unit tests. The meaningful automated check is `npm run build` succeeding (catches TypeScript errors in the updated FEATURES array and import changes).

### Wave 0 Gaps

No test framework gaps — existing frontend test infrastructure is sufficient. The primary verification is `npm run build` passing after changes, plus manual review of the rendered homepage.

No new test files are needed for this phase.

*(No Wave 0 gaps — build + manual review is appropriate for content/copy changes)*

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| 6 feature sections | 5 consolidated sections | D-01 |
| Mixed landscape/portrait screenshots | All landscape | D-03 |
| Conditional grid column ratios | Single fixed ratio | Simplification from D-03 |
| "Chess Opening Analysis" branding | Broader "Chess Analysis" scope | v1.5 feature expansion |

---

## Open Questions

1. **Hero subtitle exact copy**
   - What we know: Must mention openings, endgames, engine analysis (D-06)
   - What's unclear: Exact wording (Claude's discretion per CONTEXT.md)
   - Recommendation: Planner drafts 2-3 options and picks the most concise; keep under 40 words

2. **OG image replacement**
   - What we know: Current og-image.jpg is 1200x630 (correct dimensions); content is opening/board focused
   - What's unclear: Whether the user wants to replace it this phase
   - Recommendation: Mark as optional task in the plan. If retained, no action needed. If replaced, it requires human screenshot capture + image editing.

3. **Endgame section icon**
   - What we know: Lucide is already a dependency; `BarChart2` and `Activity` are natural choices
   - What's unclear: User preference
   - Recommendation: Default to `BarChart2` (bar charts = statistics visualization); switch if user prefers

4. **Engine analysis FAQ**
   - What we know: ENGINE-01/02 are Pending in REQUIREMENTS.md — not yet deployed
   - What's unclear: Will Phase 29 ship before or with Phase 33?
   - Recommendation: Omit engine analysis FAQ for now; add only endgame analytics FAQ. Revisit when Phase 29 ships.

5. **`frontend/README.md` (Vite boilerplate)**
   - What we know: It exists, contains only Vite template boilerplate
   - What's unclear: Should it be replaced with project-specific content or left alone?
   - Recommendation: Replace with a brief redirect note pointing to root README, or delete its content. Low priority — not user-facing.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `frontend/src/pages/Home.tsx` — complete FEATURES array and render logic
- Direct code inspection: `frontend/index.html` — all current meta tags
- Direct code inspection: `README.md` — current feature list and structure
- Direct code inspection: `frontend/src/prerender.tsx` — SSR setup confirmation
- Direct code inspection: `.planning/phases/33-homepage-readme-seo-update/33-CONTEXT.md` — locked decisions
- Screenshot dimension audit via ImageMagick `identify` — confirmed 3 landscape, 3 portrait in current set

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md traceability table — used to determine ENGINE-01/02 deployment status (Pending)

---

## Project Constraints (from CLAUDE.md)

These directives apply to this phase:

- **data-testid on interactive elements** — feature section slugs change (e.g. `feature-move-explorer` → `feature-opening-explorer`); updated testids are acceptable churn
- **Theme constants in theme.ts** — no new color values introduced in this phase; not applicable
- **No magic numbers** — grid ratio strings (`2fr_3fr`) should be extracted as named constants if the planner prefers, though they are already self-documenting
- **Always check mobile variants** — the feature section grid is already responsive (mobile: single column, always text-first); the simplification preserves this behavior
- **Semantic HTML** — no new interactive elements introduced; existing structure is compliant
- **Noun-based headings** — D-02 locks this; all 5 section headings must be noun phrases (already the case for all current headings)

---

## Metadata

**Confidence breakdown:**
- Existing code structure: HIGH — all files inspected directly
- Screenshot dimensions/files: HIGH — measured via ImageMagick
- SEO copy recommendations: MEDIUM — based on best practices and phase goals, not verified against a ranking tool
- FAQ content accuracy: HIGH for endgame (shipped); LOW for engine analysis (ENGINE-01/02 Pending)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain — content/copy changes only)
