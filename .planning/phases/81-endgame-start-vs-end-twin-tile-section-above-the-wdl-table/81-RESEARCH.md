# Phase 81: Endgame Start vs End — twin-tile section above the WDL table - Research

**Researched:** 2026-05-09
**Domain:** FastAPI/SQLAlchemy 2.x async backend + React 19 + TS frontend (analytics page extension)
**Confidence:** HIGH (all integration points verified in code; population baseline verified in benchmark report)

## Summary

This phase is **purely additive frontend + thin backend extension**. Every reusable asset exists and is verified in the codebase: the two stat helpers (`compute_eval_confidence_bucket` for Wald-z, `compute_confidence_bucket` for Wilson score test), the `MiniBulletChart` component, the `BulletConfidencePopover` and `ScoreConfidencePopover` components, the score-bullet constants in `frontend/src/lib/scoreBulletConfig.ts`, the `ZONE_*` theme constants, and the `_classify_endgame_bucket` color-flip helper. The pattern that this phase mirrors — "inline value row + popover icon + MiniBulletChart" — is implemented exactly in `frontend/src/pages/openings/ExplorerTab.tsx` lines 100-200 and is a drop-in template.

The backend integration point is `query_endgame_bucket_rows` (one-row-per-endgame-game variant of the `first_endgame` ply walk). It already projects `entry_eval_cp` / `entry_eval_mate` per game — Phase 81 only needs Python-side aggregation in `_get_endgame_performance_from_rows`, plus four new fields on `EndgamePerformanceResponse`. **No new SQL.** No new repository function.

**Primary recommendation:** Plan in three tightly-scoped waves:

1. **Backend** — extend `EndgamePerformanceResponse` (4 fields), add an aggregation helper in `endgame_service.py` that consumes `entry_rows` (already fetched by `get_endgame_overview`), call the existing `compute_eval_confidence_bucket` and `compute_confidence_bucket` helpers, expose ci bounds for the bullet whisker. **No SQL changes.**
2. **Frontend types + section component** — mirror types in `frontend/src/types/endgames.ts`, build `EndgameStartVsEndSection.tsx` (charcoal-texture card with two tiles laid out as a 2-col grid on `lg`+, stacked on mobile), reuse `MiniBulletChart`/`BulletConfidencePopover`/`ScoreConfidencePopover` directly, add the section above `<EndgamePerformanceSection ... />` in `Endgames.tsx`.
3. **Concept-explainer paragraphs + tests** — add two `<p>` blocks to the `endgame-concepts-trigger` accordion and ship the test matrix (backend helpers, schema contract, frontend snapshot/render tests).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| One-pass entry-eval aggregation (sum/sumsq/n) | API / Backend | Database (existing index) | Aggregation runs on already-fetched `entry_rows` — keep it in `endgame_service.py` next to `_aggregate_endgame_stats`; no DB round trip. |
| Wald z one-sample mean test | API / Backend | — | `app/services/eval_confidence.py::compute_eval_confidence_bucket` — already exists. |
| Wilson score test against 50% | API / Backend | — | `app/services/score_confidence.py::compute_confidence_bucket` — already exists. |
| Wire format (`EndgamePerformanceResponse` extension) | API / Backend | Frontend types (mirror) | Pydantic v2 schema in `app/schemas/endgames.py`; TypeScript mirror in `frontend/src/types/endgames.ts`. |
| Section composition + tile layout | Frontend Server (SSR/render) | — | New component in `frontend/src/components/charts/`, rendered inside the existing `showPerfSection` block in `Endgames.tsx`. |
| Three-state color verdict | Browser / Client | — | Pure presentation logic from (mean, p-value, threshold) → `ZONE_SUCCESS` / `ZONE_DANGER` / `ZONE_NEUTRAL`. |
| Concept-explainer paragraphs | Browser / Client | — | Static JSX inside the existing `<AccordionContent>` in `Endgames.tsx`. |

The split is conventional and matches every prior endgame-page extension. There are no tier-assignment risks for this phase.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Section Composition**
- **D-01:** Section sits inside *Endgame Overall Performance*, immediately above the existing WDL table. New section, additive — no restructuring of the existing WDL table or the score-over-time chart.
- **D-02:** Section heading: **"Endgame Start vs End"** (matches the phase name; H3 / `<h2>` matching the existing `Endgame Overall Performance` heading style on the page).
- **D-03:** No standalone lead paragraph under the section heading and no section-level info popover. The concepts accordion + per-tile popovers carry the explanation.
- **D-04:** Two tiles side-by-side on desktop (≥`lg`), stacked vertically on mobile.

**Per-Tile Composition (matches Openings ExplorerTab pattern)**

Each tile renders:

1. **Punchy title** at the top of the tile (Tile 1: "Where you start", Tile 2: "What you do with it").
2. **Inline value row** matching `frontend/src/pages/openings/ExplorerTab.tsx` rows 2 & 3:
   - Label + numeric value (colored by sig-test verdict zone) + popover icon
   - Tile 1 label: "Avg eval at endgame entry"; popover = `BulletConfidencePopover` (already shows n, p-value, confidence inside)
   - Tile 2 label: "Endgame score"; popover = `ScoreConfidencePopover` (same)
3. **`MiniBulletChart`** below the inline value row — same component as Openings ExplorerTab uses for eval and score bullets. No new chart component.
4. **No standalone stats line** ("n=… · p<0.05") — n and p-value live INSIDE the existing popovers. Don't duplicate.

- **D-05:** **n ≥ 10** is the gate for both compute and render — matches the project's existing chess-score / eval-bullet convention everywhere else.
- **D-06:** Empty / sparse states:
  - `n < 10` on a tile → tile renders the same "Not enough data yet" placeholder used elsewhere in the codebase.
  - Both tiles have zero data (no endgame games at all) → hide the entire section.
  - Mixed sparse (one tile <10, other ≥10) is essentially impossible in practice. If it ever happens, render both tiles with the empty one showing the placeholder.

**Sig-Test Verdicts**
- **D-07:** Tile 1 (entry eval): one-sample test of mean against 0, Wald z. Mate scores excluded (`eval_cp NOT NULL`).
- **D-08:** Tile 2 (endgame score): Wilson score test against 50%.
- **D-09:** Three-state color: sig positive → green (`ZONE_SUCCESS`), sig negative → red (`ZONE_DANGER`), not sig → neutral gray (`ZONE_NEUTRAL`). Reuse existing theme constants.
- **D-10:** Significance threshold: p < 0.05.

**Backend Additions**
- **D-11:** `EndgamePerformanceResponse` gains:
  - `entry_eval_mean_pawns: float`
  - `entry_eval_n: int` (mate excluded, `eval_cp NOT NULL`)
  - `entry_eval_p_value: float | None` (Wald z; None when n < 10)
  - `endgame_score_p_value: float | None` (Wilson score test against 50%; None when n < 10)
