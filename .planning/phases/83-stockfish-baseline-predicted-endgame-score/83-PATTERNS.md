# Phase 83: Stockfish-baseline predicted endgame score — Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 17 (3 NEW + 14 MODIFY)
**Analogs found:** 17 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| NEW `app/services/eval_utils.py` | utility (pure math) | transform | `app/services/eval_confidence.py` (pure math sibling); sign-flip block in `app/services/endgame_service.py:195-204` | role-match + same-pattern excerpt |
| NEW `tests/services/test_eval_utils.py` | test (unit, pure-function) | request-response | `tests/services/test_eval_confidence.py` | exact |
| MODIFY `app/services/endgame_service.py` (~line 1670) | service (aggregator) | batch transform over rows | Self-analog: existing entry-eval block at `endgame_service.py:1674-1712` | exact (mirror) |
| MODIFY `app/repositories/endgame_repository.py` (~793-841) | repository (SQL builder) | CRUD/read | Self-analog: existing `bucket_stmt` already SELECTs `eval_cp` and `eval_mate` — **no SQL change required** | exact |
| MODIFY `app/schemas/endgames.py` (~107-140) | schema (Pydantic v2) | wire format | Self-analog: existing `entry_eval_*` fields at `endgames.py:124-140` | exact (mirror) |
| MODIFY `app/services/score_confidence.py` | utility (statistical math, refactor) | transform | Self-analog: existing Wilson math at `score_confidence.py:141-143` (factor out into shared helper) | exact (extract method) |
| MODIFY `tests/services/test_endgame_service.py` (~3850-3945) | test (integration, aggregator) | request-response | Self-analog: existing entry-eval test class at lines 3850-3945 | exact (mirror) |
| MODIFY `frontend/src/components/charts/EndgameStartVsEndSection.tsx` | component (chart section) | render | Self-analog: existing tile-2 block at lines 157-201 | exact (mirror + restructure) |
| NEW `frontend/src/components/popovers/AchievableScorePopover.tsx` (or co-located) | component (popover wrapper) | render | `frontend/src/components/insights/ScoreConfidencePopover.tsx` (wrap the underlying popover with custom body) | role-match (wrapper pattern) |
| MODIFY `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | test (RTL) | request-response | Self-analog (extend) | exact |
| MODIFY `app/services/endgame_zones.py` | config (registry) | lookup | Self-analog: existing `"entry_eval_pawns"` ZoneSpec entry at `endgame_zones.py:141-150` | exact (mirror) |
| MODIFY `frontend/src/generated/endgameZones.ts` | config (auto-generated) | lookup | Self-analog: regenerate via `scripts/gen_endgame_zones_ts.py` | n/a (generated) |
| MODIFY `app/services/insights_service.py` `_findings_endgame_start_vs_end` (~443-502) | service (LLM payload emitter) | event-driven | Self-analog: existing 2-finding emitter at lines 443-502 | exact (mirror) |
| MODIFY `app/services/insights_llm.py` (`_PROMPT_VERSION` at line 66) | config (version constant) | n/a | Self-analog: line 66 with appended changelog string | exact |
| MODIFY `app/prompts/endgame_insights.md` | prompt asset (markdown) | n/a | Self-analog: glossary entry for `entry_eval_pawns` at lines 323-327 + subsection block at lines 260-286 | exact (mirror) |
| MODIFY `.claude/skills/benchmarks/SKILL.md` | skill (operator-only markdown) | n/a | Self-analog: existing Section 0 ("Endgame score") at SKILL.md:310-419 | exact (mirror new section) |
| NEW `reports/benchmarks-YYYY-MM-DD.md` | report (markdown output) | n/a | `reports/benchmarks-2026-05-10.md` Section 0 (lines 31-99) | exact (mirror) |

## Pattern Assignments

### `app/services/eval_utils.py` (NEW, pure math utility)

**Analog:** `app/services/endgame_service.py:195-204` (sign convention) + `app/services/eval_confidence.py` (pure-math sibling module shape — `import math`, top-level constants, typed pure functions).

**Sign-flip pattern to mirror exactly** (`endgame_service.py:195-204`):
```python
sign = 1 if user_color == "white" else -1

if eval_mate is not None:
    # Mate score: a positive value means the side that is to-move has mate,
    # but the raw white-perspective convention treats eval_mate > 0 as white winning.
    user_eval: int = sign * (1_000_000 if eval_mate > 0 else -1_000_000)
elif eval_cp is not None:
    user_eval = sign * eval_cp
```

**Apply (per RESEARCH §"Code Examples — Sigmoid math"):**
```python
"""Lichess winning-chances sigmoid — Stockfish eval to expected score in [0, 1]."""
import math
from typing import Literal

# Lichess accuracy / winning-chances sigmoid scale (fitted on 2300+ rapid games).
LICHESS_K: float = 0.00368208


def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float:
    sign = 1 if user_color == "white" else -1
    user_eval_cp = sign * eval_cp
    return 1.0 / (1.0 + math.exp(-LICHESS_K * user_eval_cp))


def eval_mate_to_expected_score(
    eval_mate: int,
    user_color: Literal["white", "black"],
) -> float:
    user_is_mating = (eval_mate > 0 and user_color == "white") or (
        eval_mate < 0 and user_color == "black"
    )
    return 1.0 if user_is_mating else 0.0
