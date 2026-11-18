---
phase: 251
review: 251-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Cross-mode cooldown cools flaws that were composed but never shown"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Guest purge leaves blunder-check sessions and windows behind"
  - id: WR-03
    severity: warning
    disposition: open
    title: "A debounced settings save can complete a blunder-check session irreversibly mid-drag"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Tapping Start within the debounce window silently drops the pending settings save"
  - id: IN-01
    severity: info
    disposition: open
    title: "Streak explainer popover still describes the puzzle-only rule"
  - id: IN-02
    severity: info
    disposition: open
    title: "Level options and default level are duplicated in three components"
  - id: IN-03
    severity: info
    disposition: open
    title: "Stale comment on the medal claim cap"
open: 7
total: 7
recorded: 2026-11-18T23:47:17.415Z
---

# Phase 251: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
