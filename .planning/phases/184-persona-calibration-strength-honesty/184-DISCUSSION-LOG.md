# Phase 184: Persona Calibration & Strength Honesty - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-22
**Phase:** 184-persona-calibration-strength-honesty
**Areas discussed:** Label vs retarget, Ladder coherence, Honesty surfaces, Run & pipeline

---

## Label vs retarget

| Option | Description | Selected |
|--------|-------------|----------|
| Retarget + measure (Recommended) | Re-seat each persona's botElo via the Phase-181 lookup so its preset strength targets the rung, then harness-measure each persona cell (style delta included) and display THAT measured value as the label | ✓ |
| Label-only | Keep botElo === rung; relabel with measured values (Human rungs would compress to ~920–~1060) | |
| Retarget to exact rung | Iteratively adjust botElo until measured ≈ rung, display clean rung numbers | |

**User's choice:** Retarget + measure

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot (Recommended) | Single measurement round (~2 overnight runs); measured value is the label, tilde absorbs residual error | ✓ |
| Correction pass if far off | Re-measure cells landing >±75–100 from their rung in a smaller follow-up run | |
| You decide | Plan one-shot with correction pass as documented contingency | |

**User's choice:** One-shot

---

## Ladder coherence

| Option | Description | Selected |
|--------|-------------|----------|
| Nearest 50 (Recommended) | ~950, ~1250 — matches CI scale without pseudo-precision | ✓ |
| Nearest 100 | Coarser; more rungs collapse to the same label | |
| Nearest 25 | Finer, risks implying more precision than CIs support | |

**User's choice:** Nearest 50

| Option | Description | Selected |
|--------|-------------|----------|
| Pool within CI (Recommended) | Enforce weak monotonicity PAVA-style within each style column; ties allowed | ✓ |
| Show as measured | Fully honest raw values even if a column shows an inversion | |
| Re-measure violators | Treat inversions as measurement problems (contradicts one-shot budget) | |

**User's choice:** Pool within CI

| Option | Description | Selected |
|--------|-------------|----------|
| Accept as measured (Recommended) | Divergent labels across styles at the same rung (attacker-1200 ~1150 vs wall-1200 ~1250) | ✓ |
| Align per rung | Pool across the 4 styles per rung to one number (hides the measured style delta) | |
| You decide | Pick once the actual spread is visible | |

**User's choice:** Accept as measured

---

## Honesty surfaces

| Option | Description | Selected |
|--------|-------------|----------|
| ~900 + info popover (Recommended) | Bottom rung shows its measured value like every other persona; floor explanation in the detail-surface popover | ✓ |
| Plain ~900, no marker | Tilde alone signals approximation | |
| Range or qualifier label | '≤900' or '800–900' on the card itself | |

**User's choice:** ~900 + info popover

| Option | Description | Selected |
|--------|-------------|----------|
| Global cap at ~1800 (Recommended) | No persona label ever exceeds ~1800 regardless of rung | ✓ |
| Cap only the 1800 rung | Lower rungs that overshoot show measured values | |
| You decide | Likely moot given the plateau | |

**User's choice:** Global cap at ~1800

| Option | Description | Selected |
|--------|-------------|----------|
| Popover on every label (Recommended) | Reusable measurement-disclosure popover on all 24 detail surfaces; floor note is a variant line | ✓ |
| Floor popover only | Only the 800 rung gets an explanation | |
| Bots-page footnote | Single note under the grid | |

**User's choice:** Popover on every label

---

## Run & pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Operator-run + runbook (Recommended) | Phase ships harness style-wiring + persona-cell schedule + runbook; user runs ~2 overnight sweeps under the resume supervisor; final plan fits offsets; HUMAN-UAT gate | ✓ |
| Claude runs them | In-session background runs (~10-12h wall-clock, risky) | |
| Split the phase | Merge tooling first, runs + label-update as follow-up quick task | |

**User's choice:** Operator-run + runbook

| Option | Description | Selected |
|--------|-------------|----------|
| Generated TS (Recommended) | reports/data JSON → generated frontend/src/generated file keyed by PersonaId, CI drift-checked (botStrengthCurves.ts pattern) | ✓ |
| Hand-edited registry | Transcribe measured values into personaRegistry.ts with provenance comments | |
| You decide | Pick during planning | |

**User's choice:** Generated TS

| Option | Description | Selected |
|--------|-------------|----------|
| Documented policy note (Recommended) | Doc comment in botStyleBundles.ts + generated file: style-param changes invalidate calibration, re-run the sweep | ✓ |
| Hash guard in CI | Embed style-bundle hash in generated file; CI fails on drift | |
| Accept staleness | Tilde labels tolerate small tuning drifts | |

**User's choice:** Documented policy note

---

## Claude's Discretion

- Harness style-wiring details (BotStyleParams into the harness selectBotMove call)
- Persona-cell schedule design (anchor windowing, games-per-cell, opening FEN sampling)
- Fit approach for per-persona offsets and internal→blitz conversion reuse
- Retarget edge mechanics (800-rung clamp, trust of beyond_ladder lookup rows)
- Generated-file name/location and generator language
- Popover copy (disclosure requirements override minimalism per percentile-chip precedent)

## Deferred Ideas

- Ladder extension above ~1800 / >2000 personas — SEED-114 (dormant)
- Style-bundle retuning + re-calibration workflow — future; only the staleness policy ships now
- Measuring style-opening-book strength effects — structurally outside the harness; accepted
- Correction-pass re-measurement — not budgeted; revisit only if UAT shows labels wildly off
