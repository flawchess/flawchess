# Phase 53: Endgame Score Gap & Material Breakdown - Research

**Researched:** 2026-04-12
**Domain:** Endgame analytics — score difference metric and material-stratified WDL table
**Confidence:** HIGH (all codebase findings verified by direct inspection)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per user request.

### Claude's Discretion
All implementation choices are at Claude's discretion. Detailed specs are in
`docs/endgame-analysis-v2.md` sections 1-2. Use ROADMAP phase goal, success
criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.
</user_constraints>

---

## Summary

Phase 53 adds two new metrics to the Endgames page Stats tab: an **Endgame Score
Difference** (signed number showing endgame score minus non-endgame score) and a
**Material-Stratified WDL Table** (three rows: Ahead / Equal / Behind based on
`material_imbalance` at endgame entry). Both answers the question *"how much worse
do I score in endgames, and does my starting material situation matter?"*

The data pipeline for both metrics already exists. `query_endgame_performance_rows`
already returns WDL rows for endgame vs non-endgame games. `query_endgame_entry_rows`
already returns `(game_id, endgame_class, result, user_color, user_material_imbalance,
user_material_imbalance_after)` — the exact columns needed for material bucket
classification. The overall score needed for Verdict calibration can be computed from
the existing `endgame_wdl` + `non_endgame_wdl` already present in
`EndgamePerformanceResponse`.

**Primary recommendation:** Extend `EndgameOverviewResponse` with a new
`score_gap_material` field by adding a pure Python aggregation function in
`endgame_service.py` that reuses the `entry_rows` already fetched by
`get_endgame_performance`. No new DB queries are needed — all data is already
retrieved in `get_endgame_overview`.

---

## Standard Stack

Phase 53 uses no new libraries. Everything is built on the existing stack.
[VERIFIED: direct codebase inspection]

| Layer | Existing Tooling | Purpose |
|-------|-----------------|---------|
| Backend schema | `app/schemas/endgames.py` (Pydantic v2) | New response models |
| Backend service | `app/services/endgame_service.py` | Aggregation logic |
| Backend router | `app/routers/endgames.py` | No changes needed |
| Frontend types | `frontend/src/types/endgames.ts` | New TS interfaces |
| Frontend API client | `frontend/src/api/client.ts` | No changes needed |
| Frontend hook | `frontend/src/hooks/useEndgames.ts` | No changes needed |
| Frontend component | New `EndgameScoreGapSection.tsx` | New section component |
| Frontend page | `frontend/src/pages/Endgames.tsx` | Render new section |

---

## Architecture Patterns

### Existing Data Flow (Phase 52 overview endpoint)

```
GET /api/endgames/overview
  └─ endgame_service.get_endgame_overview()
       ├─ get_endgame_stats()         → query_endgame_entry_rows()
       ├─ get_endgame_performance()   → query_endgame_performance_rows()
       │                                query_endgame_entry_rows()   (second call)
       ├─ get_endgame_timeline()      → query_endgame_timeline_rows()
       └─ get_conv_recov_timeline()   → query_conv_recov_timeline_rows()
```

`get_endgame_overview` currently calls `get_endgame_performance`, which internally
calls **both** `query_endgame_performance_rows` and `query_endgame_entry_rows`
independently. The `entry_rows` result from `get_endgame_performance` is lost after
gauge computation — it is not threaded through to `get_endgame_overview`.

### Recommended Extension: Add `score_gap_material` to `EndgameOverviewResponse`

The cleanest approach is a **new helper function** in `endgame_service.py`:

```python
def _compute_score_gap_material(
    endgame_wdl: EndgameWDLSummary,
    non_endgame_wdl: EndgameWDLSummary,
    entry_rows: list[Row[Any]],
) -> ScoreGapMaterialResponse:
    ...
```

This function is called inside `get_endgame_overview` using the `entry_rows` already
fetched by `get_endgame_performance`. To enable this, `get_endgame_performance` should
return its `entry_rows` alongside the `EndgamePerformanceResponse`, OR the
`get_endgame_overview` refactors to call the repository functions directly and pass
`entry_rows` to both `get_endgame_performance` and `_compute_score_gap_material`.

**Preferred approach:** Refactor `get_endgame_overview` to fetch `entry_rows` once
and thread them into both `get_endgame_performance` (which currently fetches them
again internally) and `_compute_score_gap_material`. This eliminates the redundant
second `query_endgame_entry_rows` call inside `get_endgame_performance`.

