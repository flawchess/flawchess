# Phase 238: Endgame Stats Percentile-First Redesign (SEED-196) - Research

**Researched:** 2026-10-11
**Domain:** FastAPI/SQL on-read analytics over the canonical ranked slice, LLM insights payload, React/Recharts dashboard rework
**Confidence:** HIGH for the codebase map and the definitional-parity findings (read and probed this session); MEDIUM for the response-schema and plan-split recommendations (design judgement)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from SEED-196 (locked 2026-10-11, do not re-ask)
- **D-00a:** Percentile bar (0-100, typical band 25-75 shaded, median tick, dot red <25 / blue 25-75 / green >75) is the only verdict on peer-ranked metrics. Values uncolored.
- **D-00b:** Display the ranked value, not the filtered whole-history value.
- **D-00c:** One popover per metric: WHAT + sign, percentile statement + the four disclosures (cohort, recent-games basis, filter independence, anchor composition), then n / 95% CI / p-value greyed below a separator. Merges `MetricStatPopover` and `PercentileChip`.
- **D-00d:** Gauges removed; bracket under the WDL bar marks what the rate counts.
- **D-00e:** Endgame Type Breakdown becomes a table with grey typical ranges, white "you" tick, amber below-typical value, rows under ~100 games faded, no red/green, stacked rows on mobile.
- **D-00f:** Clock Gap timeline and time-pressure curve: one grey typical band, neutral line/dots.
- **D-00g:** "Compared to similar-rated players" dot-plot card ships; rows link to their sections.
- **D-00h:** One TC switch per section, synced; Overall becomes per-TC (2 cards); aggregated cross-TC chips retire.
- **D-00i:** Unchanged: Shelly block, per-section narration slots, Endgame Score Gap over Time, Endgame ELO Timeline visuals.

#### Filters on the Stats tab
- **D-01:** The Stats tab ignores filters entirely. Every Stats section reads the ranked sample per TC. Filters keep working on the Games tab. — **Reversibility:** costly — reintroducing filtered values means a second value path per section and brings back the dual-value problem.
- **D-02:** The filter panel (desktop sidebar and mobile filter button/drawer) is **hidden** while the Stats tab is active and reappears on the Games tab. Applied filter state is preserved (not reset) while hidden.
- **D-03:** Both timelines (Endgame Score Gap over Time, Endgame ELO Timeline) switch to the ranked sample and follow the section TC switch. The ELO Timeline keeps its existing green/red band (only the data source changes).
- **D-04:** Shelly insights become filter-independent: one report per user, no reset-filters-before-Generate step, no per-filter-state cache key (the `opponent_strength` exception in `_validate_full_history_filters` and the frontend `toInsightsFilters` / `areFiltersEqual` cache plumbing go away). Narrated numbers come from the ranked sample (SEED-196 payload alignment). — **Reversibility:** costly — touches the insights request contract, server cache keying and the frontend cache.

#### Ranked-sample scope
- **D-05:** The Endgame Type Breakdown table also uses the ranked sample per TC and follows the TC switch. Accept more rows under the fade threshold. Grey typical ranges stay the existing population zones (`PER_CLASS_TC_GAUGE_ZONES` / type score-gap band).
- **D-06:** Time Pressure curve (per-quintile score gaps) and Clock Gap timeline use the ranked sample per TC.
- **D-07:** Values are **computed on read** from the canonical ranked slice (reuse `canonical_slice_sql.py`; CDF-side and user-side SQL stay byte-identical). Percentiles stay as persisted by Stage A/B.
- **D-08:** No drift handling between a fresh on-read value and the stored percentile. Owner: percentiles are recomputed very quickly on import. Do not add "percentile updating" states or value/n mismatch disclosures.

#### Missing-percentile states
- **D-09:** TC below the 30-game anchor floor (`MEDIAN_ANCHOR_MIN_GAMES`): TC stays in the switch, cards show ranked-sample values + WDL, the percentile bar slot reads "Not enough games to rank yet (18 of 30)" with no colored dot. The dot-plot card omits that TC (or hides when the selected TC is unranked).
- **D-10:** No TC above the floor: same per-TC treatment as D-09; the dot-plot card hides. If the ranked sample is empty (0 qualifying games in every TC), the Stats tab shows one empty state explaining what counts (rated, human opponents, ±100 Elo, last 36 months) and pointing to the Games tab.
- **D-11:** Stage B not landed (entry evals pending, so value and percentile are missing for conversion/parity/recovery/clock metrics): the card keeps its layout and shows a muted line like "Analyzing your games, this fills in once evaluations finish" instead of value/bar. Cards whose data is ready (e.g. Endgame Score Gap from Stage A) render normally. No new polling. If evals exist but the percentile row is not written yet, show the value with a "not ranked yet" style slot (same visual family as D-09).

#### TC switch
- **D-12:** Default TC on load = TC with the most ranked-sample games, ties to the faster TC; prefer an above-floor TC when one exists.
- **D-13:** Selected TC is remembered across visits in `localStorage` (try/catch, render fine without it); fall back to D-12 when the stored TC has no ranked games.
- **D-14:** The switch lists only TCs with ≥1 ranked-sample game, same list in every section. Below-floor TCs are listed (D-09); zero-game TCs are omitted.

### Claude's Discretion
- Plan split (backend ranked-sample payload vs frontend rework; likely 2-3 plans).
- Exact copy for empty / pending / not-ranked states (follow popover copy minimalism; disclosure contract applies to the percentile popover only).
- Where the on-read computation lives (extend endgame stats endpoint vs new endpoint) and response schema shape, as long as aggregated cross-TC fields (`score_gap_percentile`, `achievable_score_gap_percentile`, `per_tc_breakdown`) retire.
- Whether the TC-switch state lives in a small shared store or URL; persistence per D-13 regardless.
- Which p-value / CI rows apply per metric in the popover footer.

### Deferred Ideas (OUT OF SCOPE)
- Removing the "Compared to similar-rated players" card (owner may drop it after living with it).
- Value-axis percentile strips (the full quantile table allows them later; SEED-196 note).
- Restyling the Endgame ELO Timeline band (explicitly kept as-is, D-03).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md exists; requirement IDs are TBD. The CONTEXT.md decisions (D-00a..i, D-01..D-14) are the coverage contract. The Validation Architecture section maps each one to a test.
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Treat these like locked decisions:

