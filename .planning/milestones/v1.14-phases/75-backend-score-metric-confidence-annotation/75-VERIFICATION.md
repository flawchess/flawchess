---
phase: 75-backend-score-metric-confidence-annotation
verified: 2026-04-28T13:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 75: Backend — Score Metric and Confidence Annotation Verification Report

**Phase Goal:** Replace `loss_rate`/`win_rate` with chess score `(W + 0.5·D)/N` in `opening_insights_service.py` and `openings_repository.py`. Classify on score vs 0.50 pivot with effect-size thresholds (minor ≥ 0.05, major ≥ 0.10). Compute trinomial Wald (D-05 amendment) 95% half-width per finding and bucket to low/medium/high. Drop `MIN_GAMES_PER_CANDIDATE` from 20 → 10. Expose `confidence`/`p_value` on `OpeningInsightFinding` (D-09 amendment removes `loss_rate`/`win_rate`). Update CI-enforced consistency test mirroring `arrowColor.ts`.

**Verified:** 2026-04-28T13:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth (= Requirement)                                                                                              | Status     | Evidence                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | INSIGHT-SCORE-01 — Replace loss_rate/win_rate with score `(W + 0.5·D)/N` in service and repository                | ✓ VERIFIED | `opening_insights_service.py:84` `score = (row.w + 0.5 * row.d) / row.n`; `_compute_score:102` `(row.w + row.d / 2) / row.n`; repository `score_expr = (cast(wins, Float) + 0.5 * cast(draws, Float)) / cast(n_games, Float)` (line 655). No live `loss_rate`/`win_rate` field references remain (only historical docstring mentions). |
| 2   | INSIGHT-SCORE-02 — Pivot at 0.50                                                                                   | ✓ VERIFIED | `OPENING_INSIGHTS_SCORE_PIVOT: float = 0.50` in `opening_insights_constants.py:25`; consumed in service via `SCORE_PIVOT` alias and in repository via `OPENING_INSIGHTS_SCORE_PIVOT`.                                       |
| 3   | INSIGHT-SCORE-03 — Effect-size thresholds (minor ≥ 0.05, major ≥ 0.10) symmetric, strict ≤/≥, in constants module | ✓ VERIFIED | Constants `OPENING_INSIGHTS_MINOR_EFFECT: float = 0.05`, `OPENING_INSIGHTS_MAJOR_EFFECT: float = 0.10`; `_classify_row` lines 84-97 implement strict `<= 0.45 / 0.40` weakness and `>= 0.55 / 0.60` strength; boundary tests pass (0.45→minor weakness, 0.40→major, 0.55→minor strength, 0.60→major, 0.46/0.54→None). |
| 4   | INSIGHT-SCORE-04 — Trinomial Wald 95% CI; half-width buckets ≤0.10→high, ≤0.20→medium, else low; pure stdlib       | ✓ VERIFIED | `_compute_confidence` lines 105-152: variance `(w + 0.25*d)/n - score*score` clamped at 0; `se = sqrt(variance/n)`; `half_width = 1.96 * se`; bucketed on `CONFIDENCE_HIGH_MAX_HALF_WIDTH` (0.10) / `CONFIDENCE_MEDIUM_MAX_HALF_WIDTH` (0.20). Pure `math` only — no scipy. SE=0 guards return ("high", 1.0)/("high", 0.0). All 7 confidence boundary tests pass. |
| 5   | INSIGHT-SCORE-05 — Drop `MIN_GAMES_PER_CANDIDATE` 20 → 10                                                          | ✓ VERIFIED | `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 10` (constants:20); SQL HAVING uses `n_games >= OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE` (repo:697); test `test_min_games_per_candidate_floor_at_10` exists.            |
| 6   | INSIGHT-SCORE-06 — Add `confidence: Literal["low","medium","high"]` and `p_value: float` to `OpeningInsightFinding`; remove `loss_rate`/`win_rate` | ✓ VERIFIED | `app/schemas/opening_insights.py:65-68` declares both new fields with the correct types. No `win_rate`/`loss_rate` field declarations anywhere in the schema. Service `compute_insights` populates them at lines 423-447 (`confidence=confidence, p_value=p_value`). |
| 7   | INSIGHT-SCORE-07 — CI consistency test asserts score-based lock-step                                              | ✓ VERIFIED | `tests/services/test_opening_insights_arrow_consistency.py` ships four tests (`test_score_pivot_matches_frontend`, `test_minor_effect_matches_frontend`, `test_major_effect_matches_frontend`, `test_min_games_matches_frontend`); all 4 pass. Frontend `arrowColor.ts:21-23` exports `SCORE_PIVOT=0.50`, `MINOR_EFFECT_SCORE=0.05`, `MAJOR_EFFECT_SCORE=0.10`. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                                                            | Expected                                                                                          | Status     | Details                                                                                                                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/services/opening_insights_constants.py`                        | Six new constants (pivot, minor/major effect, two half-width buckets, MIN_GAMES=10); `LIGHT_THRESHOLD` removed | ✓ VERIFIED | All six constants present at correct values; `OPENING_INSIGHTS_LIGHT_THRESHOLD` fully removed. Imported by both service and repository.                                          |
| `app/schemas/opening_insights.py`                                   | `OpeningInsightFinding` with `confidence` + `p_value`, no `loss_rate`/`win_rate`                  | ✓ VERIFIED | Fields present with correct Literal/float types; legacy fields removed; class docstring updated to (D-03, D-05, D-25; Phase 75 D-09).                                            |
| `app/services/opening_insights_service.py`                          | `_classify_row` score-based; `_compute_confidence` helper; `compute_insights` wires new fields    | ✓ VERIFIED | All three changes present and consumed at line 398 (classify), 423-424 (score+confidence), 446-447 (constructor wiring). `DARK_THRESHOLD` removed.                                |
| `app/repositories/openings_repository.py`                           | HAVING uses score-based gate (n>=10, score<=0.45 or score>=0.55)                                  | ✓ VERIFIED | Lines 695-703: HAVING combines `n_games >= 10` with `or_(score_expr <= 0.45, score_expr >= 0.55)`. `score_expr` built at line 655 from castfloat ratio.                          |
| `frontend/src/lib/arrowColor.ts`                                    | Pure-additive exports `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`; body unchanged   | ✓ VERIFIED | Three new exports at lines 21-23 with values 0.50/0.05/0.10. `getArrowColor` and `arrowSortKey` body untouched. Existing `LIGHT_COLOR_THRESHOLD`/`DARK_COLOR_THRESHOLD`/hex constants preserved per Phase 76 deferral.    |
| `tests/services/test_opening_insights_arrow_consistency.py`         | Four lock-step tests (pivot, minor, major, min_games)                                             | ✓ VERIFIED | All four tests present and pass.                                                                                                                                                  |
| `.planning/REQUIREMENTS.md`                                         | INSIGHT-SCORE-04 amended (Wilson → trinomial Wald + half-width buckets); INSIGHT-SCORE-06 adds `p_value`; footer notes amendments | ✓ VERIFIED | Lines 19, 21, 68 updated as specified. "Wilson 95% confidence interval" no longer appears (REQ note: "binomial Wilson approximation" remains as a contrastive reference in the trinomial Wald description). |

### Key Link Verification

| From                                                              | To                                                            | Via                                                                | Status   | Details                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/services/test_opening_insights_arrow_consistency.py`       | `app/services/opening_insights_constants.py`                  | Imports four backend constants                                      | ✓ WIRED  | Lines 16-21 import OPENING_INSIGHTS_SCORE_PIVOT/MINOR/MAJOR_EFFECT and MIN_GAMES_PER_CANDIDATE.                                                                                                                                                                                                                 |
| `tests/services/test_opening_insights_arrow_consistency.py`       | `frontend/src/lib/arrowColor.ts`                              | Regex extraction                                                    | ✓ WIRED  | `_extract_float`/`_extract_int` over `_ARROW_TS` path. Tests pass against current arrowColor.ts.                                                                                                                                                                                                                |
| `app/services/opening_insights_service.py::_classify_row`         | `app/services/opening_insights_constants.py`                  | Aliased import of SCORE_PIVOT, MINOR_EFFECT, MAJOR_EFFECT           | ✓ WIRED  | Lines 36-40 alias five constants from the constants module; classifier consumes all three at lines 84-88.                                                                                                                                                                                                       |
| `app/services/opening_insights_service.py::_compute_confidence`   | `app/services/opening_insights_constants.py`                  | Aliased CONFIDENCE_HIGH_MAX_HALF_WIDTH / CONFIDENCE_MEDIUM_MAX_HALF_WIDTH | ✓ WIRED  | Lines 36-37 alias both bucket thresholds; consumed at 143-145.                                                                                                                                                                                                                                                  |
| `app/services/opening_insights_service.py::compute_insights`      | `app/schemas/opening_insights.py::OpeningInsightFinding`      | Constructor passes `confidence=confidence, p_value=p_value`        | ✓ WIRED  | Lines 446-447. No `loss_rate`/`win_rate` arguments.                                                                                                                                                                                                                                                              |
| `app/repositories/openings_repository.py::query_opening_transitions` | `app/services/opening_insights_constants.py`               | Imports MIN_GAMES, SCORE_PIVOT, MINOR_EFFECT, MAJOR_EFFECT          | ✓ WIRED  | Lines 20-25; HAVING references all of them inline at 656-697.                                                                                                                                                                                                                                                    |

