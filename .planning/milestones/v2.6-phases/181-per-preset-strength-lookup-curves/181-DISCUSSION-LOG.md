# Phase 181: Per-preset strength lookup curves - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-21
**Phase:** 181-per-preset-strength-lookup-curves
**Areas discussed:** Rating basis & offset math, Artifact shape & boundary, Plateaus & honest ranges, Confirmation-cell protocol

---

## Rating basis & offset math

| Option | Description | Selected |
|--------|-------------|----------|
| vs_maia − pooled G | Fit on rating_vs_maia, subtract per-preset pooled G (41/186/247) + C; matches SEED-104 formula, smooths noisy per-cell G | ✓ |
| vs_sf directly + C | Equivalent to per-cell G subtraction; noisier (per-cell G swings 61–313) | |
| Average both families | Midpoint fit, subtract G/2; no principled interpretation | |
| Researcher decides | Empirical comparison in RESEARCH.md | |

**User's choice:** vs_maia − pooled G (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Components + derived | Artifact stores internal fit, G_preset, C separately AND derived lookup; C a named constant, retune = regenerate | ✓ |
| Baked numbers only | Final lookup entries only; opaque provenance | |

**User's choice:** Components + derived (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Blanket ± band | One global band per preset (C's ±100 + typical fit CI) as a constant | ✓ |
| Per-entry propagated CI | Per-lookup-entry band; implies false precision | |
| No numeric band | Only the word "approximate" | |

**User's choice:** Blanket ± band (Recommended)

---

## Artifact shape & boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Artifact + generated TS | Lookup JSON + generated frontend/src/generated/ TS via gen_*.py pattern; knip exception until a consumer; no UI wiring | ✓ |
| Artifact only, no TS yet | JSON + findings note; TS created by first consumer phase | |
| Wire minimal UI too | Also apply slider ranges/label on /bots (scope extension) | |

**User's choice:** Artifact + generated TS (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| New gen script | scripts/gen_bot_strength_curves*.py reads frozen Phase-180 JSON; fit + offset + inversion + emit | ✓ |
| Extend calibration_anchor_fit.py | One script raw TSV → artifact; couples measurement to artifact churn | |
| Planner decides | Seam left to planner | |

**User's choice:** New gen script (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, ship the string | Final disclaimer as exported constant in generated TS + JSON; all surfaces import one copy | ✓ |
| Placeholder only | Polished wording deferred to first UI phase | |

**User's choice:** Yes, ship the string (Recommended)

---

## Plateaus & honest ranges

| Option | Description | Selected |
|--------|-------------|----------|
| Lowest bot_elo wins | Isotonic fit; flat-segment targets map to LOWEST bot_elo; ceiling = plateau value | ✓ |
| Smooth monotone spline | Strictly-increasing smoothed inversion; invents slope inside plateaus | |
| Researcher decides | Compare on actual curves | |

**User's choice:** Lowest bot_elo wins (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep, flagged | Include beyond_ladder Human cells (700, 1100), marked extrapolated; floor ~900; verify the odd 1100 flag | ✓ |
| Trim to validated band | Only 1100–2000 band; Human floor rises to ~1150 | |
| Researcher verifies first | Explain flags, then keep-vs-trim per cell | |

**User's choice:** Keep, flagged (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Accept measured floors | Measured floor IS the slider floor; note narrower overlap zone in findings | ✓ |
| Add low-end cells | Extend sweep below bot_elo 1100 for Light/Deep | |
| Defer to a seed | New seed alongside SEED-114 | |

**User's choice:** Accept measured floors (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Round inward | Floor UP to next 100, ceiling DOWN; only fully-measured targets | ✓ |
| Round to nearest | Friendlier ranges, partly extrapolated edges | |

**User's choice:** Round inward (Recommended)

---

## Confirmation-cell protocol

| Option | Description | Selected |
|--------|-------------|----------|
| Operator-run HUMAN-UAT | Mirror 180 D-01: phase completes at pipeline + artifact + prediction file; operator runs cells after | ✓ |
| On the critical path | Phase blocked on hours of engine wall-clock | |

**User's choice:** Operator-run HUMAN-UAT (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Off-grid predictions | Run PREDICTED bot_elo values from inversion (true artifact test); near-endpoints + mid-range; planner picks exact values | ✓ |
| Re-run measured cells | Higher-N stability check only | |
| Planner decides | Selection principle left open | |

**User's choice:** Off-grid predictions (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Within 95% CI | Measured internal rating (vs-Maia) within fit's interpolated 95% CI at that bot_elo | ✓ |
| Fixed ± tolerance | Flat ±100 internal ELO | |
| Researcher defines | Criterion proposed after CI-width inspection | |

**User's choice:** Within 95% CI (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Refit + regenerate | Fold confirmation games into fit, re-run pipeline, regenerate artifact; document shift | ✓ |
| Investigate first | Treat failure as potential methodology bug before refit | |
| Widen the band | Publish wider ± band; hides real curve errors | |

**User's choice:** Refit + regenerate (Recommended)

---

## Claude's Discretion

- Exact confirmation-cell target values; isotonic-fit implementation (stdlib PAVA vs scipy);
  TS module / JSON naming; prediction-file format; exact blanket band values per preset.

## Deferred Ideas

- Ceiling extension above ~1900 approx-blitz (SEED-114, already captured).
- Probing Light/Deep floors below bot_elo 1100 (explicitly not pursued; possible future seed).
- Custom bot builder / preset cards / SEED-098 personas (consumer surfaces, future phases).
- Reviewed todos not folded: 172-deferred-review-findings, wr01 Tailwind label fix (both
  keyword false positives, unrelated to this phase).
