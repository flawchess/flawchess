---
phase: 66
slug: frontend-endgameinsightsblock-beta-flag
status: draft
shadcn_initialized: true
preset: radix-nova (frontend/components.json)
created: 2026-04-21
---

# Phase 66 — UI Design Contract

> Visual and interaction contract for the Endgame Insights block (top-of-tab overview card + per-section headlines) and the `beta_enabled` user flag. Consumes upstream CONTEXT.md D-01..D-19; this file codifies only what "Claude's Discretion" left open.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn (existing project) |
| Preset | `radix-nova` (neutral base color, cssVariables, lucide icons, prefix=none) — `frontend/components.json` |
| Component library | Radix via shadcn (`@/components/ui/*`) |
| Icon library | `lucide-react` (already used across Endgames.tsx — e.g. `HelpCircle`) |
| Font | `Nunito Sans` (body, via `--font-sans` in `index.css`); `Fredoka` via `.font-brand` (not used in this block) |
| Theme tokens | All colours come from `frontend/src/lib/theme.ts` or existing CSS variables in `src/index.css` (`--foreground`, `--muted-foreground`, `--border`, `--charcoal`, `--brand-brown`, `--destructive`). No new theme constants required for this phase. |

No new shadcn components are added. The block reuses the existing `Button` variants (`default`, `brand-outline`), `charcoal-texture` utility class, standard `h2` treatment, and inline-SVG lucide icons.

---

## Spacing Scale

Declared values (Tailwind default 4px unit scale — inherited from tailwindcss 4; no project overrides):

| Token | Value | Usage in this phase |
|-------|-------|---------------------|
| 1 | 4px | Outdated indicator icon ↔ text gap |
| 2 | 8px | Bullet-list indent, button icon gap, vertical gap between headline and bullets |
| 3 | 12px | Gap between overview paragraph and Regenerate button row |
| 4 | 16px | Inside padding of the top Insights card (`p-4` — matches existing `charcoal-texture rounded-md p-4`) |
| 6 | 24px | Vertical gap between loading-skeleton blocks |
| (inherit) | — | Outer gap between the Insights top card and the first H2 — reuses the parent `flex flex-col gap-4` on `statisticsContent` (no new spacing) |

Exceptions: none. Block composes existing 4px-multiple spacing tokens; no bespoke values.

SectionInsight slot spacing inside each existing H2 group:
- `mt-0` directly under the H2 (the H2 already provides `mt-2` above itself), `mb-3` between the SectionInsight and the first chart's `charcoal-texture` card below it.
- Bullets use `<ul>` with `list-disc list-outside pl-5` (Tailwind defaults) — 20px indent, 4px bullet-to-text gap.

Outdated indicator placement:
- Inline, right of the top card's "Insights" H2 (desktop); wraps below on narrow viewports. Gap `gap-2` (8px) between H2 text and indicator.

---

## Typography

All sizes come from Tailwind's default scale; no custom size/weight combinations.

| Role | Tailwind class | Size | Weight | Line Height | Usage |
|------|----------------|------|--------|-------------|-------|
| Block H2 ("Insights") | `text-lg font-semibold text-foreground mt-2` | 18px | 600 | 1.75 | Top card heading — matches the 4 existing Endgame H2s verbatim (`Endgames.tsx:230,291,313,338`) |
| Blurb (pre-click) | `text-sm text-muted-foreground` | 14px | 400 | 1.25 | 1-line explainer under the H2 before first Generate click |
| Overview paragraph | `text-sm text-foreground leading-relaxed` | 14px | 400 | 1.625 | Post-click overview (≤150 words, 1–2 paragraphs per INS-02). `leading-relaxed` (1.625) chosen over `leading-normal` (1.5) because paragraph flow is the dominant rendering mode |
| SectionInsight headline | `text-sm font-semibold text-foreground` | 14px | 600 | 1.25 | ≤12-word per-section headline inside each H2 group |
| SectionInsight bullet | `text-sm text-muted-foreground` | 14px | 400 | 1.5 | 0–2 bullets per section, ≤20 words each |
| Stale banner copy | `text-xs text-muted-foreground` | 12px | 400 | 1 | Muted one-liner above overview when `status=="stale_rate_limited"` |
| Outdated indicator | `text-xs text-muted-foreground` | 12px | 500 | 1 | Pill-like caption with icon — "Filters changed — click Regenerate to update" |
| Error copy | `text-sm text-muted-foreground` | 14px | 400 | 1.5 | Locked D-11 copy + (optional) D-14 retry line |
| Error headline | `text-base font-medium text-foreground` | 16px | 500 | 1.5 | "Couldn't generate insights." first line — matches the existing error-state pattern at `Endgames.tsx:357-362` |

