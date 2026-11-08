# Phase 245: Analysis Contextual Explain Bar for Flaws (SEED-208) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-05
**Phase:** 245-analysis-explain-bar
**Areas discussed:** Inaccuracy support, Missing-PV fallback

Scout findings presented before selection: `game_flaws` holds mistakes and blunders only, so tactic-lines 404s for inaccuracies. In dev PV-complete games, missed PV is null for about 20% of M/B flaws and allowed PV for about 1%; unanalyzed games have almost no PVs.

Areas offered but not selected: Bar copy & content (left to UI-SPEC), Deep-link auto-open (kept unchanged).

---

## Inaccuracy support

| Option | Description | Selected |
|--------|-------------|----------|
| Small backend fallback | tactic-lines rebuilds the board from game_positions.move_san when no game_flaws row exists | |
| Drop inaccuracies | Explain covers mistakes and blunders only, purely frontend | ✓ |
| Separate endpoint | New position-based PV endpoint for any ply | |

**User's choice:** Drop inaccuracies

---

## Missing-PV fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to other line | Null direction-rule line → open the other orientation | ✓ |
| Strict direction rule | No fallback; Explain unavailable | |

| Option | Description | Selected |
|--------|-------------|----------|
| Hide the bar | No bar when both PVs are null | ✓ |
| Disabled with tooltip | Greyed Explain with "No engine line for this move" | |

| Option | Description | Selected |
|--------|-------------|----------|
| Prefetch on landing | useTacticLines fires at an M/B flaw ply; bar shows once a line exists | ✓ |
| has_pv flags on FlawMarker | Backend adds availability flags | |
| Optimistic, resolve on click | Always show; fetch on click | |

---

## Claude's Discretion

- Bar copy/visuals/icon/tokens (UI-SPEC), Umami event names, testids, fork-node bar state, fast-forward interaction.
- Deep-link tactic auto-open kept unchanged.

## Deferred Ideas

- Explain for inaccuracies (needs the fetch_tactic_lines fallback).
- Explain for free-play / what-if moves.
