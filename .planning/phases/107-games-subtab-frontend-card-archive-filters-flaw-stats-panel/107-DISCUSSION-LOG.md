# Phase 107: Games Subtab Frontend — Card Archive, Filters & Flaw-Stats Panel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
**Areas discussed:** Opportunity/Impact rates gap, GameCard reuse seam

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Opportunity/Impact rates gap | Zone 3 wants rates the backend doesn't expose | ✓ |
| GameCard reuse seam | Fork vs refactor card + pagination | ✓ |
| Tag chip honesty cue | Hover tooltip vs cursor-pointer only | |

**Notes:** UI-SPEC (`107-UI-SPEC.md`) was found and is a near-complete design
contract, so most HOW decisions were already locked. Tag chip behavior left as
locked (cursor-pointer + honest ARIA, no extra tooltip). The endpoint name was
corrected: ROADMAP's `mistake-stats` is stale; real route is `flaw-stats`.

---

## Opportunity / Impact rates gap

The backend `TagDistribution` (`app/schemas/library.py`) exposes only `tempo`,
`result_changing_rate`, and `phase_histogram` — no miss/lucky-escape (Opportunity)
or while-ahead (Impact) rates that the UI-SPEC Zone 3 needs.

| Option | Description | Selected |
|--------|-------------|----------|
| Drop both sub-columns | Ship Zone 3 with tempo + phase histogram only; stays strictly frontend-only | |
| Small backend extension | Add opportunity/impact rate fields to TagDistribution + aggregation; breaks "No backend work" boundary | ✓ |
| Drop, keep placeholders | Render "coming soon" scaffolding for the columns | |

**User's choice:** Small backend extension.
**Notes:** Flagged as expanding the phase past the roadmap's "No backend work"
boundary; user approved. Verified the extension is small — `_compute_tag_distribution`
already iterates every tag of every M+B flaw.

### Schema shape follow-up

| Option | Description | Selected |
|--------|-------------|----------|
| Three flat rate floats | `miss_rate`, `lucky_escape_rate`, `while_ahead_rate`, each count/total M+B flaws, mirrors `result_changing_rate` | ✓ |
| Two nested dicts | `opportunity_rates {miss, lucky_escape}` + `impact_rates {while_ahead}` (UI-SPEC's original suggestion) | |

**User's choice:** Three flat rate floats.
**Notes:** Consistent with the existing `result_changing_rate` precedent; avoids a
singleton dict for impact. Client-side derivation from card chips was ruled out
(page-limited, game-deduped presence flags ≠ true per-flaw rate).

---

## GameCard reuse seam

| Option | Description | Selected |
|--------|-------------|----------|
| Extract shared pagination | Pull pagination out of GameCardList into a shared component/hook; LibraryGameCard stays separate | ✓ |
| Fork + duplicate pagination | New components, ~80 lines of pagination duplicated | |
| Generic GameCardList<T> | Render-prop generic list; rewrites Openings/Endgames call sites | |

**User's choice:** Extract shared pagination.
**Notes:** Pagination (`getPaginationItems` + controls) is the only genuinely
type-agnostic reusable part. Card bodies differ too much to share, so
`LibraryGameCard` is a separate component. Refactor touches GameCardList (used by
Openings/Endgames) — planner must keep those tests green (behavior-preserving).

---

## Claude's Discretion

- Trend chart: Recharts `AreaChart` vs `LineChart` (follow existing endgame chart pattern).
- Extracted pagination as a component vs a hook (planner's call).

## Deferred Ideas

- Tag-chip deep-link into a pre-filtered Flaws view — deferred until the Flaws subtab exists.
- Per-card eval sparkline — deferred by the roadmap.
- "Coming soon" placeholder scaffolding for Opportunity/Impact columns — unneeded; backend extension makes the data real.