```

**Conventions to copy:**
- Module docstring with source citation (Lichess accuracy doc) — mirrors `score_confidence.py:1-43` style.
- Named constant `LICHESS_K` at module level (no magic number inside function body).
- `Literal["white", "black"]` on `user_color` (CLAUDE.md type-safety rule; matches `endgame_zones.py:25` style).
- Explicit return-type annotation on every function (CLAUDE.md ty-compliance rule).
- No I/O, no DB — pure stdlib only.

---

### `tests/services/test_eval_utils.py` (NEW, pure-function unit tests)

**Analog:** `tests/services/test_eval_confidence.py` (exact match — pure math, same `tests/services/` directory).

**Imports & scaffolding pattern** (`test_eval_confidence.py:1-26`):
```python
"""Unit tests for app.services.eval_confidence.compute_eval_confidence_bucket.

Bucketing rule under test (unified two-sided standard, 260505):
  ...
"""

import math
import pytest

from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.opening_insights_constants import EVAL_CONFIDENCE_MIN_N
```

**Class-grouped test style** (RESEARCH §"Code Examples — Unit test scaffolding"):
- `class TestSigmoid:` and `class TestMate:` per D-03 — class grouping mirrors RESEARCH example and is also used in other pure-math test files.
- `pytest.approx(..., abs=1e-9)` for float comparisons (matches `test_eval_confidence.py:33-46`).
- Plain `def test_*` functions inside the class — no fixtures needed (pure functions).
- Each test name self-describes the case (`test_centered_at_zero`, `test_sign_convention_white`, `test_mate_for_black_user`).

**Test cases to write** (from D-03 + RESEARCH §Pitfall 1):
- `test_centered_at_zero` — `eval_cp_to_expected_score(0, "white") == 0.5`
- `test_sign_convention_white` / `test_sign_convention_black` — `+100 cp` → 0.591 white / 0.409 black
- `test_white_black_symmetry` — `f(+100, "white") + f(+100, "black") == 1.0`
- `test_saturation_high` / `test_saturation_low` — `±1500 cp` → `> 0.99` / `< 0.01`
- `test_mate_for_white_user` / `test_mate_against_white_user`
- `test_mate_for_black_user` / `test_mate_against_black_user` (covers Pitfall 1)

---

### `app/services/endgame_service.py` (MODIFY, aggregator extension at ~line 1670)

**Analog (self):** existing entry-eval aggregator at `endgame_service.py:1674-1712`.

**Existing loop pattern to mirror** (lines 1680-1693):
```python
for row in bucket_rows:
    # Pitfall 3: explicit None checks. Never use `or` for numeric defaulting.
    if row.eval_mate is not None:  # ty: ignore[unresolved-attribute]
        continue  # mate-excluded per D-07
    if row.eval_cp is None:  # ty: ignore[unresolved-attribute]
        continue  # NULL eval excluded
    sign = 1 if row.user_color == "white" else -1  # ty: ignore[unresolved-attribute]
    signed_cp = float(sign * row.eval_cp)  # ty: ignore[unresolved-attribute]
    eval_sum += signed_cp
    eval_sumsq += signed_cp * signed_cp
    eval_n += 1
```

**Wire-format gating pattern to mirror** (lines 1699-1712):
```python
# Pitfall 5: gate the wire-format p-value to None when below the reliability
# threshold. Surfacing 1.0 would conflate "no data" with "definitely H0".
entry_eval_p_value: float | None = p_eval_raw if eval_n >= 10 else None
entry_eval_mean_pawns = mean_cp / 100.0 if eval_n > 0 else 0.0
entry_eval_ci_low_pawns: float | None
entry_eval_ci_high_pawns: float | None
if eval_n >= 2:
    entry_eval_ci_low_pawns = (mean_cp - ci_half_cp) / 100.0
    entry_eval_ci_high_pawns = (mean_cp + ci_half_cp) / 100.0
else:
    entry_eval_ci_low_pawns = None
    entry_eval_ci_high_pawns = None
```

**Apply (NEW expected-score sibling block — per RESEARCH §Pattern 2):**
```python
# Per Phase 83 D-04, D-06, D-07. Sibling to the entry-eval aggregator above.
EVAL_CLIP_MAX_CP = 2000  # D-07, no magic number

ex_sum = 0.0
ex_n = 0
for row in bucket_rows:
    if row.eval_mate is not None:  # ty: ignore[unresolved-attribute]
        # D-06: mate INCLUDED here (unlike entry-eval). Routed through mate helper.
        ex = eval_mate_to_expected_score(row.eval_mate, row.user_color)  # ty: ignore[unresolved-attribute]
        ex_sum += ex
        ex_n += 1
    elif row.eval_cp is not None:  # ty: ignore[unresolved-attribute]
        if abs(row.eval_cp) >= EVAL_CLIP_MAX_CP:  # D-07
            continue
        ex = eval_cp_to_expected_score(row.eval_cp, row.user_color)  # ty: ignore[unresolved-attribute]
        ex_sum += ex
        ex_n += 1
    # both NULL -> skip per D-06 cohort filter

entry_expected_score = ex_sum / ex_n if ex_n > 0 else 0.0
# Wilson test vs 50% via the new (score, n) helper — see score_confidence.py refactor.
_conf_x, p_ex_raw, _se = compute_score_confidence_from_mean(entry_expected_score, ex_n)
entry_expected_score_p_value: float | None = p_ex_raw if ex_n >= 10 else None
if ex_n >= 2:
    ci_low, ci_high = wilson_bounds(entry_expected_score, ex_n)
else:
    ci_low = ci_high = None  # type: ignore[assignment]
