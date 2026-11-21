# Phase 258: Library Stats Recent Sample for Snapshot Charts (SEED-261121-3ou) - Research

**Researched:** 2026-11-21
**Domain:** Backend query windowing (SQLAlchemy 2 async + PostgreSQL window functions) and the Library Stats tab (React 19 + TanStack Query)
**Confidence:** HIGH for the code map, the design and the dev measurements; MEDIUM for prod performance (not measured from here; the SQL to run is below)

## Summary

The three snapshot endpoints (`/library/flaw-comparison`, `/library/facepalm-comparison`, `/library/tactic-comparison`) already share one filter kwargs set and one "analyzed games" seam: every fetch takes an `analyzed_game_ids_subq` argument (`_analyzed_game_ids_subquery(user_id)`) and joins its anchor through `Game.id IN (SELECT game_id FROM analyzed)`. That argument is the cleanest insertion point. Restricting it to the window's game ids (`game_ids_any_predicate`, the Endgames ranked-sample precedent) windows all three fetches **without changing any fetch signature, any COUNT column, or the facepalm fence**. The window itself is one new repository statement: `ROW_NUMBER() OVER (PARTITION BY time_control_bucket ORDER BY played_at DESC, id DESC)` over the endpoint's existing `_filtered_games_base`, with the 36-month bound or the explicit recency filter, keeping `rn <= RECENT_GAMES_PER_TC_CAP`. The counts for the basis line (window games, analyzed, oldest game date, cap reached) come out of the same rows in Python, so the basis line and the tiles cannot disagree (D-06).

The TC switch must keep listing time controls from the unwindowed filtered set (D-15). The cheapest source is the one the switch already reads: `get_flaw_comparison` already runs an unwindowed `count_analyzed_by_tc`. Keep that count unwindowed and use it only to decide which TCs are offered; every per-TC number in the payload becomes windowed. `/flaw-stats` `trend_by_tc` is the wrong source (it drops TCs below the 10-game timeline floor, uses a different "analyzed" definition, and waits on the heavy facepalm-count scan).

Dev measurements (read-only, this session) say the window statement is cheap and the windowed fetches are faster than today: on dev user 28 (5,401 fully analyzed games) today's `get_flaw_comparison` took 290 to 1,542 ms and `get_tactic_comparison` about 420 ms, while the window ids took 4 to 6 ms and the windowed flaw fetch 44 to 57 ms, windowed tactic fetches 77 to 81 ms. The facepalm fetch improved least (287 ms to 214 ms). Prod must still be measured (D-18/D-19); the SQL and the timing method are in "Performance Check".

**Primary recommendation:** add `fetch_recent_window_rows` (one ranked statement) plus a pure `summarize_window` in the backend, thread `now_utc` from `dev_now_utc` into the three services, restrict `_analyzed_game_ids_subquery` to the window ids, keep the unwindowed analyzed count as the TC-offer source, and extend `FlawComparisonTc` with `sample_since`, `cap_reached` and `history_analyzed_n`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (seed "Decided Shape" and roadmap, owner 2026-11-21; not re-discussed)
- **D-01: Split by chart type, no filter-default changes.** The shared filter store keeps `recency: null`.
- **D-02: Timelines keep full history.** Sidebar filters, including an explicit recency choice, crop them as
  today.
- **D-03: Snapshot charts always use the recent sample** (`RECENT_GAMES_PER_TC_CAP` = 1000,
  `RECENCY_WINDOW_MONTHS` = 36, both in `app/services/canonical_slice_sql.py`; reuse the constants, do not
  redefine them).
- **D-04: An explicit recency filter replaces the 36-month bound; the 1000-game cap stays.**
- **D-05: The cap counts all filtered games, then the analyzed subset is shown.** The window is defined by
  time, not by analysis coverage. Thin coverage gives a small sample, never a silently older one.
- **D-06: One shared windowed game set** for the counts and all three comparisons, so the basis line, the
  tiles and the cards always agree.
- **D-07: No "Recent / All games" switch.** The lifetime snapshot is deliberately unreachable.
- **D-08: No default opponent strength of ±100.** The filter stays available and off by default.
- **D-09: Accepted:** the last timeline point (trailing 100 games, `FLAW_TREND_WINDOW`) and the snapshot tile
  (up to 1000 games) show different numbers.
- **D-10: Facepalm rows stay on their own endpoint** with JIT off (257 D-21). The existing analyzed-game
  gates (`FLAW_COMPARISON_GATE`, `TACTIC_COMPARISON_GATE`) and the facepalm low-coverage rule are unchanged;
  they now apply to the windowed set.

#### Cap vs colour filter
- **D-11: Filter first, then cap.** With "Played as: White", the sample is the most recent 1000 White games
  per time control. Colour is treated like platform, rated, opponent type and opponent strength: every
  sidebar filter is applied before the ranking. One code path, no colour special case. Accepted consequence:
  a colour view reaches about twice as far back as the unfiltered view.

#### Basis line
- **D-12: The existing coverage line becomes the basis line, shown once.** `CoverageBasisLine` in the Flaw
  Stats section (currently "1,768 of 1,790 rapid games analyzed in the current filters.") is replaced by the
  basis line, above the tiles. It keeps its analysis-progress icon and hint (updating / low coverage). It is
  not repeated under "You vs. your opponents" or "Tactic motifs", and it does not move into the sticky TC
  bar.
- **D-13: Wording names the bound that actually cut the sample.** Four variants (exact wording may be
  polished, the structure is locked):
  - At the cap, default window: "Based on your most recent 1,000 blitz games (since Mar 2025), 640 analyzed."
  - Under the cap, default window: "Based on your 412 blitz games from the last 36 months, 300 analyzed."
  - At the cap, recency filter set: "Based on your most recent 1,000 blitz games in the selected period
    (since Aug 2026), 640 analyzed."
  - Under the cap, recency filter set: "Based on your 212 blitz games in the selected period, 180 analyzed."
  - "in the current filters" is appended only when a sidebar filter other than recency is active.
  - The API returns what the line needs per time control: the window start date, the number of games in the
    window, the analyzed count, and whether the cap was reached.
- **D-14: The timeline gets a short muted caption at its title: "All games in the current filters".** No
  added popover sentence about the tile-versus-last-point difference.

#### No recent games
- **D-15: A time control with games but none in the window stays on the TC switch,** so its full-history
  timeline remains reachable. The switch therefore has to list time controls from the unwindowed filtered
  set, not only from time controls with snapshot data (today it reads `/flaw-comparison` `tcs`).
- **D-16: One message, snapshot sections hidden.** For such a time control the basis-line slot carries the
  message, and the tiles, "You vs. your opponents" and "Tactic motifs" are not rendered. The page is the
  message plus the timeline.
- **D-17: "All time" stays the untouched default and reads as 36 months for the snapshots.** No filter-store
  change and no relabelled option. The empty-state message names the real way out, for example: "No blitz
  games in the last 36 months. Choose Past 5 years or a custom range under Recency to include older games."
  No button that changes the filter for the user (it would alter the shared filter store).

#### Performance bar
- **D-18: Pass criterion: no slower than today.** Each of the three endpoints is timed before and after on
  the largest prod account, and none may regress. A regression is fixed before merge.
