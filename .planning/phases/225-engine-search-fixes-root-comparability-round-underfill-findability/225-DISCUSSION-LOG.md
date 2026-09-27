# Phase 225: Engine Search Fixes — Root Comparability, Round Underfill & Findability Fallback - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-27
**Phase:** 225-engine-search-fixes-root-comparability-round-underfill-findability
**Areas discussed:** none individually. The user answered "You decide" to the area selection, delegating all four areas to Claude.

---

## Visit-guard scope

| Option | Description | Selected |
|--------|-------------|----------|
| Guard all root children | Simple; but root PUCT never visits clearly-worse low-prior children, so it mostly disables the clear-winner stop | |
| Guard within-margin children | Cheap; leaky because unexpanded values are unboosted and the first-expansion boost can exceed the 0.05 margin | |
| Boost-aware window (margin + measured allowance) | Guard set sized from the measured first-expansion boost; no value correction | ✓ (Claude) |
| Also guard the deadline cut | Risk: multi-round overrun makes the bot flag | not selected; report-only exposure count |

## Findability fallback

| Option | Description | Selected |
|--------|-------------|----------|
| As seeded: f·V + (1−f)·V_fallback | Promotes hard-to-find bad moves toward the average (breaks rankScore ≤ V) | |
| Clamped: f·V + (1−f)·min(V, V_fallback) | Keeps rankScore ≤ V; bad moves sort by own V | ✓ (Claude) |
| P_REF_ANCHORS | Retune only if a D-03 regression case fails | ✓ (Claude) |

## Non-root candidate cap (item 4)

| Option | Description | Selected |
|--------|-------------|----------|
| Include as a measured arm | Third bot-strength change, needs its own calibration arm | |
| Defer | Keep phase to two bot-strength changes; revisit after item 2's throughput win | ✓ (Claude) |

## Measurement design

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked arms A0 → A2 → A21 | Attribution by successive diffs; item 3 is off the bot path | ✓ (Claude) |
| Reuse Phase 199 five-cell parity check verbatim | Same cells, thresholds, verdict script; A21 first, A2 only on fail/shift | ✓ (Claude) |
| Refit on failure | Out of scope; ship only passing items, seed a follow-up | rejected |

## Claude's Discretion

All four areas (the user selected "You decide").

## Deferred Ideas

- Non-root candidate cap (item 4).
- Guarding flatness branch / deadline cut, pending the exposure count.