- **D-12:** Aggregation reuses the existing `first_endgame` ply walk in `app/repositories/endgame_repository.py`.

**Concept-Explainer Accordion**
- **D-13:** Add two paragraphs to existing `endgame-concepts-trigger` accordion in `Endgames.tsx`:
  - "Avg eval at endgame entry" — Stockfish-eval-at-entry concept, equal-footing baseline (~0 cp), positive/negative meaning, "we can't tell" null framing, mate exclusion.
  - "Absolute endgame score" — 50% break-even line under rating-matched opponents, Wilson score test, "we can't tell" framing. Note Opponent Strength filter link.
- **D-14:** Place both new paragraphs after the existing Conversion / Parity / Recovery paragraphs and before the trailing rating-changes caveat paragraph.

**Visual / Axis Defaults (Claude's discretion — iterate during execution)**
- **D-15:** Pawn-axis domain for Tile 1: **±2.0 pawns**.
- **D-16:** Score-axis domain and neutral band for Tile 2: **reuse the existing Openings score-bullet constants** (`SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN`, `SCORE_BULLET_NEUTRAL_MAX`).
- **D-17:** Mobile ordering when stacked: **entry-eval first, score second**.

**Out of Scope**
- **D-18:** No clock-diff pairing in this section.
- **D-19:** No per-TC stratification of entry eval.
- **D-20:** No distribution-histogram view of per-game evals.
- **D-21:** WDL table stays exactly as-is. Score Gap column is **not** removed and not given a sig test in this phase.

### Claude's Discretion

- Final wording of the accordion paragraphs.
- Final visual polish (spacing, alignment of the inline value row, info-icon placement).
- Whether to colorize the punchy title text or only the value text. **Default: only the value text is colored** (matching the Openings ExplorerTab pattern).

### Deferred Ideas (OUT OF SCOPE)

- Distribution / histogram view of per-game entry evals — future "click to expand" detail.
- Per-TC stratification of entry eval — population baseline TC-invariant under equal-footing.
- Sig-test on Score Gap — out of scope this phase.
- Cross-user across-game eval × clock-diff correlation as a displayed metric.
- Pre-endgame eval over time chart (analog of `EndgameScoreOverTimeChart`) — future phase if user asks.

</user_constraints>

<phase_requirements>
## Phase Requirements

REQUIREMENTS.md lists Phase 81 as "TBD". The locked decisions above (D-01..D-21) **are** the requirement set for this phase. The mapping below cross-references each decision to the research findings that enable implementation.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01..D-04 | Section placement + 2-tile composition | `frontend/src/pages/Endgames.tsx` lines 339-403 — verified `showPerfSection` block; insert above `<EndgamePerformanceSection ... />` at line 392. |
| D-05 | n ≥ 10 gate | `OPENING_INSIGHTS_CONFIDENCE_MIN_N = 10` in `app/services/opening_insights_constants.py`; `MIN_GAMES_FOR_RELIABLE_STATS = 10` in `frontend/src/lib/theme.ts`. |
| D-06 | Sparse-state placeholder | Pattern: in `ExplorerTab.tsx` an em-dash `—` is rendered when `hasMgEval` is false (line 171). Section-hide pattern: `showPerfSection = !!(perfData && perfData.endgame_wdl.total > 0)` in `Endgames.tsx` line 321. |
| D-07 | Wald z mean test | `app/services/eval_confidence.py::compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)` returns `(confidence, p_value, mean, ci_half_width)`. |
| D-08 | Wilson score test vs 50% | `app/services/score_confidence.py::compute_confidence_bucket(w, d, l, n)` returns `(confidence, p_value, se)`. Two-sided Wilson, well-defined at boundaries. |
| D-09 | Three-state color | `ZONE_SUCCESS`/`ZONE_DANGER`/`ZONE_NEUTRAL` exported from `frontend/src/lib/theme.ts`. |
| D-10 | p < 0.05 | `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P = 0.05` constant; `isConfident(level)` from `frontend/src/lib/significance.ts` returns true for `medium`/`high` (which both require p < 0.05 + n ≥ 10). |
| D-11 | Four new response fields | Add to `app/schemas/endgames.py::EndgamePerformanceResponse` (line 107). |
| D-12 | SQL reuse | `query_endgame_bucket_rows` (line 233 in `endgame_repository.py`) already projects `entry_eval_cp`/`entry_eval_mate` per game. The orchestrator `get_endgame_overview` already fetches `entry_rows` (line 1951). Aggregate Python-side; no new query. |
| D-13, D-14 | Accordion paragraphs | `endgame-concepts-trigger` AccordionItem at line 344 of `Endgames.tsx`; insert two `<p>` blocks before line 382 (rating-changes caveat). |
| D-15 | ±2.0 pawn axis | Verified by `reports/benchmarks-2026-05-04.md` §3c: pooled `[p05, p95] = [−182.9, +197.0]` cp → symmetric **±200 cp = ±2.0 pawns** is the recommendation. |
| D-16 | Score-bullet constants | `SCORE_BULLET_CENTER = 0.5`, `SCORE_BULLET_NEUTRAL_MIN = -0.05`, `SCORE_BULLET_NEUTRAL_MAX = 0.05`, `SCORE_BULLET_DOMAIN = 0.25` — all already exported from `frontend/src/lib/scoreBulletConfig.ts`. **No extraction needed.** |
| D-17 | Mobile ordering | Achieved via Tailwind `order-` utilities or natural document order (entry-eval tile first in JSX → first on mobile). |
| D-18..D-21 | Out of scope | Confirmed; no code touches the WDL table, clock-diff section, or score-over-time chart. |

</phase_requirements>

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | HTTP layer (existing endpoint) | [VERIFIED: pyproject.toml] |
| Pydantic | v2 | Schema validation (`EndgamePerformanceResponse`) | [VERIFIED: existing schema in `app/schemas/endgames.py`] |
| SQLAlchemy 2.x async | — | DB access (no SQL changes this phase) | [VERIFIED: `app/repositories/endgame_repository.py`] |
| React | 19 | Frontend components | [VERIFIED: package.json] |
| TypeScript | — | Frontend types | [VERIFIED: codebase convention] |
| Tailwind CSS | — | Styling (`charcoal-texture`, `lg:grid-cols-2`, etc.) | [VERIFIED: `Endgames.tsx`] |
| radix-ui Popover | — | Used by `BulletConfidencePopover` / `ScoreConfidencePopover` | [VERIFIED: `BulletConfidencePopover.tsx` line 2] |
| lucide-react | — | `HelpCircle` icon for popover triggers | [VERIFIED: existing usage] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math (stdlib) | — | erfc/sqrt for two-sided z and Wilson p-values | Already used by both helpers |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `compute_eval_confidence_bucket` for Tile 1 | `scipy.stats.ttest_1samp` | scipy adds ~30 MB runtime dep for sub-1% precision gain at n ≥ 10. Project policy (CLAUDE.md): 11 critical runtime deps; adding scipy is out of scope. **Reject.** |
| Hand-rolled Wilson test for Tile 2 | `compute_confidence_bucket` | The existing helper is the project's canonical chess-score sig test (per the user's memory note "Trust the established Wilson stat method"). **Use it as-is.** |
| New chart component | Reuse `MiniBulletChart` | Already supports `value`, `center`, `neutralMin`, `neutralMax`, `domain`, `ciLow`, `ciHigh`, `barColor`. **Reuse.** |
| New popover components | Reuse `BulletConfidencePopover` + `ScoreConfidencePopover` | Already render n, p-value, confidence-level, headline. **Reuse without modification.** |

