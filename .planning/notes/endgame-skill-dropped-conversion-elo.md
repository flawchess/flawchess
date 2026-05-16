---
title: Endgame Skill dropped — timeline rewired as Conversion ELO from Conv ΔES
date: 2026-05-16
context: Captured during `/gsd-explore` reviewing Phase 87.3 (pending UAT) gauges. Two concerns surfaced — weak players posting high percentile-based Endgame Skill, and a volatile Endgame ELO timeline swinging above/below actual ELO — that traced to the same root: the percentile-of-ΔES design was validated on cross-sectional between-bucket Cohen's d but is consumed both as an individual absolute-skill label and as a within-user temporal curve, neither of which that validation licenses.
supersedes:
  - .planning/notes/endgame-skill-recovery-confound.md
related_files:
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_llm.py
  - frontend/src/components/charts/EndgameMetricsSection.tsx
  - reports/benchmarks-latest.md
related_phases: [87.2, 87.3, 87.4]
---

# Endgame Skill dropped — timeline rewired as Conversion ELO from Conv ΔES

## Supersession

This note supersedes [[endgame-skill-recovery-confound.md]] (LOCKED SPEC, 2026-05-16). That spec defined Endgame Skill as the pooled percentile rank of an equal-weighted Conv+Parity ΔES composite, feeding the Phase 57 `_endgame_elo_from_skill` formula. After reviewing live gauges from real users (pending 87.3 UAT), that design is being abandoned. Endgame Skill as a single-number concept is being **removed from the product**.

## What broke under percentile-of-ΔES

Two concerns surfaced in 87.3 UAT review, with a shared root cause:

1. **Weak players showed high Endgame Skill.** Some sub-1000 players posted Endgame Skill ratings above stronger players. Mechanism: the composite's terminal score is opponent-dependent (weak opponents err more → weak players' composite inflates). The fixed Lichess-2300+ reference removes *entry difficulty* but not *opponent strength*. The pooled percentile then maps inflated composites to absolute-population percentiles. This is the same opponent-error cohort confound that got Recovery dropped — it survives in Conv/Parity because their benchmark ELO ramp is positive and non-inverting, not because they are opponent-neutral. Non-inversion ≠ unconfounded.
2. **Endgame ELO Timeline became volatile.** Where the old rate-based `s` (Conv+Par+Recov rate pooled ≈ 0.506) was a self-averaging proportion, the new percentile-of-continuous-ΔES is steepest exactly where benchmark density is highest (the middle), so per-rolling-window sampling noise gets amplified at the median and again by the `logit→ELO` map. The LOCKED SPEC's invariants (`s ∈ [0,1]`, median 0.5, frozen reference) said nothing about *per-window variance*.

## Why no composite survives

Three replacements were considered:

- **3-way rate (Conv+Par+Recov)** — Recovery opponent-confounds (ΔES ELO ramp inverts, d≈0.85, weak cohorts highest). Already abandoned in 87.3.
- **2-way ΔES percentile (Conv+Par ΔES)** — concerns 1+2 above.
- **2-way rate (Conv+Par average)** — empirically validated (2026-05-16, benchmark DB):

| Metric | p50 @800 | p50 @2400 | Δ | Cohen's d (800 vs 2400) |
|---|---|---|---|---|
| Conversion rate | 0.6842 | 0.7427 | +0.058 | **0.83** keep |
| Parity rate | 0.5000 | 0.5390 | +0.039 | **0.49** review |
| Conv+Par avg | 0.5775 | 0.6386 | +0.061 | **0.80** keep |
| Old 3-way Conv+Par+Recov | 0.4885 | 0.5385 | +0.050 | 0.78 |

The Conv+Par average works mathematically but (a) pools to ≈ 0.61 instead of 0.50, breaking the Phase 57 "typical player ⇒ s=0.5 ⇒ lines coincide" invariant for free (requires an affine recenter with a pivot constant that has no physical meaning), and (b) dilutes the strong Conv signal (d=0.83) with the weak Parity signal (d=0.49) to land at d=0.80 — the average adds noise without adding interpretability. Re-weighting Conv vs Par with non-negative weights cannot bring the pool back to 0.5 (would require negative weight on Conv).