### Data-Flow Trace (Level 4)

| Artifact                                       | Data Variable          | Source                                                                                            | Produces Real Data | Status      |
| ---------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------- | ------------------ | ----------- |
| `OpeningInsightFinding.score`                 | service `score` var    | `_compute_score(row)` from real DB row at service line 423                                         | Yes                | ✓ FLOWING   |
| `OpeningInsightFinding.confidence` / `p_value` | tuple from `_compute_confidence(row)` | service line 424 from real DB row; values flow into constructor at 446-447                       | Yes                | ✓ FLOWING   |
| Repository `score_expr` HAVING gate            | computed from cast aggregations | wins/draws/n_games aggregated from `transitions_cte` over real `Game` rows                        | Yes                | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                     | Command                                                                                                                                                          | Result                  | Status |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------ |
| Score classifier passes boundary tests                       | `uv run pytest tests/services/test_opening_insights_service.py -q`                                                                                                | All boundary tests pass | ✓ PASS |
| Confidence helper passes boundary tests                      | `uv run pytest tests/services/test_opening_insights_service.py::test_compute_confidence_high_at_large_n` and 6 sibling tests                                     | All 7 confidence tests pass | ✓ PASS |
| Repository HAVING gate accepts/rejects on score boundaries   | `uv run pytest tests/repositories/test_opening_insights_repository.py -q`                                                                                         | All HAVING tests pass   | ✓ PASS |
| CI consistency test green                                    | `uv run pytest tests/services/test_opening_insights_arrow_consistency.py -q`                                                                                      | 4/4 pass                | ✓ PASS |
| Insights router smoke test                                   | `uv run pytest tests/routers/test_insights_openings.py -q`                                                                                                        | All pass                | ✓ PASS |
| Combined run (58 tests)                                      | `uv run pytest tests/services/test_opening_insights_arrow_consistency.py tests/services/test_opening_insights_service.py tests/repositories/test_opening_insights_repository.py tests/routers/test_insights_openings.py -q` | 58 passed in 1.27s      | ✓ PASS |
| ty check                                                    | `uv run ty check ...` on all five touched modules + the consistency test                                                                                          | All checks passed       | ✓ PASS |
| ruff check                                                  | `uv run ruff check ...` on the same set                                                                                                                          | All checks passed       | ✓ PASS |