**Installation:** None — all dependencies already present.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser: Endgames page                                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  <EndgamesPage> (frontend/src/pages/Endgames.tsx)          │ │
│  │                                                              │ │
│  │  showPerfSection block:                                     │ │
│  │    <h2>Endgame Overall Performance</h2>                     │ │
│  │    <Accordion endgame-concepts-trigger>                     │ │
│  │      ↳ +2 new <p> paragraphs (D-13, D-14)                   │ │
│  │    </Accordion>                                              │ │
│  │    ────► NEW: <EndgameStartVsEndSection data={perfData}/>  │ │
│  │            ↳ Tile 1: <EntryEvalTile>                        │ │
│  │            ↳ Tile 2: <EndgameScoreTile>                     │ │
│  │            ↳ each: inline value row + MiniBulletChart       │ │
│  │            ↳ each: BulletConfidencePopover / ScoreConfPop   │ │
│  │    <EndgamePerformanceSection /> (UNCHANGED)                │ │
│  │    <EndgameScoreOverTimeChart /> (UNCHANGED)                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│            useEndgameOverview hook (TanStack Query)              │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │ GET /api/endgames/overview
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  FastAPI: app/routers/endgames.py                                │
│    @router.get("/overview") → endgame_service.get_endgame_overview│
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  app/services/endgame_service.py                                 │
│                                                                   │
│  get_endgame_overview():                                         │
│    entry_rows = await query_endgame_entry_rows(...)              │
│      ↳ existing repo fn — projects eval_cp/eval_mate per span    │
│    perf = _get_endgame_performance_from_rows(                    │
│              endgame_rows, non_endgame_rows, entry_rows)         │
│            ────► EXTEND: aggregate entry-eval (sum, sumsq, n)    │
│                  ────► call compute_eval_confidence_bucket()     │
│                  ────► call compute_confidence_bucket()          │
│                  ────► populate four new fields                  │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  PostgreSQL (UNCHANGED — no SQL added)                           │
│    GamePosition (eval_cp, eval_mate per ply, indexed)            │
│    Game (result, user_color, played_at)                          │
└──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (delta only)

```
app/
├── schemas/
│   └── endgames.py                        # extend EndgamePerformanceResponse (4 new fields)
├── services/
│   └── endgame_service.py                 # extend _get_endgame_performance_from_rows
└── (no new repository function)

frontend/src/
├── components/
│   └── charts/
│       └── EndgameStartVsEndSection.tsx   # NEW — twin-tile section
├── types/
│   └── endgames.ts                        # extend EndgamePerformanceResponse
├── lib/
│   └── theme.ts                           # already exports ZONE_*; no edits
└── pages/
    └── Endgames.tsx                       # render new section above WDL table; +2 accordion <p>

tests/
├── services/
│   └── test_endgame_start_vs_end.py       # NEW — pure-fn aggregation tests
├── test_endgame_service.py                # extend with EndgamePerformanceResponse contract test
└── test_endgames_router.py                # extend with API contract assertions

frontend/src/components/charts/__tests__/
└── EndgameStartVsEndSection.test.tsx      # NEW — render/snapshot/zone-color tests
```

### Pattern 1: Inline Value Row + Popover Icon + Bullet Chart

**What:** A two-line per-row pattern: label-and-value text on top, a `MiniBulletChart` below.
**When to use:** Both tiles in this phase. The pattern is tested and working in `ExplorerTab.tsx`.
**Example:** (excerpt, `frontend/src/pages/openings/ExplorerTab.tsx` lines 120-200, simplified)

```typescript
// Source: frontend/src/pages/openings/ExplorerTab.tsx

<div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
  {/* Inline value row */}
  <span className="flex items-center gap-1 text-sm tabular-nums w-full">
    <span className="text-muted-foreground">Score:</span>
    <span className="ml-auto font-semibold" style={scoreColor ? { color: scoreColor } : undefined}>
      {scorePct}%
    </span>
    <ScoreConfidencePopover
      level={stats.confidence}
      pValue={stats.p_value}
      score={stats.score}
      gameCount={stats.total}
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

For Phase 81, each tile owns one row of this grid (label-value + chart). Two tiles side-by-side → use a wrapping `lg:grid-cols-2 gap-4` container.

### Pattern 2: Backend Aggregation on Pre-Fetched Rows

**What:** Compute the new fields inside `_get_endgame_performance_from_rows` from the already-passed `entry_rows`. The orchestrator (`get_endgame_overview`) already fetches them once and threads them to multiple aggregators (line 1951-1964).
**When to use:** When the data needed is a column already on a query that runs anyway. Avoids redundant DB queries.
**Example:** (sketch, to be implemented in Plan)

```python
# Source: extend app/services/endgame_service.py::_get_endgame_performance_from_rows

def _get_endgame_performance_from_rows(
    endgame_rows: list[Row[Any]],
    non_endgame_rows: list[Row[Any]],
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> EndgamePerformanceResponse:
    endgame_wdl = _build_wdl_summary(endgame_rows)
    non_endgame_wdl = _build_wdl_summary(non_endgame_rows)

    # Aggregate entry-eval, mate-excluded, signed user-perspective.
    # entry_rows columns: (game_id, endgame_class, result, user_color, eval_cp, eval_mate)
    # — per query_endgame_entry_rows. Use _classify_endgame_bucket's sign convention.
    eval_sum = 0.0
    eval_sumsq = 0.0
    eval_n = 0
    seen_game_ids: set[int] = set()
    for row in entry_rows:
        if row.game_id in seen_game_ids:
            continue  # one row per game (entry_rows can have multiple class spans)
        seen_game_ids.add(row.game_id)
        if row.eval_mate is not None:
            continue  # mate-excluded per D-07
        if row.eval_cp is None:
            continue  # NULL eval excluded
        sign = 1 if row.user_color == "white" else -1
        signed_cp = sign * row.eval_cp
        eval_sum += float(signed_cp)
        eval_sumsq += float(signed_cp * signed_cp)
        eval_n += 1

    # Wald z one-sample test (mean vs 0 cp); helper returns CI half-width too.
    _conf, p_eval_or_one, mean_cp, _ci_half = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, eval_n
    )
    entry_eval_p_value: float | None = p_eval_or_one if eval_n >= 10 else None
    entry_eval_mean_pawns = mean_cp / 100.0 if eval_n > 0 else 0.0

    # Wilson score test of endgame_wdl against 50%.
    _wconf, p_score_or_one, _se = compute_confidence_bucket(
        endgame_wdl.wins, endgame_wdl.draws, endgame_wdl.losses, endgame_wdl.total
    )
    endgame_score_p_value: float | None = p_score_or_one if endgame_wdl.total >= 10 else None

    return EndgamePerformanceResponse(
        endgame_wdl=endgame_wdl,
        non_endgame_wdl=non_endgame_wdl,
        endgame_win_rate=endgame_wdl.win_pct,
        entry_eval_mean_pawns=entry_eval_mean_pawns,
        entry_eval_n=eval_n,
        entry_eval_p_value=entry_eval_p_value,
        endgame_score_p_value=endgame_score_p_value,
    )