- **Layering:** routers hold HTTP only, services hold logic, repositories hold SQL ("no SQL in services"). New routers use `APIRouter(prefix="/endgames", tags=["endgames"])` with relative paths.
- **`apply_game_filters()` in `app/repositories/query_utils.py` is the only filter implementation.** Never duplicate filter logic. Any ranked-id restriction added to the shared repositories must go through this seam.
- **No `asyncio.gather` on one `AsyncSession`.** Run queries one after another.
- **Types:** ty must report zero errors (`uv run ty check app/ tests/ scripts/`). Use explicit return types and `Literal[...]` for fixed value sets (never bare `str`). Use `Sequence[...]` for parameters that take Literal lists. Use Pydantic at API boundaries and TypedDict/dataclass internally. Suppress only with `# ty: ignore[rule]` plus a reason.
- **No magic numbers.** Name constants such as the 100-game type-row fade threshold, the 25/75 percentile bands and the `localStorage` key.
- **Nesting depth ≤ 4** (`scripts/check_function_size.py app/ --fail-over-depth 4`, eslint `max-depth`). Soft limits: about 100 logic lines and cognitive complexity ≤ 15. `endgame_service.py` is already 3817 lines, so put the new ranked logic in a new module.
- **Sentry:** call `capture_exception` in non-trivial `except` blocks in services and routers. Pass variables through `set_context`, never in the message.
- **Frontend:** theme colors live in `lib/theme.ts`; `noUncheckedIndexedAccess` is on; knip runs in CI; minimum font size is `text-sm` (popover bodies may use `text-xs`); every interactive element gets a `data-testid`; always change the mobile layout too; `isError` branches are mandatory; `trackFeature` events go through the typed registry (reuse the 9 verbs, never rename targets); run `npm run build` (tsc) when shared types change; there is no Prettier.
- **Comment bug fixes at the fix site.** Plans must not gate completion on `bin/reset_db.sh` (memory).
- **Pre-merge gate** (mandatory before the squash-merge): ruff format, ruff check --fix, ty (app and analysis), the function-size gate, `pytest -n auto -x`, and frontend lint + build + test + knip. Also run the serial suite before a release (memory: serial CI hides isolation bugs).
- **CHANGELOG:** add user-facing bullets under `## [Unreleased]` when the phase merges.
- **Memory guardrails:** follow the percentile tooltip disclosure contract (cohort / recent-games basis / filter independence / anchor composition); no flame icons; percentile is the primary LLM narration signal; `reports/benchmark/benchmarks-latest.md` is the source of truth for "typical" copy.

## Summary

The phase splits into four engineering problems: (1) compute every displayed number **on read** from the canonical ranked slice, per TC; (2) re-point Shelly's findings at that same payload and drop all filter plumbing; (3) rebuild four frontend sections around a single `PercentileBar` + unified popover + synced TC switch; (4) retire the filtered `/endgames/overview` machinery that only the aggregated chips and the old UI needed.

The most important finding is that **the existing Python aggregators do not compute the same numbers as the persisted percentile CTEs**, so "reuse `endgame_service` over ranked games" would print values that do not match the percentile basis. Five metrics differ by definition:
- Conversion, Parity and Recovery rates: the Python path routes NULL-eval games to parity and has no sub-800 floor.
- The three per-bucket ΔES gaps: the Python per-TC cards use per-game terminal spans; the CTE uses per-(game, class) spans with LEAD.
- Clock Gap and Time Pressure Score Gap: the Python path applies a 2× base-clock clamp.
- Time Pressure Score Gap: Python never computes the 0.40-threshold scalar at all.
- Net Flag Rate: the Python denominator requires `base_time_seconds > 0`.

The fix is to compute values with canonical-mode helpers that mirror the CTE definitions, and to make a **DB-backed parity test** (on-read value == `_compute_metric_for_user_per_tc` value for all 11 families) the gate.

The second important finding is about cost. **Calling the 11 canonical CTEs on read is too slow**: 1.5 to 9.6 s per TC for heavy dev users. The recommended path is one canonical ranked-games query per TC, which reuses `selected_users_cte("single_user")` + `_recent_capped_per_tc_cte(None, tc)` unchanged, so byte-identity is untouched. Its id set is then threaded through the existing repository queries via a new `apply_game_filters` keyword, and the numbers come from canonical-mode Python. The existing filtered overview already takes 6.0 s for user 14 (22.5k games) and did not finish in more than 4 minutes for user 7 (67k games). The query stuck on user 7 was the `timeline` rows query, whose payload (`EndgameTimelineResponse`) **the frontend never reads**.

**Primary recommendation:** add `GET /api/endgames/ranked-stats` (no filter params) served by a new `app/services/endgame_ranked_service.py`. It returns all ranked TCs at once with a uniform `RankedMetricOut` per (metric, TC) that carries value, n, percentile, rank status and CI/p. Insights `compute_findings` consumes the same service. The Games tab moves to a lightweight filtered `GET /api/endgames/stats` (existing `get_endgame_stats`). Delete `get_endgame_overview`, `/endgames/overview` and the aggregated-chip helpers.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Ranked-sample game selection (36 mo, ±100, ≤3000/TC, rated, human) | Database (canonical CTE text in `canonical_slice_sql.py`) | API (repository executes) | Must be the exact SQL that feeds Stage A/B (D-07 byte-identity) |
| Per-TC metric values, WDL, CI/p | API / Backend (`endgame_ranked_service`) | — | Statistics helpers (`score_confidence.py`) live server-side; one source for UI and LLM |
| Percentile lookup | Database (persisted `user_benchmark_percentiles`) | API (read-only fetch) | D-07: percentiles stay as Stage A/B wrote them |
| Rank status (ranked / below_floor / unranked / pending) | API / Backend | Browser (renders copy only) | Needs floors, n, eval-pending counts; keep the frontend dumb |
| Default TC selection + persistence | Browser (store + `localStorage`) | API (supplies per-TC counts / anchor flags) | D-12/D-13 are presentation state |
| Filter panel hide/show per tab | Browser | — | D-02, the filter store stays intact |
| Insights findings + prompt | API / Backend (`insights_service`, `insights_llm`) | — | D-04 narrated values must equal the UI values, so it consumes the same service |
| Typical bands (type table, curve, clock timeline) | Generated constants (`endgame_zones.py` → `endgameZones.ts`) | Browser | Already codegen'd; CI drift check |

## Standard Stack

No new packages. Everything uses the existing stack. [VERIFIED: codebase — pyproject/package.json unchanged by this design]