Locked decisions:
- No new `text-*` size beyond what the Endgame tab already renders.
- Weight palette for this block: **400 (regular) + 500 (medium) + 600 (semibold)**. 500 only appears on the outdated indicator and the error headline (both precedented in `Endgames.tsx`).
- No italic, no underline except focus-ring behaviour inherited from the Button component.

---

## Color

60/30/10 audit for this block, pulling tokens from `src/index.css` dark theme (the production surface — the app ships in dark mode on the Endgame tab):

| Role | Token | Value (dark theme) | Usage in this phase |
|------|-------|--------------------|---------------------|
| Dominant (60%) | `--background` | `oklch(0.145 0 0)` | Page background behind the charcoal top card |
| Secondary (30%) | `--charcoal` | `#161412` | Top Insights card surface (via existing `.charcoal-texture`); also all sibling chart cards. The SectionInsight slots render ON this charcoal inside each H2 group's first child |
| Accent (10%) | `--brand-brown` / `--brand-brown-light` | `#8B5E3C` / `#A07850` | Generate/Regenerate button hover surface (via `brand-outline` variant when rendered in error state); Try-again button border + text; outdated-indicator dot colour (via `FILTER_MODIFIED_DOT = oklch(0.55 0.08 55)` from `theme.ts` — reuses the existing filter-modified dot, semantically identical — "filters have changed since last commit") |
| Destructive | `--destructive` | `oklch(0.704 0.191 22.216)` | Not used in this phase. D-11 failure copy is rendered with neutral `text-muted-foreground`, matching the existing error-state voice at `Endgames.tsx:357-362`. No red-on-red error surface. |

Accent reserved for:
1. The **primary "Generate insights" button** (pre-click) and **"Regenerate" button** (post-click) — both `Button variant="default"`, which is the project's canonical primary CTA treatment.
2. The **"[Try again]" button** on error — `Button variant="brand-outline"` (secondary action on a failure surface per CLAUDE.md §Frontend "Primary vs secondary buttons").
3. The **outdated indicator dot** — reuses `FILTER_MODIFIED_DOT` (brand brown mid) from `theme.ts`, applied via the existing `bg-brand-brown` Tailwind utility. Rationale: semantically identical to the filter-modified indicator that already pulses on filter-bar triggers (established 260411 quick task), so users already read brand-brown-dot as "pending recompute required".

Explicitly NOT accent:
- The SectionInsight headline and bullets — foreground / muted-foreground only. The existing H2 charcoal-texture grouping owns the visual hierarchy; adding accent colour to per-section insight text would compete with the chart data below it.
- The stale-rate-limited banner — muted-foreground only, no amber / warning colour. The content is valid; the banner is informational, not a warning.

Theme-constant rule: any colour referenced in the implementation MUST be imported from `frontend/src/lib/theme.ts` or applied via an existing Tailwind utility backed by a CSS variable in `src/index.css`. No inline hex, no inline `oklch()`, no new colour constants added to `theme.ts` for this phase.

---

## Copywriting Contract

Locked strings — render exactly as shown (no interpolation except where `{N}` is explicitly parameterised).

