---
phase: 243
review: 243-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Card reports `below_floor` (\"0 of 30\") when every TC is `ranked` but none has a peer band"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Existing users get no opening rows after deploy, and no in-app path recomputes them; seed-before-backfill ordering is silent"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "A failed background refetch replaces already-loaded card data with a LoadError"
  - id: IN-01
    severity: info
    disposition: open
    title: "Frontend eval cut is a hand-mirrored duplicate, and its comment names a constant that does not exist"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stale documentation and naming left behind"
  - id: IN-03
    severity: info
    disposition: open
    title: "`eval_mate = 0` is classified as \"even\""
open: 3
total: 6
recorded: 2026-10-31T18:10:54.992Z
---

# Phase 243: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 243-REVIEW-FIX.md |
| WR-02 | warning | fixed | 243-REVIEW-FIX.md |
| WR-03 | warning | fixed | 243-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
