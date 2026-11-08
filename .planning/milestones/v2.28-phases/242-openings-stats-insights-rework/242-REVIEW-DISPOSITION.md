---
phase: 242
review: 242-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Bookmark-twin drop runs after the deeper-line dedupe, so a deeper twin of a shallower bookmark survives"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Eval verdict applies the 20-game floor to `games`, not to the eval sample size"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "A finding classified as a weakness at exactly 45% score renders as \"typical\" because of float arithmetic"
  - id: IN-01
    severity: info
    disposition: open
    title: "\"Either colour\" requests test eval against the White baseline"
  - id: IN-02
    severity: info
    disposition: open
    title: "Popover baseline copy duplicates the constants"
  - id: IN-03
    severity: info
    disposition: open
    title: "Stale docstrings and comments left over from the rework"
  - id: IN-04
    severity: info
    disposition: open
    title: "Expansion state and the \"Played before\" toggle survive a colour switch"
  - id: IN-05
    severity: info
    disposition: open
    title: "Suggestions pool can include \"past\" openings"
  - id: IN-06
    severity: info
    disposition: open
    title: "Minor UI/theme nits"
  - id: IN-07
    severity: info
    disposition: open
    title: "The `NowUtc` dependency alias is copy-pasted into four routers"
open: 7
total: 10
recorded: 2026-10-17T18:56:58.137Z
---

# Phase 242: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 242-REVIEW-FIX.md |
| WR-02 | warning | fixed | 242-REVIEW-FIX.md |
| WR-03 | warning | fixed | 242-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
