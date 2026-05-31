# Phase 98: Per-TC Collapsible Endgame Type Cards - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the **Endgame Type Breakdown** section so time control becomes a per-card
*view dimension*. Replace the current 3-col grid of five per-type `EndgameTypeCard`s
(`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) with **one full-width collapsible
`charcoal-texture` card per time control** (bullet/blitz/rapid/classical), chevron in
the header, the user's **primary TC expanded by default**, the rest collapsed. Inside
each TC card: a responsive grid of **four endgame-type tiles** (rook, minor_piece, pawn,
queen — **Mixed dropped**, pawnless stays hidden), separated by dividers. Each tile shows
that TC's own per-(class × TC) benchmark bands — no TC-mix blending, no pooled-across-TC
band. This brings back the Conversion + Recovery gauges removed on 2026-05-29, now judged
against the right (per-class × TC) reference.

**In scope:** the Endgame Type Breakdown section only — its layout (collapsible per-TC
cards + divider-separated type tiles), the per-(class × TC) Conv/Recov/Score-Gap bands,
the primary-TC default-expand heuristic, per-TC sparsity suppression, and the backend
per-(class × TC) rate+count grouping the section needs.

**Out of scope (untouched):** the Endgame ELO Timeline (mode 2), the Endgame Metrics by
TC section (Phase 97), the Time Pressure section, the Endgame Overall Performance section,
and the LLM insights narration path (response shape preserved or additively extended).
Aligning the timeline's default-line algo to this phase's primary-TC heuristic is a
**flagged follow-up, not this phase**.

</domain>

<decisions>
## Implementation Decisions

Most of this phase is **already locked** by ROADMAP.md and
`.planning/notes/endgame-tc-disclosure-pattern.md` (the mode-3 disclosure pattern). Those
locked decisions are NOT re-derived here — see the canonical refs. Do **not** re-litigate:
full-width collapsible per-TC cards (mode 3, full-width-stacked is a hard constraint);
2×2-family type grid with Mixed dropped + pawnless hidden; Conv/Recov gauges banded
per-(class × TC); Score Gap forced per-(class × TC) for visual consistency despite being
TC-flat (d≈0.13 — the redundancy is **chosen, not a bug**); per-TC sparsity suppression.

This discussion resolved the four **open planning inputs** the roadmap flagged.

### Tile anatomy (resolved)
- **D-01:** Each type tile renders the **full pre-removal anatomy** — restore the
  `EndgameTypeCard` layout as it existed *before* the 2026-05-29 gauge removal
  (commit `d3453597`, "feat(260529-une): remove Conv/Recov gauges"). The exact prior
  layout to restore is in `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx`.
- **D-02:** Tile layout, top-to-bottom (the pre-removal structure, verbatim intent):
  1. Title + per-class title `InfoPopover` + optional `n={total}` sparse chip.
  2. **Side-by-side Conversion + Recovery gauges** (`EndgameGauge`).
  3. WDL bar row with the `Games: X% (count)` deep-link.
  4. Score bullet (`W + 0.5·D / N`) sig-gated against 50%.
  5. Per-span Score Gap bullet (eval-based, Cpu-iconed) — `ScoreGapRow`.
- **D-03:** Keep the plain Score bullet (#4) **in addition to** the Score-Gap bullet (#5)
  — user explicitly chose "everything" (no trimming). All five elements per tile.
- **D-04:** The gauges (#2) and the Score-Gap bullet (#5) are banded against that card's
  **own per-(class × TC) benchmark band**. The plain Score bullet (#4) keeps its existing
  50% anchor + sig-gate (unchanged).

### Card structure & dividers (resolved — user clarification)
- **D-05:** Each TC card is a single **`charcoal-texture rounded-md` container** with a
  **full-bleed header** (TC icon + TC label + `Games: X% (count)` with `Swords` icon),
  matching the `EndgameMetricsByTcCard` / `EndgameTimePressureCard` header convention
  (recessed `bg-black/20 border-b border-border/40`, full-bleed to card edges).
- **D-06:** The four type tiles inside are **separated by thin dividers, NOT bordered
  sub-cards** — same divider grammar as `EndgameMetricsByTcCard`: vertical `w-px
  bg-border/40` rules between columns, horizontal `border-t border-border/40` rules
  between rows. Single shared charcoal container per TC; tiles are divider-delimited
  regions, not nested boxes.
- **D-07:** Responsive staircase for the four tiles: **4×1 (desktop) → 2×2 (tablet) →
  1×4 (mobile, full-width stacked)**. No content thinning at any breakpoint — every tile
  keeps all five elements (D-02) at every width; on mobile each tile gets full card width
  so the two side-by-side gauges stay readable.
- **D-08 [PLANNER FLAG]:** `EndgameMetricsByTcCard`'s divider helper only handles ONE axis
  (`flex-col → flex-row`, single divider direction). The 4×1 → 2×2 → 1×4 staircase needs
  dividers on **both axes at the 2×2 stage** (vertical between the two columns AND
  horizontal between the two rows). The divider mechanics are therefore fiddlier than a
  straight copy — likely `divide-x`/`divide-y` utilities or per-cell border classes gated
  by breakpoint. Preserve the visual intent (D-06 divider grammar, not boxes); the exact
  CSS-grid divider technique is the planner's call.

### Primary-TC default-expand heuristic (resolved)
- **D-09:** `primary = argmax( games_in_bucket(tc) × NOMINAL_DURATION[tc] )` over TCs that
  pass the games floor, computed over the **currently-filtered** game set, **no recency
  weighting** (flat all-time). This is the locked roadmap algorithm.
- **D-10:** `NOMINAL_DURATION` constants (seconds), **user-chosen**:
  `bullet = 60`, `blitz = 180`, `rapid = 600`, `classical = 900` (ratios 1 : 3 : 10 : 15).
  Named constants, not magic numbers. These only neutralize bullet's volume advantage —
  exact accuracy doesn't matter, the ratios do.
- **D-11 [PLANNER FLAG]:** The heuristic + its constants must live in **one shared util**
  so the page can later agree with itself about "your main TC" (the Endgame ELO Timeline's
  default-line algo is a flagged follow-up to align to this same util — out of scope now,
  but place the util where the timeline can consume it). Exact module location is the
  planner's call.

### Accordion state (resolved)
- **D-12:** **Reset to the recomputed primary TC on any filter change.** When the filtered
  game set changes (TC filter, date range, color, opponent, recency), recompute the primary
  TC and reset the accordion to "primary expanded, rest collapsed." Manual expand/collapse
  persists only within a stable filter set. This avoids a stale-expanded card pointing at a
  now-suppressed TC and keeps the view coherent with the data shown ("tracks the active
  filters" per the disclosure-pattern note).

### Backend (locked by roadmap; shape is planner's call)
- **D-13:** The `/stats` endgame breakdown must expose **per-(class × TC) rates + games
  counts** grouped for per-TC rendering (Phase 97 established the per-(class × TC) path).
  **No eligible-count weighting payload** is added — that was the superseded TC-mix approach.
- **D-14:** Per-(class × TC) Conv/Recov bands + per-(class × TC) ΔES Score-Gap bands are
  generated into `frontend/src/generated/endgameZones.ts` via `app/services/endgame_zones.py`
  + `scripts/gen_endgame_zones_ts.py` (CI drift gate must stay green). Today there's a single
  per-class `achievable_score_gap` band — it gains a TC dimension; accept the four near-
  identical ΔES bands per D's "redundancy is chosen."
- **D-15:** The LLM insights path (`_findings_conversion_recovery_by_type` /
  `assign_per_class_zone`) must be **unaffected** — response shape preserved or additively
  extended only.

### Claude's Discretion
- Exact backend response shape for the per-(class × TC) rate+count grouping (D-13).
- Whether the new per-(class × TC) band structure replaces or sits alongside the existing
  per-class `BUCKETED_ZONE_REGISTRY` entries (D-14).
- Exact CSS-grid divider technique for the both-axes 2×2 staircase (D-08).
- Exact module location for the shared primary-TC util (D-11).
- knip/dead-code cleanup of the old 3-col grid assumptions and the dropped Mixed tile.
- Whether a `/gsd-ui-phase` pass is warranted: Phase 97 skipped it (all components existed).
  Phase 98 reuses the same components but in a **denser, genuinely new layout** (collapsible
  card + divider-separated 4-tile grid with two gauges per tile). Planner should decide
  whether the layout novelty justifies a UI spec or whether the pre-removal layout + Phase 97
  card scaffolding are template enough. (Process note — not a plan deliverable.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design decisions (READ FIRST — most of this phase is pre-decided)
- `.planning/ROADMAP.md` — Phase 98 block (Goal, Open planning inputs, Success Criteria 1-10).
  The success criteria are the acceptance contract.
- `.planning/notes/endgame-tc-disclosure-pattern.md` — the mode-3 "collapsible TC cards"
  pattern, the primary-TC heuristic, the Mixed-drop rationale, the "Score Gap forced per-TC"
  decision, and the Lichess Tutor research. **This note drives the phase.**
- `.planning/notes/endgame-typecard-tcmix-gauges.md` — **SUPERSEDED** TC-mix-weighted-band
  approach. Do NOT implement it; retains accurate benchmark facts only.
- `.planning/phases/97-endgame-metrics-by-time-control/97-CONTEXT.md` — Phase 97 established
  the per-(class × TC) rate aggregation path, the TC-keyed band structure
  (`PRESSURE_BIN_SCORE_NEUTRAL_ZONES` as the model), `MIN_GAMES_PER_TC_CARD`, and the per-TC
  card scaffolding this phase reuses.

### Pre-removal tile layout to restore (D-01/D-02)
- Removal commit: `d3453597` ("feat(260529-une): remove Conv/Recov gauges from EndgameTypeCard").
- Restore from: `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx`
  (the 5-element layout with side-by-side Conv+Recov gauges at the top).

### Benchmark band/zone source of truth
- `reports/benchmark/benchmarks-latest.md` — per-(class × TC) Conversion/Recovery rate
  distributions and per-(class × TC) ΔES Score-Gap distributions + Cohen's-d collapse
  verdicts. The numeric source of truth for every per-(class × TC) band. (Per-class ΔES TC
  d≈0.13 — the four Score-Gap bands will be near-identical; that's expected.)

### Zone system (code source of truth)
- `app/services/endgame_zones.py` — `BUCKETED_ZONE_REGISTRY` (per-class conv/recov/score
  bands), the `achievable_score_gap` per-class band that gains a TC dimension,
  `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (TC-keyed structure to model the new bands on),
  `MIN_GAMES_FOR_RELIABLE_STATS` / `MIN_GAMES_PER_TC_CARD` (the games floors).
- `scripts/gen_endgame_zones_ts.py` — regenerates `frontend/src/generated/endgameZones.ts`;
  CI fails on drift — re-run after editing the Python registry.
- `frontend/src/generated/endgameZones.ts` — generated bands consumed by gauge/bullet.

### Layout templates & current components
- `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` — the 3-col grid being
  replaced (its `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` + 5-card assumptions change).
- `frontend/src/components/charts/EndgameTypeCard.tsx` — current 4-element tile (post gauge
  removal); restore its pre-removal 5-element form (see above) inside the new tile grid.
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — **the divider grammar
  template** (D-06): full-bleed charcoal header + `flex-col lg:flex-row` body with
  `w-px bg-border/40` vertical / `border-t border-border/40` horizontal dividers
  (`divider` helper ~line 347).
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` / `EndgameTimePressureCard.tsx`
  — per-TC card selection, `GRID_*_CARDS` responsive staircase, fixed bullet/blitz/rapid/
  classical order, null-suppression, empty state.
- `frontend/src/components/charts/EndgameGauge.tsx` — 240° gauge; `size` prop for shrinking,
  `zones` prop for the per-(class × TC) band.
- `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (`ScoreGapRow`) — the
  Score-Gap bullet row (label, value, neutralMin/Max, start/end slots, tooltip).
- `frontend/src/components/ui/accordion.tsx` — Radix Accordion primitive (already used on
  `Endgames.tsx` for the concepts collapsible) — candidate for the per-TC chevron headers.
- `frontend/src/pages/Endgames.tsx` — mounts `EndgameTypeBreakdownSection` (~line 648),
  passes `categories` + `endgame_games`; hosts the out-of-scope sections.

### Data shape & backend
- `frontend/src/types/endgames.ts` — `EndgameCategoryStats` / `EndgameStatsResponse`
  (currently pooled-across-TC; gains a per-TC dimension).
- `app/services/endgame_service.py` — `query_endgame_bucket_rows` / bucket aggregation
  (per-(class × TC) grouping to add); LLM `_findings_conversion_recovery_by_type` /
  `assign_per_class_zone` (must stay unaffected, D-15).

### Project conventions
- `CLAUDE.md` — theme constants in `theme.ts`, `data-testid` + ARIA on interactive elements
  (chevron headers need keyboard-accessible `data-testid`s per SC-2), mobile parity,
  `text-sm` floor (tooltip exception), no magic numbers, Sentry capture rules, CHANGELOG
  `[Unreleased]` entry required.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EndgameMetricsByTcCard`: the divider-grammar + full-bleed-header template (D-05/D-06).
- `EndgameTimePressureSection`/`Card`: per-TC selection, responsive grid staircase, fixed
  TC order, null suppression, empty state.
- Pre-removal `EndgameTypeCard` (commit `d3453597^`): the exact 5-element tile to restore.
- `EndgameGauge` (`size` + `zones` props), `ScoreGapRow`, `MiniWDLBar`, `MiniBulletChart`,
  `MetricStatPopover` — all exist; this is re-grouping, not new visual primitives.
- `accordion.tsx` (Radix) — already on the page; reuse for the per-TC chevron cards.
- `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` — TC-keyed band structure to model the per-(class × TC)
  bands on.

### Established Patterns
- Zone bands are Python source of truth (`endgame_zones.py`) codegen'd to TS
  (`endgameZones.ts`) with a CI drift gate — new bands go through `gen_endgame_zones_ts.py`.
- Per-TC cards gate on `MIN_GAMES_PER_TC_CARD` and suppress whole cards below the floor.
- Sidebar `timeControls` filter flows through `apply_game_filters`; stats re-scope by TC.
- Fixed bullet/blitz/rapid/classical render order across all per-TC sections.

### Integration Points
- New per-(class × TC) rate+count query slots into the endgame overview service alongside
  the existing per-TC paths.
- New per-(class × TC) band export consumed by the type tiles.
- Shared primary-TC util (D-11) consumed now by this section, later by the timeline.
- Removal of the old 3-col grid + Mixed-tile assumptions (knip-clean unused exports).

</code_context>

<specifics>
## Specific Ideas

- The tile layout is not a fresh design — it's a **literal restore** of the pre-2026-05-29
  `EndgameTypeCard` (commit `d3453597^`), now with correct per-(class × TC) bands. User was
  explicit: "use the same within-card layout we had before removing the gauges."
- Divider grammar must match `EndgameMetricsByTcCard` exactly — divider rules, not bordered
  sub-cards. User clarification: "the endgame types should be separated with vertical and/or
  horizontal dividers (same approach as in the Endgame Metrics TC-specific cards)."
- Lichess Tutor is the inspiration (always per-speed, 30-games-per-speed floor, never pooled,
  most-played speed default) — see the disclosure-pattern note.

</specifics>

<deferred>
## Deferred Ideas

- **Align the Endgame ELO Timeline's default-line algo to this phase's primary-TC heuristic**
  — the timeline currently ranks by raw game count (always picks bullet); aligning it to the
  shared `games × NOMINAL_DURATION` util (D-11) is a flagged follow-up, explicitly out of
  Phase 98 scope.
- **Adopt the mode-3 collapsible affordance on the Phase 97 Endgame Metrics by TC section** —
  out of scope; that section is already per-TC.
- **Mixed endgame-type analysis** — Mixed tile is dropped (least-actionable catch-all);
  backend still computes per-class Mixed for the LLM path. Pawnless stays hidden.

### Reviewed Todos (not folded)
- `2026-05-17-recovery-score-gap-popover-copy.md` (Reframe Recovery Score Gap popover copy —
  opponent-first): the Recovery score-gap bullet + popover return to the tiles this phase, so
  it was offered for folding but the user declined to expand scope. Leave for its own pass.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (invalid Tailwind `pt-33` on
  Score Y-axis label): trivial; fix opportunistically only if the relevant file is touched.

</deferred>

---

*Phase: 98-per-tc-collapsible-endgame-type-cards*
*Context gathered: 2026-05-30*
