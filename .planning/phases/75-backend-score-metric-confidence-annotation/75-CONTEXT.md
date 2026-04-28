# Phase 75: Backend — score metric and confidence annotation - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning
**Requirements:** INSIGHT-SCORE-01, INSIGHT-SCORE-02, INSIGHT-SCORE-03, INSIGHT-SCORE-04 (amended), INSIGHT-SCORE-05, INSIGHT-SCORE-06 (amended), INSIGHT-SCORE-07

<domain>
## Phase Boundary

Backend-only refinement of the v1.13 `opening_insights_service` (Phase 70). Three coupled changes inside the existing pipeline:

1. **Metric swap.** Replace the `loss_rate`/`win_rate` classifier with chess score `(W + 0.5·D)/N` against a 0.50 pivot. Effect-size gate at `|score − 0.50| ≥ 0.05` (minor) / `≥ 0.10` (major), strict boundaries, symmetric on both sides.
2. **Confidence annotation.** Compute a trinomial Wald 95% confidence interval per surviving finding and bucket the half-width into `low / medium / high`. Surfaced as a new `confidence` field on the `OpeningInsightFinding` API contract; the raw two-sided p-value is also surfaced for tooltip use.
3. **Discovery floor.** Drop `MIN_GAMES_PER_CANDIDATE` from 20 to 10. The confidence badge replaces the prior hard floor — borderline-evidence findings surface with `(low)` rather than being filtered out.

No schema changes. No new endpoint. No router changes. The HAVING clause in `query_opening_transitions()` swaps from a loss/win-rate gate to a score-based effect-size gate. Confidence math is post-aggregation in Python. The CI consistency test (`tests/services/test_opening_insights_arrow_consistency.py`) is updated alongside `frontend/src/lib/arrowColor.ts` to assert score-based effect-size constants instead of percent thresholds.

Two REQUIREMENTS.md amendments emerge from this discussion (apply at Phase 75 commit time, see D-05 and D-09):

1. **INSIGHT-SCORE-04** — replace "Wilson 95% confidence interval" with "trinomial Wald 95% confidence interval". Bucket rule moves from direction-based (LB-vs-pivot/threshold tests) to half-width-based: `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`.
2. **INSIGHT-SCORE-06** — extend the API contract addition to include both `confidence: "low" | "medium" | "high"` AND `p_value: float` (two-sided test of observed score vs 0.50).

Phase 76 (frontend) consumes the new fields. The CI consistency test (Phase 75 scope) asserts effect-size lock-step against `arrowColor.ts`; confidence bucket constants are NOT in the CI test (Phase 75 ships them as backend-only, Phase 76 decides whether moves-list rows compute confidence locally or fetch a new payload field).

</domain>

<decisions>
## Implementation Decisions

### Metric and classifier (INSIGHT-SCORE-01, INSIGHT-SCORE-02, INSIGHT-SCORE-03)

- **D-01:** Classification metric is chess score `score = (W + 0.5·D) / N`. Replaces `loss_rate` (weakness side) and `win_rate` (strength side). Single metric, draw-rate-robust, matches what chess actually uses. Already documented in `.planning/notes/opening-insights-v1.14-design.md`; this CONTEXT.md just locks the implementation specifics.
- **D-02:** Pivot is fixed at **0.50**. No user-baseline shrinkage (rejected during `/gsd-explore`; see design note for full rationale — chess.com / lichess matchmaking already centers users near 50%, the existing opponent-strength filter handles drift cases).
- **D-03:** Effect-size thresholds, strict boundaries, symmetric:
  - Minor weakness: `score ≤ 0.45`
  - Major weakness: `score ≤ 0.40`
  - Minor strength: `score ≥ 0.55`
  - Major strength: `score ≥ 0.60`
  - No asymmetry (eliminates the prior `loss_rate > 0.55` strict-greater-than asymmetry).
- **D-04:** `MIN_GAMES_PER_CANDIDATE` drops from 20 to 10. Borderline-evidence findings surface with `confidence = "low"` (handled by D-05 / D-06) rather than being filtered out.

### Confidence formula and buckets (INSIGHT-SCORE-04 — amended)

