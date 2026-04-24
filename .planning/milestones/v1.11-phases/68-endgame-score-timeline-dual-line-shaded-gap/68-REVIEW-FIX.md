---
phase: 68-endgame-score-timeline-dual-line-shaded-gap
fixed_at: 2026-04-24
review_path: .planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 2
skipped: 1
status: partial
---

# Phase 68: Code Review Fix Report

**Fixed at:** 2026-04-24
**Source review:** `.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical + Warning; Info excluded)
- Fixed: 2
- Skipped: 1 (already mitigated)

## Fixed Issues

### WR-02: `_run_agent` latency timer starts before `agent.run()`

**Files modified:** `app/services/insights_llm.py`
**Commit:** `bd0502f`
**Applied fix:** Moved `t0 = time.monotonic()` from before the `try:` block to be the first statement inside it. `get_insights_agent()` remains outside the try (it only reads a module-level `lru_cache` entry and doesn't need timing). Latency now measures only the `await agent.run()` call as the docstring claims. Added an inline comment referencing WR-02 explaining the placement. Verified with `uv run ruff check`, `uv run ty check`, and the insights test suites (`tests/services/test_insights_llm.py`, `tests/test_insights_llm_thinking.py`, `tests/test_insights_router.py`; 69 passed).

### WR-03: `EndgameInsightsBlock` has dead `staleMinutes` state — always null

**Files modified:** `frontend/src/components/insights/EndgameInsightsBlock.tsx`
**Commit:** `a0a64b3`
**Applied fix:** Deleted the dead `const staleMinutes: number | null = null;` declaration, removed `staleMinutes` from the `RenderedState` prop signature and call-site, and collapsed the two-branch `staleCopy` ternary to the single generic string. Added a comment referencing WR-03 explaining the rationale. Verified with `npm run lint --prefix frontend` (0 errors) and `npm run build --prefix frontend` (built in 4.73s). Confirmed no remaining `staleMinutes` references in `frontend/src/`.

## Skipped Issues

### WR-01: Rate-limit check is vulnerable to concurrent request TOCTOU

**File:** `app/services/insights_llm.py:1800-1813`
**Reason:** already-mitigated — no code change needed.
**Original issue:** Two concurrent requests from the same user can both pass the `count_recent_successful_misses < INSIGHTS_MISSES_PER_HOUR` gate, doubling LLM spend during a concurrent burst (double-click, mid-flight retry, second tab).

**Investigation:** The review's lowest-cost fix was to "add a frontend mutex so the button is disabled while `mutation.isPending`". Inspected `EndgameInsightsBlock.tsx`:
- `HeroState` (line 150 pre-fix, still present): `const disabled = isPending || blockedReason !== null;` disables the first-click "Generate Insights" button while the mutation is pending.
- `RenderedState` (line ~204 post-fix): `const disabled = isPending || blockedReason !== null;` with `aria-busy={isPending}` disables the "Regenerate" button too.

Both CTA paths already prevent same-tab double-click / double-submit as-is. No frontend change required.

**Residual risk (documented, not fixed in this PR):** The TOCTOU window is still reproducible across multiple browser tabs for the same user, or via a mid-flight retry that somehow bypasses the mutation's isPending guard. Consequence is at most ~2x spend during a concurrent burst (bounded by `INSIGHTS_MISSES_PER_HOUR = 3/hr`), not a security breach. A proper server-side fix (SELECT ... FOR UPDATE on a per-user lock row, or writing a placeholder `llm_logs` row inside a transaction and bumping it on success) is disproportionate for the current blast radius and intentionally deferred. Revisit if abuse patterns or cost observability show this matters.

---

_Fixed: 2026-04-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
