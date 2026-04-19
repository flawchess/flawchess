# Phase 57: Endgame ELO — Timeline Chart - Research

**Researched:** 2026-04-18
**Domain:** Backend aggregation + Recharts line chart (FlawChess codebase — internal patterns)
**Confidence:** HIGH (all critical findings verified in-repo; no external library uncertainty since the phase reuses existing project patterns)

## Summary

Phase 57 adds a paired-line timeline chart to the Endgames tab that tracks Endgame ELO (bright line, performance rating derived from Endgame Skill) vs Actual ELO (dark line, actual user rating trajectory) per qualifying (platform, time-control) combo. All algorithmic decisions are already LOCKED in 57-CONTEXT.md (formula, windowing, thresholds, chart shape) and all visual decisions are LOCKED in 57-UI-SPEC.md (palette, axis helper, legend mobile layout, info popover copy). This is a low-uncertainty phase: the planner's job is to turn locked specs into tasks, not to redesign.

The biggest planning decisions left open are: (a) the boundary between Phase 56 (already committed to porting `endgame_skill()` to the backend + breakdown endpoint) and Phase 57 (timeline endpoint), (b) the exact query shape for co-computing `endgame_skill` + `avg_opp_rating` + `avg(user_rating)` on aligned weekly timestamps across up to 8 combos, and (c) whether Phase 57 self-contains its backend computation or depends on a Phase-56-introduced helper. CONTEXT.md explicitly permits either approach; based on existing patterns in `endgame_service.py`, the cleanest path is a new `_compute_eg_elo_weekly_series(combo)` helper alongside `_compute_weekly_rolling_series`, invoked per-combo in a new `get_endgame_elo_timeline` orchestrator.

**Primary recommendation:** Extend `EndgameOverviewResponse` with an `endgame_elo_timeline: EndgameEloTimelineResponse` field served from the existing `/endgames/overview` endpoint (one extra section of data in the same single request — consistent with how Phase 52 consolidated four separate endpoints into one). Build a parallel but independent helper `_compute_endgame_elo_weekly_series` rather than trying to shoehorn paired-line logic into `_compute_weekly_rolling_series` — the latter is win-rate-specific and would need too many parameters to generalize cleanly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Endgame ELO formula computation (skill, clamp, log-odds) | API / Backend | — | Pure function on already-fetched rows; lives in `app/services/endgame_service.py` next to `_compute_weekly_rolling_series`. Frontend only renders. |
| Per-game rolling window accumulation | API / Backend | — | Same pattern as `_compute_score_gap_timeline` and `_compute_clock_pressure_timeline` — Python-side chronological walk over DB rows. |
| Per-combo partitioning (8 combos max) | API / Backend | — | Data is segmented server-side so the payload is already grouped by combo when the frontend receives it; frontend doesn't do SQL-like partitioning. |
| Filter restriction (sidebar → visible combos) | API / Backend | Browser / Client | Backend applies `apply_game_filters()` (source of truth). Frontend only passes filter params — does not re-filter the backend response. |
| Min-games threshold (≥ 10 endgame games per window) | API / Backend | — | Threshold enforcement sits inside the weekly-series helper so silently-dropped points never reach the wire. |
| Legend toggle (hide/show combo) | Browser / Client | — | Pure UI state (`hiddenKeys: Set<string>`) — no server round-trip. Matches existing `EndgameTimelineChart` pattern. |
| Y-axis tick computation (`niceEloAxis`) | Browser / Client | — | Recomputed per legend toggle (different combos visible → different rating range). Pure function, new helper in `frontend/src/lib/utils.ts`. |
| Cold-start empty-state detection | Browser / Client | — | Frontend checks `eloTimelineData.combos.length === 0` after filter; renders the empty-state markup. Backend guarantees no under-threshold points are emitted. |
| TanStack Query fetching | Browser / Client | — | Extends existing `useEndgameOverview` — no new hook. Phase 57 data piggybacks on the consolidated `/overview` response. |

## Standard Stack

### Core (all already in the codebase — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x [VERIFIED: pyproject.toml, phase stack] | Router + dependency injection | Already mounted at `/api/endgames` |
| SQLAlchemy async | 2.x [VERIFIED: CLAUDE.md] | DB layer for timeline row queries | Existing pattern throughout repos |
| Pydantic | v2 [VERIFIED: CLAUDE.md] | Response schema validation | Existing pattern in `app/schemas/endgames.py` |
| Recharts | ^2.15.4 [VERIFIED: frontend/package.json] | Line chart rendering | Already powering `EndgameTimelineChart`, `RatingChart`, `ClockPressureTimelineChart` |
| @tanstack/react-query | ^5.90.21 [VERIFIED: frontend/package.json] | Data fetching, caching, `isError` | Existing pattern in `useEndgames.ts` (`useEndgameOverview`) |

### Supporting (reused as-is — new `niceEloAxis` helper is pure arithmetic, not a new library)