- **D-05 (amends INSIGHT-SCORE-04):** Confidence is computed via the **trinomial Wald 95% confidence interval**, not a binomial Wilson interval on score. Wilson on `(W + 0.5·D)/N` would treat the score as a Bernoulli proportion and assume per-game variance `score · (1 − score)`, which over-states uncertainty when draws are common. The trinomial Wald uses the actual per-game variance:

  ```python
  # per-game variance: E[X²] - score² where X ∈ {0, 0.5, 1}
  variance = (w + 0.25 * d) / n - score * score
  se = sqrt(variance / n)
  half_width = 1.96 * se
  ```

  This is the standard formula for chess match statistics (BayesElo, Ordo). Two-sided p-value from the same Z-statistic:

  ```python
  z = (score - 0.50) / se
  p_value = math.erfc(abs(z) / math.sqrt(2))   # standard-normal two-sided
  ```

  Pure Python `math` only — no scipy dependency.

- **D-06:** Confidence buckets, half-width-based, decoupled from severity:
  - `high` if `half_width ≤ 0.10`
  - `medium` if `half_width ≤ 0.20`
  - `low` otherwise
  Bucket boundaries live in `opening_insights_constants.py` (see D-11) so they can be retuned against real data without touching service code.

### Computation location (Phase 75 implementation)

- **D-07:** The trinomial Wald half-width and bucket assignment run **post-aggregation in Python**, inside `compute_insights()`, as a pure helper over `Row` attrs (`row.w`, `row.d`, `row.l`, `row.n`). Reasons: (a) the formula and bucket boundaries are policy and belong co-located with the other thresholds in `opening_insights_constants.py`; (b) the helper is trivially unit-testable; (c) the number of surviving rows after the HAVING filter is small (tens), so no perf concern. SQL stays clean and only handles the effect-size gate.
- **D-08:** The SQL HAVING clause in `query_opening_transitions()` is rewritten from the current `n ≥ 20 AND (win_rate > 0.55 OR loss_rate > 0.55)` to:

  ```sql
  HAVING n_games >= 10
     AND (
         (wins + 0.5 * draws) / n_games <= 0.45
         OR (wins + 0.5 * draws) / n_games >= 0.55
     )
  ```

  The minor-effect threshold (0.05) drives the SQL gate — major findings (effect ≥ 0.10) are a post-filter assertion in Python. The `OR` keeps the gate simple and symmetric. `MIN_GAMES_PER_CANDIDATE = 10` is the new floor (D-04).

### API contract (INSIGHT-SCORE-06 — amended)

- **D-09 (amends INSIGHT-SCORE-06):** `OpeningInsightFinding` schema changes:
  - **REMOVE** `loss_rate: float` and `win_rate: float`. Drop cleanly — the only consumer is the v1.14 frontend in this same milestone (Phase 76), so a deprecation window adds dead weight to the contract.
  - **ADD** `confidence: Literal["low", "medium", "high"]`. Derived per D-05 / D-06.
  - **ADD** `p_value: float`. Two-sided p-value for `H0: score = 0.50`, computed via the same Z-statistic that drives the half-width (D-05). Surfaced for a Phase 76 tooltip on the confidence badge.
  - **KEEP** `score: float` (already present per Phase 70 D-06; promoted from informative-only to canonical metric).
  - **KEEP** `severity: Literal["minor", "major"]` (effect-size). Stays orthogonal to `confidence` (precision) — frontend renders both.
  - **KEEP** `wins`, `draws`, `losses`, `n_games`. Frontend WDL bars consume these directly; nothing changes for the literal-data display.

### Constants module (INSIGHT-SCORE-03, INSIGHT-SCORE-05, INSIGHT-SCORE-07)

- **D-10:** `app/services/opening_insights_constants.py` is rewritten. After Phase 75:

  ```python
  # Entry-position bounds — unchanged from Phase 70
  OPENING_INSIGHTS_MIN_ENTRY_PLY: int = 3
  OPENING_INSIGHTS_MAX_ENTRY_PLY: int = 16

  # Discovery floor — was 20, dropped per INSIGHT-SCORE-05 / D-04
  OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 10

  # Score classifier — replaces LIGHT_THRESHOLD/DARK_THRESHOLD
  OPENING_INSIGHTS_SCORE_PIVOT: float = 0.50
  OPENING_INSIGHTS_MINOR_EFFECT: float = 0.05   # |score - pivot| >= 0.05 → minor
  OPENING_INSIGHTS_MAJOR_EFFECT: float = 0.10   # >= 0.10 → major

  # Confidence buckets — half-width thresholds (D-06)
  OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH: float = 0.10
  OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH: float = 0.20
  ```

  `DARK_THRESHOLD` (currently in `opening_insights_service.py`) is removed; both effect-size constants now live in the constants module so the CI consistency test (D-12) reads everything from one place.

