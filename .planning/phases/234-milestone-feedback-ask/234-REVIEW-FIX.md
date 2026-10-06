---
phase: 234
fixed_at: 2026-10-06T00:00:00Z
review_path: /home/aimfeld/Projects/Python/flawchess/.planning/phases/234-milestone-feedback-ask/234-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 234: Code Review Fix Report

**Fixed at:** 2026-10-06
**Source review:** /home/aimfeld/Projects/Python/flawchess/.planning/phases/234-milestone-feedback-ask/234-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (fix_scope critical_warning; the 5 Info findings are out of scope)
- Fixed: 2
- Skipped: 0

**Verification environment:** all gates ran in the main checkout on branch
`gsd/phase-234-milestone-feedback-ask` (no worktree; the caller asked for the current
branch, and the frontend gates need node_modules). Ran ruff format/check, ty,
check_function_size (depth <= 4) and the five backend test modules (81 passed, up from 75).
No frontend files changed, so no frontend gates were run.

## Fixed Issues

### WR-01: `apply_feedback_ask_action` documents "always succeeds" but a corrupt stored state returns 500 on the write path

**Files modified:** `app/services/feedback_ask_service.py`, `tests/test_feedback_ask.py`
**Commit:** d4357b380
**Applied fix:** `_transition` and the no-op `get_state` re-read now share one `try/except ValidationError`. On failure the handler calls `_capture_corrupt_state` (Sentry capture with `feedback_ask` context), runs `await session.rollback()` so the already-executed UPDATE is not committed, and returns inactive. The reviewer's note about the in-flight UPDATE was applied (rollback before returning). A bug-fix comment sits at the site.
**Test:** `test_feedback_ask_corrupt_state_fails_closed_not_500`, parametrized over view, snooze and done. It stores `{"feedback_v1": {"bogus_key": 1}}`, expects 200 `{"active": false}` and an unchanged stored state. Proven by reverting the service change: all 3 cases fail with `ValidationError`.
**Status:** fixed (error-handling change, behaviour covered by tests).

### WR-02: snooze and done are not gated on eligibility, so an ineligible user or one who already gave feedback can write ask state

**Files modified:** `app/services/feedback_ask_service.py`, `tests/test_feedback_ask.py`
**Commit:** cb8cb200e
**Applied fix:** The gate is now `if action != "done" and not _base_eligible(...)`, so `view` and `snooze` need the eligibility rule (>= 5 active days, no feedback); `done` stays unconditional.
**Locked-decision check:** 234-CONTEXT.md D-01..D-05 say nothing about gating snooze/done. SEED-191 #1 defines eligibility, #5 says "Sure!" marks done forever (even without submitting), #6 says "Maybe later" snoozes. Nothing intends an ungated snooze, and `done` is kept ungated, so no locked decision is contradicted.
**Tests:** `test_feedback_ask_ineligible_snooze_writes_nothing` and `test_feedback_ask_snooze_after_feedback_writes_nothing` (both fail without the fix, proven by revert), plus `test_feedback_ask_done_stays_ungated` to pin the intentional asymmetry.
**Status:** fixed: requires human verification (logic/eligibility-rule change; the owner should confirm that gating snooze, but not done, matches intent).

## Skipped Issues

None. Info findings IN-01 to IN-05 were out of scope for this run (fix_scope: critical_warning).

---

_Fixed: 2026-10-06_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