| Element | Copy | Source |
|---------|------|--------|
| Block H2 | `Insights` | CONTEXT.md D-06 (not "AI Insights", not "Endgame Insights") |
| Pre-click blurb (1 line) | `Generate a short written summary of your endgame performance based on the current filters.` | Drafted this phase. Under 20 words; names the artifact ("written summary"), scopes the subject ("endgame performance"), and tells the user filters are respected without re-explaining what filters do |
| Primary CTA (pre-click) | `Generate insights` | CONTEXT.md D-10 |
| Primary CTA (post-click) | `Regenerate` | CONTEXT.md D-10 |
| Outdated indicator | `Filters changed — click Regenerate to update` | Drafted this phase. One em-dash is within the "sparingly" budget (CLAUDE.md §Communication Style) and separates condition from action cleanly. Rendered with a 6px brand-brown dot to the left (icon-less, matches the `FILTER_MODIFIED_DOT` convention) |
| Stale-rate-limited banner | `Showing your most recent insights. You've hit the hourly limit; try again in ~{N} min.` | CONTEXT.md D-12 + D-14 rounding rule. `N = max(1, Math.ceil(retry_after_seconds / 60))`. If `retry_after_seconds` is null (defensive — backend should always populate for 429), fall back to `Showing your most recent insights. You've hit the hourly limit; try again in a moment.` |
| Error headline | `Couldn't generate insights.` | CONTEXT.md D-11 (split into two lines: headline + body for visual rhythm matching `Endgames.tsx:357-362`) |
| Error body | `Please try again in a moment.` | CONTEXT.md D-11 |
| Error retry (429 only, D-14) | `Try again in ~{N} min.` | CONTEXT.md D-14. Same rounding rule as the stale banner |
| Retry CTA (error surface) | `Try again` | CONTEXT.md D-11. Rendered as `Button variant="brand-outline"` |
| Empty state | **Not applicable** — the block has no empty state. Pre-click hero card IS the "no report yet" state. Post-click, at least 1 SectionInsight always renders (Phase 65 D-19 enforces `min_length=1`). If the overview is hidden via `INSIGHTS_HIDE_OVERVIEW=true`, the top card renders the hero blurb + Regenerate button with no overview paragraph — per CONTEXT.md D-05 / Phase 65 D-18. | n/a |
| Destructive confirmation | **Not applicable** — no destructive actions in this phase. Regenerate replaces the rendered report but does not delete persisted data; backend cache is append-only on `llm_logs`. | n/a |

