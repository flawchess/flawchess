# Phase 258: Library Stats Recent Sample for Snapshot Charts - Pattern Map

**Mapped:** 2026-11-21
**Files analyzed:** 14 (10 modified, 1 new test file, 3+ test files modified)
**Analogs found:** 14 / 14 (all in-repo; this phase extends existing seams)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/repositories/library_repository.py` (add `RecentWindowRow`, `fetch_recent_window_rows`; extend `_analyzed_game_ids_subquery(game_ids=)`) | repository | CRUD read (ranked window) | same file `count_analyzed_by_tc` (L1992) + `_filtered_games_base` (L1743); `app/repositories/endgame_ranked_repository.py` `RankedGameRow`/`fetch_ranked_games` (L21-60) | exact |
| `app/services/library_service.py` (`months_before`, `recent_window_start`, `TcWindowSummary`, `summarize_window`, `now_utc` on 3 services, split `get_flaw_comparison`) | service | request-response | same file `get_flaw_comparison` (L1823-1927); `app/services/endgame_ranked_service.py` `fetch_ranked_inputs` (L188-231) | exact |
| `app/schemas/library.py` (`FlawComparisonTc`, `FlawComparisonResponse`, `TacticComparisonTc` docstring) | schema | transform | same file L481-520 | exact |
| `app/routers/library.py` (3 routes take `now_utc`) | router | request-response | same file L225-270; `app/routers/openings.py` L14, L31, L53 (`NowUtc`) | exact |
| `frontend/src/types/library.ts` | type | transform | existing `FlawComparisonTc` mirror in same file | exact |
| `frontend/src/lib/flawComparisonMeta.ts` (`librarySampleBasisText`, quiet copy, `libraryBasisText` wording) | utility (pure copy) | transform | same file `libraryCoverageBasisText` L311-326 | exact |
| `frontend/src/components/library/stats/LibraryStatsSections.tsx` | component | request-response | same file `CoverageBasisLine` L100-160, `FlawStatsSection` L220-276, `VsOpponentsSection` L298+ | exact |
| `frontend/src/components/library/FlawTrendChart.tsx` (caption) | component | n/a | same file `CardHeader` L167-172 | exact |
| `frontend/src/hooks/useLibraryStatsTc.ts` (quiet-all fallback) | hook | transform | same file `pickDefaultLibraryTc` L26-32 | exact |
| `tests/services/test_library_window.py` (NEW) | test | DB integration + unit | `tests/services/test_flaw_comparison.py` seed helpers L60-100 | role-match |
| `tests/services/test_flaw_comparison.py`, `tests/services/test_tactic_comparison_service.py`, `tests/routers/test_library_tactic_comparison.py`, `tests/test_library_router.py` | test | DB integration | own `_seed_game`; `tests/test_feature_route.py` L184-190 (dev clock pin) | exact |
| `frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts` + section/meta tests | test fixture | n/a | existing fixtures file | exact |
| `CHANGELOG.md` | docs | n/a | `[Unreleased]` section | exact |

## Pattern Assignments

### `app/repositories/library_repository.py`

**Analog A: `_analyzed_game_ids_subquery` (L1888-1905), the seam to extend.** Current body:
```python
return (
    select(Game.id.label("game_id"))
    .where(Game.user_id == user_id, Game.full_evals_completed_at.isnot(None))
    .subquery("analyzed")
)
```
Add `game_ids: Sequence[int] | None = None`; when set, `.where(game_ids_any_predicate(Game.id, game_ids))`. Default `None` keeps today's behaviour (needed by the prod "today" timing arm and `/flaw-stats`).

**Analog B: `game_ids_any_predicate`** (`app/repositories/query_utils.py` L152-166), reuse, do not rewrite:
```python
ids_param = bindparam("ranked_game_ids", value=list(game_ids), type_=ARRAY(Integer), unique=True)
return column == any_(ids_param)
```
Its docstring forbids `IN (subquery)` for id restriction (planner hang).

**Analog C: kwarg signature for `fetch_recent_window_rows`**: copy the keyword-only filter list from `count_analyzed_by_tc` (L1992-2010) verbatim (`time_control`, `platform`, `rated`, `opponent_type`, `from_date`, `to_date`, `flaw_severity=None`, `opponent_gap_min=None`, `opponent_gap_max=None`, `color=None`, `tactic_families=None`, `tactic_filter_orientation="either"`), spelled out (no `**kwargs`, ty). Feed them into `_filtered_games_base(user_id, ...)` (L1743) exactly like `count_analyzed_by_tc` does. Same ply gate as its docstring states: `ply_count IS NOT NULL AND > 0`, `time_control_bucket IS NOT NULL`; plus `played_at IS NOT NULL` (Pitfall 2).

**Analog D: row type.** `endgame_ranked_repository.py` L21-35 uses `@dataclass(frozen=True) class RankedGameRow` and converts rows explicitly (L52-60):
```python
return [RankedGameRow(game_id=int(row.game_id), played_at=row.played_at, ...) for row in result.fetchall()]
```
Use the same style for `RecentWindowRow(game_id, tc, played_at, analyzed, tactic_ready)`. Ranked SQL itself: RESEARCH.md Pattern 1 (`func.row_number().over(partition_by=Game.time_control_bucket, order_by=(Game.played_at.desc(), Game.id.desc()))`, outer `rn <= cap`). Do NOT reuse `ranked_games_sql` / `_recent_capped_per_tc_cte` (hard-code ±100 and rated, violates D-08/D-11). Import `RECENT_GAMES_PER_TC_CAP` from `app/services/canonical_slice_sql.py`.

**JIT:** `disable_jit_for_transaction` (L1659-1668, `SET LOCAL jit = off`) must be called before the window statement in the facepalm path.

---

### `app/services/library_service.py`

**Analog: `get_flaw_comparison` (L1823-1927).** Keep its skeleton:
- `platform = resolve_library_platforms(platform, include_pasted=include_pasted, surface="analytics")`
- `_filter_kwargs: dict[str, Any] = dict(time_control=..., ..., color=color)` shared across all calls
- two sequential `count_analyzed_by_tc` calls (`analyzed_only` True / False) stay unwindowed (TC offer + page `total_n`)
- `analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)` at L1902 becomes `..., game_ids=summary_analyzed_ids`
- same `try/except` wrapper:
```python
except Exception as exc:  # noqa: BLE001 — capture before re-raise for Sentry
    sentry_sdk.set_context("flaw_comparison", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise
```
Same edits at L1962 (`get_facepalm_comparison`) and L2170 (`get_tactic_comparison`), each with its existing except block (L1988, L2208).
- TC loop today: `for tc in LIBRARY_TC_ORDER if counts.get(tc)`; keep iterating the unwindowed `counts`, but fill `analyzed_n`/`total_n`/`below_gate` from the window summary (0 for quiet TCs) and add `history_analyzed_n=counts[tc]`.

**Split seam (Pitfall 9):** copy `endgame_ranked_service.fetch_ranked_inputs` (L188-231): one async `_fetch_*_inputs` doing sequential awaits, collects ids into a union list, skips row queries `if union_ids:` empty, then a pure builder. Its docstring line "queries run one after another (CLAUDE.md, never asyncio.gather on a session)" is the comment to mirror.

**New pure helpers:** `months_before`, `recent_window_start` (RESEARCH Pattern 2), `summarize_window` + `@dataclass(frozen=True) TcWindowSummary` (RESEARCH Code Examples). Import `RECENCY_WINDOW_MONTHS`, `RECENT_GAMES_PER_TC_CAP` from `canonical_slice_sql`; never redefine.

---

### `app/schemas/library.py`

**Analog: `FlawComparisonTc` / `FlawComparisonResponse` (L481-520).** Docstring style lists each field with a one-line meaning; update `analyzed_n`/`total_n` docs to "in the recent window", add `sample_since: datetime.date | None`, `cap_reached: bool`, `history_analyzed_n: int`; response adds `recency_filtered: bool`, `window_months: int`, `games_cap: int`. Rewrite the `tcs:` docstring (TCs are offered from the unwindowed analyzed set; `total_n == 0` = quiet TC).

---

### `app/routers/library.py`

**Analog: `/flaw-comparison` (L225-270) + `openings.py` clock alias.**
```python
from app.core.dev_clock import dev_now_utc          # openings.py L14
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]   # openings.py L31
...
async def get_flaw_comparison(session: ..., user: ..., now_utc: NowUtc, ...):   # openings.py L53
```
Keep the existing 422 guard (`from_date > to_date`) and pass `now_utc=now_utc` into the service call. Do not copy the endgames.py L42-46 dev-clock exception docstring; instead note in the docstring that the window uses `dev_now_utc` because nothing persisted must match.

---

### `frontend/src/lib/flawComparisonMeta.ts`

**Analog: `libraryCoverageBasisText` (L311-326):**
```ts
const fmt = (n: number): string => n.toLocaleString('en-US');
const games = tc === null ? 'games' : `${tc} games`;
if (analyzedN >= totalN) return `All ${fmt(totalN)} ${games} in the current filters are analyzed.`;
return `${fmt(analyzedN)} of ${fmt(totalN)} ${games} analyzed in the current filters.`;
```
New `librarySampleBasisText(b: SampleBasis)` follows this pure-string style (RESEARCH Code Examples), date via `format(parseISO(...), 'MMM yyyy')` from date-fns (already used in `frontend/src/lib/recency.ts`). Keep `libraryCoverageBasisText` only for the `tc === null` fresh-import branch (or remove for knip if unused). `libraryBasisText`/`scopeText` (L300-309) reword per Open Question 1. Update the header comment (L8-9) listing exports.

---

### `frontend/src/components/library/stats/LibraryStatsSections.tsx`

**Analog: `CoverageBasisLine` (L100-160).** Keep: `isUpdating`/`isLowCoverage` threshold math, `ANALYSIS_PENDING_TINT_CLASS`, `Cpu` icon with `data-testid="flaw-stats-coverage-icon"`, `<span data-testid="flaw-stats-basis">`, hint span `flaw-stats-coverage-hint`, `InfoPopover testId="flaw-stats-coverage-info"`, guest `CoverageSignupButton`. Swap the text source to `librarySampleBasisText(...)`; add props for `capReached`, `sampleSince`, `recencyFiltered`, `windowMonths`, `otherFiltersActive`.

**Analog: `FlawStatsSection.renderBody` (L227-262)** early-return chain: `isError` -> `LoadError`, loading -> skeleton, fresh import (`tcs.length === 0 && total_n > 0`) -> coverage line with `tc={null}`, missing tcStats -> `COPY_NO_ANALYZED`. Insert quiet branch (`tcStats.total_n === 0`) before the main return: message `<div data-testid="flaw-stats-no-recent">` + `<FlawTimeline .../>` only.

**Analog: `VsOpponentsSection` (L298-320)** / `TacticMotifsSection` (L366): both read `useLibraryFlawComparison` + `useLibraryStatsTc(tcs)`; add `if (tcStats?.total_n === 0) return null;` at the component level (heading included, D-16). For Tactic, read the flaw comparison tcStats (tactic payload omits quiet TCs).

**otherFiltersActive:** copy `frontend/src/pages/Openings.tsx` L177: `!areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS)`, with a field list derived from `LIBRARY_FILTER_DOT_FIELDS` minus `recency`, `customRange`, `matchSide` (FilterPanel.tsx L128-151). Name it `BASIS_FILTER_FIELDS`.

---

### `frontend/src/components/library/FlawTrendChart.tsx`

**Analog: its own header (L167-172):**
```tsx
<CardHeader size="compact" className="flex items-center gap-2">
  Flaws Timeline
  <InfoPopover ariaLabel="About facepalm blunders" testId="flaw-trend-facepalm-info">
