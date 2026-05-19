---
title: Endgame Skill composite — Recovery opponent-confound and the [−300,−100] clamp fix
date: 2026-05-16
context: Captured during `/gsd-explore` while reviewing the shipped Phase 87.2 Section 2 ΔES Score Gap bullets against `reports/benchmarks-latest.md` §3.2. The §3.2.2 calibrated bands are already in production (not placeholders — `app/services/endgame_zones.py` lines 205-224). This note records why the Endgame Skill composite is partly invalid as a skill measure and the proposed fix.
related_files:
  - app/services/endgame_zones.py
  - app/services/endgame_service.py
  - frontend/src/generated/endgameZones.ts
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-latest.md
related_seeds: [SEED-015, SEED-016]
---

# Endgame Skill composite — Recovery opponent-confound and the [−300,−100] clamp fix

## The problem

`Endgame Skill` is the equal-weighted mean of three per-bucket ΔES Score Gaps:
Conversion (entry eval > +100cp), Parity (−100..+100cp), Recovery (eval < −100cp,
unbounded below). It also feeds the **Endgame ELO Timeline** chart, so any redefinition
is downstream-visible there.

Benchmark evidence (`reports/benchmarks-latest.md` §3.2.1 / §3.2.2, 2026-05-16 dump):

| bucket | ELO direction | Cohen's d (ELO) | opponent-confounded? |
|---|---|---|---|
| Conversion gap | up (toward 0 from −) | 1.62 | no |
| Parity gap | up, same as conv | 0.57 | no (sigmoid locally linear near 0.5) |
| Recovery gap | **down — inverts** (800 +10.7pp → 2400 +4.3pp) | 0.85 | **yes** |

Recovery is opponent-confounded **because of where its bucket boundary sits**, not
because "defense" is intrinsically unmeasurable. It is defined on the *deep-losing*
zone (eval < −100cp, unbounded — includes −800cp, mate-down). In that zone:

1. The sigmoid floor compresses the user's own downside to ~0 — only the **opponent's**
   errors can move the result up.
2. Opponent error frequency is **cohort-correlated** (weak/bullet opponents blunder back
   won games far more often). So weak cohorts post the *highest* recovery gaps
   (+17.9pp at 800-bullet) — that number measures the opponent's failure, not the
   user's defensive skill.

Net effect: Recovery's ELO ramp runs **opposite** to Conversion's, so equal-weighting
it into the composite **actively cancels** the clean conversion skill signal. The
benchmark's "Skill ELO d=0.81 keep separate" is a muted residual of a strong
conversion ramp partly neutralized by an inverse, opponent-driven recovery ramp.

## Why not just drop Recovery / use Conversion as Skill

Considered and rejected. Conversion alone has the strongest signal *and* the best
per-user coverage (1,657 users clear the floor vs Parity 1,508 vs Recovery 1,609),
so a composite is not needed for robustness. But the offense / parity / defense
**triad is a better, more legible product story** than a single number, and Parity
is a genuinely independent, opponent-neutral, positively-ELO-correlated signal
(d=0.57) that reinforces rather than cancels Conversion. No data reason to drop it.

An earlier "collapse Parity + holdable-Recovery into one symmetric Defense bucket"
idea was over-engineering — it dissolved a legible bucket for abstraction elegance.
Rejected.

## The fix (proposed, gated on validation)

Keep Conversion and Parity buckets **exactly as they are**. Surgically clamp
**Recovery to a band: eval in [−300cp, −100cp]**:

- Upper bound −100cp keeps Recovery disjoint from Parity.
- Lower bound −300cp (≈ ES_entry ~0.20, the sigmoid knee) amputates the dead-lost
  tail where opponent error registers asymmetrically and cohort-inverts the signal.

This is the same de-biasing mechanism as pulling defense out of the sigmoid floor,
applied to the **one broken boundary** only — minimally invasive, preserves the triad.

Then keep the **3-way equal-weighted composite**. If clamped-Recovery's ELO ramp
comes out positive (or flat, not inverting), all three buckets point the same way and
the average is a genuine three-dimensional skill measure, richer and more robust than
Conversion alone, with no cancellation. The Endgame ELO Timeline inherits a richer,
still-monotone signal.

## Honest residuals (do not paper over)

- The clamp **de-biases, it does not de-noise**. Terminal-span ΔES uses the game
  *result*, so single-game opponent error is still present at any entry eval — but as
  roughly *symmetric variance* (washed out by per-user means), not cohort *bias*.
  Evidence this works: Parity gap (entry ≈ 0, maximally exposed to opponent error)
  still yields a clean positive monotone ELO ramp, not an inverted one.