```

**Sign convention** mirrors `_classify_endgame_bucket` (line 167 of `endgame_service.py`): white-user `sign = 1`, black-user `sign = -1`. SQL projects raw white-perspective eval; service flips at read time. **[VERIFIED: comment block at lines 184-188]**

### Anti-Patterns to Avoid

- **Don't add a new SQL query for entry-eval aggregation.** `query_endgame_entry_rows` already returns the data; aggregate in Python next to the existing `_get_endgame_performance_from_rows`. Adding a separate SQL aggregation duplicates the index scan and the row-walk logic.
- **Don't expose a CI in the response payload.** The Wald-z helper returns `ci_half_width`; if you want a whisker on Tile 1, compute `ci_low = mean − ci_half_width` and `ci_high = mean + ci_half_width` *in pawns* and pass to `MiniBulletChart`. But D-15 (±2.0 pawn domain) means most CIs will overflow at n ≈ 50 (per-game SD ≈ 4.18 pawns ⇒ SE ≈ 0.59 pawns at n=50 ⇒ CI half-width ≈ 1.16 pawns). The whisker is informative even when wide — keep it. **Recommendation: include `entry_eval_ci_low_pawns` and `entry_eval_ci_high_pawns` (signed) in the response, mirroring how the Openings stats board does it for `eval_ci_low_pawns` / `eval_ci_high_pawns`.** Same for Tile 2: use `wilson_bounds(score, n)` and pass `ciLow` / `ciHigh` as already done in `ExplorerTab.tsx` line 149.
- **Don't editorialize the sig test.** Per the user's memory note: trust the established Wilson stat method. Don't invent a new method or write a custom note in the popover.
- **Don't render a separate "n=… · p<0.05" stats line.** Per CONTEXT.md specifics — popovers carry these.
- **Don't hide either tile when only one is sparse.** D-06: render both, the sparse one shows the placeholder. Layout stability matters.
- **Don't change `endgame_zones.py`.** No new zone is introduced; the three-state color uses theme constants directly. The CI drift gate (`scripts/gen_endgame_zones_ts.py`) does **not** need to run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wald z one-sample mean test | A new `_compute_z_pvalue()` helper | `compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)` from `app/services/eval_confidence.py` | Already handles n<10 gate, n=1 edge, SE=0 degeneracy, Bessel correction, two-sided erfc, returns CI half-width too. |
| Wilson score test vs 50% | A new chess-score sig helper | `compute_confidence_bucket(w, d, l, n)` from `app/services/score_confidence.py` | Two-sided Wilson, well-defined at all-wins/all-losses boundaries; project's canonical method. |
| Wilson 95% CI bounds | A new bounds calculator | `wilson_bounds(p, n)` from `app/services/score_confidence.py` | Returns clamped `(lower, upper)` in [0, 1]; inversion of the score test (CI and verdict agree by construction). |
| Bullet chart with neutral band | A new chart component | `MiniBulletChart` (`frontend/src/components/charts/MiniBulletChart.tsx`) | Already supports center, domain, neutral band, CI whisker, zone fill, neutral fill. |
| Confidence-detail popover (eval) | A new popover | `BulletConfidencePopover` | Drop-in; renders `EvalConfidenceTooltip` with n, p, mean, color baseline. |
| Confidence-detail popover (score) | A new popover | `ScoreConfidencePopover` | Drop-in; renders `WdlConfidenceTooltip` with n, p, score, headline. |
| Color flip for eval sign | A new helper | Inline `sign = 1 if user_color == "white" else -1` (mirrors `_classify_endgame_bucket`) | The pattern is established and self-evident; a new helper would just rename it. |
| Score-bullet domain / center / neutral | Hard-coded values | `SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN`, `SCORE_BULLET_NEUTRAL_MAX`, `scoreBulletDomain()` from `frontend/src/lib/scoreBulletConfig.ts` | Already exported and consumed by Openings; reusing keeps visual parity (the explicit goal of D-16). |
| Three-state zone color (eval pawns) | Hard-coded thresholds | Define a small helper or inline check using `ZONE_SUCCESS`/`ZONE_DANGER`/`ZONE_NEUTRAL` and the `isConfident(level)` gate from `frontend/src/lib/significance.ts` | Match the Openings pattern: only paint the value color when both (a) confidence ≠ 'low' AND (b) the value falls outside the neutral band. Pure inline logic; not worth a util. |

**Key insight:** This phase is a composition phase, not a "build new things" phase. Every backend math function and every frontend chart/popover already exists. **The single new artifact is the `EndgameStartVsEndSection.tsx` container component** — and even that is a thin wrapper over reused parts.

## Runtime State Inventory

> Phase 81 is **purely additive** code/schema work. No rename, no migration, no string replacement.
>
> The four new schema fields have **default values** that work for users with no endgame games (n = 0): `entry_eval_mean_pawns = 0.0`, `entry_eval_n = 0`, `entry_eval_p_value = None`, `endgame_score_p_value = None`. There is no datastore that needs reseeding.
>
> No deferred categories apply:
> - **Stored data:** None — no new persisted columns. Eval data already exists in `game_positions` (filled by Phase 79).
> - **Live service config:** None.
> - **OS-registered state:** None.
> - **Secrets/env vars:** None.
> - **Build artifacts:** None.
>
> Section explicitly omitted (rename-only inventory does not apply).

## Common Pitfalls

### Pitfall 1: Double-counting per-game when iterating `entry_rows`
**What goes wrong:** `query_endgame_entry_rows` returns ONE row per (game, endgame_class) span. A game with two qualifying spans (e.g. KR_KR then KP_KP) appears twice. Naively summing eval over `entry_rows` would double-count that game.
**Why it happens:** The schema convention (see `query_endgame_bucket_rows` at line 233 — "exactly one row per endgame game") differs from `query_endgame_entry_rows`. The orchestrator currently passes `entry_rows` (multi-row) to the performance computer.
**How to avoid:** Either (a) iterate `entry_rows` and dedupe by `game_id` (use `seen_game_ids: set[int]` — same approach `_compute_score_gap_material` uses at line 748 of `endgame_service.py`), or (b) switch the call site to use `query_endgame_bucket_rows` which is one-row-per-game by construction. **Recommendation: (a).** Smaller blast radius — the existing call sites for `query_endgame_entry_rows` rely on its multi-row shape (per-class WDL aggregation in `_aggregate_endgame_stats`).
**Warning signs:** `entry_eval_n > endgame_wdl.total` in the API response, or unit-test failures comparing the new field to `endgame_wdl.total` for users with rook→pawn class transitions.

### Pitfall 2: Sign-flip omission for black users
**What goes wrong:** `eval_cp` in `game_positions` is white-perspective. A black user with raw `eval_cp = +200` is actually `−200` from their perspective (they're losing by 2 pawns). Forgetting the flip would invert the sign for ~half the user's games.
**Why it happens:** Easy to overlook — the SQL doesn't flip; the service does (REFAC-02 lock).
**How to avoid:** Apply `sign = 1 if user_color == "white" else -1` before adding to `eval_sum` / `eval_sumsq`. Mirrors `_classify_endgame_bucket` at line 194-202.
**Warning signs:** Per-user means cluster around the population white-skew (~+25 cp at MG entry, smaller at EG entry per benchmark v3) instead of around 0 — i.e. the test would systematically show black users as "behind" and white users as "ahead."

### Pitfall 3: Mate-row contamination
**What goes wrong:** A row with `eval_mate IS NOT NULL` and `eval_cp IS NULL` (mate score) is excluded from the test (D-07). But a defensive coding might do `signed_cp = eval_cp or 0`, which would silently turn `None` into `0` and inflate `eval_n` while pulling the mean toward 0.
**Why it happens:** Python `None or 0 == 0` truthiness trap.
**How to avoid:** Explicit `if row.eval_cp is None: continue` and `if row.eval_mate is not None: continue` before incrementing. Don't use `or` for numeric defaulting on an Optional column.
**Warning signs:** `entry_eval_n` matches `endgame_wdl.total` exactly even though the benchmark shows ≈5.2% mate prevalence at endgame entry. Test: load a fixture with one mate row and assert `entry_eval_n == total - 1`.

### Pitfall 4: Wide CI whisker rendering as a render bug
**What goes wrong:** With per-game SD ≈ 4.18 pawns and an axis of ±2.0 pawns, the 95% CI half-width at n=50 is ≈ 1.16 pawns. At small N (n=10..30) the CI usually exceeds the axis. `MiniBulletChart` already handles this by rendering open-ended whiskers (no end cap) when `ciLow < axisMin` or `ciHigh > axisMax` — see lines 198-235 of `MiniBulletChart.tsx`. **Don't add custom clamping.**
**Why it happens:** Implementer might think "the whisker breaks the box" and add manual clamping to make it fit, hiding the real signal that the data is noisy.
**How to avoid:** Pass raw `ciLow` / `ciHigh` (in pawn units, signed). The chart clamps and suppresses end caps internally. The "looks too wide" is the desired UX signal — see `openingStatsZones.ts` comment at line 11-13: "this is the desired UX signal 'we don't have enough data to tell.'"

### Pitfall 5: Forgetting the n < 10 gate on p-value field
**What goes wrong:** `compute_eval_confidence_bucket(0, 0, 0)` returns `(low, 1.0, 0.0, 0.0)` — p=1.0, not None. If you assign this directly to `entry_eval_p_value`, the API will return `1.0` instead of `null`, breaking D-11.
**Why it happens:** Helper API returns float-always for arithmetic generality.
**How to avoid:** Branch explicitly: `entry_eval_p_value = p if eval_n >= 10 else None`. Same for the score test.
**Warning signs:** Schema test `assert response.entry_eval_p_value is None` fails on a user with n=5 endgame games.

### Pitfall 6: TypeScript `noUncheckedIndexedAccess` on the new fields
**What goes wrong:** `noUncheckedIndexedAccess` is enabled (CLAUDE.md). Reading `perfData.entry_eval_p_value` returns `number | null` (correct). But computing the verdict color requires narrowing: `if (p !== null && p < 0.05 && mean > 0)`.
**Why it happens:** TypeScript will surface the issue; just be aware to narrow before comparison.
**How to avoid:** Standard `if (p !== null && ...)` narrowing. No `as` casts.

### Pitfall 7: ty-check on the Pydantic schema extension
**What goes wrong:** Adding `entry_eval_p_value: float | None = None` is fine for Pydantic v2 but ty wants every model boundary to be explicit. The default `None` is needed so existing tests that construct the response without the new fields don't break — a defensive default may be required for tests using `EndgamePerformanceResponse(...)` mock factories.
**Why it happens:** Backwards-compat with existing test fixtures.
**How to avoid:** Add `= 0.0` / `= 0` / `= None` defaults on all four new fields. Production code should always populate them; defaults make the schema migration drop-in.
**Warning signs:** Pre-existing tests that construct `EndgamePerformanceResponse(endgame_wdl=..., non_endgame_wdl=..., endgame_win_rate=...)` start failing.

### Pitfall 8: Sentry double-capture on aggregation errors
**What goes wrong:** Adding a `try/except sentry_sdk.capture_exception()` around the new aggregation when no exception path actually exists creates noise.
**Why it happens:** Reflexive following of CLAUDE.md "Always call `sentry_sdk.capture_exception()` in every non-trivial except block."
**How to avoid:** Don't add a catch block. The aggregation is pure-Python arithmetic; no I/O, no parsing of user input. The n ≥ 10 gate inside the helpers prevents division by zero. Let unexpected exceptions propagate to the route-level handler that's already wired.

## Code Examples

### Example 1: Wald-z helper consumption (existing pattern from `stats_service.py`)

```python
# Source: app/services/stats_service.py lines 410-425 (verified)
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
    eval_n = pe.eval_n_mg