Concretely: extract a new private `_get_endgame_performance_from_rows` that takes
pre-fetched `entry_rows` as a parameter. Call it from `get_endgame_overview`. The
public `get_endgame_performance` (used in tests) stays but delegates to the inner
function.

### Score Formula [VERIFIED: docs/endgame-analysis-v2.md section 1]

```
Score = (Win% + Draw% / 2) / 100          # range 0.0 to 1.0
Endgame Score Difference = Endgame Score − Non-endgame Score
```

Both `endgame_wdl` and `non_endgame_wdl` are already fields in
`EndgamePerformanceResponse` and available in `get_endgame_overview`. These carry
`win_pct` and `draw_pct` as `float` (0-100), so:

```python
def _wdl_to_score(wdl: EndgameWDLSummary) -> float:
    return (wdl.win_pct + wdl.draw_pct / 2) / 100
```

### Material Buckets [VERIFIED: docs/endgame-analysis-v2.md section 2]

| Bucket Label | Condition on `user_material_imbalance` |
|---|---|
| `ahead` | `>= 100` (centipawns) |
| `equal` | `> -100 and < 100` |
| `behind` | `<= -100` |

`user_material_imbalance` at endgame entry is already sign-flipped in
`query_endgame_entry_rows` so positive = user ahead. No further transformation
needed. [VERIFIED: endgame_repository.py lines 156-170]

**Important:** Unlike conversion/recovery, material buckets for this table do NOT
require the persistence check (no `user_material_imbalance_after` filter). The spec
says "material balance at the first ply of each endgame span (same entry logic as
conversion/recovery)" — referring to the entry logic (first ply of span), not the
persistence filter. The table shows all endgame entries regardless of whether the
imbalance persisted. [VERIFIED: docs/endgame-analysis-v2.md section 2]

### Verdict Calibration [VERIFIED: docs/endgame-analysis-v2.md section 2]

Verdicts are relative to the user's **overall score** (across all games, not just
endgames):

```
overall_score = (endgame_score * endgame_total + non_endgame_score * non_endgame_total) / total_games
```

Or equivalently computed from combined WDL:
```
overall_win_pct  = (endgame_wdl.wins + non_endgame_wdl.wins) / total * 100
overall_draw_pct = (endgame_wdl.draws + non_endgame_wdl.draws) / total * 100
overall_score    = (overall_win_pct + overall_draw_pct / 2) / 100
```

Thresholds:
- `row_score >= overall_score` → `"good"`
- `row_score >= overall_score - 0.05` → `"ok"`
- `row_score < overall_score - 0.05` → `"bad"`

### Recommended Project Structure Extension

```
app/schemas/endgames.py          # Add MaterialRow, ScoreGapMaterialResponse
app/services/endgame_service.py  # Add _compute_score_gap_material(),
                                 #   refactor get_endgame_performance internals
frontend/src/types/endgames.ts   # Add MaterialRow, ScoreGapMaterialResponse
frontend/src/components/charts/  # Add EndgameScoreGapSection.tsx
frontend/src/pages/Endgames.tsx  # Render new section after conv/recov timeline
```

### Anti-Patterns to Avoid

- **Do NOT add a new DB query.** All data is in `entry_rows` already fetched. A new
  repo function would be wasteful and violates the Phase 52 consolidation intent.
- **Do NOT asyncio.gather.** The codebase is explicit: AsyncSession is not safe for
  concurrent use. `get_endgame_overview` already runs sequentially. [VERIFIED:
  endgame_repository.py lines 424-428, endgame_service.py line 843 comment]
- **Do NOT duplicate the material-entry logic.** `query_endgame_entry_rows` already
  computes `user_material_imbalance` from the first ply of each span using the
  array_agg pattern. Reuse those rows.
- **Do NOT hard-code color values in the new component.** Use `WDL_WIN`, `WDL_LOSS`,
  `GAUGE_WARNING`, and `GAUGE_SUCCESS` from `frontend/src/lib/theme.ts`. [VERIFIED:
  CLAUDE.md "Theme constants in theme.ts"]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score calculation | Custom score function | Inline arithmetic using existing `win_pct` / `draw_pct` | One-liner; no abstraction needed |
| WDL aggregation | New query | Iterate over `entry_rows` already returned | Same rows used by conversion/recovery |
| Verdict logic | Complex rule engine | Simple threshold comparisons in Python | Three cases only |
| Overall score | Second DB query | Compute from `endgame_wdl` + `non_endgame_wdl` | Both already in `get_endgame_performance` |

