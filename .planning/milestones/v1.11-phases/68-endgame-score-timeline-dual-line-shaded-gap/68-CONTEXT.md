# Phase 68: Endgame Score Timeline (dual-line + shaded gap) — Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Source:** Inline (discussion captured from conversation — discuss-phase skipped)

<domain>
## Phase Boundary

Replace the existing **single-line "Endgame vs Non-Endgame Score Gap over Time"** chart on the Endgame tab with a **two-line "Endgame vs Non-Endgame Score over Time"** chart that plots both absolute Score series with a color-coded shaded area between them representing the gap. The motivation comes from the v1.11 insights work: the `score_gap` metric hides which side moved (endgame weakness vs non-endgame strength), which forced the LLM prompt to carry a special `score_gap` framing rule. A two-line chart makes the composition self-evident and lets that prompt rule be simplified.

Scope:
- Frontend: new chart component + removal of old single-line chart + info-popover rewrite.
- Backend: rename `score_gap_timeline` subsection to `score_timeline`, emit two series (`endgame`, `non_endgame`) below the `[summary]` block instead of the single `score_gap` series that was mislabeled as an aggregate.
- Prompt: drop the `score_gap` framing rule at ~line 290 of `app/prompts/endgame_insights.md`, remove the "no [summary]" exception note for `score_gap_timeline`, update subsection-id references (`score_gap_timeline` → `score_timeline`), update the subsection/section mapping table, bump prompt version.
- Tests: insights snapshot tests, chart render tests, backend payload-builder test for the new subsection shape.