```

Append the five new fields to the `EndgamePerformanceResponse(...)` constructor call at lines 1722-1732.

**Constants to reuse / introduce:**
- `EVAL_CLIP_MAX_CP = 2000` — extract as module-level constant (CLAUDE.md "no magic numbers"). Place next to existing `EVAL_ADVANTAGE_THRESHOLD = 100` (line 166).

---

### `app/repositories/endgame_repository.py` (~793-841)

**Analog (self):** existing `bucket_stmt` at lines 803-841.

**Existing SELECT already returns `eval_cp` and `eval_mate`** (lines 822-833):
```python
bucket_stmt = (
    select(
        Game.played_at,
        Game.platform,
        Game.time_control_bucket,
        Game.user_color,
        Game.white_rating,
        Game.black_rating,
        entry_subq.c.entry_eval_cp.label("eval_cp"),
        entry_subq.c.entry_eval_mate.label("eval_mate"),
        Game.result,
    )
    ...
)
```

**Action:** Confirm in Plan 2 that no SQL change is required (RESEARCH explicitly verified — line 311 in RESEARCH.md: "NO CHANGE (SQL already returns eval_cp + eval_mate)"). If a planner spike reveals a missing column, extend the SELECT list following the same `entry_subq.c.<name>.label(...)` style.

---

### `app/schemas/endgames.py` (~107-140)

**Analog (self):** existing Phase 81 `entry_eval_*` field block at lines 124-140.

**Pattern to mirror exactly** (lines 121-140):
```python
# Phase 81 (D-11): entry-eval aggregation for "Endgame Start vs End" twin-tile section.
# Defaults are required so existing call sites that build the response without these
# fields (tests, prior callers) keep working — see Pitfall 7 in 81-RESEARCH.md.
entry_eval_mean_pawns: float = 0.0
"""Avg Stockfish eval at endgame entry, signed from user's perspective, in pawns. 0.0 when n=0."""

entry_eval_n: int = 0
"""Count of games contributing to entry_eval_mean_pawns. Mate scores and NULL evals excluded; per-game (deduped over multi-class entry_rows)."""

entry_eval_p_value: float | None = None
"""Wald-z two-sided p-value of mean vs 0 cp. None when entry_eval_n < 10 (D-05 reliability gate)."""
...
```

**Apply (NEW Phase 83 block — same shape, terse docstrings per memory `feedback_wilson_chess_score.md`):**
```python
# Phase 83 (D-21): Stockfish-baseline achievable score for "Where you start" tile.
# Defaults match the Phase 81 D-11 safe-empty pattern so existing call sites keep working.
entry_expected_score: float = 0.0
"""Mean per-game expected score from endgame-entry eval, via Lichess sigmoid (mate→0/1). 0.0 when n=0."""

entry_expected_score_n: int = 0
"""Count of games contributing to entry_expected_score. Mate INCLUDED (D-06); NULL evals excluded; |eval_cp| < 2000 clip applied."""

entry_expected_score_p_value: float | None = None
"""Two-sided p-value vs 50%. None when entry_expected_score_n < 10."""

entry_expected_score_ci_low: float | None = None
"""Lower bound of 95% Wilson CI. None when entry_expected_score_n < 2."""

entry_expected_score_ci_high: float | None = None
"""Upper bound of 95% Wilson CI. None when entry_expected_score_n < 2."""
```

**Do NOT** editorialize the methodology in docstrings (memory: `feedback_wilson_chess_score.md`). Keep it descriptive ("Two-sided p-value vs 50%"), not prescriptive ("Wilson test, refactored to accept float means…").

---

### `app/services/score_confidence.py` (MODIFY — factor Wilson math)

**Analog (self):** existing Wilson test at lines 141-143.

**Existing math to factor out** (`score_confidence.py:141-143`):
```python
se_null = math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)
z = (score - SCORE_PIVOT) / se_null
p_value = math.erfc(abs(z) / math.sqrt(2.0))
```

**Apply (NEW private helper per RESEARCH "Critical methodology note"):**
```python
def _wilson_score_test_vs_half(score: float, n: int) -> tuple[float, float]:
    """Return (p_value, se_null) for two-sided Wilson score-test of H0: score == 0.5.

    Pure math — no bucketing, no edge-case clamp. Callers gate on n <= 0.
    """
    se_null = math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)
    z = (score - SCORE_PIVOT) / se_null
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return p_value, se_null


