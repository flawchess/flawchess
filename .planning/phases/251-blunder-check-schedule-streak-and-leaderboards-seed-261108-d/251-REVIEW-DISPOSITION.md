---
phase: 251
review: 251-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Cross-mode cooldown cools flaws that were composed but never shown"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Guest purge leaves blunder-check sessions and windows behind"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "A debounced settings save can complete a blunder-check session irreversibly mid-drag"
  - id: WR-04
    severity: warning
    disposition: deferred
    title: "Tapping Start within the debounce window silently drops the pending settings save"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Streak explainer popover still describes the puzzle-only rule"
  - id: IN-02
    severity: info
    disposition: deferred
    title: "Level options and default level are duplicated in three components"
  - id: IN-03
    severity: info
    disposition: deferred
    title: "Stale comment on the medal claim cap"
open: 0
total: 7
recorded: 2026-11-18T23:47:17.415Z
---

# Phase 251: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 9b454124b |
| WR-02 | warning | fixed | c6b438318 |
| WR-03 | warning | fixed | f188a23e2 |
| WR-04 | warning | deferred | follow-up: narrow 600 ms window; flush draft before Start (owner chose not to fix in phase 251) |
| IN-01 | info | fixed | 921e1c0ca |
| IN-02 | info | deferred | follow-up: level options duplication, refactor later |
| IN-03 | info | deferred | follow-up: stale comment on medal claim cap |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