Copy rules enforced:
- Em-dash budget per CLAUDE.md: outdated indicator has exactly one em-dash. All other copy uses commas, periods, or semicolons.
- Never embed variables into error messages (per CLAUDE.md §Sentry Backend Rules — applies here only for clarity; the frontend's `Sentry.captureException` happens globally in `queryClient.ts` and does not string-interpolate either).
- Stale banner copy avoids the word "cached" — the user doesn't know what a cache is and "most recent" is more honest.

---

## Loading & Skeleton Shape

The LLM call takes 5–15s (Phase 65 D-25). A static spinner is user-hostile at that latency; a sized skeleton communicates "real content is coming".

| State | Render |
|-------|--------|
| `mutation.isPending` (after Generate click, before response) | Top card: H2 "Insights" stays; replace blurb + button area with a **skeleton block** — 3 horizontal bars of varying widths (`w-full`, `w-11/12`, `w-3/4`) at `h-4` each, gap `gap-2`, with subtle shimmer via `animate-pulse`. Below: a single `h-8 w-32` bar where the Regenerate button will land. Total height approximates the expected post-click card height so the page does not jank when the response lands. |
| SectionInsight slots during pending | Inside each of the 4 H2 groups, a thin skeleton directly under the H2: `h-4 w-2/3` (headline) + two `h-3 w-11/12` lines (bullets), gap `gap-2`, above the existing first charcoal card (which keeps its existing `mb-0` relationship with the H2). |
| `mutation.isPending` while a previous report is rendered | Previous overview + SectionInsights **stay visible** (no flash-of-skeleton). A small `Loader2` spinning icon appears inline-right of the "Regenerate" button; the button itself is disabled (`aria-busy=true`). Matches existing `useImportTrigger` pattern on the Import button. |

Skeleton colour: Tailwind `bg-muted/30` on the charcoal surface, giving a low-contrast grey shimmer that reads as "loading" without competing with the surrounding content.

Shimmer animation: Tailwind built-in `animate-pulse` — already available in the codebase, no new keyframe.

---

## Outdated Indicator Treatment (D-07)

CONTEXT.md left the "exact visual treatment" to this phase. Locked here:

- **Placement:** Inline right of the "Insights" H2 text, separated by `gap-2`. Wraps below the H2 on viewports narrower than ~400px (`flex-wrap` on the H2 container).
- **Visual:** A 6px round dot (`size-1.5 rounded-full bg-brand-brown`) + caption text (`text-xs text-muted-foreground font-medium`). No border, no background pill — the dot-plus-text pattern matches the existing filter-modified indicator the user is already trained on.
- **Copy:** `Filters changed — click Regenerate to update`.
- **Visibility condition:** `rendered !== null && reportFilters !== null && !areFiltersEqual(reportFilters, appliedFilters)`. Any field change triggers this; backend cache + `status: "cache_hit"` absorbs the "color/rated_only only" case per D-08.
- **Animation:** No pulse. The dot is static — pulse would over-emphasise a low-urgency signal (user can read the same stats they already have; regenerating is optional).

---

## SectionInsight In-H2 Slot (D-03)

CONTEXT.md left typography, margin, and divider-rule choices to this phase. Locked here:

- **Container:** A `<div data-testid="insights-section-{section_id}" className="mb-3">` rendered as the first child of the H2 group (i.e. immediately after the `<h2>` element, before the first existing `charcoal-texture` card).
- **Background:** None — no charcoal wrapper, no card border. The H2 already owns the visual grouping per CONTEXT.md D-03.
- **Headline:** `<p className="text-sm font-semibold text-foreground mb-2">`. Not an `<h3>` — keeps the existing H2 → card structure semantically clean and avoids creating a second heading level that screen readers would announce as a structural sub-section.
- **Bullets:** `<ul className="list-disc list-outside pl-5 space-y-1 text-sm text-muted-foreground">`. Zero bullets → render only the headline; one or two bullets → render `<ul>` with that many `<li>` children. No horizontal rule above or below.
- **Empty sections:** If the LLM omits a section (Phase 65 D-19 allows 1–4), the slot renders nothing — no placeholder, no "no insight for this section" copy (CONTEXT.md D-05).
- **H2 suppression:** If the host H2 is already hidden by the existing guard (e.g. `showClockPressure && showTimePressureChart` both false → Time Pressure H2 does not render), the matching SectionInsight is dropped client-side (CONTEXT.md D-05).

---

## Stale-Rate-Limited Banner (D-12)

- **Placement:** Inside the top Insights card, between the H2 row and the overview paragraph.
- **Visual:** `<div className="flex items-center gap-2 text-xs text-muted-foreground mb-3"><Info className="size-3.5 shrink-0" />{copy}</div>`. `Info` from `lucide-react`. No border, no background — muted-foreground + small icon is sufficient for informational context.
- **No dismiss affordance** — the banner disappears automatically on the next successful (non-stale) generate.

---

## Error State (D-11, D-14)

- **Placement:** Replaces the overview paragraph + Regenerate button area inside the top card (H2 stays). SectionInsight slots render **nothing** on error (per CONTEXT.md success criterion #5 — "single retry affordance ... rather than empty state or partial content").
- **Visual:** 
  ```
  Couldn't generate insights.              ← text-base font-medium text-foreground
  Please try again in a moment.            ← text-sm text-muted-foreground
  Try again in ~{N} min.                   ← text-sm text-muted-foreground (HTTP 429 only)
  [ Try again ]                            ← Button variant="brand-outline", mt-3
  ```
- **Button behaviour:** Always enabled. Clicking re-triggers the mutation; if the server 429s again, the same error UI re-renders (cheap, per CONTEXT.md D-14).
- **Sentry:** Do NOT add `Sentry.captureException` inside the component. The global `MutationCache.onError` in `frontend/src/lib/queryClient.ts` already captures mutation failures per CLAUDE.md §Error Handling & Sentry.

---

## Mobile Treatment

CONTEXT.md flagged mobile as "matches existing Endgame tab mobile layout patterns" with discretionary tweaks.

- **Top Insights card:** No mobile-specific layout. `charcoal-texture rounded-md p-4` works on mobile the same as on desktop — padding is already touch-comfortable, and the card is full-width by default.
- **H2 + outdated indicator:** On viewports narrower than ~400px, the indicator wraps below the H2 (`flex-wrap` on the H2 row). No alternative compact treatment needed.
- **Buttons:** `Button size="default"` (`h-8`, 32px) — the existing project-wide default. No mobile-specific `w-full` — buttons stay intrinsically sized so they read as distinct CTAs rather than full-width sections. This matches the existing "Import Games" empty-state button at `Endgames.tsx:377-379` which also uses the default intrinsic width.
- **Overview paragraph:** Wraps naturally. `leading-relaxed` prevents the text from feeling dense on narrow screens.
- **SectionInsight slots:** No mobile-specific changes. The existing H2 → chart-card spacing already adapts; inserting a compact headline + bullets between them is visually quiet on mobile.
- **Skeleton:** Same widths (`w-full`, `w-11/12`, `w-3/4`) — they remain proportional on any viewport.

---

## Data-TestID Inventory

Per CLAUDE.md §Frontend §Browser Automation Rules (`data-testid` on every interactive element + major layout containers; kebab-case; component-prefixed).

| Element | `data-testid` | Kind |
|---------|---------------|------|
| Top Insights card container | `insights-block` | Layout container |
| Overview paragraph (post-click) | `insights-overview` | Layout container |
| Generate button (pre-click) | `btn-generate-insights` | Button |
| Regenerate button (post-click) | `btn-regenerate-insights` | Button |
| Try-again button (error state) | `btn-insights-retry` | Button |
| Outdated indicator (dot + text) | `insights-outdated-indicator` | Layout container |
| Stale banner | `insights-stale-banner` | Layout container |
| Error container (headline + body + retry line) | `insights-error` | Layout container |
| Loading skeleton container | `insights-skeleton` | Layout container |
| SectionInsight slot (overall) | `insights-section-overall` | Layout container |
| SectionInsight slot (metrics+ELO) | `insights-section-metrics_elo` | Layout container |
| SectionInsight slot (time pressure) | `insights-section-time_pressure` | Layout container |
| SectionInsight slot (type breakdown) | `insights-section-type_breakdown` | Layout container |

Naming rules applied:
- `btn-{action}` for action buttons (three).
- `insights-{...}` prefix on all block-scoped layout containers — disambiguates from any other potential `*-section-*` in the Endgame tab.
- `insights-section-{section_id}` — `section_id` values come directly from Phase 65's `SectionInsight.section_id` Literal union (`overall | metrics_elo | time_pressure | type_breakdown`); keeps FE and BE in lockstep so a test that knows the backend contract can assert on the rendered DOM without a translation table.

ARIA:
- Generate / Regenerate / Try-again buttons have visible text → no `aria-label` required per CLAUDE.md.
- Outdated indicator — decorative dot + text; `role="status"` on the container communicates "live informational region" to screen readers without being interruptive (`aria-live="polite"` implied by `status`).
- Stale banner — `role="status"` with `aria-live="polite"`.
- Error container — `role="alert"` so screen readers announce when a failed mutation settles.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official (already installed, preset `radix-nova`) | No new blocks added by this phase. Reuses existing `Button` (`@/components/ui/button`). Possibly reuses `Skeleton` if the planner pulls it from shadcn, but plain Tailwind `animate-pulse` on styled `<div>`s is the simpler path and is what this UI-SPEC specifies. | not required (official registry) |
| Third-party registries | None declared for this phase. | n/a — vetting gate not triggered |

No `npx shadcn add` commands expected during execution. If the planner decides to pull shadcn's `Skeleton` component (official) to replace the hand-rolled `animate-pulse` block, that's a neutral change and does not require additional safety vetting.

---

## Integration Hooks (for the planner)

These are notes the planner will use; not a design contract proper.

- **Mount point:** Top of `Endgames.tsx:219` `statisticsContent` JSX, before the `{overviewLoading ? ...}` ternary. The block self-gates on `beta_enabled` per CONTEXT.md D-17 and returns `null` for non-beta users, so the surrounding JSX stays unchanged.
- **Per-section slot placement:** Each of the 4 H2s (`Endgames.tsx:230`, `:291`, `:313`, `:338`) gets a SectionInsight slot inserted **immediately after the `<h2>` and before the first `<div className="charcoal-texture rounded-md p-4">`**. Order relative to the existing Accordion concepts panel at `:231-277`: slot goes BELOW the Accordion (after it closes), above the first chart card. This keeps the "Endgame statistics concepts" explainer anchored to the H2 as today.
- **Filter comparison for outdated indicator:** Shallow-equal `appliedFilters` vs `reportFilters` on the fields `recency`, `opponent_strength`, `time_controls`, `platforms`, `color`, `rated_only`. Any diff → indicator lights. (Backend filters out non-findings-affecting changes via cache; FE stays dumb per CONTEXT.md D-08.)
- **Locked failure copy test assertion:** `screen.getByTestId('insights-error')` contains exactly the three text fragments `Couldn't generate insights.`, `Please try again in a moment.`, and (on HTTP 429) `Try again in ~{N} min.`. Tests should assert against the rendered text, not against prop wiring.

---

## Pre-Populated From

| Source | Decisions Used |
|--------|---------------|
| CONTEXT.md (D-01..D-19) | 19 locked decisions — block architecture, state transitions, button variants, locked failure copy, stale banner, filter invalidation, beta flag backend |
| Phase 65 CONTEXT.md (D-14..D-19, D-31..D-32) | Response envelope shape (`status`, `stale_filters`), error envelope (`error`, `retry_after_seconds`), section_id Literal union, POST endpoint path + query-param filter convention |
| REQUIREMENTS.md (INS-01, INS-02, INS-03, BETA-01, BETA-02) | Beta gating, ≤150 word overview, ≤12 word headline, 0–2 bullets ≤20 words each, filter invalidation semantics |
| CLAUDE.md §Frontend | data-testid convention, Primary vs secondary button rule, theme-constants-in-theme.ts rule, mobile-friendly requirement, noUncheckedIndexedAccess, Literal types on API status/error |
| `frontend/src/lib/theme.ts` | `FILTER_MODIFIED_DOT` reused for outdated indicator; no new constants added |
| `frontend/src/index.css` | `.charcoal-texture` utility + CSS variables (`--foreground`, `--muted-foreground`, `--charcoal`, `--brand-brown`, `--destructive`) |
| `frontend/src/pages/Endgames.tsx` (L219–383) | H2 visual pattern, existing error-state voice (`:357-362`), spacing token `flex flex-col gap-4` inherited by the top card's place in the parent |
| `frontend/src/components/ui/button.tsx` | `Button` variants (`default` for primary, `brand-outline` for secondary) |
| `frontend/src/hooks/useImport.ts` | `useMutation` template for the new `useEndgameInsights` hook (CONTEXT.md D-09) |

Items left to the UI-SPEC (now locked above):
- Outdated indicator treatment — dot + caption text, static, brand-brown via `FILTER_MODIFIED_DOT`.
- SectionInsight typography + spacing — `text-sm font-semibold` headline + `list-disc text-sm text-muted-foreground` bullets, `mb-3` below, no dividers, no background wrapper.
- Stale banner styling — `text-xs text-muted-foreground` + `Info` icon, no border/background.
- Loading skeleton shape — 3-bar overview skeleton + 1-bar button slot in top card; compact headline+bullets skeleton in each SectionInsight slot; no skeleton flash when a previous report is already rendered (inline spinner on Regenerate instead).
- Full `data-testid` inventory (13 testids).
- Mobile treatment — no mobile-specific deviations; inherits existing Endgame tab patterns.
- Minute-rounding rule — `N = max(1, Math.ceil(retry_after_seconds / 60))` for both the 429 retry line and the stale banner.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
