---
quick_id: 260620-vsu
slug: fix-seed-061-confidence-gate
description: "Fix SEED-061 — Games-tab tactic filter omits the chip-confidence gate"
status: complete
---

# Quick Task 260620-vsu: Games-tab tactic filter confidence gate

## Problem

The Games-tab tactic-family EXISTS in `apply_game_filters` (query_utils.py) omitted
the `conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN` (70) gate that `build_flaw_filter_clauses`
(Flaws list) applies. A game whose only family-X tactic was below threshold could
match the filter, yet the card shows no chip for that tactic (chip display gates at
70). The two filter surfaces disagreed on "has a tactic in family X."

## Decision

User chose **Add the gate (align)** over keeping the documented asymmetry. The Phase
129 "Pitfall 3" asymmetry was incidental ("keep intentional OR fix deliberately"),
and the code review (WR-02) flagged it for explicit decision.

## Tasks

1. Add `& (conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN)` to each orientation branch in the
   Games-tab tactic EXISTS; import the constant from library_repository.
2. Reverse the unit test `test_no_confidence_gate_in_exists_site` →
   `test_confidence_gate_present_in_exists_site` (assert the gate IS in the SQL).
3. Add a behavioral regression test: a sub-threshold fork is excluded while a
   threshold fork matches.
4. Update two stale "no confidence gate" docstrings.

## must_haves

- truths: Games-tab tactic filter matches only tactics that would render a chip (conf >= 70).
- artifacts: confidence predicate on each EXISTS branch; reversed + new tests.
- key_links: `app/repositories/query_utils.py`, `tests/test_query_utils.py`, `tests/test_library_repository.py`.
