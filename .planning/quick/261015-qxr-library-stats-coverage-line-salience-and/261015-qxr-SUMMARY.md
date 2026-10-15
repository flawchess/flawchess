---
quick_id: 261015-qxr
status: complete
commit: b2896d32e
---

# Summary: Library Stats coverage line salience

- `CoverageBasisLine` (LibraryStatsSections.tsx): below `COVERAGE_UPDATING_THRESHOLD` (0.98, per selected TC)
  the line gets the amber analysis-pending tint and a hint: "Stats below update as analysis continues."
  (authenticated, pulsing Cpu) or "Only analyzed games are counted." (guest, no pulse). At/above threshold
  it is a plain muted line; complete TCs read "All N <tc> games in the current filters are analyzed."
- Guest sign-up CTA rule (LOW_COVERAGE_THRESHOLD 0.8) unchanged.
- Amber tint centralized in theme.ts (`ANALYSIS_PENDING_TINT_CLASS`, `ANALYSIS_PENDING_ICON_CLASS`) and
  reused by EvalCoverageHeader + EvalCpuPlaceholder. Deviation: switched the tones to the Alert warning
  variant (amber-500/10 fill, amber-400 icon). Browser check showed the old bg-amber-50/60 put near-white
  text on a pale fill in the app's permanent dark theme (pre-existing contrast bug in the Quick Scan banner).
- No tactic coverage line (tactic tagging is near-instant).

Verification: vitest (library/stats/EvalCoverageHeader, 294 tests), lint, build, knip green; mutation check
(removing the guest no-pulse guard fails the guest test); live dev-build check with a mocked 46% coverage
response (screenshot: temp/library-stats-coverage/updating-state.jpg).
