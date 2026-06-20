---
id: SEED-062
status: dormant
planted: 2026-06-20
planted_during: v1.28 Tactic Tagging (Phase 129)
trigger_when: when next touching get_tactic_comparison, fetch_tactic_comparison, or the tactic-comparison grid's family-narrowing path
scope: small
---

# SEED-062: tactic-comparison family narrowing inherits orientation="allowed", mismatching the dual-orientation grid

## Why This Matters

`get_tactic_comparison` threads `tactic_families` into both the gate
(`count_filtered_and_analyzed`) and the two per-orientation `fetch_tactic_comparison` calls.
Inside `fetch_tactic_comparison`, `tactic_families` flows into `_filtered_games_base` →
`apply_game_filters` with its **default** `orientation="allowed"`. So when a user narrows to e.g.
`tactic_families=["fork"]`, the comparison-grid *game set* is filtered on the **allowed** column
only, while the per-game family counts (and the bullets the grid renders) are computed for **both**
missed and allowed orientations (D-09 shows both). The gate's `analyzed_n` denominator and the
bullet population can then rest on different game populations — at worst the "X of 20" gate count
and the bullet rates disagree. This endpoint has no orientation query param, so the inherited
single-orientation narrowing is easy to miss.

## When to Surface

**Trigger:** when next touching `get_tactic_comparison` / `fetch_tactic_comparison` or the
tactic-comparison grid family-filter path. Confirm the intended semantics before changing — this is
a correctness question, not a clear-cut bug.

## Scope Estimate

**Small** — if the grid should narrow on "either" (to match its dual-orientation display), thread
`orientation="either"` explicitly into the `tactic_families` path for this endpoint rather than
inheriting the `"allowed"` default. Add a test asserting the gate `analyzed_n` and the bullet
population share an orientation basis when `tactic_families` is set.

## Breadcrumbs

- `app/services/library_service.py` (~lines 1419-1434) — `get_tactic_comparison`; `_filter_kwargs`
  carries `tactic_families` into the gate and both fetches.
- `app/repositories/library_repository.py` — `fetch_tactic_comparison` → `_filtered_games_base` →
  `apply_game_filters(..., orientation="allowed")` default is the inherited basis.
- `apply_game_filters` supports `orientation="either"` — likely the intended basis for the
  dual-orientation grid.
- Source: Phase 129 code review **WR-03** — see
  `.planning/phases/129-tactic-filter-ui/129-REVIEW.md`.

## Notes

Subtle because the endpoint exposes no orientation param. Verify whether the mismatch is observable
with real data before investing — may be benign if family membership rarely differs by orientation,
but the gate-vs-bullet population split is the thing to assert in a test.
