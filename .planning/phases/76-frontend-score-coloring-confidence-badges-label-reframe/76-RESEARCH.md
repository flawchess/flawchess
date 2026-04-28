# Phase 76: Frontend — score-based coloring, confidence badges, label reframe - Research

**Researched:** 2026-04-28
**Domain:** React/TypeScript frontend rewire + targeted backend extension (Pydantic schema, Python helper module migration)
**Confidence:** HIGH (all file shapes verified by direct read; ambiguity resolved against actual source)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Section titles, card copy, sort order**
- **D-01:** Section titles unchanged — "White Opening Weaknesses" / "Black Opening Weaknesses" / "White Opening Strengths" / "Black Opening Strengths". Confidence + sort carry the SEED-008 calibration.
- **D-02:** Card prose: `You score X% as White after <san>` for both weakness and strength sections. X% = `round(finding.score * 100)`. Border-tint via existing `getSeverityBorderColor` unchanged.
- **D-03:** Sort within each section: `confidence DESC, then |score − 0.50| DESC`. Implemented in `compute_insights` (backend).
- **D-04 (descopes INSIGHT-UI-04):** "Soften severity copy" descopes — severity word ("major"/"minor") never appears as user-facing text today; stays that way.

**Confidence on moves-list rows (INSIGHT-UI-03)**
- **D-05:** Backend extends `NextMoveEntry` — gains `confidence: Literal["low","medium","high"]` and `p_value: float`.
- **D-06:** New module `app/services/score_confidence.py`. Phase 75's `_compute_confidence` migrates here. Both `opening_insights_service.compute_insights` AND the moves-explorer query path import from it.
- **D-07:** Confidence computed Python-side, post-aggregation. No SQL push.
- **D-08:** New "Conf" column between Games and Results. Visible desktop and mobile. Labels: `low` / `med` / `high`. Plain small grey text. Header text: "Conf".

**Confidence on Opening Insights cards (INSIGHT-UI-05)**
- **D-09:** `OpeningFindingCard` adds line under prose: `Confidence: low/medium/high` (full words). Plain grey style.
- **D-10:** Hover tooltip on the "Confidence: …" line, level-specific:
  - `low` → "small sample, treat as a hint"
  - `medium` → "enough games to trust the direction"
  - `high` → "sample is large enough to trust the magnitude"

**Mute rule**
- **D-11:** Existing `UNRELIABLE_OPACITY = 0.5` applied to row OR card when `n_games < 10` OR `confidence === "low"`. Reuses existing mechanism — no new theme constants.

**Score-based coloring (INSIGHT-UI-01, INSIGHT-UI-02)**
- **D-12:** `getArrowColor()` body migrates to score-based effect-size buckets, strict ≥/≤ boundaries, using `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`. `MIN_GAMES_FOR_COLOR < gameCount` guard stays. Hover blue stays.
- **D-13:** Signature: `getArrowColor(score, gameCount, isHovered)`. Drop `winPct` and `lossPct`. `NextMoveEntry` schema gains `score: float` on backend.
- **D-14:** Move Explorer row tint uses same `getArrowColor()` output (score-based).
- **D-15:** Old constants `LIGHT_COLOR_THRESHOLD` / `DARK_COLOR_THRESHOLD` removed from `arrowColor.ts`.

**Explainer popover (INSIGHT-UI-06)**
- **D-16:** Four `InfoPopover` icons, one per section title. All four show same copy.
- **D-17:** Popover copy in single exported constant in `openingInsights.ts` (replacing stale `INSIGHT_THRESHOLD_COPY`). Draft A score-first three-paragraph form (text in CONTEXT.md).
- **D-18:** No block-level "Opening Insights" title.

**Stale-code cleanup**
- **D-19:** `OpeningFindingCard.tsx:25-27` reads removed `loss_rate` / `win_rate` — D-02 prose migration fixes this.
- **D-20:** `frontend/src/lib/openingInsights.ts`: `MIN_GAMES_FOR_INSIGHT` → 10 (or rename); `INSIGHT_RATE_THRESHOLD` → remove; `INSIGHT_THRESHOLD_COPY` → remove.
- **D-21:** `frontend/src/types/insights.ts` `OpeningInsightFinding` — remove `loss_rate`, `win_rate`; add `confidence: 'low' | 'medium' | 'high'`, `p_value: number`.

**CI consistency test**
- **D-22:** `tests/services/test_opening_insights_arrow_consistency.py` extended to assert moves-explorer payload `confidence` field comes from same shared helper. Or: replace with unit test of `score_confidence.compute_confidence_bucket()` covering boundary cases.

**Out-of-scope clarifications**
- **D-23:** Arrows stay confidence-agnostic — no opacity, dashing, or dotting cue.
- **D-24:** No changes to `_dedupe_continuations`, `_dedupe_within_section`, attribution pipeline, section caps.
- **D-25:** Mobile parity satisfied by D-08, D-09, D-16, D-11.

### Claude's Discretion
- Mobile pixel width of "Conf" column (responsive Tailwind classes) — must fit 375px alongside Move + Games + WDL.
- Whether D-10 tooltip uses `Tooltip` (existing in `OpeningFindingCard.tsx:68,80`) or a small custom span. `Tooltip` is the obvious pick unless touch breaks.
- Score-prose rounding edge cases (e.g. 0.499 → "50%" but classified weakness): consistency at display required; fall back to `.toFixed(1)` if needed.
- Whether the Conf column header itself gets InfoPopover or just title-tooltip — section-title popover already covers framing; column-header tooltip optional.

### Deferred Ideas (OUT OF SCOPE)
- `getSeverityBorderColor` simplification — Claude's discretion later, not locked.
- Calibrating `low / medium / high` boundaries against real data — already deferred from Phase 75.
- Extending `(low) / (medium) / (high)` cue to other chart surfaces (WinRateChart, EndgameTimelineChart) — out of scope for v1.14.
- Surfacing raw p-value or half-width to power users — explicitly rejected.
- LLM narration over opening findings — future seed beyond v1.14.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSIGHT-UI-01 | Migrate `arrowColor.ts` from loss-rate to score; effect-size only color encoding (no opacity/dashing). | D-12, D-13, D-15 — body rewrite + signature change + dead constant removal. Phase 75 additive exports `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` already in place at `arrowColor.ts:21-23`. |
| INSIGHT-UI-02 | Migrate Move Explorer moves-list row tint to score (same color encoding as arrows). WDL bars unchanged. | D-14 + D-13 — `MoveExplorer.tsx:228` call-site updates from `entry.win_pct, entry.loss_pct` to `entry.score`. Existing `severityColor = arrowColor === GREY ? null : arrowColor` pattern at line 229 stays. |
| INSIGHT-UI-03 | Three-level confidence indicator on Move Explorer rows (`low / med / high`), backend-supplied. | D-05, D-06, D-08 — `NextMoveEntry` gains `confidence` + `p_value` + `score`. Shared helper `score_confidence.py` invoked by `get_next_moves`. New table column "Conf". |
| INSIGHT-UI-05 | Confidence badge on each `OpeningFindingCard`, plus prose migration. | D-02, D-09 — prose rewrite, new "Confidence: …" line, level tooltip per D-10. Backend (Phase 75) already supplies `confidence` and `p_value`; only frontend type catch-up needed (D-21). |
| INSIGHT-UI-06 | Explainer popover triggered from `?` icon on section titles. | D-16, D-17 — four `InfoPopover` icons in `OpeningInsightsBlock` (lines 199-209), single shared copy constant in `openingInsights.ts`. |
| INSIGHT-UI-07 | Mobile parity at 375px: no horizontal scroll, ≥44px touch, `data-testid` on all interactive elements. | D-08 (Conf column visible mobile), D-09 (Confidence line wraps in card prose flex column), D-16 (`InfoPopover` already tap-friendly via Stats tabs usage), D-11 (opacity rule viewport-agnostic). |
| INSIGHT-UI-04 | DESCOPED per D-04 (no-op — severity word not user-facing). | Confidence + sort calibration carries the SEED-008 intent. Apply REQUIREMENTS.md amendment at phase commit time. |
</phase_requirements>

