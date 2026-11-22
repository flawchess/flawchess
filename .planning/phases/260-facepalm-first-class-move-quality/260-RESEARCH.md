# Phase 260: Facepalm as a First-Class Move Quality - Research

**Researched:** 2026-11-22
**Domain:** Internal refactor across FastAPI/SQLAlchemy (flaw filter clause builder) and React/TS (move-quality table, eval chart, Flaws filter)
**Confidence:** HIGH for the code map (every file was read in the worktree this session); MEDIUM for the desktop height derivation (computed from classes, still needs a browser measurement)

## Summary

The phase is a split of one existing concept, not new machinery. Every surface it touches already knows what a facepalm is: the frontend predicate `isFacepalmBlunder` (`frontend/src/lib/facepalm.ts:173`), the backend stats cut `FACEPALM_STATS_MIN` (`app/services/blunder_check_rules.py:65`), the query-time score `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`, the "???" glyph `FACEPALM_GLYPH`, the `FacepalmBlunderIcon` and the `SEV_FACEPALM` colour. The work is to route the existing blunder rows, dots and filter values through a three-way split (mistake / blunder-not-facepalm / facepalm) in one shared place per stack, then delete the score range filter.

There are three things the planner must not miss. (1) **Opponent blunders carry no facepalm score in the game card payload today.** `fetch_page_facepalm_scores` applies `player_only_gate`, so every opponent `FlawMarker.facepalm_score` is null. With the code as it is, the opponent column of the new Facepalm row is always 0 and every opponent facepalm stays in the Blunder row and as a red dot, which contradicts the "two-sided" intent of D-01 and the "both sides" note in the discussion log (D-17). This needs an owner decision before the frontend plan is written (Open Question 1). (2) **Under the new filter semantics `["mistake", "blunder"]` no longer means "everything".** It now means "everything except facepalms". That breaks the backend default `_DEFAULT_SEVERITY = ["mistake", "blunder"]` in `get_library_flaws`, the frontend `isFlawFilterNonDefault` (`severity.length === 1`), the FlawsTab URL writer (`severity.length < 2`), the ring logic in `LibraryGameCard` and `SeverityBadge`, and a LibraryGameCard test that asserts "both = no ring". Every "both selected = none selected" shortcut must become "all three selected = none selected". (3) **D-13 collides with Phase 259 in two files beyond the repository and service:** `tests/services/test_facepalm_score.py` imports `_FACEPALM_PCT_SCALE` from `library_repository` (line 40), and 259-12 edits that same test; and 259-12's acceptance check greps `FACEPALM_HIGH_CUTOFF = ` in `frontend/src/lib/facepalm.ts`, whose neighbouring lines D-14 deletes.

**Primary recommendation:** Add one backend `Literal` (`FlawSeverityFilter = Literal["facepalm", "blunder", "mistake"]`) plus one `_severity_clause` helper inside `build_flaw_filter_clauses`, and one frontend classifier `flawMoveCategory(marker)` in `lib/moveStatsCounts.ts` that every table count, cycle list, dot colour and tooltip reads. Plan four units: backend D-12 now, the frontend table/chart split now, the frontend filter change plus D-14 removal now, and backend D-13 after Phase 259 is on `main`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Move quality table (game card and /analysis)

- **D-01: Facepalm is an 8th two-sided row, a main category like the other seven.** Label "Facepalm", the
  existing "???" icon (257 D-22). It is the last row, after Blunder. Not a nested "of which" line (rejected by
  the owner in the explore session). The same 8 rows render in `AnalysisTagsPanel`.
- **D-02: Blunder and Facepalm are disjoint in this table.** Blunder row = blunders that are not facepalms
  ("??" moves), Facepalm row = facepalm blunders ("???" moves). Every move sits in exactly one row, like
  Best vs Gem / Great, and the counts match the icons drawn on the chart and board.
- **D-03: Definition of a facepalm here:** `severity === 'blunder' && isFacepalmBlunder(facepalm_score)`.
  A blunder without a score is never a facepalm and stays in the Blunder row.
- **D-04: Cell cycling follows the split.** The Blunder cell cycles through the "??" plies only, the
  Facepalm cell through the "???" plies only. Zero-count cells stay inert as today.
- **D-05: Mobile compact row:** Gem, Great, Best, Mistake, Blunder, Facepalm, chevron (7 cells, today 8).
  Inaccuracy and Good leave the compact row only; the expanded table keeps all 8 rows. Counts and cycling
  stay scoped to the user's side as today, with the D-02 split.
- **D-06: Info popover (`MoveStatsInfo`).** Add the Facepalm definition to the list, in the wording family
  of the existing facepalm copy: a blunder that should have been easy to see for a player at the mover's
  level. The Blunder definition stays "Costs 15% winning chances or more." The Lichess sentence gains one
  statement: blunders and facepalms together match the Lichess blunder count. Do not state the cut as a
  literal; read `FACEPALM_HIGH_CUTOFF` if the number is shown at all.
- **D-07: Where the split applies.** The move quality table, the eval chart and the Flaws filter tags use
  the split (Blunder = not a facepalm). Everywhere else "blunder" keeps its Lichess meaning, facepalms
  included: Library Stats, the Flaws Timeline, the KPI tiles, accuracy, and the severity stored and
  returned by the API. No blanket copy change.

#### Flaws filter

- **D-08: Three tags in the Flaws row, labelled in the singular and in this order: Facepalm, Blunder,
  Mistake.** Today's "Blunders" / "Mistakes" labels become singular, consistent with the Gem / Great tags. They combine with OR like every
  tag section; nothing selected shows everything, as today. The Facepalm tag uses the "???" icon and the
  dark red `SEV_FACEPALM` in the pill style of the other two.

  | Selected | Listed |
  |---|---|
  | Facepalm | facepalm blunders |
  | Blunder | blunders that are not facepalms (below the cut, or unscored) |
  | Blunder + Facepalm | all blunders |
  | Mistake + Facepalm | mistakes and facepalm blunders |
  | nothing, or all three | all mistakes and blunders |

- **D-09: The Blunder tag now means "blunder that is not a facepalm",** the same split as the table
  (D-02, D-03). An unscored blunder counts as a Blunder. Owner's reasoning: it matches the move quality
  list and the way the Gem / Great tags work.
- **D-10: The Facepalm Score range filter is removed.** No slider, no presets, no hint. Supersedes
  253 D-04 and D-09 to D-12 and this session's first outcome (the "???" on the High preset and a range that
  applies to blunders only). Reasoning: the score is a model output that supports a cut, not 5% steps;
  Gem / Great and the severities are also cuts on continuous quantities with no slider; a hard-to-see
  blunder is the unremarkable case, like a plain Best move. Known loss, accepted by the owner: no way to
  filter for very hard-to-see blunders (0 to 30% apart from 30 to 70%).
- **D-11: The facepalm score stays visible** where it is today (the chip on the Flaws card, the eval chart
  tooltip, the move list, `FacepalmExplanation`). Only the filtering by range goes.
- **D-12: Backend, severity filter.** The shared flaw clause builder in
  `app/repositories/library_repository.py` accepts the facepalm value in the severity filter and applies
  D-08, using `FACEPALM_STATS_MIN` for the cut, so the Games tab, the Flaws tab and every other caller of
  the builder agree. The stored severity and `FlawSeverity` (inaccuracy / mistake / blunder) do not change:
  the filter value set is its own `Literal`. No migration.
  — **Reversibility:** reversible — a query-clause change; the request parameter keeps its name and gains
  one accepted value.
- **D-13: Backend, parameter removal.** `min_facepalm_pct` / `max_facepalm_pct` are removed from the API
  (router, service, repository, `query_utils.py`) together with `_facepalm_clause` and helpers that have no
  reader left. This is the last plan of the phase and runs after Phase 259 has merged to `main`, so it does
  not collide with plans 259-13 and 259-14 in the same files.
  — **Reversibility:** costly — the parameters run through about 15 function signatures; bringing a range
  filter back means re-threading them (git history has the shape).
- **D-14: Frontend removal.** `FacepalmFilter`, the `facepalmMin` / `facepalmMax` store fields, the query
  parameter mapping and the range, preset and summary helpers in `lib/facepalm.ts` that lose their last
  reader (knip gates this). `FACEPALM_HIGH_CUTOFF`, `isFacepalmBlunder`, `toFacepalmPct` and the copy
  constants stay. Any persisted filter state that still carries the range fields must load cleanly.

#### Desktop game card height

- **D-15: The miniboard grows with the table.** The 8th row keeps today's row spacing; the desktop
  miniboard (`DESKTOP_BOARD_SIZE`, 225 in `LibraryGameCard.tsx`, local to that file) is enlarged so the
  board and the move quality card still end level. Every desktop game card gets taller by about one row.
  Rejected: tightening the rows to keep 225px, and letting the card overhang the board.
- **D-16: Everything that is sized to the miniboard height follows it** (the eval chart block and the lane
  row next to the board). The new size is derived from the table, not picked by eye. Mobile sizing
  (`MOBILE_BOARD_SIZE`, 50% viewport) is untouched.

#### Eval chart and filter emphasis

- **D-17: A facepalm blunder's dot is dark red.** Use the existing `SEV_FACEPALM` (theme.ts, equal to the
  Flaws Timeline band swatch); no new theme constant. It applies to every blunder dot that is drawn today,
  for either side, in the normal, highlighted and dimmed states alike. This reverses the "eval-chart flaw
  dots" exclusion of 257 D-22.
- **D-18: The chart tooltip of a facepalm blunder shows the "???" icon** in place of "??", in the same
  dark red.
- **D-19: Highlighting follows D-04:** cycling or hovering the Blunder cell highlights only "??" dots, the
  Facepalm cell only "???" dots.
- **D-20: The filter ring (`outlinedRef`) marks the cells whose tags are selected,** on the user's side:
  Blunder rings the Blunder cell, Facepalm the Facepalm cell, Mistake the Mistake cell. With several tags
  selected (but not all three) each selected cell is ringed, so a single `outlinedRef` no longer suffices.
  Nothing selected, or all three: no ring, as today for "both".

#### Parallel work with Phase 259

- **D-21: The cut belongs to plan 259-12.** This phase never changes the value of `FACEPALM_HIGH_CUTOFF`
  or `FACEPALM_STATS_MIN` and never states the cut as a literal in code, copy or tests. Removing the range
  presets (D-14) deletes `FACEPALM_MID_CUTOFF` and `PRESET_RANGES`; 259-12 only moves the High cutoff, so
  the overlap in `frontend/src/lib/facepalm.ts` is one constant that this phase leaves untouched.
