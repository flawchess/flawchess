---
phase: 260701-lw4
plan: 01
subsystem: infra
tags: [eval-queue, sqlalchemy, postgres, efraimidis-spirakis, backfill]

requires:
  - phase: SEED-072
    provides: routing of tier-4 flaw-blob backfill to the dedicated /flaw-blob-lease path
provides:
  - Two-stage Efraimidis-Spirakis weighted lottery replacing the tier-4 top-50 recency window in _claim_tier4_blob
  - 4 tunable TIER4_* ES constants (user/game half-life + floor), independent from tier-3
affects: [eval-queue, remote-eval-worker, blob-backfill]

tech-stack:
  added: []
  patterns:
    - "Two-stage ES weighted lottery (user pick -> game pick) reused for tier-4, mirroring tier-3's _claim_tier3_derived"

key-files:
  created: []
  modified:
    - app/services/eval_queue_service.py
    - tests/test_eval_queue_service.py

key-decisions:
  - "Tier-4 game-pick weight uses full_evals_completed_at recency only, no tc_multiplier (blob enrichment is not time-control sensitive, unlike tier-3's game pick)"
  - "New TIER4_* constants are seeded from tier-3's values but kept independently tunable, per plan"

requirements-completed: [260701-lw4]

duration: ~25min
completed: 2026-07-01
status: complete
---

# Phase 260701-lw4: Replace tier-4 blob-backfill top-50 recency window with two-stage ES lottery Summary

**Replaced `_claim_tier4_blob`'s hard top-50 recency-window CTE with a two-stage Efraimidis-Spirakis weighted lottery (user pick then game pick) mirroring tier-3, so the full analyzed-but-unblobbed backlog drains instead of only the freshly-analyzed trickle.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-01T13:51Z (approx)
- **Completed:** 2026-07-01T13:57Z
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments

- `_claim_tier4_blob` now runs two sequential ES-weighted picks in the same `AsyncSession` (no `asyncio.gather`): Stage 1 picks a non-guest user weighted by `last_activity` recency + a floor; Stage 2 picks that user's NULL-blob analyzed game weighted by `full_evals_completed_at` recency + a floor (no TC multiplier — blob enrichment isn't time-control sensitive).
- `TIER4_RECENCY_WINDOW` (the old hard top-50 cutoff, which gave game #51+ zero selection probability) is gone. Four new tunable constants replace it: `TIER4_USER_RECENCY_HALF_LIFE_DAYS`, `TIER4_USER_WEIGHT_FLOOR`, `TIER4_GAME_RECENCY_HALF_LIFE_DAYS`, `TIER4_GAME_WEIGHT_FLOOR`, seeded from the equivalent tier-3 values but independently tunable.
- The docstring and all comments in the tier-4 region were rewritten to describe the ES lottery and its anti-starvation rationale; the unrelated tier-2 (`TIER_AUTO_WINDOW`) historical comment at the top of the module was intentionally left untouched (different lane, not part of this change).
- Replaced the old `test_claim_tier4_blob_recency_favors_fresh_game` (which monkeypatched the now-removed `TIER4_RECENCY_WINDOW`) with `test_claim_tier4_blob_anti_starvation_and_recency_preference`, asserting both that an old, heavily-aged game is picked at least once over 40 draws (anti-starvation — the actual fix) and that a fresh game still wins a strict majority (recency preference retained).

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite `_claim_tier4_blob` as a two-stage ES lottery + swap constants + clean stale comments** - `6000f70a` (feat)
2. **Task 2: Replace the Phase 146 recency-window test with an anti-starvation + recency-preference test** - `9ac007ea` (test)

_Note: plan metadata commit (this SUMMARY, STATE.md) is created separately by the orchestrator._

## Files Created/Modified

- `app/services/eval_queue_service.py` - `_claim_tier4_blob` rewritten as a two-stage ES lottery; `TIER4_RECENCY_WINDOW` removed; 4 new `TIER4_*` constants added.
- `tests/test_eval_queue_service.py` - old window-favors-fresh test replaced with an anti-starvation + recency-preference test using two games under one shared test user.

## Decisions Made

- **Weight tuning for the new test:** monkeypatched `TIER4_GAME_WEIGHT_FLOOR` to `0.3` (vs. the prod default `0.01`) and aged the "old" test game 400 days (vs. the 30-day `TIER4_GAME_RECENCY_HALF_LIFE_DAYS`) so its recency term is negligible and its weight collapses to ~the floor. This yields `P(old) ≈ floor / (floor + (1 + floor)) ≈ 0.1875` — inside the plan's target 0.15-0.25 band — so "old game picked >= 1 time in 40 draws" is statistically near-certain (`P(miss) ≈ (1-0.1875)^40 ≈ 4.4e-4`) while the fresh game still wins a clear majority. This avoids the plan's flagged flakiness risk (a 1-min-vs-1-hour pair would have near-identical weights given the 30-day half-life).
- **Both test games share one non-guest user** so Stage 1 (user pick) is deterministic and the entire fresh-vs-old contrast is isolated to Stage 2 (game pick), matching the plan's guidance.
- **No `tc_multiplier` in the tier-4 game-pick query** — carried forward from the plan's explicit instruction, since blob enrichment (unlike tier-3's live-eval drain) has no time-control-sensitive urgency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue, test tooling] Task 1's literal `<automated>` verify command has a false-positive scope bug**
- **Found during:** Task 1 verification
- **Issue:** The plan's per-task automated check (`grep -niE 'recency[_ ]window' ... | grep -v '^#' | wc -l | grep -qx 0`) matches the module docstring's pre-existing, unrelated tier-2 comment (`Tier 2 (TIER_AUTO_WINDOW) — automatic recency window`, line 5) because the `grep -v '^#'` exclusion is a no-op against `grep -n` output (every line is prefixed `N:`, never starts with `#`). This line describes the historical, scrapped tier-2 auto-enqueue feature and is unrelated to the tier-4 recency-window mechanism this plan replaces; the plan's own action text explicitly says not to touch unrelated routing/historical comments.
- **Fix:** No code change — verified the plan's actual `<verification>` (plan-level) intent instead, which explicitly scopes the check to "no stale (non-comment-history) references," confirming the one remaining match is legitimate historical content, not a stale tier-4 reference. `TIER4_RECENCY_WINDOW` itself has zero remaining references (the stricter, non-ambiguous check), confirmed via `grep -n`.
- **Files modified:** None (verification-only finding).
- **Verification:** `grep -n "TIER4_RECENCY_WINDOW" app/services/eval_queue_service.py tests/test_eval_queue_service.py` returns nothing; the sole `recency window` match is the unrelated tier-2 line.
- **Committed in:** N/A (no code change required).

---

**Total deviations:** 1 (documentation of a verify-script false positive; no code impact).
**Impact on plan:** None — the substantive gates (ruff format/check, `ty check` zero errors, `pytest -n auto tests/test_eval_queue_service.py -x`, no `TIER4_RECENCY_WINDOW` references) all pass cleanly.

## Issues Encountered

None beyond the verify-script false positive documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `_claim_tier4_blob` is ready to drain the full tier-4 blob-backfill backlog; no further follow-up work identified by this plan.
- Prod tuning note: `TIER4_USER_WEIGHT_FLOOR` and `TIER4_GAME_WEIGHT_FLOOR` are seeded from tier-3's values but can be independently adjusted if the anti-starvation/recency tradeoff needs retuning after observing real drain behavior.

## Self-Check: PASSED

- FOUND: app/services/eval_queue_service.py
- FOUND: tests/test_eval_queue_service.py
- FOUND: .planning/quick/260701-lw4-replace-tier-4-blob-backfill-top-50-rece/260701-lw4-SUMMARY.md
- FOUND commit: 6000f70a
- FOUND commit: 9ac007ea