- **D-19: Measured on prod data before the squash-merge,** read-only (`EXPLAIN ANALYZE` of the new query
  shape over the prod tunnel). If an index turns out to be needed, it is measured the same way before any
  migration is written.

### Claude's Discretion
- API field names and schema shape for the window metadata, and whether it rides on `FlawComparisonTc` or a
  shared response field.
- How the windowed set is shared in SQL between counts and the three comparisons (CTE, subquery helper, or
  a repository-level builder).
- Which clock anchors the 36 months: `dev_now_utc` per the project rule, or SQL `NOW()` as the Endgames
  ranked sample does (a documented dev-clock exception there). Prefer `dev_now_utc` unless it breaks plan
  caching or parity with Endgames.
- Which time control is selected by default when the remembered one has no recent games.
- Ties on `played_at` at the cap boundary (a deterministic tiebreak such as game id).
- `data-testid` names and Umami targets (follow the existing library-stats patterns).

### Deferred Ideas (OUT OF SCOPE)
- Full-history timelines on Endgames Stats with the same split (seed follow-on, a separate decision).
- Treating an actively chosen "All time" as an explicit recency choice (needs the filter store to tell an
  untouched default from a chosen value; rejected for this phase).
- Recent-sample treatment for the Results Breakdown section of the Stats tab (not in the roadmap's list).

#### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-08-29-variation-tree-nested-button.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`:
  keyword-only matches, unrelated to this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are mapped. The CONTEXT.md decisions are the requirement set.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | No filter-default change | Frontend: no `FilterPanel` change; regression test on `DEFAULT_FILTERS.recency === null` (Validation) |
| D-02 | Timelines keep full history | `/flaw-stats` path is untouched (`get_flaw_stats`, `fetch_flaw_trend_rows`); test old games still feed the trend |
| D-03 | Snapshots use the recent sample, reuse constants | `fetch_recent_window_rows` imports `RECENT_GAMES_PER_TC_CAP` / `RECENCY_WINDOW_MONTHS`; Pattern 1 |
| D-04 | Explicit recency replaces the 36-month bound | `recent_window_start()` returns `None` when `from_date or to_date` is set; Pattern 2 |
| D-05 | Cap counts all filtered games, then analyzed subset | Rank over the filtered base without the analyzed predicate; analyzed is a column of the window rows |
| D-06 | One shared windowed set | Materialized window ids feed `_analyzed_game_ids_subquery(..., game_ids=)`; counts from the same rows |
| D-07 | No lifetime switch | Nothing to build; no request parameter disables the window |
| D-08 | No default ±100 | Do not reuse `_recent_capped_per_tc_cte` (it hard-codes equal footing) |
| D-09 | Tile vs last timeline point differ | Accepted, no code |
| D-10 | Gates unchanged, applied to the window | `analyzed_n` / `below_gate` computed from windowed counts; facepalm low-coverage unchanged on windowed rows |
| D-11 | Filter first, then cap | Ranking runs over `_filtered_games_base(**same kwargs)`; colour is just another kwarg |
| D-12 | Basis line replaces `CoverageBasisLine`, once | Frontend Pattern 5 |
| D-13 | Four wording variants plus suffix | Pure `librarySampleBasisText`; API fields `total_n`, `analyzed_n`, `sample_since`, `cap_reached`, `recency_filtered` |
| D-14 | Timeline caption | `FlawTrendChart` header (single caller, no prop) |
| D-15 | Quiet TC stays on the switch | Offer TCs from the unwindowed `count_analyzed_by_tc`; windowed `total_n == 0` marks quiet |
| D-16 | Message, sections hidden | `isQuietTc(tcStats)`; VsOpponents and Tactic sections return `null` |
| D-17 | "All time" reads as 36 months | Message copy; quiet state can only occur without a recency filter (see Pitfall 6) |
| D-18 | No slower than today | Interleaved before/after timing script on prod (Performance Check) |
| D-19 | Prod EXPLAIN ANALYZE before merge | SQL statements in Performance Check; orchestrator runs them |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Routers stay thin; logic in services; SQL only in repositories. `APIRouter(prefix="/library")` already set.
- `apply_game_filters` (via `_filtered_games_base`) is the single filter implementation. Never duplicate filter logic; the window ranks the rows it leaves.
- Time-dependent endpoints take `now_utc` from `dev_now_utc` (`app/core/dev_clock.py`), never `datetime.now()` inline.
- Never `asyncio.gather` on one `AsyncSession`; sequential awaits.
- No magic numbers (reuse `RECENT_GAMES_PER_TC_CAP`, `RECENCY_WINDOW_MONTHS`; name new copy constants). `Literal` types instead of bare `str` for fixed value sets; explicit return types; ty clean (`uv run ty check app/ tests/ scripts/`).
- Sentry: `capture_exception` in non-trivial service `except` blocks, context via `set_context`, no variables in messages (the three services already follow this; keep it).
- Nesting depth <= 4 (`scripts/check_function_size.py app/ --fail-over-depth 4`; eslint `max-depth`). `get_flaw_comparison` is already long (about 100 lines); split along pipeline seams (`_fetch` / `_summarize` / `_build`) rather than growing it.
- Comment bug fixes at the fix site.
- Frontend: `text-sm` minimum, theme colours from `theme.ts`, `data-testid` on every interactive element and major container, mobile parity, handle `isError` in every loading chain, `npm run build` before integration (lint/test do not type-check), knip (remove `libraryCoverageBasisText` if it becomes unused).
- Pre-merge gate (full list in root CLAUDE.md) before the squash-merge; `CHANGELOG.md` `[Unreleased]` bullet when the phase merges.
- Never run `bin/reset_db.sh`, never gate a plan on a dev DB reset, never touch `.env` files. Prod access only read-only and from the orchestrator (subagents lack the project MCPs).
- Em-dashes sparingly in UI copy and docs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Window definition (rank, cap, 36-month / recency bound) | Database / Storage (repository statement) | API service (bound computed from `now_utc`) | Ranking over a user's games is a set operation; the bound is business logic |
| Window summary (games, analyzed, oldest date, cap reached) | API / Backend (pure service helper) | — | Derived from the same rows the fetch is restricted to, so it cannot drift |
| Restricting the three comparisons to the window | Database (anchor via `_analyzed_game_ids_subquery`) | — | Existing seam, no fetch signature change |
| TC offer list (unwindowed) | API (`get_flaw_comparison`) | Browser (TC store) | Payload decides offered TCs; switch stays client-side |
| Basis-line wording, quiet-TC message, section hiding | Browser / Client | API supplies fields | Copy depends on sidebar filter state the client owns |
| Clock (`now_utc`) | API router dependency (`dev_now_utc`) | — | Project rule; enables dev-clock and deterministic tests |

## Standard Stack

No new packages. Everything uses what the project already has.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 [VERIFIED: `uv run python -c "import sqlalchemy"`] | `func.row_number().over(partition_by=..., order_by=...)`, subqueries | Project ORM, `select()` API |
| FastAPI | 0.141.1 [VERIFIED: same probe] | `Depends(dev_now_utc)` | Project framework |
| Pydantic | 2.13.5 [VERIFIED: same probe] | Response schema fields (`datetime.date | None`, `bool`) | Project validation |
| PostgreSQL | 18 dev (docker `flawchess-dev-db-1` up) [VERIFIED: `docker ps`] | WindowAgg with run condition | Project DB |
| date-fns | already a dependency [VERIFIED: `frontend/src/lib/recency.ts` imports it; package-legitimacy OK] | `format(date, 'MMM yyyy')` for "since Mar 2025" | Already used by the recency filter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Materialized window ids + `= ANY(:ids)` | Inline the ranked subquery into every count/fetch (`IN (SELECT ... WHERE rn <= 1000)`) | Single statement is easier to EXPLAIN, but the window is recomputed per statement (tactic runs 3), each statement takes its own READ COMMITTED snapshot so counts and fetch can see different sets during an import, and `game_ids_any_predicate`'s own docstring records `IN (subquery)` as the form that hung the planner on large accounts |
| Python `months_before(now_utc, 36)` | SQL `:now - INTERVAL '36 months'` | SQL works with real bind params, but the bound is then not a Python value tests can assert, and `literal_binds` rendering for EXPLAIN breaks it (Pitfall 8) |
| `/flaw-comparison` unwindowed count as TC-offer source | `/flaw-stats` `trend_by_tc` | trend drops TCs under `MIN_GAMES_FOR_TIMELINE = 10`, uses the oracle-column "analyzed" gate, and waits on the facepalm count scan |
| Rename `total_n` to `window_n` | Keep `total_n` / `analyzed_n` names, redefine as windowed | Keeping names makes every existing consumer (gate slot, coverage hint, popover basis, `pickDefaultLibraryTc`) move to windowed numbers for free; rename only if the planner wants the type system to flag every reader |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| date-fns (existing dependency, no install) | npm | many years | 127M/wk | github.com/date-fns/date-fns | OK | Already in use |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Stats tab (sidebar filters, DEFAULT_FLAW_FILTER)
   |  buildLibraryParams -> same params on 3 requests (+ /flaw-stats, unchanged)
   v
Router /library/{flaw,facepalm,tactic}-comparison   <- now_utc = Depends(dev_now_utc)
   |  (from/to date 422 guard as today)
   v
Service
   |-- resolve_library_platforms (as today)
   |-- window_start = None if (from_date or to_date) else months_before(now_utc, 36)
   |-- [flaw only] count_analyzed_by_tc(unwindowed)  -> offered TCs + history_analyzed_n
   |-- [flaw only] page total_n (unwindowed)          -> fresh-import state
   |-- fetch_recent_window_rows(filters, window_start, cap=1000)
   |        SQL: ROW_NUMBER() OVER (PARTITION BY tc ORDER BY played_at DESC, id DESC)
   |             over _filtered_games_base(...) + ply/tc/played_at gates + bound;  rn <= cap
   |        -> rows (game_id, tc, played_at, analyzed, tactic_ready)
   |-- summarize_window(rows) -> per TC: total_n, analyzed_n, tactic_analyzed_n, sample_since, cap_reached
   |-- analyzed_subq = _analyzed_game_ids_subquery(user_id, game_ids=[window ids])
   |-- fetch_flaw_comparison / fetch_facepalm_comparison / fetch_tactic_comparison x2 (unchanged bodies)
   v
Response: per-TC bullets on the window + window metadata
   v
Frontend: TC switch = flaw tcs (unwindowed offer) ; quiet TC (total_n == 0) -> message + timeline only
          else basis line (4 variants + filter suffix) -> tiles -> timeline (caption) -> cards
```

### Recommended Project Structure (files touched)
```
app/repositories/library_repository.py   # fetch_recent_window_rows, RecentWindowRow, _analyzed_game_ids_subquery(game_ids=)
app/services/library_service.py          # recent_window_start, months_before, summarize_window, the 3 services take now_utc
app/schemas/library.py                   # FlawComparisonTc / FlawComparisonResponse fields, docstrings for TacticComparisonTc
app/routers/library.py                   # now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)] on the 3 routes
frontend/src/types/library.ts            # mirror the new fields
frontend/src/lib/flawComparisonMeta.ts   # librarySampleBasisText, quiet-TC copy; libraryBasisText wording (open question)
frontend/src/components/library/stats/LibraryStatsSections.tsx  # basis line, quiet state, section hiding
frontend/src/components/library/FlawTrendChart.tsx              # timeline caption
frontend/src/hooks/useLibraryStatsTc.ts  # default-TC fallback when every TC is quiet
tests/... (see Validation Architecture)
```

### Pattern 1: The window statement (repository)
**What:** one ranked SELECT over the endpoint's existing filtered base. Every sidebar filter is applied before the ranking (D-11). `analyzed` and `tactic_ready` are output columns, not predicates (D-05).
**Example (verified to compile and run on dev, plan below):**
```python
# Source: prototype run this session against the dev DB (scratchpad window_probe.py)
class RecentWindowRow(NamedTuple):
    game_id: int
    tc: TimeControlBucket
    played_at: datetime.datetime
    analyzed: bool        # full_evals_completed_at IS NOT NULL (same gate as _analyzed_game_ids_subquery)
    tactic_ready: bool    # analyzed AND blobs_completed_at IS NOT NULL (tactic basis)

async def fetch_recent_window_rows(
    session: AsyncSession,
    user_id: int,
    *,
    window_start: datetime.datetime | None,   # None = explicit recency filter (D-04)
    cap: int = RECENT_GAMES_PER_TC_CAP,        # keyword so tests can pass a small cap
    **filter_kwargs,                           # spell out the kwargs in the real code (ty)
) -> list[RecentWindowRow]:
    base = _filtered_games_base(user_id, **filter_kwargs).subquery("filtered_window")
    predicates = [
        Game.user_id == user_id,
        Game.id.in_(select(base.c.id)),
        Game.time_control_bucket.isnot(None),   # cannot be placed on the TC switch
        Game.ply_count.isnot(None),
        Game.ply_count > 0,                     # same gate as count_analyzed_by_tc / the anchors
        Game.played_at.isnot(None),             # DESC sorts NULLS FIRST in PostgreSQL
    ]
    if window_start is not None:
        predicates.append(Game.played_at >= window_start)
    ranked = (
        select(
            Game.id.label("game_id"),
            Game.time_control_bucket.label("tc"),
            Game.played_at,
            Game.full_evals_completed_at.isnot(None).label("analyzed"),
            and_(Game.full_evals_completed_at.isnot(None), Game.blobs_completed_at.isnot(None)).label("tactic_ready"),
            func.row_number().over(
                partition_by=Game.time_control_bucket,
                order_by=(Game.played_at.desc(), Game.id.desc()),   # deterministic tiebreak
            ).label("rn"),
        )
        .where(*predicates)
        .subquery("recent_window")
    )
    stmt = select(ranked.c.game_id, ranked.c.tc, ranked.c.played_at, ranked.c.analyzed, ranked.c.tactic_ready).where(ranked.c.rn <= cap)
    return [RecentWindowRow(*row) for row in (await session.execute(stmt)).all()]
```
Dev plan (user 7, 67,244 games, 17,635 in 36 months): `Bitmap Index Scan on ix_games_user_played_at` (Index Cond includes `played_at >= bound`), quicksort 1.3 MB on `(time_control_bucket, played_at DESC, id DESC)`, `WindowAgg` with `Run Condition: (row_number() OVER w1 <= 1000)`; 407 ms cold (9,074 heap blocks read), 74 ms warm; returned 2,109 rows. [VERIFIED: EXPLAIN (ANALYZE, BUFFERS) on dev this session]

### Pattern 2: The bound from `now_utc` (service)
```python
def months_before(moment: datetime.datetime, months: int) -> datetime.datetime:
    """Calendar-month subtraction with month-end clamping, the same as PostgreSQL `ts - INTERVAL 'N months'`."""
    total = moment.year * 12 + (moment.month - 1) - months
    year, month0 = divmod(total, 12)
    day = min(moment.day, calendar.monthrange(year, month0 + 1)[1])
    return moment.replace(year=year, month=month0 + 1, day=day)

def recent_window_start(now_utc, from_date, to_date) -> datetime.datetime | None:
    # D-04: any explicit date bound (a preset sends both, a custom range may send one) replaces the 36 months.
    if from_date is not None or to_date is not None:
        return None
    return months_before(now_utc, RECENCY_WINDOW_MONTHS)
```
PostgreSQL clamps the same way: `'2028-02-29 10:00+00' - interval '36 months'` = `2025-02-28 10:00:00+00`, `'2026-03-31' - 36 months` = `2023-03-31`; dev session `TimeZone` is `UTC`. [VERIFIED: dev DB query this session] The project has no existing month-arithmetic helper and no `python-dateutil` dependency [VERIFIED: grep of app/, scripts/, pyproject.toml, uv.lock].

**Clock choice: `dev_now_utc`.** The Endgames and Openings exceptions exist because their on-read numbers must match persisted Stage A/B percentiles byte for byte (`app/routers/endgames.py:42-46`, `app/routers/openings.py:85-88`). Nothing here is persisted; the zones come from the benchmark DB with its own snapshot date. Plan caching is unaffected: asyncpg prepares per SQL text and the bound is a parameter like `user_id`. The only difference from Endgames is clock skew between app and DB (milliseconds). Tests get a deterministic `now_utc` (service kwarg; router tests use `app.dependency_overrides[dev_now_utc] = lambda: now`, the `tests/test_feature_route.py:184-190` precedent).

### Pattern 3: Sharing the window through the existing analyzed seam
```python
def _analyzed_game_ids_subquery(user_id: int, game_ids: Sequence[int] | None = None) -> Subquery:
    stmt = select(Game.id.label("game_id")).where(
        Game.user_id == user_id, Game.full_evals_completed_at.isnot(None)
    )
    if game_ids is not None:
        # Phase 258: restrict to the recent window (D-06); one bound int[] param, never IN (subquery).
        stmt = stmt.where(game_ids_any_predicate(Game.id, game_ids))
    return stmt.subquery("analyzed")
```
Pass only the **analyzed** window ids (at most 4 x 1000). `fetch_flaw_comparison`, `fetch_facepalm_comparison` (through `_flaw_comparison_anchor`) and `fetch_tactic_comparison` already join `Game.id.in_(select(analyzed_game_ids_subq.c.game_id))`, so their bodies stay untouched and the facepalm `.offset(0)` fence keeps working (its inner scan reads `anchor_subq.c.game_id`). `game_ids_any_predicate` binds `ARRAY(Integer)` with `unique=True` [VERIFIED: app/repositories/query_utils.py:152-166, quoted: `ids_param = bindparam("ranked_game_ids", value=list(game_ids), type_=ARRAY(Integer), unique=True)`]. When the window has no analyzed game, skip the fetch and return empty rows (an `ANY('{}')` statement is valid but pointless).

Dev timing of this exact seam (warm, round 2; dev user 28): window ids 4 ms; windowed `fetch_flaw_comparison` 44 ms vs today's whole `get_flaw_comparison` 290 ms; windowed `fetch_facepalm_comparison` 214 ms vs today 287 ms; windowed tactic fetches x2 77 ms vs today 416 ms. [VERIFIED: scratchpad endpoint_probe.py, read-only transaction]

### Pattern 4: Service shape for `get_flaw_comparison`
1. `offered = count_analyzed_by_tc(..., analyzed_only=True)` **unwindowed**, as today. Decides which TCs appear (D-15) and gives `history_analyzed_n`.
2. Page `total_n` unwindowed, as today (`count_analyzed_by_tc(analyzed_only=False)` summed) for the "nothing analyzed yet" state. Optionally fold steps 1 and 2 into one GROUP BY with `count(*) FILTER (...)` to keep the statement count flat.
3. `rows = fetch_recent_window_rows(...)`; `summary = summarize_window(rows, cap)` (pure).
4. `fetch_flaw_comparison(..., analyzed_subq restricted to summary analyzed ids)`.
5. Build one `FlawComparisonTc` per offered TC: `analyzed_n` and `total_n` from the window summary (0 for a quiet TC), `below_gate = analyzed_n < FLAW_COMPARISON_GATE`, bullets over that TC's rows (zero-event placeholders for a quiet TC, which the frontend does not render).

`get_tactic_comparison`: window rows, `tactic_analyzed_n` per TC from `tactic_ready`, list TCs with `tactic_analyzed_n > 0` as today (the frontend hides the section for a quiet TC anyway), two fetches with the restricted subquery. `get_facepalm_comparison`: window rows, one fetch. Call `disable_jit_for_transaction` before the window statement in the facepalm path (Pitfall 4).

**Which filters the window ranks over.** Use exactly the kwargs each endpoint already passes to its base (including `flaw_severity` and `tactic_families` when present). The Stats tab sends neither (`DEFAULT_FLAW_FILTER` has `severity: []`, `tacticFamilies: []`, and `useTacticComparison` does not send families) [VERIFIED: frontend/src/hooks/useLibrary.ts, useFlawFilterStore.ts:54-65], so every real page load ranks the identical set on all three endpoints (D-06), and the existing invariant "analyzed_n matches the set the bullets aggregate over" (`test_severity_filter_zones`) keeps holding for API callers that do send them. This is D-11's "every filter before the ranking, one code path" read literally.

### Pattern 5: Frontend basis line and quiet state
- `librarySampleBasisText({ tc, totalN, analyzedN, capReached, sampleSince, recencyFiltered, otherFiltersActive, windowMonths })`, a pure function with the four D-13 variants. "since" is the **oldest game in the sample** (`sample_since`, shown only at the cap), formatted `format(parseISO(sampleSince), 'MMM yyyy')`. Numbers via `toLocaleString('en-US')` (existing convention in `libraryCoverageBasisText`).
- `otherFiltersActive = !areFiltersEqual(filters, DEFAULT_FILTERS, BASIS_FILTER_FIELDS)` with `BASIS_FILTER_FIELDS` = the library fields minus `recency` and `customRange` (and minus `matchSide`, which the Library never sends). `LIBRARY_FILTER_DOT_FIELDS` is `[...FILTER_DOT_FIELDS, 'pasted']` with `FILTER_DOT_FIELDS = ['matchSide','timeControls','platforms','rated','opponentType','opponentStrength','recency','customRange','playedAs']` [VERIFIED: frontend/src/components/filters/FilterPanel.tsx:128-151]. Note `DEFAULT_FILTERS` has `rated: true, opponentType: 'human'` [VERIFIED: FilterPanel.tsx:96-108], so the default view gets no suffix.
- Keep the `Cpu` icon, the `isUpdating` / `isLowCoverage` thresholds and hints, the guest CTA and the `flaw-stats-coverage-info` popover from `CoverageBasisLine`; the ratios now use windowed `analyzedN / totalN`.
- Quiet TC: `tcStats.total_n === 0`. `FlawStatsSection` renders the message in the basis-line slot plus `FlawTimeline`; `VsOpponentsSection` and `TacticMotifsSection` return `null` (heading included). Message: "No {tc} games in the last {windowMonths} months. Choose Past 5 years or a custom range under Recency to include older games." Testids: `flaw-stats-basis` (keep), `flaw-stats-no-recent` (new container, not interactive). No new interactive element, so no new Umami target.
- Timeline caption: inside `FlawTrendChart`'s `CardHeader` after "Flaws Timeline", a muted `text-sm` span "All games in the current filters" with `data-testid="flaw-trend-caption"`. Single caller, so no prop (owner preference: tweak constants over opt-in props).

### Recommended schema (Claude's discretion)
```python
class FlawComparisonTc(BaseModel):
    tc: TimeControlBucket
    analyzed_n: int        # analyzed games in the recent window (gate basis)          <- redefined
    total_n: int           # games in the recent window, analyzed or not (0 = quiet TC) <- redefined
    below_gate: bool
    sample_since: datetime.date | None   # oldest game in the window; None when total_n == 0
    cap_reached: bool                    # total_n >= RECENT_GAMES_PER_TC_CAP
    history_analyzed_n: int              # unwindowed analyzed games (why the TC is offered; default-TC fallback)
    bullets: list[FlawBullet]
    tempo_phase_cells: list[TempoPhaseCell]

class FlawComparisonResponse(BaseModel):
    tcs: list[FlawComparisonTc]
    analyzed_gate: int
    total_n: int            # unwindowed, unchanged meaning (fresh-import state)
    recency_filtered: bool  # from_date or to_date set: names the bound in the basis line
    window_months: int      # RECENCY_WINDOW_MONTHS, so the frontend does not mirror it a third time
    games_cap: int          # RECENT_GAMES_PER_TC_CAP
```
Rationale: the basis line lives in the Flaw Stats section, which already reads `/flaw-comparison`; putting the metadata there means one request drives the switch, the basis line and the tiles. `TacticComparisonTc.analyzed_n` keeps its name with a windowed docstring. `FacepalmComparisonTc` needs no new field. The frontend already mirrors the two constants once (`frontend/src/components/openings/stats/outOfOpeningCopy.ts:23-25`); returning them avoids another copy.

### Anti-Patterns to Avoid
- **Reusing `_recent_capped_per_tc_cte` / `ranked_games_sql`:** they hard-code the benchmark universal filter (`g.rated AND NOT g.is_computer_game`, both ratings non-null, `abs(...) <= 100` equal footing) and one TC per call [VERIFIED: app/services/canonical_slice_sql.py:308-340]. That would silently impose D-08's rejected ±100 and ignore colour/platform filters. Reuse only the constants.
- **Putting `full_evals_completed_at IS NOT NULL` before the ranking:** violates D-05 (the sample would reach back until it found 1000 analyzed games).
- **Windowing `/flaw-stats`:** violates D-02. Its only change is nothing (the caption is frontend).
- **Reading the TC list from the tactic or facepalm payloads:** they omit quiet TCs. The switch keeps reading `useLibraryFlawComparison(...).data.tcs` [VERIFIED: LibraryStatsSections.tsx `LibraryStatsTcSwitch`; useLibraryStatsTc.ts `useSelectedLibraryStatsTc`, which GlobalStats.tsx:68 uses for the ELO charts].
- **`datetime.now()` in the service:** project rule; take `now_utc` from the router.
- **A frontend button that sets the recency filter:** rejected by D-17.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filter composition for the ranked set | New WHERE clauses | `_filtered_games_base` -> `apply_game_filters` | Single filter implementation (CLAUDE.md), handles platform default exclusion, pasted, gap bounds, colour |
| Restricting statements to an id set | `IN (1,2,...)` literal lists or `IN (subquery)` | `game_ids_any_predicate` | One bound `int[]`; the subquery form is documented as hanging the planner |
| Paired gap stats, gates, zones | Anything new | Existing `_compute_bullets`, `_compute_tempo_phase_cells`, `_compute_tactic_bullets`, `_facepalm_comparison_tc` | Unchanged; they just receive fewer rows |
| JIT suppression | A new SET | `disable_jit_for_transaction` | `SET LOCAL`, transaction-scoped, already the 257 D-21 mechanism |
| "Filters modified" detection | Hand-written field comparisons | `areFiltersEqual(filters, DEFAULT_FILTERS, fields)` | Set-equality for arrays already handled |
| Default TC choice | New picker | `pickMostPopulatedTc` via `pickDefaultLibraryTc` | Pin semantics and tie order already tested |

**Key insight:** the existing code already has every seam this phase needs. The new logic is one ranked statement, one month helper, one pure summary and copy. Anything bigger is scope creep.

## Common Pitfalls

### Pitfall 1: Test seeds have no `played_at`
**What goes wrong:** after the change, every comparison test that seeds games without `played_at` gets an empty window and fails (or worse, passes on zero-event placeholders).
**Why:** `_seed_game` in `tests/services/test_flaw_comparison.py` builds `Game(...)` without `played_at` (nullable column) [VERIFIED: test file lines 66-95; app/models/game.py:225 `played_at: Mapped[datetime.datetime | None]`]. The same applies to `tests/services/test_tactic_comparison_service.py` and `tests/routers/test_library_tactic_comparison.py` (no `played_at` in either) [VERIFIED: grep]. `tests/test_library_router.py` seeds fixed dates such as `datetime.datetime(2026, 1, 1, ...)`, which fall out of a real-clock 36-month window in 2029.
**How to avoid:** a module-level `_NOW` per test file, seeds default `played_at=_NOW - timedelta(days=1)` (or an incrementing offset), services called with `now_utc=_NOW`; router tests pin `dev_now_utc` via `dependency_overrides`. About 60 service call sites in the two service test files take the new kwarg (39 in test_flaw_comparison.py, 21 in test_tactic_comparison_service.py) [VERIFIED: grep -c]. Plan this as its own task; it is mechanical but large.
**Warning signs:** tests asserting `tcs == []` start passing for the wrong reason.

### Pitfall 2: NULL `played_at` takes cap slots
**What goes wrong:** PostgreSQL sorts `DESC` with NULLS FIRST, so NULL-dated games rank first.
**How to avoid:** `Game.played_at.isnot(None)` in the window predicates (Pattern 1). The 36-month bound excludes NULLs anyway; the explicit predicate covers the recency-filter path too.

### Pitfall 3: Counts and fetch on different populations
**What goes wrong:** `analyzed_n` from one definition, bullets from another (the bug `count_filtered_and_analyzed`'s docstring records).
**How to avoid:** `analyzed` in the window rows uses the same `full_evals_completed_at IS NOT NULL` gate as `_analyzed_game_ids_subquery`; the fetch receives exactly the analyzed ids the summary counted; tactic counts use `tactic_ready` = analyzed AND `blobs_completed_at IS NOT NULL`, the same gate as `fetch_tactic_comparison`'s anchor and `count_analyzed_by_tc(require_tactic_blobs=True)`.
**Test:** facepalm rows game ids == flaw rows game ids == analyzed window ids.

### Pitfall 4: JIT on the new window statement
**What goes wrong:** prod JIT defaults are on with `jit_above_cost` 100000 (dev shows `jit=on`, `jit_above_cost=100000`) [VERIFIED: dev `current_setting`]; prod tuning does not set `jit` [VERIFIED: docs/production-runbook.md:36 lists shared_buffers, effective_cache_size, work_mem, maintenance_work_mem, max_connections, max_wal_size, wal_compression only]. The dev window plan already costs about 86,500 for 17,635 rows; a larger prod account crosses 100,000 and pays JIT compile time on a cheap statement.
**How to avoid:** in the facepalm path move `disable_jit_for_transaction(session)` before the window statement (the window runs in the same transaction). For the flaw and tactic paths, read the prod EXPLAIN (`JIT:` block) and add the same call only if JIT shows up with meaningful time. Measure; do not guess.

### Pitfall 5: Default TC when every TC is quiet
**What goes wrong:** `pickDefaultLibraryTc` picks the TC with most `analyzed_n` among non-below-gate TCs; if all are quiet, all have `analyzed_n = 0` and the fastest TC wins, possibly one with three old games and no timeline.
**How to avoid:** when every offered TC has `total_n === 0`, rank by `history_analyzed_n`. Keep the stored (remembered) choice when it is still offered, even if quiet: the store's contract is "holds only what the user chose" (tcSelectionStore.ts doc), and D-15 exists precisely to keep that timeline reachable.

### Pitfall 6: The quiet state only exists without a recency filter
With a recency filter the window is the top 1000 of the already-cropped filtered set, so a TC offered (analyzed games in the filtered set) always has a non-empty window. The D-17 message therefore only needs the 36-month wording. A test should pin this (TC with only 4-year-old games: quiet by default, non-quiet with `from_date` 5 years back).

### Pitfall 7: Copy that still says "in the current filters"
`libraryBasisText` ("Based on your 1,841 analyzed rapid games in the current filters.") feeds popovers in FlawTiles, ContextTagCards, TempoPhaseHeatmap, FacepalmCard and MostCommonTacticsCard [VERIFIED: grep]. After the change the number is the windowed count, so the sentence understates the restriction. Not covered by a locked decision (see Open Questions).

### Pitfall 8: `literal_binds` breaks interval arithmetic in EXPLAIN scripts
Compiling `literal(now) - INTERVAL '36 months'` with `literal_binds` renders `'2026-11-21 ...' - INTERVAL '36 months'`, which PostgreSQL parses as interval minus interval and rejects (`invalid input syntax for type interval`) [VERIFIED: error reproduced this session]. Another reason to compute the bound in Python; any EXPLAIN script should render a timestamp literal or keep bind params.

### Pitfall 9: `get_flaw_comparison` size
It is about 100 lines with two count queries. Adding the window inline pushes it past the soft guidance. Split into `_fetch_flaw_comparison_inputs` (DB, sequential) and a pure `_build_flaw_comparison_tcs` (the Endgames `fetch_ranked_inputs` / `build_ranked_stats` precedent).

### Pitfall 10: Shared-checkout and long prod runs
Memory: concurrent agents in one checkout land commits on the wrong branch; executor runs die about 40 minutes into long DB plans; prod work runs from the orchestrator; prod `max_connections=50` (keep operator connections under about 25); prod reboots around 02:15 UTC. The timing script uses one connection and runs in minutes.

## Code Examples

### Pure summary (service)
```python
@dataclass(frozen=True)
class TcWindowSummary:
    total_n: int
    analyzed_n: int
    tactic_analyzed_n: int
    sample_since: datetime.date | None
    cap_reached: bool
    analyzed_ids: list[int]
    tactic_ids: list[int]

def summarize_window(rows: Sequence[RecentWindowRow], cap: int) -> dict[TimeControlBucket, TcWindowSummary]:
    ...  # group by tc; sample_since = min(played_at).date(); cap_reached = total_n >= cap
```
Keep it pure so it is unit-tested without the DB.

### Router
```python
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]   # app/routers/openings.py:31 precedent