---

## Schema Design

### Backend — New Pydantic Models (add to `app/schemas/endgames.py`)

```python
# Source: docs/endgame-analysis-v2.md sections 1-2
MaterialBucket = Literal["ahead", "equal", "behind"]
Verdict = Literal["good", "ok", "bad"]

class MaterialRow(BaseModel):
    bucket: MaterialBucket         # "ahead" | "equal" | "behind"
    label: str                     # "Ahead (≥ +1)" | "Equal" | "Behind (≤ −1)"
    games: int
    win_pct: float                 # 0-100
    draw_pct: float                # 0-100
    loss_pct: float                # 0-100
    score: float                   # 0.0-1.0
    verdict: Verdict               # "good" | "ok" | "bad"

class ScoreGapMaterialResponse(BaseModel):
    endgame_score: float           # 0.0-1.0
    non_endgame_score: float       # 0.0-1.0
    score_difference: float        # endgame_score - non_endgame_score (signed)
    overall_score: float           # user's overall score across ALL games
    material_rows: list[MaterialRow]   # 3 rows: ahead / equal / behind
```

`EndgameOverviewResponse` gains a new field:
```python
class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    conv_recov_timeline: ConvRecovTimelineResponse
    score_gap_material: ScoreGapMaterialResponse  # NEW
```

### Frontend — New TypeScript Interfaces (add to `frontend/src/types/endgames.ts`)

```typescript
export type MaterialBucket = 'ahead' | 'equal' | 'behind';
export type Verdict = 'good' | 'ok' | 'bad';

export interface MaterialRow {
  bucket: MaterialBucket;
  label: string;
  games: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  score: number;
  verdict: Verdict;
}

export interface ScoreGapMaterialResponse {
  endgame_score: number;
  non_endgame_score: number;
  score_difference: number;
  overall_score: number;
  material_rows: MaterialRow[];
}

// Update EndgameOverviewResponse:
export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  conv_recov_timeline: ConvRecovTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;  // NEW
}
```

---

## Common Pitfalls

### Pitfall 1: Forgetting the No-Persistence Rule for Material Buckets
**What goes wrong:** Applying the persistence filter (`user_material_imbalance_after`)
to the material table rows, matching the conversion/recovery pattern.
**Why it happens:** `query_endgame_entry_rows` returns both entry AND
`entry_imbalance_after`. The spec explicitly says "same entry logic as
conversion/recovery" — but it means the entry *detection* only (first ply of span
with ≥ 6 plies), not the persistence check.
**How to avoid:** Only use `user_material_imbalance` (not `user_material_imbalance_after`)
for bucket assignment in `_compute_score_gap_material`.

### Pitfall 2: Double-Counting Multi-Class Games
**What goes wrong:** A single game can appear multiple times in `entry_rows` (once per
endgame class it spent ≥ 6 plies in). Counting each row as a distinct game inflates
the total for the material table.
**Why it happens:** `query_endgame_entry_rows` returns one row per `(game_id,
endgame_class)` pair, not per game. [VERIFIED: endgame_repository.py line 85-90]
**How to avoid:** The material table should count **games, not spans**. Deduplicate by
`game_id` before bucketing — keep only the first (or any deterministic) span per
game_id. This matches how `endgame_performance_rows` works: it returns one row per
game via `query_endgame_performance_rows`.

**Resolution options:**
1. Use `query_endgame_performance_rows` (already deduplicated per game) for the
   WDL side and `query_endgame_entry_rows` (deduped in Python) for the material bucket.
2. Or: deduplicate `entry_rows` in Python by `game_id` (keeping the first row per
   game), then assign material bucket from that row's `user_material_imbalance`.

Option 2 is simpler since `entry_rows` already carries both result and imbalance.

### Pitfall 3: ty Type-Check Failures on New Service Functions
**What goes wrong:** New functions fail `uv run ty check app/ tests/` due to missing
return type annotations or use of `list[str]` instead of `Sequence[str]` for parameters.
**Why it happens:** `ty` is strict; list is invariant, Sequence is covariant.
**How to avoid:** Follow CLAUDE.md: use `Sequence[str]` for filter params, add explicit
return types on all functions, use `# ty: ignore[rule-name]` with reason for unfixable
errors.