### Requirements Coverage

| Requirement       | Source Plan(s)        | Description (paraphrased)                                          | Status      | Evidence                                                                                                                                              |
| ----------------- | --------------------- | ------------------------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| INSIGHT-SCORE-01  | 75-02, 75-03          | Replace loss_rate/win_rate with score in service + repository      | ✓ SATISFIED | Schema removed legacy fields; service/repo compute and surface score-based metric.                                                                    |
| INSIGHT-SCORE-02  | 75-03                 | Pivot at 0.50                                                      | ✓ SATISFIED | `OPENING_INSIGHTS_SCORE_PIVOT = 0.50`.                                                                                                                |
| INSIGHT-SCORE-03  | 75-01, 75-03          | Effect-size gate (0.45/0.40 weakness, 0.55/0.60 strength) in constants module | ✓ SATISFIED | Constants present; `_classify_row` enforces strict ≤/≥ at exact boundaries; boundary tests cover 0.45, 0.40, 0.55, 0.60, 0.46, 0.54.                  |
| INSIGHT-SCORE-04  | 75-03, 75-04          | Trinomial Wald 95% CI; half-width buckets; pure stdlib             | ✓ SATISFIED | `_compute_confidence` matches D-05 formula; REQUIREMENTS.md amended.                                                                                  |
| INSIGHT-SCORE-05  | 75-01, 75-03          | Drop MIN_GAMES_PER_CANDIDATE to 10                                 | ✓ SATISFIED | Constant updated; SQL HAVING references the constant; repo test renamed `..._floor_at_10`.                                                            |
| INSIGHT-SCORE-06  | 75-02, 75-03, 75-04   | Add confidence + p_value to API; drop loss_rate/win_rate           | ✓ SATISFIED | Schema fields added; service constructor wires them; REQUIREMENTS.md amended.                                                                         |
| INSIGHT-SCORE-07  | 75-01                 | CI consistency test asserts score-based lock-step                  | ✓ SATISFIED | Test rewritten with four assertions; CI-enforced via standard `pytest` collection in `tests/`.                                                       |

All seven Phase 75 requirement IDs from REQUIREMENTS.md are accounted for; no orphaned IDs.

### Anti-Patterns Found

None. No TODO/FIXME/HACK/PLACEHOLDER markers in any of the six touched code files. No empty implementations. No console-log-only handlers. No hardcoded empty data feeding renderers. The two surviving "loss_rate/win_rate" mentions are deliberate historical references in docstrings (`opening_insights.py:43` and `openings_repository.py:535`).

### Human Verification Required

None. Phase 75 is a pure backend phase whose behavior is fully unit/integration-testable; the user-visible frontend consumption of `confidence`/`p_value` is explicitly out of scope (Phase 76 owns that). The roadmap bullet uses the legacy phrase "Wilson 95% half-width" — the trinomial Wald amendment was made in `/gsd-discuss-phase` and reflected in REQUIREMENTS.md (D-05) plus the verifier task description; this is documented and consistent across all artifacts.

### Gaps Summary

No gaps. All seven must-haves verified; all artifacts present and substantive; all key links wired; data flows from DB through repository and service into the API contract; all 58 directly relevant tests pass; ty + ruff clean on every touched module. The Wave 1 / Wave 2 plan ordering produced the documented expected-transient breakage during Wave 1 (broken imports) which Plan 03 resolved — the post-merge state is fully green.

---

_Verified: 2026-04-28T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