@router.get("/flaw-comparison", response_model=FlawComparisonResponse)
async def get_flaw_comparison(..., now_utc: NowUtc, ...) -> FlawComparisonResponse:
    ...
    return await library_service.get_flaw_comparison(session, user_id=user.id, now_utc=now_utc, ...)
```

### Frontend basis text (shape)
```ts
export function librarySampleBasisText(b: SampleBasis): string {
  const n = (x: number) => x.toLocaleString('en-US');
  const scope = b.otherFiltersActive ? ' in the current filters' : '';
  const since = b.sampleSince ? ` (since ${format(parseISO(b.sampleSince), 'MMM yyyy')})` : '';
  const head = b.capReached
    ? `most recent ${n(b.totalN)} ${b.tc} games${b.recencyFiltered ? ' in the selected period' : ''}${since}`
    : `${n(b.totalN)} ${b.tc} games ${b.recencyFiltered ? 'in the selected period' : `from the last ${b.windowMonths} months`}`;
  return `Based on your ${head}${scope}, ${n(b.analyzedN)} analyzed.`;
}
```
Where the suffix goes inside the sentence is a wording call (D-13 allows polish); the planner should fix one placement and table-test all eight combinations.

## Performance Check (D-18 / D-19)

**Status: unmeasured on prod.** This agent has no prod access. The orchestrator (or owner) runs these after `bin/prod_db_tunnel.sh`.

**Step 1: pick the account(s)** via the `flawchess-prod-db` MCP:
```sql
SELECT user_id,
       count(*) AS games,
       count(*) FILTER (WHERE full_evals_completed_at IS NOT NULL) AS analyzed,
       count(*) FILTER (WHERE played_at >= now() - interval '36 months') AS recent_36m