### Pitfall 4: Missing `data-testid` on New Frontend Elements
**What goes wrong:** CI knip pass or automation tests fail to find interactive elements.
**Why it happens:** CLAUDE.md mandates `data-testid` on every interactive element
with component-prefixed kebab-case naming.
**How to avoid:** All buttons, table rows (dynamic elements), and section containers in
`EndgameScoreGapSection.tsx` need `data-testid`. Example:
`data-testid="score-gap-section"`, `data-testid="material-row-ahead"`.

### Pitfall 5: Hard-coding Color Values
**What goes wrong:** Using inline hex/oklch strings instead of theme constants for
verdict colors (green/yellow/red).
**Why it happens:** Quick implementation.
**How to avoid:** Import `WDL_WIN`, `WDL_LOSS`, `GAUGE_WARNING` from `lib/theme.ts`.
Add verdict-color constants there if not already present.

### Pitfall 6: Missing Mobile Section
**What goes wrong:** The new section appears on desktop but not mobile (or vice versa).
**Why it happens:** `Endgames.tsx` has separate `statisticsContent` JSX that renders
inside BOTH the desktop SidebarLayout and the mobile `<div className="md:hidden">`.
Both read from the same `statisticsContent` variable (see lines 234-297 and 497/503).
**How to avoid:** Since `statisticsContent` is a single variable consumed in both the
desktop TabsContent and mobile TabsContent, adding the new section to `statisticsContent`
once covers both layouts automatically. No separate mobile section needed.
[VERIFIED: Endgames.tsx lines 424-425 and 497]

---

## Code Examples

### Score Computation
```python
# Source: docs/endgame-analysis-v2.md section 1
def _wdl_to_score(wdl: EndgameWDLSummary) -> float:
    """Convert WDL summary to score in range 0.0-1.0."""
    if wdl.total == 0:
        return 0.0
    return (wdl.win_pct + wdl.draw_pct / 2) / 100
```

### Material Bucket Assignment (deduplicating multi-class games)
```python
# Source: docs/endgame-analysis-v2.md section 2 + endgame_repository.py entry logic
# entry_rows: list[(game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after)]
seen_game_ids: set[int] = set()
bucket_rows: list[tuple] = []
for row in entry_rows:
    game_id = row[0]
    if game_id not in seen_game_ids:
        seen_game_ids.add(game_id)
        bucket_rows.append(row)

# Now assign buckets from bucket_rows (one per game)
for _game_id, _class, result, user_color, user_material_imbalance, _after in bucket_rows:
    if user_material_imbalance is None:
        continue
    if user_material_imbalance >= 100:
        bucket = "ahead"
    elif user_material_imbalance <= -100:
        bucket = "behind"
    else:
        bucket = "equal"
```

### Verdict Computation
```python
# Source: docs/endgame-analysis-v2.md section 2
def _compute_verdict(row_score: float, overall_score: float) -> Verdict:
    if row_score >= overall_score:
        return "good"
    elif row_score >= overall_score - 0.05:
        return "ok"
    else:
        return "bad"
```

### Frontend: Score Difference Display (color coding)
```tsx
// Source: docs/endgame-analysis-v2.md section 1
// Green ≥ 0, red < 0
const scoreDiff = data.score_gap_material.score_difference;
const color = scoreDiff >= 0 ? 'text-green-600' : 'text-red-600';
const sign = scoreDiff >= 0 ? '+' : '';
<span className={color}>{sign}{scoreDiff.toFixed(3)}</span>
```