## Summary

This phase consumes the Phase 75 backend contract (already shipped via PR #69) and rewires three frontend surfaces — Move Explorer arrows, Move Explorer moves-list rows, and the Opening Insights cards/section titles — to use chess score `(W+0.5·D)/N` with low/medium/high confidence annotation. One targeted backend extension (locked at D-05/D-06/D-07) adds `score`, `confidence`, and `p_value` fields to `NextMoveEntry` and migrates Phase 75's `_compute_confidence` helper from `opening_insights_service.py:105-152` to a new shared module `app/services/score_confidence.py`.

Almost every locked decision in CONTEXT.md is a mechanical edit — file shapes, function signatures, and call sites have been verified via direct source read. The riskiest area is **mobile column width** for the new "Conf" column on a viewport that already carries Move + Games + WDL bar at 375px. Second-riskiest is **`OpeningFindingCard.tsx:25-27`**: the file currently reads removed `loss_rate` / `win_rate` fields, so it has been broken since Phase 75 backend shipped — D-02 prose migration repairs this in the same commit. [VERIFIED: file read]

**Primary recommendation:** Plan as four task clusters: (1) shared helper + schema (`score_confidence.py`, `NextMoveEntry`, `compute_insights` re-sort, `get_next_moves` call-site), (2) `arrowColor.ts` body+signature, (3) `MoveExplorer.tsx` Conf column + mute extension + call-site, (4) `OpeningFindingCard.tsx` prose+confidence-line + `OpeningInsightsBlock.tsx` four `InfoPopover` icons + `openingInsights.ts` cleanup. Test cluster runs in parallel: `score_confidence.py` unit tests, `arrowColor.test.ts` rewrite, `MoveExplorer.test.tsx` extension, `OpeningFindingCard.test.tsx` rewrite, CI consistency test extension, `openingInsights.test.ts` rewrite.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trinomial Wald formula (variance, half-width, p-value) | API/Backend (Python) | — | Single language for the math (Phase 75 D-07 anti-pattern lock); shared between two call sites via `score_confidence.py`. |
| Confidence bucket assignment | API/Backend (Python) | — | Same as above; bucket boundaries live in `opening_insights_constants.py`. |
| Score field on `NextMoveEntry` | API/Backend (Python) | — | Trivially derived from existing W/D/L aggregates already returned by `query_next_moves`. Frontend should not re-derive (would duplicate logic with `OpeningInsightFinding.score`). |
| Score-to-color mapping | Frontend (Browser) | — | Pure presentation — boundary thresholds verified against backend by CI consistency test. No SSR/hydration concern. |
| Row tint, Conf column rendering | Frontend (Browser) | — | DOM-level rendering of values fetched from API. |
| `data-testid`, ARIA labels | Frontend (Browser) | — | Per CLAUDE.md browser-automation rules. |
| InfoPopover copy constant | Frontend (Browser) | — | Co-locates with consumers (`OpeningInsightsBlock`) via existing `openingInsights.ts` module. |

No tier misassignment risk in this phase — every capability lives in its natural tier. The only cross-tier concern is the CI consistency test (D-22) which crosses the Python/TypeScript boundary by regex-extracting `arrowColor.ts` exports. That pattern is already established in Phase 75 and is the right tool for this job. [VERIFIED: `tests/services/test_opening_insights_arrow_consistency.py` read]

## Standard Stack

This phase uses no new libraries — all work is on existing stack.

### Core (existing, already in place)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.x | Component rendering | Already in tree |
| TypeScript | latest | Type safety, `noUncheckedIndexedAccess` enforcement | Project convention |
| Vitest | latest | Frontend unit/component tests | Already configured (no `vitest.config.ts`; `// @vitest-environment jsdom` per-file) [VERIFIED: `frontend/vite.config.ts` read, no test stanza; `npm test → vitest run`] |
| @testing-library/react | latest | Component test rendering | Used in all existing component tests |
| radix-ui | latest | `Popover` primitive used by `InfoPopover` and `Tooltip` | Already imported by both components |
| pytest | latest | Backend unit tests | Project convention |
| Pydantic v2 | latest | Schema validation | Project convention; `Literal["low","medium","high"]` already used in `OpeningInsightFinding` [VERIFIED: `app/schemas/opening_insights.py:76-78`] |

### Alternatives Considered
None. Every decision in CONTEXT.md fixes the specific component/library to use; the only Claude's-discretion items concern presentation details (column width, tooltip vs span), not stack swaps.

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────────────┐
                │ POST /api/openings/next-moves        │      POST /api/insights/openings
                │  (existing endpoint, schema gains    │       (existing, no schema change)
                │   confidence, p_value, score)        │
                └──────────────┬───────────────────────┘
                               │
   ┌───────────────────────────▼─────────────────────────────────────┐
   │  app/services/openings_service.py :: get_next_moves             │   app/services/opening_insights_service.py
   │   - query_next_moves (repository)        ← unchanged             │     :: compute_insights
   │   - per-row aggregation loop             ← gains:                │      - per-row score + confidence
   │       - score = (w + d/2)/n                                      │        ← migrates import to
   │       - confidence, p_value via shared helper                    │          score_confidence.compute_confidence_bucket
   │   - sort by frequency / win_rate         ← unchanged             │      - re-sort each section by
   │                                                                  │        (confidence DESC, |score-0.5| DESC) ← NEW (D-03)
   └────────────────────┬─────────────────────┬─────────────────────────┘
                        │                     │
                        ▼                     ▼
              ┌─────────────────────────────────────────┐
              │  app/services/score_confidence.py        │   ← NEW MODULE (D-06)
              │   compute_confidence_bucket(w, d, l, n)  │     migrates Phase 75's
              │     -> (Literal["low","medium","high"],  │     _compute_confidence
              │         float)                            │     verbatim. Imports
              │                                           │     constants from
              │   reads: HIGH_MAX_HALF_WIDTH,             │     opening_insights_constants.py.
              │          MEDIUM_MAX_HALF_WIDTH,           │
              │          SCORE_PIVOT                       │
              └───────────────────────────────────────────┘

   Frontend rendering paths
   ────────────────────────────────────────────────────────────────────
   useNextMoves() (TanStack Query) ──→ MoveExplorer.tsx
                                          - getArrowColor(score, gc, hovered) ← rewritten (D-12)
                                          - row tint = same arrowColor (D-14)
                                          - <td>Conf</td> column NEW (D-08)
                                          - mute when game_count<10 OR confidence==='low' (D-11)

   useOpeningInsights() ──→ OpeningInsightsBlock.tsx
                              - 4 sections, titles unchanged (D-01)
                              - InfoPopover ? next to each <h3> (D-16, D-17)
                              ──→ OpeningFindingCard.tsx
                                    - "You score X%" prose (D-02), reads finding.score
                                    - "Confidence: ..." line + level tooltip (D-09, D-10)
                                    - mute when n_games<10 OR confidence==='low' (D-11)
```

### Recommended Project Structure (file-level changes only — no folder restructure)

```
app/
├── services/
│   ├── score_confidence.py          # NEW — D-06
│   ├── opening_insights_service.py  # imports switched (D-06); compute_insights re-sort (D-03)
│   └── openings_service.py          # get_next_moves: per-row score + confidence (D-05, D-13)
└── schemas/
    └── openings.py                  # NextMoveEntry: + score, confidence, p_value (D-05, D-13)

frontend/src/
├── lib/
│   ├── arrowColor.ts                # body rewrite (D-12); sig (D-13); remove dead consts (D-15)
│   ├── openingInsights.ts           # cleanup (D-20); add OPENING_INSIGHTS_POPOVER_COPY (D-17)
│   ├── arrowColor.test.ts           # rewrite for score-based signature
│   └── openingInsights.test.ts      # rewrite — drop stale-constant assertions
├── types/
│   ├── insights.ts                  # OpeningInsightFinding: -loss_rate -win_rate +confidence +p_value (D-21)
│   └── api.ts                       # NextMoveEntry: +score +confidence +p_value (D-05)
└── components/
    ├── move-explorer/
    │   ├── MoveExplorer.tsx         # Conf column (D-08); call site (D-13); mute extension (D-11)
    │   └── __tests__/MoveExplorer.test.tsx
    └── insights/
        ├── OpeningFindingCard.tsx   # prose (D-02); confidence line (D-09); tooltip (D-10); mute (D-11)
        ├── OpeningFindingCard.test.tsx
        ├── OpeningInsightsBlock.tsx # 4 InfoPopover icons (D-16)
        └── OpeningInsightsBlock.test.tsx

tests/services/
├── test_score_confidence.py                        # NEW — boundary cases for migrated helper
├── test_opening_insights_arrow_consistency.py      # extended (D-22)
├── test_opening_insights_service.py                # update sort assertions (D-03 ordering)
└── (existing tests touched only where needed)
```

### Pattern 1: Shared helper module after a body of code matures (D-06)

**What:** Phase 75 placed `_compute_confidence` as a private helper inside `opening_insights_service.py` because there was only one consumer. Phase 76 needs a second consumer (`get_next_moves`); the response is to extract to a sibling module, not to import a private symbol from the original.

**When to use:** When a pure helper acquires its second caller, and especially when the alternative would be importing a `_private` symbol across module boundaries.

**Example:**
```python
# app/services/score_confidence.py — NEW MODULE
"""Trinomial Wald confidence helper, shared between opening_insights_service
and openings_service. Migrates Phase 75's _compute_confidence verbatim.

Pure helper: no DB/session/config dependency. Project convention is one
shared utility module per cross-cutting concern (cf. app/repositories/query_utils.py).
"""

import math
from typing import Any, Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH,
    OPENING_INSIGHTS_SCORE_PIVOT,
)


