---
phase: 75-backend-score-metric-confidence-annotation
reviewed: 2026-04-28T10:37:30Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app/services/opening_insights_constants.py
  - app/services/opening_insights_service.py
  - app/repositories/openings_repository.py
  - app/schemas/opening_insights.py
  - frontend/src/lib/arrowColor.ts
  - tests/services/test_opening_insights_arrow_consistency.py
  - tests/services/test_opening_insights_service.py
  - tests/repositories/test_opening_insights_repository.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 75: Code Review Report

**Reviewed:** 2026-04-28T10:37:30Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

The score-based metric swap is well-executed. The classifier (`_classify_row`) correctly avoids the IEEE-754 boundary trap documented in its own docstring, the SQL HAVING clause matches the Python boundaries exactly (verified via the integer-row factories used in repository tests), and the trinomial Wald variance/p-value derivation is mathematically sound. The new constants module successfully breaks the would-be circular import. Frontend changes are pure-additive as planned. Test coverage of the new behavior (boundary tests at 0.40/0.45/0.55/0.60, SE=0 degenerate paths, end-to-end smoke for `confidence` + `p_value`) is appropriate.

That said, several quality issues should be addressed before this rolls into a milestone:

1. The repository imports `OPENING_INSIGHTS_MAJOR_EFFECT` purely "for docstring traceability" and silences ruff with `noqa: F401`. This is an anti-pattern that misleads readers and bypasses the linter's purpose.
2. `_replay_san_sequence(list(row.entry_san_sequence or []))` silently falls back to the initial-position FEN when the sequence is empty, contradicting the function's own docstring that says "Never falls back to the initial position (D-34)."
3. The new `OpeningInsightFinding` numeric fields (`score`, `p_value`, `n_games`, `wins`, `draws`, `losses`) ship with no Pydantic range constraints. This is the API boundary; bounds should be enforced.

No security vulnerabilities, no correctness bugs in the classifier or HAVING gate, no data-loss paths.

## Warnings

### WR-01: `_replay_san_sequence` fallback contradicts docstring and D-34

**File:** `app/services/opening_insights_service.py:155-165, 415, 232, 382`
**Issue:** `_replay_san_sequence` is documented as "Never falls back to the initial position (D-34)", but the call sites pass `list(row.entry_san_sequence or [])`. When `row.entry_san_sequence` is `None` or `[]`, `_replay_san_sequence([])` returns `chess.Board().fen()` — i.e. the initial position FEN — silently.

In current production this is unreachable because the CTE filters entries to ply 3..16 and the partial index plus `has_standard_start` guarantee a non-empty SAN prefix, but the contract is still violated and the silent-fallback behavior is exactly what D-34 forbids. If any future SQL change ever lets an empty/`NULL` `entry_san_sequence` through, the service will surface findings labelled with the starting-position FEN instead of dropping them — the same class of bug D-34 was written to prevent.

The same `or []` pattern appears in the parent-lineage walk (`_compute_prefix_hashes(list(r.entry_san_sequence or []))`) and in the schema population for `entry_san_sequence` itself; these all combine to make an empty SAN sequence a soft, silent code path rather than a hard error.

**Fix:**
```python
def _replay_san_sequence(san_sequence: list[str]) -> str:
    if not san_sequence:
        # D-34: never fall back to the initial position. An empty sequence at
        # this point indicates a CTE/repository contract violation upstream.
        raise ValueError(
            "_replay_san_sequence received an empty SAN sequence; "
            "expected entry_ply >= MIN_ENTRY_PLY (3)"
        )
    board = chess.Board()
    for san in san_sequence:
        board.push_san(san)
    return board.fen()
```
And drop the `or []` defensive coercion at every call site so an empty/`None` sequence raises `TypeError` (or the explicit `ValueError` above) rather than silently producing a bogus finding. The top-level `try/except` in `compute_insights` already routes to Sentry with full request context.

---

### WR-02: `OPENING_INSIGHTS_MAJOR_EFFECT` imported with `noqa: F401` "for docstring traceability"

**File:** `app/repositories/openings_repository.py:19-26`
**Issue:** The repository imports a symbol it never references and silences ruff with `# noqa: F401`. The justification ("imported for docstring traceability; SQL gate uses MINOR_EFFECT, Python post-filter uses MAJOR_EFFECT") is incorrect on its own terms — `_classify_row` does not use `OPENING_INSIGHTS_MAJOR_EFFECT` either; it uses the locally-imported alias `MAJOR_EFFECT` from the service module. The import does not aid grep-discoverability (full qualified name is identical regardless of import location) and it actively hides a real lint signal.

This is the kind of defensive-but-meaningless import that decays into actual dead-import drift over time.

**Fix:** Remove the import. If cross-module discoverability is the goal, add a one-line comment near the SQL gate that names the constant:
```python
from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MAX_ENTRY_PLY,
    OPENING_INSIGHTS_MIN_ENTRY_PLY,
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
    OPENING_INSIGHTS_MINOR_EFFECT,
    OPENING_INSIGHTS_SCORE_PIVOT,
)
# Note: the SQL gate uses MINOR_EFFECT only; the major-vs-minor distinction
# is applied in opening_insights_service._classify_row (uses MAJOR_EFFECT).
```

---

### WR-03: Pydantic `OpeningInsightFinding` numeric fields lack range constraints

**File:** `app/schemas/opening_insights.py:60-68`
**Issue:** This is the public API boundary (`POST /api/insights/openings`). The new and existing numeric fields have no validation:

```python
n_games: int          # should be >= MIN_GAMES_PER_CANDIDATE (10)
wins: int             # should be >= 0, <= n_games
draws: int            # should be >= 0, <= n_games
losses: int           # should be >= 0, <= n_games
score: float          # should be in [0.0, 1.0] by construction
p_value: float        # should be in [0.0, 1.0] by erfc semantics
```

CLAUDE.md mandates "leverage Pydantic models for validation" and "type safety" with explicit constraints at system boundaries. Pydantic v2 makes this trivial via `Field(ge=..., le=...)`. Without these, a future bug that produces a negative win count or `score=1.5` will be silently shipped to the frontend instead of caught at response serialization.

**Fix:**
```python
from pydantic import BaseModel, ConfigDict, Field

class OpeningInsightFinding(BaseModel):
    ...
    n_games: int = Field(ge=10)  # gated by SQL HAVING n >= MIN_GAMES_PER_CANDIDATE
    wins: int = Field(ge=0)
    draws: int = Field(ge=0)
    losses: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)
    p_value: float = Field(ge=0.0, le=1.0)
```
(Cross-field `wins + draws + losses == n_games` would need a `model_validator`, optional.)

## Info

### IN-01: Score is computed three times per row in three different idioms

**File:** `app/services/opening_insights_service.py:84, 102, 127`
**Issue:** Three sites compute `score`:
- `_classify_row`: `(row.w + 0.5 * row.d) / row.n`
- `_compute_score`: `(row.w + row.d / 2) / row.n`
- `_compute_confidence`: `(row.w + 0.5 * row.d) / n`

All three are bit-identical for integer inputs in IEEE-754, but the divergent idioms (`0.5 * d` vs `d / 2`) invite future drift, and the helper `_compute_score` is bypassed by the two callers that need it most.

**Fix:** Compute `score` once at the top of the per-row loop in `compute_insights` and pass it into `_classify_row`/`_compute_confidence` as an argument:
```python
score = _compute_score(row)
cls = _classify_row(row, score)
confidence, p_value = _compute_confidence(row, score)
```
This also removes the third copy of the magic literal `0.5`.

---

### IN-02: All-result-equal lines bucket as "high" confidence on n=10

**File:** `app/services/opening_insights_service.py:134-140`
**Issue:** The SE=0 degenerate path returns `("high", ...)` regardless of n. A user with exactly 10 all-loss games on a candidate move will surface as a major weakness with high confidence, which is statistically dishonest (one outlier game flipping result would change the picture). The docstring acknowledges this as an intentional design choice deferred to the upstream `MIN_GAMES_PER_CANDIDATE = 10` floor.

This is a known-and-accepted simplification, but it is worth flagging because n=10 is also the new (lowered) discovery floor — the two simplifications stack. Worst case is "10 all-losses on a single candidate move ⇒ major weakness, high confidence, p_value=0.0" displayed to the user. Whether that is intended product behavior should be confirmed before Phase 76 ships the UI badge.

**Fix:** None required if the product accepts this. If not, the simplest mitigation is a small additive tweak to the SE=0 branch:
```python
if se == 0.0:
    # Degenerate variance — bucket conservatively unless n is large.
    confidence = "high" if n >= 30 else "medium"
    return confidence, (1.0 if score == SCORE_PIVOT else 0.0)
```
Or revisit the floor itself. Recommend leaving as-is and revisiting after Phase 76 telemetry, per the existing comment.

---

### IN-03: `_compute_confidence` recomputes score and variance instead of accepting them

**File:** `app/services/opening_insights_service.py:105-152`
**Issue:** The helper signature `_compute_confidence(row)` couples the helper to the `row` shape. A purer signature `(score: float, w: int, d: int, n: int)` or `(score: float, variance: float, n: int)` would be easier to test in isolation, and removes one of the three score-computation sites.

**Fix:** Refactor along with IN-01 once the callers have a precomputed `score`:
```python
def _compute_confidence(
    score: float, w: int, d: int, n: int,
) -> tuple[Literal["low", "medium", "high"], float]:
    ...
```

---

### IN-04: `arrowColor.ts` exports SCORE_PIVOT/MINOR/MAJOR but `getArrowColor` still uses the old win/loss-rate thresholds

**File:** `frontend/src/lib/arrowColor.ts:21-23, 47-69`
**Issue:** Phase 75 D-12 marks the frontend changes as "pure additive — Phase 76 will rewrite the body". This is intentional and tracked. However, the file's own header comment ("Colors are assigned based on clear thresholds: dark green 60%+ win rate ...") still describes the old win/loss-rate scheme, while three new score-based constants now sit at the top of the file with no JSDoc tying them to the (still-unused) future code path. A new reader will struggle to reconcile the two.

**Fix:** Add a leading-block comment to the new exports clarifying they are dormant for Phase 75:
```typescript
// Score-based thresholds (Phase 75; consumed by Phase 76 once getArrowColor
// body migrates to score-based coloring). Do NOT reference these from the
// existing percentage-based getArrowColor() body — the migration is a single
// atomic rewrite in Phase 76 to keep arrow color and insight classification
// in lock-step.
export const SCORE_PIVOT = 0.50;
export const MINOR_EFFECT_SCORE = 0.05;
export const MAJOR_EFFECT_SCORE = 0.10;
```
The existing comment on lines 17-20 partially does this; folding the file header into the same paragraph would tie the dormant constants to the existing scheme more clearly.

---

_Reviewed: 2026-04-28T10:37:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
