# Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 115-you-vs-opponent-comparison-api-bullet-grid-ui
**Areas discussed:** Grid layout & grouping, Zone constants & bands, Sample gates & fallbacks, Filter interactions

---

## Grid layout & grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Family-grouped (Recommended) | Subsection headers per family (Severity/Tempo/Phase/Opportunity/Impact/Combos) | ✓ |
| Flat uniform grid | All 15 in one grid, no headers | |
| Headline + grouped rest | Flaw Rate oversized headline + grouped rest | |

**User's choice:** Family-grouped

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both unchanged (Recommended) | Band keeps toggle; grid fixed per-100 | |
| Keep Band, drop toggle | Band fixed to per-100, NormToggle removed — one unit panel-wide | ✓ |
| Slim the Band down | Reduce Band tiles | |

**User's choice:** Keep Band, drop toggle

| Option | Description | Selected |
|--------|-------------|----------|
| 2-col desktop, 1-col mobile (Recommended) | Wider charts, ~8 rows | |
| 3-col desktop, 1-col mobile | ~5 rows, tighter charts | ✓ |
| Single column everywhere | Max readability, long scroll | |

**User's choice:** 3-col desktop, 1-col mobile

| Option | Description | Selected |
|--------|-------------|----------|
| Per-metric domain (Recommended) | Domain calibrated per metric from §5 p05/p95 | ✓ |
| Per-family domain | One domain per family group | |
| Single global domain | One ±~2pp scale for all 15 | |

**User's choice:** Per-metric domain

---

## Zone constants & bands

| Option | Description | Selected |
|--------|-------------|----------|
| Editorial + minimum width (Recommended) | Hand-set, rounded, min visible band width | |
| Raw Q1/Q3 verbatim | Copy §5 pooled quartiles exactly, hairlines accepted | ✓ |
| Uniform rounded bands per family | One band per family | |

**User's choice:** Raw Q1/Q3 verbatim

| Option | Description | Selected |
|--------|-------------|----------|
| Pooled global for all 15 (Recommended) | Follow §5 recommendation everywhere | ✓ |
| Per-ELO for the two flagged | endgame-phase + blunders get 5 ELO-bucket zones | |

**User's choice:** Pooled global for all 15

| Option | Description | Selected |
|--------|-------------|----------|
| Backend registry, served via API (Recommended) | flaw_delta_zones.py; bounds in response; no codegen | ✓ |
| Backend registry + TS codegen | endgame_zones → gen_endgame_zones_ts pattern | |
| Frontend-only constants | TS constants only (contradicts FLAWCMP-03) | |

**User's choice:** Backend registry, served via API

| Option | Description | Selected |
|--------|-------------|----------|
| Keep you−opp, invert colors (Recommended) | Raw delta displayed; MiniBulletChart inverted-color mode | ✓ |
| Negate to opp−you | Positive = good, existing colors work | |
| Neutral bar, no verdict colors | barColor='neutral' Tufte mode | |

**User's choice:** Keep you−opp, invert colors

---

## Sample gates & fallbacks

| Option | Description | Selected |
|--------|-------------|----------|
| 20 analyzed games (Recommended) | Matches §5 cohort basis; ~half of active users | ✓ |
| 10 analyzed games | More permissive, very wide CIs | |
| 30 analyzed games | More conservative | |

**User's choice:** 20 analyzed games

| Option | Description | Selected |
|--------|-------------|----------|
| Replace grid with CTA state (Recommended) | "Analyze more games" state with count + guidance | ✓ |
| Greyed-out grid + overlay | Desaturated bullets + banner | |
| Hide the zone entirely | Nothing below floor | |

**User's choice:** Replace grid with CTA state

| Option | Description | Selected |
|--------|-------------|----------|
| Keep row, muted placeholder (Recommended) | Label + muted "no events", no reflow | ✓ |
| Hide the row | Drop zero-event bullets | |
| Render delta 0 with no CI | Zero-length bar | |

**User's choice:** Keep row, muted placeholder

| Option | Description | Selected |
|--------|-------------|----------|
| Ship with fallback (Recommended) | Keep low-clock+miss; placeholder + CI handles thin data | ✓ |
| Drop it, ship 14 bullets | Only hasty+miss survives | |
| Defer decision to plan-time check | Planner decides from FLAWCMP-04 validation | |

**User's choice:** Ship with fallback

---

## Filter interactions

| Option | Description | Selected |
|--------|-------------|----------|
| Hide zones, keep delta+CI (Recommended) | Zoneless under non-default severity filter | |
| Keep zones with caveat | Zones visible + tooltip caveat (M+B basis) | ✓ |
| Grid ignores severity filter | Grid always M+B | |

**User's choice:** Keep zones with caveat

| Option | Description | Selected |
|--------|-------------|----------|
| Amend to global-zone wording (Recommended) | Reword FLAWUI-03 + REQUIREMENTS amendment | |
| Keep requirement, future-proof copy | Generic wording that survives per-ELO refinement | ✓ |

**User's choice:** Keep requirement, future-proof copy

| Option | Description | Selected |
|--------|-------------|----------|
| Split: specific vs shared (Recommended) | Per-bullet popover + section popover split | |
| Everything per-bullet | All lines in each popover | |
| Everything in one section popover | One popover for the grid | |

**User's choice:** Other (freeform): "Follow the tooltip style used in endgame metrics. Add specific metric paragraphs if needed" — i.e. the MetricStatPopover pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| Disclosure line only (Recommended) | Section-popover line on ELO-matched zone basis | |
| Hide zones when gap filter active | Degrade like a basis mismatch | |
| Nothing | Generic zone wording covers it implicitly | ✓ |

**User's choice:** Nothing

---

## Claude's Discretion

- CI method (default: normal/t approximation over per-game deltas)
- Endpoint shape (extend flaw-stats vs sibling endpoint)
- Family header / bullet label / CTA / popover copy
- SQL aggregation strategy for per-game paired deltas
- FlawTagDistribution removal mechanics

## Deferred Ideas

- Per-ELO zone refinement (endgame-phase, blunders) — next benchmark refresh
- Tactic-motif bullets (SEED-039), eval-coverage raising (SEED-012) — v2 as scoped