def compute_confidence_bucket(
    w: int, d: int, l: int, n: int
) -> tuple[Literal["low", "medium", "high"], float]:
    """Trinomial Wald confidence bucket and two-sided p-value.

    See app/services/opening_insights_service.py (Phase 75 D-05, D-06)
    for the full derivation; this module is a pure migration of that
    helper plus a row-shape unwrap.
    """
    score = (w + 0.5 * d) / n
    variance = max((w + 0.25 * d) / n - score * score, 0.0)
    se = math.sqrt(variance / n)

    if se == 0.0:
        return "high", 1.0 if score == OPENING_INSIGHTS_SCORE_PIVOT else 0.0

    half_width = 1.96 * se
    if half_width <= OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH:
        confidence: Literal["low", "medium", "high"] = "high"
    elif half_width <= OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_HALF_WIDTH:
        confidence = "medium"
    else:
        confidence = "low"

    z = (score - OPENING_INSIGHTS_SCORE_PIVOT) / se
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return confidence, p_value
```

The original `_compute_confidence` in `opening_insights_service.py:105-152` is removed; `compute_insights` swaps to:

```python
from app.services.score_confidence import compute_confidence_bucket
...
confidence, p_value = compute_confidence_bucket(row.w, row.d, row.l, row.n)
```

[VERIFIED: `opening_insights_service.py:105-152` reads exactly the formula CONTEXT.md describes]

### Pattern 2: Schema-additive backend extension (D-05, D-13)

**What:** Adding fields to a Pydantic model that the API already serializes — frontend gets the new fields automatically once it updates its TypeScript mirror.

**When to use:** Cross-tier contract changes where backend ships first (or in same PR with the frontend type catch-up).

**Example:**
```python
# app/schemas/openings.py — NextMoveEntry
class NextMoveEntry(BaseModel):
    move_san: str
    game_count: int
    wins: int
    draws: int
    losses: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    result_hash: str
    result_fen: str
    transposition_count: int
    # NEW (Phase 76 D-05, D-13):
    score: float = Field(ge=0.0, le=1.0)            # (W + D/2) / n
    confidence: Literal["low", "medium", "high"]    # trinomial Wald bucket
    p_value: float = Field(ge=0.0, le=1.0)          # two-sided H0: score = 0.50
```

```typescript
// frontend/src/types/api.ts — NextMoveEntry
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
  // NEW (Phase 76 D-05, D-13):
  score: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;
}
```

[VERIFIED: `app/schemas/openings.py:185-198` and `frontend/src/types/api.ts:93-105` are exact mirrors today]

### Pattern 3: getArrowColor body rewrite + signature change (D-12, D-13)

```typescript
// frontend/src/lib/arrowColor.ts — body rewrite

