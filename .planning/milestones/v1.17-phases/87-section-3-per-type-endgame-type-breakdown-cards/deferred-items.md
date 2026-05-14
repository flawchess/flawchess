# Phase 87 — Deferred Items

Out-of-scope discoveries logged during Plan 03 execution. Not fixed in
Phase 87 per the executor scope boundary (only auto-fix issues DIRECTLY
caused by the current task's changes).

## 1. Pre-existing failing test: `MetricStatTooltip.test.tsx > renders bold name followed by the explanation prose`

- **File:** `frontend/src/components/popovers/__tests__/MetricStatTooltip.test.tsx:305`
- **Status:** Failing on the Phase 87 base (commit `2feb441e`), unrelated to
  any Plan 03 changes. Verified by running the test with HEAD reset to the
  base before any Plan 03 commits.
- **Root cause:** the test expects the rendered output to use `"Achievable
  Score. Custom explanation..."` (period separator) but the component renders
  `"Achievable Score: Custom explanation..."` (colon separator). Either the
  component was refactored to use `:` and the test wasn't updated, or vice
  versa.
- **Recommended fix (follow-up):** update the regex in the test to expect
  the colon: `/Achievable Score: Custom explanation here\./`. Single-line
  change, no behavior impact.
- **Why deferred:** outside the Plan 03 scope (per-type Endgame Type
  Breakdown cards). Pure tooling/test-fixture issue, not user-visible.
