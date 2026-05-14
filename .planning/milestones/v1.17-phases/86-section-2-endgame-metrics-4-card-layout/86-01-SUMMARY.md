---
phase: 86
plan: 01
subsystem: backend-stats
tags: [score-confidence, peer-bullet, wald-z, endgame, sig-test]
requires: []
provides:
  - compute_skill_diff_test
  - compute_per_bucket_diff_test
  - _headline_rate
  - _headline_rate_variance
affects:
  - app/services/score_confidence.py
  - tests/services/test_score_confidence.py
tech-stack:
  added: []
  patterns:
    - Wald-z on independent headline-rate difference (per-bucket)
    - Wald-z on Skill composite mean over active buckets
    - Mirror identity inversion (opp_rate = 1 − userRate(opp_row))
    - Variance-0 trap mirroring compute_score_difference_test pattern
key-files:
  created: []
  modified:
    - app/services/score_confidence.py
    - tests/services/test_score_confidence.py
decisions:
  - "Active bucket for Skill helper = user_N > 0 AND opp_N > 0 (symmetric composite)"
  - "Variance per bucket uses the bucket's HEADLINE-RATE formula, NOT chess-score on all three"
  - "Per-bucket helper uses STRICT opp-side N>=10 gate (D-05), not min-of-both"
  - "Helpers internalize mirror identity inversion; callers pass user's mirror-bucket row"
metrics:
  duration: "~25 min"
  completed: "2026-05-14"
requirements:
  - SEC2-06
  - SEC2-08
---

# Phase 86 Plan 01: Backend Math Helpers for Section 2 Peer Bullets Summary

Two pure-math helpers in `app/services/score_confidence.py` powering Phase 86's
per-card peer-bullet sig tests, with HEADLINE-RATE variance per bucket (Conv
Bernoulli win, Recov Bernoulli save, Parity trinomial chess-score) — not the
incorrect chess-score-on-all-three approach the initial draft used.

## What Was Built

- `compute_skill_diff_test(conv_row, parity_row, recov_row, opp_conv_row,
  opp_parity_row, opp_recov_row) -> (skill, opp_skill, p_value, ci_low, ci_high)`
  for the Skill-card peer bullet. Active bucket = user_N > 0 AND opp_N > 0;
  Wald-z on mean-difference; SE composition with per-bucket headline-rate
  variance; sig-gated on `n_active < 2 OR any opp_row.N < CONFIDENCE_MIN_N`.
  Skill scalars returned even when sig fields are None.
- `compute_per_bucket_diff_test(bucket, user_row, opp_row) ->
  (p_value, ci_low, ci_high)` for the Conv / Parity / Recov per-card peer
  bullet. Wald-z on `userRate − (1 − userRate(opp_row))`. Strict opp-side
  `opp_row.N < CONFIDENCE_MIN_N` gate per D-05 (NOT min-of-both).
- Private `_headline_rate(bucket, w, d, _l, n)` and
  `_headline_rate_variance(bucket, w, d, _l, n)` shared internals; one place
  to update the legacy frontend `userRate()` math if it ever changes.
- 13 new pytest cases across `TestComputeSkillDiffTest` (7 methods) and
  `TestComputePerBucketDiffTest` (6 methods), including the two BLOCKER
  regression tests (headline-rate-variance vs chess-score variance; parity
  self-mirror diff = 2·rate − 1).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add compute_skill_diff_test + compute_per_bucket_diff_test helpers | d5c18508 | app/services/score_confidence.py |
| 2 | Add TestComputeSkillDiffTest + TestComputePerBucketDiffTest pytest coverage | 2a3c3be5 | tests/services/test_score_confidence.py |

## Verification