export function getArrowColor(score: number, gameCount: number, isHovered: boolean): string {
  if (isHovered) return HOVER_BLUE;
  if (gameCount < MIN_GAMES_FOR_COLOR) return GREY;

  // Strict ≥ / ≤ boundaries match Phase 75 D-03 / D-11 backend behavior.
  if (score >= SCORE_PIVOT + MAJOR_EFFECT_SCORE) return DARK_GREEN;   // ≥ 0.60
  if (score >= SCORE_PIVOT + MINOR_EFFECT_SCORE) return LIGHT_GREEN;  // ≥ 0.55
  if (score <= SCORE_PIVOT - MAJOR_EFFECT_SCORE) return DARK_RED;     // ≤ 0.40
  if (score <= SCORE_PIVOT - MINOR_EFFECT_SCORE) return LIGHT_RED;    // ≤ 0.45
  return GREY;
}
```

Removed: `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD` (lines 26-27), and the win/loss-rate body (lines 47-69). The Phase 75 additive exports stay. Note **strict** boundaries — ordering matters: dark before light on each side. [VERIFIED: `arrowColor.ts` read in full]

### Anti-Patterns to Avoid

- **Re-implementing the trinomial Wald formula in TypeScript.** D-05/D-06 explicitly route confidence through the API. The frontend never touches the math. Locked under Phase 75's anti-pattern.
- **Computing `score` in the frontend from `wins / draws / losses / game_count`.** Backend computes; frontend reads. D-13 makes this explicit by adding `score` to the payload.
- **Re-sorting findings on the frontend.** `compute_insights` already sorts (today by severity desc, n_games desc; Phase 76 changes to confidence desc, |score-0.5| desc). Frontend trusts the order — `OpeningInsightsBlock.tsx:191-194` slices by index, never sorts. D-03 must land in `compute_insights`, not in `OpeningInsightsBlock`.
- **Adding a custom `data-testid` scheme for the "Conf" column.** Reuse the existing `move-explorer-row-${move_san}` row testid — the new `<td>` doesn't need its own testid (per CLAUDE.md "data-testid on every interactive element" — `<td>` is not interactive). The header `<th>` may carry `move-explorer-th-conf` if a test wants to assert presence.
- **Putting the `Confidence: …` line label tooltip on a different surface from the line itself.** The `Tooltip` wraps the literal `Confidence: <level>` span; do not wrap a separate `?` icon — D-09 calls for the tooltip to fire from the line, not an adjacent trigger.
- **Skipping `extra="forbid"` on the new field additions.** `OpeningInsightFinding` already uses Pydantic; `NextMoveEntry` does not declare `extra="forbid"` today — keep its default behavior unchanged. Don't tighten as a side effect.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trinomial Wald confidence formula | TypeScript port of `_compute_confidence` | API field `confidence` from `NextMoveEntry` (D-05/D-06) | Phase 75 anti-pattern lock; SE=0 edge cases would diverge between languages. |
| Frontend re-derivation of score | `(wins + 0.5*draws) / game_count` in MoveRow | API field `score` from `NextMoveEntry` (D-13) | `OpeningInsightFinding.score` is already returned by backend; consistency with `compute_insights` flow. |
| Tap-friendly tooltip | Custom popover for D-10 | Existing `Tooltip` component (`@/components/ui/tooltip`) | Already used by `OpeningFindingCard.tsx:68,80`; suppresses hover on touch via pointer-type tracking [VERIFIED: `tooltip.tsx:33-43`]. |
| Section-title `?` icon popover | Custom dropdown / dialog | Existing `InfoPopover` (`@/components/ui/info-popover`) | Already used elsewhere in MoveExplorer (line 166); single hex copy via shared constant per D-17. |
| Mute / unreliable opacity | New theme constant | `UNRELIABLE_OPACITY` from `theme.ts:77` | Already imported and applied at `MoveExplorer.tsx:5,239`. Just extend the trigger condition (D-11). |
| Severity border color (cards) | Manual `getArrowColor()` invocation per card | Existing `getSeverityBorderColor` (`openingInsights.ts:19`) | Card border tint is unchanged — only its inputs come from the same Phase 75 contract; mapping `(classification, severity) → hex` stays untouched. Simplification deferred. |

**Key insight:** The shape of this phase is "thread already-computed values from Phase 75's contract through three frontend surfaces." Almost every component already has its imports, primitives, and patterns in place. The exception — and the one place to be careful — is `score_confidence.py` itself: it must be a pure migration of `_compute_confidence` (verbatim formula and SE=0 branches) so the boundary tests Phase 75 wrote (`test_compute_confidence_p_value_at_score_050_is_one`, `test_compute_confidence_se_zero_all_draws`, etc., at `tests/services/test_opening_insights_service.py:247-272`) can be **lifted unchanged** to a new `test_score_confidence.py`.

## Common Pitfalls

### Pitfall 1: `noUncheckedIndexedAccess` on the new "Conf" column
**What goes wrong:** The TypeScript compiler (project setting per CLAUDE.md) treats `arr[i]` as `T | undefined`. `MoveExplorer.tsx` doesn't index into arrays for confidence, but `OpeningInsightsBlock.tsx:155` already has a guarded indexed access pattern using `!`:
```typescript
const prevCount = i === 0 ? 0 : (data[SECTIONS[i - 1]!.findingsKey].length);
```
**How to avoid:** When mapping `confidence` levels to display strings, use a typed `Record<'low' | 'medium' | 'high', string>` object literal (TypeScript narrows correctly), not a switch with a `default` case that returns `undefined`. Example: `const LABEL: Record<NextMoveEntry['confidence'], string> = { low: 'low', medium: 'med', high: 'high' };`. Then `LABEL[entry.confidence]` is `string` (no narrowing needed).
**Warning signs:** Any `entry.confidence` access pattern that uses array indexing or `Map.get` (returns `T | undefined`) instead of object-record indexing.

### Pitfall 2: Mobile Conf column overflows 375px viewport
**What goes wrong:** Today's table has Move (`w-[3rem]` = 48px), Games (`w-[5.5rem]` = 88px), and Results (flexible width). Adding Conf eats into Results width. At 375px viewport with ~16px container padding (Tailwind `px-4` → 32px both sides), the table inner width is ~343px. After Move + Games + 2*pl-2 padding (16px), Results currently has ~199px for the WDL bar. A new ~3rem (48px) Conf column drops Results to ~151px — still legible but tight.
**How to avoid:** Set Conf column to `w-[2.5rem]` (40px) `text-center text-xs`. Verify in playwright/manual at 375px before merging. If WDL bar truncates, reduce Conf to `w-[2.25rem]` (36px) — "med" fits in 32px at `text-xs`.
**Warning signs:** Vitest renders fine but real device shows WDL bar < 100px (illegible). [VERIFIED: `MoveExplorer.tsx:163,178` widths]

### Pitfall 3: D-22 CI consistency test extension hits a structural problem
**What goes wrong:** The CI test today regex-extracts constants from `arrowColor.ts`. There's no equivalent constant in `arrowColor.ts` for "the confidence buckets" because confidence is not on board arrows (D-23 prohibits it). So D-22's "assert moves-explorer payload `confidence` field comes from same shared helper" cannot be tested by string-matching `arrowColor.ts`.
**How to avoid:** Take D-22's *fallback* path — "replace the assertion with a unit test of `score_confidence.compute_confidence_bucket()` covering boundary cases." Concretely: lift the existing Phase 75 boundary tests (`test_compute_confidence_*` at `test_opening_insights_service.py:201-272`) into `tests/services/test_score_confidence.py` and add coverage for `n_games == 10` floor, `half_width == 0.10` exact (high boundary), `half_width == 0.20` exact (medium boundary). The structural guarantee — "both call sites use the same helper" — is enforced by `score_confidence.py` being the only place the formula exists.
**Warning signs:** Trying to add `EXPORT_CONST OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_HALF_WIDTH` to `arrowColor.ts` to satisfy the regex test — that's a smell; the constant has no business in a frontend-arrow file.

### Pitfall 4: D-02 prose rounding contradicts section
**What goes wrong:** A finding with `score = 0.499` survives the weakness gate (`score ≤ 0.45`? **No** — wait, `0.499 > 0.45`, so `score = 0.499` would NOT survive the backend gate at all). So this is **not** a real edge case for surviving findings. **Real** edge case: a strength finding with `score = 0.5499` rounds to `55%` and the section says "Strengths" — consistent. A weakness finding with `score = 0.4501` (just over 0.45) — wait, this also fails the gate. The actual gate is strict `≤ 0.45` and `≥ 0.55`, so the surviving range guarantees `score ≤ 0.45` (rounds to ≤ 45%) or `score ≥ 0.55` (rounds to ≥ 55%). A "50% in a Weaknesses section" requires `score = 0.45` exactly rounding to "45%" — round() in JS handles this fine.

The CONTEXT.md "edge case" is over-stated — but the discretion line ("fall back to `.toFixed(1)` if needed") still applies if the displayed integer ever feels off. **Recommendation:** Use `Math.round(finding.score * 100)` with no fallback. The backend gate prevents the contradiction by construction.
**How to avoid:** Trust the backend gate; don't pre-emptively add `.toFixed(1)` complexity.
**Warning signs:** A weakness finding shows "50%" or "51%" — would indicate a backend gate bug, not a rounding bug.

### Pitfall 5: `OpeningFindingCard.tsx` is broken in production right now
**What goes wrong:** Line 25-27 reads `finding.loss_rate` and `finding.win_rate` — both fields removed by Phase 75 D-09. TypeScript should be flagging this, but the frontend type at `frontend/src/types/insights.ts:85-86` still declares them, so the compiler is happy. At runtime, `undefined * 100 = NaN`, and `Math.round(NaN) = NaN`, displayed as "NaN%" in the prose. [VERIFIED: `OpeningFindingCard.tsx:25-27`, `insights.ts:85-86`, Phase 75 D-09]
**How to avoid:** D-21 (frontend type catch-up) and D-02 (prose migration) must land **together**. If D-21 lands without D-02, TypeScript breaks the build (good — fail-fast). If D-02 lands without D-21, the existing tests at `OpeningFindingCard.test.tsx:55-65` continue to pass against stale fixtures (bad — silent stagnation). **Plan order:** Land both in the same plan/commit.
**Warning signs:** If you see "NaN%" anywhere in opening insights cards in dev, this is the bug. (Adrian likely has not noticed because Phase 75 shipped 2026-04-28 same-day as Phase 76 prep.)

### Pitfall 6: Stale `MIN_GAMES_FOR_INSIGHT = 20` in `openingInsights.ts` no longer matches backend
**What goes wrong:** `frontend/src/lib/openingInsights.ts:5` declares `MIN_GAMES_FOR_INSIGHT = 20`. Backend dropped to 10 in Phase 75 D-04. Currently no consumer outside `openingInsights.test.ts:93-94` (which asserts the value is 20). [VERIFIED via grep]
**How to avoid:** D-20 — update value to 10, OR remove entirely if there's no remaining consumer. Verify with grep before removing. Update or delete the test assertion.
**Warning signs:** Any new code that imports `MIN_GAMES_FOR_INSIGHT` and uses it for filtering — would wrongly hide findings with 10-19 games.

### Pitfall 7: SQL HAVING clause re-runs the trinomial Wald formula in `query_next_moves`
**What goes wrong:** Phase 75 D-08 only rewrote the HAVING clause in `query_opening_transitions` (used by insights). `query_next_moves` (used by Move Explorer) does NOT have a HAVING clause that filters on score — it returns all moves with at least one game (line 446: `.group_by(gp1.move_san, gp2.full_hash)` — no HAVING). The "min games" cutoff is enforced only by the frontend mute rule and `MIN_GAMES_FOR_RELIABLE_STATS = 10` opacity.
**How to avoid:** Do NOT add a HAVING clause to `query_next_moves` as part of this phase. The Move Explorer surfaces ALL moves (low-game ones muted), which is intentional per the existing UX. Confidence computation in `get_next_moves` runs over ALL rows; `low` confidence is the expected output for low-n moves.
**Warning signs:** Any "while we're here, let's add a HAVING clause" suggestion — that would silently hide moves the user expects to see.

## Runtime State Inventory

This phase is a code edit with one schema addition. No data migration, no OS-registered state, no secrets.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `score`, `confidence`, `p_value` are computed per-request from existing `wins/draws/losses/game_count` columns. No DB schema change. | None — verified by grep for `Alembic`, no migration needed. |
| Live service config | None — no external services. | None — verified. |
| OS-registered state | None — no cron, systemd, or task scheduler entries touched. | None — verified. |
| Secrets/env vars | None — no auth, no API keys, no SOPS. | None — verified. |
| Build artifacts | Frontend build will pick up new types automatically; ty/tsc will re-typecheck. No `*.egg-info`, no compiled binaries. Vite HMR + `npm run build` regenerate. | None beyond standard rebuild on deploy (handled by `bin/deploy.sh`). |

## Code Examples

### Move Explorer Conf column (D-08)

```tsx
// MoveExplorer.tsx — header
<thead>
  <tr>
    <th className="w-[3rem] text-left text-xs text-muted-foreground font-normal pb-1">
      <span className="inline-flex items-center gap-1">
        Move
        <InfoPopover ariaLabel="Move arrows info" testId="move-arrows-info" side="top">{/* unchanged */}</InfoPopover>
      </span>
    </th>
    <th className="w-[5.5rem] text-right text-xs text-muted-foreground font-normal pb-1">Games</th>
    <th
      className="w-[2.5rem] text-center text-xs text-muted-foreground font-normal pb-1"
      data-testid="move-explorer-th-conf"
    >
      Conf
    </th>
    <th className="text-left text-xs text-muted-foreground font-normal pb-1 pl-2">Results</th>
  </tr>
