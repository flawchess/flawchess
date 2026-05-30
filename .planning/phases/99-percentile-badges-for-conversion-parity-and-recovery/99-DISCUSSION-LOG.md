# Phase 99: Percentile Badges for Conversion, Parity, and Recovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 99-percentile-badges-for-conversion-parity-and-recovery
**Areas discussed:** Chip model, Chip floor, Parity, Tooltip, Two-chip differentiation

---

## Chip model (rate chip vs existing ΔES-gap chip)

| Option | Description | Selected |
|--------|-------------|----------|
| Replace gap with rate chip | New raw-rate percentile becomes the single chip; ΔES-gap chip removed | |
| Show both chips | Rate chip + gap chip coexist per metric block | ✓ |
| Rate is primary, gap demoted | Rate chip prominent; gap moved into tooltip/secondary | |

**User's choice:** Show both chips.
**Notes:** Time Pressure TC cards already show 3 chips per card. The new chips go on the Conversion/Parity/Recovery **title lines, right-aligned**. Existing ΔES-gap chips stay on the bullets.

---

## Chip floor (per-(metric, TC) inclusion floor)

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Phase 94.3 chip floor | Same per-metric percentile-inclusion floor the Time Pressure per-TC chips use | ✓ |
| Metric-specific floors | Higher floor for thin conv/recov denominators vs parity | |
| You decide in planning | Defer exact value to research/planning | |

**User's choice:** Reuse Phase 94.3 chip floor.
**Notes:** Validate against dev-DB per-(metric, TC) denominators during planning; flag if inadequate for conv/recov rather than silently raise.

---

## Parity (per-TC cohort CDF vs collapsed)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-TC cohort CDF (as spec'd) | Parity gets its own per-(parity_rate, TC) CDF; 12 metrics total | ✓ |
| Reconsider parity chip | Drop parity chip or share one global CDF | |

**User's choice:** Per-TC cohort CDF (as spec'd).
**Notes:** Neutral band stays global (Phase 97), but the ranking cohort is per-TC — band and percentile are independent signals.

---

## Tooltip (disclosure copy adaptation for rate semantics)

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse contract, swap metric noun | Keep 4-bullet structure verbatim; only bullet-1 metric noun changes | ✓ |
| Rework for rate semantics | Revisit rating-coupling framing for raw rates | |

**User's choice:** Reuse contract, swap metric noun.
**Notes:** Peer-relative cohort framing (Phase 94.4) already absorbs rating coupling; no structural change.

---

## Two-chip differentiation

| Option | Description | Selected |
|--------|-------------|----------|
| Tooltips carry the distinction | No new visual treatment; tooltips say "rate" vs "gap" | ✓ |
| Add a short inline label | Tiny inline 'rate' qualifier on title-line chips | |
| You decide in planning | Flag divergence risk; let planner/UI settle | |

**User's choice:** Tooltips carry the distinction.
**Notes:** The two percentiles can diverge sharply (raw rate tracks ELO harder than the skill-adjusted gap); the tooltip metric noun makes clear which is which.

---

## Claude's Discretion

- Exact ENUM member naming/casing and migration shape for the 12 new metrics.
- Direction/sign convention per rate (higher rate → higher percentile is the obvious default).
- Backend response field shape for the new rate percentile (must be separate from the existing gap `block.percentile`).
- knip/dead-code posture (additive phase — no removals expected).
- No `/gsd-ui-phase` (existing components, wiring a second chip).

## Deferred Ideas

- Inline "rate"/"gap" qualifier labels on the chips (deferred in favor of tooltip-carried distinction).
- Reworking tooltip rating-coupling framing for raw rates (cohort framing already absorbs it).
- LLM narration of the new rate percentiles (Phase 100).
