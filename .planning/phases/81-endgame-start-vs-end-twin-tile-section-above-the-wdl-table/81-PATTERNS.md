# Phase 81: Endgame Start vs End — Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 11 (2 backend modify, 1 frontend new, 4 frontend modify, 4 test new/extend)
**Analogs found:** 11 / 11 (every artifact has a verified, in-tree analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/endgame_service.py` (modify `_get_endgame_performance_from_rows`) | service / aggregator | request-response, transform | `app/services/endgame_service.py::_compute_score_gap_material` (lines 700-787) | exact — same fn, same pre-fetched-rows pipeline |
| `app/schemas/endgames.py` (extend `EndgamePerformanceResponse`) | schema | request-response | `app/schemas/endgames.py::EndgamePerformanceResponse` (line 107) | exact — same model, additive fields |
| `frontend/src/types/endgames.ts` (extend `EndgamePerformanceResponse`) | type mirror | request-response | `frontend/src/types/endgames.ts::EndgamePerformanceResponse` (line 58) | exact — same interface |
| `frontend/src/components/charts/EndgameStartVsEndSection.tsx` (NEW) | component | event-driven render | `frontend/src/pages/openings/ExplorerTab.tsx` lines 92-202 (rows 2 & 3) | exact — locked layout pattern |
| `frontend/src/pages/Endgames.tsx` (insert section + accordion paragraphs) | page integration | event-driven render | `frontend/src/pages/Endgames.tsx` line 340-394 (`showPerfSection` block) | exact — same insertion site |
| `frontend/src/lib/endgameEntryEvalZones.ts` (NEW, optional) | constants | n/a | `frontend/src/lib/openingStatsZones.ts` | exact — sibling module pattern |
| `tests/services/test_endgame_start_vs_end.py` (NEW) | test (unit) | n/a | `tests/services/test_eval_confidence.py` + `tests/test_endgame_service.py::TestScoreGapMaterialInvariant` | role-match |
| `tests/test_endgame_service.py` (extend with contract test) | test (schema contract) | n/a | existing tests in same file | exact |
| `tests/test_endgames_router.py` (extend with API contract) | test (integration) | n/a | existing endgame router tests in same file | exact |
| `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` (NEW) | test (component) | n/a | `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` | exact |
| `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` (NEW) | test (page integration) | n/a | existing `Endgames.statsBoard.test.tsx` (per RESEARCH.md) | role-match |

## Pattern Assignments

### `app/services/endgame_service.py::_get_endgame_performance_from_rows` (service, transform)

**Analog:** `app/services/endgame_service.py::_compute_score_gap_material` (same module — already does the per-game dedupe over `entry_rows`).

**Imports pattern** (top of `endgame_service.py`, lines 28-66):
```python
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Literal, cast

from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.endgame_repository import (
    query_endgame_entry_rows,
    ...
)
from app.schemas.endgames import (
    EndgamePerformanceResponse,
    EndgameWDLSummary,
    ...
)
```

**Add for Phase 81:**
```python
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.score_confidence import compute_confidence_bucket
```

**Per-game dedupe over `entry_rows` (the load-bearing pattern)** — `_compute_score_gap_material` lines 744-775:
```python
# rows carry labeled columns in prod (see query_endgame_bucket_rows /
# query_endgame_entry_rows) and a matching NamedTuple stand-in in tests,
# so attribute access is valid in both cases even though the declared
# parameter type unions in plain tuple for backward-compat.
rows_by_game: dict[int, list[Row[Any]]] = defaultdict(list)
for row in entry_rows:
    rows_by_game[row.game_id].append(row)  # ty: ignore[unresolved-attribute, invalid-argument-type]

for game_id, game_rows in rows_by_game.items():
    chosen_row: Row[Any] | None = None
    # ... pick one row per game ...
    if chosen_row is None:
        chosen_row = min(game_rows, key=lambda r: r.endgame_class)
```

**For Phase 81: pick the lowest-`endgame_class` row per game (deterministic).** The eval at endgame entry should be from the FIRST qualifying span (earliest endgame class transition) — `min(game_rows, key=lambda r: r.endgame_class)` mirrors the priority-3 fallback in `_compute_score_gap_material` line 774.

**Sign-flip pattern** — `_classify_endgame_bucket` lines 184-202:
```python
# Sign convention:
#     Raw SQL eval is always white-perspective. For black users the sign is
#     flipped so positive user_eval = user is ahead.
sign = 1 if user_color == "white" else -1
if eval_mate is not None:
    user_eval: int = sign * (1_000_000 if eval_mate > 0 else -1_000_000)
elif eval_cp is not None:
    user_eval = sign * eval_cp
```

**Wald-z helper consumption pattern** — `app/services/stats_service.py` lines 410-425 (verified in RESEARCH.md):
```python
from app.services.eval_confidence import compute_eval_confidence_bucket

if pe is not None and pe.eval_n_mg > 0:
    confidence, p_value, mean_cp, ci_half_width = compute_eval_confidence_bucket(
        pe.eval_sum_mg,
        pe.eval_sumsq_mg,
        pe.eval_n_mg,
    )
    if pe.eval_n_mg >= 2:
        ci_low_pawns = (mean_cp - ci_half_width) / 100.0
        ci_high_pawns = (mean_cp + ci_half_width) / 100.0
```

**Wilson helper consumption pattern** — RESEARCH.md Example 2:
```python
from app.services.score_confidence import compute_confidence_bucket
confidence, p_value, se = compute_confidence_bucket(w, d, l, n)
```

**N-gate-to-None pattern (Pitfall 5)** — apply explicitly:
```python
entry_eval_p_value: float | None = p_eval if eval_n >= 10 else None
endgame_score_p_value: float | None = p_score if endgame_wdl.total >= 10 else None
```

**Mate / NULL exclusion (Pitfall 3)** — never use `or` for numeric defaulting on Optional columns:
```python
# Per row from query_endgame_entry_rows: (game_id, endgame_class, result, user_color, eval_cp, eval_mate)
if row.eval_mate is not None:
    continue  # mate-excluded per D-07
if row.eval_cp is None:
    continue  # NULL eval excluded
```

---

### `app/schemas/endgames.py::EndgamePerformanceResponse` (schema, request-response)

**Analog:** the model itself (line 107). Pattern is additive — append four optional-with-default fields.

**Existing model** (lines 107-119):
```python
class EndgamePerformanceResponse(BaseModel):
    """Response for GET /api/endgames/performance (Phase 59-trimmed). ..."""

    endgame_wdl: EndgameWDLSummary
    non_endgame_wdl: EndgameWDLSummary
    endgame_win_rate: float
```

**Add for Phase 81 (per D-11; defaults per Pitfall 7):**
```python
    entry_eval_mean_pawns: float = 0.0
    entry_eval_n: int = 0
    entry_eval_p_value: float | None = None
    endgame_score_p_value: float | None = None
    # Optional whisker bounds for Tile 1 bullet (RESEARCH §Anti-Patterns rec):
    entry_eval_ci_low_pawns: float | None = None
    entry_eval_ci_high_pawns: float | None = None
```

**Defaults are mandatory** — backwards-compat with existing test fixtures that construct `EndgamePerformanceResponse(endgame_wdl=..., non_endgame_wdl=..., endgame_win_rate=...)`.

---

### `frontend/src/types/endgames.ts::EndgamePerformanceResponse` (type mirror, request-response)

**Analog:** the interface itself (line 58). Mirror the four/six new backend fields.

**Existing** (lines 58-62):
```typescript
export interface EndgamePerformanceResponse {
  endgame_wdl: EndgameWDLSummary;
  non_endgame_wdl: EndgameWDLSummary;
  endgame_win_rate: number;
}
```

**Add (mirror schema):**
```typescript
  entry_eval_mean_pawns: number;
  entry_eval_n: number;
  entry_eval_p_value: number | null;
  endgame_score_p_value: number | null;
  entry_eval_ci_low_pawns: number | null;
  entry_eval_ci_high_pawns: number | null;
```

---

### `frontend/src/components/charts/EndgameStartVsEndSection.tsx` (component, event-driven render — NEW)

**Analog:** `frontend/src/pages/openings/ExplorerTab.tsx` lines 92-202 (the `gamesData.stats.total > 0` block, rows 2 & 3). This is the canonical locked layout for both tiles.

**Imports pattern** (mirror `ExplorerTab.tsx` lines 1-33):
```typescript
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreBulletDomain,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { isConfident } from '@/lib/significance';
import { ZONE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { EndgamePerformanceResponse } from '@/types/endgames';
```

**Confidence-derivation pattern** (ExplorerTab.tsx lines 65-86) — the gating logic for "paint the value color only when confident AND outside the neutral band":
```typescript
const isUnreliable = stats.total < MIN_GAMES_FOR_RELIABLE_STATS;
const zoneHex = scoreZoneColor(stats.score);
const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
const showZoneFontColor = isConfident(stats.confidence) && isInColoredZone;
const scoreColor: string | undefined = showZoneFontColor ? zoneHex : undefined;
```

**For Phase 81:** confidence level must be derived on the frontend from `(p_value, n)` since the backend response only carries the raw p-value. Use the `deriveLevel` helper from RESEARCH.md Example 5:
```typescript
function deriveLevel(p: number | null, n: number): 'low' | 'medium' | 'high' {
  if (n < 10 || p == null) return 'low';
  if (p < 0.01) return 'high';
  if (p < 0.05) return 'medium';
  return 'low';
}
```

**Inline value row + popover + bullet chart** (ExplorerTab.tsx lines 120-200) — the locked tile body for both tiles:
```typescript
<div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
  {/* Inline value row */}
  <span className="flex items-center gap-1 text-sm tabular-nums w-full">
    <span className="text-muted-foreground">Score:</span>
    <span
      className="ml-auto font-semibold"
      style={scoreColor ? { color: scoreColor } : undefined}
    >
      {scorePct}%
    </span>
    <ScoreConfidencePopover
      level={stats.confidence}
      pValue={stats.p_value}
      score={stats.score}
      gameCount={stats.total}
      lastPlayedAt={stats.last_played_at}
      testId="score-bullet-popover-trigger"
    />
  </span>
  {/* Bullet chart */}
  <div className="min-w-0 tabular-nums">
    <MiniBulletChart
      value={stats.score}
      center={SCORE_BULLET_CENTER}
      neutralMin={SCORE_BULLET_NEUTRAL_MIN}
      neutralMax={SCORE_BULLET_NEUTRAL_MAX}
      domain={scoreBulletDomain()}
      ciLow={clampScoreCi(stats.ci_low)}
      ciHigh={clampScoreCi(stats.ci_high)}
      barColor="neutral"
    />
  </div>
</div>
```

**Tile 1 (entry-eval) value-line — eval row pattern** (ExplorerTab.tsx lines 156-200):
```typescript
{hasMgEval ? (
  <span
    className="ml-auto font-semibold inline-flex items-center gap-0.3"
    style={showEvalZoneFont && evalZoneHex ? { color: evalZoneHex } : undefined}
  >
    {formatSignedEvalPawns(stats.avg_eval_pawns as number)}
    <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
  </span>
) : (
  <span className="ml-auto text-muted-foreground">—</span>
)}
{hasMgEval && (
  <BulletConfidencePopover
    level={stats.eval_confidence}
    pValue={stats.eval_p_value}
    gameCount={stats.eval_n}
    evalMeanPawns={stats.avg_eval_pawns}
    color={filterColor}
    testId="eval-bullet-popover-trigger"
  />
)}
```

**Tile container styling** (ExplorerTab.tsx line 94):
```typescript
<div
  className="charcoal-texture rounded-md p-4 order-2 lg:order-1"
  style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
  data-testid="wdl-moves-position"
>
```

**For Phase 81:** the section is a 2-col grid container on `lg`+. Each tile is its own `charcoal-texture rounded-md p-4` card. Use `order-1 lg:order-1` for entry-eval and `order-2 lg:order-2` for score (D-17: chronological setup → execution on mobile).

**Use placeholder, not opacity dim, for n < 10** (per RESEARCH §Open Question 4). When `entry_eval_n < 10` show "Not enough data yet" text in place of the value row + chart pair; do NOT apply `UNRELIABLE_OPACITY`.

---

### `frontend/src/pages/Endgames.tsx` (page integration)

**Analog:** the `showPerfSection` block (lines 340-394) — the section's exact insertion home.

**Render-guard pattern** (line 321):
```typescript
const showPerfSection = !!(perfData && perfData.endgame_wdl.total > 0);
```

**Reuse this exact predicate for the new section** — D-06 says hide entire section when zero endgame games, which is identical to `showPerfSection`. No new predicate is needed; render the new section inside the same `{showPerfSection && (...)}` block.

**Insertion point** — between the `<Accordion ...>` close (line 391) and the existing `<div className="charcoal-texture rounded-md p-4">` wrapping `<EndgamePerformanceSection ...>` (line 392):
```typescript
</Accordion>
{/* NEW: */}
<EndgameStartVsEndSection data={perfData} />
{/* EXISTING: */}
<div className="charcoal-texture rounded-md p-4">
  <EndgamePerformanceSection data={perfData} scoreGap={scoreGapData} />
</div>
```

**Accordion concept-paragraphs pattern** (lines 350-388) — append two `<p>` blocks to the existing `<AccordionContent>` after the existing Conversion / Parity / Recovery paragraphs (lines 367-381) and before the rating-changes caveat (line 382-388):
```typescript
<p>
  <strong>Conversion:</strong> percentage of games where you entered the endgame with a
  Stockfish evaluation of +1.0 or better...
</p>
<p>
  <strong>Parity:</strong> ...
</p>
<p>
  <strong>Recovery:</strong> ...
</p>
{/* NEW for Phase 81 — D-13, D-14: insert here */}
<p>
  <strong>Avg eval at endgame entry:</strong> ...
</p>
<p>
  <strong>Absolute endgame score:</strong> ...
</p>
{/* EXISTING — rating-changes caveat */}
<p>
  Conversion and Recovery rates usually reflect your performance against opponents at your rating
  level...
</p>
```

---

### `frontend/src/lib/endgameEntryEvalZones.ts` (constants — NEW, optional)

**Analog:** `frontend/src/lib/openingStatsZones.ts` (sibling module).

**Imports pattern + constants pattern** (`openingStatsZones.ts` lines 22-52):
```typescript
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** MG: lower bound of the neutral zone in pawns (signed user-perspective, around 0 cp). */
export const EVAL_NEUTRAL_MIN_PAWNS = -0.30;

/** MG: upper bound of the neutral zone in pawns. Symmetric around 0. */
export const EVAL_NEUTRAL_MAX_PAWNS = 0.30;

/** MG: bullet-chart half-domain (in pawns). Values beyond +-domain clamp; CI whiskers go open-ended. */
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;

/** Pick the zone color for the MG-entry eval bullet relative to 0 cp. ... */
export function evalZoneColor(value: number): string {
  if (value >= EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (value <= EVAL_NEUTRAL_MIN_PAWNS) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
```

**For Phase 81 (per RESEARCH §Open Question 1, recommendation b):**
```typescript
/** EG-entry: neutral band, ±0.75 pawns from benchmark v3 §3c. */
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75;
export const ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = 0.75;

/** EG-entry: bullet-chart half-domain, D-15. */
export const ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0;

export function endgameEntryEvalZoneColor(value: number): string { ... }
```

---

### `tests/services/test_endgame_start_vs_end.py` (test — NEW)

**Analog (math-helper-test layout):** `tests/services/test_eval_confidence.py` (lines 1-100).

**Module docstring + import pattern** (`test_eval_confidence.py` lines 1-25):
```python
"""Unit tests for app.services.eval_confidence.compute_eval_confidence_bucket.

Bucketing rule under test (unified two-sided standard, 260505):
  - n < EVAL_CONFIDENCE_MIN_N (10) -> "low"  (unreliable-stats gate)
  ...
"""

import math

import pytest

from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.opening_insights_constants import EVAL_CONFIDENCE_MIN_N
```

**Edge-case test naming + assertion pattern** (`test_eval_confidence.py` lines 31-46):
```python
def test_n_zero_returns_low_one_zero_zero() -> None:
    """n=0: no data — returns ("low", 1.0, 0.0, 0.0) without raising."""
    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(0.0, 0.0, 0)
    assert confidence == "low"
    assert p_value == 1.0
    assert mean == 0.0
    assert ci_half_width == 0.0
```

**For Phase 81:** test the new aggregation in `_get_endgame_performance_from_rows` with NamedTuple stand-in rows mirroring `query_endgame_entry_rows` columns: `(game_id, endgame_class, result, user_color, eval_cp, eval_mate)`. Cover:
- Empty `entry_rows` → all four fields default (n=0, p=None, mean=0.0).
- n=9 → `entry_eval_p_value is None` (gate).
- n=10 with all-zero eval → `entry_eval_p_value == 1.0`.
- Per-game dedupe: same `game_id` appearing in two `endgame_class` spans counts once; `entry_eval_n == 1`.
- Sign flip: black user with `eval_cp = +200` produces `entry_eval_mean_pawns = -2.0`.
- Mate exclusion: row with `eval_mate=5, eval_cp=None` skipped → `entry_eval_n` decremented vs total.
- NULL exclusion: row with `eval_cp is None and eval_mate is None` skipped.

---

### `tests/test_endgame_service.py` (extend — schema contract)

**Analog:** existing test classes in the same file (e.g. `TestScoreGapMaterialInvariant` referenced in `endgame_service.py` line 738).

**Pattern:** add `class TestEndgamePerformanceContract` asserting all six new fields are present with correct types when `_get_endgame_performance_from_rows` is called with non-empty rows, and that defaults work when called with empty rows.

---

### `tests/test_endgames_router.py` (extend — API contract)

**Analog:** existing endgame router tests in the same file.

**Pattern:** add `test_overview_includes_start_vs_end_fields` that hits `/api/endgames/overview` and asserts the response JSON contains `performance.entry_eval_mean_pawns`, `performance.entry_eval_n`, `performance.entry_eval_p_value`, `performance.endgame_score_p_value` keys. Use the same auth + seeded-data fixtures already in the file.

---

### `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` (test — NEW)

**Analog:** `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` (lines 1-80).

**Vitest jsdom + Recharts mock + matchMedia/ResizeObserver stubs** (`EndgamePerformanceSection.test.tsx` lines 1-80):
```typescript
// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>...</div>
    ),
  };
});

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn().mockImplementation(...) });
  class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
  // ... assign to window
});
```

**For Phase 81:** test cases per RESEARCH.md "Phase Requirements → Test Map":
- `n < 10` → renders "Not enough data yet" placeholder, no `MiniBulletChart`.
- `n >= 10`, `p < 0.05`, `mean > 0` → value text gets `ZONE_SUCCESS` color.
- `n >= 10`, `p < 0.05`, `mean < 0` → value text gets `ZONE_DANGER` color.
- `n >= 10`, `p >= 0.05` → value text neutral (no inline color).
- Both tiles render in DOM order: entry-eval first (D-17 mobile order via natural document order).
- `MiniBulletChart` receives `domain={2.0}` and `center={0}` for Tile 1.
- `MiniBulletChart` receives `domain={SCORE_BULLET_DOMAIN}` and `center={SCORE_BULLET_CENTER}` for Tile 2.

---

## Shared Patterns

### Pattern A: Three-state zone color (gated on confidence)
**Source:** `frontend/src/pages/openings/ExplorerTab.tsx` lines 65-73 + `frontend/src/lib/significance.ts`
**Apply to:** `EndgameStartVsEndSection.tsx` (both tiles)

```typescript
import { isConfident } from '@/lib/significance';
import { ZONE_SUCCESS, ZONE_DANGER, ZONE_NEUTRAL } from '@/lib/theme';