- **D-22: The final visual UAT and the merge wait for 259-12** (the switch release), since the refit
  changes which blunders count as facepalms. Planning and execution of everything but D-13 can run before.
- **D-23: Order of the backend work.** D-12 (the new severity value) is small and local to the clause
  builder and can run now. D-13 (parameter removal) waits for Phase 259 on `main` and is then rebased
  onto it.

### Claude's Discretion

- Wording of the Facepalm definition in `MoveStatsInfo` and of the Lichess sum sentence, within the
  popover-copy rule and "eval, not pawns". Whether the Flaws filter needs a line saying Blunder excludes
  facepalms, and where.
- The name and type of the facepalm filter value on the wire, and the type shape for the 8th category
  (`MoveStatCategory`) and for a multi-cell ring.
- Analytics: the `severity` filter-change target gains the facepalm value; the `facepalm` filter-change
  target loses its only caller and is removed from the registry (a removal, not a rename).
- How D-13 is split and ordered relative to the merge of Phase 259.
- Test updates, including backend tests for the D-08 table.

### Deferred Ideas (OUT OF SCOPE)

- **A filter for very hard-to-see blunders.** Lost with the range filter (D-10). If a need shows up, it
  returns as its own control designed for that purpose, not as a second control on the facepalm dimension.

#### Reviewed Todos (not folded)
- The todo matcher returned keyword matches only (an invalid Tailwind class on a Score axis label, deferred
  review findings of Phase 172, bitboard storage). None concerns this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are mapped (TBD). The CONTEXT.md decisions are the requirements; the planner should cite D-xx in each plan's `requirements:` list.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01..D-04 | 8th Facepalm row, disjoint from Blunder, split by `isFacepalmBlunder`, cycling follows | §Pattern 1 (`flawMoveCategory`), §Frontend map (MoveStats, moveStatsCounts, LibraryGameCard/AnalysisTagsPanel `categoryPlies`), Open Question 1 |
| D-05 | Compact row of 6 categories + chevron | §Frontend map (MoveStats `grid-cols-8` at line 327) |
| D-06 | Popover copy | §Frontend map (MoveStatsInfo lines 95-137), §Code Examples |
| D-07 | Split only in table, chart, filter | §Don't Hand-Roll, Pitfall 7 |
| D-08, D-09, D-12 | Three OR tags; backend clause | §Pattern 2 (`_severity_clause`), §Backend map, Pitfall 2 |
| D-10, D-11, D-13, D-14 | Range filter removal | §Removal inventory (backend and frontend), §Phase 259 collision table |
| D-15, D-16 | Desktop miniboard grows with the table | §Desktop height derivation |
| D-17..D-19 | Dark red dot, "???" tooltip, highlight split | §Frontend map (EvalChart lines 289-293, 419-458, 1205-1229), Pitfall 5 |
| D-20 | Multi-cell ring | §Pattern 3, Pitfall 2 |
| D-21..D-23 | Parallel-work rules | §Phase 259 collision table |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend layout: routers are HTTP only, services hold logic, repositories hold SQL; all game filtering goes through `apply_game_filters()` in `app/repositories/query_utils.py`. Never duplicate filter logic.
- Never use bare `str` for a fixed value set: `Literal[...]` in schemas, function signatures, service and repository params. Use `Sequence[...]` (not `list[...]`) for params receiving `list[Literal]` values (list is invariant).
- `uv run ty check app/ tests/ scripts/` zero errors; `# ty: ignore[rule]` only where unfixable, with the rule name.
- No magic numbers: named constants. (D-21 adds: never state the facepalm cut as a literal in code, copy or tests.)
- Nesting depth <= 4 per function (`scripts/check_function_size.py app/ --fail-over-depth 4`; eslint `max-depth` 4 in the frontend). Soft guidance ~100 logic lines / cognitive complexity 15.
- Comment bug fixes at the fix site.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; never embed variables in error messages.
- Never `asyncio.gather` on one `AsyncSession`.
- Frontend: theme colours only from `theme.ts`; `text-sm` floor (tooltip/popover bodies may use `text-xs`); `data-testid` on every interactive element; apply changes to mobile too; `npm run build` (tsc -b) before integrating type changes; knip gates dead exports; `noUncheckedIndexedAccess` is on.
- Analytics: register targets in `FeatureEventMap` (`lib/analytics.ts`); never rename an existing event or target; removal of a target whose only caller is removed is allowed per CONTEXT discretion.
- Copy: em-dashes sparingly; never "pawns" as the eval unit.
- Pre-merge gate (full) before squash-merging to `main`; CHANGELOG bullets under `## [Unreleased]`.
- GSD scope: do not add unplanned features; flag instead.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Facepalm/blunder split for filtering (D-08, D-12) | API / Backend (repository `build_flaw_filter_clauses`) | Database (query-time `facepalm_expr`) | The filter selects rows; the score is a SQL expression over stored facts, so the split must be a WHERE clause shared by Games EXISTS and Flaws list |
| Facepalm/blunder split for display (D-01..D-05, D-17..D-19) | Browser / Client (`lib/moveStatsCounts.ts`) | — | Counts and cycling already reduce `flaw_markers` client-side; `facepalm_score` is already on each marker |
| Opponent facepalm scores on markers (Open Question 1) | API / Backend (`fetch_page_facepalm_scores`) | — | Only the backend decides whether opponent scores reach the payload; the frontend cannot compute the score |
| Filter state and URL sync | Browser / Client (`useFlawFilterStore`, `FlawsTab`) | — | In-memory module store, URL params on the Flaws tab only |
| Range-filter removal (D-13, D-14) | API / Backend and Browser / Client | — | Parameters threaded through both stacks |
| Desktop card geometry (D-15, D-16) | Browser / Client | — | Tailwind layout in `LibraryGameCard.tsx` |

## Standard Stack

No new libraries. Everything uses the existing stack (FastAPI 0.141.x, SQLAlchemy 2.x async, Pydantic v2, React 19, TypeScript, Tailwind 4, recharts, vitest, pytest). [VERIFIED: CLAUDE.md, frontend/package.json:75 `"tailwindcss": "^4.3.0"`]

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Backend map (D-12, D-13)

### Severity value flow, router to clause

[VERIFIED: app/routers/library.py:35-38]
```python
# The Games/Flaws filter offers only the mistake/blunder severity tiers
# (inaccuracies are count-only, never a filter; game_flaws stores M+B only).
# Constraining the Query type rejects anything else at the HTTP boundary.
SeverityFilter = Literal["mistake", "blunder"]
```
`SeverityFilter` types the `severity: list[SeverityFilter] | None = Query(default=None)` parameter of **six** routes: `/games` (line 72), `/flaw-stats` (185), `/flaw-comparison` (233), `/facepalm-comparison` (287), `/tactic-comparison` (331), `/flaws` (389). [VERIFIED: grep + Read of app/routers/library.py]

Two downstream paths, both ending in `build_flaw_filter_clauses`:

1. **Games tab and all stats endpoints** — router passes `flaw_severity=list(severity) if severity else None` (lines 133, 220, 274, 318, 376) → service (`get_library_games`, `get_flaw_stats`, `get_flaw_comparison`, `get_facepalm_comparison`, `get_tactic_comparison`) → repository functions with `flaw_severity: Sequence[str] | None` (`query_filtered_games`, `_filtered_games_base`, `count_filtered_and_analyzed`, `count_analyzed_by_tc`, `fetch_recent_window_rows`, `_flaw_comparison_anchor`, `fetch_flaw_comparison`, `fetch_facepalm_counts`, `fetch_facepalm_comparison`, `fetch_tactic_comparison`, `fetch_flaw_trend_rows`) → `apply_game_filters(flaw_severity=...)` → `flaw_exists_from_table` → `build_flaw_filter_clauses`. [VERIFIED: awk/grep map of app/repositories/library_repository.py and app/services/library_service.py]
   In `query_utils.py` the value is cast, not validated: [VERIFIED: app/repositories/query_utils.py:399, 414, 420]
   ```python
   from app.services.flaws_service import FlawSeverity, FlawTag
   if flaw_severity or flaw_tags or tactic_active or facepalm_active:
   severities = cast(Sequence[FlawSeverity], flaw_severity or [])
   ```
2. **Flaws tab** — router passes `severity=list(severity) if severity else []` (line 442) → `library_service.get_library_flaws(severity: list[FlawSeverity])` → `effective_severity = severity if severity else _DEFAULT_SEVERITY` → `query_flaws(severity: Sequence[FlawSeverity])` → `build_flaw_filter_clauses`. [VERIFIED: app/services/library_service.py:1424-1427, 1434, 1474]
   ```python
   # Default severity tiers when none are specified (M+B only)
   _DEFAULT_SEVERITY: list[FlawSeverity] = ["mistake", "blunder"]
   ```

The frontend never sends `severity` to the stats endpoints: every stats hook caller passes `DEFAULT_FLAW_FILTER` (`LibraryStatsSections.tsx` lines 199, 243-245, 359-360, 429-431; `useLibraryStatsTc.ts:67`) or `NO_FLAW_FILTER` (`FlawsTab.tsx:238`). Widening the shared `SeverityFilter` therefore changes the stats routes' accepted values but not their behaviour for the shipped UI. [VERIFIED: grep of frontend callers]

### Current clause and the types involved

[VERIFIED: app/services/flaws_service.py:108] `FlawSeverity = Literal["inaccuracy", "mistake", "blunder"]` — stays 3-valued (D-12).
[VERIFIED: app/repositories/game_flaws_repository.py:30] `_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}` — a `"facepalm"` key lookup would raise `KeyError`, so the new value must never reach `_SEVERITY_INT[s]`.
[VERIFIED: app/repositories/library_repository.py:743-748]
```python
    # Severity filter — set membership. The UI exposes Blunders/Mistakes as
    # independent toggles, so ["mistake"] must match mistakes ONLY (not "mistakes or
    # worse"). A prior MIN-threshold (severity >= min) leaked blunders into a
    # mistakes-only selection. game_flaws stores only mistake(1)/blunder(2).
    if severity:
        clauses.append(GameFlaw.severity.in_([_SEVERITY_INT[s] for s in severity]))
```
[VERIFIED: app/repositories/library_repository.py:647-658] signature:
```python
def build_flaw_filter_clauses(
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
    tactic_families: Sequence[str] = (),
    orientation: TacticOrientation = "either",
    min_tactic_depth: int | None = None,
    max_tactic_depth: int | None = None,
    decided_lost: ColumnElement[bool] | None = None,
    min_facepalm_pct: int | None = None,
    max_facepalm_pct: int | None = None,
    facepalm_score: ColumnElement[float] | None = None,
) -> list[ColumnElement[bool]]:
```
Callers of `build_flaw_filter_clauses`: `flaw_exists_from_table` (line 823, no `facepalm_score`) and `query_flaws` (line 1213, passes `facepalm_score=facepalm_chip`, the same bound expression it later selects as the chip at line ~1318). Callers of `flaw_exists_from_table`: only `apply_game_filters` (query_utils.py:422). [VERIFIED: grep + Read]

