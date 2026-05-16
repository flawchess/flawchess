---
created: 2026-05-16T00:00:00.000Z
title: Center the Conversion Score Gap bullet on its blue-zone midpoint (display-only)
area: frontend / endgame charts
priority: high
status: in-scope for Phase 87.4
files:
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
  - frontend/src/generated/endgameZones.ts
  - app/services/endgame_zones.py
related_notes:
  - .planning/notes/endgame-skill-dropped-conversion-elo.md
  - .planning/notes/endgame-skill-recovery-confound.md
---

# Center the Conversion Score Gap bullet on its blue-zone midpoint

**Promoted to in-scope for Phase 87.4 (2026-05-16).** With Endgame Skill dropped and Conv ΔES Score Gap structurally promoted to the **spine** of the Endgame metrics section (it now feeds the Conversion ELO Timeline via an affine recenter — see `.planning/notes/endgame-skill-dropped-conversion-elo.md`), getting the Conv ΔES display axis right is no longer optional polish. Phase 87.4 plan-phase must wire this in alongside the timeline rewire.

## Problem

The shipped `section2_score_gap_conv` band is `[−0.11, 0.00]` (sigmoid-ceiling null,
correctly off-zero). On the bullet chart this renders as an off-center blue zone that
fights the user's "zero = neutral" intuition — a player converting at engine-par
(gap ≈ 0) sits at the *top* of the band, which reads oddly even though it's correct.

## Fix

Apply a **pure display affine shift**: subtract the blue-zone midpoint
(`(−0.11 + 0.00) / 2 = −0.055`) from the displayed value and the displayed band, so
`0` renders as "typical population result" and the gauge becomes the intuitive
"higher = better, above zero = above typical." Underlying MetricId value, band width,
LLM zone, and Cohen's d are **unchanged** — only the rendered axis shifts.

Precedent: §3.1.5 / §3.1.6 gauges are already centered on their null. Keep the tile
axis and the LLM zone aligned (per `feedback_zone_band_judgement` memory).

## Scope notes

- Decide whether centering applies only to Conversion or to all four Section 2
  buckets (parity/recov/skill bands are near-symmetric so the shift is small; keeping
  the transform uniform across the four is likely cleaner than special-casing one).
- Mobile + desktop bullet renderers both (per CLAUDE.md "apply changes to mobile too").
- This does NOT change `endgame_zones.py` band tuples — it is a presentation-layer
  offset in the chart component, not a recalibration.