**No composite has a definition that survives scrutiny on all four axes**: cohort de-confounding, individual absolute-skill interpretation, per-window temporal stability, and the Phase 57 median-coincide invariant. The "triad makes a better product story" argument from the original Recovery note now cuts the other way: a confected single number is the cause of every failure mode here.

## Locked decision

1. **Drop Endgame Skill entirely as a concept.** Remove the Endgame Skill card, the Endgame Skill Score Gap card, the percentile reference artifact (D-01..D-03 of 87.3 CONTEXT), the drift-gate, and the Endgame Skill LLM payload field.
2. **Conv / Parity / Recovery remain as three independent cards.** Conversion is the actual skill axis (user's technique dominates variance). Parity and Recovery stay as **descriptive tiles** (Parity = near-coin signal influenced by opponent variance; Recovery = opponent-dependent comeback metric). The 87.3 reading-order and Recovery descriptive framing/popover copy are preserved minus the Skill card.
3. **Endgame ELO Timeline → Conversion ELO Timeline.** Renamed to match what it now measures: "what your ELO would be if everyone played the way you do when up material."
4. **Fed from Conversion ΔES Score Gap** (Phase 87.2, already shipped — Lichess-2300+ sigmoid reference, calibrated band `[−0.11, 0.00]`, pop p50 = `−0.0474`, d=1.62 between 800 and 2400, the strongest ELO ramp in the entire benchmark report).
5. **Affine recenter into Phase 57**, unchanged formula:
   ```
   s = clamp(0.5 + α · (conv_ΔES − (−0.0474)), 0.05, 0.95)
   endgame_elo = actual_elo + 400 · log10(s / (1 − s))      # Phase 57, unchanged
   ```
   Pivot at the benchmark p50 (`−0.0474`) → typical player ⇒ s=0.5 ⇒ Conversion ELO = actual ELO. Plan-phase tunes `α` so the calibrated band `[−0.108, +0.002]` maps to s ∈ ~[0.40, 0.60]. Frozen constants ⇒ historical timeline points non-drifting by construction.

## Honest residual

Conv ΔES is still result-based, so the cohort-error confound is technically present. At d=1.62 — the strongest signal in the system — genuine skill stratification dominates noise by a large margin. The "weak player out-percentiles a strong one" failure mode is much rarer under a direct affine of Conv ΔES than under percentile-of-Conv+Par-ΔES, because no percentile transform is stretching outliers. This is the best signal the current span-eval architecture (no per-ply Stockfish eval) can honestly produce. A per-move-accuracy metric remains the only fully opponent-invisible defense signal and would be a separate milestone.

## What survives from 87.2 / 87.3

- **87.2** ships as merged (PR #98). The Conv/Par/Recov ΔES Score Gap bullets remain on the three surviving cards; only the Skill card and Skill Score Gap card are removed. The Conversion ΔES Score Gap is now structurally promoted: it is the **spine** of the Endgame metrics section, not one of four parallel metrics.
- **87.3** is largely retracted. Surviving from 87.3: Recovery and Parity descriptive framing + popover copy, Conversion display-centering todo (now in-scope for 87.4 — see `.planning/todos/pending/2026-05-16-conversion-score-gap-display-centering.md`), CHANGELOG Section 2 entries that don't reference the percentile composite. Removed: Endgame Skill card, Endgame Skill Score Gap card, percentile reference artifact, drift-gate gen script, Skill LLM payload field, `endgame_skill_percentile` API field.
- **87.3 UAT items** for the Endgame Skill gauge and the current Endgame ELO timeline are flagged as superseded — they should not be approved as shipped.

## Next

Phase 87.4 inserted in `.planning/milestones/v1.17-ROADMAP.md`: "Drop Endgame Skill, rewire timeline as Conversion ELO from Conv ΔES." That phase carries the implementation: remove Skill surfaces (BE/FE/LLM), rename timeline, wire the affine recenter, fold in the Conv ΔES display-centering, prompt-version bump, CHANGELOG entry. Phase 57 `_endgame_elo_from_skill` stays untouched — only its input source is rewired.
