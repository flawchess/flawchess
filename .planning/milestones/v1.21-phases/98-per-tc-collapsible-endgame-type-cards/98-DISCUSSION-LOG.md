# Phase 98: Per-TC Collapsible Endgame Type Cards - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 98-per-tc-collapsible-endgame-type-cards
**Areas discussed:** Tile anatomy, Mobile density, NOMINAL_DURATION, Accordion state

Note: this phase was already heavily pre-specified by ROADMAP.md and
`.planning/notes/endgame-tc-disclosure-pattern.md`. The discussion covered only the four
"Open planning inputs" the roadmap flagged; all locked decisions (mode-3 layout, Mixed-drop,
per-(class × TC) banding, primary-TC heuristic shape) were not re-litigated.

---

## Tile anatomy

| Option | Description | Selected |
|--------|-------------|----------|
| WDL + 2 gauges + Score-Gap (drop plain Score) | Cleanest tile leading with the returning gauges; drops the plain Score-vs-50% bullet as redundant with WDL | |
| Everything (keep plain Score too) | WDL + Conv gauge + Recov gauge + plain Score bullet + Score-Gap bullet | ✓ |
| Gauges + WDL only (drop both score bullets) | Leanest; contradicts the roadmap's per-TC Score-Gap decision | |

**User's choice:** "Everything (keep plain Score too), use the same within-card layout we had before removing the gauges."
**Notes:** Pinned to the literal pre-removal `EndgameTypeCard` layout — commit `d3453597`
removed the gauges; restore from `d3453597^`. Five elements per tile: title, side-by-side
Conv+Recov gauges, WDL+games-link, plain Score bullet (vs 50%), eval-based Score-Gap bullet.

---

## Mobile density

| Option | Description | Selected |
|--------|-------------|----------|
| 1-column stack on mobile, full tile content | Desktop 2×2, mobile single full-width column, no thinning | |
| Stay 2×2, shrink gauges on mobile | Compact but gauges risk being unreadable in a half-screen cell | |
| 1-column on mobile + thin content | Drop gauges below a breakpoint — loses the headline feature | |

**User's choice (free-text):** "We'll use 4col×1row (desktop) collapsing to 2col×2row collapsing to 1col×4row (mobile) layout."
**Follow-up clarification (mid-discussion):** TC-specific cards are `charcoal-texture`
containers with a TC header; inside, the endgame types are separated by vertical and/or
horizontal **dividers** — same approach as the Endgame Metrics TC-specific cards
(`EndgameMetricsByTcCard`), NOT bordered sub-cards.
**Notes:** Established the full responsive staircase (4×1 → 2×2 → 1×4) and the divider
grammar. Flagged to the planner that the 2×2 stage needs dividers on both axes, unlike the
single-axis `EndgameMetricsByTcCard` divider helper.

---

## NOMINAL_DURATION

| Option | Description | Selected |
|--------|-------------|----------|
| 120 / 300 / 1200 / 3000 s | Note's suggested values (bullet 2 / blitz 5 / rapid 20 / classical 50 min) | |
| TC-bucket boundary midpoints | Derive from existing bucketing thresholds | |
| Claude's discretion | Planner picks + sanity-checks | |

**User's choice (free-text):** "60 / 180 / 600 / 900"
**Notes:** bullet 60s / blitz 180s / rapid 600s / classical 900s (ratios 1:3:10:15). Named
constants in a shared util (placement is a planner detail; the ELO timeline should later
consume the same util).

---

## Accordion state

| Option | Description | Selected |
|--------|-------------|----------|
| Reset to recomputed primary on filter change | Always coherent with the data shown; avoids stale-expanded suppressed cards | ✓ |
| Persist manual state across filter changes | Stickier but risks stale-empty expanded cards | |
| Persist, but re-default if expanded TC suppressed | Middle ground, more state logic | |

**User's choice:** Reset to recomputed primary on filter change.
**Notes:** Manual expand/collapse persists only within a stable filter set.

---

## Claude's Discretion

- Exact backend response shape for the per-(class × TC) rate+count grouping.
- Whether the new per-(class × TC) band structure replaces or sits alongside the existing
  per-class `BUCKETED_ZONE_REGISTRY`.
- Exact CSS-grid divider technique for the both-axes 2×2 staircase.
- Exact module location for the shared primary-TC util.
- Whether a `/gsd-ui-phase` pass is warranted given the denser-but-component-reusing layout.
- knip/dead-code cleanup of old 3-col grid + Mixed-tile assumptions.

## Deferred Ideas

- Align the Endgame ELO Timeline's default-line algo to the shared primary-TC heuristic
  (flagged follow-up, out of scope).
- Adopt the collapsible affordance on the Phase 97 Endgame Metrics by TC section.
- Two reviewed-not-folded todos (recovery score-gap popover copy; invalid Tailwind pt-33) —
  offered for folding, user declined to expand scope.
