# Phase 26: Position Classifier & Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 26-position-classifier-schema
**Areas discussed:** Phase boundary heuristic, Endgame class rules, Material signature format, Imbalance calculation, Tactical indicators

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Phase boundary heuristic | How to classify opening/middlegame/endgame — material-weight thresholds, piece counts, or hybrid approach? | |
| Endgame class rules | How the 6 categories are defined and their mutual exclusivity rules | |
| Material signature format | Exact string encoding for canonical signatures | |
| Imbalance calculation | Piece values and sign convention for centipawn imbalance | |

**User's choice:** "I'll leave these decisions to you, go for established best practices and important references"
**Notes:** User delegated all four areas to Claude's discretion. No specific preferences expressed.

---

## Claude's Discretion

All four gray areas were deferred to Claude with guidance to follow established best practices:

1. **Phase boundary heuristic** — Material-weight scoring with thresholds at 50/25 (standard chess programming approach)
2. **Endgame class rules** — Six mutually exclusive categories with priority-based classification
3. **Material signature format** — Repeated piece letters in descending value order, underscore separator, stronger side first
4. **Imbalance calculation** — Standard centipawn values (P=100, N=300, B=300, R=500, Q=900), white minus black

## Tactical Indicators (follow-up discussion)

User raised whether bishop pair and similar indicators should be added to avoid a second backfill pass.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep imbalance pure | Standard centipawn values only, defer indicators to TACT-01 | |
| Bake bishop pair into imbalance | Add ~50cp Kaufman bonus to the imbalance number, no new columns | |
| Add indicator columns | 3 new boolean columns: has_bishop_pair_white/black, has_opposite_color_bishops | ✓ |

**User's choice:** Add 3 indicator columns
**Notes:** User pointed out that Phase 27 backfill already replays every position — computing extra booleans is free, but a second backfill later would duplicate the expensive PGN replay + DB write cycle on the constrained production server. Claude initially recommended deferring to TACT-01 but agreed the backfill argument was strong.

## Deferred Ideas

- **Passed pawn detection** — More complex to compute (pawn structure analysis), deferred to future TACT-01 phase
- **Open file detection** — Would require 8 boolean columns (one per file), deferred to TACT-01
- **Isolated pawn detection** — Moderate complexity, deferred to TACT-01