FROM games
WHERE platform NOT IN ('flawchess', 'pgn') AND rated AND NOT is_computer_game
GROUP BY user_id
ORDER BY analyzed DESC
LIMIT 5;
```
Measure the top account by `analyzed` (the fetch cost driver; 257 used this) and, if different, the top by `games` (the window sort cost driver).

**Step 2: EXPLAIN the window statement** (Stats-tab default filters: rated, human, default platform exclusion, no recency; replace `:uid`):
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT r.game_id, r.tc, r.played_at, r.analyzed, r.tactic_ready
FROM (
  SELECT g.id AS game_id, g.time_control_bucket AS tc, g.played_at,
         g.full_evals_completed_at IS NOT NULL AS analyzed,
         (g.full_evals_completed_at IS NOT NULL AND g.blobs_completed_at IS NOT NULL) AS tactic_ready,
         row_number() OVER (PARTITION BY g.time_control_bucket
                            ORDER BY g.played_at DESC, g.id DESC) AS rn
  FROM games g
  WHERE g.user_id = :uid
    AND g.platform NOT IN ('flawchess', 'pgn') AND g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL AND g.ply_count IS NOT NULL AND g.ply_count > 0
    AND g.played_at IS NOT NULL AND g.played_at >= now() - interval '36 months'
) r
WHERE r.rn <= 1000;
```
Expect: `ix_games_user_played_at` index scan, a sort, `WindowAgg` with `Run Condition`. Read the `JIT:` block (Pitfall 4). Also run it with `played_at >= now() - interval '5 years'` (the "Past 5 years" path, larger sort).

