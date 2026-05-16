# Spike: clamped-Recovery ELO ramp validation — 2026-05-16

**Gate for:** Endgame Skill composite redesign (keep Conv/Parity, clamp Recovery, keep 3-way average).
**Source note:** `.planning/notes/endgame-skill-recovery-confound.md`
**Method:** §3.2.2 per-user ΔES gap methodology (equal-footing ±100, ≥20 spans/user, sparse `(2400,classical)` excluded), pooled per-ELO over TC. Recovery bucket lower bound swept; Conv/Parity untouched. Benchmark DB, read-only.

## Result — FAIL

Per-ELO Recovery `mean_gap` (pp) and Cohen's d(800↔2400). Positive d here = **inverted** (weak cohort higher), the failure direction.

| Recovery band | 800 | 1200 | 1600 | 2000 | 2400 | trend | d(800↔2400) | 800-cohort n_users |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| (−∞, −100] baseline | +10.7 | +7.8 | +5.1 | +4.1 | +4.3 | inverts | 0.89 | 306 |
| [−400, −100] | +9.8 | +7.7 | +4.2 | +3.9 | +3.3 | inverts | 0.86 | 200 |
| [−300, −100] | +8.4 | +6.5 | +3.1 | +2.7 | +2.8 | inverts | 0.71 | 151 |
| [−250, −100] | +7.4 | +5.9 | +2.3 | +2.2 | +2.1 | inverts | 0.63 | 121 |
| [−200, −100] | +5.5 | +5.3 | +2.4 | +1.4 | +1.6 | inverts | 0.43 | 71 |

Baseline reproduces the §3.2.2 inverted ramp (report ELO marginal +10.7/+7.8/+5.1/+4.1/+4.3; d≈0.85 cell-marginal ≈ 0.89 pooled-by-ELO here). Sanity check passes.

## Conclusion

**PASS criterion** (a cut where the ELO trend is non-decreasing / flat with small d) is **never met**. Clamping monotonically *attenuates* the inversion (d 0.89 → 0.43) but never flips its sign. Even [−200,−100] — directly adjacent to Parity, where the ELO ramp is *positive* (d=0.57) — still inverts at d=0.43.

Two independent failures:

1. **The confound is not a deep-lost-floor artifact.** It persists across the entire disadvantaged range because terminal-span ΔES is result-based: weak-cohort opponents fail to convert advantages at *every* disadvantage level, not only the dead-lost one. Pulling out of the sigmoid floor (the §3.2.2 / note hypothesis, by Parity analogy) is necessary but **not sufficient**.
2. **Coverage collapse.** Clamping starves the 800 cohort (n 306 → 71 at −200). Weak players' losing endgames are predominantly deep-lost; a tight band removes exactly the data the metric most needs to characterize.

The only architecturally honest defense signal would be per-move-vs-engine accuracy (opponent-invisible by construction), which requires per-ply Stockfish eval the span-eval architecture does not have. Out of scope.

## Verdict → routing

Take the spike's **FAIL branch**: drop Recovery from the Endgame Skill composite.

- **Endgame Skill = equal-weighted mean of Conversion + Parity** (both honest, opponent-neutral, same-direction positive ELO ramps; no cancellation).
- **Recovery Score Gap survives as a standalone descriptive tile** ("comeback from losing endgames"), explicitly framed as opponent-dependent — NOT a skill verdict, NOT in the composite.
- **Endgame ELO Timeline** is downstream of Skill: it now tracks a clean Conv+Parity signal instead of a partially-cancelled 3-way one.
- The clamp idea is abandoned (no recalibration of `section2_score_gap_recov` bounds needed; the existing descriptive band stays for the standalone tile).
