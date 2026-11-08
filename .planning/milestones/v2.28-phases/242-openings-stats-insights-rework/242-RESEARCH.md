# Phase 242: Openings Stats + Insights Rework (SEED-204) - Research

**Researched:** 2026-10-17
**Domain:** FastAPI/SQLAlchemy opening aggregates (eval z-test, dedupe, recency cutoff, weekly series) + React/TanStack Openings Stats page rebuild
**Confidence:** HIGH (all claims below were read from the codebase or measured on the dev DB this session, except the items in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (summary only, read SEED-204 for the full list)
- **D-00:** All SEED-204 "Locked decisions" apply verbatim: Insights merged into Stats (subtab + mobile tab +
  route removed), one sticky colour switch (not persisted), 99% findings gate with top 5 per section,
  finding-card layout, repertoire table columns (Opening · Games · Results · Score · Eval after opening),
  rows <20 games faded and never coloured, duplicate-row collapse, expanded row contents, `ScoreChart` reuse
  with optional weekly volume bars, multi-line bookmark chart dropped, eval centred on the colour baseline
  (Openings tab only: Moves, Games, Stats; Endgames `evalContext="endgame-entry"` unchanged), popover
  footers with 99% CI + p + reference + n, no ECO codes, no "pawns" unit, "After the opening" dropped.
  The 238/239 system decisions D-14..D-17 apply unchanged.
- **D-00b:** Score band stays the shared ±5% (45–55%, today's `SCORE_BULLET_NEUTRAL_*`). Benchmark §2 pooled
  IQR [46.1%, 57.3%] confirms keeping it; no re-derivation in this phase.

#### Current vs past repertoire cutoff
- **D-01:** An opening is **current** when it was last played within the user's last 200 games of that colour
  **OR** within the last 60 days, whichever reaches further back. Everything else is "past".
  Rationale (prod check 2026-10-17, 1,276 user×colour pairs): with a pure 200-game rule, users with
  1000+ games per colour get a window of only ~61–68 days median and ~15–17 days at p10, so an opening
  last played 3 weeks ago would be "past". The 60-day floor fixes that and leaves light users unchanged
  (<200 games per colour = everything current; 466 of 1,276 pairs).
- **D-02:** The cutoff is computed **under the active sidebar filters** (TC, platform, rated, opponent type,
  recency, etc. via `apply_game_filters()`), per colour. "Current" stays consistent with the rows shown.
- **D-03:** Constants, not magic numbers: e.g. `CURRENT_REPERTOIRE_RECENT_GAMES = 200`,
  `CURRENT_REPERTOIRE_MIN_DAYS = 60`. The day floor anchors on `now_utc` from the `dev_now_utc` dependency
  (`app/core/dev_clock.py`), never `datetime.now()`.
- **D-04:** The cutoff drives all three SEED-204 uses: most-played rows → "Played before (n)" group; stale
  bookmarks stay pinned with a "not played recently" chip; findings from older games get an "older games"
  chip and sort after current ones. Backend returns the cutoff date (or a per-row `is_current` flag; planner
  picks) so the frontend does not re-derive it.

#### Most-played row count
- **D-05:** Per colour, show **up to 10 current rows** in the main table and **up to 10 past rows** in the
  collapsed "Played before (n)" group. The backend fetches enough candidates before dedupe and the split
  (order of 30 per colour; planner/researcher sizes it) so past openings never push current ones out.
  Replaces the single `TOP_OPENINGS_LIMIT = 10` (`app/services/stats_service.py:41`) with named limits for
  current/past plus a fetch limit.
- **D-06:** Order of operations: fetch → dedupe (identical game sets keep the deeper line; most-played rows
  duplicating a same-colour bookmark position are dropped, bookmark wins) → split current/past → cap each
  at 10. Bookmarks are never capped and never dropped.
- **D-07:** Minimum game count for a most-played row is unchanged (`MIN_GAMES_FOR_OPENING = 1`). The faded
  <20-games styling carries the low-sample signal, in both the current table and "Played before".

#### Findings density
- **D-08:** Phone shows **2 finding cards per section**, then a "Show more" control expanding to the 5-card
  cap. Desktop/tablet shows all 5 (2-column grid). "Show more" needs a testid and an Umami event
  (frontend/CLAUDE.md).
- **D-09:** The faded "Not clear yet (n)" list holds **only medium-confidence candidates (p < 0.05, not at
  99%)**. Low-confidence rows are dropped as noise (D-17). The header count `n` is the full count of medium
  candidates for that section.
- **D-10:** "Not clear yet" shows at most **10 rows**, sorted by strongest p first (lowest p), with current
  findings before "older games" ones (same rule as the cards). No colour, faded, collapsed by default.
- **D-11:** The empty-state copy ("Nothing clear yet as Black. 3 moves lean this way…") counts the same
  medium-confidence candidates as D-09.

### Claude's Discretion
(defaults accepted by owner, 2026-10-17)
- **D-12:** Plan split: backend wave first (eval baseline centring + z-test, dedupe, current/past cutoff,
  row limits, weekly game counts per time series), then frontend plans. Planner decides plan granularity.
- **D-13:** The baseline-centred eval z-test ships in this phase for **all Openings call sites**, including
  the Moves tab (`openings_service.py:190`), alongside `stats_service.py` (most-played + bookmark phase-entry
  metrics) and `opening_insights_service.py:407`. `endgame_service.py` stays untouched. Update the "H0 = 0 cp,
  baseline is only a tick" comments (`stats_service.py` ~line 425, `opening_insights_constants.py`,
  `app/schemas/stats.py:89`).
- **D-14:** `ScoreChart`'s multi-bookmark mode is **retired**: `pages/openings/StatsTab.tsx` is its only
  caller. It becomes a single-opening chart with the optional weekly volume series.
- **D-15:** `/openings/insights` and any insights deep links (`useDeepLinkHighlight`, `useTabReset`,
  `useOpeningsHandlers`) **redirect to `/openings/stats`** (not a 404).
- Exact copy for chips, "Show more" and "Played before (n)" follows sketch 012 and the popover-minimalism
  rule; planner/UI phase may tune wording.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Reviewed todos from `todo.match-phase` were keyword-only
matches unrelated to this phase and were not folded.)
</user_constraints>

<phase_requirements>
## Phase Requirements (coverage contract = CONTEXT D-00..D-15)

