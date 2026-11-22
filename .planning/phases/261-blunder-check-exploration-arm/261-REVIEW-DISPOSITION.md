---
phase: 261
source: 261-REVIEW.md
updated: 2026-11-22
---

# Phase 261 review disposition

One row per finding. Default is `open`; nothing was fixed in this run (the review is advisory and the fixes are outside the executed plans).

| ID | Severity | Disposition | Note |
|----|----------|-------------|------|
| WR-01 | warning | accepted | Exploration pass runs before the main pass, so under thin supply a main slot can lose its only host game and redraw toward an easier shape. Accepted as is by the owner on 2026-11-22 (261-UAT.md test 4); no code change. |
| IN-01 | info | open | `caught_rate.py --since` binds a bare date as local midnight, not UTC. |
| IN-02 | info | open | `UNSCORED_BAND` is a dead constant. |
| IN-03 | info | open | The four-value type-line Literal is defined twice. |
| IN-04 | info | resolved | Neutral copy "a player at that level" has no antecedent. Moot: the neutral chip form and its copy were removed in the UAT change. |
| IN-05 | info | open | `_selection_record` returns None silently; a NULL arm would read as legacy with no Sentry signal. |
| IN-06 | info | open | `arm_probability` holds the arm share only, not the per-blunder inclusion probability. |
| IN-07 | info | open | `type_swing >= 0` relies on the floors being 0; `max(0, round(...))` would make it robust. |
