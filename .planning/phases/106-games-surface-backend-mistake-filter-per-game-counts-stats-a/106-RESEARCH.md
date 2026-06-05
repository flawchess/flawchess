# Phase 106: Games-Surface Backend — Mistake Filter, Per-Game Counts & Stats Aggregates - Research

**Researched:** 2026-06-05
**Domain:** Async SQLAlchemy 2.x window-function queries over `game_positions ⋈ games`; reuse of the Phase 105 `mistakes_service` kernel; on-the-fly mistake aggregation (no materialization).
**Confidence:** HIGH (entirely codebase-internal; every claim below is grounded in a read file with line numbers).

## Decisions Locked (user, 2026-06-05 — resolved before planning)

These resolve the two open forks below. The planner MUST follow them and need not re-open them.

- **D1 — Tagging architecture: PRAGMATIC kernel-reuse (Open Question 1 / "Critical Contradiction" → RESOLVED).** SQL window-scan handles ONLY the `EXISTS` severity filter, the per-severity flagged-row count aggregates, and the ≥90% analyzed denominator. Tags come from re-calling the existing Phase 105 kernel (`classify_game_mistakes`) per game — over the returned page for card chips, and over the analyzed filtered set for the stats tag-distribution. Add ONE small additive `count_game_severities(game, positions) -> SeverityCounts | GameNotAnalyzed` helper to `mistakes_service.py` for the inaccuracy count (per A3). Do **NOT** refactor the private tag functions into a public row-shaped API; shipped 105 code stays untouched except for that additive helper. The single SQL severity-math transcription is guarded by the cross-check fixture test (criterion 5). Benchmark the O(analyzed games) stats-path kernel calls (A4); if a power user's analyzed set proves too large, that's a follow-up optimization, not in-scope for 106.
- **D2 — Endpoints: NEW `/library` router (Open Question 2 → RESOLVED).** Create `app/routers/library.py` (prefix `/library`, `GET /games` + `GET /mistake-stats`), `app/services/library_service.py`, `app/repositories/library_repository.py`, `app/schemas/library.py`. Extend `apply_game_filters()` in place with the mistake-`EXISTS` param. Do not fold into openings/endgames.
- **D3 — Trend bucketing (Open Question 3):** rolling-game-window via the `get_time_series` machinery (researcher recommendation; planner's discretion on window size).

## Summary

Phase 106 builds two read-only HTTP endpoints for the Library "Games" subtab, both derived on-the-fly. The good news: Phase 105 already shipped the complete pure-Python kernel (`app/services/mistakes_service.py`) and a repository (`app/repositories/mistakes_repository.py`), and the codebase already has every reusable piece this phase needs — `apply_game_filters()`, the `GameRecord` schema, a canonical paginated-archive query (`query_endgame_games`), the ES sigmoid (`eval_cp_to_expected_score`), a rolling-window time-series precedent (`openings_service.get_time_series`), and an existing SQL window-function pattern (`ROW_NUMBER() OVER (PARTITION BY ...)` in `canonical_slice_sql.py`). There is **no greenfield infrastructure** to invent.

The one genuine design tension is the architecture amendment locked in Phase 105's CONTEXT (§decisions, line 53): the cross-game work must be a **SQL window-scan returning only flagged mistake+blunder rows**, with **Python applying the 8 tags over that reduced set**, reusing the kernel's tag functions. But the kernel's tag functions are **module-private** (`_build_tags`, `_is_miss`, `_classify_tempo`, etc.) and operate on `list[GamePosition]` ORM objects plus an `all_moves` dict, not on a flat row-set returned by a window query. **This is the central contradiction the planner must resolve** (see "Critical Contradiction" below). Two viable strategies exist; the recommendation is the **per-game kernel re-call** strategy for correctness-first v1, with the SQL window-scan reserved for the count-filter + count-aggregate path where it is unambiguous.

**Primary recommendation:** Create **one new router** `app/routers/library.py` (prefix `/library`, two GET endpoints: `/games` and `/mistake-stats`), a new service `app/services/library_service.py`, and extend `app/repositories/query_utils.py` with a boolean mistake-`EXISTS` filter. For per-game B/M/I counts + curated chips, **re-call `classify_game_mistakes()` per game on the paginated page only** (≤ limit games, default 20) — the kernel is already the source of truth and reusing it avoids the SQL-vs-Python drift the roadmap explicitly warns against. Use the SQL window-scan for the two places it is unambiguous and cheap: the `EXISTS` severity filter (no Python needed) and the stats-panel aggregates over the full filtered set (where re-calling the kernel for thousands of games is too expensive).

---

<user_constraints>
## User Constraints (from Phase 105 CONTEXT.md — the binding upstream contract)

Phase 106 has **no CONTEXT.md of its own yet** (`has_context: false`). The binding decisions come from Phase 105's CONTEXT.md `<deferred>` block (which named this phase's scope) and the SEED-036 amendment. They are reproduced verbatim where they constrain 106.

