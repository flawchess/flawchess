---
phase: "102"
plan: "05"
subsystem: "insights-llm"
tags: ["llm", "prompt-engineering", "percentile", "rating-anchor", "platform-composition"]
dependency_graph:
  requires: ["102-04"]
  provides: ["Lichess-equivalent anchor framing in LLM reports"]
  affects: ["app/services/insights_llm.py", "app/schemas/insights.py", "app/services/insights_service.py", "app/prompts/endgame_insights.md"]
tech_stack:
  added: []
  patterns: ["Pydantic v2 model composition", "LLM prompt teaching via structured payload blocks"]
key_files:
  created: []
  modified:
    - "app/schemas/insights.py"
    - "app/services/insights_service.py"
    - "app/services/insights_llm.py"
    - "app/prompts/endgame_insights.md"
    - "tests/test_insights_schema.py"
    - "tests/services/test_insights_llm.py"
decisions:
  - "RatingAnchorContext mirrors RatingAnchorOut (endgames.py) rather than reusing it, keeping the insights pipeline independent of the endgames schema"
  - "cohort_anchors changed from dict[str, int] to dict[str, RatingAnchorContext] — backwards-incompatible but safe (field is optional, no external consumer reads it directly)"
  - "Rating-basis block emitted once after player-profile, before sections, so the LLM has the conversion context before any pctl= annotation is encountered"
  - "Four disclosure branches mirror PercentileChipPopoverBody exactly: pure-cc (conversion note), mixed (both platforms), pure-lichess (no conversion note), suppressed (omitted)"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-01"
  tasks_completed: 1
  files_modified: 6
---

# Phase 102 Plan 05: Rating-Basis Lichess-Equivalent Framing Summary

Chess.com players confused by being measured against "~1550-rated peers" when their chess.com rating is ~1400. This plan teaches the LLM to surface the Lichess-equivalent framing and explain the conversion for chess.com-heavy users, exposing the platform composition in the payload.

## Tasks

### Task 1 — Payload, prompt, and version bump (commit `1a4e71eb`)

**Payload changes:**

- Added `RatingAnchorContext` Pydantic model to `app/schemas/insights.py` carrying `anchor_rating`, `n_chesscom_games`, `n_lichess_games`, `chesscom_median_native`, `lichess_median_native`. Added to `__all__`.
- Changed `EndgameTabFindings.cohort_anchors` from `dict[str, int] | None` to `dict[str, RatingAnchorContext] | None` with an explanatory comment.
- Updated `insights_service.compute_findings` to populate `cohort_anchors[tc]` with `RatingAnchorContext(...)` from each `all_time_resp.rating_anchors[tc]`. Fixed all four callers that previously read an integer from `cohort_anchors.get(tc)` to read `.anchor_rating` instead (for `MetricPercentileRecord.anchor` which stays `int | None`).

**Prompt changes (`_format_rating_basis_block`):**

- Added `_format_rating_basis_block(cohort_anchors)` helper in `insights_llm.py`. Renders one `[rating basis] {tc}: anchor ~A (Lichess-equivalent) | ...` line per TC, following the four disclosure branches that mirror `PercentileChipPopoverBody`:
  - Pure chess.com: shows `chess.com median ~{cc_med} (converted)`, `lichess median n/a`, game counts
  - Mixed: shows both platforms with native medians and game counts
  - Pure lichess: shows `lichess median ~{li_med} (native)`, `chess.com median n/a`, game counts
  - Suppressed (both zero): TC omitted
- Block emitted once in `_assemble_user_prompt` after `_format_player_profile_block`, before section blocks
- Updated `_render_summary_block` and `_render_subsection_block` signatures: `cohort_anchors` parameter type updated from `dict[str, int] | None` to `dict[str, RatingAnchorContext] | None`

**Prompt teaching (`endgame_insights.md`):**

- Added `D-05a` framing rule after D-05. Teaches:
  - The cohort anchor is always a Lichess-equivalent rating
  - Four disclosure branches with concrete instructions per case
  - Conversion clarification must appear AT MOST ONCE in the report
  - Pure-lichess users: no conversion note
  - Chess.com-heavy users: cite `chesscom_median_native` from the `[rating basis]` block

**Version bump:** `endgame_v37` -> `endgame_v38` with inline changelog entry describing all changes.

**Tests:**

- `test_insights_schema.py`: Added `RatingAnchorContext` import; updated `test_all_contains_expected_names` (added `RatingAnchorContext`); updated `test_field_order_locked` comment; added `TestRatingAnchorContext` class with 4 test cases covering basic construction, pure-lichess, mixed user, and `cohort_anchors` in `EndgameTabFindings`
- `test_insights_llm.py`: Updated all 8 `endgame_v37` occurrences to `endgame_v38`; fixed 3 `cohort_anchors={"blitz": 1500}` legacy tests to use `RatingAnchorContext` or `None`; added `TestRatingBasisBlock` class with 9 test cases covering all disclosure branches, TC ordering, integration into assembled prompt, and prompt teaching presence

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `app/schemas/insights.py`: `RatingAnchorContext` class present, `cohort_anchors` uses it
- `app/services/insights_service.py`: `RatingAnchorContext` imported and used in `cohort_anchors` build
- `app/services/insights_llm.py`: `_format_rating_basis_block` present, called from `_assemble_user_prompt`, `_PROMPT_VERSION == "endgame_v38"`
- `app/prompts/endgame_insights.md`: `D-05a` teaching present with four disclosure branches
- Commit `1a4e71eb` verified
- `uv run pytest -n auto`: 2237 passed, 10 skipped
- `uv run ty check`: 0 errors
- `uv run ruff check` + `uv run ruff format`: clean
