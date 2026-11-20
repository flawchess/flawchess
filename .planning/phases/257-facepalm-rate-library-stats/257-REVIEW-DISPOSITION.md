---
phase: 257
review: 257-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "The \"missed win\" type and its copy claim material was won for rows with no such evidence"
  - id: IN-01
    severity: info
    disposition: open
    title: "Doc comments left orphaned by insertion (three sites)"
  - id: IN-02
    severity: info
    disposition: open
    title: "The share chart's percent axis can show uneven, rounded tick labels"
  - id: IN-03
    severity: info
    disposition: open
    title: "The share card duplicates the empty state when the timeline is empty"
  - id: IN-04
    severity: info
    disposition: open
    title: "`FacepalmRow` and `ContextTagRow` are near-duplicates, and the chart ticks use a raw 12px font"
  - id: IN-05
    severity: info
    disposition: open
    title: "A shipped comment records an unfinished prod probe"
open: 6
total: 6
recorded: 2026-11-20T13:35:55.123Z
---

# Phase 257: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
