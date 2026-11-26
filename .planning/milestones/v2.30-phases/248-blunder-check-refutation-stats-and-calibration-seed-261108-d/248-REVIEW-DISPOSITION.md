---
phase: 248
review: 248-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`--from-cache` with a mismatching `--db` resolves cached game ids against the wrong database"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Backfill treats `StaleDataError` as a generic write failure (Sentry noise, counts toward the abort threshold)"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`MAX_BLUNDER_POSITION` is coupled to `WINDOW_LENGTHS` only by a comment; a mismatch silently zeroes the fit"
  - id: IN-01
    severity: info
    disposition: open
    title: "Spot-check overwrite guard fires for a file that will not be written"
  - id: IN-02
    severity: info
    disposition: open
    title: "Refutation-mode backfill reports flaws counters that are always zero"
  - id: IN-03
    severity: info
    disposition: open
    title: "The \"user-side blunder\" predicate is implemented three separate ways"
  - id: IN-04
    severity: info
    disposition: open
    title: "`sample.py` imports a constant from a script module"
  - id: IN-05
    severity: info
    disposition: open
    title: "Good-move oddness sample includes forced single-legal-move plies"
  - id: IN-06
    severity: info
    disposition: open
    title: "Minor report hygiene (hard-coded numbers in prose, unvalidated `--date`)"
open: 9
total: 9
recorded: 2026-11-10T14:20:00Z
---

# Phase 248: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
