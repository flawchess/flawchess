# Phase 76: Frontend score coloring, confidence badges, label reframe — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 17 (5 backend new/modified, 7 frontend new/modified, 5 test new/modified)
**Analogs found:** 17 / 17 (every file has a strong in-tree analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/score_confidence.py` | service utility (NEW) | pure transform (counts → bucket+p) | `app/repositories/query_utils.py` (shared utility module pattern) + `app/services/opening_insights_service.py:105-152` (verbatim formula source) | exact (migration) |
| `app/services/opening_insights_service.py` | service (MIGRATION) | request-response | self lines 105-152 + 322-331 — replace import + `_rank_section` body | exact |
| `app/services/openings_service.py` | service (EXTENSION) | request-response | self lines 354-468 — extend per-row aggregation loop (439-460) | exact |
| `app/repositories/openings_repository.py` | repository (call-site verify) | DB read | unchanged — `query_next_moves` already returns w/d/l/n | n/a (no edit expected) |
| `app/schemas/openings.py` (`NextMoveEntry`) | schema (EXTENSION) | API contract | `app/schemas/opening_insights.py:39-81` `OpeningInsightFinding` (already declares score+confidence+p_value with same Pydantic v2 idioms) | exact |
| `frontend/src/lib/arrowColor.ts` | utility (REWRITE — body + signature) | pure transform | self (`getArrowColor` lines 39-69) — keep imports/exports, swap internals | exact |
| `frontend/src/lib/openingInsights.ts` | utility (CLEANUP + new constant) | pure transform | self (existing exports `getSeverityBorderColor`, `trimMoveSequence`); InfoPopover-children pattern from `MoveExplorer.tsx:166-175` | exact |
| `frontend/src/types/insights.ts` | type catch-up | API mirror | self lines 69-88; `app/schemas/opening_insights.py:39-81` (Python source of truth) | exact |
| `frontend/src/types/api.ts` (`NextMoveEntry`) | type extension | API mirror | self lines 93-105; `app/schemas/openings.py:185-198` (Python source of truth) | exact |
| `frontend/src/components/move-explorer/MoveExplorer.tsx` | component (EXTENSION — column + mute + signature call-site) | request-response render | self lines 161-181 (table head) + 207-220 (`MoveRow` props) + 222-253 (mute/tint logic). Also `InfoPopover` consumer at line 166 | exact |
| `frontend/src/components/insights/OpeningFindingCard.tsx` | component (EXTENSION — prose + line + tooltip + mute) | render | self lines 55-64 (proseLine) + 66-93 (Tooltip-around-button at lines 68 & 80) | exact |
| `frontend/src/components/insights/OpeningInsightsBlock.tsx` | component (EXTENSION — 4 InfoPopover icons) | render | self lines 198-209 (section `<h3>`); `MoveExplorer.tsx:163-176` for the `<h?> + InfoPopover` pattern | exact |
| `tests/services/test_score_confidence.py` (NEW) | test (NEW) | unit | `tests/services/test_opening_insights_service.py:201-272` (lift verbatim) | exact (lift) |
| `tests/services/test_opening_insights_arrow_consistency.py` (D-22 extend) | test (EXTENSION) | unit / regex | self full file (existing 4 regex-extracted assertions) | exact |
| `tests/services/test_opening_insights_service.py` (D-03 sort) | test (UPDATE) | unit | self lines 635-684 (existing `test_ranking_severity_desc_then_n_games_desc`) — rewrite for new key | exact |
| `tests/test_openings_service.py` (D-05 next-move fields) | test (EXTENSION) | unit | self existing fixtures + `_seed_game` helper at top of file | exact |
| `frontend/src/lib/arrowColor.test.ts` (REWRITE) | test (rewrite) | unit | self full file (existing boundary-style tests, signature now `(winPct, lossPct, gameCount, hovered)`) | exact (signature swap) |
| `frontend/src/lib/openingInsights.test.ts` (REWRITE) | test (rewrite) | unit | self lines 92-105 (stale-constant assertions to remove) | role-match |
| `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` (EXT) | test (extension) | component | self full file; `makeEntry` fixture at lines 20-35 | exact |
| `frontend/src/components/insights/OpeningFindingCard.test.tsx` (REWRITE prose) | test (rewrite) | component | self lines 28-50 (`makeFinding`), 56-102 (prose tests), 156-188 (link tests stay) | exact |
| `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` (EXT) | test (extension) | component | self full file; `makeFinding` fixture at lines 46-68 | exact |

## Pattern Assignments

### `app/services/score_confidence.py` (service utility, NEW MODULE)

**Analog A (module shape):** `app/repositories/query_utils.py` — single shared-helper module pattern. CLAUDE.md: "Never duplicate filter logic in individual repositories" — Phase 76 D-06 extends the same principle to confidence math.

**Analog B (formula body to migrate verbatim):** `app/services/opening_insights_service.py:105-152` (the existing `_compute_confidence`).

**Module-docstring + import pattern** (copy from `query_utils.py:1-10`):
```python
"""Shared query utilities for repository filter operations."""

import datetime
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import case

from app.models.game import Game

DEFAULT_ELO_THRESHOLD = 50
```
For `score_confidence.py`, drop the SQLAlchemy/datetime imports — pure helper. Keep the one-liner module docstring → expanded multi-paragraph form because this is a math helper that benefits from inline derivation notes (already verbatim in `opening_insights_service.py:105-125`).

**Body to migrate verbatim** (`opening_insights_service.py:105-152`):
```python
def _compute_confidence(row: Any) -> tuple[Literal["low", "medium", "high"], float]:
    n = row.n
    score = (row.w + 0.5 * row.d) / n
    variance = (row.w + 0.25 * row.d) / n - score * score
    variance = max(variance, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        if score == SCORE_PIVOT:
            return "high", 1.0
        return "high", 0.0

    half_width = 1.96 * se  # 1.96 = z_{0.975}, constant of the formula
    if half_width <= CONFIDENCE_HIGH_MAX_HALF_WIDTH:
        confidence: Literal["low", "medium", "high"] = "high"
    elif half_width <= CONFIDENCE_MEDIUM_MAX_HALF_WIDTH:
        confidence = "medium"
    else:
        confidence = "low"

    z = (score - SCORE_PIVOT) / se
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return confidence, p_value
```

**Signature change for the new module:** swap `row: Any` → explicit `(w: int, d: int, l: int, n: int)` so callers don't have to fabricate a SQLAlchemy `Row` shim. Public name: `compute_confidence_bucket`. Public, not underscore-prefixed (D-06: shared between two services).

**Import pattern** (copy from `opening_insights_service.py:35-41`):
```python
from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH as CONFIDENCE_HIGH_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH as CONFIDENCE_MEDIUM_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)
```

**ty compliance:** explicit return type `tuple[Literal["low", "medium", "high"], float]`; explicit parameter types `int`; module already passes `ty check` because it mirrors the existing one.

---

### `app/services/opening_insights_service.py` (service, MIGRATION)

**Analog:** self.

**Import migration** — replace `_compute_confidence` definition (lines 105-152) with import:
```python
from app.services.score_confidence import compute_confidence_bucket
```
Call-site rewrite — search for `_compute_confidence(row)` and replace with `compute_confidence_bucket(row.w, row.d, row.l, row.n)`. Keep the same `(confidence, p_value)` tuple unpacking.

**`_rank_section` body rewrite** (D-03; existing implementation lines 322-331):
```python
# CURRENT (Phase 70):
def _rank_section(findings: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    """Sort findings by (severity desc, n_games desc) per D-07."""
    return sorted(
        findings,
        key=lambda f: (0 if f.severity == "major" else 1, -f.n_games),
    )
```
New body per RESEARCH.md `compute_insights re-sort` pattern:
```python
_CONFIDENCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

def _rank_section(findings: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    """Sort findings by (confidence DESC, |score - 0.50| DESC) per Phase 76 D-03."""
    return sorted(
        findings,
        key=lambda f: (_CONFIDENCE_RANK[f.confidence], -abs(f.score - 0.5)),
    )
```
Update the docstring to reference D-03 and remove the Phase 70 D-07 reference.

---

### `app/services/openings_service.py` (service, EXTENSION)

**Analog:** self lines 439-460 (existing `NextMoveEntry` build loop).

**Existing per-row build loop** (lines 439-460):
```python
moves: list[NextMoveEntry] = []
for row in move_rows:
    gc = row.game_count
    w, d, lo = row.wins, row.draws, row.losses
    wp = round(w / gc * 100, 1) if gc > 0 else 0.0
    dp = round(d / gc * 100, 1) if gc > 0 else 0.0
    lp = round(lo / gc * 100, 1) if gc > 0 else 0.0
    moves.append(
        NextMoveEntry(
            move_san=row.move_san,
            game_count=gc,
            wins=w,
            draws=d,
            losses=lo,
            win_pct=wp,
            draw_pct=dp,
            loss_pct=lp,
            result_hash=str(row.result_hash),
            result_fen=result_fens.get(row.result_hash, ""),
            transposition_count=trans_counts.get(row.result_hash, gc),
        )
    )
```

**Extension pattern** — at top of the loop, compute score + confidence + p_value, then pass into the constructor. Mirrors the `_compute_score` helper at `opening_insights_service.py:100-102`:
```python
score = (w + d / 2) / gc  # Phase 75 D-09 canonical metric
confidence, p_value = compute_confidence_bucket(w, d, lo, gc)  # D-06 shared helper
```
Add to the import block at file top:
```python
from app.services.score_confidence import compute_confidence_bucket
```
Add the three new fields to the `NextMoveEntry(...)` call alongside `transposition_count=...`. Pitfall 7 from RESEARCH.md: **do NOT add a HAVING clause to `query_next_moves`** — Move Explorer surfaces all moves; low-game ones get `confidence="low"` naturally and the frontend mute rule handles them.

---

### `app/schemas/openings.py` — `NextMoveEntry` (schema, EXTENSION)

**Analog:** `app/schemas/opening_insights.py:39-81` (`OpeningInsightFinding`) — already declares the exact three fields with the right Pydantic v2 idioms.

**Existing `NextMoveEntry`** (lines 185-198):
```python
class NextMoveEntry(BaseModel):
    """Statistics for a single next move from a queried position."""

    move_san: str
    game_count: int
    wins: int
    draws: int
    losses: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    result_hash: str   # BigInt as string for JS safety (full_hash of resulting position)
    result_fen: str    # board FEN of resulting position (piece placement only)
    transposition_count: int
```

**Field declarations to add** (copy idioms from `opening_insights.py:73-81`):
```python
score: float = Field(
    ge=0.0, le=1.0
)  # (W + D/2)/n; canonical classification metric (Phase 75 D-09)
confidence: Literal[
    "low", "medium", "high"
]  # Trinomial Wald 95% CI half-width bucket (Phase 75 D-05/D-06)
p_value: float = Field(
    ge=0.0, le=1.0
)  # Two-sided p-value for H0: score = 0.50 (Phase 75 D-05/D-09)
```
Confirm `from typing import Literal` and `from pydantic import BaseModel, Field` are already imported at file top (they are — this is the same `openings.py` that already uses `Literal[...]` for `time_control`/`platform`/`color` filters).

**RESEARCH.md anti-pattern note:** do NOT add `model_config = ConfigDict(extra="forbid")` to `NextMoveEntry` — it doesn't have one today; tightening as a side effect would break unrelated callers.

---

### `frontend/src/lib/arrowColor.ts` (utility, REWRITE)

**Analog:** self.

**Existing function body** (lines 39-69) — strip the win/loss-rate logic + `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` constants (lines 26-27).

**Replace with** (per RESEARCH.md Pattern 3, score-based body using already-present additive exports `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`):
```typescript
/**
 * Returns a categorical hex color string for a board arrow.
 *
 * @param score     Score in [0, 1] = (W + 0.5·D) / N
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(score: number, gameCount: number, isHovered: boolean): string {
  if (isHovered) return HOVER_BLUE;
  if (gameCount < MIN_GAMES_FOR_COLOR) return GREY;

  // Strict ≥ / ≤ boundaries match Phase 75 D-03 / D-11 backend behavior.
  // Order matters: dark before light on each side.
  if (score >= SCORE_PIVOT + MAJOR_EFFECT_SCORE) return DARK_GREEN;   // ≥ 0.60
  if (score >= SCORE_PIVOT + MINOR_EFFECT_SCORE) return LIGHT_GREEN;  // ≥ 0.55
  if (score <= SCORE_PIVOT - MAJOR_EFFECT_SCORE) return DARK_RED;     // ≤ 0.40
  if (score <= SCORE_PIVOT - MINOR_EFFECT_SCORE) return LIGHT_RED;    // ≤ 0.45
  return GREY;
}
```
**Keep unchanged:** `MIN_GAMES_FOR_COLOR`, `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`, all hex constants (`GREY`, `LIGHT_GREEN`, `DARK_GREEN`, `LIGHT_RED`, `DARK_RED`, `HOVER_BLUE`), and the `arrowSortKey` function (lines 77-90).

**Remove:** `LIGHT_COLOR_THRESHOLD = 55` and `DARK_COLOR_THRESHOLD = 60` (lines 26-27) plus the leading comment (lines 1-13) — replace with a short docstring describing the score-based encoding.

**knip note:** dead constants will fail `npm run knip`; removing them is required for CI.

---

### `frontend/src/lib/openingInsights.ts` (utility, CLEANUP + new constant)

**Analog A (existing module shape):** self.

**Analog B (InfoPopover JSX-children pattern):** `MoveExplorer.tsx:166-175`:
```tsx
<InfoPopover ariaLabel="Move arrows info" testId="move-arrows-info" side="top">
  <div className="space-y-2">
    <p>
      These are the moves that occurred next in the position shown on the board, ...
    </p>
    <p>
      On desktop, click a move to play it. On mobile, tap to highlight ...
    </p>
  </div>
</InfoPopover>
```
This pins `OPENING_INSIGHTS_POPOVER_COPY` semantics: a single `ReactNode` JSX fragment with two-three `<p>` blocks. Because `openingInsights.ts` currently has no JSX, RESEARCH.md Open Question #3 calls for either renaming to `.tsx` or defining the constant as a small component in `OpeningInsightsBlock.tsx` directly. Recommend the latter for minimal blast radius — declare `const OPENING_INSIGHTS_POPOVER_COPY: ReactNode = (...)` inside `OpeningInsightsBlock.tsx`, importing nothing from `openingInsights.ts` for this concern. (Planner: pick whichever, but document the choice.)

**Stale exports to remove** (lines 5, 8, 11):
```typescript
export const MIN_GAMES_FOR_INSIGHT = 20;
export const INSIGHT_RATE_THRESHOLD = 55;
export const INSIGHT_THRESHOLD_COPY = 'Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%.';
```

**Keep unchanged:** `getSeverityBorderColor` (lines 19-27) — its mapping `(classification, severity) → hex` still mirrors the score-color scheme; simplification is deferred per CONTEXT.md Deferred Ideas. `trimMoveSequence` (lines 42-97) is untouched.

**knip will catch dangling imports** — verify no consumer remains with `grep -R MIN_GAMES_FOR_INSIGHT frontend/src/`. RESEARCH.md Pitfall 6 confirms the only consumer today is `openingInsights.test.ts:93-103`.

---

### `frontend/src/types/insights.ts` — `OpeningInsightFinding` (type catch-up)

**Analog:** `app/schemas/opening_insights.py:39-81` (Python source of truth — already shipped Phase 75).

**Existing TS interface** (lines 69-88):
```typescript
export interface OpeningInsightFinding {
  // ...
  n_games: number;
  wins: number;
  draws: number;
  losses: number;
  win_rate: number;
  loss_rate: number;
  score: number;
}
```

**Edit:** remove `win_rate` and `loss_rate` (lines 85-86); add `confidence` and `p_value`. Final shape mirrors Python exactly:
```typescript
export interface OpeningInsightFinding {
  color: 'white' | 'black';
  classification: 'weakness' | 'strength';
  severity: 'minor' | 'major';
  opening_name: string;
  opening_eco: string;
  display_name: string;
  entry_fen: string;
  entry_san_sequence: string[];
  entry_full_hash: string;
  candidate_move_san: string;
  resulting_full_hash: string;
  n_games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;
}
```
**Watch:** TypeScript strict-mode (`noUncheckedIndexedAccess`) means any `Record<finding.confidence, ...>` indexing is automatically narrowed because `confidence` is a literal-union type.

---

### `frontend/src/types/api.ts` — `NextMoveEntry` (type extension)

**Analog:** `app/schemas/openings.py:185-198` (Python source of truth, after the D-05 extension lands).

**Existing TS interface** (lines 93-105):
```typescript
export interface NextMoveEntry {
  move_san: string;
  game_count: number;
  wins: number;
  draws: number;
  losses: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  result_hash: string;
  result_fen: string;
  transposition_count: number;
}
```
Append three fields verbatim from RESEARCH.md Pattern 2:
```typescript
score: number;
confidence: 'low' | 'medium' | 'high';
p_value: number;
```

---

### `frontend/src/components/move-explorer/MoveExplorer.tsx` (component, EXTENSION)

**Analog:** self lines 161-181 (header) + 207-220 (`MoveRow` props) + 222-253 (mute/tint logic).

**Existing call site to update** (line 228):
```tsx
const arrowColor = getArrowColor(entry.win_pct, entry.loss_pct, entry.game_count, false);
```
**Replace with** (D-13 signature change):
```tsx
const arrowColor = getArrowColor(entry.score, entry.game_count, false);
```

**Existing mute trigger** (line 222):
```tsx
const isBelowThreshold = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS;
// ...
if (isBelowThreshold) rowStyle.opacity = UNRELIABLE_OPACITY;
```
**Extend to D-11 condition** (RESEARCH.md "Mute rule extension"):
```tsx
const isLowConfidence = entry.confidence === 'low';
const isUnreliable = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS || isLowConfidence;
// ...
if (isUnreliable) rowStyle.opacity = UNRELIABLE_OPACITY;
```

**New "Conf" column header** (insert between Games line 178 and Results line 179, mirroring Move column at lines 163-177):
```tsx
<th
  className="w-[2.5rem] text-center text-xs text-muted-foreground font-normal pb-1"
  data-testid="move-explorer-th-conf"
>
  Conf
</th>
```
Optional: wrap "Conf" text in a one-line `Tooltip` ("How well-sampled this move is") per RESEARCH.md Open Question 1 — discretion.

**New Conf cell** (insert between Games `<td>` and Results `<td>` in MoveRow body — analog: existing `<td>` cells at lines 270+ which use `tabular-nums text-xs`). RESEARCH.md Code Examples gives:
```tsx
<td className="py-1 text-center text-xs text-muted-foreground tabular-nums">
  {entry.confidence === 'medium' ? 'med' : entry.confidence}
</td>
```
**Pitfall 1 (`noUncheckedIndexedAccess`):** prefer the inline ternary above (already type-safe) over a `Record` lookup if you don't reuse the mapping.

**`data-testid` rule:** the row already carries `move-explorer-row-${entry.move_san}` (line 262). Don't add cell-level testids — `<td>` is not interactive.

---

### `frontend/src/components/insights/OpeningFindingCard.tsx` (component, EXTENSION)

**Analog A (prose pattern):** self lines 55-64 (existing `proseLine`).

**Analog B (Tooltip-around-content pattern):** self lines 66-93 (`linksRow`) — the `<Tooltip content={...}>` wrapping the two action buttons. The new confidence-line tooltip uses the exact same wrapper.

**Existing prose** (lines 25-27, 29, 55-64) — currently broken because it reads removed `loss_rate`/`win_rate`:
```tsx
const ratePercent = Math.round(
  (isWeakness ? finding.loss_rate : finding.win_rate) * 100,
);
const verb = isWeakness ? 'lose' : 'win';
// ...
<p className="text-sm text-muted-foreground">
  You {verb}{' '}
  <span style={{ color: borderLeftColor }} className="font-semibold">
    {ratePercent}%
  </span>{' '}
  as {colorLabel} after{' '}
  <span className="font-mono text-foreground">{trimmedSequence}</span>
</p>
```

**Replace with** (RESEARCH.md Code Example, D-02 prose migration):
```tsx
const scorePercent = Math.round(finding.score * 100);
// (drop verb/isWeakness for prose — section title carries the polarity)

const proseLine = (
  <p className="text-sm text-muted-foreground">
    You score{' '}
    <span style={{ color: borderLeftColor }} className="font-semibold">
      {scorePercent}%
    </span>{' '}
    as {colorLabel} after{' '}
    <span className="font-mono text-foreground">{trimmedSequence}</span>
  </p>
);
```

**Add confidence line + tooltip** — analog: the `<Tooltip content={...}>` wrapper used at lines 68 and 80. Place between `proseLine` and `linksRow`:
```tsx
const CONFIDENCE_TOOLTIP: Record<OpeningInsightFinding['confidence'], string> = {
  low: 'small sample, treat as a hint',
  medium: 'enough games to trust the direction',
  high: 'sample is large enough to trust the magnitude',
};

const confidenceLine = (
  <Tooltip content={CONFIDENCE_TOOLTIP[finding.confidence]}>
    <p
      className="text-xs text-muted-foreground"
      data-testid={`opening-finding-card-${idx}-confidence`}
    >
      Confidence: <span className="font-medium">{finding.confidence}</span>
    </p>
  </Tooltip>
);
```
**`noUncheckedIndexedAccess` note:** `Record<'low'|'medium'|'high', string>` is exhaustive — `CONFIDENCE_TOOLTIP[finding.confidence]` types as `string`, no narrowing needed.

**Mute rule** — wrap the outermost card `<div>` (line 96-101) with conditional opacity (analog: `MoveExplorer.tsx:239`):
```tsx
const isUnreliable = finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
const cardStyle: React.CSSProperties = {
  borderLeftColor,
  ...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {}),
};
// ...
<div
  data-testid={`opening-finding-card-${idx}`}
  className="block border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3"
  style={cardStyle}
>
```
**New imports** to add at file top (analog: `MoveExplorer.tsx:5`):
```tsx
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
```

**Insert `confidenceLine` into both layouts** — both the mobile branch (lines 103-116) and the desktop branch (lines 118-130) currently render `proseLine` then `linksRow` inside a `flex flex-col gap-2`. Insert `confidenceLine` between them in both branches (CLAUDE.md "Always apply changes to mobile too" rule).

---

### `frontend/src/components/insights/OpeningInsightsBlock.tsx` (component, EXTENSION)

**Analog:** self lines 198-209 (current section `<h3>`); `MoveExplorer.tsx:163-176` for the `<header-text> + <InfoPopover>` pattern.

**Existing section header** (lines 199-209):
```tsx
<section
  data-testid={`opening-insights-section-${section.key}`}
  className="space-y-2"
>
  <h3 className="text-base font-semibold flex items-center gap-1.5">
    <span
      className={`inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground ${swatchClass}`}
      aria-hidden="true"
    />
    {section.title}
  </h3>
```

**Pattern to copy from `MoveExplorer.tsx:164-176`** (the `<header-element><span><InfoPopover>...</InfoPopover></span></...>` shape):
```tsx
<th className="...">
  <span className="inline-flex items-center gap-1">
    Move
    <InfoPopover ariaLabel="Move arrows info" testId="move-arrows-info" side="top">
      <div className="space-y-2">
        <p>...</p>
        <p>...</p>
      </div>
    </InfoPopover>
  </span>
</th>
```

**Apply to each of the four section headers** — RESEARCH.md Code Example:
```tsx
<h3 className="text-base font-semibold flex items-center gap-1.5">
  <span
    className={`inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground ${swatchClass}`}
    aria-hidden="true"
  />
  {section.title}
  <InfoPopover
    ariaLabel={`${section.title} info`}
    testId={`opening-insights-section-${section.key}-info`}
    side="bottom"
  >
    {OPENING_INSIGHTS_POPOVER_COPY}
  </InfoPopover>
</h3>
```
`side="bottom"` so the popover doesn't clip at viewport top (existing analogs in the file use `side="top"` only when anchored low; `<h3>` headers sit at section tops).

**`OPENING_INSIGHTS_POPOVER_COPY` constant** — RESEARCH.md Open Question 3 favors keeping the constant local to `OpeningInsightsBlock.tsx` (this file is already `.tsx`, avoiding the rename of `openingInsights.ts → .tsx`):
```tsx
import type { ReactNode } from 'react';

const OPENING_INSIGHTS_POPOVER_COPY: ReactNode = (
  <div className="space-y-2">
    <p>
      <strong>Score</strong> is (W + ½D) / N. 50% means you and your opponents broke even.
    </p>
    <p>
      A finding shows up when your score sits at least 5% from 50%, enough of a gap that it's probably not random.
    </p>
    <p>
      <strong>Confidence</strong> says how big the sample is. <em>Low</em> findings are worth a glance;{' '}
      <em>high</em> findings are well-supported.
    </p>
  </div>
);
```
Em-dashes per CLAUDE.md style: rewrite the CONTEXT.md draft using commas (the version above already does this).

**Test-id rule:** four new triggers each get `opening-insights-section-${section.key}-info` (kebab keys already locked at `OpeningInsightsBlock.tsx:34/41/48/55`).

---

### `tests/services/test_score_confidence.py` (NEW FILE)

**Analog:** `tests/services/test_opening_insights_service.py:201-272` — eight existing boundary tests for `_compute_confidence`. Lift verbatim, retargeted at `score_confidence.compute_confidence_bucket`. RESEARCH.md Wave 0 Gaps explicitly approves this lift.

**Existing tests to lift** (lines 201-268):
```python
def test_compute_confidence_high_at_large_n() -> None:
    row = _make_row(n=400, w=80, d=80, losses=240)
    confidence, p_value = _compute_confidence(row)
    assert confidence == "high"
    assert 0.0 <= p_value < 1.0


def test_compute_confidence_medium_at_moderate_n() -> None:
    row = _make_row(n=30, w=6, d=6, losses=18)
    confidence, _p_value = _compute_confidence(row)
    assert confidence == "medium"


def test_compute_confidence_low_at_n10_extreme_score() -> None:
    row = _make_row(n=10, w=2, d=2, losses=6)
    confidence, _p_value = _compute_confidence(row)
    assert confidence == "low"


def test_compute_confidence_just_inside_medium_boundary() -> None:
    row = _make_row(n=25, w=5, d=5, losses=15)
    confidence, _p_value = _compute_confidence(row)
    assert confidence == "medium"


def test_compute_confidence_p_value_at_score_050_is_one() -> None:
    row = _make_row(n=20, w=8, d=4, losses=8)
    _confidence, p_value = _compute_confidence(row)
    assert p_value == pytest.approx(1.0, abs=1e-9)


def test_compute_confidence_se_zero_all_draws() -> None:
    row = _make_row(n=10, w=0, d=10, losses=0)
    confidence, p_value = _compute_confidence(row)
    assert confidence == "high"
    assert p_value == 1.0


def test_compute_confidence_se_zero_all_wins() -> None:
    row = _make_row(n=10, w=10, d=0, losses=0)
    confidence, p_value = _compute_confidence(row)
    assert confidence == "high"
    assert p_value == 0.0
```

**Adaptation pattern** — drop `_make_row`, call directly with positional args:
```python
from app.services.score_confidence import compute_confidence_bucket


def test_high_at_large_n() -> None:
    confidence, p_value = compute_confidence_bucket(w=80, d=80, l=240, n=400)
    assert confidence == "high"
    assert 0.0 <= p_value < 1.0


def test_se_zero_all_draws() -> None:
    confidence, p_value = compute_confidence_bucket(w=0, d=10, l=0, n=10)
    assert confidence == "high"
    assert p_value == 1.0
```

**Add D-22 boundary cases:** `n=10` floor row (smallest legal); a row that lands inside the "high" half-width bucket; the all-losses SE=0 case (mirror of all-wins). The "exact half-width = 0.10 / 0.20" cases are documented in `test_compute_confidence_just_inside_medium_boundary` as un-hittable with integer (w,d,l,n) — keep that comment in the lifted test.

---

### `tests/services/test_opening_insights_arrow_consistency.py` (D-22 — extend)

**Analog:** self.

**Pitfall 3:** the existing regex-based assertions (lines 32-46, 49-70) cannot test "both call sites use the same helper" because confidence has no constant in `arrowColor.ts` (D-23 prohibits surfacing it on board arrows). RESEARCH.md prescribes the **fallback path** — extend with a unit-style assertion that imports and asserts the helper module's location and name:
```python
def test_compute_confidence_bucket_is_single_implementation() -> None:
    """D-22 fallback: structural assertion that score_confidence.compute_confidence_bucket
    is the only implementation of the trinomial Wald formula. The boundary
    behavior is exercised by tests/services/test_score_confidence.py.
    """
    from app.services import score_confidence
    assert hasattr(score_confidence, "compute_confidence_bucket")
    # opening_insights_service no longer defines _compute_confidence
    from app.services import opening_insights_service
    assert not hasattr(opening_insights_service, "_compute_confidence")
```
The strict guarantee — "no duplicate formula" — is a **structural** invariant (only one module defines it) rather than a value-equivalence test.

**Existing 4 regex tests stay unchanged** — they already pass after Phase 75 and continue to anchor the score-pivot/effect/min-games trio.

---

### `tests/services/test_opening_insights_service.py` (D-03 — UPDATE existing test)

**Analog:** self lines 635-684 (`test_ranking_severity_desc_then_n_games_desc`).

**Existing test asserts** (line 684): `weaknesses[0].severity == "major"`.

**Rewrite for new key** `(confidence DESC, |score - 0.5| DESC)`. The fixture rows already produce known scores:
- `row_minor_large_n`: n=100, w=30, d=24, l=46 → score 0.42 (|delta|=0.08), confidence likely "high" (large n)
- `row_minor_small_n`: n=50, w=15, d=12, l=23 → score 0.42 (|delta|=0.08), confidence "high" or "medium"
- `row_major`: n=20, w=4, d=4, l=12 → score 0.30 (|delta|=0.20), confidence "medium" or "low"

The planner must **compute the actual confidence buckets** for each fixture using the helper formula and rewrite assertions accordingly. With `(confidence DESC, |score-0.5| DESC)` the new ordering favors the high-n minors over the lower-n major. Likely outcome: `[row_minor_large_n, row_minor_small_n, row_major]` (high → high → medium/low). Rename the test to `test_ranking_confidence_desc_then_score_distance_desc` and update the docstring to cite D-03.

**Add new test** for the second key kicking in: two rows with the same confidence but different `|score - 0.5|` — assert the larger-distance row sorts first.

---

### `tests/test_openings_service.py` (D-05 — EXTENSION)

**Analog:** self (existing module + `_seed_game` helper at top).

**Add unit test** asserting that `get_next_moves` populates the three new fields:
```python
async def test_get_next_moves_populates_score_confidence_p_value(
    db_session: AsyncSession,
) -> None:
    """D-05/D-13: Each NextMoveEntry carries score, confidence, p_value
    computed via the shared score_confidence.compute_confidence_bucket helper.
    """
    # Seed games where 1.e4 followed by 1...c5 produces 10 wins, 5 draws, 5 losses.
    # Expected: score = (10 + 2.5)/20 = 0.625; confidence buckets per Wald formula.
    # ... (use existing _seed_game helper)
    response = await get_next_moves(db_session, user_id=1, request=...)
    e4_entry = next(m for m in response.moves if m.move_san == "e4")
    assert 0.0 <= e4_entry.score <= 1.0
    assert e4_entry.confidence in ("low", "medium", "high")
    assert 0.0 <= e4_entry.p_value <= 1.0
    # Cross-check: same value as the helper would return directly
    expected_confidence, expected_p = compute_confidence_bucket(
        e4_entry.wins, e4_entry.draws, e4_entry.losses, e4_entry.game_count
    )
    assert e4_entry.confidence == expected_confidence
    assert e4_entry.p_value == pytest.approx(expected_p)
```

---

### `frontend/src/lib/arrowColor.test.ts` (REWRITE)

**Analog:** self.

**Existing tests use `(winPct, lossPct, gameCount, hovered)` signature** — every assertion at lines 13-153 must be rewritten for `(score, gameCount, hovered)`.

**Replacement boundary table:**
```typescript
// Below threshold guard
expect(getArrowColor(0.65, 9, false)).toBe(GREY);
expect(getArrowColor(0.65, 9, true)).toBe(HOVER_BLUE);

// Hover always blue
expect(getArrowColor(0.50, 20, true)).toBe(HOVER_BLUE);

// Neutral grey zone (strict boundaries)
expect(getArrowColor(0.50, 20, false)).toBe(GREY);
expect(getArrowColor(0.501, 20, false)).toBe(GREY);   // just above pivot, below MINOR
expect(getArrowColor(0.549, 20, false)).toBe(GREY);   // just below MINOR threshold
expect(getArrowColor(0.451, 20, false)).toBe(GREY);   // just above LIGHT_RED threshold

// Light green (≥ 0.55, < 0.60). Strict ≥.
expect(getArrowColor(0.55, 20, false)).toBe(LIGHT_GREEN);
expect(getArrowColor(0.599, 20, false)).toBe(LIGHT_GREEN);

// Dark green (≥ 0.60)
expect(getArrowColor(0.60, 20, false)).toBe(DARK_GREEN);
expect(getArrowColor(0.80, 20, false)).toBe(DARK_GREEN);

// Light red (≤ 0.45, > 0.40). Strict ≤.
expect(getArrowColor(0.45, 20, false)).toBe(LIGHT_RED);
expect(getArrowColor(0.401, 20, false)).toBe(LIGHT_RED);

// Dark red (≤ 0.40)
expect(getArrowColor(0.40, 20, false)).toBe(DARK_RED);
expect(getArrowColor(0.20, 20, false)).toBe(DARK_RED);
```
Drop the "both win and loss > 55%" tests (lines 95-107) — the score input collapses both into a single value, removing the conflict case entirely.

The `arrowSortKey` test block (lines 109-153) stays, but its `getArrowColor` round-trip cases (lines 138-153) need the signature swap.

---

### `frontend/src/lib/openingInsights.test.ts` (REWRITE)

**Analog:** self.

**Existing stale-constant block** (lines 92-105):
```typescript
describe('shared constants', () => {
  it('MIN_GAMES_FOR_INSIGHT mirrors backend MIN_GAMES_PER_CANDIDATE = 20', () => {
    expect(MIN_GAMES_FOR_INSIGHT).toBe(20);
  });
  // ...
});
```
**Remove entire block.** Drop the stale imports at top (lines 5-7).

**Keep unchanged:** `trimMoveSequence` and `getSeverityBorderColor` describe blocks (lines 11-90).

**Optional new smoke test** — if the planner places `OPENING_INSIGHTS_POPOVER_COPY` in a re-imported location, assert it renders three paragraphs containing "Score", "5%", "Confidence". If the constant lives privately in `OpeningInsightsBlock.tsx`, this lives in `OpeningInsightsBlock.test.tsx` instead.

---

### `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` (EXTENSION)

**Analog:** self (`makeEntry` fixture lines 20-35).

**Existing `makeEntry`** must be extended for the three new `NextMoveEntry` fields once `frontend/src/types/api.ts` is updated (TS will fail-build until both land):
```typescript
function makeEntry(overrides: Partial<NextMoveEntry> & Pick<NextMoveEntry, 'move_san'>): NextMoveEntry {
  return {
    move_san: overrides.move_san,
    game_count: 100,
    wins: 50,
    draws: 25,
    losses: 25,
    win_pct: 50,
    draw_pct: 25,
    loss_pct: 25,
    result_hash: '0',
    result_fen: '',
    transposition_count: 100,
    score: 0.625,             // NEW (Phase 76)
    confidence: 'high',       // NEW
    p_value: 0.05,            // NEW
    ...overrides,
  };
}
```

**New tests:**
- `it('renders Conf header cell with data-testid="move-explorer-th-conf"')` — analog: existing `getByTestId('move-explorer-table')` queries
- `it('renders "low" / "med" / "high" labels per entry.confidence')` — render three rows with different confidence values, assert text content
- `it('applies UNRELIABLE_OPACITY when entry.confidence === "low"')` — analog: existing `expect(row.style.backgroundColor)` style assertions at lines 76-78
- `it('applies UNRELIABLE_OPACITY when entry.game_count < 10')` — pre-existing behavior, add explicit test

---

### `frontend/src/components/insights/OpeningFindingCard.test.tsx` (REWRITE prose tests)

**Analog:** self.

**`makeFinding` fixture rewrite** (lines 28-50) — drop `win_rate` and `loss_rate`, add `confidence` and `p_value`:
```typescript
function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'black',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Sicilian Defense: Najdorf',
    opening_eco: 'B90',
    display_name: 'Sicilian Defense: Najdorf',
    entry_fen: '...',
    entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6'],
    entry_full_hash: '111',
    candidate_move_san: 'Be2',
    resulting_full_hash: '222',
    n_games: 18,
    wins: 4,
    draws: 3,
    losses: 11,
    score: 5.5 / 18,         // (4 + 1.5) / 18 ≈ 0.306
    confidence: 'medium',    // NEW
    p_value: 0.05,           // NEW
    ...overrides,
  };
}
```

**Existing prose tests at lines 56-102 must be rewritten:**
- "lose 62% as Black" → "score 31% as Black" (where 31 = round(0.306 * 100); pick fixture scores that give clean integers)
- "win 58% as White" → "score 58% as White" (set `score: 0.58`)
- Drop the `loss_rate: 0.62` / `win_rate: 0.58` overrides and replace with `score:` overrides
- Drop the `verb` polarity assertion (`/lose/i` / `/win/i`) — both sections use "score" now

**New tests:**
- `it('renders Confidence: <level> line with data-testid="opening-finding-card-${idx}-confidence"')`
- `it('applies opacity when finding.confidence === "low"')`
- `it('applies opacity when finding.n_games < 10')`

**Border-color tests** at lines 104-154 stay unchanged — those still test severity → hex mapping.

---

### `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` (EXTENSION)

**Analog:** self.

**`makeFinding` fixture rewrite** (lines 46-68) — same shape as `OpeningFindingCard.test.tsx` (drop `win_rate`/`loss_rate`, add `confidence`/`p_value`).

**New tests:**
- `it('renders InfoPopover trigger on each section header (4 total)')` — `getAllByTestId(/^opening-insights-section-.+-info$/)` returns 4
- `it('InfoPopover trigger has aria-label matching the section title')` — analog: existing testid/aria assertions

**Existing tests** (skeleton/error/empty-state at lines 95+) stay unchanged.

---

## Shared Patterns

### Pattern: `<header-element><span><InfoPopover>...</InfoPopover></span></...>`

**Source:** `frontend/src/components/move-explorer/MoveExplorer.tsx:163-176`

**Apply to:** `OpeningInsightsBlock.tsx` (four section `<h3>`) and (optional) `MoveExplorer.tsx` Conf `<th>` if the planner adds a column-header tooltip.

```tsx
<h3 className="text-base font-semibold flex items-center gap-1.5">
  {/* leading swatch ... */}
  {section.title}
  <InfoPopover
    ariaLabel={`${section.title} info`}
    testId={`opening-insights-section-${section.key}-info`}
    side="bottom"
  >
    {OPENING_INSIGHTS_POPOVER_COPY}
  </InfoPopover>
</h3>
```

### Pattern: `<Tooltip content={...}>{trigger}</Tooltip>` for tap-friendly hover hints

**Source:** `frontend/src/components/insights/OpeningFindingCard.tsx:68,80` (already in the file being extended); `frontend/src/components/ui/tooltip.tsx:33-43` (touch-suppression mechanism)

**Apply to:** the new "Confidence: …" line in `OpeningFindingCard.tsx`.

```tsx
<Tooltip content={CONFIDENCE_TOOLTIP[finding.confidence]}>
  <p className="text-xs text-muted-foreground" data-testid={`opening-finding-card-${idx}-confidence`}>
    Confidence: <span className="font-medium">{finding.confidence}</span>
  </p>
</Tooltip>
```
Anti-pattern (RESEARCH.md): do NOT add a separate `?` icon trigger — the tooltip fires from the line itself.

### Pattern: Mute via `UNRELIABLE_OPACITY`

**Source:** `frontend/src/lib/theme.ts:74-77` (constants); `frontend/src/components/move-explorer/MoveExplorer.tsx:5,239` (existing usage).

**Apply to:** both row mute (`MoveExplorer.tsx`) and card mute (`OpeningFindingCard.tsx`).

**Trigger condition (D-11):**
```tsx
const isUnreliable = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS || entry.confidence === 'low';
if (isUnreliable) rowStyle.opacity = UNRELIABLE_OPACITY;
```
Don't add new theme constants. Don't merge with existing tint logic — this is purely additive.

### Pattern: `data-testid` naming for new elements

**Established convention** (from `OpeningInsightsBlock.tsx:200`, `OpeningFindingCard.tsx:73,85`, `MoveExplorer.tsx:138,160,262`):

| New element | data-testid |
|-------------|-------------|
| Section-title popover trigger | `opening-insights-section-{section.key}-info` (4 IDs) |
| Card confidence line | `opening-finding-card-{idx}-confidence` |
| Move Explorer Conf column header | `move-explorer-th-conf` |
| Conf cells | none (cells are not interactive; rows already have `move-explorer-row-${move_san}`) |

ARIA: each new `InfoPopover` already requires an `ariaLabel` prop (see `info-popover.tsx:8`). Pass `${section.title} info` to satisfy CLAUDE.md "ARIA labels on icon-only buttons".

### Pattern: Pydantic `Literal[...]` + `Field(ge=, le=)` for new schema fields

**Source:** `app/schemas/opening_insights.py:69-81`

**Apply to:** `app/schemas/openings.py` `NextMoveEntry`. Three new fields:
```python
score: float = Field(ge=0.0, le=1.0)
confidence: Literal["low", "medium", "high"]
p_value: float = Field(ge=0.0, le=1.0)
```
ty compliance: use `Literal[...]` not bare `str` (CLAUDE.md "Type safety" rule).

### Pattern: Shared helper module after second consumer appears

**Source:** `app/repositories/query_utils.py` (single shared utility module per cross-cutting concern).

**Apply to:** `app/services/score_confidence.py` (NEW). Pure helper, no DB session, no config. The verbatim formula migrates from `app/services/opening_insights_service.py:105-152`.

```python
"""Trinomial Wald confidence helper, shared between opening_insights_service
and openings_service. Migrates Phase 75's _compute_confidence verbatim.
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH as CONFIDENCE_HIGH_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH as CONFIDENCE_MEDIUM_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)


def compute_confidence_bucket(
    w: int, d: int, l: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]:
    """..."""  # body verbatim from opening_insights_service.py:105-152
```

## No Analog Found

None for this phase — every file has a strong in-tree analog. This is consistent with RESEARCH.md's primary recommendation: "almost every component already has its imports, primitives, and patterns in place." Phase 76 is a coordinated wire-through of values from Phase 75's contract, not new architecture.

## Metadata

**Analog search scope:**
- `app/services/`, `app/repositories/`, `app/schemas/` (backend)
- `frontend/src/lib/`, `frontend/src/types/`, `frontend/src/components/{insights,move-explorer,ui}/` (frontend)
- `tests/services/`, `tests/`, `frontend/src/**/__tests__/`, co-located `*.test.{ts,tsx}` (tests)

**Files scanned (concrete):** 21 source files + 7 test files = 28 files via direct `Read` calls; all referenced line ranges verified.

**Pattern extraction date:** 2026-04-28

**Related canonical references:**
- `.planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md` (Phase 75 lock-in)
- `.planning/notes/opening-insights-v1.14-design.md` (milestone design)
- CLAUDE.md sections: Coding Guidelines, Frontend, Browser Automation Rules
