---
phase: 246
review: 246-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: deferred
    title: "Archive query has no supporting index on `drill_solves`; the flagged \"no migration\" assumption was never verified"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "No test pins the upper boundary of the archive `offset` bound"
  - id: WR-03
    severity: warning
    disposition: accepted
    title: "The new Parked sentence misstates the park rule for puzzles that were ever solved"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Rank-line row is reserved while loading and then removed when there is no rank, so the card jumps"
  - id: IN-01
    severity: info
    disposition: open
    title: "Formatting glitch in `TrainPuzzleCard`"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stale docstring and a stray double blank line in `TrainStartScreen`"
  - id: IN-04
    severity: info
    disposition: open
    title: "The Archive explainer sentence is not tied to the toggle for assistive tech"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "Unverified: wrapped `ToggleGroupItem`s may lose the group's joined-border styling"
open: 3
total: 8
recorded: 2026-11-07T07:54:12.954Z
---

# Phase 246: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | deferred | Prod checks P1/P2 ran during execution: 19,493 rows and 3.6 ms with the seq scan, under the 300k/50 ms migration rule. No migration; revisit if the table nears 300k. Evidence in 246-RESEARCH.md. |
| WR-02 | warning | fixed | 246-REVIEW-FIX.md |
| WR-03 | warning | accepted | Owner 2026-11-08: "Missed 3 or more times" also covers a 4th miss; copy is good enough. |
| WR-04 | warning | fixed | 246-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-04 | info | open | - |
| IN-03 | info | fixed | The defect was reported by the owner in UAT. The items are now direct children of a full-width group, with a sentence below instead of help icons. Later replaced by compact pills (D-04); owner approved 2026-11-07 in 246-UAT.md. (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