Both callers apply `player_only_gate(GameFlaw.ply, Game.user_color)`, so the filter stays user-only, as 257 D-06 requires. [VERIFIED: library_repository.py:837-842 and the query_flaws WHERE]

### The cut

[VERIFIED: app/services/blunder_check_rules.py:61-65]
```python
# 257 D-01: the library stats cut, the label meaning of a facepalm blunder (253 D-23: "should
# score above 70%"). Separate from the drill's FACEPALM_SCORE_MIN on purpose. It equals the
# Facepalm filter's High preset bound (70 / 100.0 in library_repository), so a stats row counts
# exactly the blunders the High preset lists (257 research Pitfall 7).
FACEPALM_STATS_MIN: float = 0.7
```
Already imported in `library_repository.py` line 41: `from app.services.blunder_check_rules import FACEPALM_LIBRARY_LAMBDA, FACEPALM_STATS_MIN`. The stats count compares `per_blunder.c.s >= FACEPALM_STATS_MIN` (line 1752). The new clause must use the same comparison so the filter, the timeline band and the stats rows agree. (The comment block above mentions the High preset; after D-13 it is stale and 259-12 may rewrite it. Leave it to D-13, see collision table.)

**The pin test** [VERIFIED: tests/services/test_facepalm_score.py:40, 1194-1225]:
```python
from app.repositories.library_repository import _FACEPALM_PCT_SCALE
...
HIGH_PRESET_PCT = 70
STATS_MIN_VALUE = 0.7
...
def test_facepalm_stats_min_is_the_high_preset_cut() -> None:
    # Read through the module so a missing constant fails this assertion, not the file's import.
    stats_min = getattr(blunder_check_rules, "FACEPALM_STATS_MIN", None)
    assert stats_min == STATS_MIN_VALUE
    assert stats_min == HIGH_PRESET_PCT / _FACEPALM_PCT_SCALE
    assert stats_min != FACEPALM_SCORE_MIN
```
It does not read the frontend file; it restates 70 as a literal. Plan 259-12 owns these two literals ("update STATS_MIN_VALUE / HIGH_PRESET_PCT ... if the stats cut moved", 259-12-PLAN.md). D-13 deletes `_FACEPALM_PCT_SCALE`, so D-13 must touch this test's import (see collision table).

### Removal inventory for D-13 (all read this session)

| File | Symbol / lines | Action |
|------|----------------|--------|
| `app/routers/library.py` | `/games` params 84-95, forward 139-140; `/flaws` params 402-413, forward 455-456; reads `library_repository.FACEPALM_PCT_MIN/MAX` | delete |
| `app/services/library_service.py` | `get_library_games` params 968-969, forward 1029-1030; `get_library_flaws` params 1447-1448, forward 1500-1501 | delete |
| `app/repositories/query_utils.py` | `apply_game_filters` params 196-199 (with comment), lazy import `facepalm_range_active` 396, `facepalm_active` 410-413, gate term in 414, forward 430-431, docstring lines | delete; gate becomes `if flaw_severity or flaw_tags or tactic_active:` |
| `app/repositories/library_repository.py` | constants 94-102 (`FACEPALM_PCT_MIN`, `FACEPALM_PCT_MAX`, `_FACEPALM_PCT_SCALE` and comment); `facepalm_range_active` 340-347; `_facepalm_clause` 350-376; `build_flaw_filter_clauses` params `min_facepalm_pct`/`max_facepalm_pct` + docstring + lines 763-766; `flaw_exists_from_table` params 778-779, docstring, forward 831-832; `query_flaws` params 1163-1164, docstring, forward 1221-1222, the chip comment at ~1207; `query_filtered_games` params 1834-1835, docstring 1859-1861, forward 1885-1886 | delete |
| `build_flaw_filter_clauses(facepalm_score=...)` | param kept | **Keep**: after D-12 the new severity clause reads it, so it does not lose its last reader |
| `FACEPALM_LIBRARY_LAMBDA`, `facepalm_expr` imports | kept | still read by the chip and the new clause |

Constants file comment: [VERIFIED: app/repositories/library_repository.py:94-102]
```python
# Facepalm score range filter: inclusive whole-percent bounds on the floored scale the
# Flaws-card Facepalm chip shows. Mirrors FACEPALM_PCT_MIN / FACEPALM_PCT_MAX in
# frontend/src/lib/facepalm.ts. Deliberately this module's own constants, independent of
# the blunder-check drill cut, so a refit of that cut never moves the filter (D-09, D-07).
# Public because the router uses them as Query bounds.
FACEPALM_PCT_MIN: int = 0
FACEPALM_PCT_MAX: int = 100
_FACEPALM_PCT_SCALE: float = 100.0
```

Tests that go with D-13 (range-only, delete or rewrite): `tests/test_library_repository.py` `_compile_facepalm_clauses` (2698), `TestFacepalmBuildFlawFilterClauses` (2724-2780), `TestFacepalmGamesFilter` (2819-2928, rewrite its three cases onto `severity=["facepalm"]`); `tests/repositories/test_library_repository.py` `_query_facepalm_flaws` (861-889) and `TestFacepalmRangeQueryFlaws` (891-1060, keep the chip/expression assertions in `test_item_carries_expression_score_or_none`, drop range cases); `tests/test_query_utils.py` `TestFacepalmGate` (492-540); `tests/test_library_router.py` `TestFacepalmFilterEndToEnd` (2750, keep the two payload tests), `TestFacepalmGamesEndToEnd` (2822), `TestFacepalmGamesParamThreading` (2878), `TestFacepalmParamValidation` (2926-2990). [VERIFIED: grep of test class names]

After deletion, FastAPI ignores unknown query parameters, so a stale cached PWA that still sends `min_facepalm_pct` gets an unfiltered list, not a 422. [ASSUMED] (standard FastAPI behaviour, not probed this session; a one-line router test can confirm it.)

### Phase 259 collision table

| Plan | Files it modifies that this phase also touches | Region it edits | This phase's edit in that file | Ordering |
|------|-----------------------------------------------|-----------------|--------------------------------|----------|
| 259-12 | `frontend/src/lib/facepalm.ts` | line 40 `export const FACEPALM_HIGH_CUTOFF = 70;` and possibly its doc comment 35-39; its acceptance check is `grep -c "FACEPALM_HIGH_CUTOFF = " frontend/src/lib/facepalm.ts` prints 1 | D-14 deletes lines 29-33 (`FACEPALM_STEP`, `FACEPALM_MID_CUTOFF`) and 66-155 (presets, helpers), rewrites the header 1-15 | D-14 runs now, but must leave lines 34-40 byte-identical (the comment "Mid / High boundary, included in both (... D-09)" becomes stale; fix it in the post-259 plan, not now). Deleting line 33 next to line 35 risks a merge conflict only if 259-12 edits the comment; keep one unchanged blank line between |
| 259-12 | `tests/services/test_facepalm_score.py` | stats-min test 1194-1225 (`STATS_MIN_VALUE`, `HIGH_PRESET_PCT`) | D-13 must replace the `_FACEPALM_PCT_SCALE` import (line 40) and the expression on line 1224 | D-13 only, after 259 merges |
| 259-12 | `frontend/src/lib/__tests__/gapBar.test.ts` (pins `expect(FACEPALM_HIGH_CUTOFF).toBe(70)` at line 199) | — | none | no conflict |
| 259-12 | `CHANGELOG.md` | adds a bullet naming "the Facepalm filter" | adds bullets | Wording conflict: 259's bullet mentions a filter this phase removes. Flag at merge time |
| 259-13 | `app/repositories/game_flaws_repository.py`, scoring services, scripts, line-material tests | — | none (this phase reads `_SEVERITY_INT` only) | no conflict |
| 259-14 | `app/repositories/library_repository.py` | `disable_jit_for_transaction` (~1679) and its calls in `fetch_facepalm_counts` (~1717) and `fetch_facepalm_comparison` (~2589) | D-12: `build_flaw_filter_clauses` (647-768) and a new helper next to it; D-13: lines 94-102, 340-376, 647-840, 1146-1225, 1828-1890 | Different hunks. D-12 can run now; D-13 after merge (locked) |
| 259-14 | `app/services/library_service.py` | ~2105-2130 (`get_facepalm_comparison` JIT call) | D-12: types of `get_library_flaws` and `_DEFAULT_SEVERITY` (1424-1474); D-13: 968-1030, 1447-1501 | Different hunks |
| 259-14 | `tests/services/test_flaw_comparison.py`, `tests/services/test_facepalm_score.py` | JIT tests, array CHECK tests | none for D-12 | — |

[VERIFIED: .planning/phases/259-facepalm-first-principles-refit/259-12-PLAN.md, 259-13-PLAN.md, 259-14-PLAN.md frontmatter and task text]

## Frontend map (verified this session)

### Category type and counts — `frontend/src/lib/moveStatsCounts.ts`
[VERIFIED: lib/moveStatsCounts.ts:19, 47-59]
```ts
export type MoveStatCategory = 'gem' | 'great' | 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';
...
export function severityCountsBySide(
  markers: FlawMarker[],
): Record<MoveStatSide, Record<FlawSeverity, number>> {
  ...
  for (const m of markers) {
    const side = moverColorAtPly(m.ply);
    out[side][m.severity]++;
  }
```
`FlawMarker` already carries the score: [VERIFIED: types/library.ts:184-189] `facepalm_score?: number | null;` with the comment "null/absent when unscored (today the backend scores only the user's own blunders)".

### The opponent-score gap (Open Question 1)
[VERIFIED: app/repositories/library_repository.py:1403-1436, `fetch_page_facepalm_scores`]
```python
    Returns owner-side plies only (`player_only_gate` on the game's own user_color): opponent
    rows carry facts and score in SQL since SEED-261114-iuv Part A step 4, but opponent markers
    keep a null facepalm score and type because showing opponent scores is an open product
    decision (Part B; 257 D-06). Callers still gate on severity.
    ...
            player_only_gate(GameFlaw.ply, Game.user_color),  # owner side only
```
This feeds both the Library card (`library_service.py:1060-1062, 1097`) and the single-game `/analysis` card (`library_service.py:861-863`). Consequence: the opponent Facepalm cell is always 0, opponent facepalms count as Blunder and draw as red squares. 257 D-06 restricts only drill selection and the library tag filters to the user, not display. [VERIFIED: 257-CONTEXT.md D-06 "Opponent scores stay out of drill selection and the library tag filters (user-only, `player_only_gate`)."]

