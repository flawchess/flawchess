# Phase 237 — Code Review Disposition

Source: `237-REVIEW.md` (standard depth, 28 source files; 0 critical, 4 warning, 3 info). One row per finding; `open` until fixed, skipped or accepted.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed (e6e27ad71, 358f21567) | restored stand-in grade: permanent "…" eval pill, Best chip can be lost |
| WR-02 | warning | fixed (24ba06770) | action bar mounted twice (duplicate testids, one hidden) |
| WR-03 | warning | fixed (996042af5) | game-footer Analyze bypasses `walkthrough.leave()` |
| WR-04 | warning | fixed (b36fe01ae) | tapping the shown node counts a line step and advances the tour |
| IN-01 | info | open | `VerdictCopy.clause` / `verdictClause` dead in production |
| IN-02 | info | open | stale `TrainLineStepper` comments in `useAnalysisBoard.ts` |
| IN-03 | info | open | restored `rootFocus` not checked against current chips |

*Disposition: open · fixed · skipped · accepted*