### Frontend: Verdict Badge (use theme colors)
```tsx
// Source: CLAUDE.md "Theme constants in theme.ts"
import { WDL_WIN, WDL_LOSS, GAUGE_WARNING } from '@/lib/theme';

const VERDICT_COLORS: Record<Verdict, string> = {
  good: WDL_WIN,    // green
  ok: GAUGE_WARNING, // amber
  bad: WDL_LOSS,    // red
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| 4 separate HTTP requests | Single `/overview` endpoint | Phase 52 | New data must go into `EndgameOverviewResponse` |
| `asyncio.gather` | Sequential execution on one session | Phase 52 design | Cannot parallelize queries |

---

## Assumptions Log

All claims in this research were verified by direct codebase inspection or the spec
document. No `[ASSUMED]` tags were used.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims were verified or cited — no user confirmation needed.**

---

## Open Questions

1. **Double-count deduplication strategy for material table**
   - What we know: `entry_rows` has one row per `(game_id, endgame_class)` so a game
     with rook + pawn endgame spans appears twice.
   - What's unclear: should we use the first span's imbalance, the worst-case span, or
     average? The spec says "material balance at the first ply of each endgame span" but
     is silent on deduplication at game level.
   - Recommendation: Use the first occurrence (minimum `ply`), which is already the
     ordering from `array_agg(ORDER BY ply ASC)`. Since `entry_rows` is fetched without
     explicit ordering, use Python dict insertion order (first `game_id` seen) which
     reflects whatever DB ordering applies. If strict determinism is required, sort
     `entry_rows` by `game_id` and `endgame_class` first.

2. **Handling zero-game buckets**
   - What we know: Some users may have zero games in a bucket (e.g. never entered an
     endgame while ahead).
   - Recommendation: Include all three rows always, with `games=0`, `score=0.0`, and
     `verdict="bad"`. This prevents the frontend from needing to handle missing rows.
     Alternatively, the frontend can render a "—" or dim row for empty buckets.

---

## Environment Availability

Step 2.6: SKIPPED — no external dependencies. Phase is pure code/logic addition to
existing backend and frontend. No new packages, CLIs, or services required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| SC-1 | Score difference formula: (win% + draw%/2)/100 signed float | unit | `uv run pytest tests/test_endgame_service.py::TestScoreGapMaterial -x` | ❌ Wave 0 |
| SC-2 | Material buckets: ahead/equal/behind WDL with correct games, percentages, score, verdict | unit | same | ❌ Wave 0 |
| SC-3 | Multi-class game deduplication: game counted once in material table | unit | same | ❌ Wave 0 |
| SC-4 | Verdict calibration: good/ok/bad relative to overall_score | unit | same | ❌ Wave 0 |
| SC-5 | `GET /endgames/overview` includes `score_gap_material` field with correct shape | integration | `uv run pytest tests/test_endgames_router.py -x` | ✅ (add test cases) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_endgame_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + `uv run ty check app/ tests/` before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_endgame_service.py` — add `TestScoreGapMaterial` class (file exists, add new class)
- [ ] `tests/test_endgames_router.py` — add overview field presence test (file exists, add test case)

*(No new test files needed — extend existing test files)*

---

## Security Domain

Phase 53 adds read-only analytics metrics derived from existing stored game data. No
new authentication, session management, access control changes, or cryptographic
operations. No external input beyond existing filter parameters (already validated by
FastAPI query params on existing endpoint).

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | Existing JWT auth unchanged |
| V3 Session Management | no | No new session logic |
| V4 Access Control | no | Same `current_active_user` guard |
| V5 Input Validation | yes (existing) | FastAPI Query() validators on filter params |
| V6 Cryptography | no | No new crypto |

No new threat patterns — existing SQL injection protection via SQLAlchemy ORM is
unchanged. No user-supplied strings are interpolated into queries.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `app/repositories/endgame_repository.py` — `query_endgame_entry_rows` signature,
  columns, sign flip, deduplication behavior
- `app/services/endgame_service.py` — `get_endgame_overview`, `get_endgame_performance`,
  `_aggregate_endgame_stats`, `_MATERIAL_ADVANTAGE_THRESHOLD=100`
- `app/schemas/endgames.py` — all existing response models, `EndgameOverviewResponse`
- `frontend/src/types/endgames.ts` — TS interfaces
- `frontend/src/pages/Endgames.tsx` — `statisticsContent` shared across desktop/mobile
- `frontend/src/lib/theme.ts` — color constants
- `docs/endgame-analysis-v2.md` sections 1-2 — formulas, bucket thresholds, verdict
  calibration
- `CLAUDE.md` — ty compliance, theme.ts rule, data-testid rule, no asyncio.gather

### Secondary (MEDIUM confidence)
- `tests/test_endgame_service.py` — existing test patterns to extend
- `tests/test_endgames_router.py` — existing router test patterns to extend

---

## Metadata

**Confidence breakdown:**
- Data pipeline: HIGH — all needed data already fetched by existing queries
- Schema design: HIGH — follows established Pydantic v2 patterns in this codebase
- Frontend integration: HIGH — `statisticsContent` variable covers both desktop and mobile automatically
- Deduplication: MEDIUM — spec says "same entry logic as conversion/recovery" but
  is silent on what to do when a game has multiple class spans; recommendation is
  first-seen which is deterministic

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable codebase; changes only if Phase 53 is deferred past Phase 54)