Out of scope:
- No changes to the `overall_wdl` chart (already shows endgame vs non-endgame at the aggregate level — that's fine).
- No changes to the `score_gap` aggregate value in the `overall` subsection's `[summary score_gap]` — it stays as the authoritative single-number `score_gap` mean.
- No changes to downstream sections (`metrics_elo`, `time_pressure`, `type_breakdown`) — this is an `overall` section concern only.
- No tombstone or migration for old cached LLM reports — cache will naturally invalidate when `prompt_version` bumps (per Phase 65 cache-key design).

</domain>

<decisions>
## Implementation Decisions

### Chart design
- **Two line series** on the same Y-axis: endgame Score and non-endgame Score, both as whole-number percentages in `[0, 100]`.
- **Shaded area fill between the two lines**, color-coded: green when endgame > non-endgame, red when below. Neutral/none when within a small epsilon (e.g. ≤ 1% absolute gap) to avoid noise.
- **Colors from theme.ts** — reuse WDL/zone colors that already exist. Do NOT hard-code hex values. Green = success, red = danger (same semantic meaning used elsewhere).
- **Line styling**: endgame line in brand-primary; non-endgame line in a distinct muted/neutral color so the "main" series reads clearly. Legend shows both labeled.
- **X-axis**: same monthly bucketing as today's chart. Activity gaps rendered the same way (current behavior).
- **Tooltip**: on hover, show `{bucket date} · Endgame: X% (n=...) · Non-endgame: Y% (n=...) · Gap: ±Z%`.
- **Empty-state**: when either series has < some minimum buckets (current threshold), fall back to the same empty state pattern as today's chart.

### Chart title
- Rename to **"Endgame vs Non-Endgame Score over Time"**. The current title "Endgame vs Non-Endgame Score Gap over Time" must be fully removed from UI code, test assertions, and any docs references.

### Info popover rewrite
- Drop the caveat paragraph: "the Score Gap is a comparison, not an absolute measure. A positive value can mean stronger endgames *or* weaker non-endgame play; a negative value, the reverse. Compare the two Score rows to see which side is driving it." — the two-line chart makes this visible.
- Keep the factual definition ("endgame phase = ≥ 3 full moves with ≤ 6 major/minor pieces") and the sample-quality footnote (points with `n < 3` dropped).
- Add one new short sentence explaining the shaded area: "The shaded area between the lines is color-coded: green when your endgame Score leads your non-endgame Score, red when it trails."

### Backend payload shape
- Rename subsection id `score_gap_timeline` → `score_timeline` in `app/schemas/insights.py` (SubsectionId enum) and in the builder (`app/services/insights_service.py`).
- Emit a `[summary score_timeline]` block above the series — this fixes the existing "no [summary]" exception. Summary block carries the aggregate gap (for backward compat with the prompt's framing) but the two per-series blocks are the primary data.
- Emit two `[series]` blocks per window:
  - `[series score, all_time, monthly, part=endgame]` — bucketed endgame Score series.
  - `[series score, all_time, monthly, part=non_endgame]` — bucketed non-endgame Score series.
- Per-bucket point: `bucket_start` (YYYY-MM-DD), `value` (whole-number %), `n` (sample size). Points with `n < 3` still filtered out. Activity gaps inline as today.
- The existing `[summary score_gap]` in the `overall` subsection **stays** — it's the authoritative gap aggregate and the prompt's `overall_wdl` framing rule still points to it.

### Prompt simplification
- Remove the `score_gap` framing rule block at ~line 290 of `app/prompts/endgame_insights.md` (the paragraph starting "Framing rule (important):" through "Source of the aggregate:"). The two-line chart + existing `overall_wdl` table now make composition self-evident; the rule becomes redundant.
- Remove the "score_gap_timeline is the one exception to the summary-per-metric rule" paragraph (~line 138) — no longer an exception.
- Update the `Subsection → section_id mapping` table: `score_gap_timeline` row → `score_timeline`.
- Update any narrative examples that reference the old subsection id.
- Bump `prompt_version` string (e.g. `endgame_v12` → `endgame_v13`) so cached LLM reports invalidate and the next generation reads the new rules.

### Frontend test coverage
- Chart renders correctly with two series, with and without shading, with activity gaps.
- Legend labels are present and match UI vocabulary ("Endgame", "Non-endgame").
- Mobile layout: chart scales without cutoff or overflow (same breakpoints as today).
- Info popover no longer contains the removed caveat sentence (negative assertion).

### Backend test coverage
- New subsection id emitted with `score_timeline` name.
- Two series blocks emitted per window, each populated from the per-month endgame and non-endgame score aggregates.
- `[summary score_timeline]` block carries the aggregate gap and zone.
- Snapshot of a known fixture payload matches the new shape (replace the old snapshot).
- Existing insights LLM snapshot tests (Phase 67 fixtures) still pass after the prompt rule simplification — the prompt change removes scaffolding, not content, so the narrative output for the SEED-001 fixture should be stable.

### Claude's Discretion
- Exact shading implementation (Recharts `<Area>` between two lines, or a custom gradient) — pick the cleanest path for the charting lib already in use (likely Recharts given the existing chart stack).
- Color tokens: use the existing theme.ts WDL/zone tokens (e.g. `WIN_COLOR` / `LOSS_COLOR` or zone-strong / zone-weak) — pick what reads semantically closest to "endgame leading = good" / "endgame trailing = bad".
- Mobile-specific layout tweaks if the two-line + legend layout becomes cramped (e.g. legend below instead of beside).
- Whether to keep a tiny inline "current gap" readout near the chart (e.g. latest-bucket gap pill) — nice-to-have, not required.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prompt and payload
- `app/prompts/endgame_insights.md` — system prompt; framing rule at ~line 290 and the `score_gap_timeline` exception note at ~line 138 are what's being simplified.
- `app/services/insights_service.py` — findings + payload builder; source of the `score_gap_timeline` subsection today.
- `app/schemas/insights.py` — Pydantic schemas; `SubsectionId` enum needs the rename.

### Frontend chart
- `frontend/src/components/endgame/EndgamePerformanceSection.tsx` — current `EndgamePerformanceSection` component that renders the Score Gap timeline chart (around lines 303-334 per earlier exploration). Replace the chart component it renders.
- `frontend/src/lib/theme.ts` — source of semantic color tokens (WDL, zone). Do NOT hard-code hex values.

### Reference patterns
- `frontend/src/components/endgame/EndgameClockPressureSection.tsx` (lines ~449-475) — existing dual-series timeline (avg clock diff over time) with similar shape; useful analog.

### Project rules
- `CLAUDE.md` — coding guidelines, theme constants rule, mobile-friendly UI rule, data-testid requirement for interactive elements.

</canonical_refs>

<specifics>
## Specific Ideas

- Use a Recharts `<Area>` between two `<Line>` elements with a fill driven by a sign-aware function, OR two separate `<Area>` components (one green when endgame ≥ non-endgame, one red when below). Whichever renders cleanly with activity gaps is fine.
- For the color fill, keep the opacity low (e.g. 15-25%) so it doesn't dominate the lines. The lines are the primary read.
- Keep the latest-bucket labels (current Score values in the legend/tooltip) consistent with other timeline charts on the page.
- The existing `score_gap_timeline` series points are already computed from the per-month endgame and non-endgame scores via the existing `compute_findings()` flow — wiring two separate series is a matter of splitting the existing aggregation, not computing new data.

</specifics>

<deferred>
## Deferred Ideas

- Population-level baseline overlay (a dashed horizontal line showing cohort median Score for comparison) — out of scope; belongs in v1.12's calibration work.
- A "trend arrow" badge next to the chart summarizing recent direction — nice but not required.
- Making the shading hover-aware (e.g. brighter on hover) — polish, defer unless it falls out of the chart library naturally.
- Cache migration for old LLM reports that reference the old subsection id — not needed; cache invalidates on `prompt_version` bump by existing design.

</deferred>

---

*Phase: 68-endgame-score-timeline-dual-line-shaded-gap*
*Context gathered: 2026-04-24 via inline discussion (discuss-phase skipped by user decision)*
