---
phase: 242-openings-stats-insights-rework
plan: 02
subsystem: api
tags: [fastapi, openings, insights, wilson, dev-clock, partition]

requires:
  - phase: 242-01
    provides: repertoire_recency (resolve_current_cutoffs, is_current), opening_eval.finalize_opening_eval, VERDICT_CI_Z_99
provides:
  - "POST /insights/openings with now_utc from dev_now_utc, per-finding is_current and current_cutoff_white/black"
  - "Four card lists of at most 5 high-confidence (p < 0.01) findings, current before older, Wilson order kept"
  - "Four not-clear lists of at most 10 medium findings (current first, lowest p) plus full *_not_clear_count"
  - "Baseline-centred MG-entry eval with 99% bounds on card findings; 99% Wilson score CI on every finding"
affects: [242-07, openings-frontend]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2
plan_head_before: 18c603f2a8927460526b7e77646f0794ca44842e
plan_head_after: b12f0072899857fcd4258915e9827dce1418a3d5

tech-stack:
  added: []
  patterns:
    - "Pure _partition_section (stable sort keeps Wilson order inside current/older groups)"
    - "Eval enrichment only on the capped card list (Pitfall 8)"

key-files:
  created: []
  modified:
    - app/services/opening_insights_service.py
    - app/schemas/opening_insights.py
    - app/routers/insights.py
    - tests/services/test_opening_insights_service.py
    - tests/routers/test_insights_openings.py

key-decisions:
  - "Cutoffs are carried on _PipelineContext (default None/None) and set by compute_insights before _build_sections, so the existing fetch helpers keep their signatures"
  - "_build_sections split into _rank_sections, _fetch_eval_metrics and the partition step to keep nesting shallow; it now returns dict[str, _SectionPartition]"
  - "Not-clear findings carry no eval; only cards are enriched"

patterns-established:
  - "Existing service tests use 60-game samples (12/12/36) where they need a card-eligible finding"

requirements-completed: [D-00, D-02, D-03, D-04, D-08, D-09, D-10, D-11, D-13]

coverage:
  - id: D1
    description: "now_utc from dev_now_utc reaches compute_insights; every finding carries is_current against its colour cutoff; both cutoffs echoed"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/routers/test_insights_openings.py#test_post_openings_endpoint_passes_dev_clock_now_utc"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_insights_service.py#test_findings_carry_is_current_against_the_colour_cutoff"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cards are 99%-gated, at most 5, current first; not-clear list medium-only, at most 10, count taken before the cap; low dropped"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_insights_service.py#test_partition_not_clear_is_capped_sorted_and_counted_before_the_cap"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_insights_service.py#test_card_list_is_99_gated_capped_and_eval_runs_on_cards_only"
        status: pass
    human_judgment: false
  - id: D3
    description: "Card eval centred on the colour baseline with 99% bounds; every finding has 99% Wilson bounds"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_insights_service.py#test_card_eval_is_centred_on_the_colour_baseline_and_carries_99_cis"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_insights_service.py#test_every_finding_has_a_99_wilson_interval_wider_than_the_95"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 02: Insights endpoint rework Summary

**POST /insights/openings now returns 99%-gated top-5 cards per section, a capped "not clear yet" medium list with its full count, per-finding is_current under a filter-scoped dev-clock cutoff, and baseline-centred eval with 99% CIs on cards only.**

## Accomplishments

- Router: `NowUtc` alias and `now_utc` parameter on `get_opening_insights`; `compute_insights(..., *, now_utc)` resolves per-colour cutoffs with the request filters (`resolve_current_cutoffs`) and stamps `is_current` in `_row_to_finding`.
- `FINDINGS_CARD_CAP = 5` and `FINDINGS_NOT_CLEAR_CAP = 10` replace the two caps of 10. `_partition_section` (`_SectionPartition` dataclass) builds cards (high only, current first, stable Wilson order) and the not-clear list (medium only, current first then lowest p); `not_clear_count` is the medium count before the cap; low findings are dropped.
- Eval enrichment moved after the partition and runs only on card findings (at most 5 per section); `_apply_eval_metrics_to_finding` now delegates to `finalize_opening_eval(pe, finding.color)`, so the z-test is centred on +25 cp (White) / -25 cp (Black) and the 99% eval bounds are filled.
- Schema: `ci99_low/high`, `eval_ci99_low/high_pawns`, `is_current` on findings; four `*_not_clear` lists, four `*_not_clear_count`, `current_cutoff_white/black` on the response; docstrings updated to the new contract.
- `_build_sections` was split (`_rank_sections`, `_fetch_eval_metrics`) so no function breaches the nesting gate.

## Task Commits

1. **Task 1 (tracer): now_utc -> cutoff -> is_current** - `0b36a335e` (feat). Tracer verified end to end (`pytest tests/services/test_opening_insights_service.py tests/routers/test_insights_openings.py`: 50 passed) before expanding. This commit also carries the full schema (additive defaults), so the response contract exists from the first commit.
2. **Task 2: 99% card partition, not-clear list, centred eval, 99% CIs** - `b12f00728` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in existing tests] Legacy fixtures were not card-eligible**
- **Found during:** Task 2
- **Issue:** Existing tests used 20-game samples (score 0.30, p ~ 0.07, "low") and 40-game transposition samples; under the new partition those findings are dropped or demoted, so 11 tests failed on counts.
- **Fix:** Moved those fixtures to high-confidence samples (60 games 12/12/36; pos WDL 48/12/20, 30/30/60, 36/12/12, 32/0/8) and updated the matching assertions (n_games, wins, score). The behaviour under test (attribution, dedupe, transposition WDL) is unchanged.
- **Files modified:** `tests/services/test_opening_insights_service.py`
- **Committed in:** `b12f00728`

**2. [Rule 3 - Blocking] Cutoff lookup needed a test seam**
- **Issue:** Every direct `compute_insights` call in the existing tests now needs a cutoff resolver and `now_utc`.
- **Fix:** Autouse fixture `mock_resolve_cutoffs` (default: no cutoffs) and `now_utc=NOW_UTC` on all calls. `_run_compute` gained optional `eval_metrics` / `eval_calls`.
- **Committed in:** `0b36a335e`, `b12f00728`

**Total deviations:** 2, both test-side; no production-scope change.

## Verification

- `uv run pytest tests/services/test_opening_insights_service.py tests/routers/test_insights_openings.py tests/services/test_opening_insights_arrow_consistency.py`: 61 passed
- Full suite `uv run pytest -n auto -x`: 5559 passed, 19 skipped
- `ruff format`, `ruff check`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean
- Mutation proof: replacing the current-first card sort with a plain slice made 3 tests fail (partition x2, end-to-end card test); restored.

## Known Stubs

None.

## Threat Flags

None. `user_id` still comes only from `current_active_user`; `OpeningInsightsRequest` keeps `extra="forbid"`; `dev_now_utc` is inert outside development; eval enrichment is limited to card findings.

## Notes for downstream plans

- Frontend (242-07) must mirror: `ci99_low/high`, `eval_ci99_low/high_pawns`, `is_current` on findings; `*_not_clear`, `*_not_clear_count`, `current_cutoff_white/black` on the response. The four existing lists now hold only `confidence == "high"` findings.
- `openings_service.py` (Moves tab) still uses the 0 cp H0; that is plan 242-03's scope.

## Self-Check: PASSED

- Modified files exist; commits `0b36a335e` and `b12f00728` are ancestors of HEAD.
