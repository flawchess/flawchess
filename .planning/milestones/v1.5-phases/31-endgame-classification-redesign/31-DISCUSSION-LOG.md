# Phase 31: Endgame Classification Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 31-endgame-classification-redesign
**Areas discussed:** Endgame analytics impact, Classifier changes

---

## Endgame Analytics Impact

### How should the Endgames tab use per-position classification?

| Option | Description | Selected |
|--------|-------------|----------|
| Simpler backend only | Keep same UI, simplify SQL queries | ✓ |
| Position-level drill-down | New capability: explore endgame positions on board | |
| Both: simplify now, drill-down later | Phase 31 simplifies, future phase adds drill-down | |

**User's choice:** Simpler backend only
**Notes:** No frontend changes needed.

### Should a game count in multiple endgame categories?

| Option | Description | Selected |
|--------|-------------|----------|
| One category per game | Each game counts once (first endgame class) | |
| Multiple categories per game | Game counts in every endgame type it passes through | ✓ |
| User chooses aggregation | Toggle between first-class and all-classes | |

**User's choice:** Multiple categories per game
**Notes:** User identified that "first endgame class" is biased toward Mixed (since games often enter endgame with multiple piece families still present). Counting all classes with a ply threshold better captures endgame skill.

### Minimum ply threshold for counting a game in an endgame class

| Option | Description | Selected |
|--------|-------------|----------|
| 5 plies | Low-moderate threshold | |
| 6 plies (3 full moves) | Moderate threshold, filters tactical transitions | ✓ |
| 10 plies (5 full moves) | Very strict, may miss short legitimate sequences | |

**User's choice:** 6 plies (3 full moves)
**Notes:** User wanted a higher threshold than initially proposed. Short transitions are tactics-based (e.g., piece sacrifices for checkmate), not endgame skill, and should be filtered out.

### Transition point for conversion/recovery

| Option | Description | Selected |
|--------|-------------|----------|
| First position of class span | Material imbalance at entry to each endgame class | ✓ |
| You decide | Claude picks best approach | |

**User's choice:** First position of class span
**Notes:** Same semantics as today's transition point, applied per-class.

---

## Classifier Changes

### Should position_classifier.py compute game_phase and endgame_class?

| Option | Description | Selected |
|--------|-------------|----------|
| Add to classifier | classify_position() returns game_phase + endgame_class | |
| Separate derivation function | New function for phase/class, keeps classifier focused on raw metrics | ✓ |
| You decide | Claude picks based on architecture | |

**User's choice:** Separate derivation function
**Notes:** User explicitly does NOT want game_phase stored in DB — it's easily derived from piece_count <= 6. Only endgame_class should be stored, derived from material_signature.

### Should endgame_class be stored or derived at query time?

| Option | Description | Selected |
|--------|-------------|----------|
| Store endgame_class column | Add to game_positions, populated where piece_count <= 6 | ✓ |
| Derive in Python at query time | Fetch all endgame positions, classify each | |
| SQL CASE expression | Derive in SQL using CASE/LIKE on material_signature | |

**User's choice:** Store endgame_class column

### Backfill strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Alembic data migration | Single migration adds column + populates from existing data | ✓ |
| Standalone backfill script | Separate script with batching/resumability | |

**User's choice:** Alembic data migration
**Notes:** No PGN replay needed — backfill derives endgame_class from existing material_signature + piece_count columns.

---

## Claude's Discretion

- SQL query structure for per-position grouping with ply count threshold
- Whether to move classify_endgame_class() to position_classifier.py
- Batching strategy for Alembic data migration
- Index strategy for endgame_class column

## Deferred Ideas

- Position-level endgame drill-down (explore endgame positions on board)
- MATFLT-01 material signature drill-down (finer breakdown by specific material config)