- **D-11:** `_classify_row()` in `opening_insights_service.py` is rewritten to operate on score:

  ```python
  def _classify_row(row) -> tuple[Literal["weakness", "strength"], Literal["minor", "major"]] | None:
      score = (row.w + 0.5 * row.d) / row.n
      delta = score - SCORE_PIVOT  # 0.50
      if delta <= -MINOR_EFFECT:
          severity = "major" if delta <= -MAJOR_EFFECT else "minor"
          return "weakness", severity
      if delta >= MINOR_EFFECT:
          severity = "major" if delta >= MAJOR_EFFECT else "minor"
          return "strength", severity
      return None
  ```

  Strict `≤` / `≥` boundaries (D-03). The function signature stays identical so the rest of the pipeline (`compute_insights`, dedupe, ranking) is unchanged.

### CI consistency test and frontend pre-additions (INSIGHT-SCORE-07)

- **D-12 (Phase 75 → Phase 76 ordering — option (b)):** `frontend/src/lib/arrowColor.ts` gains pure-additive named exports as part of Phase 75. The `getArrowColor()` body is NOT touched (Phase 76 rewrites it). Additions:

  ```typescript
  // Score-based thresholds (Phase 75; consumed by Phase 76)
  export const SCORE_PIVOT = 0.50;
  export const MINOR_EFFECT_SCORE = 0.05;
  export const MAJOR_EFFECT_SCORE = 0.10;
  // MIN_GAMES_FOR_COLOR is already 10 in this file — leave as is, the CI test
  // now asserts it matches OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE.
  ```

  This decouples the merge ordering: Phase 75 ships, the CI test passes immediately against the new constants, and Phase 76 then refactors `getArrowColor()` body to consume them.

- **D-13:** `tests/services/test_opening_insights_arrow_consistency.py` is rewritten to assert:
  1. `SCORE_PIVOT` matches `OPENING_INSIGHTS_SCORE_PIVOT`.
  2. `MINOR_EFFECT_SCORE` matches `OPENING_INSIGHTS_MINOR_EFFECT`.
  3. `MAJOR_EFFECT_SCORE` matches `OPENING_INSIGHTS_MAJOR_EFFECT`.
  4. `MIN_GAMES_FOR_COLOR` matches `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE`.

  The old `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` assertions are removed (those constants stay in `arrowColor.ts` for the duration of Phase 75 because `getArrowColor()` still references them; they become dead and are removed by Phase 76).

  **Confidence bucket constants are NOT in the CI test.** Phase 75 ships confidence as a backend payload field; the moves-list `(low)/(medium)/(high)` indicator (Phase 76 INSIGHT-UI-03) is a Phase 76 question — either the moves explorer endpoint adds confidence to its payload, or the frontend computes it locally from `n/w/d/l`. Phase 76 decides and extends the test scope if needed.

### Out-of-scope clarifications

- **D-14:** No changes to `query_top_openings_sql_wdl` (used by the moves explorer endpoint, not by insights). Confidence/p-value on moves-list rows is a Phase 76 decision and may or may not require backend work.
- **D-15:** No changes to `_dedupe_continuations`, `_dedupe_within_section`, attribution pipeline, or section caps. The metric swap is internal to `_classify_row` and the HAVING clause; everything downstream is metric-agnostic.
- **D-16:** No new Alembic migration. Phase 70's `ix_gp_user_game_ply` partial index still serves the rewritten HAVING clause (the index is on `(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17` — independent of the WDL gate).

</decisions>

<deferred>
## Deferred Ideas

