---
phase: 75-backend-score-metric-confidence-annotation
fixed_at: 2026-04-28T10:55:00Z
review_path: .planning/phases/75-backend-score-metric-confidence-annotation/75-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 75: Code Review Fix Report

**Fixed at:** 2026-04-28T10:55:00Z
**Source review:** .planning/phases/75-backend-score-metric-confidence-annotation/75-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (0 critical + 3 warnings)
- Fixed: 3
- Skipped: 0
- Info findings (4): out of scope for `critical_warning` fix run; left for human triage / Phase 76.

## Fixed Issues

### WR-01: `_replay_san_sequence` fallback contradicts docstring and D-34

**Files modified:** `app/services/opening_insights_service.py`
**Commit:** `2a59409`
**Applied fix:** Added an explicit `if not san_sequence: raise ValueError(...)` guard at the top of `_replay_san_sequence` so an empty SAN sequence raises rather than silently replaying to the initial-position FEN. Removed the `or []` defensive coercions at all four call sites in the service module:
- `_attribute_finding` Pass 2 lineage walk (line 232)
- `compute_insights` parent-prefix gather (line 382)
- `compute_insights` entry-FEN replay (line 415)
- `OpeningInsightFinding(entry_san_sequence=...)` schema population (line 434)

An empty/None `row.entry_san_sequence` now raises a `TypeError` (or the explicit `ValueError` from `_replay_san_sequence`) which propagates to the top-level `try/except` in `compute_insights` and gets captured by Sentry with full request context — matching the D-34 contract that this code path "never falls back to the initial position". All 34 service + arrow-consistency tests pass; 18 repository tests pass; 241 insights-related tests in the wider suite pass.

### WR-02: `OPENING_INSIGHTS_MAJOR_EFFECT` imported with `noqa: F401`

**Files modified:** `app/repositories/openings_repository.py`
**Commit:** `fe2c508`
**Applied fix:** Removed the `OPENING_INSIGHTS_MAJOR_EFFECT` import and its `# noqa: F401` justification. Replaced it with a one-line comment near the remaining imports that names the constant for cross-module discoverability ("the SQL gate uses `OPENING_INSIGHTS_MINOR_EFFECT` only; the major-vs-minor distinction is applied downstream in `opening_insights_service._classify_row`"). ruff, ty, and pytest all clean.

### WR-03: Pydantic `OpeningInsightFinding` numeric fields lack range constraints

**Files modified:** `app/schemas/opening_insights.py`
**Commit:** `bf7e28c`
**Applied fix:** Added `Field(ge=..., le=...)` constraints to the numeric fields of `OpeningInsightFinding`:
- `n_games: int = Field(ge=OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE)` — couples the floor to the SQL HAVING gate via the shared constant rather than a magic number.
- `wins`, `draws`, `losses: int = Field(ge=0)` — non-negative game counts.
- `score: float = Field(ge=0.0, le=1.0)` — score is `(W + D/2)/n` by construction.
- `p_value: float = Field(ge=0.0, le=1.0)` — two-sided erfc p-value bounded in [0, 1].

Imported `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE` from `app.services.opening_insights_constants`. Did not add the optional `wins + draws + losses == n_games` `model_validator` cross-field check — left for a future enhancement since the review explicitly marked it optional and the additional constraint surface would risk legitimate data being rejected if rounding ever creeps in. ruff, ty, and all 241 insights-related tests pass.

## Skipped Issues

None — all 3 warning-level findings were fixed.

---

_Fixed: 2026-04-28T10:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
