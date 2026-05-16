---
created: 2026-05-16T00:00:00.000Z
title: "SPIKE (gating): validate clamped-Recovery [−300,−100] ELO ramp + pin the lower cut"
area: skills / benchmarks, endgame metrics
priority: high
files:
  - .claude/skills/benchmarks/SKILL.md
  - app/services/endgame_zones.py
  - reports/benchmarks-latest.md
related_notes:
  - .planning/notes/endgame-skill-recovery-confound.md
---

# SPIKE (gating): validate clamped-Recovery [−300,−100] ELO ramp

This is a **feasibility gate**. The Endgame Skill composite redesign (keep Conv/Parity
as-is, clamp Recovery to a contested band, keep the 3-way average) MUST NOT be planned
into a ROADMAP phase until this spike passes. See
`.planning/notes/endgame-skill-recovery-confound.md` for full reasoning.

## Hypothesis

Recovery ΔES Score Gap inverts with ELO (d=0.85, weak cohorts highest) **because its
bucket sits in the deep-losing sigmoid floor where opponent error is asymmetric and
cohort-correlated**. Constraining the Recovery bucket to a contested band that excludes
the dead-lost tail should make its ELO ramp **non-inverting** (positive, or at worst
flat) — like Parity (d=0.57 positive, opponent-neutral) already is.

## Method (benchmark DB, read-only — `mcp__flawchess-benchmark-db__query`)

Reuse the §3.2.2 per-bucket ΔES methodology from `SKILL.md` (per-user `mean_gap`,
equal-footing filter, sparse `(2400, classical)` excluded, ≥20 spans/user/bucket).
Change ONLY the Recovery bucket definition and **sweep its lower bound**:

| Recovery band | run |
|---|---|
| (−∞, −100] | baseline (current — should reproduce d≈0.85, inverted) |
| [−400, −100] | sweep |
| [−300, −100] | sweep (primary candidate) |
| [−250, −100] | sweep |
| [−200, −100] | sweep |

For each band, report per-ELO Recovery `mean_gap` (800/1200/1600/2000/2400), the
ELO Cohen's `d_max`, and **the sign of the 800→2400 trend**. Conversion and Parity
buckets are untouched — no need to re-run them.

## Pass / fail

- **PASS**: there exists a lower cut at which the Recovery ELO trend is monotone
  non-decreasing (or flat, d small) — i.e. no longer inverts. Record that cut as the
  recommended Recovery lower bound; recommend recalibrated `section2_score_gap_recov`
  band ([p25, p75] of the clamped distribution) and the resulting 3-way Skill ELO d.
- **FAIL**: every cut down to [−200,−100] still inverts (negative 800→2400 trend).
  Then the span-eval/result architecture cannot produce an honest defense signal;
  fall back to Skill = Conversion + Parity only (drop Recovery from the composite,
  keep it as a descriptive "comeback" tile labeled opponent-dependent).

## Deliverable

Append findings to `reports/benchmarks-latest.md` as a §3.2.4 block (or a scratch
report), and update `.planning/notes/endgame-skill-recovery-confound.md` Status with
the verdict + chosen cut. Then (and only then) the redesign can be routed to a phase.

---

## RESOLVED 2026-05-16 — FAIL

Ran the sweep against the benchmark DB. Every cut (−400/−300/−250/−200) still
**inverts** the ELO ramp; clamping only attenuates d (0.89 → 0.43), never flips sign.
Plus 800-cohort coverage collapses (n 306 → 71). Full results:
`reports/spike-clamped-recovery-elo-ramp-2026-05-16.md`.

**FAIL-branch decision applied:** Endgame Skill = Conversion + Parity only; Recovery
becomes a standalone opponent-dependent descriptive tile (not in composite). No
`section2_score_gap_recov` recalibration. Note Status updated. The composite redesign
is no longer gated and can be routed to a ROADMAP phase.