### `MoveStats.tsx` (`frontend/src/components/library/MoveStats.tsx`)
- `CATEGORY_ORDER` 45-53, `CATEGORY_LABELS` 55-63, `SEVERITY_CATEGORIES` 65, `isSeverityCategory` 78-80, `CATEGORY_DEFINITIONS` 95-103, `MoveStatsInfo` 106-138, `outlinedRef?: MoveStatsCellRef | null` prop 157-158, `countFor` 210-213, `renderCountCell` 247-284 (ring: `sameCellRef(outlinedRef, ref) && ACTIVE_FILTER_RING_CLASS` line 272), accuracy strip 292-308 with the comment "py-0.5 (not py-1) keeps the card's natural height under the Library desktop miniboard (225px)" (lines 289-291), compact row 325-385 with `className="grid grid-cols-8 items-center gap-1 p-2"` (327) iterating `CATEGORY_ORDER` (330) and **no** outline ring on compact cells (357-360), table 393-419. [VERIFIED: Read]
- Icons: `<MoveQualityIcon quality={category} ...>` at 120, 337, 411. `MoveQualityIcon` takes `MoveQuality` [VERIFIED: lib/moveQuality.ts:37 `export type MoveQuality = 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder' | 'gem' | 'great';`], a different concept (live engine grading) with a file-level warning against merging. Adding `'facepalm'` to `MoveStatCategory` makes these three calls fail `tsc -b`. Render `FacepalmBlunderIcon` (`components/icons/SeverityGlyphIcon.tsx:65-67`) for the facepalm category via a local `CategoryIcon` in MoveStats instead of widening `MoveQuality`. Both icons draw `circle cx=12 cy=12 r=11` in a 24-unit viewBox, so sizes match. [VERIFIED: Read of MoveQualityIcon.tsx:48-51 and SeverityGlyphIcon.tsx:40-49]

### Cycling maps — two copies by convention
- `LibraryGameCard.tsx` `categoryPlies` 432-449 (`push(fm.severity, moverColorAtPly(fm.ply), fm.ply)` line 441), `pliesForRef` 588-593, `highlightedPlies` 489-511 (category refs read `categoryPlies`), `facepalmPlies` 303-311 (hover miniboard badge). [VERIFIED: Read]
- `AnalysisTagsPanel.tsx` keeps its own `FlawRef` (36-42), `categoryPliesKey` (58-60) and `categoryPlies` (172-189, `push(fm.severity, ...)` line 181) "per this component's 'trivially safe copies, not shared extractions' convention". [VERIFIED: Read]
Both `push(fm.severity, ...)` lines must call the shared classifier; then D-04 and D-19 follow automatically because `highlightedPlies` for category refs is read from `categoryPlies`.

### Ring — `LibraryGameCard.tsx:619-629`
[VERIFIED: Read]
```ts
  const outlinedCellRef: MoveStatsCellRef | null = useMemo(() => {
    if (userColor == null || flawFilter.severity.length !== 1) return null;
    const sev = flawFilter.severity[0];
    if (sev == null) return null;
    return { kind: 'category', category: sev, side: userColor };
  }, [flawFilter.severity, userColor]);
```
Passed at 1067 (mobile) and 1270 (desktop). `AnalysisTagsPanel` passes no ring. The filter values `'facepalm' | 'blunder' | 'mistake'` equal the `MoveStatCategory` names, so the mapping is direct.

### Eval chart — `frontend/src/components/library/EvalChart.tsx`
- [VERIFIED: EvalChart.tsx:288-293]
  ```ts
  /** Map FlawSeverity to its theme color constant. No inline literals. */
  function severityColor(sev: FlawSeverity): string {
    if (sev === 'blunder') return SEV_BLUNDER;
    if (sev === 'mistake') return SEV_MISTAKE;
    return SEV_INACCURACY;
  }
  ```
- `flawDotElement(isUser, color, ...)` 364-405 (filled circle for the user, hollow square for the opponent); `buildDotRenderer` 415-459 computes `const color = severityColor(marker.severity);` (444) once for all states, so swapping the colour source covers normal, highlighted and dimmed (D-17). `allMarkerMap` (609) holds both sides.
- Tooltip 1205-1229: `MarkerGlyph` (a dot-shaped glyph, not "??") coloured `severityColor(activeMarker.severity)` plus the text `{'You' | 'Opponent'} · {Severity capitalised}`; `FacepalmTooltipLine` below for scored blunders (1221-1228). The tooltip draws no "??" today, so D-18 ("???" in place of "??") needs an interpretation (Open Question 3).
- Testability: `buildDotRenderer` and `severityColor` are not exported; the test file tests the exported `bestMoveDotSpec` from `lib/bestMoveDot.ts` instead (EvalChart.test.tsx:43). Follow that precedent: put the colour choice in a pure lib function and unit-test it.

### Theme — `frontend/src/lib/theme.ts`
[VERIFIED: theme.ts:66, 73, 289, 521-527]
```ts
export const SEV_BLUNDER = 'oklch(0.58 0.19 25)';
export const SEV_BLUNDER_BG = 'oklch(0.58 0.19 25 / 0.14)';
export const ACTIVE_FILTER_RING_CLASS = 'ring-2 ring-offset-1';
export const FACEPALM_BAND_FILL = 'oklch(0.42 0.17 25 / 0.70)';
export const FACEPALM_BAND_SWATCH = 'oklch(0.42 0.17 25)';
export const SEV_FACEPALM = FACEPALM_BAND_SWATCH;
```
There is no `SEV_FACEPALM_BG`. The severity pill takes `{ color, bg }` (`FlawFilterControl.tsx` `SeverityButtonConfig` 121-127, `style={selected ? { color, borderColor: color, backgroundColor: bg } : undefined}` line 248). The Facepalm pill needs a bg tint; D-17's "no new theme constant" is about the dot. Adding `SEV_FACEPALM_BG = 'oklch(0.42 0.17 25 / 0.14)'` (the `SEV_*_BG` 14% alpha convention) is the clean way; flag it to the owner since it is a new constant (Open Question 4).

### Flaws filter — `frontend/src/components/filters/FlawFilterControl.tsx`
- Props 58-61 (`severity: ('blunder' | 'mistake')[]`), facepalm props 82-90, `SEVERITY_BUTTONS` 129-132 [VERIFIED]:
  ```ts
  const SEVERITY_BUTTONS: SeverityButtonConfig[] = [
    { sev: 'blunder', label: 'Blunders', icon: BlunderIcon, color: SEV_BLUNDER, bg: SEV_BLUNDER_BG },
    { sev: 'mistake', label: 'Mistakes', icon: MistakeIcon, color: SEV_MISTAKE, bg: SEV_MISTAKE_BG },
  ];
  ```
- `SeverityFilterButton` 235-255: testid `filter-flaw-severity-${sev}`, aria-label `Filter flaws by severity: ${label}`.
- `handleSeverityToggle` 511-517 tracks `trackFeature('filter-change', { target: 'severity', value: sev })`.
- Facepalm block 605-613: `{onFacepalmChange && <FacepalmFilter .../>}` and divider `filter-facepalm-divider`. Both go (D-14).
- Callers: `FlawsTab.tsx` 321, 546; `GamesTab.tsx` 338, 525 (each passes `facepalm=` / `onFacepalmChange=` at FlawsTab 341-343, 566-568; GamesTab 358-360, 549-551); `LibraryFilterPanel.tsx:86` (severity only, no facepalm). [VERIFIED: grep]

### Store — `frontend/src/hooks/useFlawFilterStore.ts`
[VERIFIED: useFlawFilterStore.ts:16, 42-43, 61-62, 81-99, 106]
```ts
  severity: ('blunder' | 'mistake')[];
  facepalmMin: number;
  facepalmMax: number;
...
    filter.severity.length === 1 ||
...
    (filter.facepalmMin ?? DEFAULT_FACEPALM_VALUE.min) !== DEFAULT_FACEPALM_VALUE.min ||
    (filter.facepalmMax ?? DEFAULT_FACEPALM_VALUE.max) !== DEFAULT_FACEPALM_VALUE.max ||
...
let currentFlawFilter: FlawFilterState = { ...DEFAULT_FLAW_FILTER };
```
The store is module-level memory only, no `localStorage`/`sessionStorage` (grep of hooks, pages/library, lib found none for the flaw filter). The only URL persistence is `FlawsTab.tsx` 93-121, which reads and writes `tag`, `severity` and `tactic` only, never the facepalm range. So no persisted state carries `facepalmMin`/`facepalmMax`; "load cleanly" (D-14) is satisfied by construction. What does need care is old URLs: [VERIFIED: FlawsTab.tsx:102, 116-118]
```ts
    const urlSeverity = initialSearchParams.current.getAll('severity') as ('blunder' | 'mistake')[];
...
    if (flawFilter.severity.length < 2) {
      flawFilter.severity.forEach((s) => params.append('severity', s));
    }
```
The reader casts without validation (an unknown `?severity=` value is sent to the API and 422s; pre-existing), and the writer's `< 2` encodes the old "both = all" rule.

### Query mapping — `frontend/src/hooks/useLibrary.ts` and `frontend/src/api/client.ts`
- `buildLibraryParams(filters, severity: ('blunder' | 'mistake')[], ...)` 89-110; `useLibraryGames` sends severity only when `isFlawFilterNonDefault` (139-150) and builds `facepalmParam` 165-171 into the query key (179) and request (189); `useLibraryFlaws` always sends severity (380) and builds `facepalmParam` 389-395 (key 403, request 413). [VERIFIED: Read]
- `client.ts`: `severity?: ('blunder' | 'mistake')[]` at 503, 520, 573, 611, 637; `min_facepalm_pct` / `max_facepalm_pct` at 531-532, 555-556 (getGames) and 647-648, 669-670 (getFlaws). [VERIFIED: grep]
- Inline `'blunder' | 'mistake'` unions elsewhere: `FlawFilterControl.tsx` 59, 61, 123, 226, 511; `analytics.ts:512`. Replace all with one exported `FlawSeverityFilter` type in `types/library.ts`.