**Step 3: before/after wall time per endpoint (the D-18 gate).** Write `temp/library-258/time_snapshot_endpoints.py` (gitignored `temp/`, per the drafts-in-temp convention): connects with `db_url_for_target("prod")` [VERIFIED: app/core/config.py:247-263], opens a `SET TRANSACTION READ ONLY` transaction per call, and for the target user times, interleaved for at least 3 rounds (memory: wall-clock drift needs interleaved arms):
- arm "today": `count_analyzed_by_tc` x2 + `fetch_flaw_comparison(_analyzed_game_ids_subquery(uid))`; `fetch_facepalm_comparison(... unwindowed)`; tactic count + 2 fetches. These primitives survive the change (`_analyzed_game_ids_subquery` with `game_ids=None` is today's behaviour), so both arms run in one process after implementation.
- arm "windowed": the new `get_flaw_comparison` / `get_facepalm_comparison` / `get_tactic_comparison` with `now_utc=datetime.now(UTC)`.
Pass: each endpoint's windowed median <= today median (D-18). The script can also capture the executed SQL with a `before_cursor_execute` listener and re-run it under `EXPLAIN (ANALYZE, BUFFERS)` for the fetch statements [ASSUMED: listener-based capture mechanics; verify on dev first]. Run from the orchestrator, one connection, a few minutes.

**Index question (D-19).** A `(user_id, time_control_bucket, played_at DESC)` index would let each partition be read in order, but the dev plan shows the cost is heap reads of the user's games (which today's count queries already pay), not the sort (1.3 MB quicksort). Expected: no index needed [ASSUMED until the prod EXPLAIN]. If one is needed, measure it on a non-prod DB first, then write the migration (D-19).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Lifetime snapshot per TC | Most recent 1000 games per TC in 36 months (or the selected period) | This phase | Tiles and cards describe current play and match the zone basis |
| SQL `NOW()` for recent windows (Endgames, Openings exceptions) | `dev_now_utc` where nothing persisted must match | This phase | Dev-clock testable |
| Benchmark CTE without tiebreak (`ORDER BY played_at DESC`) | `played_at DESC, id DESC` here | This phase | Deterministic at ties; differs from the benchmark only on exact timestamp ties |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prod endpoints get faster, not slower, with the window | Summary, Performance Check | D-18 fails; fix before merge (JIT, index or plan shape) |
| A2 | No new index is needed | Performance Check | A migration task appears after the prod EXPLAIN |
| A3 | `before_cursor_execute` capture works for EXPLAINing the fetch statements | Performance Check | Fall back to wall timings plus the window EXPLAIN |
| A4 | Treating a `to_date`-only custom range as an explicit recency filter matches the owner's intent | Pattern 2 | Copy says "in the selected period" for a range without a start; low impact |
| A5 | Keeping the remembered TC even when it is quiet is preferred over auto-switching | Pitfall 5 | Owner may prefer jumping to a TC with recent data; one-line change in the picker |
| A6 | The popover `libraryBasisText` wording should change too | Pitfall 7, Open Questions | Popovers keep saying "in the current filters" for a windowed number |