| Item | Location | Purpose | When to Use |
|------|----------|---------|-------------|
| `_compute_weekly_rolling_series` | `app/services/endgame_service.py:1290` [VERIFIED: grep] | Reference pattern for ISO-week bucketing + trailing rolling window | Copy structure, swap the win-rate accumulator for Endgame-ELO accumulator |
| `MIN_GAMES_FOR_TIMELINE = 10` | `app/services/openings_service.py:43` [VERIFIED: grep] | Per-point threshold | Reuse verbatim (D-06) |
| `SCORE_GAP_TIMELINE_WINDOW = 100` / `CLOCK_PRESSURE_TIMELINE_WINDOW = 100` | `app/services/endgame_service.py:167, 826` [VERIFIED: grep] | Precedent for 100-game window | Add `ENDGAME_ELO_TIMELINE_WINDOW = 100` matching these |
| `user_rating_expr` case statement | `app/repositories/stats_repository.py:63-66` [VERIFIED: read] | White/black rating → user-perspective rating | Lift the `case(...)` into a helper or copy into new repo function for `avg(user_rating)` per combo |
| `apply_game_filters` | `app/repositories/query_utils.py:13` [VERIFIED: read] | Canonical filter application | Every new repo query MUST go through this; CLAUDE.md prohibits duplicating filter logic |
| `recency_cutoff` | `app/services/openings_service.py:76` [VERIFIED: grep] | Recency filter → datetime | Use for the recency cutoff param |
| `derive_user_result` | `app/services/openings_service.py:55` [VERIFIED: read] | PGN result → win/draw/loss | Not needed for ELO (we don't derive outcomes, we average ratings) — only for computing skill's Conv/Parity/Recovery rates |
| `endgameSkill()` helper | `frontend/src/components/charts/EndgameScoreGapSection.tsx:167-177` [VERIFIED: read] | Current frontend-only composite | Phase 56 ports to backend; Phase 57 consumes the backend version |
| `ChartContainer` / `ChartLegend` / `ChartLegendContent` with `hiddenKeys` + `onClickItem` | `frontend/src/components/ui/chart.tsx:107-169` [VERIFIED: read] | shadcn chart primitives with per-item toggle | Reuse verbatim; `onClickItem` wiring already exists |
| `InfoPopover` | `frontend/src/components/ui/info-popover.tsx` [VERIFIED: existence check] | Help icon with tooltip | Reuse verbatim |
| `createDateTickFormatter` + `formatDateWithYear` | `frontend/src/lib/utils.ts:29, 48` [VERIFIED: read] | X-axis + tooltip date formatting | Reuse verbatim |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Decision |
|------------|-----------|----------|----------|
| Reuse `_compute_weekly_rolling_series` directly | Parameterize it with a callable accumulator | Generalization adds complexity to a function 4 other callers depend on | **Rejected** — build parallel `_compute_endgame_elo_weekly_series` alongside it |
| New dedicated `/endgames/elo-timeline` endpoint | Piggyback on `/endgames/overview` | Two endpoints = two round trips + more frontend state | **Piggyback** — Phase 52 consolidated to one endpoint on purpose; stay consistent |
| Per-combo Elo computed on a single row pass | Pre-fetch all games once, partition in Python by `(platform, time_control_bucket)` | Single-pass SQL with group-by per combo is more DB work; Python partition is O(N) over already-fetched rows | **Python partition** — matches how `_compute_weekly_rolling_series` walks a pre-sorted list; DB load stays cheap since filters drop to one table scan |
| Opacity modifier on bright line for dark line | Two theme constants (`bright`, `dark`) | Opacity composites toward black on dark surface and weakens the "same hue family" read | **Two constants** (LOCKED in 57-UI-SPEC.md) |
| Single shared `Set<lineKey>` for 16 lines | Single `Set<comboKey>` toggling both lines of that combo as a unit | Per-line toggle means 16 independent toggles — confusing UX | **Combo-level toggle** (LOCKED in 57-UI-SPEC.md) |

**No new installations:** All packages already in `pyproject.toml` and `frontend/package.json`. [VERIFIED]

**Version verification:**
- `recharts@2.15.4` [VERIFIED: `frontend/package.json`]
- `@tanstack/react-query@5.90.21` [VERIFIED: `frontend/package.json`]
- `fastapi 0.115.x`, `sqlalchemy 2.x`, `python-chess 1.10.x`, `pydantic v2` [VERIFIED: CLAUDE.md §Tech Stack]

## Architecture Patterns

### System Architecture Diagram

```
Sidebar filters (applied)
        |
        v
useEndgameOverview (TanStack Query)
        |
        v
GET /api/endgames/overview?time_control=...&platform=...&recency=...&rated=...&opponent_type=...&opponent_strength=...
        |
        v
endgame_service.get_endgame_overview
        |
        +--> [existing] stats, performance, timeline, score_gap_material, clock_pressure, time_pressure_chart
        |
        +--> [NEW in Phase 57] endgame_elo_timeline:
                |
                v
         get_endgame_elo_timeline(session, user_id, ...filters)
                |
                +--> query_endgame_elo_timeline_rows  (new repo function)
                |       |
                |       +--> SELECT from Game joined with bucket_rows (per-game first-endgame imbalance + after)
                |             WHERE apply_game_filters(...)
                |             columns: played_at, platform, time_control_bucket, user_color,
                |                      white_rating, black_rating, user_material_imbalance,
                |                      user_material_imbalance_after, result
                |
                +--> partition rows by (platform, time_control_bucket) -> up to 8 combos
                |
                +--> for each combo:
                |       _compute_endgame_elo_weekly_series(endgame_rows, all_games_rows, window=100):
                |         1. walk chronological merged events (endgame + non-endgame) maintaining
                |            two trailing-100 windows (endgame window for skill, all-games window for Actual ELO)
                |         2. for each ISO week's final event, compute:
                |            - skill = backend endgame_skill(endgame_window)  (Phase 56 helper; or fallback: inline)
                |            - avg_opp = mean(opponent_rating in endgame_window)
                |            - endgame_elo = round(avg_opp + 400 * log10(clamp(skill, 0.05, 0.95) / (1 - clamp)))
                |            - actual_elo = round(mean(user_rating in all_games_window))
                |         3. emit only if endgame_window_count >= MIN_GAMES_FOR_TIMELINE
                |
                v
         EndgameEloTimelineResponse { combos: [EndgameEloTimelineCombo {combo_key, platform, time_control, points: [...]}] }
        |
        v
Frontend: overviewData.endgame_elo_timeline
        |
        v
EndgameEloTimelineSection
        |
        +--> niceEloAxis(visibleEloValues)  [new helper in utils.ts]
        +--> ELO_COMBO_COLORS[combo]  [new theme constant]
        +--> hiddenKeys Set<comboKey> + handleLegendClick
        +--> LineChart with 2*N <Line> elements (N = visible combos, 2 = bright+dark per combo)
        +--> Per-combo legend entry with split swatch (linear-gradient)
        +--> Tooltip block per combo showing endgame_elo / actual_elo / gap / games_in_window
```

### Recommended Project Structure (deltas from current tree)

```
app/
├── repositories/
│   └── endgame_repository.py         # ADD: query_endgame_elo_timeline_rows(...)
├── services/
│   └── endgame_service.py            # ADD: ENDGAME_ELO_TIMELINE_WINDOW = 100
│                                     # ADD: _compute_endgame_elo_weekly_series(...)
│                                     # ADD: get_endgame_elo_timeline(...)
│                                     # EXTEND: get_endgame_overview to include elo_timeline in response
├── schemas/
│   └── endgames.py                   # ADD: EndgameEloTimelinePoint, EndgameEloTimelineCombo,
│                                     #      EndgameEloTimelineResponse
│                                     # EXTEND: EndgameOverviewResponse with endgame_elo_timeline field
└── routers/
    └── endgames.py                   # NO CHANGES — /overview already serves the composed response

frontend/src/
├── lib/
│   ├── theme.ts                      # ADD: ELO_COMBO_COLORS: Record<EloComboKey, {bright, dark}>
│   └── utils.ts                      # ADD: niceEloAxis(values: number[]) — lifted from RatingChart inline logic
├── types/
│   └── endgames.ts                   # ADD: EndgameEloTimelinePoint, EndgameEloTimelineCombo,
│                                     #      EndgameEloTimelineResponse, EloComboKey
│                                     # EXTEND: EndgameOverviewResponse
├── components/
│   └── charts/
│       └── EndgameEloTimelineSection.tsx   # NEW — the section component
└── pages/
    └── Endgames.tsx                  # EXTEND: wire up new section under shared "Endgame ELO" h2
```

### Pattern 1: Weekly Rolling Window Series (copy from `_compute_weekly_rolling_series`)

**What:** Walk chronologically sorted rows, maintain a trailing `window`-size slice, overwrite a per-ISO-week dict so each week keeps the window state after its last game.

**When to use:** Every endgame timeline chart in the codebase. Matches `_compute_score_gap_timeline` and `_compute_clock_pressure_timeline`.

**Example (existing, proven):**
```python
# Source: app/services/endgame_service.py:1290-1337
def _compute_weekly_rolling_series(rows: list[Row[Any]], window: int) -> list[dict]:
    results_so_far: list[Literal["win", "draw", "loss"]] = []
    data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)

        window_slice = results_so_far[-window:]
        window_total = len(window_slice)
        win_rate = window_slice.count("win") / window_total if window_total > 0 else 0.0

        iso_year, iso_week, iso_weekday = played_at.isocalendar()
        monday = (played_at - timedelta(days=iso_weekday - 1)).date()
        data_by_week[(iso_year, iso_week)] = {
            "date": monday.isoformat(),
            "win_rate": round(win_rate, 4),
            "game_count": window_total,
        }

    return [
        data_by_week[key]
        for key in sorted(data_by_week.keys())
        if data_by_week[key]["game_count"] >= MIN_GAMES_FOR_TIMELINE
    ]
```

**For Phase 57:** The new helper merges two row streams (endgame games + all games) into a single chronologically-sorted event list, keeps two parallel trailing windows, and at each ISO-week boundary computes both lines. This is closer in shape to `_compute_score_gap_timeline` (which already merges endgame + non-endgame events — see lines 558-615) than to the vanilla `_compute_weekly_rolling_series`. **Use `_compute_score_gap_timeline` as the shape reference, not `_compute_weekly_rolling_series`.** [VERIFIED via read of lines 540-615]

### Pattern 2: Composed Overview Response (Phase 52 consolidation)

**What:** One HTTP request returns all Endgame-tab data. Internal queries run sequentially on one `AsyncSession`.

**When to use:** Any new Endgame-tab chart. CLAUDE.md forbids `asyncio.gather` on `AsyncSession`.

**Example (existing):**
```python
# Source: app/routers/endgames.py:28-61 + app/schemas/endgames.py:332-346
class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    score_gap_material: ScoreGapMaterialResponse
    clock_pressure: ClockPressureResponse
    time_pressure_chart: TimePressureChartResponse
```

**For Phase 57:** Add `endgame_elo_timeline: EndgameEloTimelineResponse` to this model. Orchestrator adds one more sequential DB call. No new router endpoint.

### Pattern 3: Recharts Legend Toggle (`hiddenKeys` Set)

**What:** Local `useState<Set<string>>`, `onClickItem` mutates into a new Set (React referential equality), `<Line hide={hiddenKeys.has(key)} />`.

**When to use:** Every multi-series Recharts chart in the codebase. Standard for this project.

**Example (existing):**
```tsx
// Source: frontend/src/components/charts/EndgameTimelineChart.tsx:33-45
const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
const handleLegendClick = useCallback((dataKey: string) => {
  setHiddenKeys((prev) => {
    const next = new Set(prev);
    if (next.has(dataKey)) next.delete(dataKey);
    else next.add(dataKey);
    return next;
  });
}, []);
// ...
<ChartLegend content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />} />
{typeKeys.map((key) => <Line key={key} dataKey={key} hide={hiddenKeys.has(key)} ... />)}
```

**For Phase 57:** One Set keyed by combo_key (8 entries max, not 16). Both bright and dark `<Line>` for that combo share the same `hide={hiddenKeys.has(combo)}` expression. [VERIFIED: chart.tsx accepts `hiddenKeys` + `onClickItem` props at lines 113-120]

### Pattern 4: Nice-Axis Helper (lifted from `RatingChart`)

**What:** Given a list of rating values, pick the largest step from [50, 100, 200, 500] where `range / step >= 4`, produce an integer tick array.

**When to use:** Any rating-scale Y axis. `niceWinRateAxis` (0-1 percent) is NOT suitable.

**Source:** `frontend/src/components/stats/RatingChart.tsx:54-106` [VERIFIED: read]

**Phase 57 decision:** UI-SPEC §Axes (lines 196-205) already prescribes promoting this inline logic into a named helper `niceEloAxis` in `frontend/src/lib/utils.ts`. Tick candidates `[50, 100, 200, 500]` (UI-SPEC differs slightly from RatingChart's `[10, 20, 50, 100, 200, 500]` — use UI-SPEC's values since Elo ranges are always >= 50).

### Anti-Patterns to Avoid

- **`asyncio.gather` on the `AsyncSession`.** CLAUDE.md §Critical Constraints forbids this. Existing code executes queries sequentially on one session. New queries MUST follow suit.
- **Duplicating `apply_game_filters` logic.** Every new repo query MUST use the shared helper. Inline WHERE clauses for platform/time_control/rated/opponent_type/recency are a bug by design.
- **Coloring chart lines with hex literals.** CLAUDE.md §Frontend rule: theme constants go in `theme.ts`. UI-SPEC lines 77-98 already prescribe the exact oklch values — planner just commits them to `theme.ts`.
- **Per-line legend toggle (16 entries).** UI-SPEC locks combo-level toggle. Planner MUST NOT revisit.
- **Rolling the Elo formula into `_compute_weekly_rolling_series` via callback parameterization.** 4 existing callers depend on that function; adding a callback breaks encapsulation. Build a parallel helper.
- **Fetching all-games and endgame-games in separate HTTP requests.** Both must share the same `AsyncSession` and be invoked from the same orchestrator.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO-week bucketing | Custom week-start math | `played_at.isocalendar()` + `timedelta(days=iso_weekday - 1)` — already in `_compute_weekly_rolling_series` | Handles year boundaries, leap weeks, DST |
| Rolling window accumulator | Custom `deque` wrapper | Python list with `list[-N:]` slice — existing pattern | Matches 4 other timeline helpers; consistency beats micro-perf |
| Nice axis tick selection | Tight-loop tick picker | Promote `RatingChart`'s `[50, 100, 200, 500]` step algorithm into `niceEloAxis(values)` | Already shipping, tested visually — no reason to reinvent |
| Chart legend with click-to-toggle | Custom Recharts Legend | `ChartLegend` + `ChartLegendContent` from `frontend/src/components/ui/chart.tsx` | Already supports `hiddenKeys` + `onClickItem` props; split-swatch can be achieved via custom `content` prop without reinventing the surrounding layout |
| Line chart paired stroke styles | Custom SVG paths | Two `<Line>` elements per combo — bright + dark stroke constants + `strokeDasharray="4 2"` on dark | Recharts natively supports per-Line styling |
| Platform/time-control filter application | Repeat WHERE clauses | `apply_game_filters(...)` from `query_utils.py` | CLAUDE.md rule; single source of truth |
| User rating from white/black | Custom conditional | `case((Game.user_color == "white", Game.white_rating), else_=Game.black_rating)` — lift from `stats_repository.py:63` | Already proven; ensures consistency with `RatingChart` data |
| Endgame Skill composite | Frontend `endgameSkill()` only | Phase 56 backend `endgame_skill()` function (to be built) | Timeline needs skill computed per (combo, rolling window) — can't do this from the already-aggregated breakdown table |
| Opponent rating extraction | Custom `case` every time | Mirror `user_rating_expr`: `case((Game.user_color == "white", Game.black_rating), else_=Game.white_rating)` | Same pattern as `apply_game_filters` opponent_strength block (lines 59-66) |

**Key insight:** Phase 57 is almost entirely composition of existing patterns. The one genuinely new piece is the Elo formula itself (~4 lines: clamp + log-odds). Every other piece — windowing, filtering, row aggregation, legend toggling, axis computation, tooltip rendering, empty state — exists and must be reused rather than rebuilt.

## Runtime State Inventory

> Omitted — this is a greenfield feature phase, not a rename/refactor/migration. No stored data is renamed, no live service config changes, no OS-registered state, no secrets rotate, no build artifacts invalidate.

## Common Pitfalls

### Pitfall 1: Empty-Bucket Divide-By-Zero in Elo Formula

**What goes wrong:** Computing `log10(skill / (1 - skill))` with `skill == 0` or `skill == 1` blows up (log10(0) = -inf, 1/0 = div-by-zero).

**Why it happens:** A user with exactly 0 wins in their rolling window (all draws/losses → Conv = 0, Recov might still be > 0 but composite could still trend toward 0) or exactly 1.0 (all conversions won, unlikely but possible in small samples).

**How to avoid:** Apply `skill_clamped = max(0.05, min(0.95, skill))` BEFORE the log10 call. D-01 locks this exact clamp. Backend `endgame_elo` computation MUST apply clamp unconditionally — not conditionally on "only if extreme".

**Warning signs:** Divide-by-zero or `inf` in test logs when a combo has fewer than ~20 games. Add a unit test for skill=0.0 and skill=1.0 inputs to the formula.

### Pitfall 2: Window Starvation from Recency Filter

**What goes wrong:** User applies "past 3 months" recency filter; first emitted point claims "past 100 games" but the window hasn't actually filled yet, so the displayed Elo jitters wildly until the window truly holds 100 games.

**Why it happens:** Naive implementation applies the recency cutoff to the SQL query, so the rolling-window accumulator only sees games from the last 3 months.

**How to avoid:** Follow the existing pattern from `get_endgame_timeline` (lines 1425-1457) and `_compute_score_gap_timeline`'s `cutoff_str` parameter (line 614): fetch games WITHOUT the recency cutoff (let the window pre-fill from earlier games), then filter emitted POINTS to only those dated on or after the cutoff. [VERIFIED: `endgame_service.py:1438-1457`]

**Warning signs:** The first few emitted points of a recency-filtered chart showing wildly different Elo values than a non-filtered chart for the same user.

### Pitfall 3: Per-Combo Partition Produces Zero-Combo Output When Filter Narrows to One Platform

**What goes wrong:** Sidebar sets platform=["chess.com"] only; backend only returns chess.com combos (4 max instead of 8). Frontend expects 8 and renders empty dark-theme chart.

**Why it happens:** Frontend hard-codes combo keys instead of iterating over `response.combos[]`.

**How to avoid:** Backend response shape is `combos: EndgameEloTimelineCombo[]` (a list, not a fixed-keys object). Frontend iterates whatever comes back, not over `['chess_com_bullet', ..., 'lichess_classical']`. Legend is dynamically built from `response.combos`.

**Warning signs:** Legend shows ghost entries for combos the filter excluded, or tooltip crashes referencing an undefined `ELO_COMBO_COLORS[combo]` for a combo that doesn't exist.

### Pitfall 4: Cold-Start Recency + New Account = Visible Gray Chart Instead of Empty State

**What goes wrong:** Brand-new user, recency filter "past week", no 100-endgame-game rolling window has been reached yet. Backend returns `{combos: []}` (D-10 three-tier hide). Frontend's `showEloTimeline = eloTimelineData.combos.length > 0` guard evaluates false. If the outer `{showEloTimeline && <Section />}` check is used, the section heading AND info popover disappear too.

**Why it happens:** Naive conditional render hides the whole section instead of just swapping chart for empty-state.

**How to avoid:** Follow UI-SPEC §"Conditional render" (lines 181): render the section heading and info popover ALWAYS; swap only the chart body between chart and empty-state. This mirrors the existing `EndgameTimelineChart` empty-state handling (lines 67-73).

**Warning signs:** Users with sparse data can't read the info popover that would explain why they don't see data.

### Pitfall 5: ty Errors from SQLAlchemy Row Attribute Access

**What goes wrong:** ty complains about `row.played_at` or `row.platform` access because the `Row[Any]` type doesn't surface labeled columns at type-check time.

**Why it happens:** SQLAlchemy's `Row[Any]` is intentionally open — labels only exist at runtime.

**How to avoid:** Either tuple-unpack `(played_at, platform, tc, ...) = row` (matches `_compute_weekly_rolling_series` pattern) OR add `# ty: ignore[unresolved-attribute]` with a brief reason, matching the `_compute_score_gap_material` pattern at line 684. The tuple-unpack approach is cleaner and already dominant in the codebase. [VERIFIED: `endgame_service.py:1316`]

**Warning signs:** `uv run ty check app/ tests/` fails in CI between ruff and pytest.

### Pitfall 6: `noUncheckedIndexedAccess` Trap on `ELO_COMBO_COLORS[combo]`

**What goes wrong:** TypeScript flags `ELO_COMBO_COLORS[combo].bright` because the Record access returns `T | undefined`.

**Why it happens:** `tsconfig.json` has `noUncheckedIndexedAccess: true` [VERIFIED: CLAUDE.md §Frontend line 4].

**How to avoid:** Two options:
1. **Preferred (type-safe):** Type the record as `Record<EloComboKey, {...}>` where `EloComboKey` is a string-literal union of the 8 known keys. Then narrow combo to `EloComboKey` at the API boundary (e.g. `as EloComboKey` after validating against the known set, or parse with zod).
2. **Fallback-friendly:** Use `?? FALLBACK_COLOR` every time. Uglier but never crashes on an unknown combo.

**Warning signs:** Red squiggles under every `ELO_COMBO_COLORS[combo]` usage, build fails under strict TS.

### Pitfall 7: Silent Gap Filling by `connectNulls` Masks Data Sparsity

**What goes wrong:** A combo has data for weeks 1-5 and weeks 20-25 but nothing in between. Recharts with `connectNulls={true}` draws a straight line across 15 empty weeks, implying smooth Elo progression where none exists.

**Why it happens:** UI-SPEC line 210 explicitly sets `connectNulls={true}` for both lines.

**Mitigation:** Accept the tradeoff — each weekly point already represents a trailing 100-game window, so a "gap" usually means the user didn't play 10 endgame games in that week but their 100-game window is still healthy. The bridging line is a reasonable approximation. Document in the info popover ("dots aren't shown per-week; the line summarizes your trailing 100 endgame games"). Do NOT add dots (`dot={false}` is correct) because 8 combos × 2 lines × many points = visual overload.

**Warning signs:** User questions why a line "looks flat" during a period they remember taking a break from chess.

## Code Examples

### Elo formula computation (new — backend)

```python
# Source: Phase 57 locked decision D-01 (57-CONTEXT.md)
import math
from typing import Final

ENDGAME_ELO_TIMELINE_WINDOW: Final[int] = 100
_SKILL_CLAMP_LO: Final[float] = 0.05
_SKILL_CLAMP_HI: Final[float] = 0.95


def _endgame_elo_from_skill(skill: float, avg_opp_rating: float) -> int:
    """Performance rating from skill composite + opponent average.

    skill in [0, 1]; clamped to [0.05, 0.95] before log10 to cap at ~510 Elo
    beyond the opponent average (well above realistic performance-rating range
    in small samples).
    """
    s = max(_SKILL_CLAMP_LO, min(_SKILL_CLAMP_HI, skill))
    return round(avg_opp_rating + 400 * math.log10(s / (1 - s)))
```

### Weekly Elo rolling helper (new — shape lifted from `_compute_score_gap_timeline`)

```python
# Source: pattern adapted from app/services/endgame_service.py:540-615
def _compute_endgame_elo_weekly_series(
    endgame_rows: list[Row[Any]],   # (played_at, user_color, white_rating, black_rating,
                                    #  user_material_imbalance, user_material_imbalance_after, result)
    all_games_rows: list[Row[Any]], # (played_at, user_color, white_rating, black_rating)
    window: int,
    cutoff_str: str | None = None,
) -> list[EndgameEloTimelinePoint]:
    """Co-compute weekly Endgame-ELO + Actual-ELO rolling series for one combo.

    Walks a merged chronological event stream of endgame games and all games
    (tagged "endgame"/"all") while maintaining two independent trailing windows.
    At each ISO-week boundary, emits one point with both lines computed.

    Per-point emission requires endgame_window_count >= MIN_GAMES_FOR_TIMELINE
    (D-06, three-tier hide tier 1).

    `cutoff_str` filters output points to >= cutoff while letting earlier games
    pre-fill the windows (same pattern as get_endgame_timeline).
    """
    # (actual body: merge+sort events, walk, compute skill from endgame window,
    # avg_opp_rating from endgame window, user_rating from all_games window,
    # apply Elo formula, bucket by ISO week, drop points under threshold or
    # before cutoff_str)
    ...
```

### Frontend section component skeleton (new)

```tsx
// Source: structure lifted from EndgameTimelineChart.tsx + EndgameScoreGapSection.tsx + UI-SPEC
import { useState, useCallback, useMemo } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { createDateTickFormatter, formatDateWithYear, niceEloAxis } from '@/lib/utils';
import { ELO_COMBO_COLORS, type EloComboKey } from '@/lib/theme';
import type { EndgameEloTimelineResponse } from '@/types/endgames';

interface Props { data: EndgameEloTimelineResponse; }

export function EndgameEloTimelineSection({ data }: Props) {
  const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
  const handleLegendClick = useCallback((comboKey: string) => {
    setHiddenKeys(prev => {
      const next = new Set(prev);
      if (next.has(comboKey)) next.delete(comboKey); else next.add(comboKey);
      return next;
    });
  }, []);

  // Collect all unique dates across all visible combos
  const allDates = useMemo(/* flatten combos[].points[].date, dedupe, sort */, [data, hiddenKeys]);
  // Flatten all visible Elo values for axis computation
  const yAxis = useMemo(/* niceEloAxis(visibleEloValues) */, [data, hiddenKeys]);

  if (data.combos.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8" data-testid="endgame-elo-timeline-empty">
        <p className="font-medium">Not enough endgame games yet for a timeline.</p>
        <p className="text-sm mt-1">Import more games or loosen the recency filter.</p>
      </div>
    );
  }

  // Build chartData: one row per date with {combo}_endgame_elo and {combo}_actual_elo columns
  const chartData = /* ... */;

  return (
    <div>
      <div className="mb-3">
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame ELO Timeline
            <InfoPopover
              ariaLabel="Endgame ELO Timeline info"
              testId="endgame-elo-timeline-info"
              side="top"
            >
              {/* UI-SPEC locked prose (lines 128-157) */}
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Endgame ELO versus Actual ELO over time, per platform and time control.
          Bright lines are Endgame ELO, dark lines are Actual ELO.
        </p>
      </div>
      <ChartContainer config={{}} className="w-full h-72" data-testid="endgame-elo-timeline-chart">
        <LineChart data={chartData}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tickFormatter={createDateTickFormatter(allDates)} tick={{ fontSize: 12 }} />
          <YAxis domain={yAxis.domain} ticks={yAxis.ticks} tick={{ fontSize: 12 }} />
          <ChartTooltip content={/* per-combo block tooltip */} />
          <ChartLegend content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />} />
          {data.combos.map((combo) => (
            <>
              <Line
                key={`${combo.combo_key}_endgame_elo`}
                dataKey={`${combo.combo_key}_endgame_elo`}
                stroke={ELO_COMBO_COLORS[combo.combo_key as EloComboKey].bright}
                strokeWidth={2}
                dot={false}
                connectNulls
                hide={hiddenKeys.has(combo.combo_key)}
              />
              <Line
                key={`${combo.combo_key}_actual_elo`}
                dataKey={`${combo.combo_key}_actual_elo`}
                stroke={ELO_COMBO_COLORS[combo.combo_key as EloComboKey].dark}
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                connectNulls
                hide={hiddenKeys.has(combo.combo_key)}
              />
            </>
          ))}
        </LineChart>
      </ChartContainer>
    </div>
  );
}
```

### Phase 56 boundary contract (what Phase 57 needs from Phase 56)

Phase 57 needs **at minimum** a backend `endgame_skill(rows_like_endgame_bucket) -> float | None` function operating on the same per-game bucket rows shape (`user_material_imbalance`, `user_material_imbalance_after`, `result`, `user_color`). If Phase 56 lands first, Phase 57 imports this helper. If Phase 56 is not yet merged, Phase 57 can inline the identical logic with a clear comment pointing to where it will be deduplicated.

**Minimum viable Phase 56 contract (for Phase 57 to depend on):**

```python
# app/services/endgame_service.py (added by Phase 56)
def endgame_skill(
    entry_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> float | None:
    """Composite Endgame Skill: mean of Conversion Win %, Parity Score %,
    Recovery Save %, excluding buckets with 0 games. Returns None when all
    three buckets are empty (caller treats as "insufficient data")."""
    ...
```

Everything else Phase 56 builds (breakdown endpoint, frontend table, info popover) is Phase-56 scope and Phase 57 neither consumes nor blocks on it.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `/api/endgames/{stats,performance,timeline,conv-recov-timeline}` endpoints | Single `/api/endgames/overview` composed response | Phase 52 (2026-04-11) | Phase 57 MUST follow this — one endpoint, sequential queries |
| `asyncio.gather` across repos on one session | Sequential awaits on one `AsyncSession` | Phase 52 | Mandatory — CLAUDE.md §Critical Constraints |
| Daily timeline datapoints (RatingChart) / per-game-date datapoints | Weekly ISO-week bucketing with 100-game rolling window | Phase 53 + quick-260416-vcx + quick-260416-w3q + quick-260417-o2l (2026-04-16/17) | Phase 57 MUST follow — CONTEXT.md D-05 |
| MIN_GAMES threshold set to 3 in individual charts | Uniform `MIN_GAMES_FOR_TIMELINE = 10` | Phase 52+ consolidation | Phase 57 uses 10 verbatim (D-06) |
| Per-game material imbalance classification without persistence | Persistence check at entry + 4 plies, threshold 100cp | Phase 48 (2026-04-07) | Affects upstream: `user_material_imbalance_after` is the relevant column for skill compute |
| Frontend-only `endgameSkill()` composite | Backend `endgame_skill()` helper (Phase 56) | Phase 56 (upcoming) | Phase 57 consumes this |
| Global-average opponent baseline | Self-calibrating opponent baseline via same-game symmetry | Phase 60 (2026-04-14) | Not directly relevant to Phase 57 — ELO uses `avg(opponent_rating)`, not user-vs-opponent score symmetry |

**Deprecated / outdated (do NOT mimic):**
- `RatingChart`'s inline tick-step algorithm — UI-SPEC prescribes lifting into `niceEloAxis`.
- `_compute_rolling_series` (per-game datapoints) in `endgame_service.py:1249-1287` — the per-game variant is being phased out in favor of `_compute_weekly_rolling_series`. Phase 57 uses weekly ONLY.

## Project Constraints (from CLAUDE.md)

Non-negotiable project rules applicable to Phase 57:

### Backend
- **No `asyncio.gather` on `AsyncSession`.** Execute queries sequentially. (§Critical Constraints)
- **Use `httpx.AsyncClient`** for any outbound HTTP (not applicable here — no external calls in Phase 57).
- **Use `apply_game_filters`** from `query_utils.py` as the single source of truth for game filtering. Never duplicate filter logic in new repo queries. (§Shared Query Filters)
- **Type safety, no `any`, Literals for fixed string sets.** (§Coding Guidelines)
- **`uv run ty check app/ tests/` must pass zero-errors.** Use `Sequence[str]` not `list[str]` for function params accepting `list[Literal[...]]` values. Suppressions use `# ty: ignore[rule-name]` with reason. (§ty compliance)
- **Comment bug fixes** at the fix site when touching existing code. (§Coding Guidelines)
- **Sentry rules:** call `sentry_sdk.capture_exception()` in non-trivial except blocks in services/routers; skip trivial ValueErrors; never embed variables in error messages (use `set_context`); use tags for filterable dimensions. (§Error Handling & Sentry §Backend Rules)
- **Foreign key constraints, unique constraints, appropriate column types** — not relevant to Phase 57 since no schema changes.

### Frontend
- **Theme constants in `theme.ts`** — `ELO_COMBO_COLORS` must live there, not inline in the component. (§Frontend)
- **`noUncheckedIndexedAccess` enabled** — narrow before use; never `// @ts-ignore`. (§Frontend Code Style)
- **Knip runs in CI** — any new export must be imported somewhere. (§Frontend Code Style)
- **Mobile friendly UI** — Tailwind breakpoints, flexible layouts. UI-SPEC §"Legend — mobile parity decision" already details this.
- **Always apply changes to mobile too** — not strictly applicable since UI-SPEC §Mobile parity says one component renders both viewports via breakpoint utilities, no second copy. Planner MUST keep it that way.
- **Primary vs secondary buttons** — Phase 57 has no buttons. N/A.
- **Global TanStack Query errors already captured** in `queryClient.ts`; do NOT add duplicate `Sentry.captureException()` in components using `useQuery`/`useMutation`. (§Frontend Rules)
- **`isError` branch mandatory** in every data-loading ternary chain — UI-SPEC §Copywriting Contract already prescribes the exact error copy. (§Frontend Rules)
- **`data-testid` on every interactive + structural element.** UI-SPEC §Browser Automation Contract already prescribes the exact IDs. (§Browser Automation Rules)
- **Semantic HTML, ARIA labels on icon-only triggers, `data-testid` on chess board (N/A here).** (§Browser Automation Rules)

### Communication / Style
- **Em-dashes sparingly** in info popover prose and any user-facing copy. UI-SPEC budget is one em-dash total across 4 popover paragraphs. Tooltip and empty-state copy must follow the same rule.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 56 will introduce a backend `endgame_skill()` function with a shape compatible with Phase 57's needs | Pattern 2 Phase 56 boundary contract | If Phase 56 ships a different shape (e.g. requires pre-aggregated MaterialRow list instead of raw entry rows), Phase 57 needs a light adapter. Low risk because CONTEXT.md D-03 explicitly says Phase 56 ports the computation server-side. |
| A2 | The existing `apply_game_filters` is sufficient for the Actual ELO line's "all games" query (no endgame-only filter needed) | Standard Stack | If there's a hidden requirement that Actual ELO should also restrict to games with clock data or similar, query design changes. Low risk — D-04 explicitly says "ALL games for that combo". |
| A3 | No need for a new database index to support the new query | Common Pitfalls (implicit) | If the combined (platform, time_control_bucket) + played_at sort produces a slow query at prod scale, indexing would be needed. Low risk — existing indexes on Game + GamePosition already support this. Mitigation: planner instructs the executor to check `EXPLAIN ANALYZE` on prod via the `flawchess-prod-db` MCP tool after deploy. |
| A4 | Opponent rating for skill computation comes from the Game row (`white_rating`/`black_rating` opposite of `user_color`), not from a per-game pre-stored column | Code Examples | If opponent rating needs to come from a different source (e.g. opponent profile snapshot), Phase 57 needs a different SQL shape. Low risk — `apply_game_filters`'s opponent_strength code at lines 59-66 already derives opp rating this way. |
| A5 | `endgame_skill` requires the same entry/bucket row shape as `_compute_score_gap_material` consumes | Code Examples | If Phase 56 designs `endgame_skill()` to take a pre-aggregated MaterialRow list (matching the frontend helper's signature), Phase 57's weekly windowing can't slot it in cleanly — Phase 57 needs raw rows to compute the composite per-window. Moderate risk — flagged in Open Questions. |

**Action:** Assumption A5 should be resolved during Phase 56 planning. Phase 57 plan should include a light adapter/fallback in case A5 proves wrong (inline the skill computation in Phase 57 with a TODO pointing to Phase 56 helper).

## Open Questions

1. **Phase 56 `endgame_skill()` function signature**
   - What we know: Phase 56 will port the frontend `endgameSkill()` composite to backend (D-03).
   - What's unclear: Does it take raw `entry_rows` (like `_compute_score_gap_material`) or a pre-aggregated `list[MaterialRow]` (like the frontend helper)?
   - Recommendation: Raw rows are needed for windowed computation in Phase 57. Recommend Phase 56 expose BOTH: `endgame_skill_from_rows(entry_rows) -> float | None` AND the existing `endgame_skill_from_material_rows(material_rows) -> float | None` pattern. Phase 57 imports the former. If Phase 56 only exposes the latter, Phase 57 inlines row → MaterialRow aggregation inside the per-window loop (small duplication, acceptable).

2. **Combo ordering in the response**
   - What we know: UI-SPEC gives 8 combo display labels but doesn't mandate an ordering in the legend.
   - What's unclear: Alphabetical? Sample-size descending? chess.com-first then lichess? Bullet→Classical within each platform?
   - Recommendation: Platform-first (chess.com → lichess), then speed-ascending (Bullet → Blitz → Rapid → Classical) within each. Matches the existing `_TIME_CONTROL_ORDER` convention in `endgame_service.py:822`. Planner locks this in schema docstring.

3. **Tooltip for hidden combos**
   - What we know: Recharts default renders tooltip entries for ALL lines, even hidden ones (`hide={true}` hides the line but not the tooltip payload).
   - What's unclear: Should the tooltip suppress hidden combos' rows?
   - Recommendation: Yes, filter tooltip payload by `!hiddenKeys.has(combo_key_from_dataKey)`. This matches user expectation (legend toggle = combo is gone). Planner confirms in plan.

4. **Games-in-window counter per line vs per combo**
   - What we know: UI-SPEC tooltip shows `(past {games_in_window} games)` after each combo block.
   - What's unclear: Is `games_in_window` the endgame-window count (what drives skill/opp_avg) or the all-games-window count (what drives Actual ELO)? They differ.
   - Recommendation: Show the ENDGAME-window count (the quantity the ≥10 threshold applies to) — matches UI-SPEC's tooltip example phrasing `(past 100 games)` which implies the endgame count. Explicit field on the backend: `endgame_games_in_window: int`. Actual-ELO window size is always ≈100 and not informative to show.

5. **"Cold-start" wording in empty state**
   - What we know: UI-SPEC locks the exact copy: "Not enough endgame games yet for a timeline. / Import more games or loosen the recency filter."
   - What's unclear: None — copy is locked. Marking resolved.

## Environment Availability

> Skipped — Phase 57 is a code/config-only feature phase with no new external dependencies. All tools, libraries, and services it needs are already present and in active use for the existing Endgames tab. The only environment requirement is the standard dev loop: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` for Postgres, `uv sync`, `npm install`. [VERIFIED: CLAUDE.md §Commands]

## Validation Architecture

> `workflow.nyquist_validation: true` in `.planning/config.json` [VERIFIED: read]. Section included.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x (async-enabled via `pytest-asyncio`) [VERIFIED: existing test suite] |
| Backend config file | `pyproject.toml` (pytest config lives there in this project) / `tests/conftest.py` |
| Backend quick run | `uv run pytest tests/test_endgame_service.py -x` |
| Backend full suite | `uv run pytest` |
| Backend type-check | `uv run ty check app/ tests/` |
| Backend lint | `uv run ruff check .` |
| Backend format-check | `uv run ruff format --check .` |
| Frontend framework | Vitest (via `npm test`) [VERIFIED: CLAUDE.md §Commands] |
| Frontend quick run | `npm test -- --run <testfile>` |
| Frontend full suite | `npm test` |
| Frontend lint | `npm run lint` |
| Frontend knip | `npm run knip` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ELO-05 | Paired lines per (platform, time-control) render in chart | unit (frontend) | `npm test -- --run EndgameEloTimelineSection.test.tsx` | ❌ Wave 0 |
| ELO-05 | Endgame ELO formula: `round(avg_opp + 400·log10(clamp(skill) / (1 − clamp)))` | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameElo -x` | ❌ Wave 0 |
| ELO-05 | Clamp applies at boundaries: skill=0.0 and skill=1.0 don't blow up | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameElo::test_clamp_boundaries -x` | ❌ Wave 0 |
| ELO-05 | Actual ELO = mean(user_rating over all-games-100-window) | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameEloTimeline::test_actual_elo_from_all_games -x` | ❌ Wave 0 |
| ELO-05 | Weekly point emitted only when endgame-window ≥ 10 games (D-06) | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameEloTimeline::test_below_min_games_dropped -x` | ❌ Wave 0 |
| ELO-05 | Chart updates when sidebar filters change (three-tier hide D-10) | integration (backend) | `uv run pytest tests/test_integration_routers.py::test_endgame_overview_elo_timeline_respects_filters -x` | ❌ Wave 0 |
| ELO-05 | Combo with zero qualifying points is dropped from response (D-10 tier 2) | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameEloTimeline::test_combo_dropped_when_zero_points -x` | ❌ Wave 0 |
| ELO-05 | Cold-start: no artifacts on new account with recency filter (SC-3) | integration (backend) | `uv run pytest tests/test_integration_routers.py::test_endgame_overview_elo_timeline_cold_start_returns_empty_combos -x` | ❌ Wave 0 |
| ELO-05 | Recency cutoff filters output but window pre-fills from earlier games | unit (backend) | `uv run pytest tests/test_endgame_service.py::TestEndgameEloTimeline::test_cutoff_does_not_starve_window -x` | ❌ Wave 0 |
| ELO-05 | `apply_game_filters` is the only place that filters games (CLAUDE.md rule) | unit (backend) — assertion via grep or structural test | manual code review; optionally `tests/test_endgame_repository.py::test_elo_timeline_uses_shared_filter` mocking the helper | ❌ Wave 0 |
| ELO-05 | `niceEloAxis(values)` picks sensible ticks for Elo ranges | unit (frontend) | `npm test -- --run utils.test.ts` (extend existing utils test) | ❌ Wave 0 (or extend existing) |
| ELO-05 | Legend toggle hides both lines of a combo | unit (frontend) | `npm test -- --run EndgameEloTimelineSection.test.tsx` | ❌ Wave 0 |
| ELO-05 | Empty-state renders section heading + info popover + empty-state text (Pitfall 4) | unit (frontend) | `npm test -- --run EndgameEloTimelineSection.test.tsx` | ❌ Wave 0 |
| ELO-05 | Error-state renders locked copy (CLAUDE.md isError rule) | unit (frontend) | page-level test in `Endgames.test.tsx` or section test | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_endgame_service.py -x && uv run ty check app/ tests/` (backend work) OR `npm run lint && npm run knip && npm test -- --run` (frontend work).
- **Per wave merge:** `uv run pytest && uv run ty check app/ tests/ && uv run ruff check . && npm test && npm run lint && npm run knip`.
- **Phase gate (before `/gsd-verify-work`):** Full suite green, including the new tests above; manual visual smoke test on desktop + mobile with ≥ 2 combos and with filter narrowing to 1 combo.

### Wave 0 Gaps

- [ ] `tests/test_endgame_service.py::TestEndgameElo` — formula + clamp boundary tests
- [ ] `tests/test_endgame_service.py::TestEndgameEloTimeline` — weekly helper tests (min-games threshold, cutoff, actual-elo integration, cold-start)
- [ ] `tests/test_integration_routers.py` — extend with `/endgames/overview` integration checks covering the new `endgame_elo_timeline` field (cold-start and filter-respect)
- [ ] `frontend/src/components/charts/EndgameEloTimelineSection.test.tsx` — new test file (empty state, error state, legend toggle, combo rendering)
- [ ] `frontend/src/lib/utils.test.ts` — extend (or create) with `niceEloAxis` coverage
- [ ] `tests/seed_fixtures.py` — extend `seeded_user` fixture if the integration test needs additional game shapes (ratings, endgame spans). Phase 61 already added this fixture [VERIFIED: `.planning/ROADMAP.md` Phase 61 §61-01 plan].

**No framework install needed** — pytest + vitest are already in the suite.

## Security Domain

> `security_enforcement` is not set in `.planning/config.json`. Under absent-is-enabled interpretation, this section applies. Phase 57 has minimal security surface: read-only analytics endpoint reusing existing auth.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (indirect) | Reuses `current_active_user` dep from FastAPI-Users — no new auth logic |
| V3 Session Management | yes (indirect) | Existing Bearer JWT via FastAPI-Users; Phase 57 introduces nothing new |
| V4 Access Control | yes | Every query scoped to `user_id=user.id` — same pattern as existing `get_endgame_overview`. Planner MUST verify the new repo function filters by `user_id` at the SQL level, never via Python post-filter |
| V5 Input Validation | yes | Query params validated via FastAPI `Query(...)` and `Literal` types. No new input surface beyond the existing `/overview` params |
| V6 Cryptography | no | No crypto operations in Phase 57 |
| V7 Error Handling | yes | Sentry rules from CLAUDE.md §Error Handling apply — capture in non-trivial excepts, tag with `source="api"` and context dict for user_id |
| V8 Data Protection | yes (indirect) | Rating data is already exposed via `RatingChart` on Global Stats; no new PII surface. Opponent rating is not PII. |
| V12 File Integrity | no | No file I/O |
| V14 Configuration | yes | New constants (`ENDGAME_ELO_TIMELINE_WINDOW`) are code, not env config. No secrets. |

### Known Threat Patterns for FastAPI + SQLAlchemy async stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via filter params | Tampering | SQLAlchemy parameterized queries + Pydantic validation. Already enforced by `apply_game_filters` and `Literal[...]` typed `opponent_strength`. Phase 57 MUST follow suit — no f-strings into SQL. |
| Information disclosure across users (IDOR) | Information Disclosure | Every query filters by `Game.user_id == user_id` (the authenticated caller). Planner MUST verify new repo function has this WHERE clause at the TOP-LEVEL of the query, not just a subquery. |
| Unauthenticated access | Spoofing | `/overview` already uses `Depends(current_active_user)`. Phase 57 extends the same route, so this is inherited. |
| DoS via expensive query (large rolling windows × 8 combos × all history) | Denial of Service | Backend fetches already-filtered rows, partitions in Python O(N). Existing queries on `game_positions` (with covering indexes) take O(10k–100k rows) for typical users. Filter param `recency` naturally bounds cost. No pagination needed because response is bounded by combos × weeks ≤ 8 × ~300 weeks = ~2400 points worst case. |
| Rate abuse | Denial of Service | Not specific to Phase 57 — existing rate limits on API apply. Phase 44's `SEC-02` covers guest creation; general endpoints rely on authenticated sessions. |

**No new security controls required.** Phase 57 is additive to an already-authenticated endpoint.

## Sources

### Primary (HIGH confidence)

- **57-CONTEXT.md** [file: `.planning/phases/57-endgame-elo-timeline-chart/57-CONTEXT.md`] — D-01..D-10 locked decisions, formula, windowing, threshold, chart shape, cold-start handling
- **57-UI-SPEC.md** [file: `.planning/phases/57-endgame-elo-timeline-chart/57-UI-SPEC.md`] — visual contract, palette, axis helper, legend mobile layout, info popover copy, tooltip shape, test IDs
- **app/services/endgame_service.py** [lines 167, 540-615, 826, 1025-1103, 1249-1337] — `_compute_weekly_rolling_series`, `_compute_score_gap_timeline`, `_compute_clock_pressure_timeline`, constants
- **app/services/openings_service.py** [lines 43, 55, 76] — `MIN_GAMES_FOR_TIMELINE`, `derive_user_result`, `recency_cutoff`
- **app/repositories/query_utils.py** [entire file, 78 lines] — `apply_game_filters` canonical
- **app/repositories/stats_repository.py** [lines 46-97] — `query_rating_history`, `user_rating_expr`
- **app/repositories/endgame_repository.py** [entire file] — query shapes for endgame bucket rows, timeline rows, clock stats rows
- **app/routers/endgames.py** [entire file, 102 lines] — `/overview` endpoint already consolidates all endgame payloads
- **app/schemas/endgames.py** [lines 332-346] — `EndgameOverviewResponse` composed shape
- **frontend/src/components/charts/EndgameTimelineChart.tsx** [entire file, 179 lines] — legend toggle pattern, chart container + XAxis/YAxis/CartesianGrid/Tooltip wiring, empty state shape
- **frontend/src/components/stats/RatingChart.tsx** [lines 54-106] — rating-axis tick algorithm to lift into `niceEloAxis`
- **frontend/src/components/charts/EndgameScoreGapSection.tsx** [lines 167-177] — `endgameSkill()` frontend helper, info popover prose structure
- **frontend/src/components/ui/chart.tsx** [lines 107-169] — `ChartLegendContent` with `hiddenKeys` + `onClickItem`
- **frontend/src/lib/theme.ts** [entire file, 79 lines] — theme constant shape + existing palette (WDL, gauge, MY_SCORE_COLOR, impersonation)
- **frontend/src/lib/utils.ts** [lines 29-75] — date tick formatter + `niceWinRateAxis` template
- **frontend/src/hooks/useEndgames.ts** [entire file, 57 lines] — `useEndgameOverview` TanStack Query hook pattern
- **frontend/src/api/client.ts** [lines 157-193] — `endgameApi.getOverview` call shape
- **CLAUDE.md** [entire file] — project constraints, Sentry rules, type-safety, frontend rules, browser automation rules
- **.planning/ROADMAP.md** [Phase 56 + 57 sections, lines 236-257] — phase goals, requirements, success criteria
- **.planning/milestones/v1.8-REQUIREMENTS.md** [lines 56-61] — ELO-01..ELO-06 original definitions

### Secondary (MEDIUM confidence)

- **Recharts 2.15.4 docs** [inferred from usage patterns throughout the codebase, not fetched] — Line `hide`, `dot`, `strokeDasharray`, `connectNulls` props; `Legend` custom `content`. Codebase usage is authoritative for Phase 57 scope.

### Tertiary (LOW confidence)

- None. Phase 57 is entirely within project conventions; no LOW-confidence findings informed the recommendations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library, version, and helper verified in-repo (grep + read)
- Architecture: HIGH — reuses 3 existing weekly-rolling-series helpers, 1 existing consolidated-overview endpoint, 1 existing legend-toggle pattern
- Pitfalls: HIGH — 5 of 7 pitfalls are recurrences of issues already solved in the codebase (Pitfalls 2, 4, 5, 6, 7); Pitfalls 1 and 3 are formula-specific and validated against D-01 clamp decision
- Tests: HIGH — existing `test_endgame_service.py` has direct precedents (`TestScoreGapTimeline`, `TestClockPressureTimeline`) whose shape the Phase 57 tests mirror
- Security: HIGH — no new auth surface; inherits from `current_active_user` on `/overview`

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (30 days — stable backend patterns, stable frontend deps at pinned versions)