### Analytics — `frontend/src/lib/analytics.ts`
[VERIFIED: analytics.ts:25, 458-478, 512, 517]
```ts
import type { FacepalmPreset } from '@/lib/facepalm';
export const FILTER_TARGETS = [ ..., 'severity', ..., 'facepalm', 'has-gem', ... ] as const;
  | { target: 'severity'; value: Extract<FlawSeverity, 'blunder' | 'mistake'> }
  | { target: 'facepalm'; value: FacepalmPreset | 'custom' }
```
Only caller of `target: 'facepalm'` is `FacepalmFilter.tsx` (63, 76). The `analytics.test.ts` "kebab-case slug" test iterates `FILTER_TARGETS` (line 306) and survives the removal. The test `FlawFilterControl.test.tsx:530` (`expectSingleEvent({ target: 'facepalm', value: 'high' })`) goes with FacepalmFilter.

### `lib/facepalm.ts` after D-14
Keep: `FACEPALM_HIGH_CUTOFF` (40, untouched), `FACEPALM_DEFINITION`/`FACEPALM_TRAINING` (48-49, private), `FACEPALM_CARD_INFO` (50), `FACEPALM_LOW_COVERAGE_NOTE` (52), `FACEPALM_TIMELINE_INFO` (54), `facepalmScoreMeaning` (61, used by `FacepalmExplanation.tsx`), `FACEPALM_PCT_SCALE` (67), `FACEPALM_PCT_MIN`/`FACEPALM_PCT_MAX` (24, 27; still read by `toFacepalmPct` for clamping), `toFacepalmPct` (164), `isFacepalmBlunder` (173), type tint block (180-210).
Delete: `FACEPALM_STEP` (30), `FACEPALM_MID_CUTOFF` (33), `FACEPALM_DEFAULT_PRESET` (70), `FacepalmPreset` (74), `FacepalmValue` (80), `PRESET_RANGES` (87), `PRESET_LABELS` (95), `PRESET_ORDER` (102), `DEFAULT_FACEPALM_VALUE` (105), `derivePreset` (110), `presetToRange` (119), `sliderToRange` (124), `isFacepalmNarrowed` (132), `formatFacepalmSummary` (141), `facepalmToQueryParams` (150), and the slider-centric header 1-15. [VERIFIED: grep -n of exports]
knip runs with `"ignoreExportsUsedInFile": true` (`frontend/knip.json`), so `FACEPALM_PCT_MIN`/`MAX` may stay exported. [VERIFIED: Read of knip.json]

### Other ring surface: `SeverityBadge`
[VERIFIED: components/library/SeverityBadge.tsx:135-139]
```ts
  const isActive =
    showActiveFilterRing &&
    (severity === 'blunder' || severity === 'mistake') &&
    flawFilter.severity.length === 1 &&
    flawFilter.severity.includes(severity);
```
Used by `FlawCard.tsx:352` (Flaws tab card, passes `facepalm={isFacepalmBlunder(flaw.facepalm_score)}` at 358) and `TrainPuzzleCard.tsx:173`. Under D-08 a facepalm card listed by the Facepalm tag would never ring, and `["blunder"]` would ring a "??" badge correctly by accident only. Not named in CONTEXT; recommend aligning it with D-20 in the filter plan (Open Question 5).

### Generated files
None affected. `frontend/src/generated/` holds `botStrengthCurves.ts`, `endgameZones.ts`, `flawThresholds.ts`, `personaCalibration.ts`; none mention facepalm or severity filters. No `scripts/gen_*.py` re-run is needed. [VERIFIED: ls + grep -il]

## Desktop height derivation (D-15, D-16)

Layout facts [VERIFIED: LibraryGameCard.tsx:81-82, 1187-1279; MoveStats.tsx; index.css:221-230, 701-713]:
- `const DESKTOP_BOARD_SIZE = 225;` is used once: `<LazyMiniBoard size={DESKTOP_BOARD_SIZE} .../>` (1198). `LazyMiniBoard` sizes its placeholder with `style={{ width: size, height: size }}` (LazyMiniBoard.tsx:49), so the lazy placeholder follows automatically.
- The board row is `flex gap-3 items-stretch`; the right column stretches to the row height; inside it the lane row is `flex-1 flex gap-3 items-stretch`. Left lane: EvalChart with a **fixed** `heightClass="h-[104px]"` ("Chart + 16px slider row = 104px", 1236-1237), then the tags card `flex-1` filling the rest. Right lane: `shrink-0 w-64 flex flex-col` containing `MoveStats className="flex-1"`.
- So on desktop nothing except the board itself is sized from `DESKTOP_BOARD_SIZE`. The row height is `max(board, MoveStats natural height, left-lane natural height)`. Today MoveStats is shorter than the board and stretches to it; with 8 rows it becomes taller and the board stops short. The mobile eval block (`h-[114px]`, "Chart + 16px slider row = MOBILE_BOARD_SIZE (130px)", 1152-1155) is tied to `MOBILE_BOARD_SIZE` and stays untouched (D-16).
- `.charcoal-texture` has `border: 1px solid var(--card-edge)` (index.css:229). Desktop `text-sm` is Tailwind's 14px/20px; the 16px/24px bump in index.css:708-712 applies only below 640px.

MoveStats natural height at `lg`, computed from the classes:

| Part | Classes | px |
|------|---------|----|
| card border top + bottom | `.charcoal-texture` 1px | 2 |
| accuracy strip | `py-0.5` (2+2) + max(h4 `py-1.5` + 20px line, pill `py-1.5` + 20px line) = 32, `border-b` 1 | 37 |
| table padding | `p-2` | 16 |
| each category row | `py-0.5` (2+2) + 20px (icon `h-5`, `text-sm` line) | 24 |
| **7 rows (today)** | 2 + 37 + 16 + 7×24 | **223** |
| **8 rows** | 2 + 37 + 16 + 8×24 | **247** |

The 223 figure is consistent with the code comment that `py-1` instead of `py-0.5` (+4px) would push the 225px row "1-2px taller" (227). [VERIFIED by arithmetic against MoveStats.tsx:289-291 comment; the per-row 24px is ASSUMED until measured, since an inline `<button>` inside a block line box can add a pixel or two of baseline/strut slack.]

**Recommendation:** derive the size in code from named constants and the category count, and round up to a multiple of 8 so the 8×8 board squares land on whole pixels (225 gives 28.125px squares; 248 gives 31px):
```ts
// MoveStats natural desktop height: card borders + accuracy strip + table padding + one row per
// category (lg text-sm = 20px line; each row py-0.5). Mirrors the classes in MoveStats.tsx.
const MOVE_STATS_CHROME_PX = 2 + 37 + 16;
const MOVE_STATS_ROW_PX = 24;
const BOARD_SQUARES = 8;
const DESKTOP_BOARD_SIZE =
  Math.ceil((MOVE_STATS_CHROME_PX + MOVE_STATS_CATEGORY_COUNT * MOVE_STATS_ROW_PX) / BOARD_SQUARES) * BOARD_SQUARES; // 248
```
with `MOVE_STATS_CATEGORY_COUNT` exported from `MoveStats.tsx` (`CATEGORY_ORDER.length`). Then verify in a real browser at `lg`: `getBoundingClientRect().height` of `[data-testid="move-stats-table-card-<id>"]` must be <= the board container height, and the two bottoms must be level. jsdom cannot measure layout, so this is a browser check (per the project memory, run it yourself with the browser tools, not as a deferred human item). Also update the stale "225px" comments in `MoveStats.tsx:289-291` and `LibraryGameCard.tsx:1259`.

The eval chart on desktop is **not** board-sized (fixed `h-[104px]`), so with a 248px board the extra ~23px lands in the tags card under the chart. D-16 names "the eval chart block" as following the board; whether the owner wants the chart taller is Open Question 2.

## Architecture Patterns

### System Architecture Diagram

```
                 Flaws filter tags (Facepalm | Blunder | Mistake)            game card / analysis payload
                              |                                                        |
                 useFlawFilterStore.severity: FlawSeverityFilter[]           GameFlawCard.flaw_markers[]
                     |                    |                                  (severity + facepalm_score)
       isFlawFilterNonDefault     FlawsTab URL sync                                     |
                     |                                                       flawMoveCategory(marker)
            useLibraryGames / useLibraryFlaws                           ('inaccuracy'|'mistake'|'blunder'|'facepalm')
                     | ?severity=facepalm&severity=mistake                 /        |         \          \
                     v                                          severityCountsBySide  categoryPlies   EvalChart dot colour
          routers/library.py (SeverityFilter Literal, 422 on unknown)   (MoveStats rows,   (cycle +      + tooltip glyph
                     |                                                    compact row)     highlight)
         library_service (get_library_games / get_library_flaws, default = all three)
                     |                                            filter ring: flawFilter.severity -> MoveStatsCellRef[] (user side)
      query_utils.apply_game_filters ---- query_flaws
                     |                         |
           flaw_exists_from_table              |
                     \_______ build_flaw_filter_clauses _______/
                                    |
                         _severity_clause(selected, score)
                    mistake: severity=1
                    blunder: severity=2 AND coalesce(score, 0) < FACEPALM_STATS_MIN
                    facepalm: severity=2 AND score >= FACEPALM_STATS_MIN
                    blunder+facepalm: severity=2
                                    |
                    score = facepalm_expr(FACEPALM_LIBRARY_LAMBDA) (query-time, game_flaws facts)
                                    |
                         game_flaws (player_only_gate, user_id scope)
```

### Recommended file touch list
```
app/repositories/library_repository.py   # FlawSeverityFilter Literal + values tuple, _severity_clause, builder signature (D-12); range removal (D-13)
app/repositories/query_utils.py          # cast target type (D-12); range removal (D-13)
app/services/library_service.py          # get_library_flaws type + _DEFAULT_SEVERITY (D-12); range removal (D-13)
app/routers/library.py                   # SeverityFilter = FlawSeverityFilter (D-12); range params (D-13)
frontend/src/types/library.ts            # FlawSeverityFilter = 'facepalm' | 'blunder' | 'mistake' (+ ordered const array)
frontend/src/lib/moveStatsCounts.ts      # MoveStatCategory += 'facepalm', flawMoveCategory(), counts
frontend/src/components/library/MoveStats.tsx        # 8 rows, compact list, popover, CategoryIcon, outlinedRefs, MOVE_STATS_CATEGORY_COUNT
frontend/src/components/results/LibraryGameCard.tsx  # categoryPlies via classifier, outlinedRefs, DESKTOP_BOARD_SIZE derivation
frontend/src/components/analysis/AnalysisTagsPanel.tsx # categoryPlies via classifier
frontend/src/components/library/EvalChart.tsx         # dot colour + tooltip from classifier
frontend/src/lib/flawDotColor.ts (new, or inside moveStatsCounts.ts) # pure colour function, unit-tested
frontend/src/components/filters/FlawFilterControl.tsx # 3 tags, singular labels, remove FacepalmFilter block
frontend/src/components/filters/FacepalmFilter.tsx    # delete
frontend/src/hooks/useFlawFilterStore.ts, hooks/useLibrary.ts, api/client.ts, lib/analytics.ts, lib/facepalm.ts, pages/library/{GamesTab,FlawsTab}.tsx
frontend/src/components/library/SeverityBadge.tsx    # ring alignment (if confirmed)
frontend/src/lib/theme.ts                             # SEV_FACEPALM_BG (if confirmed)
```