- The exact lower cut (−400 / −300 / −250 / −200) is **empirical, not principled** —
  it is the entry-eval where Cohen's d stops being negative. Must be found, not assumed.
- The only *truly* opponent-invisible defense metric is per-move-vs-engine accuracy,
  which needs per-ply Stockfish eval the span-eval architecture does not have. The
  clamp is the best signal this architecture can honestly produce.

## Separate, independent improvement

Conversion Score Gap display: subtract the blue-zone midpoint (band `[−0.11, 0.00]`
→ midpoint −0.055) so `0` renders as "typical population result" instead of an
off-center blue zone fighting the user's "zero = neutral" intuition. Pure display
affine shift — data, band width, Cohen's d unchanged. Precedent: §3.1.5 / §3.1.6
gauges are already centered on their null. Independent of the composite redesign;
shippable on its own. Tracked as a separate todo.

## Status / next

**Spike RESOLVED 2026-05-16 — FAIL.** See
`reports/spike-clamped-recovery-elo-ramp-2026-05-16.md`. Sweeping the Recovery lower
bound (−400 / −300 / −250 / −200) only *attenuates* the ELO inversion (d 0.89 → 0.43);
it never flips sign. Even [−200,−100] (adjacent to positively-ramping Parity) still
inverts. The confound is **not** a deep-lost-floor artifact removable by clamping —
result-based terminal ΔES means weak-cohort opponents under-convert at every
disadvantage level. Clamping also collapses 800-cohort coverage (n 306 → 71).

**Decision (FAIL branch):** the clamp is abandoned. Endgame Skill composite =
**Conversion + Parity only** (equal-weighted; both honest, opponent-neutral,
same-direction). Recovery Score Gap stays as a **standalone descriptive tile**
("comeback"), explicitly opponent-dependent, NOT in the composite and NOT a skill
verdict. Endgame ELO Timeline now tracks the clean 2-way signal. No
`section2_score_gap_recov` recalibration needed (descriptive band stays).

## LOCKED SPEC — phase 87.3 (confirmed 2026-05-16)

Definition settled after a full A-vs-B exploration (see git history this date).
Empirical comparisons run against the benchmark DB (`mcp__flawchess-benchmark-db`):

- **Reference choice:** Lichess 2300+ expected-score sigmoid (`k=0.00368208`) beats a
  Stockfish-perfect anchor. Evidence: with a perfect-play reference the conversion
  region is saturated (≈0.95–1.0), so subtracting it removes almost no entry-difficulty
  variance — ELO Cohen's d ≈ 0.90 for *any* perfect-play instantiation (step or steep
  sigmoid), vs **d ≈ 1.39** for the Lichess-referenced gap. The gentle Lichess slope is
  what de-confounds (it stays in the 0.6–0.9 dynamic range over conversion entries).
- **A2 vs B is a presentation choice, not a signal choice** — both are monotone
  transforms of the *same* composite gap, so they rank users identically.
- **Endgame ELO formula is the hard constraint.** `_endgame_elo_from_skill`
  (`app/services/endgame_service.py:1348`, Phase 57): `endgame_elo =
  actual_elo + 400·log10(s/(1−s))`, `s` clamped [0.05, 0.95], **s=0.5 ⇒ lines
  coincide**. This mandates `s ∈ [0,1]`, median 0.5. Percentile rank fits natively;
  A2 (~0.96-centered) would peg the clamp (+510 Elo) for *every* player and require
  scrapping the formula. So percentile is **mandatory** for the timeline, not optional.

### Locked definition

1. **Substrate:** per-(user / rolling-window) composite = equal-weighted mean of
   **Conversion ΔES** and **Parity ΔES**; Lichess 2300+ sigmoid reference;
   ≥10-span floor per active bucket; **Recovery excluded** from the composite.
2. **Endgame Skill (gauge + number):** pooled **percentile rank** of that composite
   vs a **frozen, versioned** benchmark reference distribution; neutral zone
   centered at **50**.
3. **Endgame ELO timeline:** unchanged Phase 57 `_endgame_elo_from_skill`, with
   `s` = that percentile. **Invariant the plan must assert:** `s ∈ [0,1]`,
   population median = 0.5 (preserves the "typical player ⇒ lines coincide"
   contract the current rate-based composite satisfies because it pools ≈ 50.6%).
   Frozen reference ⇒ historical Endgame ELO points never drift.
4. **Recovery Score Gap:** standalone descriptive tile, explicitly
   opponent-dependent, NOT in the composite, NOT a skill verdict.
5. **Independent:** Conversion Score Gap display-centering todo (unchanged,
   shippable separately).

Next: insert ROADMAP phase 87.3 and run plan-phase against this locked spec.
