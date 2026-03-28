# Phase 33: Homepage, README & SEO Update - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Update homepage content, project README, and SEO metadata to showcase v1.5 features (endgame analytics, engine analysis import) alongside existing opening analysis features. The homepage is the primary deliverable; README, SEO, and FAQ updates derive from homepage changes.

</domain>

<decisions>
## Implementation Decisions

### Homepage Feature Sections
- **D-01:** Consolidate from 6 feature sections to 5, grouping related capabilities:
  1. **Interactive Opening Explorer** — combines move explorer + opponent scouting
  2. **Opening Comparison and Tracking** — weakness detection, win rate trends
  3. **System Opening Grouping** — analyzing opening systems (e.g. the London)
  4. **Endgame Analysis** — new v1.5 endgame analytics (new section)
  5. **Cross-Platform with Powerful Filters** — chess.com + lichess import, time control/color/recency filters
- **D-02:** Noun-based headings (current style), not verb-based action phrases
- **D-03:** All landscape screenshots — no portrait orientation. Simplifies the grid layout (remove conditional landscape/portrait column ratio logic)
- **D-04:** All 5 sections get fresh new screenshots (no reuse of existing screenshots)

### Hero Section
- **D-05:** Keep the tagline ("Engines are flawless, humans play FlawChess") — it's brand identity
- **D-06:** Update the hero subtitle to broaden scope beyond openings — mention endgames and engine analysis alongside opening analysis

### Claude's Discretion
- README content and structure (no root README exists currently — only Vite boilerplate at `frontend/README.md`)
- SEO meta tags updates (title, description, OG tags, Twitter cards) — should reflect broadened feature set
- FAQ updates — add or update questions to cover endgame analytics and engine analysis
- OG image — assess whether current `og-image.jpg` needs updating
- Callout pills below hero CTA — update if needed to reflect new positioning
- Description text for each consolidated feature section

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Homepage
- `frontend/src/pages/Home.tsx` — Current homepage component with FEATURES array, hero section, FAQ accordion, footer CTA
- `frontend/src/components/layout/PublicHeader.tsx` — Public header used on homepage

### SEO & Meta
- `frontend/index.html` — Meta tags, OG tags, Twitter cards, page title
- `frontend/src/prerender.tsx` — SSR/prerender setup for homepage and privacy page (SEO-critical)

### Theme & Styling
- `frontend/src/lib/theme.ts` — Theme constants including PRIMARY_BUTTON_CLASS

### Existing Screenshots
- `frontend/public/screenshots/` — Current screenshot assets (all to be replaced)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PublicHeader` component — used on homepage, keep as-is
- `Accordion` (shadcn/ui) — used for FAQ section
- `Button` with `PRIMARY_BUTTON_CLASS` — hero and footer CTA buttons
- `prerender.tsx` — SSR for homepage already set up, will render updated content automatically

### Established Patterns
- FEATURES array in `Home.tsx` defines feature sections declaratively (slug, icon, heading, desc, screenshot, imagePosition)
- Alternating image left/right layout with responsive grid
- Lucide icons for each feature section
- `data-testid` on all interactive elements and sections

### Integration Points
- `FEATURES` array is the single source of truth for feature sections — update this array to change homepage content
- `index.html` meta tags are static (not dynamically generated) — update directly
- Screenshot files in `frontend/public/screenshots/` — replace with new landscape images
- `imagePosition` alternation and `orientation` field in FEATURES can be simplified since all screenshots are now landscape

</code_context>

<specifics>
## Specific Ideas

- User explicitly listed the 5 consolidated sections with their groupings and naming
- All screenshots must be landscape orientation — the current portrait/landscape alternation pattern should be removed
- The FEATURES type can drop the `orientation` field (or always set to `'landscape'`) and simplify grid column logic

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-homepage-readme-seo-update*
*Context gathered: 2026-03-27*
