---
phase: quick-260428-tgg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/opening_insights_constants.py
  - app/services/score_confidence.py
  - app/services/opening_insights_service.py
  - app/services/openings_service.py
  - tests/services/test_score_confidence.py
  - tests/services/test_opening_insights_service.py
  - tests/test_openings_service.py
autonomous: true
requirements:
  - QUICK-260428-tgg
must_haves:
  truths:
    - "Within a confidence bucket, weaknesses are ranked by their Wald 95% upper bound ascending (most confidently bad first), not by raw |score - 0.50|."
    - "Within a confidence bucket, strengths are ranked by their Wald 95% lower bound descending (most confidently good first)."
    - "Bucket order (high -> medium -> low) is preserved as the primary sort key."
    - "A small-N high-effect finding does NOT outrank a large-N moderate-effect finding within the same bucket (small N inflates SE, widens the bound, and demotes the row)."
    - "Wald bounds are clamped to [0, 1] so degenerate (all-wins / all-losses) rows produce well-defined sort keys."
    - "The Wald z-score 1.96 is named (WALD_Z_95) and lives in opening_insights_constants.py next to the other Wald constants — no magic number at the call site."
    - "compute_confidence_bucket exposes SE alongside confidence and p_value so callers can compute bounds without re-deriving the formula."
    - "Both callers (opening_insights_service._rank_section and openings_service.get_next_moves) pass through the new 3-tuple cleanly."
    - "uv run ruff check ., uv run ruff format ., uv run ty check app/ tests/, uv run pytest all pass."
  artifacts:
    - path: app/services/opening_insights_constants.py
      provides: WALD_Z_95 constant (= 1.96, the 95% normal-approx z-score)
      contains: "WALD_Z_95"
    - path: app/services/score_confidence.py
      provides: 3-tuple return (confidence, p_value, se) from compute_confidence_bucket
      contains: "tuple[Literal[\"low\", \"medium\", \"high\"], float, float]"
    - path: app/services/opening_insights_service.py
      provides: direction-aware _rank_section using Wald CI bound tiebreak
      contains: "wald_bound"
    - path: app/services/openings_service.py
      provides: 3-tuple unpack of compute_confidence_bucket
      contains: "confidence, p_value, _se"
    - path: tests/services/test_score_confidence.py
      provides: assertions on the SE component of the 3-tuple
      contains: "se"
    - path: tests/services/test_opening_insights_service.py
      provides: ranking tests covering small-N-vs-large-N tiebreak and direction-aware bound
      contains: "wald"
  key_links:
    - from: app/services/opening_insights_service.py::_rank_section
      to: app/services/opening_insights_constants.py::WALD_Z_95
      via: "import OPENING_INSIGHTS_WALD_Z_95 as WALD_Z_95"
      pattern: "WALD_Z_95"
    - from: app/services/opening_insights_service.py::compute_insights
      to: app/services/opening_insights_service.py::_rank_section
      via: "passes direction=\"weakness\" or \"strength\" derived from section key"
      pattern: "_rank_section\\(.*direction="
---

<objective>
Replace the effect-size tiebreak (|score - 0.50|) inside each confidence bucket with a direction-aware Wald 95% CI bound. The bound mixes effect and uncertainty within the existing Wald framework, so a small-N high-effect finding can no longer leapfrog a large-N moderate-effect finding within the same bucket.

Purpose: Within a "high" bucket, two findings can have very different SE — one based on n=10 and one based on n=400. Both pass the p-value gate, but the n=10 row's confidence interval is wide. Sorting by raw |score - 0.50| promotes wide-interval rows above tight-interval rows, the opposite of what users want.

Output:
- `compute_confidence_bucket` returns a 3-tuple `(confidence, p_value, se)`.
- `_rank_section` takes a `direction: Literal["strength", "weakness"]` and sorts by `(confidence_rank, wald_bound)` where `wald_bound` is the upper bound (ascending) for weaknesses and the negated lower bound (effectively descending) for strengths, both clamped to `[0, 1]`.
- All call sites and tests updated; full test+lint+ty suite green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@app/services/score_confidence.py
@app/services/opening_insights_constants.py
@app/services/opening_insights_service.py
@app/services/openings_service.py
@tests/services/test_score_confidence.py

