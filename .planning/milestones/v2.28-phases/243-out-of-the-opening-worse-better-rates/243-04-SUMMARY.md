---
phase: 243-out-of-the-opening-worse-better-rates
plan: 04
subsystem: backend
tags: [fastapi, percentiles, wilson, openings, read-path]

requires:
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 01
    provides: fetch_opening_out_counts, opening_out_seed helpers
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 02
    provides: colour-pooled opening CDF cells in benchmark_cohort_cdf
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 03
    provides: fetch_opening_out_rows (persisted per-colour percentiles)
provides:
  - GET /api/openings/out-of-opening-stats (authenticated, parameterless, filter-independent)
  - opening_out_stats_service (fetch_opening_out_inputs, pure build_out_of_opening_stats, get_out_of_opening_stats)
  - schemas OpeningOutTcOut / OpeningOutRateOut / OpeningOutColorOut / OutOfOpeningStatsResponse
  - public rank_status / is_anchor_game in endgame_ranked_service
affects: [243-05 frontend section card and popover]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Gate z passed in (OPENING_INSIGHTS_CI_Z_95); the Endgames 99% helpers are neither reused nor edited"
    - "Orientation applied last: gate and direction guard see raw values only"

key-files:
  created:
    - app/services/opening_out_stats_service.py
    - app/schemas/opening_out.py
    - tests/routers/test_openings_out_of_opening.py
    - tests/services/test_opening_out_stats_service.py
  modified:
    - app/services/endgame_ranked_service.py
    - app/routers/openings.py

key-decisions:
  - "A3 adopted: a ranked TC with no CDF cell is listed but excluded from headline and gate"
  - "A4 adopted: footer band is the game-weighted p25/p50/p75 over contributing TCs; per-TC list has no band"
  - "A5 modified: nothing-contributes card status is pending > unranked > below_floor"
  - "A6 rejected: pending mirrors Endgames exactly (rank_status with eval_dependent=True, eval_pending per TC)"
  - "Dev-clock exception: window uses SQL NOW() to match the Stage B basis, documented in the route docstring"

requirements-completed: [D-06, D-07, D-08, D-10, D-11]

coverage:
  - id: D1
    description: "Endpoint requires auth (401), takes no parameters and returns an identical body for any query string; user_id only from the authenticated user"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/routers/test_openings_out_of_opening.py#test_requires_auth_returns_401"
        status: pass
      - kind: integration
        ref: "tests/routers/test_openings_out_of_opening.py#test_seeded_user_gets_ranked_collapsed_stats"
        status: pass
    human_judgment: false
  - id: D2
    description: "A user with no games gets below_floor 0 of 30 on both colours and both rates with an empty TC list"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "tests/routers/test_openings_out_of_opening.py#test_user_without_games_is_below_floor_everywhere"
        status: pass
    human_judgment: false
  - id: D3
    description: "Seeded user: ranked card with on-read k/n, per-TC entry, 95% Wilson CI around the rate, peer p25/p50/p75 from the CDF cell, worse percentile inverted (30 -> 70.0), better not inverted"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/routers/test_openings_out_of_opening.py#test_seeded_user_gets_ranked_collapsed_stats"
        status: pass
    human_judgment: false
  - id: D4
    description: "Headline is the n-weighted mean of contributing per-TC raw percentiles (40/80 at 300/100 games -> 50.0); below-floor, no-cell, anchor-floor and pending TCs are excluded but listed"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_headline_is_game_weighted_over_contributing_tcs"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_below_floor_tc_is_excluded_but_listed"
        status: pass
    human_judgment: false
  - id: D5
    description: "Gate: pooled 95% Wilson CI vs game-weighted peer median; a case significant at 95% but not 99% is significant; the direction guard blocks a CI on the opposite side of the percentile"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_gate_uses_95_percent_not_99"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_gate_direction_guard_blocks_ci_on_the_opposite_side_of_the_percentile"
        status: pass
    human_judgment: false
  - id: D6
    description: "Card states with no contributing TC (pending > unranked > below_floor with largest floor_n, 0 of 30 when nothing is listed) and colour independence"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_card_is_pending_when_any_tc_is_pending"
        status: pass
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_colours_are_independent"
        status: pass
    human_judgment: false
  - id: D7
    description: "Footer data: peer band is the game-weighted mean over contributing TCs; pooled k and n exclude non-contributing TCs"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "tests/services/test_opening_out_stats_service.py#test_footer_band_is_weighted_over_contributing_tcs_only"
        status: pass
    human_judgment: false
  - id: D8
    description: "Endgames behaviour unchanged by the rank_status / is_anchor_game rename (service, parity and router tests pass untouched)"
    verification:
      - kind: integration
        ref: "tests/services/test_endgame_ranked_service.py, tests/services/test_endgame_ranked_parity.py, tests/test_endgames_router.py"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-10-31
