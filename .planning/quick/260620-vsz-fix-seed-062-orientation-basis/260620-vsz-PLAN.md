---
quick_id: 260620-vsz
slug: fix-seed-062-orientation-basis
description: "Fix SEED-062 — tactic-comparison family narrowing inherits orientation=allowed"
status: complete
---

# Quick Task 260620-vsz: tactic-comparison orientation basis

## Problem

`get_tactic_comparison` threads `tactic_families` into the gate
(`count_filtered_and_analyzed`) and both per-orientation `fetch_tactic_comparison`
calls. But the base game-set narrowing flows into `_filtered_games_base` →
`apply_game_filters` with its **default** `orientation="allowed"`. So when a user
narrows to e.g. `["fork"]`, the comparison-grid population is filtered on the
**allowed** column only, while the grid renders **both** missed and allowed bullets.
A game whose only fork is missed-only is excluded entirely, biasing the Missed
bullets and the `analyzed_n` denominator.

## Fix

Thread `orientation="either"` into the tactic_families narrowing for this endpoint:

1. `_filtered_games_base`: add `tactic_orientation: TacticOrientation = "allowed"` →
   `apply_game_filters(orientation=...)`.
2. `count_filtered_and_analyzed`: add `tactic_filter_orientation = "allowed"` → base.
3. `fetch_tactic_comparison`: add `tactic_filter_orientation = "allowed"` → base
   (distinct from the existing `orientation`, which drives the COUNT columns).
4. `get_tactic_comparison`: add `tactic_filter_orientation="either"` to `_filter_kwargs`
   (flows to the gate and both fetches).

## must_haves

- truths: the comparison gate's analyzed_n and both bullet populations share the
  "either" basis when tactic_families is set.
- artifacts: tactic_orientation/tactic_filter_orientation params; service passes "either"; regression test.
- key_links: `app/services/library_service.py`, `app/repositories/library_repository.py`.
