---
phase: 76
fixed_at: 2026-04-28
review_path: .planning/phases/76-frontend-score-coloring-confidence-badges-label-reframe/76-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 76: Code Review Fix Report

**Fixed at:** 2026-04-28
**Source review:** .planning/phases/76-frontend-score-coloring-confidence-badges-label-reframe/76-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (MEDIUM × 2; no BLOCKER, no HIGH)
- Fixed: 2
- Skipped: 0

LOW (LO-01..LO-04) and INFO (IN-01..IN-05) findings are outside the critical_warning fix scope and were not addressed. They remain in REVIEW.md for the developer to triage.

## Fixed Issues

### MD-01: Confidence-line tooltip is mouse-only — breaks D-10 / D-25 mobile parity

**Files modified:** `frontend/src/components/insights/OpeningFindingCard.tsx`
**Commit:** 4128892
**Applied fix:** Replaced the `Tooltip` wrap around the `<p>Confidence: …</p>` line with an `InfoPopover` rendered inline next to the level word. Matches the section-title pattern in `OpeningInsightsBlock.tsx`. Adds `flex items-center gap-1` to the `<p>` so the help icon aligns with the text. Imported `InfoPopover` from `@/components/ui/info-popover`. Updated the comment to explain the mobile-parity / keyboard-accessibility rationale. The visible "Confidence: <level>" text and existing `data-testid` are preserved, so all 19 OpeningFindingCard tests pass without modification. The new help icon gets `data-testid={...}-confidence-info` for future tap-target tests.

### MD-02: `compute_confidence_bucket(... n=0)` raises ZeroDivisionError

**Files modified:** `app/services/score_confidence.py`
**Commit:** dad5475
**Applied fix:** Added an `if n <= 0: return "low", 1.0` short-circuit at the top of `compute_confidence_bucket` (immediately before the `score = (w + 0.5*d) / n` line that previously could divide by zero). Comment in-place explains the inconsistent guard at `openings_service.py:447-448` and why "low / p=1.0" is the conservative answer. Chose the helper-side guard over removing the upstream `if gc > 0 else 0.5` because it defends every call site uniformly, including `opening_insights_service._classify_row` which has no caller guard at all. Did not refactor the duplicated score derivation (IN-01 — out of fix scope). All 14 score_confidence + confidence-related backend tests pass; ty check clean.

---

_Fixed: 2026-04-28_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