```

### Example 2: Wilson helper consumption (existing pattern from `openings_service.py`)

```python
# Source: tests/test_openings_service.py lines 775+ (verified)
from app.services.score_confidence import compute_confidence_bucket

confidence, p_value, se = compute_confidence_bucket(w, d, l, n)
# Use `confidence` for bucket; `p_value` for raw p; `se` is informational only.
```

### Example 3: Per-game dedupe over `entry_rows` (existing pattern)

```python
# Source: app/services/endgame_service.py lines 748-787 (verified)
rows_by_game: dict[int, list[Row[Any]]] = defaultdict(list)
for row in entry_rows:
    rows_by_game[row.game_id].append(row)

# Then iterate one game at a time. For Phase 81 we need only ONE row per game
# (the eval at first qualifying span — array_agg ORDER BY ply already gives
# this for `query_endgame_bucket_rows` but NOT for `query_endgame_entry_rows`
# which is per-class). Choose the first row deterministically: lowest endgame_class.
```

### Example 4: Frontend tile layout (mirror this for both tiles)

```typescript
// Mirror of: frontend/src/pages/openings/ExplorerTab.tsx lines 120-200
// (slimmed to just the inline-row + bullet-chart pair for one tile)

<div
  className="charcoal-texture rounded-md p-4"
  data-testid="tile-entry-eval"
