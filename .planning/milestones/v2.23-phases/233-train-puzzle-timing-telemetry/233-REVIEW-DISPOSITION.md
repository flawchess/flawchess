---
phase: 233
review: 233-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`client` classifies every iPad as \"desktop\" (irreversible mislabelled data)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Next-path review flush is a plain XHR and its \"flushed\" guard is set before success, so a lost Next flush is never retried and corrupts the D-07 derivation"
  - id: IN-01
    severity: info
    disposition: open
    title: "`v: Literal[1]` on both schemas is not covered by the parity test"
  - id: IN-02
    severity: info
    disposition: open
    title: "Dropped solve telemetry is completely unobservable"
  - id: IN-03
    severity: info
    disposition: open
    title: "`_merged_telemetry` relies on callers to keep None out of the patch"
  - id: IN-04
    severity: info
    disposition: open
    title: "First-puzzle `guess_ms` includes the intro stepper with no flag on the row"
open: 4
total: 6
recorded: 2026-10-05T18:41:10.175Z
---

# Phase 233: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 54bf184a0 (telemetry-only iPadOS check; install prompt unchanged) |
| WR-02 | warning | fixed | c741b6334 (Next flush over keepalive fetch; recordReview removed) |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
