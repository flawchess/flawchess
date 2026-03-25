# Phase 28: Engine Analysis Import - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 28-engine-analysis-import
**Areas discussed:** Data storage schema, Lichess eval extraction, Chess.com accuracy import, Backfill strategy

---

## Data Storage Schema

### Research: Platform API capabilities
Before discussing storage, fetched real API responses from both platforms:
- **Lichess**: PGN contains `[%eval 0.18]` and `[%eval #-7]` annotations (centipawns and mate-in-N)
- **Chess.com**: Game JSON has `"accuracies": {"white": 83.53, "black": 88.34}` at game level. PGN has `%clk` only — NO per-move evals available through public API.

**User's initial request:** Research if chess.com has per-move evals. Web search confirmed: chess.com public API does NOT provide per-move evaluation data.

### Storage approach

| Option | Description | Selected |
|--------|-------------|----------|
| Split across tables | Per-move eval on game_positions, game-level accuracy on games | ✓ |
| Everything on game_positions | Store both + denormalize accuracy onto every position row | |
| Everything on games | Aggregate lichess evals into game-level only | |
| Per-move eval only | Skip chess.com accuracy entirely | |
| Store both + derive accuracy | Same as split + compute accuracy for lichess games | |

**User's choice:** Split across tables — matches data granularity naturally.

---

## Lichess Eval Extraction

### Eval representation

| Option | Description | Selected |
|--------|-------------|----------|
| Centipawns integer | SmallInteger centipawns + separate SmallInteger mate-in-N column | ✓ |
| Pawns as float | Float in pawn units, sentinel value for mate | |
| Combined string | String like '+0.18' or '#-7' | |

**User's choice:** Centipawns integer — matches engine internal representation.

### API request strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Always request evals | Add `evals=true` to all lichess API calls | ✓ |
| Only for analyzed games | Check analysis flag first, then re-fetch with evals | |

**User's choice:** Always request evals — zero overhead for unanalyzed games.

---

## Chess.com Accuracy Import

### What to store

| Option | Description | Selected |
|--------|-------------|----------|
| Store user's accuracy only | One nullable Float column, pick based on user_color | |
| Store both sides' accuracy | Two nullable Float columns: white_accuracy, black_accuracy | ✓ |

**User's choice:** Store both sides — useful for opponent scouting.

---

## Backfill Strategy

### Backfill approach

| Option | Description | Selected |
|--------|-------------|----------|
| Re-import backfill | Re-fetch from APIs, UPDATE existing rows | |
| Accept NULL for old games | Only new imports get eval/accuracy data | Initially selected, then revised |
| User-triggered re-sync | UI button for targeted re-fetch | |

**User initially chose:** Accept NULL for old games, and deferred full re-import to future phase.

**User then revised:** "I prefer to have a script which refetches all games and reruns the import."

### Re-import script approach

| Option | Description | Selected |
|--------|-------------|----------|
| Delete + re-import | Script deletes all games + positions, re-imports from scratch | ✓ |
| Re-fetch + UPDATE | Re-fetch and UPDATE existing rows without deleting | |
| Re-fetch PGN only | Update PGN column and add eval/accuracy data only | |

**User's choice:** Delete + re-import — clean slate, reuses existing import logic.

### Trigger mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Admin script only | `uv run python scripts/reimport_games.py [--user-id N \| --all]` | ✓ |
| User-triggerable via UI | Re-import button on Import page | |

**User's choice:** Admin script only — run once after deploying Phase 28.

---

## Claude's Discretion

- How to extend hashes_for_game() or the per-ply loop for eval extraction
- Re-import script implementation details (batch size, progress, error handling)
- Test structure and coverage
- Whether to update stored PGN with eval-enriched version

## Deferred Ideas

- Full re-import via UI (user-triggerable) — future phase
- Human-like engine analysis (Stockfish + Maia) — v2+ milestone
- Derive unified accuracy metric for lichess games from per-move evals