>
  <h3 className="text-base font-semibold mb-2">Where you start</h3>
  <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
    <span className="flex items-center gap-1 text-sm tabular-nums w-full">
      <span className="text-muted-foreground">Avg eval at endgame entry:</span>
      <span
        className="ml-auto font-semibold"
        style={evalColor ? { color: evalColor } : undefined}
      >
        {formatSignedEvalPawns(entryEvalMeanPawns)}
      </span>
      <BulletConfidencePopover
        level={evalConfidenceLevel}
        pValue={entryEvalPValue}
        gameCount={entryEvalN}
        evalMeanPawns={entryEvalMeanPawns}
        color="white"  /* endgame stats are color-agnostic; pass white for the white-tick fallback (D-19) */
        testId="entry-eval-popover-trigger"
      />
    </span>
    <div className="min-w-0 tabular-nums">
      <MiniBulletChart
        value={entryEvalMeanPawns}
        center={0}
        neutralMin={ENTRY_EVAL_NEUTRAL_MIN_PAWNS}  /* TBD value or reuse openingStatsZones */
        neutralMax={ENTRY_EVAL_NEUTRAL_MAX_PAWNS}
        domain={2.0}  /* D-15 */
        ciLow={entryEvalCiLowPawns}
        ciHigh={entryEvalCiHighPawns}
        barColor="neutral"
        ariaLabel={`Avg eval at endgame entry: ${entryEvalMeanPawns.toFixed(2)} pawns`}
      />
    </div>
  </div>
</div>
```

### Example 5: Three-state zone color (gated on confidence)

```typescript
// Pattern from frontend/src/pages/openings/ExplorerTab.tsx lines 70-73, 82-86

import { isConfident } from '@/lib/significance';
import { ZONE_SUCCESS, ZONE_DANGER, ZONE_NEUTRAL } from '@/lib/theme';

// Confidence level derived on the frontend from p-value + n; matches
// score_confidence.compute_confidence_bucket gate.
function deriveLevel(p: number | null, n: number): 'low' | 'medium' | 'high' {
  if (n < 10 || p == null) return 'low';
  if (p < 0.01) return 'high';
  if (p < 0.05) return 'medium';
  return 'low';
}

// Three-state color (D-09): only paint when confident AND outside the neutral band.
const evalLevel = deriveLevel(entryEvalPValue, entryEvalN);
const evalZoneHex = entryEvalMeanPawns >= ENTRY_EVAL_NEUTRAL_MAX_PAWNS
  ? ZONE_SUCCESS
  : entryEvalMeanPawns <= ENTRY_EVAL_NEUTRAL_MIN_PAWNS
    ? ZONE_DANGER
    : ZONE_NEUTRAL;
const evalColor: string | undefined =
  isConfident(evalLevel) && evalZoneHex !== ZONE_NEUTRAL ? evalZoneHex : undefined;
```

**Note on the neutral band for Tile 1:** the existing MG-entry constants `EVAL_NEUTRAL_MIN_PAWNS = -0.30` / `MAX = 0.30` are calibrated for MG entry (per-game SD ≈ 2.4 pawns). EG entry has SD ≈ 4.4 pawns (per benchmarks-2026-05-04 §3c) — wider neutral band may be appropriate. Per-user means at EG entry pool to `[p25, p75] = [-53.8, +75.3]` cp, suggesting a symmetric **±0.75 pawns**. The planner should decide whether to:
- (a) Reuse `EVAL_NEUTRAL_MIN_PAWNS` / `EVAL_NEUTRAL_MAX_PAWNS` from `openingStatsZones.ts` (consistency, but tighter than data warrants),
- (b) Add new constants `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75` / `MAX = +0.75` (data-driven; matches benchmark v3 §3c recommendation), or
- (c) Reuse but document the tightness in the popover.

**Recommendation:** (b). Population data is unambiguous; using the wider band prevents false-positive zone color when the user's mean is +0.4 pawns and the test is significant only because n is huge. Define the new constants in a new module (or extend `openingStatsZones.ts` and rename it; small refactor) — this is **Claude's discretion** territory under D-15.

### Example 6: Section render guard (D-06 — hide when no data)

```typescript
// Source: pattern from frontend/src/pages/Endgames.tsx line 321
const showStartVsEnd = !!(perfData && perfData.endgame_wdl.total > 0);

// Then inside the showPerfSection block, before <EndgamePerformanceSection ...>:
{showStartVsEnd && (
  <EndgameStartVsEndSection data={perfData} />
)}
<div className="charcoal-texture rounded-md p-4">
  <EndgamePerformanceSection data={perfData} scoreGap={scoreGapData} />
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Score-Gap-as-second-tile + WDL table restructure (rescinded design) | Absolute endgame score vs 50% as second tile, WDL table unchanged | 2026-05-09 (D-21 lock) | The original `.planning/notes/endgame-entry-eval-tile-design.md` design is partly obsolete. Use only its benchmark/null-framing content. |
| One-sample t-test against 0 (n=30 floor in obsolete note) | Wald z (n ≥ 10 floor) | This phase (D-05, D-07) | n=10 matches the project's existing chess-score / eval-bullet convention everywhere else. |
| scipy.stats.ttest_1samp | math.erfc-based stdlib helper | 2025-Q4 (Phase 80 D-08) | scipy out of scope; n ≥ 10 makes z and t indistinguishable. |
| Per-color asymmetric MG eval baseline (+31.5 / −18.9 cp) | Symmetric ±25 cp (white tempo) | 2026-05-04 v3 (Phase 80) | EG-entry baseline analog is ~±10 cp; **for this phase the Tile 1 H0 is 0 cp**, no per-color baseline tick needed (the centering decision was for MG only). |

**Deprecated/outdated:**
- Tile-anatomy "n=… · p<0.05" stats line (from `.planning/notes/endgame-entry-eval-tile-design.md` §"Tile anatomy" point 4) — **rescinded by D-04**; popovers carry n and p, the inline UI does not.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The MG-entry `EVAL_NEUTRAL_MIN_PAWNS / MAX_PAWNS = ±0.30` is too tight for EG entry; recommend ±0.75 from benchmark v3 §3c data | Code Examples (Example 5) | If wrong, the neutral band is over-wide and the test rarely shows green/red even with strong signal. **Mitigated:** the planner / discuss-phase can reconcile by reading `reports/benchmarks-2026-05-04.md` §3c directly. The recommendation is sourced from that report (CITED, not assumed). Marking as **A1 only because** the project hasn't yet committed to a specific EG-entry neutral-band number; it's Claude's discretion under D-15. |
| A2 | Iterating `entry_rows` and deduping by `game_id` is preferable to switching to `query_endgame_bucket_rows` | Pitfall 1 | If wrong, refactor the call site to use the bucket-row variant. Both are correct; (a) has smaller blast radius. |

