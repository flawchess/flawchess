---
created: 2026-05-17T00:00:00.000Z
title: Reframe Recovery Score Gap popover copy — opponent-first
area: frontend
files:
  - frontend/src/components/charts/EndgameMetricCard.tsx
---

## Why

The Recovery Score Gap bullet is structurally an opponent-conversion signal,
not a player-skill signal: when you enter an endgame with eval <= -1.0, you
cannot outperform Stockfish on your own — any positive score gap is the
opponent failing to convert their winning position. Benchmarks §3.2.3
confirms this: raw recovery rate is flat across ELO (29.7% at 800 → 33.0%
at 2400) but the score gap collapses from +10.7pp at 800 to +4.3pp at 2400
(d=0.88). That gradient is pure opponent-blunder differential.

Current popover copy says *"you salvaged disadvantages above the Stockfish
baseline"* — gives the user agency they don't have and invites the wrong
("higher = I'm a better endgame player") reading.

Keep the metric name `Recovery Score Gap` for parity with Conv/Parity Score
Gap; the body copy carries the caveat.

## What

In `frontend/src/components/charts/EndgameMetricCard.tsx`, replace the
`recovery` entry in `POPOVER_COPY` (currently lines 51-52) with:

> Per-span Score Gap on endgame spans you entered behind by >= 1 pawn.
> Above baseline = opponents failed to convert their winning positions
> more often than Stockfish predicted. Not a pure skill signal — you cannot
> outplay an engine from a lost position on your own.

(Style: no em-dashes per CLAUDE.md — use a regular hyphen or comma. The
draft above is the intent; rephrase the dash on commit.)

No code changes outside that string. No test changes (existing tests don't
assert on popover copy strings).

## Out of scope (parked, not in this todo)

- Recalibrating the Recovery gauge band `(0.24, 0.36)` per TC (d=1.10) — defer
  to next zones-registry revision.
- Adjusting the shared `GAUGE_BAND_BLURB` in `EndgameMetricsSection.tsx:41-47`
  — the gauge can still be read as a weak skill proxy.
- LLM insight prompts that may reference Recovery — audit separately if
  they over-attribute agency.