### Pattern 1: One frontend classifier for the split
**What:** A single pure function every display surface reads, so the table, the cycle lists, the chart dots and the tooltip can never disagree.
**When to use:** Every place that today switches on `marker.severity` for the move-quality concept (not the Library Stats or timeline, which keep the Lichess meaning per D-07).
```ts
// frontend/src/lib/moveStatsCounts.ts
import { isFacepalmBlunder } from '@/lib/facepalm';

/** A flaw's Move Stats category: its severity, except a facepalm blunder (D-02, D-03). */
export type FlawMoveCategory = FlawSeverity | 'facepalm';

export function flawMoveCategory(marker: Pick<FlawMarker, 'severity' | 'facepalm_score'>): FlawMoveCategory {
  return marker.severity === 'blunder' && isFacepalmBlunder(marker.facepalm_score) ? 'facepalm' : marker.severity;
}

export type MoveStatCategory = 'gem' | 'great' | 'best' | 'good' | FlawMoveCategory;
```
`severityCountsBySide` becomes `Record<MoveStatSide, Record<FlawMoveCategory, number>>` with `out[side][flawMoveCategory(m)]++`. Both `categoryPlies` maps call `push(flawMoveCategory(fm), ...)`. `LibraryGameCard.facepalmPlies` (303-311) can be rewritten onto the same function. [Pattern derived from the existing code; no external source]

### Pattern 2: One backend clause for the split
**What:** Replace the severity block in `build_flaw_filter_clauses` with a helper that maps the selected set to OR branches.
```python
# app/repositories/library_repository.py
# Flaws-filter severity values (D-08, D-12). Its own Literal: the stored severity and
# FlawSeverity stay inaccuracy/mistake/blunder. Mirrored by FlawSeverityFilter in
# frontend/src/types/library.ts. Imported by query_utils, library_service and the router.
FlawSeverityFilter = Literal["facepalm", "blunder", "mistake"]


def _severity_clause(
    severity: Sequence[FlawSeverityFilter],
    score: ColumnElement[float] | None,
) -> ColumnElement[bool] | None:
    """OR of the selected Flaws tags on one game_flaws row (D-08).

    Blunder means a blunder that is not a facepalm: below FACEPALM_STATS_MIN or unscored
    (D-09). Blunder + Facepalm is every blunder, so it needs no score.
    """
    selected = set(severity)
    if not selected:
        return None
    is_blunder = GameFlaw.severity == _SEVERITY_INT["blunder"]
    branches: list[ColumnElement[bool]] = []
    if "mistake" in selected:
        branches.append(GameFlaw.severity == _SEVERITY_INT["mistake"])
    if {"blunder", "facepalm"} <= selected:
        branches.append(is_blunder)
    elif selected & {"blunder", "facepalm"}:
        expr = score if score is not None else facepalm_expr(FACEPALM_LIBRARY_LAMBDA)
        if "facepalm" in selected:
            branches.append(and_(is_blunder, expr >= FACEPALM_STATS_MIN))
        else:
            # coalesce renders the score expression once; an unscored blunder is a Blunder.
            branches.append(and_(is_blunder, func.coalesce(expr, 0.0) < FACEPALM_STATS_MIN))
    return or_(*branches)
```
Keep the existing "non-empty selection emits a clause" behaviour: all three selected compiles to `severity = 1 OR severity = 2`, which matches every `game_flaws` row and keeps today's EXISTS semantics (a game must have at least one user flaw). Returning `None` for the full set would silently change the Games tab to "all games, flawless ones included" for API callers that send all values. The frontend never sends the full set to `/games` (gated by `isFlawFilterNonDefault`). `query_flaws` passes its bound `facepalm_chip` as `score` so the WHERE and the chip read one object (the existing D-01 pattern). [Pattern derived from the existing code]

### Pattern 3: Multi-cell ring
```ts
// LibraryGameCard.tsx
const outlinedCellRefs: readonly MoveStatsCellRef[] = useMemo(() => {
  const sel = flawFilter.severity;
  if (userColor == null || !isSeverityNarrowed(sel)) return [];
  return sel.map((category) => ({ kind: 'category', category, side: userColor }));
}, [flawFilter.severity, userColor]);
```
with `isSeverityNarrowed(sel) = sel.length > 0 && sel.length < FLAW_SEVERITY_FILTER_VALUES.length` exported from one place and reused by `isFlawFilterNonDefault`, the FlawsTab URL writer and `SeverityBadge`. MoveStats prop becomes `outlinedRefs?: readonly MoveStatsCellRef[]` checked with `outlinedRefs.some((r) => sameCellRef(r, ref))`. Recommend also applying the ring to the compact row cells (today they show none), since on mobile the full table is collapsed by default and the ring would otherwise be invisible (frontend CLAUDE.md "apply changes to mobile too"; Open Question 6).

### Anti-Patterns to Avoid
- **Adding `'facepalm'` to `FlawSeverity` or `MoveQuality`:** both are shared contracts with other meanings (backend severity, live engine grading). D-12 and the moveStatsCounts header forbid it.
- **Writing `score IS NULL OR score < cut`:** renders the ~34 KB score expression twice per clause (`fetch_facepalm_counts` comment: "re-evaluates the ~34 KB score expression"). Use `coalesce`.
- **Treating two selected tags as "all":** the old `length === 1` / `length < 2` shortcuts are wrong once there are three tags (Pitfall 2).
- **Stating the cut as a literal** in tests, copy or code (D-21). Tests use `FACEPALM_STATS_MIN ± SEED_FACEPALM_MARGIN` (backend) and `FACEPALM_HIGH_CUTOFF` (frontend).
- **Rewriting `FACEPALM_HIGH_CUTOFF`'s line or comment** in the pre-merge plans (259-12 owns it).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Is this blunder a facepalm" in the frontend | a new threshold compare | `isFacepalmBlunder(score)` | Floors the same way as the chip; the cut moves with 259-12 |
| Facepalm score in SQL | a Python score or a stored column | `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` | Single query-time expression; Phase 259 swaps its internals |
| The cut in SQL | `0.7` | `FACEPALM_STATS_MIN` | Same cut as the stats counts and timeline band |
| "???" icon | new SVG | `FacepalmBlunderIcon` / `FACEPALM_GLYPH` | 257 D-22 glyph spec |
| Dark red | new colour | `SEV_FACEPALM` | D-17 |
| Test score seeding | hand-built fact columns | `tests/facepalm_seed.py` (`facepalm_fact_columns`, `SEED_FACEPALM_MARGIN = 1e-4`) and `_seed_non_tactic_flaw(..., facepalm_target=...)` / `_seed_facepalm_band_game` in `tests/repositories/test_library_repository.py` | Seeds facts that score to a target through the real expression |
| Ring styling | new class | `ACTIVE_FILTER_RING_CLASS` | Shared across chips and cells |

**Key insight:** every piece already exists; the risk is only in wiring two consistent splits (SQL and TS) and in the "two selected = all" shortcuts.

## Runtime State Inventory

The phase removes an API parameter and a UI filter; no data is renamed.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None. No column, enum or stored value changes; `game_flaws.severity` stays 1/2 (verified `_SEVERITY_INT`) | none |
| Live service config | None. No external service holds the filter | none |
| OS-registered state | None | none |
| Secrets/env vars | None | none |
| Build artifacts / client state | Stale PWA bundles may still send `min_facepalm_pct` / `max_facepalm_pct` after D-13 deploys; FastAPI ignores unknown query params [ASSUMED], so they get unfiltered results. Bookmarked Flaws-tab URLs with `?severity=blunder` keep loading but now mean "blunders that are not facepalms" | none in code; mention in CHANGELOG |

The flaw-filter store is in-memory (no localStorage) and the URL never carried the range, so there is no persisted `facepalmMin`/`facepalmMax` to migrate. [VERIFIED: useFlawFilterStore.ts:106, FlawsTab.tsx:93-121]

## Common Pitfalls

### Pitfall 1: Opponent facepalm cells are always zero
**What goes wrong:** The Facepalm row's opponent column reads 0 for every game, and opponent "???" blunders stay red "??" squares on the chart.
**Why:** `fetch_page_facepalm_scores` returns owner-side plies only.
**How to avoid:** Get the owner's call (Open Question 1) before planning; if opponent scores are wanted, drop the gate in that one function and audit the surfaces that start showing opponent "???" (analysis move list `VariationTree`, board corner markers, Explain bar, eval tooltip `FacepalmTooltipLine`, hover miniboard). `FacepalmExplanation` already has a `byOpponent` wording.
**Warning signs:** a test fixture that only scores even plies passes while the opponent cell never lights in the browser.

### Pitfall 2: "Both selected = all" shortcuts
**What goes wrong:** With three tags, `["blunder", "mistake"]` is a real narrowing (excludes facepalms), but the old code treats it as "no filter".
**Where:** `useFlawFilterStore.isFlawFilterNonDefault` (`length === 1`), `FlawsTab` URL writer (`length < 2`), `LibraryGameCard.outlinedCellRef` (`length !== 1`), `SeverityBadge.isActive` (`length === 1`), `library_service._DEFAULT_SEVERITY = ["mistake", "blunder"]` (would drop facepalms from the default Flaws list), and the test "rings no cell when the severity filter is at its default (both blunder+mistake)" (`LibraryGameCard.test.tsx:499`, plus the mocked store default `severity: ['blunder', 'mistake']` at lines 34 and 44).
**How to avoid:** one `isSeverityNarrowed` helper and one ordered values constant per stack; `_DEFAULT_SEVERITY` becomes all three values.
**Warning signs:** Flaws tab default list shrinks after D-12; the Games-tab filter dot does not light for Blunder + Mistake.

