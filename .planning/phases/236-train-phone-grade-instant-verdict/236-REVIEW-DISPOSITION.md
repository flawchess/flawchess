---
phase: 236
review: 236-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "A grading-engine Worker error after the verdict hides the verdict bubble and its Next button (violates D-15)"
  - id: WR-02
    severity: warning
    disposition: deferred
    title: "Analyze or Next pressed before the background grade lands silently drops the record, biasing the audit toward fast devices (and Analyze also loses the restorable reveal)"
  - id: IN-01
    severity: info
    disposition: open
    title: "`TrainPuzzle` / `ServerGradedMove` docstrings overstate \"exposes nothing beyond the key already sent\""
  - id: IN-02
    severity: info
    disposition: open
    title: "D-11 `serverGradedUcis` exclusion in `shouldRecheck` is unreachable from the only caller"
  - id: IN-03
    severity: info
    disposition: open
    title: "Review route accepts a `phone_grade` for any solved row with no consistency check against the D-05/D-06 invariants"
  - id: IN-04
    severity: info
    disposition: open
    title: "Defensive-fallback `GradeResult` replaces the pending state on the instant path, making the best-move arrow vanish after the verdict"
open: 4
total: 6
recorded: 2026-10-08T20:11:54.196Z
---

# Phase 236: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 236-REVIEW-FIX.md |
| WR-02 | warning | deferred | Analyze path fixed in 86a545512; Next path needs a held puzzle transition or a second grading Worker (owner decision), gap documented in 1f99cfedc |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
