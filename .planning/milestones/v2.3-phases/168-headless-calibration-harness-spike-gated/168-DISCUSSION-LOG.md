# Phase 168: Headless Calibration Harness (spike-gated) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-11
**Phase:** 168-headless-calibration-harness-spike-gated
**Areas discussed:** Runtime & spike scope, Output & ELO estimate, Grid & games-per-cell, Game mechanics

---

The user was presented four gray areas via a multiSelect menu and responded
**"You decide"** — delegating all four decisions to Claude. Claude made the
calls grounded in the existing prior-art harness (`scripts/gem-elo-calibration.mjs`,
Phase 165) and the Phase 166 `selectBotMove` contract. Options considered below.

---

## Runtime & spike scope

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `onnxruntime-web` WASM (proven) | Same headless path Phase 165 already shipped; spike measures throughput only | ✓ |
| Target `onnxruntime-node` native | Faster inference, but unproven headless here; contradicts already-working WASM path | |

**User's choice:** You decide → reuse `onnxruntime-web@1.27.0` WASM (D-01/D-02); spike is throughput/go-no-go, native node is fallback-only (D-03).
**Notes:** The literal CAL-03 wording ("lock the `onnxruntime-node` version") predates Phase 165 proving Maia ONNX runs headless in Node via `onnxruntime-web`; flagged and overridden.

---

## Output & ELO estimate

| Option | Description | Selected |
|--------|-------------|----------|
| Raw results matrix only | W/D/L + score per (cell × anchor); defer all ELO fitting | |
| Raw matrix + advisory ELO estimate | Matrix as primary + anchor-logistic ELO inversion as secondary, with caveats | ✓ |

**User's choice:** You decide → both (D-04/D-05); gem-elo TSV conventions (D-06); user-results fitting stays deferred.
**Notes:** ELO number carried with SEED-091's "coarse estimate, not precise" caveat.

---

## Grid & games-per-cell

| Option | Description | Selected |
|--------|-------------|----------|
| Coarse, CLI-configurable defaults | ELO {1100,1500,1900} × blend {0,0.5,1.0}; anchors Maia rungs + low SF skill; ~20 games/matchup | ✓ |
| Fine grid up front | More rungs/games — higher signal, much higher cost, premature before spike | |

**User's choice:** You decide → coarse, expandable via CLI flags (D-07/D-08).
**Notes:** Low Stockfish skill levels only (bot is human-strength; high levels give no signal). Bot ELO rungs must be `MAIA_ELO_LADDER` members.

---

## Game mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Vary openings + adjudicate + fixed budget | Seeded diverse opening FENs, colors alternated; terminal + eval-adjudication + ply-cap; fixed per-move budget | ✓ |
| Single start FEN, play to natural end | Simpler, but `blend=1` argmax replays identical games and long games blow up cost | |

**User's choice:** You decide → opening variety mandatory (D-09); three cost cutoffs (D-10); fixed grid-constant per-move budget (D-11).
**Notes:** Harness has no clock — clock-derived budgets are Phase 169, explicitly out of scope here.

## Claude's Discretion

All four areas (user chose "You decide"). Additionally left to planner/researcher:
opening-book source & size, exact adjudication cp/sustain-ply/ply-cap constants,
the SF-skill→Elo mapping table, scaffolding refactor vs duplication, new file
paths, and the Node `policy`/`grade` provider wiring.

## Deferred Ideas

- User-results strength calibration / curve fitting — later milestone (SEED-091 #3).
- `onnxruntime-node` native runtime — only if the throughput spike fails.