### Pitfall 3: `_SEVERITY_INT["facepalm"]` KeyError
**What goes wrong:** Any path that still does `_SEVERITY_INT[s] for s in severity` raises on the new value (500).
**How to avoid:** the new helper is the only consumer of the filter values; grep `_SEVERITY_INT\[s\]` after the change.

### Pitfall 4: Bound score expression size and JIT
**What goes wrong:** The score expression is large (the code calls it ~34 KB); repeating it in OR branches bloats every Games/Flaws query, and Phase 259 plan 12 is measuring JIT on these readers.
**How to avoid:** render it once per branch (coalesce), pass `query_flaws`'s bound `facepalm_chip`, and only reference the score when exactly one of Blunder/Facepalm is selected. The range filter today puts the same expression in the same WHERE, so there is no regression relative to shipped behaviour. [VERIFIED: _facepalm_clause and query_flaws read this session]

### Pitfall 5: Dark red text legibility
**What goes wrong:** `SEV_FACEPALM` is `oklch(0.42 ...)`, much darker than `SEV_BLUNDER` (0.58). As text colour (selected pill label, tooltip label) on the near-black card background it may read poorly.
**How to avoid:** check it in the browser UAT; if it fails, keep the dark red for the dot/icon and use `SEV_BLUNDER` or `foreground` for the label text. Do not invent a lighter tone without the owner (D-17 "no new theme constant").

### Pitfall 6: `MoveQualityIcon` type error
**What goes wrong:** `tsc -b` fails on the three `MoveQualityIcon quality={category}` calls once `MoveStatCategory` gains `'facepalm'`. `npm run lint` and `npm test` do not type-check, so this only shows in `npm run build`.
**How to avoid:** a local `CategoryIcon` in MoveStats; run `npm run build` in each frontend plan.

### Pitfall 7: Leaking the split into Lichess-meaning surfaces
**What goes wrong:** Reusing `flawMoveCategory` in `SeverityBadge` counts, FlawTiles, the timeline or `game.severity_counts` would change their numbers (D-07).
**How to avoid:** apply the classifier only in moveStatsCounts consumers, EvalChart and the filter.

### Pitfall 8: Merge conflict in `lib/facepalm.ts`
**What goes wrong:** Deleting lines 29-33 and rewriting the stale comment on 35-39 conflicts with 259-12's edit of line 40 and its comment.
**How to avoid:** leave lines 34-40 untouched before 259 merges; fix the comment in the post-merge plan.

### Pitfall 9: Height derived wrong by a pixel or two
**What goes wrong:** inline-button baseline slack makes a row 25px, so 8 rows need 255px and the card overhangs a 248px board.
**How to avoid:** measure in the browser at `lg` and adjust `MOVE_STATS_ROW_PX` (or the rounding) to the measured value.

## Code Examples

### Facepalm row copy (D-06), reading the cut rather than stating it
```tsx
// MoveStats.tsx — CATEGORY_DEFINITIONS gains (wording family of FACEPALM_DEFINITION in lib/facepalm.ts):
facepalm: "A blunder that should have been easy to see for a player at the mover's level.",
// and the Lichess paragraph:
// "Accuracy, inaccuracies, mistakes and blunders use the same formulas as Lichess, so they match
//  Lichess's game analysis. Blunders and facepalms together make up Lichess's blunder count."
```
If the number is shown, interpolate `FACEPALM_HIGH_CUTOFF` (e.g. "a facepalm score of `${FACEPALM_HIGH_CUTOFF}`% or more"), never a literal.

### Dot colour, testable
```ts
// frontend/src/lib/flawDotColor.ts (new)
import { flawMoveCategory } from '@/lib/moveStatsCounts';
import { SEV_BLUNDER, SEV_FACEPALM, SEV_INACCURACY, SEV_MISTAKE } from '@/lib/theme';
import type { FlawMarker } from '@/types/library';

const DOT_COLOR = { facepalm: SEV_FACEPALM, blunder: SEV_BLUNDER, mistake: SEV_MISTAKE, inaccuracy: SEV_INACCURACY } as const;

/** Eval-chart flaw dot and tooltip colour: dark red for a facepalm blunder (D-17), else the severity. */
export function flawDotColor(marker: Pick<FlawMarker, 'severity' | 'facepalm_score'>): string {
  return DOT_COLOR[flawMoveCategory(marker)];
}
```
`buildDotRenderer` line 444 and the tooltip lines 1209/1213 call it instead of `severityColor(marker.severity)`.

### Backend D-08 test shape (no literal cut)
```python
from app.services.blunder_check_rules import FACEPALM_STATS_MIN
from tests.facepalm_seed import SEED_FACEPALM_MARGIN

ABOVE = FACEPALM_STATS_MIN + SEED_FACEPALM_MARGIN
BELOW = FACEPALM_STATS_MIN - SEED_FACEPALM_MARGIN

@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (["facepalm"], {"above"}),
        (["blunder"], {"below", "unscored"}),
        (["blunder", "facepalm"], {"above", "below", "unscored"}),
        (["mistake", "facepalm"], {"mistake", "above"}),
        ([], {"mistake", "above", "below", "unscored"}),
        (["facepalm", "blunder", "mistake"], {"mistake", "above", "below", "unscored"}),
        (["blunder", "mistake"], {"mistake", "below", "unscored"}),
    ],
)
async def test_severity_tags_follow_d08(...): ...  # seed one user game: blunder ABOVE, blunder BELOW,
#   unscored blunder, mistake, plus an opponent blunder ABOVE that must never match.
```
Run it through both `query_flaws` (Flaws tab) and `query_filtered_games` (Games tab EXISTS), one game per row kind for the Games variant.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Facepalm Score range slider with Low/Mid/High presets (Phase 253) | Facepalm as a severity tag (this phase) | this phase | Removes ~15 signature params and the slider |
| Blunder dots all `SEV_BLUNDER` (257 D-22 exclusion) | Facepalm dots `SEV_FACEPALM` | this phase | Reverses 257 D-22's "not changed" list for dots and counts |

**Deprecated/outdated:** `FacepalmFilter.tsx`, `facepalmToQueryParams`, `_facepalm_clause`, `facepalm_range_active`, `FACEPALM_PCT_MIN/MAX` (backend), `min_facepalm_pct`/`max_facepalm_pct`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI ignores unknown query params, so stale clients sending `min_facepalm_pct` after D-13 get 200, not 422 | Backend map, Runtime State | Stale PWA users see errors on the Games/Flaws tab until reload; confirm with a one-line router test in D-13 |
| A2 | Each MoveStats row is exactly 24px at `lg` (no inline-button baseline slack) | Desktop height | Board off by a few px; measure in the browser |
| A3 | `SEV_FACEPALM` text is legible enough on the dark card for the pill label and tooltip | Pitfall 5 | Unreadable label; fall back to `SEV_BLUNDER` text |
| A4 | Postgres evaluates `severity = 2 AND <score cmp>` without measurable regression versus today's range filter | Pitfall 4 | Slower Games/Flaws queries; check with EXPLAIN on dev for one heavy user if in doubt |

## Open Questions (RESOLVED)

All eight are resolved: Q1, Q2, Q3 and Q5 by owner decisions D-24 to D-27 in 260-CONTEXT.md (2026-11-22), Q4, Q6, Q7 and Q8 by the recommendation adopted in the plans. Each question carries its resolution line.

1. **Do opponent blunders get a facepalm score on the game card and analysis payload?** (blocks the frontend table/chart plan)
   - What we know: scores exist in SQL for opponents (SEED-261114-iuv Part A on prod, used by `fetch_facepalm_comparison`); `fetch_page_facepalm_scores` gates them out on purpose ("an open product decision"); D-01 and the discussion log assume both sides.
   - What's unclear: whether the owner wants opponent "???" across all display surfaces (move list, board, tooltip, Explain bar), which a one-line gate removal would cause.
   - Recommendation: ask the owner. If yes, add a small backend task (drop the gate in `fetch_page_facepalm_scores`, keep the filter user-only per 257 D-06) and a browser check of the opponent surfaces. If no, the opponent Facepalm cell should read "—" or be explained, since a constant 0 misleads.
   - **RESOLVED (D-24):** yes. The owner-only gate is dropped (260-01 Task 3); the Flaws filter and drill selection stay user-only; the opponent surfaces are in the final UAT (260-07 Task 3).
2. **Should the desktop eval chart grow with the board?** The chart is fixed at `h-[104px]`, not board-sized; with a 248px board the tags card absorbs ~23px. Recommendation: keep the chart at 104px (no change needed) unless the owner reads D-16 as "chart grows"; confirm at UAT.
   - **RESOLVED (D-25):** the chart grows with the board and the tags card keeps its height (260-02 Task 3, `lib/gameCardGeometry.ts`).
3. **D-18 tooltip:** the tooltip shows a dot-shaped `MarkerGlyph` and the word "Blunder", not "??". Recommendation: for a facepalm blunder render `FacepalmBlunderIcon` (h-3 w-3) in place of the `MarkerGlyph` and label the line "Facepalm", in `SEV_FACEPALM` (subject to Pitfall 5); confirm wording with the owner since D-07 keeps "Blunder" elsewhere.
   - **RESOLVED (D-26):** the "???" icon replaces the dot glyph in `SEV_FACEPALM` and the line reads "You · Facepalm" / "Opponent · Facepalm" (260-04 Task 2).
4. **`SEV_FACEPALM_BG` for the Facepalm pill:** needed for the selected pill background; it is a new theme constant in the `SEV_*_BG` convention. Recommendation: add it; mention it at the checkpoint.
   - **RESOLVED (adopted, CONTEXT discretion):** `SEV_FACEPALM_BG` is added at 14% alpha (260-05 Task 1).