### Core (existing, reuse)
| Library / Module | Purpose | Why |
|---|---|---|
| `app/services/canonical_slice_sql.py` | Ranked slice CTE text | D-07 mandates reuse; Stage A/B and CDF share it |
| `app/repositories/endgame_repository.py` | Entry/bucket/performance/clock/ELO rows | Already shaped per span/game with `time_control_bucket` |
| `app/services/score_confidence.py` (`compute_paired_difference_test`, `compute_score_difference_test`, `wilson_bounds`, `compute_confidence_bucket`) | CI / p-value for the popover footer | Project convention: Wilson + paired-z (memory: trust the established Wilson method) |
| `app/repositories/user_benchmark_percentiles_repository.fetch_for_user` / `user_rating_anchors_repository.fetch_anchors_for_user` | Persisted percentiles + anchors | Unchanged read path |
| Recharts (existing charts) | Score Gap / ELO / Clock Gap / pressure curve | Visual unchanged except grey band |
| TanStack Query | `useEndgameRankedStats` hook | Existing pattern (`useEndgameOverview`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Ranked ids + canonical-mode Python | Run the 11 `per_user_cte_*` builders on read | Exact by construction, but 1.5 to 9.6 s per TC on dev heavy users and HAVING floors drop below-floor values (D-09 needs them). Rejected. |
| Ranked ids + canonical-mode Python | Persist components in Stage A/B (SEED option) | Contradicts locked D-07 (compute on read) |
| New `/endgames/ranked-stats` | Extend `/endgames/overview` | The overview is filter-shaped; mixing filtered and ranked shapes reintroduces the dual-value problem D-01 kills |
| `RankedMetricOut` dict per TC | Reuse `PerTcBucketStats` / `TimePressureTcCard` | Those carry chip-basis duplicates (`percentile_value`, `rate_percentile_*`) and gauge-era fields; a uniform model makes the dot plot and popover trivial |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase, so the audit is not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
GET /api/endgames/ranked-stats  (auth: current_active_user; no query params)
        │
        ▼
endgame_ranked_service.get_ranked_stats(session, user_id)
        │
        ├─(1) for tc in bullet..classical:  canonical ranked-games SQL
        │        WITH selected_users(single_user) , recent_capped(tc)   ← canonical_slice_sql, unchanged
        │        SELECT id, played_at, platform, time_control_str, user_elo, evals_pending
        │        → RankedGames[tc]  (ids, non-daily count, pending-eval count, ≥800 id-set)
        │        (TCs with 0 ranked games dropped → D-14)
        │
        ├─(2) repository queries ONCE with game_ids = ∪ ranked ids  (apply_game_filters(game_ids=…))
        │        entry_rows (per game×class span, LEAD)   bucket_rows (per game)
        │        performance rows (eg / non-eg)           clock rows (ply+clock arrays)
        │        elo timeline rows (per platform×tc)
        │        → grouped by time_control_bucket in Python
        │
        ├─(3) persisted reads: fetch_for_user (percentiles), fetch_anchors_for_user
        │
        ├─(4) per TC, pure functions (no DB):
        │        canonical-mode metric values (11 families) ──► parity with Stage A/B CTEs
        │        components: eg/non-eg WDL, entry eval/expected/actual, bucket WDL,
        │                    quintile curve, clock summary, clock-diff timeline,
        │                    score-gap timeline, ELO combos, type categories
        │        CI/p per metric (score_confidence helpers)
        │        rank status per metric (ranked | below_floor | unranked | pending)
        │
        ▼
EndgameRankedStatsResponse { tcs: [RankedTcStats …] }
        │                                   │
        ▼                                   ▼
Frontend Stats tab (TC switch picks tc)   insights_service.compute_findings (D-04)
                                            all_time := ranked payload, last_3mo := same builders
                                            over ranked rows with played_at ≥ now-90d
                                            → insights_llm prompt v48 (no filters, no scoping caveat)
```

### Recommended Project Structure

```
app/services/canonical_slice_sql.py        # + ranked_games_sql(tc) composer (NEW function; existing builders untouched)
app/repositories/query_utils.py            # apply_game_filters(..., game_ids: Sequence[int] | None = None)
app/repositories/endgame_repository.py     # thread game_ids through the 5 row queries (+ push into inner subqueries for perf)
app/repositories/endgame_ranked_repository.py (or a function in endgame_repository) # execute ranked_games_sql per tc
app/services/endgame_ranked_service.py     # NEW: orchestration + canonical-mode metric helpers + rank status
app/schemas/endgames.py                    # + RankedMetricOut, RankedTcStats, EndgameRankedStatsResponse; − aggregated fields
app/routers/endgames.py                    # + GET /ranked-stats; GET /overview → GET /stats (filtered, Games tab)
app/services/insights_service.py           # compute_findings(session, user_id) over the ranked payload
app/routers/insights.py                    # drop filter query params + _validate_full_history_filters
app/services/insights_llm.py / app/prompts/endgame_insights.md   # v48: ranked framing, no scoping caveat
frontend/src/components/endgames/stats/   # (or charts/) PercentileBar, RankedMetricPopover, TcSwitch,
                                           #   ComparedToPeersCard, Overall*, MetricsCard, TimePressure*, TypeTable
frontend/src/hooks/useEndgameRankedStats.ts, useEndgameStatsTc.ts (store + localStorage)
frontend/src/pages/Endgames.tsx            # extract EndgameStatsTab; hide filter UI on stats
```

### Pattern 1: Canonical ranked games, composed not re-derived

**What:** a new exported function builds the id query from the **existing** private builders. No existing builder is edited, so the D-10 source-mode parity tests and the median-anchor A1 baseline test stay green by construction.
**When:** every on-read ranked computation.
```python
# Source: composes app/services/canonical_slice_sql.py:197-228 + :284-316 (both unchanged)
def ranked_games_sql(tc: TimeControlBucket) -> str:
    """Per-TC ranked sample (same games Stage A/B rank), with display columns.

    The WITH chain is byte-identical to the per_user_cte_* preludes; only the
    outer SELECT is new, so CDF-side / user-side parity (D-10) is untouched.
    """
    return (
        f"WITH {selected_users_cte(source='single_user')},\n"
        f"{_recent_capped_per_tc_cte(None, tc)}\n"
        "SELECT rc.id, rc.played_at, g.platform, g.time_control_str, "
        f"{_user_elo_at_game_expr()} AS user_elo, (g.evals_completed_at IS NULL) AS eval_pending\n"
        "FROM recent_capped rc JOIN games g ON g.id = rc.id"
    )
# executed in a repository with text(sql).bindparams(user_id=user_id)  (V5: never f-string user_id)
```
The outer SELECT columns (`platform`, `time_control_str`, `evals_completed_at`) are `[ASSUMED]` correct column names. `platform`/`time_control_str` appear verbatim in the anchor CTE (`canonical_slice_sql.py:1259` `WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')`) and `evals_completed_at` in `game_repository.py:201`, but the executor must confirm against `app/models/game.py`.

### Pattern 2: `game_ids` through the single filter seam

```python
# app/repositories/query_utils.py — add a keyword-only param (default None = unchanged behavior)
if game_ids is not None:
    stmt = stmt.where(Game.id == any_(cast(literal(list(game_ids)), ARRAY(Integer))))  # or Game.id.in_(…)
```
Callers on the ranked path pass `time_control=None, platform=None, rated=None, opponent_type="all", from/to=None, gap=None` so the id set alone defines the population. `platform=None` still adds `NOT IN ('flawchess','pgn')`, which is harmless because ranked games are rated and non-computer. **Performance:** the inner `GamePosition` subqueries in `query_endgame_entry_rows` / `query_endgame_bucket_rows` / `query_clock_stats_rows` aggregate **all** of the user's endgame positions before the outer join (`endgame_repository.py:206-225`, `:363-382`, `:826-840`). Push the same `GamePosition.game_id = ANY(:ids)` predicate into those inner subqueries. Avoid the `game_id IN (subquery)` form: the code comment at `endgame_repository.py:822-826` documents that form hanging the planner on users with many endgame games. [VERIFIED: endgame_repository.py:822-826 quote: "the IN form caused the planner to misestimate cardinality ... that hung indefinitely on users with many endgame games"]

### Pattern 3: Canonical-mode metric helpers, guarded by a parity test

Each of the 11 values must equal what `_compute_metric_for_user_per_tc(session, user_id, family, tc)` returns (`user_benchmark_percentiles_service.py:250-280`) whenever that returns a row. Required definition per family:

| Family (CdfMetricId) | Canonical definition (CTE) | Current Python divergence | On-read rule |
|---|---|---|---|
| `score_gap` | eg = ≥6 endgame plies; `avg(score|eg) − avg(score|¬eg)`; n = eg count; floor eg≥30 AND non-eg≥30 (`:610-650`) | none (`_any_endgame_ply_subquery` same rule) | reuse performance rows |
| `achievable_score_gap` | first endgame ply eval; mate→1/0; `abs(cp)<2000` sigmoid else NULL; n = non-null (`:670-730`) | none (`endgame_service.py:3083-3107` same filters) | reuse |
| `conversion_rate` / `parity_rate` / `recovery_rate` | per game first-endgame-ply eval, **excludes NULL-eval and user_elo<800** (`:897-898`, `:974-975`, `:1048-1049`) | `_classify_endgame_bucket` routes NULL→parity (`endgame_service.py:250-252`); no 800 floor | filter bucket_rows: drop NULL eval, drop ids with user_elo<800 |
| `score_gap_conv` / `score_gap_parity` / `recovery_score_gap` | per (game,class) span ≥6 plies, LEAD next-span eval, sub-800 excluded, NULL entry excluded (`:758-843`) | per-TC cards use per-game terminal bucket_rows (`endgame_service.py:2626-2672`) | use **entry_rows** per TC (`_accumulate_endgame_rows(...)["gaps_by_bucket"]`) on ≥800 ids |
| `time_pressure_score_gap` | user pct<0.40 avg score − opp pct<0.40 avg(1−score); n=least; no clamp; base>0, both pcts non-null (`:391-440`) | not computed; quintile path clamps at 2× base (`endgame_service.py:2209-2213`) | new helper over clock rows, no clamp |
| `clock_gap` | avg((u−o)/base), both clocks non-null, base>0, **no clamp** (`:464-499`) | clamp `MAX_CLOCK_PCT_OF_BASE = 2.0` (`endgame_service.py:1833`) | new helper, no clamp |
| `net_flag_rate` | over all ≥6-ply endgame games, `(timeout W − timeout L)/count`, **no base check** (`:529-564`) | denominator requires base>0 (`endgame_service.py:2191-2193`) | new helper, count every clock row |

[VERIFIED: canonical_slice_sql.py line ranges above, Read this session; endgame_service.py:250-252 quote: `if eval_mate is None and eval_cp is None:` / `return "parity"`; :1833 quote: `MAX_CLOCK_PCT_OF_BASE = 2.0`]

`n_games` must match too, because the copy shows "n of 30" and the popover shows n. Use the CTE's n definition for each family (eg count; non-null d_i; bucket count; least(nu,no); clock pool; endgame pool).

The quintile **curve** (not a peer-ranked metric) may keep the existing clamp semantics. Document that the curve and Clock Gap rows filter games slightly differently.

### Pattern 4: Uniform per-metric output and rank status (backend-owned)

```python
RankStatus = Literal["ranked", "below_floor", "unranked", "pending"]

class RankedMetricOut(BaseModel):
    metric: CdfMetricId
    value: float | None          # None only when not computable (pending evals / zero eligible)
    n: int                       # metric-relevant n (CTE definition)
    floor_n: int                 # binding count vs floor (e.g. min(eg, non_eg) for score_gap)
    floor_required: int          # 30 (from canonical constants)
    percentile: float | None     # persisted; None unless status == "ranked"
    status: RankStatus
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
```
Status derivation per (tc, metric):
1. TC has no anchor row: compute the non-daily ranked count. If it is below `MEDIAN_ANCHOR_MIN_GAMES`, status is `below_floor` and `floor_n` = that count. This is D-09's "(18 of 30)".
2. Metric is eval-dependent (`achievable_score_gap`, the 3 ΔES buckets, the 3 rates), the TC has `eval_pending > 0` and the value is not computable: status is `pending` (D-11).
3. Metric `floor_n < floor_required`: status is `below_floor`.
4. A persisted row exists with `percentile is not None`: status is `ranked`.
5. Otherwise status is `unranked` (Stage B row not yet written, or the CDF cell is missing or out of range). Show the value with a "not ranked yet" slot (D-11 last sentence).

The clock families (`clock_gap`, `net_flag_rate`, `time_pressure_score_gap`) are Stage B but **eval-independent**. Their value is always computable, so before Stage B they land in `unranked`, not `pending`. That matches D-11's "show the value with a not-ranked-yet slot".

### Pattern 5: One builder, two windows (insights)

`compute_findings` drops `FilterContext` filtering. It calls the ranked service once and derives `all_time` (the full ranked sample) and `last_3mo` (the same pure builders over ranked rows with `played_at ≥ now−90d`). That removes the second full DB pass today's code makes (`insights_service.py:160-183`). [VERIFIED: insights_service.py:160-183 — two sequential `get_endgame_overview` awaits]

### Pattern 6: Frontend TC switch store

A tiny module store (pattern like `useFilterStore`) or React context holds `selectedTc`. It initializes from `localStorage` (try/catch) and falls back to D-12 using `tcs[].ranked_games` + anchor presence from the payload. Every section renders `<TcSwitch>` bound to the same store (synced). Track a user change with `trackFeature('option-change', { target: 'endgame-stats-tc', value })`. That needs a new `OPTION_TARGETS` entry, which is `[ASSUMED]` naming. Never fire it on restore or mount (frontend CLAUDE.md D-03).

### Anti-Patterns to Avoid
- **Re-deriving the slice in SQLAlchemy** (`ROW_NUMBER() OVER (PARTITION BY time_control_bucket)` in Core): violates D-07 and drifts silently. Compose the canonical text instead.
- **Editing any `per_user_cte_*` / `_recent_capped_per_tc_cte` body** "for reuse": it breaks D-10 source-mode parity and the persisted-percentile basis. Add new functions only.
- **Displaying `PercentileRow.value`** as the headline: D-07 says compute on read. The stored value is only a parity-test oracle.
- **Calling the 11 CTEs per request:** measured at 1.5 to 9.6 s per TC (see Environment).
- **Computing `EndgameTimelineResponse` (`timeline`)** in the ranked payload: the frontend never reads it (`grep` finds only `types/endgames.ts:152-154,466` and one test fixture). Its row query is the one that hung on dev user 7.
- **A Stats-tab code path that reads `useFilterStore`:** D-01. Only the Games tab reads filters.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Ranked game selection | New SQL/ORM slice | `selected_users_cte` + `_recent_capped_per_tc_cte` composition | D-07 byte-identity; cap, recency and equal-footing semantics |
| CI / p-values | Ad hoc z math in services or TS | `score_confidence.py` helpers (`compute_paired_difference_test`, `compute_score_difference_test` incl. `shared_n`, `wilson_bounds`) | Established Wilson / paired conventions (memory) |
| Expected score from eval | Inline sigmoid | `eval_cp_to_expected_score` / `eval_mate_to_expected_score` (`eval_utils.py:65-115`; no clip, same as the CTE) | Same K constant as SQL |
| Percentile interpolation | Re-interpolating on read | Persisted `user_benchmark_percentiles` | D-07 |
| Typical bands | New hard-coded ranges | `PER_CLASS_TC_GAUGE_ZONES`, `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`, `NEUTRAL_PCT_THRESHOLD` from generated `endgameZones.ts` | Benchmarks are the source of truth; CI drift check |
| Popover shell | New hover/tap logic | Copy `MetricStatPopover`'s Radix shell (`HOVER_OPEN_DELAY_MS=100`, Portal, `side="top"`) + `useTrackedPopoverOpen` | Same UX + analytics |

**Key insight:** the dangerous part of "compute on read" is not the SQL but **definition drift**. Three code paths (CDF build, Stage A/B, on-read) must agree. Only a numeric parity test catches a NULL-eval or clamp mismatch.

## Runtime State Inventory

This is a refactor/retirement phase (the cache contract and endpoints change).

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | `llm_logs` rows keyed by `(user_id, prompt_version, model, filter_context->>'opponent_strength')` (`llm_log_repository.py:163-205`); rows cached under v47 narrate filtered all-history values | Bump `_PROMPT_VERSION` to `endgame_v48` (only invalidation lever, per the v47 comment). Code edit, no migration. Keep `LlmLogFilterContext.opponent_strength` and write a constant (`[ASSUMED]` choice "any"); no DB migration needed |
| Stored data | `user_benchmark_percentiles` / `user_rating_anchors` | None. Read-only, semantics unchanged |
| Live service config | None. No external dashboards key on endpoint names; Umami panel targets `endgame-type-tc` / `endgame-metrics-tc` / `time-pressure-tc` simply stop firing (do not rename or delete history) | None (optional: leave the targets in `PANEL_TARGETS`) |
| OS-registered state | None. Verified there is no cron or systemd entry tied to endgame endpoints (the deploy is docker via `bin/deploy.sh`) | None |
| Secrets/env vars | None | None |
| Build artifacts | `frontend/src/generated/endgameZones.ts` (CI `git diff --exit-code` after `scripts/gen_endgame_zones_ts.py`, `.github/workflows/ci.yml:54-55`); the TanStack cache key `['endgameOverview']` is invalidated in `App.tsx:1052` and `Import.tsx:209,413`, guarded by `Import.endgameOverviewInvalidation.test.ts` | Put the new query key under the `['endgameOverview', …]` prefix (e.g. `['endgameOverview','ranked']`) so the existing partial-match invalidations cover it, OR add new invalidations and update the regex test |

## Common Pitfalls

### Pitfall 1: Headline value ≠ percentile basis
**What goes wrong:** the card prints a rate computed with NULL-eval games counted as parity, or with the 2× clock clamp, while the persisted percentile ranks the CTE value.
**Why:** five definitional divergences (Pattern 3 table).
**How to avoid:** canonical-mode helpers plus a DB-backed parity test over a seeded user with NULL-eval games, sub-800 games, >2× clocks, base_time NULL games and multi-class spans.
**Warning signs:** the parity test needs a tolerance larger than float epsilon.

### Pitfall 2: Byte-identity regressions
**What goes wrong:** someone "DRYs" a `per_user_cte_*` body or `_recent_capped_per_tc_cte`.
**How to avoid:** Wave 0 adds a golden snapshot test that hashes every existing builder's output for all TCs and both sources and checks it against a committed baseline. The existing tests only assert benchmark==single_user equality (`test_canonical_slice_per_user_vs_benchmark_parity.py`), plus one byte baseline for the non-blend median anchor (`test_canonical_slice_sql.py:946`). A same-on-both-sides edit would pass them.

### Pitfall 3: Per-metric floors differ from the anchor floor
**What goes wrong:** "(18 of 30)" shows the anchor count for a metric that is actually blocked by its own floor (e.g. 22 endgame games, or score_gap's non-endgame floor), or by the dual floor on time pressure.
**How to avoid:** the backend emits `floor_n` = the binding count per metric. score_gap needs min(eg, non_eg); time_pressure needs least(user_pressured, opp_pressured).

### Pitfall 4: Chess.com Daily
The ranked slice (`recent_capped`) includes chess.com Daily games, but the anchor excludes them (`canonical_slice_sql.py:1255-1260`). The anchor floor count must exclude Daily (`time_control_str LIKE '1/%'`), while metric values include them, exactly as Stage A/B does. [VERIFIED: canonical_slice_sql.py:1255-1260]

### Pitfall 5: Filter UI hidden but state lost
**What goes wrong:** passing `panels=[]` to `SidebarLayout` on Stats while `sidebarOpen === 'filters'` leaves a dangling active panel. The empty strip may also shift content width between tabs.
**How to avoid:** close the panel (`setSidebarOpen(null)`) and the mobile drawer on a tab change to Stats. Never call `setAppliedFilters` on hide. Check the desktop strip width at md and lg, plus the mobile sticky Filters row (`Endgames.tsx:996-1010`).

### Pitfall 6: Games tab silently loses its data
`gamesContent` reads `statsData` from the overview (`selectedCategoryStats`, `statsData.endgame_games`, `Endgames.tsx:818-859`). Retiring `/overview` without the filtered `/stats` replacement breaks `PositionResultsPanel` and the match label.

### Pitfall 7: Insights golden prompt
`tests/services/test_insights_llm.py:874-887` says the golden "is never regenerated to match a post-refactor output". This phase **intentionally** changes the prompt, so the plan must state the deliberate golden regeneration with justification. Do not "fix the code to match the golden".

### Pitfall 8: Endgames page complexity baseline
`EndgamesPage` sits at the eslint complexity baseline (comments at `Endgames.tsx:54-61, 77-85`). Extract an `EndgameStatsTab` component, and with it the insights state, instead of adding branches.

### Pitfall 9: Default-TC effect firing analytics
D-12 fallback logic in a `useEffect` must not call `trackFeature`. Only the switch's click handler tracks (frontend CLAUDE.md "never on mount or state restore").

### Pitfall 10: Timeline semantics change
The ranked timelines contain at most 3000 games per TC over 36 months, with no pre-fill from older games. The first ~10 points drop under `MIN_GAMES_FOR_TIMELINE`. That is expected; do not "fix" it by widening the sample. The ELO timeline shows ≤2 combos (chess.com + lichess) for the selected TC.

### Pitfall 11: dev clock rule
CLAUDE.md asks time-dependent endpoints to use `dev_now_utc`. The canonical window uses SQL `NOW()`, and so do Stage A/B. Keep `NOW()` so on-read stays byte-identical to the persisted basis, and comment the exception in the endpoint. `[ASSUMED]` acceptable; confirm with the owner if dev-clock testing of the 36-month edge matters.

## Code Examples

### Rank-status helper (shape)
```python
# Source: design for this phase; floors from canonical_slice_sql.py:119-152
def _rank_status(
    *, has_anchor: bool, anchor_n: int, eval_dependent: bool, value: float | None,
    eval_pending: int, floor_n: int, floor_required: int, row: PercentileRow | None,
) -> tuple[RankStatus, int]:
    if not has_anchor and anchor_n < MEDIAN_ANCHOR_MIN_GAMES:
        return "below_floor", anchor_n
    if eval_dependent and value is None and eval_pending > 0:
        return "pending", floor_n
    if floor_n < floor_required:
        return "below_floor", floor_n
    if row is not None and row.percentile is not None:
        return "ranked", floor_n
    return "unranked", floor_n
```

### Parity test (shape)
```python
# tests/services/test_endgame_ranked_parity.py  (DB-backed; reuse _seed_canonical_slice_user from
# tests/services/test_user_benchmark_percentiles_service_real_data.py:160 and extend the seed with
# NULL-eval, sub-800, >2x-clock, NULL-base, multi-class-span and out-of-window games)
@pytest.mark.parametrize("family", ("score_gap",) + STAGE_B_METRIC_FAMILIES)
async def test_on_read_value_matches_canonical_cte(seeded_user, family):
    async with session_maker() as s:
        oracle = await _compute_metric_for_user_per_tc(s, user_id, family, "blitz")
        ranked = await get_ranked_stats(s, user_id)
    m = _tc(ranked, "blitz").metrics[family]
    assert oracle is not None
    assert m.value == pytest.approx(oracle[0], abs=1e-9)
    assert m.n == oracle[1]
```

## State of the Art

| Old Approach | Current Approach (this phase) | Impact |
|---|---|---|
| Filtered whole-history value + zone color + peer chip on a different sample + z-test verdict | Ranked value + percentile bar (one verdict) | Values and percentile describe the same games |
| Game-count-weighted cross-TC chip (`_aggregate_per_tc_percentile`, `endgame_service.py:1509`) | Per-TC only | `score_gap_percentile`, `achievable_score_gap_percentile`, `score_gap_per_tc`, `achievable_score_gap_per_tc`, `PerTcBreakdownOut` retire |
| Insights keyed per opponent_strength preset, filters gated with 400s | One report per user, ranked sample | `_validate_full_history_filters`, `toInsightsFilters`, `insightsFilters.ts`, filter query params retire |
| Gauges (`EndgameGauge`), per-bin red/blue/green zones | WDL bracket; grey typical band | `EndgameGauge`, `PercentileChip`, `MetricStatPopover`, `MetricStatTooltip`, `AchievableScorePopover` likely become dead. `MiniBulletChart` stays (Openings, Library, PositionResultsPanel use it) |

**Corrections to SEED-196 / CONTEXT assumptions:**
- "Knip will flag dead zone exports in `generated/endgameZones.ts`": **false**. `knip.json:18` ignores that file. Prune generator emissions only by choice (keep the generator docstring "Only constants with an FE consumer are emitted" honest). [VERIFIED: frontend/knip.json:14-20, quote: `"src/generated/endgameZones.ts",`]
- `MetricStatPopover` is referenced by `FlawBulletPopover.tsx` and `PersonaEloDisclosurePopover.tsx` **only in comments** ("Mirrors the endgame MetricStatPopover shell"), so it can be deleted once the endgame callers move. Update those comments. [VERIFIED: grep this session]
- D-11 "pending" is rarer than CONTEXT implies. The whole Endgames page is locked until `tier2` (`Endgames.tsx:870-872`), which needs `pending == 0` and no Stage B compute in flight (`app/routers/imports.py` `get_readiness`). Guests receive tier-1 entry evals (`count_pending_evals` keys on `evals_completed_at`), so they also unlock. The `pending` state mainly covers race windows and engine-error NULL evals. Still implement it, but it is not the common path. [VERIFIED: app/routers/imports.py readiness body; game_repository.py:196-203]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Endpoint names `GET /endgames/ranked-stats` and filtered `GET /endgames/stats` | Summary / Structure | Cosmetic; rename freely |
| A2 | `RankedMetricOut` / `RankedTcStats` field shapes | Pattern 4 | Planner may reshape; the status semantics are what matters |
| A3 | Column names `g.platform`, `g.time_control_str`, `g.evals_completed_at` in the outer SELECT | Pattern 1 | SQL error caught by the first test run |
| A4 | Write a constant `opponent_strength` ("any") into `LlmLogFilterContext` instead of migrating the JSON shape | Runtime State | Cache-key semantics only; prompt-version bump invalidates anyway |
| A5 | Insights overall-section findings become per-TC (`dimension={"time_control": tc}`) to mirror the per-TC UI | Open Q1 | If the owner prefers pooled-ranked overall findings, Shelly's overall numbers will not appear on the page |
| A6 | `last_3mo` = ranked rows with `played_at ≥ now−90d` (keeps the shift-line machinery) | Pattern 5 | Alternative is dropping last_3mo, which means a larger prompt rewrite |
| A7 | Popover footer per metric: rates use Wilson CI only (no p); score_gap uses the two-sample CI+p vs 0; ΔES gaps, achievable and clock_gap use paired CI+p; time_pressure uses the two-sample with `shared_n`; net_flag_rate shows n only | Discretion | Copy/stat choice; low risk |
| A8 | New analytics target `option-change` / `endgame-stats-tc` | Pattern 6 | Naming only; must not rename existing targets |
| A9 | Keep SQL `NOW()` (not `dev_now_utc`) for the ranked window | Pitfall 11 | Dev-clock testing of the 36-month boundary impossible |
| A10 | Perf of the ranked path: about the "ranked-approx" filtered overview (3.4 s, user 14), reducible by pushing ids into inner subqueries | Environment | If still slow, add per-request caching keyed on (user_id, last import/eval timestamp) |

## Open Questions

1. **Per-TC or pooled overall findings for Shelly?**
   - What we know: D-04 requires narrated numbers to come from the ranked sample. The UI is per-TC only (D-00h). Today `endgame_start_vs_end` / `score_gap` / `score_timeline` are pooled findings.
   - What's unclear: whether the owner wants per-TC overall narration (it mirrors the page) or one pooled ranked number (which appears nowhere on the page).
   - Recommendation: per-TC, using `dimension={"time_control": tc}` the way `endgame_metrics_<tc>` already works. Flag it in the plan as an owner confirmation at plan review.
2. **Does `last_3mo` survive?**
   - Recommendation: keep it as a ranked-row subset (A6). That keeps `_summary_shift_line` and the guardrails intact and limits the prompt edit to window-meaning text and dropping the scoping caveat (`endgame_insights.md:141,204`).
3. **Is the AI-SPEC workflow required?** `workflow.ai_integration_phase: true` in `.planning/config.json`, and this phase edits the prompt and payload. The planner should decide whether `/gsd-ai-integration-phase` applies. Minimum: keep the existing prompt tests green (`tests/prompts/test_endgame_insights_prompt.py`, `test_insights_llm.py`) and do one live smoke generate on dev during UAT.
4. **Perf on the heaviest prod accounts.** Measure `/endgames/ranked-stats` on dev user 7 (67k games) after the inner-subquery id push. If it exceeds about 3 s, consider caching.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Dev PostgreSQL (docker `flawchess-dev-db-1`) | backend tests, parity test, perf probe | ✓ | PG 18 (healthy) | — |
| Benchmark DB (`flawchess-benchmark-db-1`) | not required (CDF is already persisted) | ✓ | — | — |
| Python / uv | backend | ✓ | 3.14.3 / uv 0.10.9 | — |
| Node | frontend | ✓ | v24.19.0 | — |
| Chrome extension | desktop + mobile UAT | owner's Chrome (memory: run UAT yourself) | — | — |

**Measured on the dev DB this session** [VERIFIED: probe scripts run against dev DB]:
- Canonical ranked-id query per TC: 3 to 48 ms (one 424 ms first-hit outlier).
- Running all 11 `_compute_metric_for_user_per_tc` CTEs per TC: user 14 (22.5k games) 1.7 to 2.0 s per TC; user 7 (67k games) 4.9 s (bullet) and 9.6 s (blitz, only 292 ranked games). **Too slow for on-read.**
- Existing `get_endgame_overview`, user 14: 6.0 s with default filters, 3.4 s with a ranked-approximating filter (36 mo, ±100).
- Existing overview, user 7: did not finish in more than 4 minutes. The stuck statement was the 3-column `SELECT games.played_at, games.result, games.user_color` (the `timeline` rows query), cancelled by hand.

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Backend | pytest (async, per-session cloned PG DB; `tests/conftest.py`) |
| Frontend | vitest (`vite.config.ts` test block; `src/vitest.setup.ts`) |
| Quick run (backend) | `uv run pytest tests/services/test_endgame_ranked_service.py tests/services/test_endgame_ranked_parity.py -x` |
| Quick run (frontend) | `cd frontend && npx vitest run src/components/endgames` |
| Full suite | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Decision → Test Map
| ID | Behavior | Type | Automated Command | Exists? |
|---|---|---|---|---|
| D-07 | Existing builders unchanged (golden hash of every `per_user_cte_*` / `_recent_capped_per_tc_cte` output × TC × source) | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -k golden -x` | ❌ Wave 0 |
| D-07 | `ranked_games_sql(tc)` WITH-chain equals the canonical prelude; bindparam detected | unit | `uv run pytest tests/services/test_canonical_slice_sql.py -k ranked_games -x` | ❌ Wave 0 |
| D-00b/D-07 | On-read value and n == Stage A/B CTE oracle for 11 families (seed incl. NULL eval, sub-800, >2× clock, NULL base, multi-class spans, out-of-window, ±100-violating) | integration (DB) | `uv run pytest tests/services/test_endgame_ranked_parity.py -x` | ❌ Wave 0 |
| D-00b | WDL/rate consistency: rate == wins/n (conv), (W+D/2)/n (parity), (W+D)/n (recovery) from the same bucket counts | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k bucket -x` | ❌ |
| D-09/D-10/D-11 | Rank status matrix: no anchor → below_floor(anchor_n); pending; per-metric floor; ranked; unranked; empty ranked sample → `tcs == []` | unit | `uv run pytest tests/services/test_endgame_ranked_service.py -k status -x` | ❌ |
| D-14 | Zero-game TCs omitted, order bullet→classical | unit | same file `-k tcs_listed` | ❌ |
| D-01 | `/endgames/ranked-stats` takes no filter params; result is identical for any query string; auth required | router | `uv run pytest tests/test_endgames_router.py -k ranked -x` | ❌ (rewrite) |
| D-00h | Aggregated fields absent from schema (`score_gap_percentile`, `achievable_score_gap_percentile`, `*_per_tc`, `PerTcBreakdownOut`) | schema | `uv run pytest tests/schemas/test_endgames_schema.py -x` | ⚠ rewrite |
| Games tab | Filtered `/endgames/stats` returns categories + counts under filters | router | `uv run pytest tests/test_endgames_router.py -k stats -x` | ❌ |
| D-04 | Insights router accepts no filters; no 400 `filters_not_supported`; cache key constant; v48 | router/service | `uv run pytest tests/test_insights_router.py tests/services/test_insights_llm.py -x` | ⚠ rewrite |
| D-04 | Findings values == ranked payload values (all_time) per TC; last_3mo == subset | service | `uv run pytest tests/services/test_insights_service.py -x` | ⚠ rewrite |
| D-04 | Prompt golden deliberately regenerated; no "Scoping caveat" | unit | `uv run pytest tests/services/test_insights_llm.py -k golden -x; uv run pytest tests/prompts -x` | ⚠ regen |
| D-00a | PercentileBar: band 25-75, median tick, dot color red/blue/green at 24/25/75/76, values uncolored, **no flame icon** | component | `npx vitest run src/components/endgames/stats/PercentileBar.test.tsx` | ❌ |
| D-00c | Popover: WHAT+sign, percentile sentence, 4 disclosures (3 anchor-composition branches), grey stats footer below separator | component | `npx vitest run .../RankedMetricPopover.test.tsx` | ❌ |
| D-09/D-11 | Slot copy: "Not enough games to rank yet (n of 30)" (no dot), pending line, not-ranked-yet slot | component | same as above `-t status` | ❌ |
| D-00d | Metrics card: no gauge; bracket spans W (conv) / W+D (recov) / score (parity) | component | `npx vitest run .../MetricsCard.test.tsx` | ❌ |
| D-00e | Type table: grey range + white tick, amber below typical, no red/green, rows <100 games faded, stacked on mobile | component | `npx vitest run .../TypeTable.test.tsx` | ❌ |
| D-00f | Clock timeline + pressure curve: one grey band, neutral line/dots (no zoneColor) | component | `npx vitest run src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx` | ⚠ update |
| D-00g | Dot plot: 11 rows for selected TC, grouped, links to section anchors; hidden when TC unranked | component | `npx vitest run .../ComparedToPeersCard.test.tsx` | ❌ |
| D-00h/D-12/D-13/D-14 | Synced switch across sections; default = most games, tie→faster, prefer above-floor; localStorage restore with try/catch; stale stored TC falls back; no trackFeature on restore | hook/component | `npx vitest run src/hooks/__tests__/useEndgameStatsTc.test.ts` | ❌ |
| D-02 | Filter sidebar + mobile Filters button hidden on Stats, shown on Games; applied filters unchanged after round trip | page | `npx vitest run src/pages/__tests__/Endgames.filterVisibility.test.tsx` | ❌ |
| D-10 | Empty ranked sample → one empty state naming rated / human / ±100 / 36 months + Games-tab link | page | same page test `-t empty` | ❌ |
| D-04 (FE) | Insights hook sends no filter params; single cached report; `toInsightsFilters` gone | hook | `npx vitest run src/hooks/__tests__/useEndgameInsights.test.tsx` | ⚠ rewrite |
| Invalidation | Ranked query key invalidated on import completion | static | `npx vitest run src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts` | ⚠ update if key changes |
| D-00i | Score Gap over Time + ELO Timeline visuals unchanged (data source only) | component | existing `EndgameScoreOverTimeChart` / `EndgameEloTimelineSection` tests | ✅ |
| Manual | Desktop + mobile UAT on dev (Chrome extension), popover on tap, stacked type rows, switch sync | manual | — | owner-run per memory |

### Sampling Rate
- **Per task commit:** the quick-run file(s) for the touched layer.
- **Per wave merge:** `uv run pytest -n auto -x` + `cd frontend && npm run build && npm test -- --run`.
- **Phase gate:** full pre-merge gate (CLAUDE.md), plus one serial `uv run pytest -x` before release.

### Wave 0 Gaps
- [ ] `tests/services/test_canonical_slice_sql.py`: golden hash baseline of all existing builder outputs (capture **before** any edit).
- [ ] `tests/services/test_endgame_ranked_parity.py` + extended seed helper (NULL eval, sub-800, clocks incl. >2× base, NULL base_time, multi-class spans, out-of-window and out-of-band games, chess.com Daily for the anchor count).
- [ ] `tests/services/test_endgame_ranked_service.py` (status matrix, bucket/WDL consistency, TC listing).
- [ ] Frontend test files listed above (new components + hook + page filter visibility).

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | yes | `current_active_user` dependency on the new endpoint (FastAPI-Users) |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | `user_id` only from the auth dependency, never a query param (existing V4 convention in `fetch_for_user`) |
| V5 Input Validation | yes | No user input on `/ranked-stats`. `tc` interpolation is limited to the 4-value `TimeControlBucket` Literal; `user_id` goes through `CAST(:user_id AS int)` bindparam only (`canonical_slice_sql.py:228`) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| SQL injection via f-string SQL composition | Tampering | Only Literal `tc` and Python-controlled ints are interpolated; `user_id` via bindparam (never f-string); `game_ids` passed as a bound array |
| Cross-user data exposure | Information disclosure | All repository calls scoped by the authenticated `user_id`; ranked ids come from a `selected_users` CTE bound to that id |
| DoS via expensive on-read queries | Denial of service | Ranked sample capped at 3000/TC; push ids into inner subqueries; drop the dead `timeline` query; 5-min `staleTime` on the frontend |

## Recommended Plan Split (Claude's discretion)

1. **Plan 01, Backend ranked payload (Wave 1).** Wave 0 tests (golden builder hashes, parity seed); `ranked_games_sql`; `game_ids` seam in `apply_game_filters` plus the inner-subquery push; `endgame_ranked_service.py` (canonical-mode helpers, components, timelines, type categories, rank status, CI/p); schemas; `GET /endgames/ranked-stats`; filtered `GET /endgames/stats` for the Games tab. Gate: parity test green, perf probe on dev users 7 and 14.
2. **Plan 02, Insights D-04 (Wave 2, depends on 01).** `compute_findings(session, user_id)` over the ranked service (per-TC overall findings, last_3mo subset); router drops filter params and `_validate_full_history_filters`; cached endpoint without filters; `LlmLogFilterContext` constant; prompt text (ranked framing, remove scoping caveat and filter references); `_PROMPT_VERSION = "endgame_v48"`; deliberate golden regen; rewrite tests.
3. **Plan 03, Frontend rework (Wave 2, can run alongside 02 once the 01 schema is fixed).** Types; `useEndgameRankedStats`; TC store + `localStorage`; `PercentileBar`, `RankedMetricPopover`, `TcSwitch`, `ComparedToPeersCard`; Overall (2 cards), Metrics cards (bracket, no gauge), Time Pressure (grey bands), Type table; extract `EndgameStatsTab`; hide filters on Stats (D-02); D-10 empty state; insights hooks without filters; concepts accordion copy; theme constants; analytics target.
4. **Plan 04, Retirement + gate + UAT (Wave 3).** Delete `get_endgame_overview` and `/endgames/overview`, the aggregated-chip helpers (`_aggregate_per_tc_percentile`, `_build_per_tc_breakdown`, `_per_tc_game_counts`), dead schemas/types, `EndgameGauge` / `PercentileChip` / `MetricStatPopover` / `MetricStatTooltip` / `AchievableScorePopover` / `EndgameTypeCard` / `EndgameTypeTcCard` / `EndgameOverallScoreGapRow` and their tests (keep `MiniBulletChart`), and `insightsFilters.ts`. Optionally prune the zone generator. Then CHANGELOG, the full pre-merge gate, and desktop + mobile UAT.

Risks: definition drift (mitigated by the parity test); heavy-account latency (measure); the LLM prompt change (golden + smoke); a broken Games tab (Plan 01 ships `/stats` before Plan 04 deletes `/overview`).

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/canonical_slice_sql.py` (full): constants 119-158, `_recent_capped_per_tc_cte` 284-316, all `per_user_cte_*` builders, anchor 1117-1346
- `app/services/user_benchmark_percentiles_service.py` (full): Stage A/B families 141-164, `_compute_metric_for_user_per_tc` 250-280, semaphore 173
- `app/schemas/endgames.py` (full): retiring fields 58-91, 340-348, 531-543, 977-1008
- `app/services/endgame_service.py` 200-680, 1440-3817: bucket classifier, per-TC cards, clock aggregation, performance, overview orchestration
- `app/repositories/endgame_repository.py` 1-450 + 790-878; `app/repositories/query_utils.py` (full)
- `app/services/insights_service.py` 1-1340; `app/routers/insights.py` (full); `app/services/insights_llm.py` 80-100, 1854-1900; `app/schemas/llm_log.py` 27-37; `app/core/opponent_strength.py`
- `frontend/src/pages/Endgames.tsx` (full); `frontend/knip.json`; `frontend/src/lib/analytics.ts` 355-500; `frontend/src/generated/endgameZones.ts`; `frontend/src/App.tsx` 1035-1053
- `.planning/seeds/SEED-196-...md`, `.planning/sketches/009-.../README.md` + `index.html`, `238-CONTEXT.md`
- Dev DB probes (this session): ranked-id timings, 11-CTE timings, overview timings

### Secondary
- Memory notes: percentile tooltip disclosure contract, percentile as the primary narration signal, no flame icons, frontend no-Prettier, tsc via `npm run build`

### Tertiary
- None

## Metadata

**Confidence breakdown:**
- Codebase map / retirement inventory: HIGH (read + grep)
- Definitional divergences: HIGH (both SQL and Python read side by side). The exact parity of edge cases still needs the Wave 0 test.
- Response schema / plan split: MEDIUM (design recommendation, under Claude's discretion)
- Performance: MEDIUM (dev DB measurements; prod data distribution may differ)

**Research date:** 2026-10-11
**Valid until:** 2026-11-10 (stable internal codebase; re-check if Stage A/B or canonical_slice_sql change)