## Open Questions

1. **Popover basis sentences (`libraryBasisText`).**
   - What we know: five components show "Based on your N analyzed {tc} games in the current filters." and N becomes windowed.
   - What's unclear: whether the owner wants them reworded; D-12 only says the basis line is not repeated under the cards.
   - Recommendation: change to "Based on your N analyzed {tc} games in the recent sample." (a popover is not a repeated basis line) and confirm at UAT.
2. **Fresh-import state wording.** When no game is analyzed yet, `tcs` is empty and the page shows "0 of N games analyzed in the current filters." with unwindowed N. Recommendation: keep `libraryCoverageBasisText` for this `tc === null` branch only (no window exists without a TC); confirm at UAT.
3. **Where "in the current filters" sits in the sentence.** D-13 allows polish. Recommendation: after the games clause, before ", N analyzed."; fix it in the plan and table-test it.
4. **Prod numbers.** Unmeasured here; Performance Check steps 1 to 3 are orchestrator items, step 3 gates the merge.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (docker) | Backend tests, dev probes | ✓ (`flawchess-dev-db-1` healthy) | 18 | — |
| Python / uv venv | Backend | ✓ | 3.14, SQLAlchemy 2.0.52 | — |
| Node | Frontend build/tests | ✓ | v24.19.0 | — |
| Prod DB tunnel + `flawchess-prod-db` MCP | D-18/D-19 | Not from this subagent | — | Orchestrator runs it (memory: subagents lack project MCPs) |
| `DATABASE_URL_PROD` for the timing script | D-18 | Present in settings via `db_url_for_target` (not inspected; `.env` is protected) | — | MCP EXPLAIN only |

