---
phase: 235
review: 235-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "A re-check that outlives its timeout keeps driving the engine and can starve the reveal search"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`useTrainGradingEngine` hook body has grown to roughly 790 lines"
  - id: IN-01
    severity: info
    disposition: open
    title: "Positional booleans in `ResolvedGrade(...)` construction"
  - id: IN-02
    severity: info
    disposition: open
    title: "Mangled header comment in `trainBubbleState.ts`"
  - id: IN-03
    severity: info
    disposition: open
    title: "Server trusts client-asserted ES numbers for the D-14 guess credit"
  - id: IN-04
    severity: info
    disposition: open
    title: "`_classify_sr_solve` now always reads `game_positions.best_move`"
open: 4
total: 6
recorded: 2026-10-07T20:06:56.369Z
---

# Phase 235: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 235-REVIEW-FIX.md |
| WR-02 | warning | fixed | 235-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