```
Add `<span className="text-sm text-muted-foreground" data-testid="flaw-trend-caption">{TIMELINE_CAPTION}</span>` after the title; named constant, no prop.

---

### `frontend/src/hooks/useLibraryStatsTc.ts`

**Analog: `pickDefaultLibraryTc` (L26-32):**
```ts
return pickMostPopulatedTc(tcs, (t) => !t.below_gate, (t) => t.analyzed_n);
```
Extend `LibraryTcCount` with `total_n` and `history_analyzed_n`; when every TC has `total_n === 0`, rank by `history_analyzed_n`. Stored choice semantics live in `createTcSelectionStore` (tcSelectionStore.ts), unchanged.

---

### Tests

**Seed analog: `tests/services/test_flaw_comparison.py` `_seed_game` (L68-95)** builds `Game(...)` with no `played_at`. Add `played_at: datetime.datetime = _NOW - timedelta(days=1)` param and a module-level `_NOW`; call services with `now_utc=_NOW`. Same treatment in `test_tactic_comparison_service.py`, `tests/routers/test_library_tactic_comparison.py`.

**Router clock pin: `tests/test_feature_route.py` L184-190:**
```python
def _pin(now: datetime.datetime) -> None:
    app.dependency_overrides[dev_now_utc] = lambda: now