</thead>

// MoveRow body — between Games <td> and Results <td>
<td className="py-1 text-center text-xs text-muted-foreground tabular-nums">
  {entry.confidence === 'medium' ? 'med' : entry.confidence}
</td>
```

### Mute rule extension (D-11)

```tsx
// MoveRow body
const isLowConfidence = entry.confidence === 'low';
const isUnreliable = entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS || isLowConfidence;
// ...
if (isUnreliable) rowStyle.opacity = UNRELIABLE_OPACITY;
```

### OpeningFindingCard prose + confidence line (D-02, D-09, D-10)

```tsx
// Replaces OpeningFindingCard.tsx:25-27 and proseLine
const scorePercent = Math.round(finding.score * 100);
const colorLabel = finding.color === 'white' ? 'White' : 'Black';
const trimmedSequence = trimMoveSequence(finding.entry_san_sequence, finding.candidate_move_san);
const borderLeftColor = getSeverityBorderColor(finding.classification, finding.severity);

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

// Mute rule (D-11)
const isUnreliable = finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
const cardStyle: React.CSSProperties = isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {};
```

### OpeningInsightsBlock four InfoPopover icons (D-16, D-17)

```tsx
// openingInsights.ts — replace INSIGHT_THRESHOLD_COPY with this constant
import type { ReactNode } from 'react';
import { Fragment } from 'react';

export const OPENING_INSIGHTS_POPOVER_COPY: ReactNode = (
  <Fragment>
    <p className="mb-2">
      <strong>Score</strong> is (W + ½D) / N. 50% means you and your opponents broke even.
    </p>
    <p className="mb-2">
      A finding shows up when your score sits at least 5% from 50%, enough of a gap that it's probably not random.
    </p>
    <p>
      <strong>Confidence</strong> says how big the sample is. <em>Low</em> findings are worth a glance;
      {' '}<em>high</em> findings are well-supported.
    </p>
  </Fragment>
);