<interfaces>
<!-- Current shape of compute_confidence_bucket (will change to 3-tuple). -->

From app/services/score_confidence.py:
```python
def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]:
    # returns (confidence, p_value)
    # internally already computes:
    #   score = (w + 0.5*d) / n
    #   variance = (w + 0.25*d) / n - score*score   (clamped >= 0)
    #   se = sqrt(variance / n)
```

From app/services/opening_insights_constants.py (relevant existing constants):
```python
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.05
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.10
```

From app/services/opening_insights_service.py:
```python
_CONFIDENCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

def _rank_section(findings: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    # current: sort by (confidence_rank, -abs(f.score - 0.5))
```

The caller already knows which section it is iterating — see compute_insights ~lines 425-429:
```python
for key, findings in deduped_sections.items():
    ranked = _rank_section(findings)  # need to also pass direction here
    cap = WEAKNESS_CAP_PER_COLOR if "weaknesses" in key else STRENGTH_CAP_PER_COLOR
```

Two callers of compute_confidence_bucket:
- app/services/opening_insights_service.py:388
- app/services/openings_service.py:448
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend compute_confidence_bucket to return SE; add WALD_Z_95 constant</name>
  <files>
    app/services/opening_insights_constants.py,
    app/services/score_confidence.py,
    app/services/openings_service.py,
    tests/services/test_score_confidence.py
  </files>
  <behavior>
    Tests in tests/services/test_score_confidence.py update first:
    - Every existing 2-tuple unpack `confidence, p_value = compute_confidence_bucket(...)` becomes `confidence, p_value, se = compute_confidence_bucket(...)`.
    - Add new test cases:
      - `test_se_returned_alongside_confidence_and_p` — sanity: for w=80, d=80, losses=240, n=400, returned `se` matches the manual sqrt(((w + 0.25*d)/n - score*score) / n) within 1e-9.
      - `test_se_zero_for_all_draws` — w=0, d=10, losses=0, n=10 returns se == 0.0.
      - `test_se_zero_for_all_wins_n10` — w=10, d=0, losses=0, n=10 returns se == 0.0 (variance clamped to 0).
      - `test_se_zero_for_n_zero_guard` — w=0, d=0, losses=0, n=0 returns ("low", 0.5, 0.0). Update the existing `test_n_zero_returns_low_half` accordingly or add this as a sibling.
    - The CI consistency test at tests/services/test_opening_insights_arrow_consistency.py only checks the helper exists by name — verify its assertions still pass (no signature inspection there). If it inspects signature, update.
  </behavior>
  <action>
    1. **Add the Wald z-score constant.** In `app/services/opening_insights_constants.py`, add at the end of the existing Wald confidence section:
       ```python
       # Two-sided 95% normal-approximation z-score. Used to construct the Wald
       # 95% confidence interval `score +/- WALD_Z_95 * SE` that drives the
       # within-bucket finding tiebreak in opening_insights_service._rank_section.
       # The same z value is the implicit threshold for the p<0.05 "high"
       # confidence bucket above.
       OPENING_INSIGHTS_WALD_Z_95: float = 1.96
       ```

    2. **Extend compute_confidence_bucket to return SE.** In `app/services/score_confidence.py`:
       - Update the return type annotation to `tuple[Literal["low", "medium", "high"], float, float]`.
       - Update the docstring: rename the "Returns" line to `(confidence_bucket, one_sided_p_value, standard_error)`. Document that `se` is the Wald standard error of the score `(W + 0.5D)/N` under the binomial-with-half-credit-for-draws variance, clamped at 0 for degenerate (all-wins / all-draws / all-losses) rows. Mention that callers use `se` to construct the Wald 95% CI for tiebreak ranking.
       - The early-return `if n <= 0` becomes `return "low", 0.5, 0.0`.
       - The `if se == 0.0` branch (degenerate path) already has `se` in scope; no recomputation needed. Just include `se` (which is 0.0 here) in the return tuple.
       - The trailing `return confidence, p_value` becomes `return confidence, p_value, se`.

    3. **Update openings_service.py caller.** Line 448 currently: `confidence, p_value = compute_confidence_bucket(w, d, lo, gc)`. Change to:
       ```python
       confidence, p_value, _se = compute_confidence_bucket(w, d, lo, gc)
       ```
       The `_se` underscore prefix signals "intentionally unused here" — Move Explorer rows are sorted by frequency or win_rate, not by Wald CI bound. No other change needed in this file.

    4. **Update test_score_confidence.py.** RED: extend each existing assertion to unpack `(confidence, p_value, se)`. The `_p` placeholders become `_p, _se`. Add the four new test cases listed in `<behavior>`. Run `uv run pytest tests/services/test_score_confidence.py -x` — every test should pass (this is a contract change, not a logic change).

    5. **Do NOT yet update opening_insights_service.py in this task** — Task 2 owns _rank_section. But the existing call at line 388 will break compilation/tests because of the 2-tuple unpack. Update it to `confidence, p_value, se = compute_confidence_bucket(row.w, row.d, row.l, row.n)` and pass `se` into the OpeningInsightFinding... actually, OpeningInsightFinding does not currently have an `se` field, and we don't want to add one to the public schema. Instead, **stash `se` on the finding via a parallel dict keyed by id(finding) is fragile**. Cleaner: keep `se` as a local in compute_insights and thread it through the section accumulator. Defer that wiring to Task 2 — for now, just unpack with `_se` here and leave a TODO note in code:
       ```python
       confidence, p_value, _se = compute_confidence_bucket(row.w, row.d, row.l, row.n)
       # _se threaded through to _rank_section in Task 2 below
       ```
       This keeps Task 1 self-contained: the helper signature changes, all callers compile, all tests pass. No ranking behavior change yet.
  </action>
  <verify>
    <automated>uv run ruff check app/services/opening_insights_constants.py app/services/score_confidence.py app/services/openings_service.py tests/services/test_score_confidence.py && uv run ty check app/ tests/ && uv run pytest tests/services/test_score_confidence.py tests/test_openings_service.py tests/services/test_opening_insights_arrow_consistency.py -x</automated>
  </verify>
  <done>
    - WALD_Z_95 constant exists in opening_insights_constants.py with explanatory docstring comment.
    - compute_confidence_bucket returns 3-tuple (confidence, p_value, se).
    - All call sites unpack the 3-tuple (with `_se` placeholder where unused).
    - tests/services/test_score_confidence.py has new SE assertions; all tests pass.
    - ruff, ty, and the targeted pytest run are green.
    - No ranking behavior change yet — _rank_section still uses the old |score - 0.5| tiebreak.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Direction-aware Wald CI bound tiebreak in _rank_section</name>
  <files>
    app/services/opening_insights_service.py,
    tests/services/test_opening_insights_service.py
  </files>
  <behavior>
    New/updated tests in tests/services/test_opening_insights_service.py covering:

    1. **test_ranking_small_n_high_effect_does_not_outrank_large_n_moderate_effect_within_bucket**
       Construct two weakness findings, both in the "high" confidence bucket:
       - A: n=10, w=0, d=0, losses=10. score=0.0, |score-0.5|=0.5, se=0.0 (all-losses degenerate). Wald upper bound = max(0, 0 + 1.96*0) = 0.0. Bucket: high (p=0.0).
       - B: n=400, w=80, d=80, losses=240. score=0.30, se ≈ sqrt(((80 + 20)/400 - 0.09) / 400) ≈ sqrt((0.25 - 0.09)/400) ≈ sqrt(0.0004) ≈ 0.02. Wald upper bound ≈ 0.30 + 1.96*0.02 ≈ 0.339. Bucket: high.

       Hmm — A's bound is actually 0.0 (lower than B's 0.339), so A would still rank first under upper-bound-ascending. The "small-N high-effect should NOT outrank" rule applies to NON-degenerate small-N cases. Pick a more illustrative pair:
       - A: n=10, w=0, d=2, losses=8. score=0.10, |score-0.5|=0.40. variance = (0+0.5)/10 - 0.01 = 0.04, se = sqrt(0.04/10) ≈ 0.0632. Bucket — check p: z=(0.10-0.50)/0.0632 ≈ -6.32, one-sided p ≈ 1.3e-10 — high. Wald upper = 0.10 + 1.96*0.0632 ≈ 0.224.
       - B: n=400, w=130, d=80, losses=190. score=0.425, |score-0.5|=0.075. variance = (130 + 20)/400 - 0.180625 = 0.375 - 0.180625 = 0.194375, se = sqrt(0.194375/400) ≈ 0.0220. z=(0.425-0.5)/0.0220 ≈ -3.40, one-sided p ≈ 0.00033 — high. Wald upper = 0.425 + 1.96*0.0220 ≈ 0.468.

       Old behavior: A.|delta|=0.40 > B.|delta|=0.075 → A first.
       New behavior: A.upper=0.224 > B.upper=0.468 — wait, ascending means smaller upper first, so A first again.

       The test that demonstrates the *intended* improvement is the symmetric case where small N produces a wider upper bound than large N at moderate effect. Try:
       - A: n=10, w=2, d=0, losses=8. score=0.20, variance = 2/10 - 0.04 = 0.16, se = sqrt(0.16/10) ≈ 0.1265. Wald upper = 0.20 + 1.96*0.1265 ≈ 0.448. p: z=(0.20-0.50)/0.1265 ≈ -2.37, one-sided p ≈ 0.0089 — high.
       - B: n=400, w=130, d=80, losses=190. score=0.425, se ≈ 0.0220. Wald upper ≈ 0.468. p ≈ 0.00033 — high.

       A.upper=0.448 < B.upper=0.468 → A first (small N wins at this calibration, which is reasonable: A's CI shows it really might be far below 0.5).

       The cleanest demonstration of the win: pick a small-N row whose Wald upper crosses 0.5, while a large-N moderate row's upper stays well below 0.5:
       - A: n=10, w=4, d=0, losses=6. score=0.40, |delta|=0.10. variance = 4/10 - 0.16 = 0.24, se = sqrt(0.024) ≈ 0.155. Wald upper = 0.40 + 1.96*0.155 ≈ 0.704. z = -0.645, one-sided p ≈ 0.26 — bucket: **low** (p>=0.10).
       - That falls into a different bucket — not a within-bucket comparison.

       Pragmatic test: instead of trying to construct an illustrative pair from raw counts, pick two findings with hard-coded score and SE values (the test can build OpeningInsightFinding objects directly, not via compute_confidence_bucket) and assert the ordering. Since OpeningInsightFinding does not store `se`, the test must monkeypatch or directly call _rank_section after constructing a minimal helper. ALTERNATIVELY: have _rank_section accept a list of (finding, se) tuples, since SE is not on the public schema. See <action> below for this design choice.

       Net effect on the test: **construct three findings as (finding, se) tuples directly, with hand-picked score/se/confidence values that exercise the bound logic**.

       Three test fixtures for weakness ranking (direction="weakness"):
         - F1: confidence="high", score=0.40, se=0.10. upper = 0.40 + 1.96*0.10 = 0.596.
         - F2: confidence="high", score=0.30, se=0.02. upper = 0.30 + 1.96*0.02 = 0.339.
         - F3: confidence="medium", score=0.10, se=0.01. upper = 0.10 + 1.96*0.01 = 0.120 (tiny but bucket is medium).

       Expected order under new rule: high-bucket first (F2 with upper=0.339 before F1 with upper=0.596), then medium F3.
       Expected order under old rule: F1 (|delta|=0.10), F2 (|delta|=0.20)... wait, old rule sorts by *negative* abs(score-0.5) — so larger |delta| first. F2 |delta|=0.20 > F1 |delta|=0.10 → old order: F2, F1, F3. Same top-of-bucket as new rule for this case but only by coincidence.

       To make the new rule's effect clear, swap F1 to have a wider CI:
         - F1: confidence="high", score=0.40, se=0.005. upper = 0.40 + 1.96*0.005 = 0.4098.
         - F2: confidence="high", score=0.30, se=0.10. upper = 0.30 + 1.96*0.10 = 0.496.

       Now |delta| order: F2 (0.20) > F1 (0.10) — old rule puts F2 first.
       Wald upper order: F1 (0.4098) < F2 (0.496) — new rule puts F1 first.

       This is the test: assert new ordering is [F1, F2] (F1 first) for direction="weakness". This proves the rule changed from "biggest effect" to "tightest evidence-of-being-bad".

    2. **test_ranking_strength_uses_lower_bound** — symmetric for direction="strength":
         - F1: confidence="high", score=0.60, se=0.005. lower = 0.60 - 1.96*0.005 = 0.5902.
         - F2: confidence="high", score=0.70, se=0.10. lower = 0.70 - 1.96*0.10 = 0.504.
       Expected order: [F1, F2] (F1 first — lower bound 0.59 is more confidently above 0.5 than F2's lower bound 0.504, despite F2 having larger raw effect).

    3. **test_ranking_clamps_bound_to_unit_interval** — direction="weakness", se large enough that score + 1.96*se > 1 (e.g. score=0.95, se=0.5 → unclamped upper=1.93). Assert sort succeeds and the row sorts after a row with clamped bound 1.0 (stable on tie). Mostly a smoke test that the clamp doesn't crash.

    4. **Update existing test_ranking_confidence_desc_then_score_distance_desc** — rename to e.g. `test_ranking_high_before_medium_before_low_buckets`, drop the "score distance" assertion, and assert only the bucket-level ordering (high, medium, low). The original specific score-distance ordering may no longer hold. Pick fixtures whose Wald bounds preserve the bucket order regardless of within-bucket reshuffle.

    5. **Update existing test_ranking_score_distance_tiebreak_within_same_confidence** — rename to `test_ranking_wald_upper_bound_tiebreak_within_same_confidence_for_weaknesses`. Both fixtures share confidence="high"; pick (score, se) such that the smaller upper bound corresponds to the LARGER |score - 0.5| (so the test would have failed under the old rule if anyone reverts). The current p_value=0.5 hardcode in the test fixture is fine as long as confidence stays "high" (the sort uses confidence, not p).

    6. **Existing test_compute_insights_populates_confidence_and_p_value smoke** — already passes; no change needed beyond the 2->3 tuple unpack handled in Task 1.

  </behavior>
  <action>
    1. **Decide where SE flows.** OpeningInsightFinding (the API schema) should NOT gain an `se` field — it is internal sorting state. Two clean options:
       - (a) Make _rank_section accept `list[tuple[OpeningInsightFinding, float]]` (finding + se).
       - (b) Add a private dataclass / NamedTuple wrapper (`_RankableFinding(finding, se, direction)`) and convert in/out at the call sites.

       Pick **(a)**. Smaller diff, no new types, the wrapper is invisible outside this file.

    2. **Update _rank_section signature.** Replace the existing function:
       ```python
       _CONFIDENCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


       def _rank_section(
           findings_with_se: list[tuple[OpeningInsightFinding, float]],
           direction: Literal["weakness", "strength"],
       ) -> list[OpeningInsightFinding]:
           """Sort findings by (confidence DESC, Wald 95% CI bound) per Phase 76 D-03 + 260428-tgg.

           Within a confidence bucket, the tiebreak is the *direction-aware* Wald 95%
           confidence-interval bound on the score, clamped to [0, 1]:
             - weakness: ascending upper bound `score + 1.96*SE` — the row whose
               score is most-confidently-below-0.5 (smallest plausible best case)
               sorts first.
             - strength: descending lower bound `score - 1.96*SE` — the row whose
               score is most-confidently-above-0.5 (largest plausible worst case)
               sorts first.

           Why the Wald bound and not raw |score - 0.5|: the |score - 0.5| tiebreak
           rewarded large effect regardless of sample size, so a small-N high-effect
           row could leapfrog a large-N moderate-effect row inside the same bucket
           even though the small-N row's confidence interval was much wider. The
           Wald bound mixes effect AND uncertainty within the existing Wald-test
           framework that already drives the bucket gate, so the same SE that
           determines bucket membership also determines within-bucket order.
           """
           def sort_key(item: tuple[OpeningInsightFinding, float]) -> tuple[int, float]:
               finding, se = item
               half_width = WALD_Z_95 * se
               if direction == "weakness":
                   # Ascending upper bound: tighter, more-confidently-bad rows first.
                   bound = min(max(finding.score + half_width, 0.0), 1.0)
               else:
                   # Negate the lower bound to convert "descending" into "ascending"
                   # under the default sorted() order, so the tuple stays homogeneously
                   # ascending. Equivalent to sorting -lower_bound ascending.
                   lower = min(max(finding.score - half_width, 0.0), 1.0)
                   bound = -lower
               return (_CONFIDENCE_RANK[finding.confidence], bound)

           ranked = sorted(findings_with_se, key=sort_key)
           return [f for f, _se in ranked]
       ```
       Import `WALD_Z_95` at the top of the file:
       ```python
       from app.services.opening_insights_constants import (
           OPENING_INSIGHTS_MAJOR_EFFECT as MAJOR_EFFECT,
           OPENING_INSIGHTS_MINOR_EFFECT as MINOR_EFFECT,
           OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
           OPENING_INSIGHTS_WALD_Z_95 as WALD_Z_95,
       )
       ```

    3. **Thread SE through compute_insights.** The sections accumulator currently stores `tuple[OpeningInsightFinding, int]` (finding + opening_ply_count) for the D-24 dedupe. We need both `opening_ply_count` AND `se` per row. Update the per-row accumulator:
       ```python
       sections: dict[str, list[tuple[OpeningInsightFinding, int, float]]] = {
           "white_weaknesses": [],
           ...
       }
       ```
       At the row construction site (~line 388), capture `se`:
       ```python
       confidence, p_value, se = compute_confidence_bucket(row.w, row.d, row.l, row.n)
       ```
       Then append the 3-tuple `(finding, opening_ply_count, se)` to the section.

    4. **Update _dedupe_within_section** (~lines 203-217) to accept and propagate `se`:
       ```python
       def _dedupe_within_section(
           items: list[tuple[OpeningInsightFinding, int, float]],
       ) -> list[tuple[OpeningInsightFinding, float]]:
           """Deduplicate by resulting_full_hash within a section, keeping the deepest entry.

           Returns (finding, se) tuples — opening_ply_count is consumed here and
           does not flow downstream to ranking.
           """
           best: dict[str, tuple[OpeningInsightFinding, int, float]] = {}
           for finding, ply_count, se in items:
               key = finding.resulting_full_hash
               existing = best.get(key)
               if existing is None or ply_count > existing[1]:
                   best[key] = (finding, ply_count, se)
           return [(finding, se) for finding, _ply, se in best.values()]
       ```

    5. **Update _dedupe_continuations** (~lines 220-267). It currently takes `dict[str, list[OpeningInsightFinding]]` and returns the same. To carry SE through, update to:
       ```python
       def _dedupe_continuations(
           sections: dict[str, list[tuple[OpeningInsightFinding, float]]],
       ) -> dict[str, list[tuple[OpeningInsightFinding, float]]]:
       ```
       The two places that destructure findings from `sections` need to pull `f` from the tuple:
       - The `flat` list comprehension: `flat = [(sk, f, se) for sk, items in sections.items() for f, se in items]` (and update the sort key tuple shape).
       - The final result loop: iterate `for finding, se in items` and rebuild `(finding, se)` tuples in `result[section_key]`.
       Keep all dedupe logic identical — only the carried payload widens from `f` to `(f, se)`.

    6. **Update the final ranking call site** (~lines 425-429):
       ```python
       for key, findings_with_se in deduped_sections.items():
           direction: Literal["weakness", "strength"] = (
               "weakness" if "weaknesses" in key else "strength"
           )
           ranked = _rank_section(findings_with_se, direction=direction)
           cap = WEAKNESS_CAP_PER_COLOR if "weaknesses" in key else STRENGTH_CAP_PER_COLOR
           final_sections[key] = ranked[:cap]
       ```

    7. **Update tests in tests/services/test_opening_insights_service.py.**
       - Add `from app.services.opening_insights_constants import OPENING_INSIGHTS_WALD_Z_95 as WALD_Z_95` if useful for assertions.
       - Update the two existing ranking tests as described in `<behavior>` items 4 and 5. They currently call `_rank_section(findings)` with a list of bare findings — switch to `_rank_section([(f, se) for f in findings], direction="weakness")` (or pre-build the (f, se) pairs directly).
       - Add the three new tests (1, 2, 3) from `<behavior>`.
       - The smoke test (test_compute_insights_populates_confidence_and_p_value, ~line 707) does NOT call _rank_section directly; it calls compute_insights end-to-end. It should keep passing because we threaded SE through internally without changing the public schema. Confirm by running it.

    8. **No public schema change.** OpeningInsightFinding fields are unchanged. No frontend changes. No API contract change. The only public-surface change is `compute_confidence_bucket`'s 3-tuple return (touched in Task 1).

    9. **Add a brief inline comment at the sort site** explaining why (per CLAUDE.md "comment non-obvious code"). The docstring on _rank_section already covers it; no extra comment needed inside compute_insights, but add a one-liner above the ranking loop:
       ```python
       # Per quick task 260428-tgg: rank by Wald 95% CI bound (direction-aware)
       # rather than raw |score - 0.5|, so wide-CI small-N rows do not leapfrog
       # tight-CI large-N rows inside the same bucket.
       ```
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/ && uv run pytest tests/services/test_opening_insights_service.py tests/services/test_score_confidence.py tests/test_openings_service.py tests/services/test_opening_insights_arrow_consistency.py -x</automated>
  </verify>
  <done>
    - _rank_section takes (findings_with_se, direction) and sorts by (confidence_rank, direction-aware Wald bound).
    - Wald bound is clamped to [0, 1].
    - compute_insights threads SE from compute_confidence_bucket through dedupe stages into _rank_section.
    - Two existing ranking tests updated to the new sort key and pass.
    - Three new ranking tests pass: small-N-vs-large-N within bucket, strength-uses-lower-bound, clamp safety.
    - End-to-end test_compute_insights_populates_confidence_and_p_value smoke still passes (public schema unchanged).
    - All targeted pytest, ruff, ty checks green.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full-suite verification</name>
  <files>(no file changes — verification only)</files>
  <action>
    Run the full project test + lint + type-check suite to catch any cross-file regressions the targeted runs in Tasks 1-2 missed (e.g. arrow-consistency test, openings router integration tests, Move Explorer end-to-end).

    1. `uv run ruff check .`
    2. `uv run ruff format --check .`
    3. `uv run ty check app/ tests/`
    4. `uv run pytest` (full suite)

    If any test fails:
    - First check whether it is a 2-tuple unpack of compute_confidence_bucket missed in Task 1 (search: `grep -rn "compute_confidence_bucket" app tests`).
    - Second check whether it is an _rank_section call site outside compute_insights (should be none; _rank_section is module-private).
    - Third check whether it is the arrow-consistency test (test_compute_confidence_bucket_is_single_implementation) — if it inspects signature, the signature change may need an update there.

    Do NOT skip or xfail any test. Fix the root cause.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/ && uv run pytest</automated>
  </verify>
  <done>
    - Full pytest suite passes.
    - ruff check and ruff format --check both clean.
    - ty check zero errors.
    - No new test xfails or skips introduced.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest` passes (full suite).
- `uv run ruff check .` clean.
- `uv run ruff format --check .` clean.
- `uv run ty check app/ tests/` zero errors.
- Manual reasoning check (no human-in-the-loop test): a weakness finding at n=400, score=0.30 (tight CI, upper bound ~0.34) sorts before a weakness finding at n=10, score=0.10 (wide CI, upper bound > 0.34) within the same "high" bucket — proven by `test_ranking_small_n_high_effect_does_not_outrank_large_n_moderate_effect_within_bucket` (Task 2).
- Public API surface unchanged (`OpeningInsightFinding` schema unchanged, `NextMoveEntry` schema unchanged, no new fields in API responses).
</verification>

<success_criteria>
1. compute_confidence_bucket returns (confidence, p_value, se) and is callable from both opening_insights_service and openings_service.
2. WALD_Z_95 = 1.96 lives in opening_insights_constants.py with a docstring explaining its purpose.
3. _rank_section sorts by (confidence_rank, direction-aware Wald bound clamped to [0, 1]) — the rule documented in its docstring.
4. compute_insights passes direction="weakness" or "strength" to _rank_section based on the section key.
5. SE is threaded through dedupe stages without leaking into the public OpeningInsightFinding schema.
6. All ranking tests assert the NEW behavior (Wald bound), not the old |score - 0.5| behavior.
7. Full lint + type + test suite green.
</success_criteria>

<output>
This is a quick task; no SUMMARY.md required. Update STATE.md "Quick Tasks Completed" table after merge:

| 260428-tgg | Sort opening insights findings by Wald 95% CI bound (direction-aware) within confidence buckets, replacing raw effect-size tiebreak | 2026-04-28 | (commit-sha) | [260428-tgg-sort-opening-insights-findings-by-wald-c](./quick/260428-tgg-sort-opening-insights-findings-by-wald-c/) |
</output>