yield _pin
app.dependency_overrides.pop(dev_now_utc, None)
```
Copy as a fixture into `tests/test_library_router.py`.

**New `tests/services/test_library_window.py`:** reuse the `_ensure_user`/`_seed_game`/`_seed_analyzed` helper style above (copy, or import from the flaw-comparison test module if it is already shared); cases per RESEARCH Decision -> Test Map. Mind memory note: every non-guest Game insert needs finally-cleanup for eval-lottery isolation.

## Shared Patterns

### Clock
**Source:** `app/routers/openings.py` L14/L31/L53 (`NowUtc` alias). **Apply to:** the 3 comparison routes; services take `now_utc: datetime.datetime` keyword.

### Error handling / Sentry
**Source:** `app/services/library_service.py` L1924-1927. **Apply to:** all three services and any new async helper that owns a try block. No variables in messages, `set_context` with `user_id`.

### Filter composition
**Source:** `_filtered_games_base` -> `apply_game_filters`. **Apply to:** window statement. Never add filter WHERE clauses by hand.

### Id-set restriction
**Source:** `game_ids_any_predicate` (query_utils.py L152-166); usage precedent `endgame_ranked_service.fetch_ranked_inputs` (L188-231, skip queries when id list empty).

### Sequential session use
All awaits sequential on one `AsyncSession`; no `asyncio.gather`.

### Frontend copy constants
**Source:** `frontend/src/components/openings/stats/outOfOpeningCopy.ts` L23-25 mirrors the two constants. Prefer reading `window_months`/`games_cap` from the response instead of adding another mirror.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `months_before` helper (in library_service.py) | utility | transform | No month-arithmetic helper and no dateutil in repo; use RESEARCH Pattern 2 verbatim |
| `temp/library-258/time_snapshot_endpoints.py` | operator script (gitignored) | batch | Prod timing; orchestrator-run; see RESEARCH "Performance Check". Not tracked source. |

## Metadata

**Analog search scope:** app/repositories, app/services, app/routers, app/schemas, frontend/src/{components/library,lib,hooks,pages}, tests/
**Files scanned:** ~15
**Pattern extraction date:** 2026-11-21