- `uv run pytest tests/services/test_score_confidence.py -x` -> 53 passed
- `uv run pytest tests/services/test_score_confidence.py::TestComputeSkillDiffTest -x` -> 7 passed
- `uv run pytest tests/services/test_score_confidence.py::TestComputePerBucketDiffTest -x` -> 6 passed
- `uv run ruff check app/services/score_confidence.py tests/services/test_score_confidence.py` -> All checks passed
- `uv run ruff format --check ...` -> 2 files already formatted
- `uv run ty check app/ tests/` -> All checks passed

## Deviations from Plan

None of substance. One test (`test_variance_zero_trap_gives_p_zero_collapsed_ci`)
was initially written with a flawed fixture (user all-wins vs opp all-losses
mirror would produce diff=0, not the diff=1 the docstring claimed). Caught
during self-review before commit and replaced with the correct fixture
(user all-wins vs opp_row also all-wins -> opp_rate = 1 − 1 = 0, diff = 1.0,
SE_diff = 0 -> p_value = 0.0).

## Notes

**Milestone-boundary callout.** v1.17 ROADMAP described the milestone as a
"frontend-only refactor"; Phase 86 adds two backend math helpers (this plan)
plus 5 Skill schema fields and 3 per-MaterialRow diff fields (Plan 02) per
user authorization at discuss-phase. This mirrors the Phase 85 D-01 / Phase
85.1 caveats — the peer-bullet sig tests require backend support and could
not be implemented frontend-only.

**Math correctness (Phase 86 plan-checker BLOCKER 2).** Per-bucket variance
uses HEADLINE-RATE formulas: Conv Bernoulli on the win indicator (`p·(1−p)`
with `p = W/N`), Recov Bernoulli on the save indicator (`p·(1−p)` with
`p = (W+D)/N`), Parity trinomial chess-score (`max(0, (W + 0.25·D)/N − p²)`
with `p = (W + 0.5·D)/N`). The chess-score-on-all-three approach the initial
plan draft used would have produced wrong p-values for the Conv and Recov
cards (variance off by `score² − (W + 0.25·D)/N + W/N · (1 − W/N)` in the
general case). The regression test
`test_skill_diff_uses_per_bucket_headline_variance_not_chess_score_variance`
pins the CI half-width against the manually computed headline-rate-formula
SE and explicitly asserts it does NOT equal the chess-score-formula SE.

**Parity self-mirror (Phase 86 plan-checker BLOCKER 1).** Per
`MIRROR_BUCKET = {conversion: 'recovery', recovery: 'conversion',
parity: 'parity'}`, the parity bucket is its own mirror. The helpers invert
the opp side via `1 − userRate(opp_row)` internally, so passing the SAME
parity row as both `user_row` and `opp_row` produces `diff = 2·user_rate − 1`,
NOT 0. The previously-considered "chess-score on two independent cohorts"
approach (which would have called `compute_score_difference_test(eg_w, eg_d,
eg_l, eg_n, eg_w, eg_d, eg_l, eg_n)` on the same parity row) would have
produced `diff = (W + 0.5·D)/N − (W + 0.5·D)/N = 0` for self-mirror, hiding
the headline signal entirely. The regression test
`test_parity_self_mirror_produces_nontrivial_diff` pins this behavior.

**Independence caveat for Skill composite.** Conv and Recov rows for the same
user can come from the same physical games (mirror identity at the bucket
boundary — a game that's a "conversion-win" for user-up-material is a
"recovery-loss" for the opponent in the mirror bucket). The three bucket
means are therefore not strictly independent, and `SE_diff` may slightly
under-estimate true uncertainty. Accepted for the v1.17 heuristic composite;
documented in `compute_skill_diff_test`'s docstring. The per-card
`compute_per_bucket_diff_test` is run on a single bucket and does not have
this caveat.

## Self-Check: PASSED

- FOUND: app/services/score_confidence.py (Task 1 modifications, +265 LOC)
- FOUND: tests/services/test_score_confidence.py (Task 2 modifications, +399 LOC)
- FOUND commit d5c18508 (feat 86-01 helpers)
- FOUND commit 2a3c3be5 (test 86-01 test classes)
