---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
fixed_at: 2026-07-10T13:50:30Z
review_path: .planning/phases/162-grading-run-authoritative-eval-reconciliation-precedence-fli/162-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 162: Code Review Fix Report

**Fixed at:** 2026-07-10T13:50:30Z
**Source review:** .planning/phases/162-grading-run-authoritative-eval-reconciliation-precedence-fli/162-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (fix_scope: critical_warning — 0 Critical, 2 Warning; 4 Info findings out of scope)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Verdict/arrow/eval-bar can transiently present a non-Stockfish-best move as "Stockfish's pick" when Maia is off

**Files modified:** `frontend/src/pages/Analysis.tsx`
**Commit:** 54917b36
**Applied fix:** Added a guard in the `reconciledBestUci` memo, applied exactly as suggested by the review: after building `candidateUcis` from `grading.gradeMap`'s keyspace, compute `freeRunBestUci` (the committed free run's `engine.pvLines[0]` root, gated on `freeRunCommitted`) and return `null` when it is not among the graded candidates. This treats the argmax as unresolved during the Maia-off/FC-on window where grading has landed only for the FC-only candidate set, so all consumers (verdict `stockfishLine`, green SF board arrow, eval bar via `reconciledBestEval`, `qualityBySan` Best designation) fall back to raw `engine.pvLines[0]` — the existing first-paint path, which gets the Stockfish move identity right. Depth parity is preserved (the free-run eval is never mixed into the argmax). Added `freeRunCommitted` and `engine.pvLines` to the memo's dependency array.

### WR-02: Maia chart emphasis stroke still keyed to the raw free-run `bestSan`, contradicting the reconciled Best on the same chart

**Files modified:** `frontend/src/pages/Analysis.tsx`
**Commit:** 4495cc5a
**Applied fix:** Hoisted the reconciled SAN (previously computed inline inside the `qualityBySan` memo as `designatedBestSan`) into a dedicated `reconciledBestSan` memo (`bestSanFromPv(position, reconciledBestUci)`), reused it inside `qualityBySan` (deps updated from `reconciledBestUci` to `reconciledBestSan`), and passed `bestSan={reconciledBestSan ?? bestSan}` to BOTH `MaiaHumanPanel` call sites — the mobile Maia tab and the desktop human column (CLAUDE.md mobile/desktop parity). `MaiaHumanPanel` forwards this prop directly to `MovesByRatingChart`'s emphasis-stroke check, so the thick stroke now follows the same reconciled Best the quality color/label/verdict designate. The raw `bestSan` still feeds `selectCandidatesByMass` (via `shownSans`), so the free-run pick remains plotted, per the review's note.

## Verification

- `npx tsc -b` — clean after each fix.
- `npx vitest run src/pages/__tests__/Analysis.test.tsx src/lib/engineEvalLookup.test.ts src/hooks/__tests__/useGameOverlay.test.ts` — 43/43 passed after each fix.
- `npm run lint` — clean.
- Full frontend suite (`npm test -- --run`) before the final commit — 137 files, 1702/1702 passed.

Pre-flight fixture check: all existing reconciled-argmax test fixtures include the free run's best in `gradeMap` (or have no grades at all, where the argmax already resolved to null), so the WR-01 guard changes no pinned behavior.

Note: both fixes touch display-precedence logic (WR-01 is a timing-window condition). Syntax/type/test verification passed, but the transient Maia-off/FC-on window itself is not exercisable in jsdom — worth a quick UAT glance alongside the IN-03 flicker check the reviewer already suggested.

---

_Fixed: 2026-07-10T13:50:30Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
