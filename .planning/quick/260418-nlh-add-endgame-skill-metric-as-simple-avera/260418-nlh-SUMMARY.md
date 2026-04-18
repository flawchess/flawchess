---
phase: 260418-nlh
plan: 01
subsystem: frontend-charts
tags: [endgames, gauge, composite-metric, ui]
requires: []
provides:
  - endgame-skill-composite-metric
affects:
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
tech-stack:
  added: []
  patterns:
    - "pure helper module-scoped alongside userRate/opponentRate"
    - "theme constants for all gauge zone colors (no literal color strings)"
    - "opacity-50 disabled-state pattern for 0-games buckets"
key-files:
  created: []
  modified:
    - frontend/src/components/charts/EndgameScoreGapSection.tsx
decisions:
  - "Blue band 45-55% reused from the Parity gauge so color semantics stay consistent across the four gauges"
  - "Mobile card is gauge-only (no WDL/You/Opp/Diff rows) because Endgame Skill is a summary, not a per-bucket breakdown"
  - "Disabled state (opacity-50, value=0) when all buckets have 0 games, matching the existing row/card pattern"
metrics:
  duration: ~15m
  completed: 2026-04-18
---

# Phase 260418-nlh Plan 01: Add Endgame Skill Composite Gauge Summary

Add a fourth "Endgame Skill" gauge to the Endgame Conversion & Recovery section that summarises Conversion / Parity / Recovery as the simple arithmetic mean of their per-bucket rates.

## What Changed

Single-file change in `frontend/src/components/charts/EndgameScoreGapSection.tsx`.

### Helper + Zones

- `endgameSkill(rows: MaterialRow[]): number | null` — filters to `games > 0`, sums each row's per-bucket rate (Conversion `win_pct/100`, Recovery `(win_pct+draw_pct)/100`, Parity `score`), divides by active count. Returns `null` when no bucket has games. Iterates once over filtered rows (no reuse of `userRate()` via a partial-record hack).
- `ENDGAME_SKILL_ZONES: GaugeZone[]` — `{0-0.45 GAUGE_DANGER, 0.45-0.55 GAUGE_NEUTRAL, 0.55-1.0 GAUGE_SUCCESS}`. All colors come from imported theme constants; no literal hex.

### Desktop

- Gauge strip wrapper changed `grid-cols-3` → `grid-cols-4`.
- Appended 4th gauge block after the existing `.map(...)` (so Conversion / Parity / Recovery keep their order and Skill reads as a right-hand summary).
- `data-testid="endgame-gauge-skill"`, label `"Endgame Skill"` (no metric suffix).
- Disabled-state styling (`opacity-50`) when `skill === null`, rendering `value=0`.

### Mobile

- Added a sibling `<div>` after the material cards `.map(...)` (inside `lg:hidden space-y-3` wrapper, before its closing `</div>`).
- `data-testid="endgame-skill-card"`. Same rounded/border/padding as existing cards.
- Contents: header row with `"Endgame Skill"` label, centered gauge. No WDL bar, no You/Opp/Diff row, no bullet chart.
- Same disabled-state behaviour as desktop.

### Info Popover

- Appended a new trailing `<p>` to the existing `<div className="space-y-2">`. Paragraph covers all five content requirements:
  1. Composite definition: simple mean of Conversion Win %, Parity Score %, Recovery Save %.
  2. Typical ~52% value and why the blue band mirrors Parity's 45–55%.
  3. One-number summary usefulness alongside filters.
  4. Caveat that it's an aggregate of three different rate types, so colors are comparable to Parity but the number isn't a true chess score %.
  5. 0-games buckets are excluded from the average.
- Uses `<strong>Endgame Skill</strong>` matching existing bold-term usage. Prose leans on commas/periods per CLAUDE.md em-dash guidance.

## Decisions

- **Blue band 45-55%** reused from the Parity gauge — gives the four gauges a consistent color story. Planner's calibration note (typical ~52%) sits comfortably in the middle of this band.
- **Mobile card stripped down to gauge-only** — Endgame Skill is a summary; duplicating WDL/You/Opp/Diff rows would add noise and imply per-bucket semantics that don't apply.
- **Disabled state via `opacity-50` + value=0** — matches the existing 0-games pattern on table rows and material cards. Alternative (conditionally omitting the whole block) would have shifted layout and broken muscle memory.

## Verification

- `npm run lint` — 0 errors (3 warnings in unrelated `frontend/coverage/` files pre-existing)
- `npx tsc --noEmit` — 0 errors (respects `noUncheckedIndexedAccess`)
- `npm run knip` — 0 issues; the new `endgameSkill` helper and `ENDGAME_SKILL_ZONES` constant are module-local and not flagged as unused exports
- `npm test -- --run EndgameScoreGapSection` — no test files for this component (expected; plan noted this is allowed)

## Deviations from Plan

None — plan executed exactly as written. No additional files touched. No additional helpers introduced. All `data-testid`s match the plan's naming (`endgame-gauge-skill`, `endgame-skill-card`). All theme constants were already imported (`GAUGE_DANGER / GAUGE_NEUTRAL / GAUGE_SUCCESS / GaugeZone`) so no new imports needed.

## Commits

- `021b4ac` — feat(260418-nlh): add Endgame Skill composite gauge

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — FOUND, 555 lines (+80, -1 vs base)
- Commit `021b4ac` — FOUND in `git log`
- `endgameSkill(` appears in source — FOUND (lines 167-177)
- `ENDGAME_SKILL_ZONES` appears in source — FOUND (lines 101-105)
- `data-testid="endgame-gauge-skill"` — FOUND (line 302)
- `data-testid="endgame-skill-card"` — FOUND (line 538)
- `grid-cols-4` on gauge strip — FOUND (line 270)
- Info popover paragraph with `<strong>Endgame Skill</strong>` — FOUND (line 245)
