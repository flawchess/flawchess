---
created: 2026-05-03T00:00:00.000Z
title: Rerun /benchmarks under equal-footing (±100) opponent filter and compare ELO Cohen's d ramp
area: skills / benchmarks
files:
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-2026-05-03.md
  - frontend/src/generated/endgameZones.ts
related_notes:
  - .planning/notes/benchmark-equal-footing-framing.md
---

## What

Rerun `/benchmarks` to produce `reports/benchmarks-YYYY-MM-DD.md` (next run date)
under the new equal-footing filter (`abs(opponent_rating - user_rating) <= 100`)
that was added to §2/§3/§6 in `.claude/skills/benchmarks/SKILL.md`.

Then compare the resulting per-cell and marginal Cohen's d values against the
2026-05-03 baseline (the last unfiltered run) for these metrics:

- §2 Conversion (per-user)
- §2 Parity (per-user)
- §2 Recovery (per-user)
- §2 Endgame Skill (per-user)
- §3 Endgame ELO gap
- §6 Per-class score / conversion / recovery (pooled-by-class summary is the
  primary comparison; per-cell deltas secondary)

## Why

The 2026-05-03 report flagged a likely matchmaking confound: 2400-rapid players
face opponents averaging -128 Elo, so the unfiltered ELO ramp on conv/skill
overstates pure skill differences. The framing decision is captured in
`.planning/notes/benchmark-equal-footing-framing.md`.

We want the empirical answer: how much of the ELO ramp survives at equal footing?

## Decision rule

For each metric × ELO axis pair:

- **If filtered ELO d_max < 0.5** (Cohen's "collapse" boundary), retire the
  per-ELO stratification recommendation in the threshold summary table and
  switch the recommended action to "keep" or "widen pooled". Document the d
  before/after in the report's "Top-axis collapse summary".
- **If filtered ELO d_max ≥ 0.5**, keep the per-ELO stratification
  recommendation but use the filtered cell values for any proposed bands.

Same rule on TC axis for §2 (conv / recov), where the unfiltered ramp was even
larger (`d=1.02` bullet↔rapid on conversion).

## Out of scope

- §1, §4, §5 are not skill-stratification metrics and are not affected by the
  filter (see note for rationale).
- Not actually changing `frontend/src/generated/endgameZones.ts` yet — the new
  recommended bands flow through the existing zone-calibration loop after the
  filtered numbers land.

## Acceptance

- [ ] New report exists at `reports/benchmarks-YYYY-MM-DD.md` with header note
  flagging the equal-footing filter
- [ ] Top-axis collapse summary table compares filtered d_max vs 2026-05-03
  baseline d_max for each metric
- [ ] Recommended thresholds summary table updated per the decision rule above
- [ ] Sample-floor / cell-coverage retention reported per cell (already required
  by the SKILL.md changes)
