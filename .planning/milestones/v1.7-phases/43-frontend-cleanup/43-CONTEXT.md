# Phase 43: Frontend Cleanup - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure button brand colors are fully driven by CSS variables with no hard-coded semantic color values remaining in components. Verify the existing CSS variable + Tailwind setup is clean and consistent. TOOL-04 (test coverage) dropped from scope.

</domain>

<decisions>
## Implementation Decisions

### Button Class Strategy
- **D-01:** `PRIMARY_BUTTON_CLASS` in `theme.ts` already references CSS-variable-backed Tailwind classes (`bg-brand-brown hover:bg-brand-brown-hover text-white`). The CSS variables (`--brand-brown`, `--brand-brown-hover`, `--brand-brown-active`) are defined in `index.css` and mapped in `@theme inline`. This pattern is functional — evaluate whether the JS constant adds value or if a simpler approach (e.g., Tailwind `@apply` utility) is cleaner.
- **D-02:** Audit all components for any remaining hard-coded hex/rgb values that represent brand/semantic colors. Any stray values should be migrated to CSS variables.
- **D-03:** The tab `brand` variant in `tabs.tsx` uses `bg-brand-brown-active!` — already CSS-variable-backed. Verify no hard-coded color values exist in the tab component.

### Test Coverage (TOOL-04)
- **D-04:** TOOL-04 dropped from this phase. User decided to skip test coverage analysis for the v1.7 milestone.

### Claude's Discretion
- Whether to keep `PRIMARY_BUTTON_CLASS` as a JS constant or replace with a CSS utility class / `@apply` approach — choose whatever is cleanest
- How to handle any stray hard-coded color values discovered during audit
- Whether index.css structure needs minor cleanup (note: oklch design tokens are shadcn/ui standard — do NOT restructure those)
- Overall approach to verifying brand color change propagation (only CSS variable edits needed)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme system
- `frontend/src/lib/theme.ts` — Brand button class constant, WDL colors, gauge colors, board colors
- `frontend/src/index.css` — CSS variables (`:root` and `.dark`), `@theme inline` Tailwind mappings, component layer styles

### Button usage (audit targets)
- `frontend/src/pages/Home.tsx` — Uses `PRIMARY_BUTTON_CLASS` (lines 139, 411)
- `frontend/src/pages/Openings.tsx` — Uses `PRIMARY_BUTTON_CLASS` (lines 543, 552, 986, 995)
- `frontend/src/components/layout/PublicHeader.tsx` — Uses `PRIMARY_BUTTON_CLASS` (line 28)
- `frontend/src/components/ui/tabs.tsx` — Brand tab variant with `bg-brand-brown-active!` (line 71)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CSS variables already defined: `--brand-brown`, `--brand-brown-hover`, `--brand-brown-active` in `:root`
- Tailwind mappings already registered: `--color-brand-brown`, `--color-brand-brown-hover`, `--color-brand-brown-active` in `@theme inline`
- `PRIMARY_BUTTON_CLASS` constant centralizes button styling — used in 3 files (5 instances)

### Established Patterns
- shadcn/ui design tokens use oklch color space in `:root` / `.dark` — these are standard and must not be restructured
- Custom app colors (charcoal, brand-brown, inactive-bg, etc.) follow the same pattern: CSS variable in `:root` → `@theme inline` mapping → Tailwind class usage
- Theme constants in `theme.ts` for JS-accessible values (WDL colors, board colors, gauge zones)

### Integration Points
- `PRIMARY_BUTTON_CLASS` is imported in 3 files — any refactor must update all consumers
- `tabs.tsx` brand variant references `bg-brand-brown-active!` directly in Tailwind classes
- No dark-mode variants exist for brand colors (same values in light/dark) — this is intentional

</code_context>

<specifics>
## Specific Ideas

- User noted index.css looks messy with many similar whites/greys — these are shadcn/ui standard design tokens and should NOT be restructured
- User explicitly delegated all technical decisions: "I'll leave the restructuring and cleanup to you and trust your judgement"
- The phase is small — brand color CSS variable migration is ~90% complete already

</specifics>

<deferred>
## Deferred Ideas

- **Test coverage analysis (TOOL-04)** — User decided to drop from v1.7 milestone; can revisit in a future milestone

</deferred>

---

*Phase: 43-frontend-cleanup*
*Context gathered: 2026-04-03*