const zoneHex = /* SUCCESS / DANGER / NEUTRAL based on neutral band */;
const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
const showZoneFontColor = isConfident(level) && isInColoredZone;
const valueColor: string | undefined = showZoneFontColor ? zoneHex : undefined;
```

### Pattern B: Per-game dedupe over `entry_rows`
**Source:** `app/services/endgame_service.py::_compute_score_gap_material` lines 744-775
**Apply to:** new aggregation in `_get_endgame_performance_from_rows`

```python
rows_by_game: dict[int, list[Row[Any]]] = defaultdict(list)
for row in entry_rows:
    rows_by_game[row.game_id].append(row)
for game_id, game_rows in rows_by_game.items():
    chosen = min(game_rows, key=lambda r: r.endgame_class)  # deterministic
    # ... apply mate/NULL filter, sign flip, accumulate ...
```

### Pattern C: Stat-helper consumption (Wald-z + Wilson)
**Source:** `app/services/stats_service.py` lines 410-425 (Wald-z), `app/services/score_confidence.py` docstring (Wilson)
**Apply to:** new aggregation in `_get_endgame_performance_from_rows`

```python
from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.score_confidence import compute_confidence_bucket

confidence_e, p_eval, mean_cp, ci_half = compute_eval_confidence_bucket(eval_sum, eval_sumsq, eval_n)
confidence_s, p_score, _se = compute_confidence_bucket(wins, draws, losses, total)