def compute_score_confidence_from_mean(
    score: float, n: int,
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Bucketing/gating identical to `compute_confidence_bucket` but for a float (mean, n)."""
    if n <= 0:
        return "low", 1.0, 0.0
    p_value, _se_null = _wilson_score_test_vs_half(score, n)
    if n < CONFIDENCE_MIN_N:
        return "low", p_value, 0.0
    if p_value < CONFIDENCE_HIGH_MAX_P:
        return "high", p_value, 0.0
    if p_value < CONFIDENCE_MEDIUM_MAX_P:
        return "medium", p_value, 0.0
    return "low", p_value, 0.0
```

Refactor `compute_confidence_bucket` to delegate the Wilson math through `_wilson_score_test_vs_half` (single-source the math; do not duplicate). Its public signature stays `(w, d, losses, n)` for backward compat.

**Conventions to preserve:**
- Module docstring at top documenting the test math (mirror existing top-of-file block).
- `Literal["low", "medium", "high"]` return-type annotation (matches existing).
- `SCORE_PIVOT`, `CONFIDENCE_MIN_N`, `CONFIDENCE_HIGH_MAX_P`, `CONFIDENCE_MEDIUM_MAX_P` already imported — reuse.
- Add a sibling test class in `tests/services/test_score_confidence.py` for `compute_score_confidence_from_mean` mirroring `test_n_below_gate_returns_low_even_with_strong_evidence` shape (lines 32-46).

---

### `tests/services/test_endgame_service.py` (MODIFY ~3850-3945)

**Analog (self):** existing entry-eval test class at lines 3854-3944.

**Pattern to mirror** (lines 3854-3865, 3880-3909):
```python
def test_empty_bucket_rows_yields_defaults(self) -> None:
    resp = _get_endgame_performance_from_rows(
        endgame_rows=[], non_endgame_rows=[], bucket_rows=[],
    )
    assert resp.entry_eval_n == 0
    assert resp.entry_eval_mean_pawns == 0.0
    assert resp.entry_eval_p_value is None
    ...

def test_sign_flip_for_black_users(self) -> None:
    bucket_rows = [
        self._bucket(game_id=i, user_color="black", eval_cp=200) for i in range(10)
    ]
    ...
    assert resp.entry_eval_mean_pawns == pytest.approx(-2.0)

def test_mate_row_excluded_from_aggregation(self) -> None:
    bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
    bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=5))
    ...
    assert resp.entry_eval_n == 10  # mate row dropped
```

**Apply (NEW sibling cases for entry_expected_score — at least these per RESEARCH §Pitfall 3):**
- `test_entry_expected_score_empty_defaults` — n=0, score=0.0, p_value=None, ci None.
- `test_entry_expected_score_n_nine_p_value_gated` — n=9, score computed, p_value None.
- `test_entry_expected_score_centered_when_eval_zero` — 10 rows at eval_cp=0, score ≈ 0.5, p_value ≈ 1.0.
- `test_entry_expected_score_sign_flip_black` — 10 rows at eval_cp=+200 black-user, score < 0.5.
- `test_entry_expected_score_mate_INCLUDED` (Pitfall 3 inversion) — mate-for-user row counts as 1.0, mate-against as 0.0. Asserts `entry_expected_score_n == entry_eval_n + mate_count`.
- `test_entry_expected_score_eval_cp_clip` — `|eval_cp| >= 2000` rows dropped.
- `test_entry_expected_score_p_value_gated_below_n_ten` — wire-format gate (line 3946 analog).

Use the same `self._bucket(...)` / `self._wdl_rows(...)` fixture helpers already in the test class.

---

### `frontend/src/components/charts/EndgameStartVsEndSection.tsx` (MODIFY — 2×2 restructure)

**Analog (self):** existing tile-2 block at lines 157-201.

**Existing tile-2 score bullet pattern to mirror** (lines 158-201):
```tsx
<div className="charcoal-texture rounded-md p-4" data-testid="tile-endgame-score">
  <h3 className="text-base font-semibold mb-2">What you do with it</h3>
  {showTile2Chart ? (
    <div className="grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">Endgame score:</span>
        <span className="ml-auto font-semibold"
              style={scoreColor ? { color: scoreColor } : undefined}
              data-testid="endgame-score-value">
          {`${(score * 100).toFixed(1)}%`}
        </span>
        <ScoreConfidencePopover level={scoreLevel} pValue={scorePValueForPopover}
                                score={score} gameCount={totalGames}
                                testId="endgame-score-popover-trigger" />
      </span>
      <div className="min-w-0 tabular-nums">
        <MiniBulletChart value={score}
                         center={SCORE_BULLET_CENTER}
                         neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                         neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                         domain={scoreBulletDomain()}
                         ciLow={clampScoreCi(scoreCiLow)} ciHigh={clampScoreCi(scoreCiHigh)}
                         barColor="neutral"
                         ariaLabel={`Endgame score: ${(score * 100).toFixed(1)}%`} />
      </div>
    </div>
  ) : (
    <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
  )}
</div>
```

**Existing tile-1 color-gate derivation pattern to mirror** (lines 68-74) — apply the same triad to the new "Achievable score" bullet:
```tsx
const evalLevel = deriveLevel(data.entry_eval_p_value, data.entry_eval_n);
const evalZoneHex = endgameEntryEvalZoneColor(data.entry_eval_mean_pawns);
const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
const showTile1Chart = data.entry_eval_n >= MIN_GAMES_FOR_RELIABLE_STATS;
```

**Apply (per RESEARCH §Pattern 4 + §"Code Examples — Frontend tile interior"):**
- Wrap each tile body in a `<div className="flex flex-col gap-4">` 2-row stack (preserves the existing outer `lg:grid-cols-2` — only tile interior changes per D-12).
- Add three new derived values for the achievable bullet: `achievableLevel`, `achievableZoneHex` (via the NEW `entryExpectedScoreZoneColor` helper from regenerated `endgameZones.ts`), `achievableShowZoneFontColor`, `achievableColor`, `showAchievableChart`.
- Lift `MiniWDLBar` import: `import { MiniWDLBar } from '@/components/stats/MiniWDLBar';` (D-13 — the path is `@/components/stats/MiniWDLBar`, not `EndgamePerformanceSection`).
- Top of tile-2: render `<MiniWDLBar win_pct={data.endgame_wdl.win_pct} draw_pct={data.endgame_wdl.draw_pct} loss_pct={data.endgame_wdl.loss_pct} />` with surrounding label-row matching the tile-1 conventions.

**Testid naming (Browser Automation Rules):** kebab-case, component-prefixed:
- `achievable-score-value`
- `achievable-score-popover-trigger`
- `endgame-wdl-bar` (the new tile-2 top-row WDL slot; the underlying `MiniWDLBar` already exposes `mini-wdl-bar`)
- Keep existing `tile-entry-eval`, `tile-endgame-score`, `entry-eval-value`, `endgame-score-value`.

**Mobile order:** Preserve DOM order matching desktop top-then-bottom within each tile (D-12). No mobile-specific stacking override required.

---

### `frontend/src/components/popovers/AchievableScorePopover.tsx` (NEW, thin wrapper)

**Analog:** `frontend/src/components/insights/ScoreConfidencePopover.tsx` (entire file, 97 lines).

**Pattern (existing ScoreConfidencePopover structure to wrap, lines 30-97):**
```tsx
export function ScoreConfidencePopover({ level, pValue, score, gameCount, testId, ... }) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => { hoverTimeout.current = setTimeout(() => setOpen(true), 100); };
  const handleMouseLeave = () => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); setOpen(false); };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span role="button" tabIndex={0} className="..." aria-label={ariaLabel}
              data-testid={testId} onMouseEnter={...} onMouseLeave={...}>
          <HelpCircle className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content side="top" sideOffset={4} ...>
          <WdlConfidenceTooltip level={level} pValue={pValue} score={score} gameCount={gameCount} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
```

**Apply (per RESEARCH §"Code Examples" + Open Question 1):** Build `AchievableScorePopover` as a thin wrapper. Two options, planner to pick:

1. **Wrapper component (RECOMMENDED — RESEARCH preference):** copy the ScoreConfidencePopover hover-handling and PopoverPrimitive scaffolding; replace `<WdlConfidenceTooltip ... />` body with a custom D-10 body block ("This is what a 2300+ rated player would score from your endgame-entry positions, via the Lichess winning-chances sigmoid. The Lichess curve is fitted on 2300+ rapid games — scoring below this baseline from positive evals is normal at lower ratings and is not a flaw. Compare against your achieved Endgame score in the other tile."). Use this only for the "Achievable score" bullet trigger.

2. **Optional `bodyCopy?: ReactNode` prop:** extend `ScoreConfidencePopover`. Higher coupling, churns the existing tile-2 popover signature — rejected by RESEARCH.

**Constraints:** No `—` em-dash per CLAUDE.md "Em-dashes sparingly"; the example copy above already uses commas/periods. No "underperformance" / "fall short" / "below your potential" framing (D-10 explicit forbidden words).

---

### `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx`

**Analog (self):** lines 1-80 (existing scaffolding) and remaining 16 test cases.

**Existing scaffolding to preserve** (lines 23-79):
- `vi.mock('@/components/charts/MiniBulletChart', ...)` spy pattern — extend by also spying on the new `MiniWDLBar` if any prop assertions are needed (otherwise leave the real component; it has `data-testid="mini-wdl-bar"`).
- `beforeAll` setting up `matchMedia` and `ResizeObserver` stubs — unchanged.
- `afterEach(() => { cleanup(); vi.clearAllMocks(); })` — unchanged.

**Apply (extend with cases for D-08, D-09, D-11):**
- `renders achievable-score bullet when entry_expected_score_n >= 10`
- `renders "Not enough data yet" inside tile-1 row 2 when entry_expected_score_n < 10` (independent from tile-1 row 1 entry-eval gate)
- `paints achievable-score color when zone != neutral AND p < 0.05`
- `does not paint achievable-score color when sig but inside neutral band` (Phase 82 D-12 gate carried forward)
- `renders MiniWDLBar in tile-2 top row` (assert `data-testid="mini-wdl-bar"` present once in tile-2 region — note: `data-testid` already exists once in the existing table below, so use `within(tile2)` scoping)
- `achievable-score popover trigger has stable data-testid`

Use `within(screen.getByTestId('tile-entry-eval'))` and `within(screen.getByTestId('tile-endgame-score'))` to scope assertions to the right tile when querying by shared selectors.

---

### `app/services/endgame_zones.py`

**Analog (self):** existing `"entry_eval_pawns"` entry at lines 141-150 + `MetricId` Literal at lines 30-53.

**Existing `MetricId` Literal pattern** (lines 30-53):
```python
MetricId = Literal[
    "score_gap",
    "entry_eval_pawns",            # Phase 82 D-04: new endgame_start_vs_end Tile 1
    "endgame_score",               # Phase 82 D-03: ...
    ...
]
```

**Existing ZoneSpec entry to mirror** (lines 141-150):
```python
"entry_eval_pawns": ZoneSpec(
    # Editorial tightening from benchmark IQR (±0.75) to ±0.50 —
    # half-a-pawn average swing at endgame entry is narratable. Single
    # global band justified (TC max d=0.22, ELO max d=0.28 per
    # benchmarks-2026-05-10.md §3 — both "review", not "keep separate").
    # Unit: signed pawns.
    typical_lower=-0.50,
    typical_upper=0.50,
    direction="higher_is_better",
),
```

**Apply:**
- Add `"entry_expected_score",` to the `MetricId` Literal list (with a comment `# Phase 83 D-17: new endgame_start_vs_end Tile 1 row 2 — achievable score`).
- Add new `ZoneSpec` entry in `ZONE_REGISTRY` with bounds **filled in by Plan 4** from the new `reports/benchmarks-YYYY-MM-DD.md` section. Comment block must cite the report date + collapse-verdict reasoning + any editorial tightening (D-15 / memory `feedback_zone_band_judgement.md`). Direction: `"higher_is_better"`.

Example shape (bounds TBD by Plan 4):
```python
"entry_expected_score": ZoneSpec(
    # Phase 83 D-14: pooled benchmark calibration from reports/benchmarks-YYYY-MM-DD.md §X.
    # Collapse verdict: TC d_max=<>, ELO d_max=<> → single global band.
    # Editorial: <if tightened, cite IQR vs band rationale per memory feedback_zone_band_judgement.md>.
    # Unit: expected score on the 0–1 W+0.5D scale, centered at 0.5.
    typical_lower=<TBD by Plan 4>,
    typical_upper=<TBD by Plan 4>,
    direction="higher_is_better",
),
```

---

### `frontend/src/generated/endgameZones.ts`

**Analog (self):** auto-generated file; regenerate via `uv run python scripts/gen_endgame_zones_ts.py`.

**Apply:** No hand-edit. After Plan 4 lands the new `ZoneSpec` in `endgame_zones.py`, run the codegen script and commit the regenerated `.ts` file in the same commit (RESEARCH §Pitfall 5). CI fails on drift.

**Downstream consumer:** Plan 3 imports the regenerated `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN`, `ENTRY_EXPECTED_SCORE_NEUTRAL_MAX`, and `entryExpectedScoreZoneColor` from this file (per RESEARCH §"Knip runs in CI" constraint — the new exports must be imported by `EndgameStartVsEndSection.tsx` to avoid unused-export warnings). Verify the generator emits these exports following the existing `endgameEntryEvalZoneColor` helper shape in `frontend/src/lib/endgameEntryEvalZones.ts:40-44`.

---

### `app/services/insights_service.py` `_findings_endgame_start_vs_end` (~443-502)

**Analog (self):** existing 2-finding emitter at lines 443-502.

**Existing finding-build pattern to mirror** (lines 458-478):
```python
n_eval = perf.entry_eval_n
entry_eval = perf.entry_eval_mean_pawns
if n_eval < 10:
    tile1 = _empty_finding("endgame_start_vs_end", window, "entry_eval_pawns")
else:
    eval_quality = sample_quality("endgame_start_vs_end", n_eval)
    tile1 = SubsectionFinding(
        subsection_id="endgame_start_vs_end",
        parent_subsection_id=None,
        window=window,
        metric="entry_eval_pawns",
        value=entry_eval,
        zone=assign_zone("entry_eval_pawns", entry_eval),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=n_eval,
        sample_quality=eval_quality,
        is_headline_eligible=eval_quality != "thin",
        dimension=None,
    )
```

**Apply (per RESEARCH §Pattern 3):** Add `tile3` for `entry_expected_score`, mirroring the same shape (per D-19: no `verdict` field, `dimension=None`, `trend="n_a"`, `is_headline_eligible = quality != "thin"`, sample-size gate `entry_expected_score_n >= 10`):
```python
n_ex = perf.entry_expected_score_n
if n_ex < 10:
    tile3 = _empty_finding("endgame_start_vs_end", window, "entry_expected_score")
else:
    ex = perf.entry_expected_score
    ex_quality = sample_quality("endgame_start_vs_end", n_ex)
    tile3 = SubsectionFinding(
        subsection_id="endgame_start_vs_end",
        parent_subsection_id=None,
        window=window,
        metric="entry_expected_score",
        value=ex,
        zone=assign_zone("entry_expected_score", ex),
        trend="n_a",
        weekly_points_in_window=0,
        sample_size=n_ex,
        sample_quality=ex_quality,
        is_headline_eligible=ex_quality != "thin",
        dimension=None,
    )

return [tile1, tile2, tile3]
```

Update the docstring on `_findings_endgame_start_vs_end` ("…→ TWO findings" → "…→ THREE findings (entry_eval_pawns, endgame_score, entry_expected_score)").

---

### `app/services/insights_llm.py` (`_PROMPT_VERSION` at line 66)

**Analog (self):** line 66.

**Existing pattern to mirror** (line 66 — prepend-style changelog):
```python
_PROMPT_VERSION = "endgame_v24"  # v24 (260510-ugj): tightened last_3mo narration anchors — ... v23 (260510 endgame_start_vs_end): wire Phase 81 entry-eval and endgame-score metrics ... v22 (260503 eval-proxy cutover): ...
```

**Apply (D-20):** Bump to `"endgame_v25"` and prepend a one-line changelog entry. Keep the entire historical changelog string intact behind it (the existing pattern — every prior `vN` block is preserved chronologically). Example:
```python
_PROMPT_VERSION = "endgame_v25"  # v25 (YYMMDD entry_expected_score): wire Stockfish-baseline achievable score (Lichess sigmoid) into the endgame_start_vs_end subsection alongside entry_eval_pawns and endgame_score. New ENTRY_EXPECTED_SCORE_ZONES from /benchmarks-YYYY-MM-DD.md. LLM narrates the achievable-vs-achieved gap as the headline diagnostic with entry_eval_pawns as the explanatory unit. v24 (260510-ugj): tightened last_3mo ...
```

**Cache invalidation:** automatic — `_PROMPT_VERSION` participates in cache key at line 1892 (`prompt_version=_PROMPT_VERSION`). No manual flush.

---

### `app/prompts/endgame_insights.md`

**Analog (self):** glossary entry at lines 323-327 + subsection block at lines 260-286.

**Existing glossary entry to mirror** (lines 323-327):
```markdown
- **entry_eval_pawns** (UI label: "Endgame entry eval"): user's mean Stockfish evaluation at endgame entry in pawns, signed user-perspective. ... Higher is better.
  - Scale: signed decimal pawns (e.g. `+0.62` = "entering endgames 0.62 pawns ahead on average"). Render as signed one-decimal value with the unit "pawns" (e.g. "+0.6 pawns"). Do NOT convert to centipawns.
  - Cohort typical band: **±0.50 pawns** (pooled benchmark-calibrated band; editorial tightening from IQR ±0.75 to ±0.50 ...).
  - The tile on the UI uses a significance test (Welch t-test vs H0 = 0 cp). The LLM does NOT receive the sig-test outcome — narrate strictly from `zone` + `sample_quality` + the `[near edge]` suffix for borderline cases. Do not mention p-values.
  - Emitted in subsection `endgame_start_vs_end`, `dimension=None`.
```

**Apply (NEW glossary entry — D-17, structure must match the entry_eval_pawns shape):**
```markdown
- **entry_expected_score** (UI label: "Achievable score"): per-user mean Stockfish-baseline expected score from endgame-entry positions, on the 0-100% W+0.5D scale. Derivation: Lichess winning-chances sigmoid `1 / (1 + exp(-0.00368208 * cp))` applied to signed user-perspective `eval_cp`; mate positions map directly to 0 or 1 (mate-for-user = 1.0; mate-against-user = 0.0). Mate positions ARE included in this cohort (unlike `entry_eval_pawns`). Higher is better.
  - Scale: whole-number percentage in `[0, 100]`. Attach `%` when narrating (e.g. `mean=58` → "58%").
  - Cohort typical band: **<TBD from Plan 4>** (pooled benchmark-calibrated band; see reports/benchmarks-YYYY-MM-DD.md §X).
  - The tile on the UI uses a Wilson test vs 50%. The LLM does NOT receive the sig-test outcome — narrate strictly from `zone` + `sample_quality` + `[near edge]`.
  - Framing: this is what a **2300+ rated player** would score from your endgame-entry positions. The Lichess curve is fitted on 2300+ rapid games, so scoring below this baseline from positive evals is **normal at lower ratings and is not a flaw**. Do NOT use the words "underperformance", "fall short", "below your potential", or any synonym that frames the gap as a personal failing. Describe the gap descriptively (e.g. "X% below the engine ceiling for positions like these"); for sub-2300 users the gap is rating-tilt by default.
  - Emitted in subsection `endgame_start_vs_end`, `dimension=None`.
```

**Existing subsection block to extend** (lines 260-286): currently documents the 2-tile setup→execution pair. Add a third paragraph block per D-18 explaining the achievable-vs-achieved gap as the headline diagnostic and giving worked example narrations (CONTEXT.md D-18 provides exact strings to lift). Maintain the existing 2×2 zone narration patterns; add a "Three-finding case" subblock explaining the headline ordering logic (Claude's Discretion item: lead with the gap when dominant; lead with entry_eval when entry_eval dominant).

**Final wording polish allowed during implementation** (CONTEXT.md "Claude's Discretion").

---

### `.claude/skills/benchmarks/SKILL.md`

**Analog (self):** existing Section 0 ("Endgame score") at lines 310-419.

**Existing canonical CTE shape to mirror** (lines 335-401 — `selected_users` + `endgame_game_ids` + `rows` + `per_user` + `per_user_excl_sparse` + final SELECT):
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
...
per_user_excl_sparse AS (
  -- Sparse-cell exclusion mirrors §1–§6 universal handling
  SELECT * FROM per_user
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
```

**Output structure to mirror** (lines 406-417): 5×4 cell table → TC marginal → ELO marginal → pooled overall → recommendations (cohort neutral band = pooled `[p25, p75]`, with sanity check on equal-footing filter) → collapse verdict (TC d_max + ELO d_max).

**Apply (NEW section per D-14):** Add a new section ("Section X — Stockfish-baseline expected score at endgame entry") modelled on Section 0. Same canonical CTE pattern, same sparse-cell exclusion, same equal-footing filter. The per-user metric replaces `eg_score = avg(score)` with per-user mean over per-game `expected_score`, where per-game `expected_score` is computed via:
```sql
CASE
  WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) > 0 THEN 1.0
  WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) < 0 THEN 0.0
  WHEN entry_eval_cp IS NOT NULL AND abs(entry_eval_cp) < 2000
       THEN 1.0 / (1.0 + exp(-0.00368208 * (entry_eval_cp * color_sign)))
  ELSE NULL  -- exclude from cohort
END
```
where `color_sign = CASE WHEN g.user_color = 'white' THEN 1 ELSE -1 END` (same shape Section 2 already uses for Conv/Recov classification at lines 655-668).

Apply the Plan 4 deliverables format per Section 0's recommendations subsection. Don't forget the `bic.status='completed'` filter (memory: `project_benchmark_outliers_unfiltered.md`).

---

### `reports/benchmarks-YYYY-MM-DD.md` (NEW)

**Analog:** `reports/benchmarks-2026-05-10.md` Section 0 ("Endgame score", lines 31-99).

**Pattern to mirror exactly** (lines 31-99):
1. Section header `## X. Stockfish-baseline expected score at endgame entry`
2. One-line definition.
3. `### Currently set in code` — list the new constants (`ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX`) once Plan 4 has locked them; pre-calibration this is blank.
4. `### Cell table — per-user expected_score p25 / p50 / p75 (n)` — 5×4 grid identical layout to the existing Section 0 table.
5. `### TC marginal (excl. sparse)` — 4 rows.
6. `### ELO marginal (excl. sparse)` — 5 rows.
7. `### Pooled overall` — single row with `n_users / mean / p05 / p25 / p50 / p75 / p95`.
8. `### Recommendations` — bullet list including sanity check on equal-footing filter (offset from 0.5), cohort neutral band from pooled `[p25, p75]`, per-ELO stratification check (pooled IQR width vs ELO-marginal `p50` spread).
9. `### Collapse verdict` — TC `d_max` + ELO `d_max` per the canonical < 0.2 collapse / 0.2-0.5 review / ≥ 0.5 keep-separate thresholds, plus a heatmap of per-user `p50` across (ELO × TC).

Use the same per-cell formatting (`p25 / p50 / p75 (n)` with `*` footnote for sparse `(2400, classical)`).

**Date stamp:** the YYYY-MM-DD in the filename must match today's date when Plan 4 runs (consistent with `reports/benchmarks-2026-05-10.md` naming convention).

---

## Shared Patterns

### Sign-flip for user-perspective eval
**Source:** `app/services/endgame_service.py:195-204` (`_classify_endgame_bucket`).
**Apply to:** `app/services/eval_utils.py` (both functions); `app/services/endgame_service.py` aggregator extension (new ex_sum loop).
```python
sign = 1 if user_color == "white" else -1
```
This pattern is also baked into the existing entry-eval aggregator at line 1689 and into the benchmark CTE color_sign expression at SKILL.md lines 655+.

### Sample-size gate (≥10) and wire-format p_value gating
**Source:** `app/services/endgame_service.py:1699-1702`.
**Apply to:** new `entry_expected_score_p_value` gating in the aggregator; new `tile3` finding in `_findings_endgame_start_vs_end`; new RTL test `showAchievableChart = data.entry_expected_score_n >= MIN_GAMES_FOR_RELIABLE_STATS`.
```python
entry_eval_p_value: float | None = p_eval_raw if eval_n >= 10 else None
```
This gate matches `MIN_GAMES_FOR_RELIABLE_STATS = 10` shared between backend (`CONFIDENCE_MIN_N`, `EVAL_CONFIDENCE_MIN_N`) and frontend (`MIN_GAMES_FOR_RELIABLE_STATS` from `lib/theme`).

### Schema default empty-value pattern (Phase 81 D-11 Pitfall 7)
**Source:** `app/schemas/endgames.py:124-140`.
**Apply to:** all five new `entry_expected_score*` fields on `EndgamePerformanceResponse`.
```python
entry_eval_mean_pawns: float = 0.0
entry_eval_n: int = 0
entry_eval_p_value: float | None = None
```
Safe-empty defaults keep existing call sites (tests, prior callers) working without explicit updates.

### Tile color rule `(zone != neutral) AND p < 0.05` (Phase 82 D-12)
**Source:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:72-73, 91-92`.
**Apply to:** the new "Achievable score" bullet — derive `achievableShowZoneFontColor = isConfident(achievableLevel) && achievableIsInColoredZone`. Same triad as tile-1 and tile-2.
```tsx
const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
```

### Zone registry single source of truth (Phase 63 D-01)
**Source:** `app/services/endgame_zones.py:130-228` (`ZONE_REGISTRY`) → `scripts/gen_endgame_zones_ts.py` → `frontend/src/generated/endgameZones.ts`.
**Apply to:** Plan 4 must add `ENTRY_EXPECTED_SCORE_ZONES` to the Python registry then regenerate the TS file. CI fails on drift.

### Browser-automation `data-testid` convention
**Source:** CLAUDE.md "Browser Automation Rules"; existing testids at `EndgameStartVsEndSection.tsx` (tile-entry-eval, entry-eval-value, endgame-score-value, etc.).
**Apply to:** every new interactive element in Plan 3:
- `achievable-score-value` (the percent text)
- `achievable-score-popover-trigger` (the HelpCircle icon)
- `endgame-wdl-bar` or rely on the underlying `mini-wdl-bar` testid (already present in `MiniWDLBar.tsx:16`); pick the wrapping div when scoping needed.

### "No magic numbers" — named module constants
**Source:** CLAUDE.md "Coding Guidelines"; `endgame_service.py:166` (`EVAL_ADVANTAGE_THRESHOLD = 100`).
**Apply to:** `LICHESS_K = 0.00368208` in `eval_utils.py`; `EVAL_CLIP_MAX_CP = 2000` in `endgame_service.py` (sibling to `EVAL_ADVANTAGE_THRESHOLD`).

### `Literal["white", "black"]` over bare `str` (CLAUDE.md ty-compliance)
**Source:** CLAUDE.md "Coding Guidelines"; `endgame_zones.py:25` (`Zone = Literal["weak", "typical", "strong"]`).
**Apply to:** both functions in `eval_utils.py`; the existing `user_color` parameter at `_classify_endgame_bucket` currently takes `str` — for new code, prefer `Literal["white", "black"]`.

### `# ty: ignore[unresolved-attribute]` for SQL Row access
**Source:** `endgame_service.py:1683-1690` (every `row.<col>` access tagged with the pragma).
**Apply to:** new bucket_rows loop in the aggregator extension.

### Em-dashes sparingly (CLAUDE.md "Communication Style")
**Apply to:** popover body copy (`AchievableScorePopover.tsx`); the new glossary entry and subsection block in `endgame_insights.md`; the new `reports/benchmarks-YYYY-MM-DD.md` narrative. Use commas, periods, parentheses instead.

## No Analog Found

None. Every file in this phase has a strong (exact or role-match) analog in the existing codebase. Phase 83 is incremental plumbing on top of Phase 81/82.

## Metadata

**Analog search scope:**
- `app/services/` (eval_utils, endgame_service, endgame_zones, insights_service, insights_llm, score_confidence, eval_confidence)
- `app/schemas/` (endgames)
- `app/repositories/` (endgame_repository)
- `app/prompts/` (endgame_insights.md)
- `frontend/src/components/charts/` (EndgameStartVsEndSection, EndgamePerformanceSection, MiniBulletChart)
- `frontend/src/components/insights/` (ScoreConfidencePopover, BulletConfidencePopover)
- `frontend/src/components/stats/` (MiniWDLBar)
- `frontend/src/lib/` (endgameEntryEvalZones, scoreBulletConfig, theme)
- `frontend/src/generated/` (endgameZones.ts)
- `tests/services/` (test_eval_confidence, test_score_confidence)
- `tests/` (test_endgame_service)
- `.claude/skills/benchmarks/` (SKILL.md)
- `reports/` (benchmarks-2026-05-10.md)

**Files scanned:** 17 source files + 3 test files.
**Pattern extraction date:** 2026-05-11.
