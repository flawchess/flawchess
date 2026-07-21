# Phase 180: Three-preset bot strength curves - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-19
**Phase:** 180-three-preset-bot-strength-curves
**Areas discussed:** Run scope, Grid design, Fit & output artifact, Two-pass anchor selection, Games budget, Pilot gate, Point placement

---

## Run scope

| Option | Description | Selected |
|--------|-------------|----------|
| Harness + pilot, sweep is HUMAN-UAT | Deliver harness fixes proven on a small pilot; full ~18h sweep + curves + findings folded in as an operator-run step. | ✓ |
| Full sweep in-phase | Phase not done until the real ~1,440-game sweep runs and curves + G_preset are fitted in-phase (mirrors 173 Plan 04). | |

**User's choice:** Harness + pilot, sweep is HUMAN-UAT
**Notes:** Keeps the overnight run off the interactive critical path; matches CLAUDE.md "flag long runs as HUMAN-UAT."

---

## Grid design

| Option | Description | Selected |
|--------|-------------|----------|
| Per-preset ranges (Human low, Light mid, Deep high) | Each preset gets its own bot_elo points covering the range it serves, overlapping in the middle. | ✓ |
| Uniform grid across all three | Same 5 bot_elo points for every preset; directly comparable but spends games out of range. | |
| Decide after inspecting anchor spacing | Defer point placement entirely to planner/researcher. | |

**User's choice:** Per-preset ranges (Human low, Light mid, Deep high)
**Notes:** Shape locked; exact point values deferred (see Point placement below).

---

## Fit & output artifact

| Option | Description | Selected |
|--------|-------------|----------|
| Extend calibration_anchor_fit.py (Python) | Reuse BT/Elo fitter, anchors pinned at INTERNAL_RATING, separate vs-Maia/vs-SF fits for G_preset, JSON mirroring anchor-ladder-internal-scale.json. | ✓ |
| Lightweight JS aggregation in the harness | Compute ratings + G_preset in the .mjs pipeline; fewer parts but diverges from 173 method. | |
| Let planner decide | No strong preference. | |

**User's choice:** Extend calibration_anchor_fit.py (Python)
**Notes:** Consistent fit method with 173; CIs for free.

---

## Two-pass anchor selection

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Phase 173 schedule + connectivity module | Drive cell placement through calibration-anchor-schedule.mjs (informative band, connectivity/cross-family guard, rescue). | ✓ |
| Harness-native internal-scale windowing | New, simpler purpose-built selection in the harness. | |
| Let planner decide | Defer reuse-vs-fresh. | |

**User's choice:** Reuse Phase 173 schedule + connectivity module
**Notes:** Adapt from anchor-vs-anchor pairs to bot-vs-anchor cells.

---

## Games budget

| Option | Description | Selected |
|--------|-------------|----------|
| 24 | Seed floor; ~±71/anchor, ~±35 combined; keeps sweep near ~18h. | |
| 30 | Tighter (~±64/anchor); ~25% more wall-clock; better for the flat top of the ladder. | |
| Let planner decide | Set N from a precision target given measured anchor spacing. | ✓ |

**User's choice:** Let planner decide
**Notes:** Within the seed's 24–30 band; applies to the operator sweep, not the pilot.

---

## Pilot gate

| Option | Description | Selected |
|--------|-------------|----------|
| Logic tests + small real-engine pilot | Deterministic .check.mjs tests on new windowing/two-pass PLUS a 1-2 real-cell pilot (ratings, windowing, both families, --resume). | ✓ |
| Logic tests + dry-run only | Tests + no-engine grid dry-run; no real games in-phase. | |
| Small real-engine pilot only | Eyeball 1-2 cells, no formal logic tests. | |

**User's choice:** Logic tests + small real-engine pilot
**Notes:** Strongest confidence; guards the new selection/windowing logic and confirms real play.

---

## Point placement

| Option | Description | Selected |
|--------|-------------|----------|
| Lock shape, planner places points | Three per-preset rows / non-uniform shape locked; exact bot_elo values chosen after inspecting INTERNAL_RATING spacing. | ✓ |
| I'll specify ranges now | User provides the per-preset spans as locked grid points. | |

**User's choice:** Lock shape, planner places points
**Notes:** Evidence-based placement against anchor bracketing.

---

## Claude's Discretion

- Exact per-preset `bot_elo` point values (deferred to planner/researcher).
- Measure-pass games/cell within 24–30 (deferred to planner).
- Precise adaptation of the 173 schedule module from anchor-vs-anchor pairs to bot-vs-anchor cells.

## Deferred Ideas

- Absolute human-ELO pin `C` and the shipping lookup curves / slider ranges / preset cards — SEED-104.
- Bot personas / play-style layer — SEED-098.