# N-gate to None per D-11 (Pitfall 5):
entry_eval_p_value = p_eval if eval_n >= 10 else None
endgame_score_p_value = p_score if total >= 10 else None
```

### Pattern D: Tile container card styling
**Source:** `frontend/src/pages/openings/ExplorerTab.tsx` line 94
**Apply to:** both tiles in `EndgameStartVsEndSection.tsx`

```typescript
<div
  className="charcoal-texture rounded-md p-4"
  data-testid="tile-entry-eval"  // or "tile-endgame-score"
>
  <h3 className="text-base font-semibold mb-2">{punchyTitle}</h3>
  {/* inline value row + bullet chart grid */}
</div>
```

Two-column wrapper: `<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">`.

### Pattern E: Section-render guard (hide when no data)
**Source:** `frontend/src/pages/Endgames.tsx` line 321
**Apply to:** entry point in `Endgames.tsx`

```typescript
// Reuse the existing showPerfSection — D-06 hide-when-zero matches exactly.
{showPerfSection && (
  <>
    <h2>Endgame Overall Performance</h2>
    <Accordion ... />
    <EndgameStartVsEndSection data={perfData} />  {/* NEW */}
    <div className="charcoal-texture rounded-md p-4">
      <EndgamePerformanceSection ... />
    </div>
  </>
)}
```