**Missing dependencies with no fallback:** none for implementation. The prod measurement needs the orchestrator.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend, per-worker cloned Postgres DB); Vitest + Testing Library (frontend) |
| Config file | `pyproject.toml` (`addopts` ignores `tests/scripts/benchmarks` and `tests/scripts/tagger`); `frontend` vitest config |
| Quick run command | `uv run pytest tests/services/test_flaw_comparison.py tests/services/test_tactic_comparison_service.py tests/services/test_library_window.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm test -- --run )` |

### Decision -> Test Map
| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| D-03 | Per-TC cap: 5 blitz + 2 rapid with `cap=3` -> blitz 3 newest, rapid 2; `cap_reached` true/false | repo integration | `uv run pytest tests/services/test_library_window.py -k cap -x` | ❌ Wave 0 |
| D-03 | Real constant: 1001 games -> 1000 in window (bulk insert) | repo integration | same file `-k real_cap` | ❌ Wave 0 |
| D-03 | 36-month bound with fixed `now_utc`: 35-month game in, 37-month game out | repo integration | `-k bound` | ❌ Wave 0 |
| D-03 | `months_before` matches PG clamping (Feb 29, Mar 31 cases) | unit | `-k months_before` | ❌ Wave 0 |
| D-04 | `from_date` 5 years back includes the 37-month game; cap still applies; `to_date`-only also explicit; `recency_filtered` flag | repo + service | `-k recency` | ❌ Wave 0 |
| D-05 | 3 newest unanalyzed + older analyzed, `cap=3` -> `analyzed_n == 0`, older games excluded | service | `-k cap_counts_unanalyzed` | ❌ Wave 0 |
| D-06 | Facepalm rows ids == flaw rows ids == analyzed window ids; tactic ids == tactic-ready window ids | service | `uv run pytest tests/services/test_flaw_comparison.py -k same_game_set -x` | Partly (extend `test_facepalm_anchor_same_game_set_as_flaw_comparison`) |
| D-06 | `total_n`/`analyzed_n` equal the window summary for each TC | service | `-k window_counts` | ❌ Wave 0 |
| D-10 | 25 analyzed games of which 15 in window -> `below_gate` true; facepalm low-coverage evaluated on windowed rows | service | `-k gate_on_window` | ❌ Wave 0 |
| D-11 | `color="white"` window = newest `cap` white games, reaching past mixed-colour newer games | service | `-k filter_first` | ❌ Wave 0 |
| Tiebreak | Equal `played_at` at the boundary -> higher id wins, stable across calls | repo | `-k tiebreak` | ❌ Wave 0 |
| Gates | NULL `played_at`, `ply_count` 0/NULL, NULL TC never occupy a slot | repo | `-k excluded_rows` | ❌ Wave 0 |
| D-15 | TC with only old analyzed games: in flaw `tcs` with `total_n == 0`, `history_analyzed_n > 0`; absent from tactic/facepalm | service | `-k quiet_tc` | ❌ Wave 0 |
| D-02 | `/flaw-stats` trend still includes games older than 36 months | service | `uv run pytest tests/services/test_library_service.py -k trend_full_history -x` | ❌ Wave 0 |
| Clock | Router honours `dev_now_utc` override (window shifts); response carries `recency_filtered`, `window_months`, `games_cap`, per-TC `sample_since`, `cap_reached` | router | `uv run pytest tests/test_library_router.py -k window -x` | ❌ Wave 0 |
| Security | Two-user isolation: the window never includes another user's games | service | `-k two_user` (extend existing isolation tests) | Partly |
| D-01 | `DEFAULT_FILTERS.recency === null`, untouched | frontend unit | `cd frontend && npm test -- --run FilterPanel` | ❌ Wave 0 (one assertion) |
| D-12/D-13 | Four variants x suffix on/off; "since" only at the cap; numbers en-US | frontend unit | `npm test -- --run flawComparisonMeta` | ❌ Wave 0 |
| D-12 | Basis line rendered once, keeps icon, hint, guest CTA, info popover; not in cards or sticky bar | component | `npm test -- --run LibraryStatsSections` | Update existing "coverage basis line" block |
| D-14 | Caption "All games in the current filters" in the timeline header | component | same | ❌ Wave 0 |
| D-15/D-16/D-17 | Quiet TC on the switch; message shown; tiles, VsOpponents, Tactic sections absent; timeline present; message names "Past 5 years" | component | same | ❌ Wave 0 |
| Default TC | All TCs quiet -> pick by `history_analyzed_n`; remembered quiet TC kept | unit | `npm test -- --run useLibraryStatsTc` | ❌ Wave 0 |
| D-18/D-19 | Prod before/after timings, window EXPLAIN | manual (orchestrator) | `temp/library-258/time_snapshot_endpoints.py` + MCP SQL | ❌ operator item |