**All other claims are VERIFIED** (file/line citation in the codebase) **or CITED** (from benchmark report / project docs / existing tests). The Assumptions Log is intentionally short — this phase is well-mapped.

## Open Questions (RESOLVED)

> Each question carries an inline **Recommendation** that the planning phase has accepted. Resolutions are reflected in `81-01..81-04-PLAN.md` and `81-CONTEXT.md` Q1/A1 rows.

1. **EG-entry neutral band — reuse MG ±0.30 or define new ±0.75?**
   - What we know: benchmark v3 §3c recommends ±0.75 pawns; the project does not have an existing EG-entry constant.
   - What's unclear: whether visual consistency with MG bullet (D-15 → ±2.0 pawn axis is the only locked visual; neutral band is discretion).
   - Recommendation: define new `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS = ±0.75` in `openingStatsZones.ts` (or a new `endgameEntryEvalConfig.ts`); cite the benchmark report in the comment.

2. **Should `EndgamePerformanceResponse` carry `entry_eval_ci_low_pawns` / `entry_eval_ci_high_pawns` for the bullet whisker?**
   - What we know: the Wald-z helper returns `ci_half_width`; the score helper has `wilson_bounds(p, n)` for the score CI.
   - What's unclear: whether the planner wants the whisker on Tile 1 (CONTEXT.md doesn't lock it; the Openings ExplorerTab eval row uses one).
   - Recommendation: include both pairs in the response. Whisker rendering is "free" and matches Openings.

3. **TypeScript: where do the new constants for the EG-entry neutral band live?**
   - What we know: `frontend/src/lib/openingStatsZones.ts` is named for openings; placing endgame constants there is a slight smell.
   - What's unclear: whether to extend it (rename to `phaseEntryEvalZones.ts`?), add a new module (`endgameEntryEvalZones.ts`), or inline in the new section component.
   - Recommendation: new module `frontend/src/lib/endgameEntryEvalZones.ts` to avoid renaming. Keep `openingStatsZones.ts` MG-only for clarity; both exports and consumers are stable.

4. **How does the new section interact with the unreliable-stats opacity dim?**
   - What we know: `MIN_GAMES_FOR_RELIABLE_STATS = 10`; the Openings stats board applies `opacity: UNRELIABLE_OPACITY` when below.
   - What's unclear: D-06 says "render placeholder when n < 10," not "render dimmed."
   - Recommendation: use the placeholder, not the opacity dim. The placeholder is more informative ("Not enough data yet" reads as actionable); opacity is a softer signal already used elsewhere.

## Environment Availability

> Phase 81 has no new external dependencies. All code/config-only changes use existing stack:
> - PostgreSQL (existing)
> - Python stdlib (math.erfc, math.sqrt) — already in use by sig helpers
> - npm packages (radix-ui, lucide-react, react-chessboard, etc.) — already installed
>
> **Step 2.6: Audit completed; no new dependencies. Skipping table.**

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.0.x + pytest-asyncio (verified — `tests/services/test_eval_confidence.py` runs under it) |
| Backend config file | `pytest.ini` / `pyproject.toml` (existing — no Wave 0 work) |
| Backend quick run | `uv run pytest tests/services/test_endgame_start_vs_end.py -x` (after Wave 0 creates the file) |
| Backend full suite | `uv run pytest` |
| Frontend framework | vitest + React Testing Library (verified — `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx` exists) |
| Frontend quick run | `cd frontend && npm test -- EndgameStartVsEndSection` (after Wave 0 creates the file) |
| Frontend full suite | `cd frontend && npm test` |
| Phase gate | `uv run pytest && uv run ruff check . && uv run ty check app/ tests/ && cd frontend && npm test && npm run lint && npm run knip && npm run build` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-07 (Wald z) | `compute_eval_confidence_bucket` already covered for the math | unit | `uv run pytest tests/services/test_eval_confidence.py -x` | ✅ |
| D-08 (Wilson) | `compute_confidence_bucket` already covered for the math | unit | `uv run pytest tests/services/test_score_confidence.py -x` | ✅ |
| D-11 (4 new fields) | `EndgamePerformanceResponse` includes the four fields with correct types | unit (schema contract) | `uv run pytest tests/test_endgame_service.py::TestEndgamePerformanceContract -x` | ❌ Wave 0 |
| D-12 (aggregation reuse) | `_get_endgame_performance_from_rows` aggregates entry-eval correctly: signed user perspective, mate excluded, NULL excluded, dedup by game_id, n=0/1/9/10 boundaries, color-flip correctness | unit | `uv run pytest tests/services/test_endgame_start_vs_end.py -x` | ❌ Wave 0 |
| D-12 | API contract: `/api/endgames/overview` returns `performance.entry_eval_*` and `performance.endgame_score_p_value` keys | integration | `uv run pytest tests/test_endgames_router.py::test_overview_includes_start_vs_end_fields -x` | ❌ Wave 0 |
| D-04, D-06 | Section renders only when `endgame_wdl.total > 0`; both tiles render when n ≥ 10; placeholder when n < 10 | unit (frontend) | `cd frontend && npm test -- EndgameStartVsEndSection` | ❌ Wave 0 |
| D-09 | Three-state color resolves correctly given `(mean, p, n)` inputs | unit (frontend) | `cd frontend && npm test -- EndgameStartVsEndSection.zoneColor` | ❌ Wave 0 (covered by same file) |
| D-01 | New section renders ABOVE `EndgamePerformanceSection` (DOM order) | unit (frontend, page-level) | `cd frontend && npm test -- Endgames.startVsEndOrder` | ❌ Wave 0 |
| D-13, D-14 | Two new accordion paragraphs render in the correct position | unit (frontend) | `cd frontend && npm test -- Endgames.conceptsAccordion` | ❌ Wave 0 |
| D-15, D-16 | MiniBulletChart receives correct domain (±2.0 / ±0.25) and centers (0 / 0.5) | unit (frontend) | covered by `EndgameStartVsEndSection.test.tsx` props assertions | ❌ Wave 0 |
| D-17 | Mobile order: entry-eval first | manual UAT (and Tailwind class snapshot) | visual on viewport ≤ 1024px | n/a |
| D-21 | WDL table component output unchanged | regression | `cd frontend && npm test -- EndgamePerformanceSection` (existing) | ✅ |