status: complete
plan_head_before: b3147d291312dbf2c0abb5b945ee64458ae48af9
plan_head_after: dafb73a74d536a0e02cf56ea63add6d52c03e18c
commits: 2
---

# Phase 243 Plan 04: Out-of-opening stats read path Summary

**`GET /api/openings/out-of-opening-stats` returns both colours' worse/better rates ranked per TC, collapsed to a game-weighted favourable percentile, and gated by a pooled 95% Wilson CI against the game-weighted peer median, with the per-TC list and footer data the popover needs.**

## Accomplishments

- `rank_status` and `is_anchor_game` are now public in `endgame_ranked_service.py` (rename only; Endgames output byte-identical, its 63 service/parity/router/new tests pass).
- `opening_out_stats_service.py`: sequential fetch (ranked games per TC for anchor/pending counts, on-read counts, anchors, persisted rows, one batched CDF read for peer p25/p50/p75) and a pure builder split into small helpers (`_tc_entry`, `_ranked_card`, `_unranked_card`, `_rate_card`); depth gate clean.
- Gate: `significant = ci_excludes(peer_p50, lo, hi) and (rate > peer_p50) == (raw_headline > 50)`, z = `OPENING_INSIGHTS_CI_Z_95`; none of the Endgames 99% helpers is imported or edited.
- Orientation applied last: worse = `100 - raw`, better = raw, for the card and every listed TC.
- 3 router tests and 17 pure-builder tests. Mutation check on the builder: switching z to 2.576 (2 tests fail), dropping the direction guard (1), removing the worse inversion (3) and using an unweighted mean (3) each fail the matrix; builder restored afterwards.

## Task Commits

1. **Task 1 (tracer):** `6f00cee7d` feat(243-04): GET /openings/out-of-opening-stats with per-TC collapse and 95% gate
2. **Task 2:** `dafb73a74` test(243-04): pure-builder matrix for opening-out collapse, 95% gate, orientation, statuses

Tracer gate: `<verify>` re-run end-to-end after the tracer commit (router + Endgames service/parity/router tests, ty, ruff, depth gate): passed, so expansion proceeded.

## Deviations from Plan

None - plan executed as written. No builder defect surfaced from the matrix (all 17 cases passed on first run), so no `build_out_of_opening_stats` fix was driven by a test case. Two test-typing fixes (ty `dict[str, ...]` vs Literal keys) were made in-flight.

## Known Stubs

None.

## Threat Flags

None. T-243-11 (401 without token) and T-243-12 (no parameters, identical body for extra query strings, keyword-only `user_id` from `user.id`) are covered by router tests; T-243-13 (sequential queries, 4 TCs) holds by construction.

## Verification

- `uv run pytest -n auto -x`: 5649 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`, `ruff check`, `ruff format`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `"/out-of-opening-stats"` in the router 1, `z=OPENING_INSIGHTS_CI_Z_95` 1, forbidden 99% symbols 0, `def rank_status|def is_anchor_game` 2, test count in the matrix file 17 (>= 11), `VERDICT_CI_Z_99` in it 2.

## Next Phase Readiness

Plan 05 (frontend) can consume `OutOfOpeningStatsResponse`: per colour, `worse` is the primary row, `better` the lesser; `significant` and `percentile_favorable` are decided server-side.

## Self-Check: PASSED

- FOUND: app/services/opening_out_stats_service.py, app/schemas/opening_out.py, tests/routers/test_openings_out_of_opening.py, tests/services/test_opening_out_stats_service.py
- FOUND commits: 6f00cee7d, dafb73a74