### Sampling Rate
- **Per task commit:** the quick backend command, plus the affected frontend test file.
- **Per wave merge:** `uv run pytest -n auto -x`; `cd frontend && npm run lint && npm run build && npm test -- --run`.
- **Phase gate:** full pre-merge gate from root CLAUDE.md, plus the prod performance item green, before `/gsd-verify-work` and the squash-merge.

### Wave 0 Gaps
- [ ] `tests/services/test_library_window.py`: window repository + `months_before` + `summarize_window` tests
- [ ] Seed helpers in `tests/services/test_flaw_comparison.py`, `tests/services/test_tactic_comparison_service.py`, `tests/routers/test_library_tactic_comparison.py`, `tests/test_library_router.py`: default `played_at` relative to a fixed `_NOW`, services called with `now_utc=_NOW`, router tests pin `dev_now_utc`
- [ ] Frontend fixtures `frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts`: new fields (`sample_since`, `cap_reached`, `history_analyzed_n`, response `recency_filtered`, `window_months`, `games_cap`)
- [ ] Baseline prod timing (Performance Check step 3 "today" arm) can run any time; the gate comparison runs after implementation

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | FastAPI-Users `current_active_user` |
| V3 Session Management | no | — |
| V4 Access Control | yes | `user_id` only from `current_active_user`; window statement scoped by `Game.user_id`; window ids come from our own query, never the request (same rule as `game_ids_any_predicate`) |
| V5 Input Validation | yes | Existing `from_date > to_date` 422 guard; typed `datetime.date` params; no new request parameter |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR via a game-id list | Information disclosure | No request parameter accepts ids; ids are derived per request from the authenticated user's games |
| Expensive query per request | Denial of service | Cap bounds the id array to at most 4 x 1000; window uses `ix_games_user_played_at`; prod timing gate (D-18) |
| SQL injection through f-strings | Tampering | SQLAlchemy expressions and bound params only; no f-string SQL in the new statement |

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/canonical_slice_sql.py:121-126` (constants, quoted: `RECENT_GAMES_PER_TC_CAP: int = 1000`, `RECENCY_WINDOW_MONTHS: int = 36`), `:198-215`, `:308-340`
- `app/repositories/library_repository.py:1743-1796` (`_filtered_games_base`), `:1888-1905` (`_analyzed_game_ids_subquery`), `:1992-2073` (`count_analyzed_by_tc`), `:2129-2193` (`_flaw_comparison_anchor`), `:2196-2663` (the three fetches), `:1659-1668` (`disable_jit_for_transaction`)
- `app/services/library_service.py:1119` (`FLAW_TREND_WINDOW = 100`), `:1523` (`FLAW_COMPARISON_GATE: int = 20`), `:1545`, `:1823-1927`, `:1930-1989`, `:1999` (`TACTIC_COMPARISON_GATE: int = 20`), `:2097-2209`
- `app/services/openings_service.py:63` (`MIN_GAMES_FOR_TIMELINE = 10`)
- `app/repositories/query_utils.py:152-166`, `:169-340`
- `app/routers/library.py` (full), `app/routers/endgames.py:30-50`, `app/routers/openings.py:31, 85-88`, `app/core/dev_clock.py`
- `app/models/game.py:45-123` (indexes, quoted: `Index("ix_games_user_played_at", "user_id", sa.text("played_at DESC"))`), `:150-229`
- `app/services/endgame_ranked_service.py:186-231` (materialized-ids precedent), `app/repositories/endgame_ranked_repository.py`
- `app/schemas/library.py:315-335, 455-520, 564-595`
- Frontend: `src/hooks/useLibrary.ts`, `src/hooks/useLibraryStatsTc.ts`, `src/hooks/tcSelectionStore.ts`, `src/components/library/stats/LibraryStatsSections.tsx`, `src/lib/flawComparisonMeta.ts:311-326`, `src/components/filters/FilterPanel.tsx:96-151`, `src/lib/recency.ts`, `src/components/library/FlawTrendChart.tsx:155-180`, `src/pages/GlobalStats.tsx:55-80`
- Dev DB probes (read-only): window EXPLAIN, endpoint timings, PG interval clamping, JIT settings

### Secondary
- `.planning/phases/257-facepalm-rate-library-stats/257-05-SUMMARY.md`, `257-07-SUMMARY.md` (prior prod-measurement method)

### Tertiary
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new dependencies, versions probed.
- Architecture: HIGH, every seam read in code and the window seam prototyped on dev.
- Pitfalls: HIGH for code-derived ones; MEDIUM for prod JIT behaviour.
- Performance: MEDIUM, dev only; prod is an explicit gate.

**Research date:** 2026-11-21
**Valid until:** 2026-12-21 (stable code area; re-check if the library repository changes before planning)
