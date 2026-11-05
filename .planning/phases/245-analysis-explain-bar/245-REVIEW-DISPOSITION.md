---
phase: 245
review: 245-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "An open adjacent-ply line makes a neighbouring flaw's Explain unreachable"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Mapping 404 to null removes the chip error signal and leaves `pendingFlaw` stuck, which hides the Explain bar on every other ply"
  - id: IN-01
    severity: info
    disposition: open
    title: "A cached 404 (`null`) hides Explain for 5 minutes even after `game_flaws` rows appear"
  - id: IN-02
    severity: info
    disposition: open
    title: "The mobile ExplainBar is mounted unconditionally while the hook's landing prefetch also fires during Jump animation"
open: 4
total: 4
recorded: 2026-11-05T10:00:42.073Z
---

# Phase 245: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