### Locked Decisions (carried from Phase 105 + SEED-036 amendment)
- **On-the-fly ONLY** — "No materialization, no `game_flaws` table, no backfill" (105-CONTEXT §decisions line 53). No new column, table, migration, or reimport.
- **SQL window-scan + Python tagging (Option 2)** — "The cross-game filter + stats panel are served by a SQL window-function scan over `game_positions ⋈ games` that returns only the flagged mistake+blunder rows (enriched with es_before/after, move_time, neighbor severities); Python applies the 8 tags + stats over that reduced set, reusing this module's tag functions." (105-CONTEXT line 53)
- **Inaccuracies are count-only** — "excluded from the tagged set and not listed on Flaws … `miss`/`unpunished` only reference mistake/blunder neighbors." The kernel already emits FlawRecords for mistakes+blunders only; inaccuracies must still be **counted** for the B/M/I display.
- **Boolean `EXISTS` game filter** — "Game filters are boolean `EXISTS` ('≥1 blunder'), not counts." No count thresholds. Severity/tempo thresholds are **bound query parameters**.
- **The kernel is the source of the shared tag functions** — "only the trivial severity-drop math is duplicated in SQL (kept honest by a fixture cross-check test)." (105-CONTEXT line 53)
- **Card-chip curation** (SEED-036 lines 213–217, 337): aggregate + dedupe to game level (one chip per tag type present, not per flaw); **exclude inaccuracy-level tags AND `phase`** from card chips; card-worthy tags = `result-changing`, the tempo pair, `miss`/`unpunished`, `from-winning`.
- **Boolean severity filter only on Games** (SEED-036 line 206) — Games does NOT get attribution-tag filters; only B/M/I severity boolean. (Rationale: cross-row-match ambiguity + Games-vs-Flaws separation.)
- **"Analyzed" = ≥90% per-ply eval coverage** (105-CONTEXT line 59; kernel constant `EVAL_COVERAGE_MIN = 0.90`). chess.com / unanalyzed-lichess → explicit "no engine analysis" state, never a false zero-flaw game.
- **CLAUDE.md gates**: async SQLAlchemy 2.x `select()`; asyncpg/PostgreSQL only; never `asyncio.gather` on the same `AsyncSession`; routers thin (HTTP only), business logic in services, DB access in repositories, no SQL in services; `Literal[...]` not bare `str`; `Sequence[str]` for params taking `list[Literal]`; `uv run ty check app/ tests/` zero errors; never expose internal hashes (return FEN for display).

### Claude's Discretion (for this phase)
- New endpoints vs extending the existing games-list endpoint (research recommends NEW — see Architecture).
- Whether per-game counts/chips come from the same SQL pass or a second enrichment pass (research recommends per-game kernel re-call on the page).
- Router prefix/paths, exact Pydantic schema field names.
- Whether the SQL window-scan or the Python kernel computes per-game counts (research recommends: kernel for the page, SQL for the full-set aggregates + the EXISTS filter).
- Initial recency-window bucketing for the trend series.

### Deferred Ideas (OUT OF SCOPE — do not build)
- Any UI (Games / Flaws / Analysis subtabs, cards, chips, stats-panel rendering) — LIBG-01/03 UI is a later phase.
- Attribution-tag game filters (only boolean severity on Games).
- The best-move endpoint (LIBG-05).
- Materialization / a `game_flaws` cache (returns later only as a benchmark-driven cache, not in 106).
- Material-delta filter (cut in the 2026-06-03 rework).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIBG-08 | Games-list endpoint extends `apply_game_filters` with a boolean mistake-type `EXISTS` filter (≥1 of selected severity, thresholds as bound params, no count thresholds, no materialization/backfill); returns per-game B/M/I counts + curated/deduped card tag-chips (game-level dedupe, inaccuracy-level tags + `phase` excluded), reusing the Phase 105 kernel; chess.com/unanalyzed → explicit "no engine analysis" state. Backend of LIBG-01. | EXISTS filter design in §"SQL: the EXISTS mistake filter"; per-game counts/chips via kernel re-call in §"Per-game counts & chips strategy"; the kernel (`classify_game_mistakes`) + `GameNotAnalyzed` already exist (§"Phase 105 kernel"). |
| LIBG-09 | Stats-panel aggregate endpoint over the filtered analyzed-only set — per-severity counts/rates (per game and per 100 moves), full tag distribution (tempo split, result-changing rate, phase histogram), trend-over-time series — with explicit `% analyzed` (≥90% coverage) denominator + analyzed N stated. Cross-game work pushed into a SQL window-scan returning only flagged mistake+blunder rows; Python applies tags + tag-distribution stats over that reduced set. Backend of LIBG-03. | SQL window-scan in §"SQL: the window-scan for stats"; analyzed-denominator computation in §"The ≥90% analyzed denominator"; trend series via the `get_time_series` rolling-window precedent (§"Trend-over-time"); cross-check fixture test in §"Validation Architecture". |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Boolean mistake-severity filter | API/Backend (repository) | — | Pure indexed `EXISTS` subquery; belongs in `query_utils`/repository, never in the service. |
| Per-game B/M/I counts + chips | API/Backend (service) | — | Reuses the pure-Python kernel; orchestration is service-layer work over rows loaded by the repository. |
| Stats aggregates (counts/rates/distribution/trend) | API/Backend (service over repository SQL) | — | Window-scan SQL in repository returns reduced row-set; Python tag-distribution + trend math in service. |
| Analyzed-% denominator | API/Backend (repository SQL) | service | Coverage ratio is a per-game aggregate over `game_positions`; compute in SQL, surface in response. |
| HTTP shaping / auth / validation | API/Backend (router) | — | Thin router: `current_active_user`, query params, service call, response model. |

## Standard Stack

No new external packages. This phase is pure-internal: it composes existing app modules.

### Core (existing modules reused — file paths + signatures)