- **Backward-compat window for `loss_rate`/`win_rate`** — discussed but not selected as a gray area. The default ("drop cleanly") is locked per D-09. If a future external consumer of `/api/insights/openings` emerges before this change ships, revisit before Phase 75 PR merge.
- **Confidence on moves-list rows** — Phase 76 question. Two paths: (a) backend extends moves explorer endpoint payload with `confidence` and `p_value` per move, (b) frontend computes locally from existing `n/w/d/l`. Decide during Phase 76 `/gsd-discuss-phase`.
- **Calibrating the 0.10 / 0.20 half-width buckets against real data** — current values are first-principles defaults that map ~n=50 to medium↔high boundary and ~n=20 to low↔medium boundary at score=0.6 with typical 30% draw rate. Recheck after Phase 76 ships and we have telemetry.
- **Engine-eval / population-relative weakness signals** — already out of scope per design note. Not v1.14 work.

</deferred>

<canonical_refs>
## Canonical References

Downstream agents (researcher, planner) MUST read these:

- `.planning/notes/opening-insights-v1.14-design.md` — locked design (metric, pivot, rejected alternatives). Authoritative for the conceptual model.
- `.planning/REQUIREMENTS.md` — INSIGHT-SCORE-01..07 (note D-05 / D-09 amend INSIGHT-SCORE-04 and INSIGHT-SCORE-06; apply at Phase 75 commit time).
- `.planning/milestones/v1.14-ROADMAP.md` — Phase 75 success criteria.
- `.planning/milestones/v1.13-phases/70-backend-opening-insights-service/70-CONTEXT.md` — Phase 70 D-01..D-34 (existing pipeline reference).

Code touched by Phase 75:

- `app/services/opening_insights_constants.py` — full rewrite per D-10.
- `app/services/opening_insights_service.py` — `_classify_row` rewrite (D-11), new `_compute_confidence` helper (D-05 / D-06), `compute_insights` wires confidence + p_value into `OpeningInsightFinding` construction (D-09). Remove `DARK_THRESHOLD` constant.
- `app/repositories/openings_repository.py` — `query_opening_transitions` HAVING clause rewrite (D-08); update docstring at lines 526-545.
- `app/schemas/opening_insights.py` — `OpeningInsightFinding` field changes (D-09): remove `loss_rate`/`win_rate`, add `confidence`, add `p_value`.
- `frontend/src/lib/arrowColor.ts` — pure-additive new exports per D-12 (no function-body changes).
- `tests/services/test_opening_insights_arrow_consistency.py` — full rewrite per D-13.
- `tests/services/test_opening_insights_service.py` — update existing tests for the new classifier + new fields. Add unit tests for `_compute_confidence` covering boundary cases (half-width = 0.10 exact, = 0.20 exact, n=10 floor).

</canonical_refs>

<code_context>
## Reusable Assets and Patterns

- **`apply_game_filters` shared filter** (`app/repositories/query_utils.py`) — Phase 75 doesn't touch it; just keep using it.
- **Phase 70 `ix_gp_user_game_ply` partial index** — remains the workhorse for the rewritten HAVING. No new migration.
- **`OpeningInsightFinding` Pydantic schema** — surgical field changes only; the rest of the pipeline (attribution, dedupe, ranking, section caps, four-section response shape) is metric-agnostic and untouched.
- **`opening_insights_constants.py` import path** — already imported by both the service and the repository (avoids circular import per its module docstring). Phase 75 reuses this seam.
- **CI consistency test pattern** — existing regex-extract-from-source approach in `test_opening_insights_arrow_consistency.py` works as-is; only the names and values being asserted change.

## Anti-patterns to avoid

- **Don't push the trinomial Wald formula into SQL** — locked Python-side per D-07. Keeping the formula in one language (Python) avoids SQL/Python drift on the variance expression.
- **Don't keep `loss_rate` / `win_rate` "for one milestone"** — locked drop-cleanly per D-09. The only consumer ships in the same milestone.
- **Don't compute confidence in the SQL HAVING gate** — the HAVING is for effect-size only (D-08). Confidence is annotation, not filter.
- **Don't break the CI test by removing `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` from `arrowColor.ts` in Phase 75** — the existing `getArrowColor()` body still uses them. Phase 76 removes them.

</code_context>

---

## Next Step

`/clear` then:

`/gsd-plan-phase 75`