### Sampling Rate
- **Per task commit:** quick run for the file under edit (e.g. `uv run pytest tests/services/test_endgame_start_vs_end.py -x` after backend edits).
- **Per wave merge:** the wave's full backend pytest + frontend `npm test` for components changed in the wave.
- **Phase gate:** the full suite chain above; ty + ruff + knip + eslint + build all green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/services/test_endgame_start_vs_end.py` — covers D-12 aggregation (use NamedTuple stand-in rows mirroring `query_endgame_entry_rows` columns: `game_id, endgame_class, result, user_color, eval_cp, eval_mate`)
- [ ] `tests/test_endgame_service.py` — extend with `TestEndgamePerformanceContract` covering D-11 schema fields
- [ ] `tests/test_endgames_router.py` — extend with `test_overview_includes_start_vs_end_fields` covering D-11 wire format
- [ ] `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — covers D-04, D-06, D-09, D-15, D-16 (a single file is sufficient — vitest runs are quick)
- [ ] `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — page-level integration test for D-01 (DOM order) and D-13/D-14 (accordion paragraphs); reuse the existing `Endgames.statsBoard.test.tsx` setup pattern as a template

No framework install required — pytest, vitest, and RTL all in place.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (no change) | FastAPI-Users `current_active_user` already enforces auth on `/api/endgames/overview` |
| V3 Session Management | no | This phase introduces no new session paths |
| V4 Access Control | yes (no change) | The route is already user-scoped (`user_id=user.id` from `current_active_user`); no new authz surface |
| V5 Input Validation | yes (no change) | New fields are response-only; no new query params or request body |
| V6 Cryptography | no | No crypto involved |

### Known Threat Patterns for FastAPI + SQLAlchemy 2.x async

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection on new aggregation | Tampering | None new — Phase 81 uses no new SQL. Existing query goes through SQLAlchemy parameter binding (verified). |
| User-data leak via response shape | Information Disclosure | `entry_eval_mean_pawns` / `entry_eval_n` / p-values are aggregates of the user's own games and don't expose any other user's data; route remains `current_active_user`-scoped (no admin-only fields). |
| Stack-trace leak on aggregation error | Information Disclosure | None new — exceptions propagate to the existing FastAPI top-level handler, which already strips traces in production. |
| Over-large response (DoS) | DoS | None new — adding 4 small fields per response. Endgame games per user is bounded by import volume; the existing route has no n-cap, but each user's entry_rows is also bounded. No new risk. |

**No new security surface is introduced in this phase.** The four new fields are pure aggregates of data the route already returns, computed server-side.

## Sources

### Primary (HIGH confidence)
- `app/services/score_confidence.py` (full file read) — Wilson score test, two-sided, n ≥ 10 gate, `wilson_bounds` helper.
- `app/services/eval_confidence.py` (full file read) — Wald z one-sample mean test, returns `(confidence, p_value, mean, ci_half_width)`.
- `app/services/opening_insights_constants.py` (full file read) — `OPENING_INSIGHTS_CONFIDENCE_MIN_N = 10`, `OPENING_INSIGHTS_CI_Z_95 = 1.96`, p-value thresholds.
- `app/repositories/endgame_repository.py` (full file read) — `query_endgame_entry_rows` and `query_endgame_bucket_rows` already project `entry_eval_cp` / `entry_eval_mate`.
- `app/services/endgame_service.py` (lines 167-211, 700-787, 1620-1712, 1900-2000) — `_classify_endgame_bucket` sign-flip pattern, `_compute_score_gap_material` per-game dedupe pattern, `_get_endgame_performance_from_rows` extension target, `get_endgame_overview` orchestrator.
- `app/schemas/endgames.py` (lines 85-220) — `EndgamePerformanceResponse` exact location and shape.
- `frontend/src/components/charts/MiniBulletChart.tsx` (full file read) — props, CI whisker rendering, zone fill, neutral fill.
- `frontend/src/components/insights/BulletConfidencePopover.tsx` + `EvalConfidenceTooltip.tsx` (full file read) — props, render shape.
- `frontend/src/components/insights/ScoreConfidencePopover.tsx` + `WdlConfidenceTooltip.tsx` (full file read) — props, render shape.
- `frontend/src/lib/scoreBulletConfig.ts` (full file read) — `SCORE_BULLET_CENTER`, `SCORE_BULLET_NEUTRAL_MIN/MAX`, `SCORE_BULLET_DOMAIN`, `clampScoreCi`, `scoreZoneColor`.
- `frontend/src/lib/openingStatsZones.ts` (full file read) — `EVAL_NEUTRAL_MIN/MAX_PAWNS`, `EVAL_BULLET_DOMAIN_PAWNS`, `evalZoneColor`.
- `frontend/src/lib/significance.ts` (full file read) — `isConfident(level)` gate.
- `frontend/src/lib/theme.ts` (line refs verified) — `ZONE_SUCCESS`, `ZONE_DANGER`, `ZONE_NEUTRAL`, `MIN_GAMES_FOR_RELIABLE_STATS = 10`, `UNRELIABLE_OPACITY = 0.5`.
- `frontend/src/pages/openings/ExplorerTab.tsx` (lines 1-225) — canonical inline-row-+-bullet layout; verified line numbers.
- `frontend/src/pages/Endgames.tsx` (lines 1-403) — section insertion point and existing accordion structure.
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` (lines 1-260) — surrounding visual style for the new section to match.
- `frontend/src/types/endgames.ts` (lines 1-90, 180+) — TypeScript mirror target.
- `tests/services/test_eval_confidence.py` (lines 1-100) — pattern for new aggregation tests.

### Secondary (MEDIUM confidence)
- `reports/benchmarks-2026-05-04.md` §3c — EG-entry pooled `[p05, p95] = [−182.9, +197.0]` cp → ±2.0 pawn axis confirmed; `[p25, p75] = [-53.8, +75.3]` cp → ±0.75 pawn neutral band recommended. Per-game SD ≈ 4.18 pawns at endgame entry confirmed.
- `.planning/phases/81-.../81-CONTEXT.md` — locked decisions D-01..D-21.
- `.planning/notes/endgame-entry-eval-tile-design.md` — population baseline, sample-size table, "we can't tell" framing (partly obsolete; tile-anatomy "stats line" rescinded).
- `.planning/ROADMAP.md` lines 80-86 — phase scope.

### Tertiary (LOW confidence)
- None — every claim above traces to a verified file or report.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dependency already installed and locked at known versions.
- Architecture (data flow / file targets): HIGH — file paths and line numbers verified by file reads.
- Pitfalls: HIGH — pitfalls 1, 2, 3 grounded in explicit code patterns from `endgame_service.py`; 4-8 grounded in CLAUDE.md and existing test fixtures.
- Validation architecture: HIGH — existing test files (`test_eval_confidence.py`, `test_score_confidence.py`, `test_endgame_service.py`, `MiniBulletChart.test.tsx`) confirm framework and conventions.
- Visual / axis defaults: MEDIUM — D-15 and D-16 are locked; the EG-entry neutral band recommendation (±0.75) is benchmark-cited but not yet locked by the user (Claude's discretion under D-15).

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (30 days; the codebase is stable, only changing with the v1.x feature pipeline. No upstream library churn risks affect this phase.)