| Module | Symbol / signature | Purpose | Source |
|--------|-------------------|---------|--------|
| `app/services/mistakes_service.py` | `classify_game_mistakes(game: Game, positions: list[GamePosition]) -> GameMistakesResult` | THE kernel. Returns `list[FlawRecord]` (mistakes+blunders only) or `GameNotAnalyzed`. | lines 430–495 |
| `app/services/mistakes_service.py` | `FlawRecord(TypedDict)`: `ply:int, fen:str, side:Literal["white","black"], severity:FlawSeverity, tags:list[FlawTag], es_before:float, es_after:float, move_san:str\|None` | The per-flaw contract. | lines 95–104 |
| `app/services/mistakes_service.py` | `GameNotAnalyzed(TypedDict)`: `reason:Literal["no_engine_analysis"], eval_coverage:float` | The explicit "no engine analysis" state. | lines 106–108 |
| `app/services/mistakes_service.py` | `FlawSeverity = Literal["inaccuracy","mistake","blunder"]`; `FlawTag = Literal["miss","unpunished","from-winning","result-changing","time-pressure","hasty","knowledge-gap","phase-opening","phase-middlegame","phase-endgame"]`; `TempoTag` | Severity + tag enums to import (don't re-declare). | lines 75–88 |
| `app/services/mistakes_service.py` | Constants `INACCURACY_DROP=0.05`, `MISTAKE_DROP=0.10`, `BLUNDER_DROP=0.15`, `MATE_CP_EQUIVALENT=1000`, `EVAL_COVERAGE_MIN=0.90` | The bound parameters for the SQL EXISTS / window-scan severity math. Import, don't hard-code. | lines 39–51 |
| `app/repositories/mistakes_repository.py` | `fetch_game_positions_ordered(session, game_id, user_id) -> list[GamePosition]` | Load one game's plies (ply ASC, user-owned). The per-game kernel-re-call path uses this. | lines 13–36 |
| `app/services/eval_utils.py` | `eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white","black"]) -> float` = `1/(1+exp(-K·sign·cp))`, `LICHESS_K=0.00368208` | The ES sigmoid. **The SQL window-scan must replicate this exact formula** (see §"ES-drop math in SQL"). | lines 41–66 |
| `app/repositories/query_utils.py` | `apply_game_filters(stmt, time_control, platform, rated, opponent_type, from_date, to_date, color=None, *, opponent_gap_min=None, opponent_gap_max=None) -> stmt` | The single game-filter source. **Extend with a mistake-EXISTS param.** | lines 12–92 |
| `app/schemas/openings.py` | `GameRecord(BaseModel)` — game_id, user_result, played_at, time_control_bucket, platform, platform_url, white/black_username, white/black_rating, opening_name/eco, user_color, move_count, termination, time_control_str, result_fen | Canonical per-game card. **Extend or wrap with B/M/I counts + chips.** | lines 98–117 |
| `app/services/openings_service.py` | `derive_user_result(result: str, user_color: str) -> Literal["win","draw","loss"]` | Map raw result → user POV. Already imported by the kernel. | line 109 |
| `app/services/normalization.py` | `parse_base_and_increment(tc_str: str) -> tuple[int\|None, float\|None]` | Increment derivation; kernel already uses it. | line 78 |

### Supporting (precedent patterns to copy)

| Module | What to copy | Source |
|--------|-------------|--------|
| `app/repositories/endgame_repository.py::query_endgame_games` | The exact paginated-archive shape: subquery of game_ids → `select(Game).where(Game.id.in_(...))` → `apply_game_filters(...)` → `count` via `select(func.count()).select_from(base.subquery())` → `.order_by(Game.played_at.desc().nulls_last()).offset().limit()` → `(games, matched_count)`. | lines 445–519 |
| `app/services/endgame_service.py::get_endgame_games` | GameRecord-building loop + `EndgameGamesResponse(games, matched_count, offset, limit)`. | lines 1112–1178 |
| `app/services/canonical_slice_sql.py` | `row_number() OVER (PARTITION BY g.user_id ORDER BY g.played_at DESC)` — the in-repo precedent that SQLAlchemy/Postgres window functions are an accepted pattern here. | lines 305–306 |
| `app/services/openings_service.py::get_time_series` | Rolling-window trend computation in Python over chronological per-game rows (`ROLLING_WINDOW_SIZE`, trailing window, min-games gate). Adapt for "mistake rate by recency window." | lines 48–51, 261–330 |
| `app/routers/endgames.py` | Thin GET endpoint shape: `Annotated[AsyncSession, Depends(get_async_session)]`, `Annotated[User, Depends(current_active_user)]`, `Query(...)` params, `from_date>to_date` 422 guard, `response_model=`. | lines 24–109 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `/library` router | Extend openings `POST /openings/positions` or endgames `/games` | Rejected: those are position/endgame-scoped; the Games subtab is a flat archive with a different filter (severity) + response (B/M/I + chips + stats). A new router is cleaner and avoids polluting two unrelated schemas. |
| Per-game kernel re-call for counts | Pure SQL window-scan computes ALL counts incl. inaccuracies | Viable for raw counts, but the chips need the full tag set (miss/unpunished/result-changing/tempo) which is exactly the kernel's Python logic. Re-implementing tagging in SQL = the drift the roadmap warns against. |

**Installation:** none. `uv sync` already covers all dependencies.

## Package Legitimacy Audit

> Not applicable — Phase 106 installs no external packages. All code composes existing in-repo modules. slopcheck/registry verification skipped (no new dependencies).

## Architecture Patterns

### System Architecture Diagram

```
GET /api/library/games?severity=blunder&time_control=...&offset=&limit=
        │
        ▼
  library router (thin: auth + Query params + from>to guard)
        │
        ▼
  library_service.get_library_games(...)
        │
        ├──► library_repository.query_filtered_games(...)         [REPOSITORY / SQL]
        │       select(Game).where(Game.id.in_(EXISTS-filtered ids))
        │       apply_game_filters(..., mistake_severity=<param>)  ← NEW EXISTS subquery
        │       order_by(played_at desc).offset().limit()
        │       returns (page_games: list[Game], matched_count)
        │
        ├──► for each game in page (≤ limit):                      [SERVICE → kernel reuse]
        │       positions = mistakes_repository.fetch_game_positions_ordered(g.id, user_id)
        │       result = classify_game_mistakes(g, positions)      ← PHASE 105 KERNEL
        │       if GameNotAnalyzed → counts=None, chips=[], state="no_engine_analysis"
        │       else → B/M/I counts (incl. inaccuracies via internal pass*), curated chips
        │
        ▼
  LibraryGamesResponse(games=[GameMistakeCard...], matched_count, offset, limit)


GET /api/library/mistake-stats?severity=...&time_control=...
        │
        ▼
  library router → library_service.get_mistake_stats(...)
        │
        ├──► library_repository.count_filtered_and_analyzed(...)   [analyzed denominator: SQL]
        │       total filtered N  +  analyzed-N (≥90% coverage)  →  % analyzed
        │
        ├──► library_repository.window_scan_flagged_rows(...)      [SQL window-scan]
        │       LAG/LEAD ES over game_positions ⋈ games (analyzed games only)
        │       WHERE mover-POV ES drop >= MISTAKE_DROP            (mistakes+blunders only)
        │       returns flat rows enriched: ply, side, severity, es_before, es_after,
        │                phase, clock, move_time-inputs, neighbor severities
        │
        ▼  Python over the reduced row-set:
  apply 8 tags (reuse kernel tag fns) → tag distribution + per-severity counts/rates
  + trend-over-time (rolling-window, get_time_series style)
        ▼
  MistakeStatsResponse(per_severity, rates_per_game, rates_per_100_moves,
                       tag_distribution, trend, analyzed_pct, analyzed_n, total_n)

  * inaccuracy counts: kernel currently returns mistakes+blunders only as FlawRecords.
    See "Critical Contradiction" — inaccuracy count needs either a small kernel addition
    or a SQL aggregate. RECOMMENDED: add a count-only helper to the kernel.
```

### Recommended Project Structure
```
app/
├── routers/
│   └── library.py            # NEW: prefix="/library", GET /games + GET /mistake-stats
├── services/
│   └── library_service.py    # NEW: get_library_games(), get_mistake_stats(), chip curation
├── repositories/
│   ├── library_repository.py # NEW: query_filtered_games, window_scan_flagged_rows, coverage counts
│   └── query_utils.py        # MODIFIED: apply_game_filters gains mistake_severity EXISTS param
└── schemas/
    └── library.py            # NEW: LibraryGamesResponse, GameMistakeCard, MistakeStatsResponse, etc.
```
Register the router in `app/main.py` (or wherever routers are included — verify the include pattern there) and mount under the `/api` prefix consistent with other routers.

### Pattern 1: Boolean mistake-severity `EXISTS` filter in `apply_game_filters`
**What:** Add an optional `mistake_severity: Sequence[FlawSeverity] | None = None` kwarg. When set, append a correlated `EXISTS` subquery over `game_positions` that is true iff the game contains ≥1 ply whose mover-POV ES drop meets the selected severity threshold.
**When to use:** Only the Games-list endpoint passes it. All existing callers (endgame, openings, stats repos) keep working because the param defaults to `None`.
**Note on threshold:** thresholds are **bound parameters** sourced from the kernel constants (`MISTAKE_DROP`, `BLUNDER_DROP`). For "≥1 blunder" the EXISTS predicate is `drop >= BLUNDER_DROP`; for "≥1 mistake" `drop >= MISTAKE_DROP`. The drop is computed from `LAG`-ed `eval_cp`/`eval_mate` (see §"ES-drop math in SQL").

### Pattern 2: ES-drop math in SQL (replicating `eval_cp_to_expected_score`)
**What:** The sigmoid is `ES = 1/(1+exp(-K·sign·cp))` with `K=0.00368208`, `sign = +1` for white mover, `-1` for black. PostgreSQL has `exp()`, so this is directly expressible. The mover-POV drop at ply N is `ES_before(N-1, mover) - ES_after(N, mover)` where mover = white if N even else black (matches the kernel's `_run_all_moves_pass`, lines 209–218).
**Mate Option B in SQL:** if `eval_mate` is non-null, substitute `±MATE_CP_EQUIVALENT` (±1000) as the cp before the sigmoid (kernel `_ply_to_es`, lines 133–138). Express as a `CASE WHEN eval_mate IS NOT NULL THEN sign(eval_mate)*1000 ELSE eval_cp END`.
**Window function:** `LAG(eval_cp/eval_mate) OVER (PARTITION BY game_id ORDER BY ply)` gives the previous ply's eval. Because `eval_cp` is white-perspective, compute the drop in white-perspective ES then flip per mover — or compute mover-POV ES directly with the `sign` term.
**Critical correctness pin:** the kernel's eval-AFTER semantics (mistakes_service lines 203–206): `positions[N].eval_cp` is the eval AFTER move N. So `ES_before = ES(positions[N-1])`, `ES_after = ES(positions[N])`, both from the mover's POV. The SQL `LAG` must reproduce exactly this N-1 / N pairing. **This is the line the fixture cross-check test guards.**

### Pattern 3: Per-game counts & chips via kernel re-call (the page only)
**What:** For each of the ≤`limit` games on the returned page, call `fetch_game_positions_ordered` + `classify_game_mistakes`. If `GameNotAnalyzed` → emit the "no engine analysis" card state. Else: B/M/I counts and curated chips from the `FlawRecord` list.
**Counts:** mistakes + blunders are directly countable from FlawRecords (`severity` field). **Inaccuracy count is NOT in the FlawRecord list** (kernel emits M+B only). See "Critical Contradiction" — recommended fix below.
**Chips (SEED-036 lines 213–217):** collect `set(tag for flaw in flaws for tag in flaw["tags"])`, then **drop** any `phase-*` tag and (since FlawRecords are already M+B-only, no inaccuracy-level flaws exist) emit one chip per remaining tag type. Card-worthy tag set = `{result-changing, time-pressure, hasty, knowledge-gap, miss, unpunished, from-winning}`. Dedup is just the set; "one chip per tag type present."
**Sequential, not gather:** the per-game `fetch_game_positions_ordered` loop runs sequentially on the same `AsyncSession` (CLAUDE.md: never `asyncio.gather` on one session). At default limit=20 this is 20 small indexed queries — acceptable for v1 (performance explicitly "not great, accepted" per 105-CONTEXT line 52).

### Pattern 4: Trend-over-time (rolling window)
**What:** Reuse the `get_time_series` shape (openings_service lines 261–330): pull chronological per-game mistake counts, compute a trailing rolling-window mistake-rate, drop early under-filled points. The "rate" here is mistakes-per-game or per-100-moves over the window rather than win-rate, but the windowing/min-games-gate machinery transfers directly.

### Anti-Patterns to Avoid
- **Re-implementing the 8 tags in SQL.** The roadmap (criterion 5) and 105-CONTEXT both say only the *severity-drop math* is duplicated in SQL; tags stay in Python over the reduced row-set. Do not port `_is_miss`/`_classify_tempo`/`_is_result_changing` to SQL.
- **Hard-coding thresholds.** Import `MISTAKE_DROP`/`BLUNDER_DROP`/`MATE_CP_EQUIVALENT`/`EVAL_COVERAGE_MIN`/`LICHESS_K` from their modules so SQL and Python share one source.
- **`asyncio.gather` over the per-game kernel re-calls** — forbidden on one session and provides no benefit (one connection).
- **Returning a false zero-flaw game** for chess.com / unanalyzed lichess — must emit the `no_engine_analysis` state (kernel already does this; surface it, never coerce to `0/0/0`).
- **Exposing internal hashes** — `GameRecord` already returns FENs/usernames only; keep it that way.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-ply severity + tags | A second classifier | `classify_game_mistakes` (105 kernel) | Source of truth; the roadmap mandates reuse. |
| Game filtering (TC/platform/rated/opponent/date/color/gap) | New WHERE logic | `apply_game_filters` (extend it) | Single-source filter rule (CLAUDE.md). |
| ES sigmoid | New cp→ES math | `eval_cp_to_expected_score` (Python) + the same formula transcribed in SQL | One canonical `LICHESS_K`. |
| Paginated archive query | New pagination | Copy `query_endgame_games` shape | Proven `matched_count` + offset/limit pattern. |
| Per-game card schema | New game DTO | `GameRecord` (extend/wrap) | Consistent with openings/endgames cards. |
| Rolling-window trend | New windowing | `get_time_series` machinery | Already handles min-games gate + partial windows. |
| user_result derivation | New mapping | `derive_user_result` | Already used by kernel. |

**Key insight:** This phase is 80% composition. The risk is not building new things — it's accidentally **forking** the severity math between SQL and Python. Pin both to the kernel constants and guard the seam with the cross-check fixture test.

## Critical Contradiction (planner MUST resolve)

The roadmap and 105-CONTEXT mandate **"Python applies the 8 tags + stats over the reduced [SQL window-scan] set, reusing this module's tag functions."** But the kernel's tag functions are **module-private** and **shaped for ORM input**:

- `_build_tags`, `_is_miss`, `_is_unpunished`, `_is_result_changing`, `_classify_tempo`, `_phase_tag`, `_move_time` are all `_`-prefixed (mistakes_service lines 244–422).
- They take `positions: list[GamePosition]` + an `all_moves: dict[int, _MoveEntry]` + `increment`/`base_time`/`user_result` — **not a flat SQL row-set**.
- `classify_game_mistakes` only returns **mistakes+blunders** as FlawRecords; **inaccuracy counts are computed internally but never exposed** (lines 472–480, 11–14).

**Consequences the planner must decide on:**

1. **B/M/I per-game counts (LIBG-08):** the kernel does not expose the inaccuracy count. Options:
   - **(Recommended)** Add a thin count-only helper to `mistakes_service.py`, e.g. `count_game_severities(game, positions) -> SeverityCounts | GameNotAnalyzed` returning `{inaccuracy, mistake, blunder}`, reusing `_run_all_moves_pass` + the existing severity classifier. Small, keeps the kernel the single source.
   - Or compute inaccuracy count via a SQL aggregate (drop ≥ `INACCURACY_DROP` and < `MISTAKE_DROP`) — but this re-forks the math (mate handling, eval-AFTER pairing) the roadmap warns against.

2. **Tag application over the SQL window-scan rows (LIBG-09 stats):** the private tag functions can't consume SQL rows as-is. Options:
   - **(Recommended for v1 correctness)** For the stats path, instead of "SQL rows → Python tag fns," reuse the same per-game kernel re-call but over the **full analyzed filtered set** (not just a page). This is the simplest correct path but is O(filtered games) kernel calls — acceptable only if the analyzed filtered set is modest. Given ~21.7% analyzed overall and per-user game counts, the analyzed set per user is often small; benchmark (criterion 1 / LIBG-08 benchmark clause).
   - Or refactor the kernel's tag functions to accept a neutral row dataclass and have the SQL window-scan produce that shape. This honors the literal roadmap wording (SQL reduced set + Python tags) but requires promoting the private functions to a public, row-shaped API — a real refactor of 105 code.
   - **Planner decision needed:** literal-roadmap (SQL-rows + refactored public tag fns) vs pragmatic-correctness (kernel re-call over the analyzed set + SQL only for the EXISTS filter and the coverage denominator). Either satisfies the on-the-fly / no-materialization constraint. The window-scan is still genuinely useful for the **EXISTS filter** and for the **flagged-row count aggregates** even if full tag application stays per-game.

3. **Cross-check fixture test (criterion 5):** regardless of path chosen, the SQL severity-drop math (used at minimum for the EXISTS filter) MUST be cross-checked against the Python kernel on a fixture game. This test is the guardrail keeping the two implementations honest.

**Researcher recommendation:** Adopt the **pragmatic-correctness** path. Use the SQL window-scan for (a) the `EXISTS` severity filter and (b) the per-severity flagged-row **counts/aggregates** + the coverage denominator. Apply tags via the **kernel** (re-called per game over the page for cards, and over the analyzed filtered set for stats), adding only a small `count_game_severities` helper for inaccuracy counts. This minimizes new severity-math surface (one SQL transcription, guarded by the fixture test) and avoids a public-API refactor of 105 in a phase that's supposed to be composition. Flag the literal-wording divergence in the PLAN's decision log.

## The ≥90% "analyzed" denominator (LIBG-09)

Definition (105-CONTEXT line 59, kernel `EVAL_COVERAGE_MIN=0.90`, `_compute_eval_coverage` lines 155–165): a game is analyzed iff `count(plies with eval_cp OR eval_mate non-null) / count(plies) >= 0.90`. The final ply always has null eval, so a fully-analyzed game scores `(N-1)/N` ≈ 0.99 — comfortably above 0.90.

**SQL computation over the filtered set** (in `library_repository`): per game, `SUM(CASE WHEN eval_cp IS NOT NULL OR eval_mate IS NOT NULL THEN 1 ELSE 0 END)::float / COUNT(*)` from `game_positions`, then `HAVING ratio >= 0.90` (or a CASE flag) to get `analyzed_n`. `total_n` = filtered game count. `analyzed_pct = analyzed_n / total_n`. Both `analyzed_n` and `analyzed_pct` go in the response so the panel never implies clean games where evals are merely absent (criterion 4).

**Per-game analyzed/unanalyzed classification** for cards comes free from the kernel: `GameNotAnalyzed` ⟺ unanalyzed. chess.com games have all-null `eval_cp`/`eval_mate` → coverage 0.0 → `GameNotAnalyzed`. Unanalyzed lichess games likewise.

## SQL: the EXISTS mistake filter (LIBG-08)

Shape (correlated `EXISTS` over `game_positions`, true iff the game has ≥1 qualifying-severity ply):
```
EXISTS (
  SELECT 1 FROM (
    SELECT
      gp.ply,
      gp.eval_cp, gp.eval_mate,
      LAG(gp.eval_cp)   OVER w AS prev_cp,
      LAG(gp.eval_mate) OVER w AS prev_mate
    FROM game_positions gp
    WHERE gp.game_id = games.id AND gp.user_id = :user_id
    WINDOW w AS (PARTITION BY gp.game_id ORDER BY gp.ply)
  ) p
  WHERE <mover-POV ES drop computed from prev_* and current, via the sigmoid + mate-Option-B CASE>
        >= :severity_drop   -- bound param: MISTAKE_DROP or BLUNDER_DROP
)
```
- `:severity_drop` is a **bound parameter** (no count thresholds — boolean EXISTS only, per the locked decision).
- mover = white if `ply` even else black; apply the `sign` flip inside the ES expression.
- This is index-backed: the `game_positions` **PK is `(game_id, user_id, ply)`** (model lines 79–87) — leading on `game_id`, so the `PARTITION BY game_id ORDER BY ply` scan and the `game_id = games.id AND user_id = :user_id` filter both use the PK btree.

**Index decision (criterion 1, LIBG-08 benchmark clause):** there is **already a `(game_id, user_id, ply)` PK index** that serves `(game_id, ply)` scans (the old explicit `ix_gp_user_game_ply` was retired in SEED-035 precisely because the PK absorbs it — model lines 71–73). So a *new* `(game_id, ply)` index is very likely **unnecessary**. Benchmark the window-scan first; only add an index if `EXPLAIN ANALYZE` shows the PK isn't being used (e.g. if queries lead with a per-user not per-game predicate). Document the EXPLAIN result in the PLAN/VERIFICATION.

## SQL: the window-scan for stats (LIBG-09)

Same `LAG`/`LEAD` window machinery, but instead of a boolean EXISTS, return the flagged rows for the **whole filtered analyzed-only set**: `ply, game_id, side, severity, es_before, es_after, phase, clock_seconds`, plus the inputs Python needs for tags it cannot get from a single row (neighbor severities for miss/unpunished via `LAG`/`LEAD` of the computed severity; move_time inputs via `LAG(clock_seconds, 2)`). `WHERE drop >= MISTAKE_DROP` (mistakes+blunders only — inaccuracies are count-only). Restrict to analyzed games (the ≥90% coverage set) via a join/CTE.

**If the pragmatic-correctness path is chosen** (recommended), the window-scan here is reduced to producing **per-severity counts + the inputs for tag distribution that are cheap in SQL** (phase histogram is a pure `GROUP BY phase`; tempo split / result-changing need the kernel's clock+result logic → compute via kernel re-call over the analyzed set). Reconcile this with the planner's choice on the Critical Contradiction.

**Reconciling "window-scan returns M+B only" with "B/M/I counts":** the per-game card counts include inaccuracies (the "I" in B/M/I), but the window-scan tagged set is M+B only. These are two different aggregations: the **count** path needs all three tiers (use `count_game_severities` helper / SQL aggregate), the **tagged** path needs M+B only (window-scan). The PLAN must keep them distinct — do not try to derive the inaccuracy count from the M+B window-scan.

## Code Examples

### Existing paginated archive (the template to copy)
```python
# Source: app/repositories/endgame_repository.py:489-519
base_stmt = select(Game).where(
    Game.user_id == user_id,
    Game.id.in_(select(span_subq.c.game_id)),
)
base_stmt = apply_game_filters(base_stmt, time_control=..., platform=..., ...)
count_stmt = select(func.count()).select_from(base_stmt.subquery())
matched_count = (await session.execute(count_stmt)).scalar_one()
games_stmt = base_stmt.order_by(Game.played_at.desc().nulls_last()).offset(offset).limit(limit)
games = list((await session.execute(games_stmt)).scalars().all())
return games, matched_count
```

### Existing window function in-repo (proof of pattern)
```python
# Source: app/services/canonical_slice_sql.py:305-306
row_number() OVER (PARTITION BY g.user_id ORDER BY g.played_at DESC) AS rn
# → adapt to: LAG(gp.eval_cp) OVER (PARTITION BY gp.game_id ORDER BY gp.ply)
```

### The ES sigmoid to transcribe into SQL
```python
# Source: app/services/eval_utils.py:65-66
sign = 1 if user_color == "white" else -1
return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))
# SQL: 1.0 / (1.0 + exp(-0.00368208 * <sign> * <cp_or_mate_equiv>))
```

### Kernel re-call per game (cards path)
```python
# Source: app/services/mistakes_service.py:430 + app/repositories/mistakes_repository.py:13
positions = await fetch_game_positions_ordered(session, game_id=g.id, user_id=user_id)
result = classify_game_mistakes(g, positions)
if isinstance(result, dict) and result.get("reason") == "no_engine_analysis":
    ...  # GameNotAnalyzed → "no engine analysis" card state
else:
    flaws = result  # list[FlawRecord], mistakes+blunders only
    chips = {t for f in flaws for t in f["tags"] if not t.startswith("phase-")}
```
Note: `GameNotAnalyzed` and `list[FlawRecord]` are both runtime-`list`/`dict` (TypedDicts erase to dict), so discriminate on `reason`/type, not `isinstance(TypedDict)`.

## Common Pitfalls

### Pitfall 1: SQL/Python severity-drop divergence
**What goes wrong:** The SQL transcription of the sigmoid drifts from `eval_cp_to_expected_score` (wrong K, wrong sign flip, wrong N-1/N pairing, or mate handled with hard 1.0/0.0 instead of ±1000 Option B).
**Why:** Two implementations of the same math.
**How to avoid:** Import `LICHESS_K` and the drop constants; transcribe mate as `±MATE_CP_EQUIVALENT` (NOT `eval_mate_to_expected_score`); guard with the cross-check fixture test (criterion 5).
**Warning signs:** EXISTS filter and per-game kernel counts disagree on the same fixture game.

### Pitfall 2: eval-AFTER landmine in the window scan
**What goes wrong:** Treating `gp.eval_cp` as the eval *before* the move. It is the eval *after* (kernel lines 203–206).
**How to avoid:** `ES_before = ES(LAG eval at ply N-1)`, `ES_after = ES(eval at ply N)`. The `LAG` provides ply N-1.

### Pitfall 3: Counting inaccuracies from the M+B window-scan
**What goes wrong:** The window-scan returns mistakes+blunders only; deriving the "I" count from it gives zero.
**How to avoid:** Compute inaccuracy counts separately (kernel `count_game_severities` helper, or a dedicated SQL aggregate with `INACCURACY_DROP <= drop < MISTAKE_DROP`).

### Pitfall 4: N+1 query cost on the cards page
**What goes wrong:** Per-game kernel re-call is one positions query per game. At large limits this multiplies.
**How to avoid:** Cap `limit` (default 20, max 100 like endgames); accept the cost for v1 (explicitly accepted in 105-CONTEXT line 52). Optionally batch-load all page positions in one `WHERE game_id IN (...)` query and group in Python — a cheap optimization if benchmark warrants.

### Pitfall 5: Interior null evals breaking LAG pairing
**What goes wrong:** A ply with null eval in the middle of an analyzed game. The kernel skips these (lines 213–214). SQL `LAG` will happily pair across them.
**How to avoid:** In SQL, treat a null current-or-prev eval row as non-flaggable (the drop is undefined → exclude). Mirror the kernel's "skip if either ES is None."

### Pitfall 6: `opponent_type` / `color` param plumbing
**What goes wrong:** `apply_game_filters` takes `opponent_type: str` ("human"/"bot"/"all") and `color` separately; the Games subtab has its own filter conventions. Match the existing endgame/openings call signatures exactly.
**How to avoid:** Copy the param list from `endgames.py` GET handlers verbatim (lines 68–109) and forward through.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Materialized `game_flaws` table (early SEED-036 wording) | On-the-fly SQL window-scan + Python tagging, no table | 2026-06-05 amendment (105-CONTEXT line 53) | No migration/backfill; thresholds are bound params. |
| Count-level / min-blunders game filter | Boolean `EXISTS` ("≥1 blunder") | 2026-06-05 (SEED-036 line 206) | Single indexed EXISTS, no count thresholds. |
| Explicit `ix_gp_user_game_ply` index | Absorbed by `(game_id, user_id, ply)` PK | SEED-035 | A new `(game_id, ply)` index is likely redundant. |

**Deprecated/outdated:** the materialization-prerequisite framing in earlier same-day SEED text is **superseded** (105-CONTEXT line 53 says so explicitly). Do not plan a table.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (per-run isolated PostgreSQL DB; see `tests/conftest.py`) |
| Config file | `pyproject.toml` (addopts, asyncio mode); slow-test dirs excluded via `--ignore` |
| Quick run command | `uv run pytest tests/test_library_repository.py tests/services/test_library_service.py -x` |
| Full suite command | `uv run pytest -n auto` (parallel; the integration gate before squash-merge) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIBG-08 | EXISTS severity filter selects only games with ≥1 of the severity | integration | `uv run pytest tests/test_library_repository.py -k exists_filter -x` | ❌ Wave 0 |
| LIBG-08 | **SQL drop math == Python kernel** on a fixture game (the cross-check) | integration | `uv run pytest tests/test_library_repository.py -k cross_check -x` | ❌ Wave 0 |
| LIBG-08 | chess.com / unanalyzed game → "no engine analysis" card, never 0/0/0 | unit/integration | `uv run pytest tests/services/test_library_service.py -k no_engine_analysis -x` | ❌ Wave 0 |
| LIBG-08 | per-game B/M/I counts (incl. inaccuracy) + curated chips (phase excluded, deduped) | unit | `uv run pytest tests/services/test_library_service.py -k chips -x` | ❌ Wave 0 |
| LIBG-09 | analyzed-% denominator + analyzed N in response | integration | `uv run pytest tests/test_library_repository.py -k analyzed_denominator -x` | ❌ Wave 0 |
| LIBG-09 | per-severity rates per game + per 100 moves; tag distribution; trend series | unit/integration | `uv run pytest tests/services/test_library_service.py -k stats -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command above.
- **Per wave merge:** `uv run pytest -n auto` (full suite).
- **Phase gate:** full suite green + `uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/` before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_library_repository.py` — EXISTS filter, window-scan, **SQL↔kernel cross-check fixture**, analyzed-denominator (DB-backed; reuse `_seed_game`/`_seed_position` helpers from `tests/test_mistakes_repository.py`).
- [ ] `tests/services/test_library_service.py` — counts/chips curation, no-engine-analysis state, stats aggregates, trend (mostly pure; build positions in memory à la `tests/services/test_mistakes_service.py`).
- [ ] No framework install needed — pytest/pytest-asyncio + isolated-DB harness already exist.

**The cross-check fixture test (criterion 5) is the load-bearing validation point:** construct one game with known evals, run both `classify_game_mistakes` (Python) and the SQL window-scan over the same rows, assert the per-ply severity set matches. This is the single test that prevents SQL/Python drift.

## Security Domain

`security_enforcement` is not set false in config → enabled, but the surface is minimal (read-only, owned-data only; no new external write/input surface — consistent with 105-CONTEXT §specifics).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | `current_active_user` dependency on both endpoints (copy `endgames.py` pattern). |
| V4 Access Control | yes | Every query filters `user_id == user.id` (the repository ownership guard, mistakes_repository lines 19–24). No cross-user game access. |
| V5 Input Validation | yes | Pydantic `Query(...)` params; `severity` constrained to `Literal[FlawSeverity]`; `offset/limit` bounded (`ge`/`le`); `from_date > to_date` → 422. |
| V6 Cryptography | no | None. |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via filter params | Tampering | Parameterized SQLAlchemy binds only; the one f-string precedent (`canonical_slice_sql`) is safe only because values are literal-constrained — **do not f-string user input**. Severity thresholds are bound params. |
| Cross-user data disclosure | Information Disclosure | `user_id` predicate in every WHERE / EXISTS subquery (T-105-03 mitigation pattern). |
| Hash leakage | Information Disclosure | Response returns FEN/usernames only (GameRecord); never `full_hash`/`white_hash`/`black_hash`. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 (Docker dev) | all queries / tests | assumed ✓ (CLAUDE.md dev DB) | 18 | none — start via `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| `exp()` SQL function | ES sigmoid in window-scan | ✓ (Postgres built-in) | — | — |
| python-chess 1.11.x | kernel FEN replay (already used) | ✓ | 1.11.x | — |

No external services or new tools. No `EXPLAIN` blockers — the benchmark for the index decision runs against the existing dev/prod DBs.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A new `(game_id, ply)` index is unnecessary because the `(game_id, user_id, ply)` PK already serves the window-scan | SQL EXISTS / index decision | If the planner's EXPLAIN shows a non-PK plan, an index is needed — but this is exactly what criterion 1 says to benchmark, so it's a measured decision, not a guess. |
| A2 | The pragmatic-correctness path (kernel re-call for tags, SQL only for EXISTS + counts + coverage) satisfies the on-the-fly/no-materialization constraints while minimizing severity-math forking | Critical Contradiction | Diverges from the *literal* roadmap wording ("Python tags over the SQL reduced set"); both honor the binding constraints, but the planner must explicitly choose and log it. |
| A3 | Adding a small `count_game_severities` helper to the kernel is acceptable (it's a count-only sibling of the existing internal pass) | Per-game counts | If the user wants the kernel frozen, fall back to a SQL inaccuracy aggregate (re-forks math). Confirm in discuss/plan. |
| A4 | Analyzed filtered set per user is modest enough for kernel re-call over the full set in the stats path | Window-scan for stats | If a power user has thousands of analyzed games, the stats path needs the pure SQL window-scan (literal path) instead. Benchmark; the EXISTS clause already restricts to analyzed games. |
| A5 | Router include + `/api` mount pattern matches other routers in `app/main.py` | Project structure | Trivial to verify when planning; not a design risk. |

## Open Questions

1. **Literal vs pragmatic tagging path (the Critical Contradiction).**
   - What we know: both honor on-the-fly/no-materialization; the kernel tag fns are private + ORM-shaped.
   - What's unclear: whether the user wants the literal "SQL reduced set → public row-shaped tag fns" (a real 105 refactor) or the pragmatic kernel-re-call.
   - Recommendation: pragmatic (A2); surface to the user in discuss-phase or the PLAN decision log, since it's the one architectural fork.

2. **New endpoint vs extending an existing one.**
   - What we know: a new `/library` router is cleanest (Architecture §Alternatives).
   - What's unclear: whether the user prefers folding into the openings/endgames surface.
   - Recommendation: new router; low-risk, easily revisited.

3. **Trend bucketing granularity** (by-month vs rolling-game-window).
   - Recommendation: rolling-game-window via `get_time_series` machinery (proven), but confirm the headline-metric framing ("mistake rate by recency window") in the UI phase.

## Sources

### Primary (HIGH confidence — all read this session, with line numbers)
- `app/services/mistakes_service.py` — kernel, FlawRecord/GameNotAnalyzed, tag fns, constants (lines cited throughout).
- `app/repositories/mistakes_repository.py` — `fetch_game_positions_ordered` (13–36).
- `app/services/eval_utils.py` — ES sigmoid + `LICHESS_K` (41–97).
- `app/repositories/query_utils.py` — `apply_game_filters` (12–92).
- `app/repositories/endgame_repository.py` — `query_endgame_games` archive template (445–519).
- `app/services/endgame_service.py` — `get_endgame_games` (1112–1178).
- `app/schemas/openings.py` — `GameRecord` (98–117); `app/schemas/endgames.py` — `EndgameGamesResponse` (229–238).
- `app/services/openings_service.py` — `get_time_series` rolling-window (48–51, 261–330); `derive_user_result` (109).
- `app/services/canonical_slice_sql.py` — window-function precedent (280–316).
- `app/models/game_position.py` — schema, PK `(game_id, user_id, ply)`, index history (25–134); `app/models/game.py` — game-level oracle columns (43–138).
- `app/routers/endgames.py` — thin GET handler pattern (24–109).
- `.planning/phases/105-*/105-CONTEXT.md`, `105-PATTERNS.md` — locked decisions + reuse map.
- `.planning/REQUIREMENTS.md` (LIBG-08/09), `.planning/seeds/SEED-036-library-page-milestone.md` (chip rules lines 209–337, amendment lines 53/206).

### Secondary / Tertiary
- None — no web sources needed; the phase is entirely codebase-internal.

## Metadata

**Confidence breakdown:**
- Standard stack (reused modules + signatures): HIGH — every symbol read with line numbers.
- Architecture (new-router + kernel-re-call + EXISTS + window-scan): HIGH on the constraints, MEDIUM on the literal-vs-pragmatic fork (a genuine open decision flagged for the planner/user).
- Pitfalls: HIGH — derived from the kernel's own documented landmines (eval-AFTER, interior nulls, mate Option B).

**Research date:** 2026-06-05
**Valid until:** ~2026-07-05 (stable; only invalidated by changes to the 105 kernel or `apply_game_filters`).