5. **`SeverityBadge` ring on the Flaws card:** not in CONTEXT, but its `length === 1` rule is broken by the three-tag set. Recommendation: align it with D-20 in the filter plan (ring when the badge's own tag, `facepalm` for a "???" badge, is in a narrowing selection).
   - **RESOLVED (D-27):** the badge rings when its own tag is part of a narrowing selection (260-06 Task 2).
6. **Ring on the mobile compact row:** today the compact cells show no ring and the full table is collapsed by default. Recommendation: add the ring to compact cells (user-side only already).
   - **RESOLVED (adopted, CONTEXT discretion):** the compact row carries the ring (260-06 Task 1).
7. **Explanation line under the Flaws tags** ("Blunder excludes facepalms"): Claude's discretion. Recommendation: no extra line in the panel (popover-copy minimalism); put it in the Flaws section's info popover if one exists, else in the MoveStatsInfo sentence only.
   - **RESOLVED (adopted, CONTEXT discretion):** no extra line in the panel; MoveStatsInfo carries the split and the Lichess sum sentence (260-02 Tasks 1-2).
8. **CHANGELOG:** the range filter is already deployed (verified: `origin/production:app/routers/library.py` contains `min_facepalm_pct` 4 times and `FacepalmFilter.tsx` exists there) but its bullets still sit under `## [Unreleased]` (CHANGELOG.md lines 22, 39, 40), and 259-12 adds a bullet mentioning "the Facepalm filter". Recommendation: add new Changed/Removed bullets rather than rewriting shipped ones; reconcile 259's wording at merge.
   - **RESOLVED (adopted, CONTEXT discretion):** new Changed / Removed bullets, shipped range-filter bullets untouched, Phase 259's wording reconciled (260-07 Task 3).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | frontend build/test | ✓ | v24.19.0 | — |
| frontend/node_modules in the worktree | vitest, eslint, knip, tsc | ✓ | — | `npm ci` |
| uv + `.venv` in the worktree | pytest, ty, ruff | ✓ | uv 0.10.9 | `uv sync` (memory: add `--group maia-inference` in a fresh worktree) |
| Dev PostgreSQL (docker `flawchess-dev-db-1`) | backend DB tests | ✓ (running) | 18 | — |
| Browser automation (claude-in-chrome) | D-15 height measurement, visual UAT | not probed | — | human UAT |

Probes run this session: `npx vitest run moveStatsCounts.test.ts MoveStats.test.tsx` (15 passed), `uv run pytest tests/test_query_utils.py -k Facepalm` (4 passed). Graph context (Step 1.3) and the external research seam were skipped: the phase is internal and needed no external sources.

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-xdist, per-worker cloned Postgres DB) backend; vitest 5.1 + Testing Library frontend |
| Config file | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.*` (vitest) |
| Quick run command | `uv run pytest tests/test_flaw_predicate.py tests/repositories/test_library_repository.py -x` and `cd frontend && npx vitest run src/lib/__tests__/moveStatsCounts.test.ts src/components/library/__tests__/MoveStats.test.tsx` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-08/D-12 | `_severity_clause` compiles each selected set (no score ref for Blunder+Facepalm, single score ref otherwise, no `_SEVERITY_INT` KeyError) | unit (SQL compile) | `uv run pytest tests/test_flaw_predicate.py -k severity -x` | ✅ extend |
| D-08/D-09 | Truth table on `query_flaws` with seeded ABOVE/BELOW/unscored/mistake/opponent rows | integration (DB) | `uv run pytest tests/repositories/test_library_repository.py -k severity_tags -x` | ❌ new test |
| D-08 | Same table on the Games EXISTS (`query_filtered_games`) | integration (DB) | `uv run pytest tests/test_library_repository.py -k severity_tags -x` | ❌ new test |
| D-12 | Router accepts `severity=facepalm`, 422 on `severity=inaccuracy` / unknown | integration (HTTP) | `uv run pytest tests/test_library_router.py -k severity -x` | ✅ extend |
| D-12 | `get_library_flaws` default = all three (facepalms listed with no severity param) | integration | `uv run pytest tests/services/test_library_service.py -k default_severity -x` | ❌ new test |
| D-01..D-04 | `flawMoveCategory`, `severityCountsBySide` split (unscored blunder stays Blunder; cut read from `FACEPALM_HIGH_CUTOFF`) | unit | `npx vitest run src/lib/__tests__/moveStatsCounts.test.ts` | ✅ extend |
| D-01, D-06 | 8 rows render (update "exactly 7"), Facepalm row icon, popover lists 8 definitions + Lichess sum sentence | component | `npx vitest run src/components/library/__tests__/MoveStats.test.tsx` | ✅ update |
| D-05 | Compact row has 6 category cells + chevron, no inaccuracy/good | component | same file + `LibraryGameCard.test.tsx -t "mobile MoveStats"` | ✅ update |
| D-04/D-19 | Blunder cell cycles only "??" plies, Facepalm cell only "???" plies (LibraryGameCard and AnalysisTagsPanel) | component | `npx vitest run src/components/results/__tests__/LibraryGameCard.test.tsx src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx` | ✅ extend |
| D-17 | `flawDotColor` returns `SEV_FACEPALM` for facepalm, `SEV_BLUNDER` otherwise | unit | `npx vitest run src/lib/__tests__/flawDotColor.test.ts` | ❌ new |
| D-18 | Tooltip of a facepalm blunder shows the "???" icon | component | `npx vitest run src/components/library/__tests__/EvalChart.test.tsx` | ✅ extend (tooltip render may need the exported-piece approach) |
| D-20 | Ring per selected tag, none for empty/all three, user side only | component | `LibraryGameCard.test.tsx -t "filter ring"` (rewrite the "both = no ring" case) | ✅ update |
| D-08 (UI) | Three pills in order Facepalm, Blunder, Mistake, singular labels, OR toggle, `severity` event with `facepalm` value | component | `npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` | ✅ update |
| D-08 (store) | `isFlawFilterNonDefault` true for 1 or 2 tags, false for 0 or 3 | unit | `npx vitest run src/hooks/__tests__/useFlawFilterStore.test.ts` | ✅ update |
| D-08 (URL) | FlawsTab writes severity unless all three; drops unknown URL values | component | `npx vitest run src/pages/library/__tests__/FlawsTab.test.tsx` | ✅ extend |
| D-14 | No facepalm params in requests/query keys; knip clean | unit + gate | `npx vitest run src/hooks/__tests__/useLibraryGames.test.tsx src/api/__tests__/client.test.ts && npm run knip` | ✅ update (delete range cases) |
| D-13 | Range params gone; unknown param ignored (A1) | integration | `uv run pytest tests/test_library_router.py -k "facepalm" -x` | ✅ rewrite |
| D-15/D-16 | Board and MoveStats card end level at `lg` | manual/browser | browser `getBoundingClientRect` check | — (browser UAT) |

### Sampling Rate
- **Per task commit:** the quick command for the files touched (one backend file or one vitest file group).
- **Per wave merge:** `uv run pytest -n auto -x` plus `npm run build && npm test -- --run && npm run knip`.
- **Phase gate:** full pre-merge gate from CLAUDE.md (ruff format, ruff check --fix, ty, analysis ty, `check_function_size.py app/ --fail-over-depth 4`, `pytest -n auto -x`, frontend lint/build/test/knip), plus one serial `uv run pytest -x` before the release (memory: serial CI hides isolation bugs).

### Wave 0 Gaps
- [ ] `tests/repositories/test_library_repository.py` — D-08 truth-table test on `query_flaws` (reuse `_seed_non_tactic_flaw(facepalm_target=...)`)
- [ ] `tests/test_library_repository.py` — D-08 table on the Games EXISTS
- [ ] `frontend/src/lib/__tests__/flawDotColor.test.ts` — new pure function
- [ ] No framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged (`current_active_user`) |
| V3 Session Management | no | — |
| V4 Access Control | yes | user_id from the authenticated user only; `GameFlaw.user_id == user_id` and `player_only_gate` stay on both callers (IDOR) |
| V5 Input Validation | yes | `list[FlawSeverityFilter]` Literal at the FastAPI boundary (422 on anything else); frontend validates URL `severity` values against the known set |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection through filter values | Tampering | values never interpolated; mapped to `_SEVERITY_INT` ints and bound params; the cut is a bound float constant |
| 500 on unexpected value (`KeyError`) | Denial of service | Literal validation at the router; only `_severity_clause` maps the values |
| Cross-user leakage via opponent scores | Information disclosure | if Open Question 1 is "yes", scores stay scoped to the owner's own games (`GameFlaw.user_id == user_id`); the filter stays user-side only |

## Sources

### Primary (HIGH confidence, read in the worktree this session)
- `app/repositories/library_repository.py` (lines 1-120, 280-420, 630-850, 1140-1300, 1403-1450, 1691-1760, 1820-1900)
- `app/repositories/query_utils.py` (180-215, 380-445), `app/routers/library.py` (1-470), `app/services/library_service.py` (360-430, 850-870, 955-1100, 1420-1510), `app/services/blunder_check_rules.py` (50-80), `app/repositories/game_flaws_repository.py` (30-36), `app/services/flaws_service.py:108`, `app/services/facepalm_score.py:624-636`
- `tests/services/test_facepalm_score.py` (30-45, 1190-1260), `tests/test_flaw_predicate.py` (1-40, 200-245), `tests/repositories/test_library_repository.py` (820-900), `tests/facepalm_seed.py` (1-60)
- Frontend: `lib/moveStatsCounts.ts`, `components/library/MoveStats.tsx`, `components/icons/MoveQualityIcon.tsx`, `components/icons/SeverityGlyphIcon.tsx`, `lib/severityGlyph.ts`, `lib/theme.ts` (20-30, 66-78, 289, 515-528), `components/results/LibraryGameCard.tsx` (60-180, 280-320, 370-640, 1040-1294), `components/analysis/AnalysisTagsPanel.tsx` (30-70, 165-200), `components/library/EvalChart.tsx` (280-460, 530-580, 1190-1240), `components/filters/FlawFilterControl.tsx` (1-180, 235-255, 480-640), `hooks/useFlawFilterStore.ts`, `hooks/useLibrary.ts` (60-200, 370-420), `api/client.ts` (grep), `lib/analytics.ts` (455-525), `lib/facepalm.ts`, `pages/library/FlawsTab.tsx` (85-135), `components/library/SeverityBadge.tsx` (110-160), `components/filters/LibraryFilterPanel.tsx` (60-110), `types/library.ts` (166-195), `index.css` (221-230, 701-713), `knip.json`
- `.planning/phases/259-facepalm-first-principles-refit/259-12/13/14-PLAN.md`, `.planning/phases/257-facepalm-rate-library-stats/257-CONTEXT.md`, `260-CONTEXT.md`, `260-DISCUSSION-LOG.md`, the seed, `ROADMAP.md` §260, `STATE.md`

### Secondary / Tertiary
- none (no web sources used)

## Metadata

**Confidence breakdown:**
- Code map and removal inventory: HIGH — every symbol and line range read this session.
- Backend clause design: HIGH — follows the existing builder and stats comparison; performance claim MEDIUM (A4).
- Desktop height: MEDIUM — arithmetic from classes, needs a browser measurement (A2).
- Opponent-score gap: HIGH that it exists; the product answer is open.

**Research date:** 2026-11-22
**Valid until:** until Phase 259 plans 12-14 merge (line numbers in `library_repository.py`, `library_service.py` and `test_facepalm_score.py` shift then); re-grep symbols, not line numbers, in D-13.