| ID | Description | Research Support |
|----|-------------|------------------|
| D-00 (eval centring) | Eval verdict/z-test/bar centred on colour baseline, Openings only | §Pattern B1 (4 call sites + 1 shared helper), §Pattern F4 (MiniBulletChart `center` prop for Moves/Games), Pitfall 1 (endgame isolation) |
| D-00 (merge Insights) | Insights subtab, mobile tab and route removed | §Pattern F1 (exact Openings.tsx lines, redirect hook-in at `needsLegacyRedirect`) |
| D-00 (sticky switch) | One sticky White/Black switch, table header sticks under it | §Pattern F2 (`StickyTcBar` + existing mobile sticky Filters row), Pitfall 6 (overflow-hidden kills sticky) |
| D-00 (99% gate, cards) | Findings top 5 at confidence "high" | §Pattern B5 (backend partition before eval enrichment), §Pattern F5 |
| D-00 (table) | Opening · Games · Results · Score · Eval; <20 faded, never coloured | §Pattern F3 (TypeTable/RangeCell analog, `MiniWDLBar`, `computeScoreConfidence`) |
| D-00 (popover footers) | 99% CI + p + reference + n | §Pattern B1 (backend 99% CIs via `VERDICT_CI_Z_99`), §Code Examples |
| D-00 (ScoreChart + volume) | Per-opening chart with weekly grey bars | §Pattern B6 (weekly bucketing + `per_week_games`), §Pattern F6 |
| D-00b | Score band ±5% | `SCORE_BULLET_NEUTRAL_MIN/MAX` quoted below; no change |
| D-01..D-04 | Current/past cutoff (200 games OR 60 days, under filters, `dev_now_utc`) | §Pattern B2 (SQL measured 2.9 ms on a 33k-game colour), response shape recommendation |
| D-05..D-07 | 10 current + 10 past, fetch before dedupe, MIN_GAMES_FOR_OPENING = 1 | §Pattern B3 (fetch 60; dev evidence: owner's 10th current White row is rank 33; cutoff-restricted second fetch when current rows run short, D-05 clarified) |
| D-06 (dedupe) | Identical game sets keep deeper line; bookmark twin dropped | §Pattern B4 (game-id fingerprint + ply_count; bookmark full_hash via `compute_hashes`), Open Question 1 (chart-excluded bookmarks) |
| D-08 | Phone 2 cards + "Show more" (testid + Umami) | §Pattern F7 (reuse `opening-insights-more` panel target) |
| D-09..D-11 | "Not clear yet" = medium only, ≤10, p-asc, current first; full medium count | §Pattern B5 (counts computed pre-cap, cheap) |
| D-12 | Backend wave first | §Recommended plan split |
| D-13 | Centring at all 4 Openings call sites, comments updated | §Pattern B1 file:line list |
| D-14 | ScoreChart multi-bookmark mode retired | §Pattern F6 (only caller `StatsTab.tsx:237`) |
| D-15 | `/openings/insights` redirects to `/openings/stats` | §Pattern F1 |
</phase_requirements>

## Summary

The backend work is small and well-contained. All four Openings eval call sites duplicate the same ~12-line
finalizer around `compute_eval_confidence_bucket` (stats_service most-played and bookmark, openings_service
Moves, opening_insights_service). The helper already takes `baseline_cp` (unused today), so centring is one
argument. Recommend folding the four copies into one Openings-only helper that resolves the colour baseline,
passes `baseline_cp`, and also returns 99% CI bounds. `endgame_service.py:747` calls the primitive directly and
is left alone. The current/past cutoff is one `ORDER BY played_at DESC OFFSET 199 LIMIT 1` query on the existing
`ix_games_user_played_at` index (2.9 ms measured on a 33k-game colour on dev), then `min(nth, now_utc − 60 d)`.

The most-played pipeline needs reordering more than new SQL. Today it fetches 10 rows and runs the expensive
phase-entry (eval) query on all of them. The new order is: fetch about 60 candidates, run the cheap
position-WDL batch on them (with a game-set fingerprint added), dedupe, split current/past, cap 10+10, and only
then run phase-entry on the ≤20 survivors. On dev the owner's White repertoire has its 10th *current* row at
rank 33 of the most-played list, so the "order of 30" in D-05 is too small. Use 60: the top-openings query
costs the same at any limit (0.45 to 1.8 s, noisy), and the WDL batch goes from about 0.1 s to about 0.2 s.

The frontend is the larger wave. It deletes the Insights tab and route and the 4-section bookmark/most-played
layout (`OpeningStatsSection`, `OpeningStatsCard`, `OpeningFindingCard`, `OpeningInsightsBlock`, `InsightsTab`)
and the multi-line `ScoreChart`. It then builds one colour-switched page: findings above a repertoire table. The
closest prior art is Phase 238's `TypeTable`/`RangeCell` (a table cell with a grey band and a verdict dot) and
the shared `StickyTcBar`. `GapBar` is library-specific ("fewer flaws", lower is better), so reuse its pure math
(`gapPosition`, `bandRange`) rather than the component.

**Primary recommendation:** Build the backend wave in three plans: (1) shared baseline-centred eval finalizer +
99% CIs, (2) cutoff + most-played reorder/dedupe/split + bookmark twin drop, (3) insights partition + weekly
time series. Then build the frontend wave: route/tab removal, sticky switch + repertoire table, finding cards,
expanded row + chart. Keep `MostPlayedOpeningsResponse.white/black` as flat lists (current first, then past)
with a per-row `is_current` and per-colour cutoff, so `SuggestionsModal` keeps working unchanged.

## Project Constraints (from CLAUDE.md)

- Routers are HTTP-only; business logic in services; SQL only in repositories. `APIRouter(prefix=...)` with relative paths.
- `apply_game_filters()` (`app/repositories/query_utils.py:169`) is the single filter implementation; the cutoff query must use it.
- Time-dependent endpoints take `now_utc` from `dev_now_utc` (`app/core/dev_clock.py:56`), never `datetime.now()` inline.
- Never `asyncio.gather` on one `AsyncSession`; sequential awaits (existing test `test_no_asyncio_gather_in_stats_service` enforces it for stats_service).
- No magic numbers; `Literal[...]` instead of bare `str`; explicit return types; `ty check` zero errors; `# ty: ignore[rule]` only.
- Nesting depth ≤ 4 (gated: `scripts/check_function_size.py` backend, eslint `max-depth` frontend); ~100 logic lines / cognitive complexity 15 soft.
- Sentry: `capture_exception` in non-trivial except blocks in services/routers; no variables in error messages.
- Frontend: theme colours from `lib/theme.ts`; `noUncheckedIndexedAccess`; `text-sm` floor (popover bodies may use `text-xs`); `data-testid` on every interactive element; semantic HTML; ARIA on icon buttons; knip in CI (remove dead exports); `npm run build` (tsc) before integrating type changes; apply every change to mobile too.
- Umami: every new user-facing control ships its `trackFeature` event via the typed registry; never on mount/restore; never interpolate SAN/name/FEN into an `InfoPopover` testId; URL-routed tabs need no event; never rename an existing event/target.
- Error branches: every `useQuery` data chain needs an `isError` branch ("Failed to load ...").
- Pre-merge gate (full list in CLAUDE.md) runs once before the squash-merge to `main`; CHANGELOG `[Unreleased]` entry required.
- GSD: no unplanned scope; flag rather than implement out-of-plan items.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Eval z-test centred on colour baseline | API / Backend (services) | — | p-value + confidence bucket are computed server-side today; frontend only reads `eval_confidence` |
| 99% CIs for popover footers | API / Backend | Browser (formatting) | `VERDICT_CI_Z_99` already lives in `score_confidence.py:69`; 238/239 compute 99% CIs server-side |
| Current/past cutoff | Database (indexed query) + API | Browser (bookmark chip compares against returned cutoff) | Must respect `apply_game_filters` and `dev_now_utc` (D-02/D-03) |
| Most-played dedupe + bookmark twin drop + split/cap | API / Backend | — | Must happen before the cap (D-06); the frontend only ever sees capped lists |
| Findings 99% gate / top-5 / medium count | API / Backend | Browser (phone 2-card "Show more") | Full medium count `n` (D-09) is only available pre-cap |
| Weekly game counts per series | API / Backend | — | Same pattern as `endgame_service.py:1222-1254` |
| Colour switch, table, expanded row, chart | Browser / Client | — | Pure presentation over the API payloads |
| `/openings/insights` redirect | Browser (react-router `<Navigate>`) | — | Route is client-side (`App.tsx:1070` `path="/openings/*"`) |

## Standard Stack

No new libraries. Everything is in the existing stack. [VERIFIED: frontend/package.json, pyproject via `uv run python --version`]

| Library | Version (installed) | Purpose in this phase |
|---------|---------|---------|
| FastAPI / SQLAlchemy 2 async / asyncpg | per lockfile | cutoff query, aggregate changes |
| python-chess (`app/services/zobrist.compute_hashes`) | 1.11.x | bookmark full_hash from replayed moves |
| React 19.2 / react-router 8.3 / TanStack Query 5.100 | `^19.2.8` / `^8.3.0` / `^5.100.14` | page rebuild, redirect, lazy per-row series |
| recharts 3.8 | `^3.8.1` | `ScoreChart` → `ComposedChart` with `Bar` on a hidden second Y axis (pattern in `EndgameScoreOverTimeChart.tsx:170-291`) |
| vitest 5 | `^5.0.0` | frontend tests |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages (backend or frontend).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Sidebar filters (TC, platform, rated, opp type, recency, strength)  +  X-Dev-Clock-Offset header
        │                                   │
        ▼                                   ▼
 GET /stats/most-played-openings      POST /insights/openings        POST /openings/time-series
        │  now_utc ← dev_now_utc            │ now_utc ← dev_now_utc         │ (bookmarks + lazily one
        ▼                                   ▼                               │  row on expand)
 ┌──────────────────────────┐   ┌───────────────────────────────┐          ▼
 │ cutoff(color) per colour │◄──┤ same cutoff helper            │   weekly bucketing:
 │ nth=200 OFFSET query     │   │                               │   last rolling-50 score per ISO
 │ cutoff=min(nth, now-60d) │   │ transitions → classify →      │   week + per_week_games
 │ (None if <200 games)     │   │ dedupe → rank (Wilson)        │          │
 └────────────┬─────────────┘   │ partition: high / medium / ✗  │          │
              ▼                 │ sort current-first; cap 5/10  │          │
 top openings (limit 60)        │ medium_count = len(all medium)│          │
              ▼                 │ eval enrich ONLY survivors    │          │
 position WDL batch (+fingerprint, last_played_at)              │          │
              ▼                 └───────────────┬───────────────┘          │
 dedupe identical sets (keep deeper ply)        │                          │
 drop same-colour bookmark twins (bookmarks     │                          │
   loaded server-side, full_hash via replay)    │                          │
              ▼                                 │                          │
 split is_current → cap 10 current / 10 past    │                          │
              ▼                                 │                          │
 phase-entry eval batch on ≤20 survivors        │                          │
   → shared centred finalizer (H0 = baseline,   │                          │
     95% + 99% CI)                              │                          │
              ▼                                 ▼                          ▼
 ┌───────────────────────────── Openings Stats page (one colour at a time) ─────────────┐
 │ sticky [White | Black] (+ mobile Filters)                                             │
 │ "Moves that cost you" / "Moves that work": ≤5 cards (phone 2 + Show more),            │
 │      "Not clear yet (n)" collapsed list, empty-state copy                             │
 │ Repertoire table: Bookmarks (pinned, chip if stale) → Most played (current) →         │
 │      "Played before (n)" (past, collapsed); row expand → 200px board, links,          │
 │      Score bar, Eval bar (centred on baseline, faint 0 tick), ScoreChart + volume     │
 └───────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended plan split (D-12)

| Wave | Plan | Contents |
|------|------|----------|
| 1 | 242-01 backend eval | Shared Openings eval finalizer (centred H0 + 99% CI), wire 4 call sites, docstring/comment updates, schema fields for 99% CI |
| 1 | 242-02 backend repertoire | Cutoff helper + repository query, `dev_now_utc` on both routers, most-played reorder (fetch 60 → dedupe → bookmark twin drop → split → cap → eval), response shape |
| 1 | 242-03 backend insights + series | Insights partition (high ≤5, medium ≤10 + count, current-first), cutoff on findings, weekly time series + `per_week_games` |
| 2 | 242-04 frontend shell | Remove Insights tab/route (desktop + mobile), redirect, union types, sticky colour switch + Umami, data hooks/types |
| 2 | 242-05 frontend repertoire table | Table rows, verdict cells, popovers, fade, "Played before", bookmark chip, phone stack |
| 2/3 | 242-06 frontend findings + expanded row | Finding cards, "Not clear yet", empty state, expanded row (board, links, Score/Eval bars), single-opening `ScoreChart` + volume; Moves/Games `PositionResultsPanel` re-centring; delete dead components/tests; knip |

Plans 242-01..03 touch disjoint functions but share `stats_service.py`/`opening_insights_service.py`. Sequence 01 → 02 → 03, or run 01 and 03 in parallel only if 03 rebases on 01's finalizer.

---

### Pattern B1: One baseline-centred Openings eval finalizer (D-00, D-13)

**Call sites (all read this session):**

| File:line | Context | Colour source |
|-----------|---------|---------------|
| `app/services/stats_service.py:424-439` | most-played `rows_to_openings` | `color="white"/"black"` per call (lines 345-387) |
| `app/services/stats_service.py:502-514` | `_bookmark_phase_entry_item` | `BookmarkPhaseEntryQuery.color: Literal["white","black"] \| None` (`app/schemas/stats.py:118`). Not threaded into the helper today; must be passed |
| `app/services/openings_service.py:186-201` | Moves/Games `analyze()` | `request.color: Literal["white","black"] \| None` (`app/schemas/openings.py:41`) |
| `app/services/opening_insights_service.py:394-422` | `_apply_eval_metrics_to_finding` | `finding.color: Literal["white","black"]` |
| `app/services/endgame_service.py:747` | **DO NOT TOUCH**: endgame-entry eval | n/a |

**Primitive** (`app/services/eval_confidence.py:53-55`), verbatim:
```python
def compute_eval_confidence_bucket(
    eval_sum: float, eval_sumsq: float, n: int, baseline_cp: float = 0.0
) -> tuple[Literal["low", "medium", "high"], float, float, float]:
```
`baseline_cp` is in **centipawns**. The test is `z = (mean - baseline_cp) / se` (line 119), and the CI is centred on
the observed mean (`ci_half_width = CI_Z_95 * se`, line 126). [VERIFIED: app/services/eval_confidence.py:53-139]

**Baselines** are in **pawns** (`app/services/opening_insights_constants.py:85-86`), verbatim:
```python
EVAL_BASELINE_PAWNS_WHITE: float = 0.25
EVAL_BASELINE_PAWNS_BLACK: float = -0.25
```
[VERIFIED: app/services/opening_insights_constants.py:85-86]

**99% z** (`app/services/score_confidence.py:69`), verbatim: `VERDICT_CI_Z_99: float = 2.5758293035489`
[VERIFIED: app/services/score_confidence.py:65-69]

**Recommendation:**
- New module (e.g. `app/services/opening_eval.py`) with `resolve_eval_baseline_pawns(color: Literal["white","black"] | None) -> float`.
  Black → BLACK, otherwise WHITE. This matches the existing display convention: `openings_service.py:206-208` and the
  frontend `(b.color ?? 'white')` in `useOpeningsChartData.ts:133`. Add a named `CENTIPAWNS_PER_PAWN = 100`
  (the codebase uses bare `/ 100.0` with "cp -> pawns" comments; no such constant exists today, verified by grep).
- `finalize_opening_eval(pe: OpeningPhaseEntryMetrics, color) -> OpeningEvalFields` (TypedDict or small dataclass):
  calls the primitive with `baseline_cp=resolve_eval_baseline_pawns(color) * CENTIPAWNS_PER_PAWN` and returns
  `avg_eval_pawns` (raw, uncentred, labels keep the raw eval per SEED-204), the 95% bounds (keep them for the Moves
  `MiniBulletChart` whiskers), new 99% bounds, `eval_n`, `eval_p_value`, `eval_confidence`.
- Derive the 99% bounds in the finalizer from the returned 95% half-width:
  `ci99_half = ci_half * VERDICT_CI_Z_99 / OPENING_INSIGHTS_CI_Z_95` (same `se`, no second call). This leaves the
  primitive's 4-tuple signature and the endgame call untouched.
- Add `eval_ci99_low_pawns` / `eval_ci99_high_pawns: float | None = None` to `OpeningWDL`
  (`app/schemas/stats.py:66-71`), `BookmarkPhaseEntryItem` (`:105-110`), `WDLStats` (`app/schemas/openings.py:89-94`),
  `OpeningInsightFinding` (`app/schemas/opening_insights.py:96-101`) and the TS mirrors.
- Rewrite the docstrings/comments that say H0 = 0 cp: `eval_confidence.py:15-22, 62-67`;
  `opening_insights_constants.py:70-84`; `stats_service.py:425-427, 475-478, 494-496`; `schemas/stats.py:84-89`;
  `schemas/opening_insights.py:124-126`; `openings_service.py:187-189`;
  `opening_insights_service.py:399-401`; `schemas/openings.py:127-130` (still true); `OpeningWDL.eval_p_value` comment
  "two-sided p-value vs zero" (`schemas/stats.py:70`). Keep `eval_confidence.py:38` "Callers" and note that endgame still uses 0.

**Score side (rows):** `OpeningWDL` has no score p/CI today. The frontend `lib/scoreConfidence.ts` ports the
backend Wilson test (95% only). For the popover footer "99% CI … vs 50%", add backend
`score_p_value` + `score_ci99_low/high` to `OpeningWDL` via `compute_confidence_bucket` + `wilson_bounds(p, n,
z=VERDICT_CI_Z_99)`, consistent with 238/239 (server-side 99%). Bookmark rows get WDL from the time series, so either add
the same fields to `BookmarkTimeSeries` or compute client-side via an extended `computeScoreConfidence` with a z
parameter. Recommend the server-side fields on the time series too (one source of truth). Findings already
carry `p_value`. Add `ci99_low/high` there.

### Pattern B2: Current/past cutoff (D-01..D-04)

```sql
-- measured on dev (user 7, 33,580 White games): Index Scan ix_games_user_played_at, 2.914 ms
SELECT played_at FROM games
WHERE user_id = :uid AND user_color = :color AND played_at IS NOT NULL  -- + apply_game_filters(...)
ORDER BY played_at DESC OFFSET 199 LIMIT 1;
```
[VERIFIED: EXPLAIN ANALYZE on dev DB this session; index `ix_games_user_played_at` = `Index("ix_games_user_played_at", "user_id", sa.text("played_at DESC"))` at app/models/game.py:60]

- Repository: `query_nth_recent_played_at(session, user_id, color, n, *, time_control, platform, rated, opponent_type, from_date, to_date, opponent_gap_min, opponent_gap_max) -> datetime | None` in `stats_repository.py`, built with `select(Game.played_at)…` + `apply_game_filters(...)` + `.order_by(Game.played_at.desc()).offset(n - 1).limit(1)`. `apply_game_filters` already takes `color` (`query_utils.py:177`).
- Service helper (shared by stats + insights; put it in a neutral module such as `app/services/repertoire_recency.py` to avoid stats↔insights imports): `cutoff = None if nth is None else min(nth, now_utc - timedelta(days=CURRENT_REPERTOIRE_MIN_DAYS))`. `None` means fewer than 200 games under the filters, so everything is current (D-01: light users unchanged).
- `is_current(last_played_at, cutoff) = cutoff is None or last_played_at is None or last_played_at >= cutoff`. A `None` last_played_at counts as current, as in the sketch's `isCurrent = x => !x.lp || x.lp >= CUTOFF[x.c]`.
- Routers: add `now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)]` to `GET /stats/most-played-openings` (`app/routers/stats.py:87`) and `POST /insights/openings` (`app/routers/insights.py:107`); pattern as `app/routers/train.py:65` (`NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]`). The frontend `api/client.ts` already sends the dev-clock header globally.
- Response: return both the per-colour cutoff (`current_cutoff_white/black: datetime | None`) and per-row/per-finding `is_current: bool`. The frontend needs the cutoff for **bookmarks** (their `last_played_at` comes from `/openings/time-series`). Comparing against a returned cutoff is not re-deriving it (D-04).
- Cost: two queries per endpoint (one per colour), ~3 ms each on the heaviest dev user. A selective filter (e.g. classical-only for a bullet player) can scan most of the user's index range, still tens of ms. [ASSUMED for the selective-filter worst case; only the default-filter case was measured]

### Pattern B3: Most-played reorder (D-05..D-07)

Today (`stats_service.py:280-387`): top query limit 10 → position-WDL batch → phase-entry batch (the expensive
one) on all rows, per colour, sequential.

**Dev evidence for the fetch size** (current/past split under D-01, default filters, dev snapshot):

| user | colour | cutoff | current in top 60 | rank of 10th current row |
|------|--------|--------|-------------------|--------------------------|
| 28 (owner) | white | 2026-02-14 | 12 | **33** |
| 28 (owner) | black | 2026-02-13 | 36 | 11 |
| 47 | black | 2026-03-23 | 24 | 13 |
| 7, 14, 8, 46, 31, 2, 13 | both | — | 25-54 | 10-11 |

[VERIFIED: dev DB probe `temp/phase242-research/current_split.py`, this session]

**Timing (dev user 7, 33k White games):** top query 0.45-1.8 s regardless of limit (the GROUP BY sorts all groups);
position-WDL batch 0.08 s @10 → 0.14-0.22 s @60; phase-entry batch @20 hashes 0.53-1.04 s. Measurements were noisy
(memory: dev wall clock drifts run to run). [VERIFIED: `temp/phase242-research/time_fetch.py`, this session]

**Recommendation:** `MOST_PLAYED_FETCH_LIMIT = 60`, `MOST_PLAYED_CURRENT_LIMIT = 10`, `MOST_PLAYED_PAST_LIMIT = 10`
(replace `TOP_OPENINGS_LIMIT = 10`, verbatim at `stats_service.py:41`). Pipeline per colour:
1. `query_top_openings_sql_wdl(limit=MOST_PLAYED_FETCH_LIMIT)`
2. `query_position_wdl_batch` on all 60 (cheap; extend with the fingerprint, Pattern B4)
3. dedupe identical sets → drop bookmark twins
4. split by `is_current`, sort each by `total` desc, cap 10/10
5. `query_opening_phase_entry_metrics_batch` on the ≤20 survivors only (cheaper than today's per-row eval on 10 when you count the dedupe benefit; eval is not needed for the dedupe if the game-set fingerprint is exact)

Residual risk: a user who switched repertoire recently could have fewer than 10 current rows in the top 60.
**Built (owner, "D-05 (clarified)" in 242-CONTEXT.md; plan 242-01 Task 3):** when a cutoff exists and fewer than 10
current rows survive dedupe and the twin drop, a second top query restricted to
`from_date = max(from_date, cutoff.date())` nominates extra rows. It only nominates: the nominees' WDL,
`last_played_at`, fingerprint and `is_current` come from `query_position_wdl_batch` under the unrestricted filters,
so merged rows show their full counts, then dedupe, twin drop and the 10/10 split run on the merged set. No second
query when the cutoff is `None`.

Keep `MIN_GAMES_FOR_OPENING = 1` (verbatim `stats_service.py:38`), `MIN_PLY_WHITE = 3`, `MIN_PLY_BLACK = 3`
(`:48-49`). Keep the sequential awaits.

**Response shape:** keep `white: list[OpeningWDL]`, `black: list[OpeningWDL]` as **current rows first, then past
rows**, each with `is_current: bool`. `SuggestionsModal.tsx:46-64` slices `mostPlayedData.white` /
`.black` by `SUGGESTIONS_POOL_SIZE`, so current-first ordering keeps suggestions sensible with zero changes there.
Update the docstring "Return top 10 most played openings per color" (`stats_service.py:270`, `routers/stats.py:100`).

### Pattern B4: Dedupe (D-06)

**Owner dev data confirms the two duplicate shapes the seed names** (exact game-id sets computed in Python):
- Black: `vs. Caro-Kann Defense: Advance Variation (1. e4 c6 2. d4 d5 3. e5)` and `Caro-Kann Defense: Advance Variation, Botvinnik-Carls Defense (… 3. e5 c5)`, identical set n=172.
- White: `King's Indian Defense (1. d4 Nf6 2. c4 g6 3. Nc3)` and `vs. Indian Defense: West Indian Defense (1. d4 Nf6 2. c4 g6)`, identical set n=37.
- In both cases the (total, W, D, L, last_played_at, eval_n, eval_sum) tuple also matched, with no false positives among 60 rows.
[VERIFIED: `temp/phase242-research/dups.py` on dev user 28, this session]

**Recommendation (exact and cheap):** add a game-set fingerprint to `query_position_wdl_batch`
(`stats_repository.py:457-474`): `func.sum(func.distinct(Game.id))` (and optionally
`func.bit_xor(func.distinct(Game.id))`; PostgreSQL 14+ has `bit_xor`, dev runs postgres:18). Two rows are
duplicates iff `(total, id_sum[, id_xor])` match. The positions are nested along one line, so equal count plus equal
id sum is effectively exact. Keep the **deeper line**: return `_openings_dedup.c.ply_count` from
`query_top_openings_sql_wdl` (it is already in the GROUP BY at `stats_repository.py:378` but not selected). Tie-break
by name. The row tuple is index-accessed today (`row[5]` = full_hash, comment at `stats_service.py:327-328`;
destructuring at `:395`), so switch to named attribute access (`row.full_hash`) when adding a column.

**Bookmark twin:** load `position_bookmark_repository.get_bookmarks(session, user_id)` (`:21`) in the service. For
each bookmark with a colour, replay `json.loads(bookmark.moves)` on `chess.Board()` and take `compute_hashes(board)[2]`
(full hash). This is the same approach as `update_match_side` (`position_bookmark_repository.py:277-321`), which
replays because "old bookmarks may have board-only FENs ... which produce wrong full_hash values". Drop most-played
rows whose `(color, full_hash)` is in that set, independent of the bookmark's `match_side`
(`BookmarkMatchSide = Literal["mine", "opponent", "both", "full"]`, `app/schemas/position_bookmarks.py:11`).
Bookmarks with `color = None` (`app/models/position_bookmark.py:23`) never appear in a colour table, so skip them.

**Cache coherence:** the most-played response now depends on bookmarks. `useCreatePositionBookmark` /
`useDeletePositionBookmark` (`hooks/usePositionBookmarks.ts:12-52`) invalidate only `['position-bookmarks']`; add
`['mostPlayedOpenings']`. SuggestionsModal's own save path must do the same (it imports `useQueryClient`; check its
invalidation when editing).

### Pattern B5: Insights partition (D-00 gate, D-08..D-11)

Today `_build_sections` (`opening_insights_service.py:839-965`) runs classify → attribute → dedupe within section →
global continuation dedupe → Wilson rank → **cap 10 regardless of confidence** (`WEAKNESS_CAP_PER_COLOR: int = 10`,
`STRENGTH_CAP_PER_COLOR: int = 10`, `:61-62`) → eval enrichment of survivors.

**Dev evidence (uncapped):** owner: white strengths 4 high / 4 medium / 10 low; black weaknesses 1 medium / 7 low; no
high weakness (matches the seed's "no cost-you finding at 99%"). Heavy user 7: 529 high White strengths. Uncapped eval
enrichment took 10.6 s for user 7 vs 2.3 s for the owner, **so caps must stay before eval enrichment.**
[VERIFIED: `temp/phase242-research/insights_conf.py`, this session]

**Recommendation:** after `_rank_section`, per section:
- `high = [f for f in ranked if f.confidence == "high"]`; stable-sort current-first; cap `FINDINGS_CARD_CAP = 5`.
- `medium = [f for f in ranked if f.confidence == "medium"]`; `medium_count = len(medium)` **before** capping
  (D-09/D-11); sort by `(not is_current, p_value)`; cap `FINDINGS_NOT_CLEAR_CAP = 10`.
- drop `low` (D-17 "show less rather than noise").
- enrich eval only for `high + medium` survivors (≤ 15 per section, ≤ 60 hashes total vs 40 today).

The confidence buckets are `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.01` and
`OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.05` (`opening_insights_constants.py:53-54`); the 99% gate is
exactly `confidence == "high"`. [VERIFIED: opening_insights_constants.py:52-54]

**Response shape (recommendation):** keep the four lists as the card lists (≤5), add four `*_not_clear` lists
(≤10), four `*_not_clear_count: int`, `current_cutoff_white/black`, and `is_current` on `OpeningInsightFinding`.
`OpeningInsightsRequest` has `extra="forbid"` (`schemas/opening_insights.py:26`), so it only affects request fields.
Keep `color: Literal["all","white","black"] = "all"`: the switch flips instantly between colours from one response.
Delete or rename `WEAKNESS_CAP_PER_COLOR`/`STRENGTH_CAP_PER_COLOR`; `tests/services/test_opening_insights_service.py:30-31` imports them.

Note: `_rank_section` ranks by the Wilson bound, not p. Cards keep the Wilson order (current first). Only "Not clear yet" sorts by p (D-10).

### Pattern B6: Weekly time series with volume (D-00 ScoreChart + volume)

Today `_build_bookmark_time_series` (`openings_service.py:283-345`) emits **one point per calendar date** (last game of
the date, rolling `ROLLING_WINDOW_SIZE = 50`, drop points with `game_count < MIN_GAMES_FOR_TIMELINE = 10`; `:51,55`).
Weekly bars do not fit a per-date ordinal axis (several date ticks per week would repeat one weekly count).

**Recommendation:** switch emission to ISO-week buckets keyed by the Monday date, exactly as
`endgame_service.py:1222-1254` does (`iso_year, iso_week, iso_weekday = played_at.isocalendar()`;
`monday = (played_at - timedelta(days=iso_weekday - 1)).date()`), keep the last rolling value of the week, and add
`per_week_games: int` (in-window games that week) to `TimeSeriesPoint` (`schemas/openings.py:190-196`) and the TS
type (`types/position_bookmarks.ts:60-65`). The sketch's chart is also weekly ("ordinal axis over active weeks
only"). The only consumer is `ScoreChart` (`StatsTab.tsx:237`), so nothing else breaks. `wdlStatsMap` reads only the
totals (`useOpeningsChartData.ts:181-193`).

**Most-played rows have no series today.** The request is keyed by `bookmark_id: int`
(`schemas/openings.py:134-148`), but `target_hash/match_side/color` is all the backend needs. Recommend a lazy
per-row hook (`useOpeningRowTimeSeries`) that fires only when a row is expanded, with
`{bookmark_id: 0, target_hash: row.full_hash, match_side: 'full', color}` and the same filter params as
`useOpeningsChartData.ts:158-176`. Bookmark rows reuse the already-loaded series.

---

### Pattern F1: Remove the Insights tab and route (D-00, D-15)

Read this session (`frontend/src/pages/Openings.tsx`):
- `TAB_INFO` keyed `'explorer' | 'games' | 'stats' | 'insights'` (`:69-86`). Drop `insights`; rewrite the `stats` text (it mentions bookmarked/most-played).
- `activeTab` derivation (`:98-104`): drop the insights branch.
- Redirect: `needsLegacyRedirect = location.pathname.endsWith('/statistics') || location.pathname.endsWith('/compare')` (`:96`) → `<Navigate to="/openings/stats" replace />` (`:572-574`). **Add `endsWith('/insights')` here.** That is the whole D-15 redirect. Without it `/openings/insights` would fall through to `activeTab = 'explorer'`.
- Desktop trigger `tab-insights` (`:622-632`), mobile trigger `tab-insights-mobile` (`:758-767`), `TabsContent value="insights"` (`:710`, `:851`), `insightsTabEl` (`:533-540`), `InsightsTab` import (`:65`), `Lightbulb` icon import (`:13`).
- Mobile sticky Filters row condition `(activeTab === 'stats' || activeTab === 'insights')` (`:774`).
- Union `'explorer' | 'games' | 'stats' | 'insights'` also in `useDeepLinkHighlight.ts:27`, `useTabReset.ts:16`, `useOpeningsHandlers.ts:21`, `OpeningsMobileBoardPanel.tsx:15`; `openingsBoardLayout.ts:17` (`hideOnLg = activeTab === 'stats' || activeTab === 'insights'`). Recommend one exported `OpeningsTab` type to stop the 6-way duplication.
- `useDeepLinkHighlight` and `handleOpenFinding`/`handleOpenFindingGames` **stay**: finding cards on Stats still deep-link into the Moves tab with the pulse highlight. Only the comments ("Insights → MoveExplorer") change.
- Route is `<Route path="/openings/*" …>` (`App.tsx:1070`), so no router-config change is needed. No other repo file links to `/openings/insights` (grep of `frontend/src`, `app`, `stories`: no hits).
- Delete `pages/openings/InsightsTab.tsx`, `components/insights/OpeningInsightsBlock.tsx` (+ `.test.tsx`), `components/insights/OpeningFindingCard.tsx` (+ `.test.tsx`), `components/stats/OpeningStatsSection.tsx`, `components/stats/OpeningStatsCard.tsx` (+ `__tests__/OpeningStatsCard.test.tsx`). Keep `hooks/useOpeningInsights.ts` (the new findings section uses it).

### Pattern F2: Sticky White | Black switch (D-00)

- Reuse `components/stats/StickyTcBar.tsx` (sticky container, desktop overlays the first heading row at `md:top-2`, mobile in-flow sticky row with blur; `useIsPinned`). Model the switch on `TcSwitch.tsx` (buttons with `aria-pressed`, `variant` default/brand-outline, `min-h-11` touch target, tracks only on a click that changes the selection).
- **Mobile conflict:** the Stats subtab already renders a sticky Filters row: `sticky top-0 z-20 … bg-background/80 backdrop-blur-sm` (`Openings.tsx:774-788`). Put the colour switch **in that same row** on mobile (left side), or pass `showOnMobile={false}` to the bar and render the switch there. Two `top-0` sticky rows would overlap.
- State: local `useState` (not persisted, D-00). Initial value: recommend `filters.color` at mount (the "Played as" filter), so a user browsing Black lands on Black. Do not write back to the filter store: `onTogglePlayedAs` navigates away from Stats (`Openings.tsx:817`), which the switch must not do.
- Umami: register a new option target, e.g. `{ target: 'opening-stats-color'; value: 'white' | 'black' }` in `OptionChangeProps` (`lib/analytics.ts:472-485`, add to `OPTION_TARGETS` `:434-445`).
- Table header sticks under the switch: `thead th { position: sticky; top: <switch bar height> }`. See Pitfall 6.

### Pattern F3: Repertoire table (D-00, D-05..D-07)

- Closest analog: Phase 238 `components/endgames/stats/TypeTable.tsx` (`RangeCell` = caption + value + grey band + coloured dot; `significant` prop; `MiniWDLBar` for Results; the `PERCENTILE_TRACK`/`PERCENTILE_TYPICAL_BAND` theme colours).
- Theme values (verbatim, `lib/theme.ts:313-315`): `PERCENTILE_TRACK = 'oklch(1 0 0 / 0.07)'`, `PERCENTILE_TYPICAL_BAND = 'oklch(1 0 0 / 0.13)'`, `PERCENTILE_MEDIAN_TICK = 'oklch(1 0 0 / 0.35)'`. [VERIFIED: frontend/src/lib/theme.ts:313-315]
- Verdict rule (sketch `verdict(v, band, ci99, n)`): neutral when `n < 20` or `|v| <= band` or not 99%-significant; otherwise hi/lo. Map it to:
  - Score: `v = score − 0.5`, band `SCORE_BULLET_NEUTRAL_MAX = 0.05` (verbatim `lib/scoreBulletConfig.ts:15-16`: `SCORE_BULLET_NEUTRAL_MIN = -0.05`, `SCORE_BULLET_NEUTRAL_MAX = 0.05`), significance `score confidence === 'high'` (p < 0.01).
  - Eval: `v = avg_eval_pawns − baseline`, band `EVAL_NEUTRAL_MAX_PAWNS = 0.30` (verbatim `lib/openingStatsZones.ts:28`), significance `eval_confidence === 'high'` (now vs the baseline, after Pattern B1).
- **Low-sample fade constant:** `MIN_GAMES_FOR_RELIABLE_STATS = 10` (verbatim `lib/theme.ts:347`) is **not** the 20 of D-00. Add a new named constant (e.g. `REPERTOIRE_MIN_GAMES_FOR_VERDICT = 20`, mirroring backend `OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE: int = 20`, `opening_insights_constants.py:30`). Faded rows get `UNRELIABLE_OPACITY = 0.5` (`theme.ts:358`) and a neutral dot.
- Dot colour: `gapVerdictColor` in `lib/gapBar.ts:176-180` (better→`ZONE_SUCCESS`, worse→`ZONE_DANGER`, else `GAUGE_NEUTRAL`) is direction-agnostic and reusable. Position math `gapPosition`/`bandRange` (`gapBar.ts:73-92, 143-149`) puts positive values to the right, which is "better" for score and eval too. Do **not** reuse `gapVerdict`/`effectiveVerdict`/`GapBar` directly: they hard-code "lower is better" and "flaws" wording (`gapBar.ts:95-99`, `GapBar.tsx:331-334`). Recommend a small `lib/openingVerdict.ts` (pure, unit-tested) plus a shared bar component that reuses the position helpers and the GapBar track markup.
- Rows: a `useRepertoireRows(color)` hook (CLAUDE.md data-shaping seam) merges bookmark rows (built today in `StatsTab.tsx:56-91`) and most-played rows into one view model with `kind: 'bookmark' | 'current' | 'past'`.
- Games cell: count + `formatRelativeDate` (`lib/relativeDate.ts:41`). Opening cell: 44px `LazyMiniBoard` (`components/board/LazyMiniBoard.tsx`, props `fen, flipped, size, arrows?`), name with ECO stripped (use `opening_name`/`display_name`; never `label`, which is `f"{name} ({eco})"` at `stats_service.py:446`), move line from `pgn`.
- Keep the Tier-2 readiness placeholder (`useReadiness().tier2`, `EvalCpuPlaceholder`) for the Eval cell while Stockfish is still analysing; today's cards gate on it.
- React keys and testids: use `full_hash`/bookmark id and an index, never the opening name. Names repeat without ECO: the owner's Black list has two "vs. Caro-Kann Defense" rows (B12 ply 3, n=426, and B15 ply 5, n=113, different game sets) because `openings_dedup` is `DISTINCT ON (eco, name)`. [VERIFIED: dev DB view definition + probe]
- Phone: stacked rows (name left; Score above Eval top right; WDL bar full width with "N games · last played").

### Pattern F4: Moves/Games eval re-centring (D-00 scope "Moves, Games")

`PositionResultsPanel` (`components/charts/PositionResultsPanel.tsx`) is shared by ExplorerTab, GamesTab and
**Endgames** (`pages/Endgames.tsx:296-302`, `evalContext="endgame-entry"`). Today it draws the eval `MiniBulletChart`
centred on 0 with `tickPawns={isEndgameEntryEval ? undefined : resolvedEvalBaselinePawns}` (`:232-243`) and colours
the text with `evalZoneColor(value)` anchored at 0 (`:89`, `lib/openingStatsZones.ts:48-52`). `MiniBulletChart`
already supports `center` (offsets for `neutralMin/Max` are relative to it) and `tickPawns` (absolute position)
(`components/charts/MiniBulletChart.tsx:36-73`). For `evalContext === 'opening-end'` only, pass
`center={baseline}`, `neutralMin={EVAL_NEUTRAL_MIN_PAWNS}`, `neutralMax={EVAL_NEUTRAL_MAX_PAWNS}`, `tickPawns={0}`
(the faint "equal" tick), and colour via `evalZoneColor(value − baseline)`. Keep the endgame branch byte-identical.
Update the `EvalConfidenceTooltip` copy for opening-end only (`:25-31` "deviation from 0 pawns", `:100-104` "Dashed
tick: typical eval…", "Test: two-sided Wald z vs 0 pawns"). Also drop the "pawns" unit on the Openings surfaces
(D-00). The endgame-entry copy keeps "vs 0".

### Pattern F5: Finding cards + "Not clear yet" (D-00, D-08..D-11)

- Card: "After 2...e6" via `formatCandidateMove(entry_san_sequence, candidate_move_san)` (`lib/openingInsights.ts`); subtitle opening name (no ECO; `opening_name` may be the sentinel `"<unnamed line>"`, `opening_insights_service.py:63`) + full line; board 120px with arrow via `sanToSquares(entry_fen, candidate_move_san)` + `LazyMiniBoard arrows`; "You score X%" + score popover (backend Wilson `p_value`) + WDL bar; Eval bar (centred); a "why" line only when the eval verdict is hi/lo (sketch `why()`); Moves/Games links → `handleOpenFinding` / `handleOpenFindingGames` (`useOpeningsHandlers.ts:194-225`); "older games" chip when `!is_current`.
- Phone: `INITIAL_VISIBLE_PHONE = 2`, "Show more" to 5. Desktop: all 5, `grid-cols-1 lg:grid-cols-2` (existing grid at `OpeningInsightsBlock.tsx:254`).
- Keep the `isLoading`/`isError` (with retry) branches from `OpeningInsightsBlock.tsx:95-103` (frontend/CLAUDE.md requires the error branch).

### Pattern F6: Expanded row + single-opening ScoreChart (D-00, D-14)

- `ScoreChart` (`components/charts/ScoreChart.tsx:13-16`) takes `bookmarks[]` + `series[]`, builds per-bookmark lines, a legend with hide toggles, and a "Bookmarked Openings: Score over Time" header. Retire all of that. New props: `{ series: BookmarkTimeSeries; showVolume?: boolean }`. Switch to `ComposedChart` with a `yAxisId="bars"` hidden right axis, `domain={[0, barMax * 5]}` and `fill={VOLUME_BAR_COLOR}` (verbatim `lib/theme.ts:495`: `VOLUME_BAR_COLOR = 'oklch(0.55 0 0 / 0.25)'`), per `EndgameScoreOverTimeChart.tsx:121-124, 186-188, 249-252`. Keep `inactivityGapReferenceLines({ dates, yAxisId: 'value' })` (with a named axis you must pass `yAxisId`, as the endgame chart does at `:248`).
- Expanded row: 200px board; Moves (`handleOpenMoves`), Games (`handleOpenGames` / `handleOpenChartBookmarkGames` for bookmarks), Bookmark add/remove (`useCreatePositionBookmark` / `useDeletePositionBookmark`); Score bar (centre 50%, band 45-55%); Eval bar; chart. Phone: links stack right of the board (sketch MANIFEST).
- Row expand → `trackFeature('panel-open', { target: … })`: register a new `PANEL_TARGETS` entry (e.g. `'opening-row-expand'`, analog of existing `'move-stats-expand'`, `analytics.ts:362-376`).

### Pattern F7: Umami registry changes

`PANEL_TARGETS` today contains `'opening-insights-more'` and `'opening-stats-more'` (`lib/analytics.ts:362-376`).
After deleting `OpeningStatsSection` (the only `opening-stats-more` emitter, `:66`) and `OpeningInsightsBlock` (the
only `opening-insights-more` emitter, `:271`):
- reuse `'opening-insights-more'` for the phone "Show more" findings (same concept; never rename, D-01 of analytics);
- reuse `'opening-stats-more'` for "Played before (n)" expand (same "more rows" concept), or add a new target. Planner's call;
- new: `'opening-findings-unclear'` (Not clear yet expand), `'opening-row-expand'`, option target `'opening-stats-color'`;
- `toggle` target `'bookmark-chart'` (`analytics.ts:352`) stays as long as the bookmark include/exclude toggle stays (Open Question 1).
- Popovers: `InfoPopover` testIds become `popover-open` targets via `popoverTargetFromTestId` (numeric segments stripped). Use `repertoire-row-{index}-score-info`, never SAN/name/FEN.

### Anti-Patterns to Avoid
- **Centring inside `compute_eval_confidence_bucket`'s default**: changing `baseline_cp`'s default would silently move the endgame test. Centre at the Openings finalizer only.
- **Running phase-entry eval on all 60 candidates**: that is the expensive query; run it on survivors.
- **Frontend-side cap after backend cap**: D-06 dedupe and the bookmark drop must happen before the 10/10 cap, so the cap belongs to the backend.
- **Deriving the medium count from the capped list**: D-09's `n` is the full medium count.
- **Using `label`/`opening_eco`** anywhere on the page (D-00 no ECO).
- **Reusing `GapBar` verbatim**: wrong direction and wording for opening metrics.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score significance / CI | new Wilson math in TS | backend `compute_confidence_bucket` + `wilson_bounds(z=VERDICT_CI_Z_99)` (`score_confidence.py:82, 354`); TS `computeScoreConfidence` only if client-side | the formulas already exist twice; a third copy drifts |
| Eval z-test | a second z-test | `compute_eval_confidence_bucket(..., baseline_cp=…)` | the parameter exists for exactly this |
| Weekly bucketing | ad-hoc week math | the ISO-week pattern at `endgame_service.py:1222-1254` | same semantics as the existing volume bars |
| Sticky switch | new sticky container | `StickyTcBar` + `useIsPinned` | handles desktop overlay and mobile blur |
| Inactivity breaks | new gap detection | `inactivityGapReferenceLines` | shared helper, threshold already tuned |
| Bookmark full hash | parse FEN | replay moves + `compute_hashes` | board-only legacy FENs give wrong hashes (`position_bookmark_repository.py:284-286`) |
| Relative dates | new formatter | `formatRelativeDate` (`lib/relativeDate.ts:41`) | consistent "3 days ago" copy |

**Key insight:** almost every primitive exists. The phase is mostly re-wiring and deleting, and the risk is in
ordering (dedupe before cap, cap before eval) and in scoping the eval centring to Openings only.

## Runtime State Inventory

(This phase removes a route and changes response shapes, so the inventory is included.)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. No table or column changes; no migration needed (all new fields are computed per request). Verified: no schema change is implied by any decision | none |
| Live service config | Umami: events `panel-open/opening-insights-more` and `opening-stats-more` keep their history if reused; URL pageviews for `/openings/insights` stop after deploy (expected) | reuse targets rather than rename (Pattern F7) |
| OS-registered state | None (pure web app change) | none |
| Secrets/env vars | None | none |
| Build artifacts / client state | Browser `localStorage` keys `bookmark-chart-enabled-<id>` (`Openings.tsx:7-9`, `useOpeningsChartData.ts:25-28`) persist if the include/exclude toggle is retired; TanStack cache keys `openingInsights`/`mostPlayedOpenings` change shape (cache is in-memory, refreshes on deploy); users' bookmarked `/openings/insights` URLs are covered by the redirect | if the toggle is retired, optionally clear the keys; otherwise none |

## Common Pitfalls

### Pitfall 1: Moving the endgame eval by accident
**What goes wrong:** the Endgames page eval verdict or tick shifts.
**Why:** `endgame_service.py` imports the same primitive (`:55`, call `:747`) and `EVAL_BASELINE_PAWNS_WHITE` (`:60`,
display `:824`). `PositionResultsPanel` is shared with `Endgames.tsx:296-302`.
**How to avoid:** do not change `baseline_cp`'s default; centre only in the Openings finalizer; branch the panel on `evalContext === 'opening-end'`.
**Warning signs:** `tests/test_endgame_service.py` or `Endgames.*.test.tsx` diffs.

### Pitfall 2: Cutoff with fewer than 200 games
**What goes wrong:** the floor `now − 60 d` alone marks a light user's older openings "past".
**How to avoid:** if the OFFSET query returns no row, cutoff = `None` = all current (D-01 rationale: 466 of 1,276 pairs unchanged).

### Pitfall 3: Fetch too small for heavy, repertoire-shifting users
**What goes wrong:** fewer than 10 current rows although more current openings exist.
**Evidence:** owner White, 10th current row at rank 33 (dev). **Avoid:** `MOST_PLAYED_FETCH_LIMIT = 60`, plus the cutoff-restricted second query when current rows run short (Pattern B3, built per D-05 clarified).

### Pitfall 4: Bookmark twin drop vs the bookmark include/exclude toggle
**What goes wrong:** the per-bookmark toggle (`aria-label` "Exclude from opening results" / "Include in opening results",
`PositionBookmarkCard.tsx:193`) filters bookmarks out of the Stats rows client-side (`chartBookmarks`,
`useOpeningsChartData.ts:121-124`). The backend cannot see that localStorage flag, so it would drop the most-played twin of an *excluded* bookmark, and the opening vanishes from the table.
**How to avoid:** see Open Question 1.

### Pitfall 5: Index-based row tuples
**What goes wrong:** adding `ply_count` to the top-openings SELECT shifts `row[5]` (full_hash) used in 4 places in `stats_service.py:332-387` and the 10-tuple destructure at `:395`.
**How to avoid:** switch to `row.full_hash` etc. in the same change.

### Pitfall 6: `overflow-hidden` kills `position: sticky`
**What goes wrong:** the table header does not stick under the switch.
**Why:** any ancestor with `overflow: hidden/auto` becomes the sticky scroll container. Card wrappers here use `charcoal-texture rounded-md overflow-hidden` (`StatsTab.tsx:236`).
**How to avoid:** no `overflow-hidden` on the table's ancestors (clip rounded corners on the cells instead); test the sticky behaviour in the browser.

### Pitfall 7: Medium count after the cap
**What goes wrong:** "Not clear yet (n)" shows ≤10 although more exist.
**How to avoid:** count before `[:FINDINGS_NOT_CLEAR_CAP]` (Pattern B5); unit-test with 12 medium candidates.

### Pitfall 8: Eval enrichment on uncapped findings
**What goes wrong:** the insights endpoint takes 10+ s for strong users (529 high findings).
**How to avoid:** cap (5 high + 10 medium per section) before `_enrich_findings`.

### Pitfall 9: Stale verification of frontend types
**What goes wrong:** `npm run lint` and `npm test` pass, but `tsc` fails on the changed `OpeningWDL`/`OpeningInsightsResponse`/`TimeSeriesPoint` types (memory: "Run tsc -b before integrating frontend").
**How to avoid:** `npm run build` in every frontend plan's verify step.

### Pitfall 10: knip after deletions
**What goes wrong:** CI fails on now-unused exports: `computeScoreConfidence` (`lib/scoreConfidence.ts`, only importer `OpeningStatsCard`), `evalZoneColor` and `EVAL_BULLET_DOMAIN_PAWNS` (if only the Moves panel remains), `SCORE_BULLET_DOMAIN`, `OpeningStatsSectionDescriptor`, `WdlStatsRow` (exported from StatsTab and imported by `useOpeningsChartData.ts:18`). `formatCandidateMove` stays used by the new finding cards; `formatMoveNotation` stays used by `components/library/FlawCard.tsx`.
**How to avoid:** run `npm run knip` in the deletion plan and delete or move the exports.

### Pitfall 11: Name collisions without ECO
Same display name for different positions (two "vs. Caro-Kann Defense" rows). Show the move line, and never key by name (Pattern F3).

## Code Examples

### Centred eval finalizer (backend)
```python
# Source: pattern from app/services/stats_service.py:424-439 + eval_confidence.py:53-55 signature.
# CENTIPAWNS_PER_PAWN and the module/function names are new (ASSUMED naming).
def resolve_eval_baseline_pawns(color: Literal["white", "black"] | None) -> float:
    return EVAL_BASELINE_PAWNS_BLACK if color == "black" else EVAL_BASELINE_PAWNS_WHITE

def finalize_opening_eval(pe: OpeningPhaseEntryMetrics, color: Literal["white", "black"] | None) -> OpeningEvalFields:
    baseline_cp = resolve_eval_baseline_pawns(color) * CENTIPAWNS_PER_PAWN
    confidence, p_value, mean_cp, ci_half = compute_eval_confidence_bucket(
        pe.eval_sum_mg, pe.eval_sumsq_mg, pe.eval_n_mg, baseline_cp=baseline_cp
    )
    ci99_half = ci_half * VERDICT_CI_Z_99 / OPENING_INSIGHTS_CI_Z_95
    ...  # avg_eval_pawns = mean_cp / CENTIPAWNS_PER_PAWN (raw, not centred); CIs only when eval_n_mg >= 2
```

### Cutoff (backend)
```python
# Source: SQL measured on dev this session; filter seam app/repositories/query_utils.py:169.
stmt = select(Game.played_at).where(
    Game.user_id == user_id, Game.played_at.isnot(None)
)
stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type, from_date, to_date,
                          color=color, opponent_gap_min=opponent_gap_min, opponent_gap_max=opponent_gap_max)
stmt = stmt.order_by(Game.played_at.desc()).offset(CURRENT_REPERTOIRE_RECENT_GAMES - 1).limit(1)
nth = (await session.execute(stmt)).scalar_one_or_none()
cutoff = None if nth is None else min(nth, now_utc - datetime.timedelta(days=CURRENT_REPERTOIRE_MIN_DAYS))
```

### Weekly point (backend)
```python
# Source: app/services/endgame_service.py:1222-1254 (ISO week, Monday key).
iso_year, iso_week, iso_weekday = played_at.isocalendar()
monday = (played_at - datetime.timedelta(days=iso_weekday - 1)).date()
```

### Redirect (frontend)
```tsx
// Source: frontend/src/pages/Openings.tsx:96 (existing legacy redirect, extended).
const needsLegacyRedirect = location.pathname.endsWith('/statistics')
  || location.pathname.endsWith('/compare')
  || location.pathname.endsWith('/insights');
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Eval H0 = 0 cp, baseline as tick (`opening_insights_constants.py:82-84`) | H0 = colour baseline (Openings only) | this phase | some verdicts change; the owner's sketch data shows 5 of 25 repertoire verdicts change, all colour-driven (SEED-204) |
| Bullet charts with CI whiskers + coloured fonts + spines | one verdict bar, grey band, verdict dot, 99% gate | Phases 238/239 | page-level consistency |
| Per-date time series points | weekly points + volume | this phase | fewer, steadier points |

**Deprecated/outdated after this phase:** `OpeningStatsSection`, `OpeningStatsCard`, `OpeningFindingCard`, `OpeningInsightsBlock`, `InsightsTab`, multi-line `ScoreChart`, `WEAKNESS_CAP_PER_COLOR`/`STRENGTH_CAP_PER_COLOR`, `TOP_OPENINGS_LIMIT`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Selective filters keep the cutoff query in the tens of ms (only default filters were measured) | B2 | slower endpoint; mitigate with EXPLAIN on prod in UAT |
| A2 | `(count, sum(distinct id))` (+ optional `bit_xor`) has no practical collisions among one user's nested opening game sets | B4 | a wrongly merged row (rare); add the eval_n/last_played_at equality as a belt-and-braces check |
| A3 | Initialising the colour switch from `filters.color` is what the owner wants (the sketch defaults to White) | F2 | trivial copy/UX change |
| A4 | Reusing `opening-insights-more` / `opening-stats-more` targets for the new expanders is acceptable to the owner | F7 | analytics continuity only |
| A5 | 60 fetch rows is enough on prod (sized on the dev snapshot; the owner has more recent games on prod) | B3 | moot: the cutoff-restricted second query (built per D-05 clarified) fills current rows when the top 60 hold fewer than 10 |
| A6 | New helper/module/constant names (`opening_eval.py`, `CENTIPAWNS_PER_PAWN`, `MOST_PLAYED_FETCH_LIMIT`, `FINDINGS_CARD_CAP`, target names) | Patterns | naming only |
| A7 | Moves/Games keep the `MiniBulletChart` (re-centred) rather than adopting the new verdict bar | F4 | if the owner wants the new bar there too, add a plan. **Superseded by D-17** (new verdict bar, plan 242-04) |

## Open Questions (RESOLVED)

All four items were answered on 2026-10-17 (owner decisions D-16..D-18 in 242-CONTEXT.md, item 4 by the planner).

1. **Bookmark include/exclude toggle vs server-side bookmark-twin drop (blocking design point).**
   - Known: the toggle ("Include in opening results") filters bookmarks out of the Stats rows via localStorage (`chartBookmarks`); its name says "chart" because it also fed the multi-line chart that D-14 retires. The backend dedupe cannot see it.
   - Unclear: should an excluded bookmark still suppress its most-played twin?
   - Recommendation: ask the owner. Option A (simplest): with the multi-line chart gone, **retire the toggle** (all coloured bookmarks are rows; delete `chartEnabledMap`, localStorage keys, the `bookmark-chart` toggle UI). Option B: keep the toggle and send the excluded bookmark ids to `/stats/most-played-openings` so the backend skips them during the twin drop.
   - **RESOLVED (D-16):** Option A. The toggle and its localStorage state are retired (plan 242-05); the endpoint takes no bookmark-exclusion parameter (plan 242-01).
2. **Moves/Games eval visual.** D-00 lists Moves/Games in the centring scope. Is re-centring the existing `MiniBulletChart` enough (recommended, minimal), or should they adopt the new verdict bar? The default in A7 is re-centre only.
   - **RESOLVED (D-17):** Moves and Games adopt the new 238/239-style verdict bar for `evalContext="opening-end"` (plan 242-04); Endgames keeps its current display. This supersedes A7.
3. **Bookmark score p/CI source.** Server-side on `BookmarkTimeSeries` (recommended, one source) or client-side `computeScoreConfidence` with a z parameter. The planner picks; both are cheap.
   - **RESOLVED (D-18):** server-side on `BookmarkTimeSeries` with the same score/Wilson util as the most-played rows (plan 242-03); the client-side `computeScoreConfidence` is deleted (plan 242-06).
4. **Insights response compatibility.** Changing the four lists to "high only, ≤5" changes their meaning for any other consumer. Grep shows the only consumers are the frontend block and tests (no LLM use of `compute_insights`). Safe to change in place.
   - **RESOLVED (planner):** changed in place, no versioned endpoint (plan 242-02).

Not an open question, recorded here so plans can cite it: the second top query for heavy users (Pattern B3,
Pitfall 3, assumption A5) **is built** (owner, "D-05 (clarified)" in 242-CONTEXT.md, superseding the earlier
"not built" note). `MOST_PLAYED_FETCH_LIMIT = 60` runs first; plan 242-01 Task 3 adds the cutoff-restricted second
fetch, and plan 242-09 keeps "10 current rows for the owner's White repertoire" as a UAT check.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev DB (Docker `flawchess-dev-db-1`) | backend tests, probes | ✓ | postgres:18-alpine | — |
| uv / Python | backend | ✓ | uv 0.10.9 / Python 3.14.3 | — |
| Node / npm | frontend | ✓ | v24.19.0 / 11.17.0 | — |
| Chrome (browser UAT of sticky header, phone layout) | UAT | not probed | — | owner device UAT |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest + pytest-asyncio (`asyncio_mode = "auto"`, pyproject.toml:83-93), per-worker cloned Postgres DB |
| Framework (frontend) | vitest 5 (`npm test` = `vitest run`) + Testing Library |
| Config files | `pyproject.toml [tool.pytest.ini_options]`; `frontend/vite.config.ts` test block + `src/vitest.setup.ts` |
| Quick run (backend) | `uv run pytest tests/test_stats_service.py tests/services/test_stats_service_phase_entry.py tests/services/test_opening_insights_service.py tests/test_openings_time_series.py tests/services/test_eval_confidence.py -x` |
| Quick run (frontend) | `cd frontend && npx vitest run src/pages/__tests__/Openings.render.test.tsx src/components/charts/__tests__/ScoreChart.test.tsx` |
| Full suite | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-00/D-13 | finalizer passes `baseline_cp = ±25`; a mean of exactly +25 cp for White reads p ≈ 1 / "low"; −25 for Black likewise; raw `avg_eval_pawns` unchanged | unit | `uv run pytest tests/services/test_opening_eval.py -x` | ❌ Wave 0 |
| D-13 | all 4 call sites centred (most-played, bookmark with colour, Moves `analyze`, insights finding) | integration | `uv run pytest tests/services/test_stats_service_phase_entry.py tests/test_openings_service.py tests/services/test_opening_insights_service.py -x` | ✅ (extend) |
| D-13 guard | endgame eval unchanged | regression | `uv run pytest tests/test_endgame_service.py -x` | ✅ |
| D-01/D-02/D-03 | cutoff: <200 games → None; 200th date vs 60-day floor picks the earlier; respects filters; uses injected now_utc | unit/integration | `uv run pytest tests/test_repertoire_recency.py -x` | ❌ Wave 0 |
| D-05/D-06 | fetch → dedupe identical set keeps deeper ply → bookmark twin dropped (bookmark `moves` replay) → split → cap 10/10; current-first ordering | integration | `uv run pytest tests/test_stats_service.py -k most_played -x` | ✅ (extend) |
| D-06 | dedupe does not merge different sets with equal W/D/L | unit | same file | ❌ Wave 0 |
| D-09/D-10/D-11 | high ≤5 current-first; medium ≤10 by p asc, current first; `*_not_clear_count` = full count; low dropped | unit (mocked repos, existing harness `test_opening_insights_service.py:144-210`) | `uv run pytest tests/services/test_opening_insights_service.py -x` | ✅ (extend; caps import at :30-31 changes) |
| D-00 series | weekly points + `per_week_games`; rolling warm-up preserved; totals unchanged | integration | `uv run pytest tests/test_openings_time_series.py tests/test_aggregation_sanity.py -x` | ✅ (update same-day/date assertions) |
| D-03 | routers inject `dev_now_utc` | router | `uv run pytest tests/test_stats_router.py tests/routers/test_insights_openings.py -x` | ✅ (extend) |
| D-15 | `/openings/insights` → `/openings/stats`; no insights triggers | component | `npx vitest run src/pages/__tests__/Openings.render.test.tsx` | ✅ (update lines 159, 167) |
| D-00 layout | board hidden on stats only | unit | `npx vitest run src/pages/__tests__/Openings.statsBoard.test.tsx` | ✅ (drop the insights case at :23-26) |
| D-00 verdicts | opening verdict: n<20 neutral; inside band neutral; outside + high → hi/lo; eval centred on baseline | unit | `npx vitest run src/lib/__tests__/openingVerdict.test.ts` | ❌ Wave 0 |
| D-00 table | pinned bookmarks, current, collapsed "Played before (n)", stale-bookmark chip, faded rows, no ECO | component | `npx vitest run src/components/openings/__tests__/RepertoireTable.test.tsx` | ❌ Wave 0 |
| D-08..D-11 | phone 2 + Show more (trackFeature called), Not clear yet (n), empty-state copy | component | `npx vitest run src/components/openings/__tests__/OpeningFindings.test.tsx` | ❌ Wave 0 |
| D-14 | single-series ScoreChart renders volume bars when `showVolume` | component | `npx vitest run src/components/charts/__tests__/ScoreChart.test.tsx` | ✅ (rewrite) |
| D-00 Moves | PositionResultsPanel opening-end centred, endgame-entry unchanged | component | `npx vitest run src/components/insights/__tests__/EvalConfidenceTooltip.test.tsx src/pages/__tests__/Endgames.readinessGate.test.tsx` | ✅ (extend) |
| UAT | sticky switch + sticky header on scroll; phone stacking; owner data (Queen's Gambit 280 games Oct 2023 → "Played before"; Caro-Kann Advance 172 dup collapsed) | manual-browser | `/gsd-verify-work` (browser UAT, memory: run it yourself) | — |

### Sampling Rate
- **Per task commit:** the quick-run command for the touched side.
- **Per wave merge:** full backend suite (`-n auto`) after wave 1; full frontend gate after wave 2.
- **Phase gate:** the full CLAUDE.md pre-merge gate green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/services/test_opening_eval.py`: centred finalizer
- [ ] `tests/test_repertoire_recency.py`: cutoff helper (fixtures with >200 and <200 games, `now_utc` injected)
- [ ] dedupe/split cases in `tests/test_stats_service.py`
- [ ] `frontend/src/lib/__tests__/openingVerdict.test.ts`
- [ ] repertoire table + findings component tests
- [ ] Delete with their components: `OpeningStatsCard.test.tsx`, `OpeningFindingCard.test.tsx`, `OpeningInsightsBlock.test.tsx`; adjust `EvalCpuPlaceholder.test.tsx` (renders `OpeningStatsCard`, line ~97) and `openingStatsZones.test.ts` if exports move.
- Memory reminders for the tests: every non-guest `Game` insert needs finally-cleanup (eval lottery isolation); serial CI can expose isolation bugs that `-n auto` hides.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no change | FastAPI-Users `current_active_user` on all three endpoints |
| V3 Session Management | no | — |
| V4 Access Control | yes | user scoping by `user.id` from the auth dependency; bookmarks loaded server-side by `get_bookmarks(session, user_id)`, so no client-supplied bookmark ids for dedupe (Option A) or validated ints scoped to the user (Option B) |
| V5 Input Validation | yes | Pydantic `Literal` filters, `extra="forbid"` on `OpeningInsightsRequest`; dev clock header honoured only when `ENVIRONMENT == "development"` (`dev_clock.py:68`) |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Forged `X-Dev-Clock-Offset-Minutes` on prod to shift the cutoff | Tampering | inert outside development (`dev_clock.py:68-69`) |
| IDOR through Option B bookmark ids | Information disclosure | filter ids by `user_id` in the repository query |
| Free text in Umami props | Information disclosure | enumerated literal targets only; no SAN/name in testIds |

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/{stats_service,openings_service,opening_insights_service,eval_confidence,opening_insights_constants,score_confidence,endgame_service}.py`; `app/repositories/{stats_repository,openings_repository,position_bookmark_repository,query_utils}.py`; `app/schemas/{stats,openings,opening_insights,position_bookmarks}.py`; `app/routers/{stats,openings,insights}.py`; `app/core/dev_clock.py`; `app/models/{game,position_bookmark}.py`
- `frontend/src/pages/Openings.tsx`, `pages/openings/*`, `components/{charts/ScoreChart,charts/EndgameScoreOverTimeChart,charts/PositionResultsPanel,charts/MiniBulletChart,library/stats/GapBar,stats/StickyTcBar,stats/TcSwitch,insights/*,endgames/stats/TypeTable}.tsx`, `lib/{gapBar,openingStatsZones,scoreBulletConfig,theme,analytics,scoreConfidence}.ts`, `hooks/{useStats,usePositionBookmarks,useOpeningInsights}.ts`
- `.planning/seeds/SEED-204-*.md`, `.planning/sketches/012-opening-stats-repertoire/{README.md,index.html}`, `239-CONTEXT.md` (D-14..D-17), `reports/benchmark/benchmarks-latest.md` §2/§2.1
- Dev DB probes (read-only): EXPLAIN of the cutoff query; `temp/phase242-research/{time_mpo,dups,current_split,time_fetch,insights_conf}.py`

### Secondary / Tertiary
- none (no web research was needed; no new libraries)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies.
- Architecture: HIGH. Every call site, line and data shape was read; the cutoff, dedupe and fetch size were measured on dev.
- Pitfalls: HIGH for the code-level items; MEDIUM for prod-scale performance (dev snapshot only).

**Research date:** 2026-10-17
**Valid until:** 2026-11-16 (stable internal code; re-check line numbers if other phases touch these files first)