// OpeningInsightsBlock.tsx — section header
<h3 className="text-base font-semibold flex items-center gap-1.5">
  <span className={`inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground ${swatchClass}`} aria-hidden="true" />
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

Note `side="bottom"` — `OpeningInsightsBlock` headings are at the top of each section; popovers below avoid clipping at viewport top. [VERIFIED: pattern by analogy with `MoveExplorer.tsx:166` which uses `side="top"`.]

### compute_insights re-sort (D-03, backend)

```python
# opening_insights_service.py — replace _rank_section
_CONFIDENCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

def _rank_section(findings: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]:
    """Sort findings by (confidence DESC, |score - 0.50| DESC) per Phase 76 D-03.

    high → medium → low; ties broken by absolute distance from the 0.50 pivot.
    Replaces Phase 70's (severity DESC, n_games DESC) ordering.
    """
    return sorted(
        findings,
        key=lambda f: (_CONFIDENCE_RANK[f.confidence], -abs(f.score - 0.5)),
    )
```

[VERIFIED: existing `_rank_section` at `opening_insights_service.py:322-331`]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `loss_rate` / `win_rate` on `OpeningInsightFinding` | `score`, `confidence`, `p_value` | Phase 75 (PR #69, 2026-04-28) | Phase 76 frontend type must catch up (D-21); existing card prose breaks until D-02 lands. |
| `getArrowColor(winPct, lossPct, gameCount, isHovered)` | `getArrowColor(score, gameCount, isHovered)` | Phase 76 (this phase) | Single call site (`MoveExplorer.tsx:228`); change is mechanical. |
| `_compute_confidence` private to `opening_insights_service.py` | Shared `score_confidence.compute_confidence_bucket` | Phase 76 (this phase) | Two consumers; matches `query_utils.py` shared-helper pattern. |
| `_rank_section` ordering (severity DESC, n_games DESC) | (confidence DESC, &#124;score-0.5&#124; DESC) | Phase 76 (this phase) | Test `test_ranking_severity_desc_then_n_games_desc` at `test_opening_insights_service.py:636` MUST be rewritten. |
| `MIN_GAMES_FOR_INSIGHT = 20` in `openingInsights.ts` | 10, or removed | Phase 76 (this phase, D-20) | Stale since Phase 75. |

**Deprecated/outdated:**
- `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD` (`arrowColor.ts:26-27`): kept alive in Phase 75 only because `getArrowColor` body still consumed them. Phase 76 removes both.
- `INSIGHT_RATE_THRESHOLD = 55` (`openingInsights.ts:8`): no remaining consumers — remove.
- `INSIGHT_THRESHOLD_COPY` (`openingInsights.ts:11`): replaced by `OPENING_INSIGHTS_POPOVER_COPY`.

## Assumptions Log

All factual claims about file shapes and behavior are tagged `[VERIFIED]` from direct file reads. The few `[ASSUMED]` claims:

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vitest uses jsdom-per-file convention with no `vitest.config.ts` (verified absent in `vite.config.ts`); the `// @vitest-environment jsdom` comment in each component test sets the environment. | Standard Stack | Low — if a `vitest.config.ts` is later added, tests still work; current convention is fine. |
| A2 | The `Conf` column at `w-[2.5rem]` (40px) fits at 375px without breaking the WDL bar — based on arithmetic only, not on a real device test. | Pitfall 2 | Medium — actual device may need `w-[2.25rem]` (36px). Test at execution time. |
| A3 | `OpeningFindingCard.tsx` runtime currently renders "NaN%" for the prose due to missing `loss_rate`/`win_rate` fields. Verified by source read of `OpeningFindingCard.tsx:25-27` (reads removed fields) + `opening_insights.py:39-94` (Phase 75 schema does not return them) + `insights.ts:85-86` (frontend type still declares them, so TS doesn't catch). Not visually confirmed in dev. | Pitfall 5 | Low — even if it renders something unexpected like blank, the D-02 fix is the same. |
| A4 | The CI consistency test at `test_opening_insights_arrow_consistency.py` cannot meaningfully assert structural equivalence between the two `compute_confidence_bucket` call sites via regex on `arrowColor.ts`, because confidence is not exposed as a frontend constant by D-23. The fallback unit-test path (D-22 sentence 2) is the right approach. | Pitfall 3 | Low — D-22 explicitly lists this fallback. |

## Open Questions

1. **Conf column header tooltip — yes or no?**
   - What we know: D-16 covers the framing in the section-title popover. CONTEXT.md `<decisions>` Claude's-discretion calls a column-header tooltip "optional decoration."
   - What's unclear: Whether a brief inline tooltip on the `Conf` `<th>` ("Confidence in the score estimate, low/medium/high") improves discoverability for users who never expand a section.
   - Recommendation: Add a tiny `Tooltip` wrap with one-line copy (e.g. "How well-sampled this move is"). Keeps `OPENING_INSIGHTS_POPOVER_COPY` as the canonical long-form. Cost: ~5 LOC.

2. **Plan ordering — backend extension first or frontend cleanup first?**
   - What we know: Backend extension (D-05/D-06/D-07) gates the moves-explorer Conf column. Frontend type cleanup (D-21) gates the card prose fix. These are independent code-wise but both must ship before the user sees a clean state.
   - What's unclear: Whether to land them as one plan (single PR) or two (parallel waves).
   - Recommendation: Single plan, four waves: (W1) backend `score_confidence.py` + schema + helper migration + `compute_insights` re-sort (atomic). (W2) frontend types + `arrowColor.ts` + `openingInsights.ts` cleanup. (W3) `MoveExplorer.tsx` + tests. (W4) `OpeningFindingCard.tsx` + `OpeningInsightsBlock.tsx` + tests + CI consistency test. Each wave green before the next.

3. **Should `OPENING_INSIGHTS_POPOVER_COPY` be a string or `ReactNode`?**
   - What we know: D-17 says "Markdown-style emphasis stays inline (matches existing `InfoPopover` consumers that render React fragments with bold/italic)." The example in `MoveExplorer.tsx:167-174` does pass JSX (a `<div>` with two `<p>`).
   - What's unclear: Whether to keep the constant as `ReactNode` (matches `MoveExplorer` pattern; testable via `screen.getByText`) or as a structured object (`{ paragraphs: [...] }`) the consumer renders.
   - Recommendation: `ReactNode` (matches existing pattern). Tradeoff is that the constant becomes JSX (file extension `.tsx`) — `openingInsights.ts` is currently `.ts`. Either rename to `.tsx` OR define a small `OpeningInsightsPopoverCopy` component in `OpeningInsightsBlock.tsx` directly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 + uv | Backend tests, ty | ✓ | 3.13 | — |
| PostgreSQL 18 (dev) | Integration tests (none new in this phase) | ✓ via `docker compose -f docker-compose.dev.yml` | 18 | — |
| Node + npm | Frontend tests, build | ✓ | — | — |
| Vitest + jsdom | Component tests | ✓ via devDependencies | — | — |
| pytest + pytest-asyncio | Backend service tests | ✓ | — | — |
| ty | Backend type check (CI gate) | ✓ | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json` — validation included.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio |
| Backend config file | `pyproject.toml` (existing) |
| Frontend framework | Vitest + @testing-library/react (jsdom per-file) |
| Frontend config file | None (`vite.config.ts` has no test stanza); `// @vitest-environment jsdom` per file |
| Backend quick run | `uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_arrow_consistency.py tests/services/test_opening_insights_service.py -x` |
| Backend full suite | `uv run pytest` |
| Frontend quick run | `cd frontend && npm test -- src/lib/arrowColor.test.ts src/lib/openingInsights.test.ts src/components/move-explorer/__tests__/MoveExplorer.test.tsx src/components/insights/OpeningFindingCard.test.tsx src/components/insights/OpeningInsightsBlock.test.tsx` |
| Frontend full suite | `cd frontend && npm test` |
| Type-check gate | `uv run ty check app/ tests/` (zero errors required) |
| Lint gate | `uv run ruff check . && uv run ruff format --check . && cd frontend && npm run lint && npm run knip` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSIGHT-UI-01 | `getArrowColor(score, gameCount, isHovered)` maps score to correct bucket: ≥0.60→DARK_GREEN, ≥0.55→LIGHT_GREEN, ≤0.40→DARK_RED, ≤0.45→LIGHT_RED, else GREY; gameCount<10→GREY; isHovered→HOVER_BLUE; strict ≥/≤ boundaries. | unit | `cd frontend && npm test -- src/lib/arrowColor.test.ts` | ✅ rewrite (existing tests use win/loss-rate signature) |
| INSIGHT-UI-01 | `arrowColor.ts` removes `LIGHT_COLOR_THRESHOLD` and `DARK_COLOR_THRESHOLD` (D-15). | static | grep assertion in `test_opening_insights_arrow_consistency.py`; or `npm run knip` flags as unused. | ✅ Wave 0 — extend |
| INSIGHT-UI-01 | CI consistency: `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE`, `MIN_GAMES_FOR_COLOR` match `opening_insights_constants.py`. | unit | `uv run pytest tests/services/test_opening_insights_arrow_consistency.py` | ✅ exists, kept as-is (already passes after Phase 75) |
| INSIGHT-UI-02 | `MoveExplorer.tsx` renders row tint matching `getArrowColor(entry.score, entry.game_count, false)`; GREY → no tint. | component | `cd frontend && npm test -- src/components/move-explorer/__tests__/MoveExplorer.test.tsx` | ✅ extend |
| INSIGHT-UI-03 | `MoveExplorer.tsx` renders Conf column with cells `low / med / high` per `entry.confidence`. | component | same as above | ✅ extend |
| INSIGHT-UI-03 | Mute rule extends to `confidence === 'low'`: `rowStyle.opacity === UNRELIABLE_OPACITY`. | component | same as above | ✅ extend |
| INSIGHT-UI-03 | `score_confidence.compute_confidence_bucket(w, d, l, n)` returns same `(bucket, p_value)` as Phase 75's `_compute_confidence` for: n=10 floor, half_width=0.10 exact, half_width=0.20 exact, all-draws (SE=0, score=0.5 → high, 1.0), all-wins (SE=0 → high, 0.0), score=0.5 → p_value=1.0. | unit | `uv run pytest tests/services/test_score_confidence.py` | ❌ Wave 0 — NEW FILE |
| INSIGHT-UI-03 | `get_next_moves` populates `score`, `confidence`, `p_value` on every `NextMoveEntry`; values match the helper. | unit | extend `tests/test_openings_service.py` if it exists, else add unit test in `tests/services/test_score_confidence.py` invoking `get_next_moves` with a fixture. | ⚠️ check `tests/test_openings_service.py` existence at planning time |
| INSIGHT-UI-05 | `OpeningFindingCard` prose renders "You score X% as White after \<san\>" using `Math.round(finding.score * 100)`; no `lose`/`win` verb. | component | `cd frontend && npm test -- src/components/insights/OpeningFindingCard.test.tsx` | ✅ rewrite (existing tests assert "lose"/"win" verb) |
| INSIGHT-UI-05 | `OpeningFindingCard` renders `Confidence: <level>` line; level matches `finding.confidence`. | component | same as above | ✅ extend |
| INSIGHT-UI-05 | `OpeningFindingCard` opacity = UNRELIABLE_OPACITY when `n_games < 10` OR `confidence === 'low'`. | component | same as above | ✅ extend |
| INSIGHT-UI-05 | `compute_insights` orders findings by (confidence DESC, &#124;score-0.5&#124; DESC). | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_ranking_*` | ✅ rewrite existing `test_ranking_severity_desc_then_n_games_desc` |
| INSIGHT-UI-06 | `OpeningInsightsBlock` renders four InfoPopover icons, one per section, with shared copy constant. | component | `cd frontend && npm test -- src/components/insights/OpeningInsightsBlock.test.tsx` | ✅ extend |
| INSIGHT-UI-07 | All new interactive elements have `data-testid`. ARIA labels present on the four InfoPopover triggers. | component | extend MoveExplorer + OpeningInsightsBlock tests with `getByTestId` assertions for `move-explorer-th-conf`, `opening-insights-section-{key}-info`, `opening-finding-card-{idx}-confidence`. | ✅ extend |
| INSIGHT-UI-07 | Mobile parity at 375px: Conf column does not break layout. | manual | resize browser to 375px, verify no horizontal scroll on `/openings`. | manual-only — recorded in UAT |
| (cross-cut) | Existing tests `openingInsights.test.ts` lines 93-103 break (asserts removed constants). | unit | `cd frontend && npm test -- src/lib/openingInsights.test.ts` | ✅ rewrite — replace with assertion on `OPENING_INSIGHTS_POPOVER_COPY` shape (or testid presence in OpeningInsightsBlock test) |

### Sampling Rate
- **Per task commit:** Backend quick run (~3 service test files) + Frontend quick run (~5 test files). Both should run in < 30 seconds combined on a developer machine.
- **Per wave merge:** Full backend suite + full frontend suite + `ty check` + `ruff` + `npm run lint` + `npm run knip`.
- **Phase gate:** All gates green; manual 375px-viewport check on `/openings` page.

### Wave 0 Gaps
- [ ] `tests/services/test_score_confidence.py` — NEW file. Lift the boundary tests from `test_opening_insights_service.py:201-272` (`test_compute_confidence_*`) verbatim, retargeted at `score_confidence.compute_confidence_bucket`. Add: `n=10` floor, `half_width=0.10` exact (high boundary), `half_width=0.20` exact (medium boundary). Wave 0 because subsequent waves depend on this file's existence.
- [ ] Frontend `arrowColor.test.ts` rewrite — current tests use `getArrowColor(winPct, lossPct, gameCount, hovered)` signature. Rewrite for `getArrowColor(score, gameCount, hovered)`. Add boundary cases: `score = 0.60` exact (DARK_GREEN), `score = 0.55` exact (LIGHT_GREEN), `score = 0.45` exact (LIGHT_RED), `score = 0.40` exact (DARK_RED), `score = 0.501` (GREY), etc.
- [ ] Frontend `openingInsights.test.ts` rewrite — drop assertions on removed constants; add a smoke test on `OPENING_INSIGHTS_POPOVER_COPY` (e.g. renders three paragraphs containing "Score", "5%", "Confidence").
- No framework install needed — pytest/Vitest already configured.

## Project Constraints (from CLAUDE.md)

Constraints relevant to this phase:

- **Theme constants in theme.ts** — D-11 reuses existing `UNRELIABLE_OPACITY`, `MIN_GAMES_FOR_RELIABLE_STATS`. Do NOT add new theme constants. The "Confidence: low/medium/high" line uses `text-muted-foreground` (existing utility), no new color.
- **Mobile-first; verify at 375px** — D-08, D-09, D-25 demand mobile parity. Conf column width is the riskiest area.
- **`data-testid` on every interactive element** — Add `data-testid="opening-insights-section-{key}-info"` to each new InfoPopover. Add `data-testid="opening-finding-card-{idx}-confidence"` to the new confidence line. The Conf column header gets `data-testid="move-explorer-th-conf"`. Cells inside the table do NOT need testids (rows are interactive, cells are not — already covered by `move-explorer-row-${move_san}`).
- **Primary vs secondary buttons** — N/A this phase (no new buttons).
- **`noUncheckedIndexedAccess`** — relevant for `confidence` mapping; use `Record<'low'|'medium'|'high', string>` not array indexing.
- **ty type-check gate** — must pass with zero errors. New backend code must use `Literal["low", "medium", "high"]`, explicit return types, `Sequence[str]` for parameters that accept `list[Literal[...]]`. Pydantic for boundaries; `# ty: ignore[rule]` only with reason.
- **Coding guideline: No magic numbers** — backend uses `OPENING_INSIGHTS_*` constants from `opening_insights_constants.py`; frontend uses `SCORE_PIVOT`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` from `arrowColor.ts`. The `0.5` in `(w + 0.5*d)/n` is a mathematical constant of the score formula, not a magic number — fine to inline.
- **Sentry rules** — no new `except` blocks introduced; the existing top-level handler in `compute_insights` (line 487-495) continues to capture failures. `get_next_moves` already has `_fetch_result_fens` which captures (`openings_service.py:339`); no change needed for the new helper invocation.
- **httpx async only, never `requests`** — N/A this phase (no HTTP calls).
- **No `asyncio.gather` on the same `AsyncSession`** — N/A this phase (no new async sessions).
- **PostgreSQL only, asyncpg** — N/A (no DB schema change).
- **Em-dashes sparingly** — apply to the InfoPopover copy in `OPENING_INSIGHTS_POPOVER_COPY` (CONTEXT.md draft uses two em-dashes; rewrite as commas where natural).
- **No sycophancy in PR / commit / planning prose** — straightforward technical messages.
- **Versioning / branching** — `feature/76-frontend-score-coloring-confidence-badges-label-reframe` branch (per `git.branching_strategy: phase`).
- **Changelog** — `## [Unreleased]` accumulates per phase; this phase will add bullets under `### Changed`, `### Removed`, `### Tests` when it merges.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/76-frontend-score-coloring-confidence-badges-label-reframe/76-CONTEXT.md` — phase decisions D-01..D-25.
- `.planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md` — Phase 75 lock-in (D-01..D-16).
- `.planning/notes/opening-insights-v1.14-design.md` — milestone-level design lock.
- `.planning/REQUIREMENTS.md` — INSIGHT-UI-01..07 mapping.
- `frontend/src/lib/arrowColor.ts` — direct read; current body lines 47-69, Phase 75 additive exports lines 21-23.
- `frontend/src/lib/openingInsights.ts` — direct read; stale constants lines 5, 8, 11; `getSeverityBorderColor` line 19.
- `frontend/src/types/insights.ts` — direct read; `OpeningInsightFinding` lines 69-88; stale `loss_rate`/`win_rate` lines 85-86.
- `frontend/src/types/api.ts` — direct read; `NextMoveEntry` lines 93-105.
- `frontend/src/components/move-explorer/MoveExplorer.tsx` — direct read; row tint at lines 222-253; `getArrowColor` call at line 228; table headers at lines 161-181.
- `frontend/src/components/insights/OpeningFindingCard.tsx` — direct read; broken `loss_rate`/`win_rate` reads at lines 25-27; prose pattern lines 55-64; Tooltip usage lines 68, 80.
- `frontend/src/components/insights/OpeningInsightsBlock.tsx` — direct read; section render lines 198-209; section meta array lines 32-61.
- `frontend/src/components/ui/info-popover.tsx` — direct read; `InfoPopoverProps` lines 6-11; tap-friendly span trigger lines 28-41.
- `frontend/src/components/ui/tooltip.tsx` — direct read; touch suppression lines 33-43.
- `frontend/src/lib/theme.ts` — direct read; `UNRELIABLE_OPACITY` line 77, `MIN_GAMES_FOR_RELIABLE_STATS` line 74.
- `app/services/opening_insights_service.py` — direct read; `_compute_confidence` lines 105-152 (the helper to migrate); `_rank_section` lines 322-331; `_classify_row` lines 66-97.
- `app/services/opening_insights_constants.py` — direct read; all constants Phase 76 needs are already defined.
- `app/schemas/opening_insights.py` — direct read; `OpeningInsightFinding` lines 39-81 already includes `confidence`, `p_value`.
- `app/schemas/openings.py` — direct read; `NextMoveEntry` lines 185-198 (target for D-05 additions).
- `app/services/openings_service.py` — direct read; `get_next_moves` lines 354-468; per-row aggregation loop lines 439-460.
- `app/repositories/openings_repository.py` — direct read; `query_next_moves` returns rows with `(move_san, result_hash, game_count, wins, draws, losses)` (no HAVING gate, lines 380-446).
- `tests/services/test_opening_insights_arrow_consistency.py` — direct read; current 4 assertions match Phase 75 D-13.
- `tests/services/test_opening_insights_service.py` — direct read; existing `test_ranking_*` at line 636; `test_compute_confidence_*` at lines 201-272 (lift candidates).
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — direct read; existing tests assert "lose"/"win" verb (must be rewritten for D-02).
- `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` — direct read; fixture at line 27 uses `loss_pct`, will need `score`/`confidence`/`p_value` added.
- `frontend/src/lib/openingInsights.test.ts` — direct read; lines 93-103 assert removed constants.
- `frontend/vite.config.ts` — direct read; no test stanza, jsdom set per-file.
- `frontend/package.json` — `npm test → vitest run`; testing libs in devDependencies.
- `.planning/config.json` — `nyquist_validation: true`; `branching_strategy: phase`.

### Secondary (MEDIUM confidence)
None this phase — every claim was verifiable in-tree.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in tree; no new dependencies.
- Architecture: HIGH — every file shape verified by direct read; the only ambiguity (Vitest config) was resolved (no config file, jsdom per-file).
- Pitfalls: HIGH for #1, #3, #5, #6, #7 (verified by file read); MEDIUM for #2 (mobile width — needs device confirmation at execution time); LOW-but-not-applicable for #4 (over-stated edge case).
- Validation architecture: HIGH — test framework conventions verified; gaps explicitly listed.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (30 days — stable phase, no fast-moving libraries; backend Phase 75 already shipped so contracts are frozen)