### Pattern F: Pydantic schema additive extension with defaults
**Source:** `app/schemas/endgames.py` (existing model patterns)
**Apply to:** `EndgamePerformanceResponse` (D-11)

```python
# Defaults required for backwards-compat with existing test fixtures
# that construct EndgamePerformanceResponse(endgame_wdl=..., non_endgame_wdl=...,
# endgame_win_rate=...) — see Pitfall 7.
new_field: float = 0.0
new_optional: float | None = None
```

### Pattern G: TypeScript type-mirror parity with backend schema
**Source:** `frontend/src/types/endgames.ts` (entire file is mirror-pattern)
**Apply to:** `EndgamePerformanceResponse` interface

Mirror exact field names + types; `float | None` → `number | null`; default values are NOT mirrored (TypeScript types describe wire shape only).

---

## No Analog Found

None. Every artifact has a verified, in-tree analog at file:line precision (per RESEARCH.md §Sources).

---

## Metadata

**Analog search scope:**
- `app/services/endgame_service.py` (full read of relevant ranges 1-250, 700-787, 1620-1712, 1900-2017)
- `app/services/eval_confidence.py`, `app/services/score_confidence.py` (full reads)
- `app/schemas/endgames.py` lines 85-220
- `app/repositories/endgame_repository.py` lines 140-230
- `frontend/src/pages/openings/ExplorerTab.tsx` (full read)
- `frontend/src/pages/Endgames.tsx` lines 315-410
- `frontend/src/components/insights/BulletConfidencePopover.tsx`, `ScoreConfidencePopover.tsx` (full reads)
- `frontend/src/lib/scoreBulletConfig.ts`, `openingStatsZones.ts`, `significance.ts` (full reads)
- `frontend/src/types/endgames.ts` lines 1-100
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` lines 1-80
- `tests/services/test_eval_confidence.py` lines 1-80
- `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` lines 1-80

**Files scanned:** 14 source/test files
**Pattern extraction date:** 2026-05-09
