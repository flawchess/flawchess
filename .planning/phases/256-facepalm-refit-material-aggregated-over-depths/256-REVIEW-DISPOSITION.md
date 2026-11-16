---
phase: 256
review: 256-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Loses material\" gate None is hair-trigger under the decaying mean (score discontinuity)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Shipped material input is contradicted by the only fresh data, at the shipped cut"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Owner-fixture test pins an observed regression and hard-codes refit output"
  - id: IN-01
    severity: info
    disposition: open
    title: "Test name no longer matches what it asserts"
  - id: IN-02
    severity: info
    disposition: open
    title: "Wrong comment and a vacuous `first_stable` branch in the fractional-mean gate test"
  - id: IN-03
    severity: info
    disposition: open
    title: "Pure-miss rows without `maia_best_prob` silently become unscored; the impact is not quantified"
  - id: IN-04
    severity: info
    disposition: open
    title: "Fit report mixes depth-3 bookkeeping with aggregate-input results"
  - id: IN-05
    severity: info
    disposition: open
    title: "`fit_facepalm.py` is a 2,569-line module with stale prose and inconsistent boundaries"
open: 8
total: 8
---
# Phase 256: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
