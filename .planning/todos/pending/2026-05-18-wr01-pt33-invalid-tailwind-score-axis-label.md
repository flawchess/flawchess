---
created: 2026-05-18T23:30:00.000Z
title: WR-01 — pt-33 is not a valid Tailwind class on the Score Y-axis label
area: frontend
source: 88.3-REVIEW.md (WR-01)
files:
  - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
---

## Problem

`EndgameScoreOverTimeChart.tsx:175` uses `pt-33`, which is not on Tailwind's
default spacing scale (siblings use `pt-32` / `pt-40`). Tailwind emits no rule
for `pt-33`, so the rotated "Score" Y-axis label collapses to `padding-top: 0`
and renders misaligned on every desktop render. Flagged by the Phase 88.3 code
review (88.3-REVIEW.md, WR-01, Warning severity).

Deferred 2026-05-18 by user decision — out of scope for Phase 88.3 (SC-4 was the
Palmtree-glyph + shared-helper rollout; this is a pre-existing layout defect in
a file the phase happened to touch).

## Solution

Replace `pt-33` with the intended on-scale value. Determine the correct padding
by comparing against the sibling axis-label offsets (`pt-32` / `pt-40`) and the
Y-axis label position on the other over-time charts that share the layout, then
use the matching Tailwind spacing token (or an arbitrary value `pt-[Npx]` if no
scale token fits). Verify visually at desktop and 375px that the rotated "Score"
label aligns with the axis.
