# Phase 253: Facepalm Score in the Library UI - Research

**Researched:** 2026-11-14
**Domain:** Library flaw filter (FastAPI + SQLAlchemy shared predicate) and React filter panel / Flaws-card badge
**Confidence:** HIGH (everything is grounded in the repo; no new packages, no web sources needed)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (seed and roadmap, owner 2026-11-14; not re-discussed)
- **D-01: Name and casing.** "Facepalm", capitalized, as the filter label and in popover copy. UI, code and docs
  all say facepalm. (Revised 2026-11-14: the card no longer shows the word, see D-14.)
- **D-02: Icon.** lucide `TreePalm`. (Revised 2026-11-14, owner: on the Flaws card the icon stands without the
  word, inside the Blunder badge, see D-14. The popover names it.)
- **D-03: Not a probability** (250 D-01). The score is a ranking; no copy presents it as a share of peers or a
  chance. Banned wording: "avoidable", "chance you'd see it".
- **D-04: Filter semantics.** Full range 0-100% = no filter (no clause added). A narrowed range keeps only flaws
  with a non-NULL `facepalm_score` in range, so mistakes, inaccuracies and blunders without a score drop out.
- **D-05: User flaws only.** Tag filters already pass through `player_only_gate`; no opponent scoring needed.
- **D-06: Games tab.** The range joins the single flaw `EXISTS`, so it combines with severity, tags and tactic
  filters on the same flaw row.
- **D-07: Provisional values.** Until 250-10 runs, scores come from unrepaired lines and pre-refit constants. The
  owner accepts this; no "provisional" note in the UI and no code change is needed after 250-10.

#### Filter control shape
- **D-08: Presets plus slider.** A third wrapper over the shared `PresetRangeFilter`, same look as Tactic Depth:
  label with info popover, active summary, preset chips, two-handle slider.
- **D-09: Four presets, fixed cutoffs at 30% and 70%.** All = 0-100 (no filter), Low = 0-29, Mid = 30-69,
  High = 70-100. The cutoffs are plain UI constants, independent of `FACEPALM_SCORE_MIN`; they do not move when
  the drill cut is refitted. (The owner considered thirds at 33/66 and settled on 30/70.) All is the default.
- **D-10: Slider step 5%.** The upper handle covers its whole 5% bucket, so the bounds are half-open on the top
  side: Low puts the handles at 0 and 25 and matches score < 30; Mid at 30 and 65, matching 30 <= score < 70;
  High at 70 and 100. A handle at 100 includes 100%. Chip labels and the summary still read 0-29, 30-69, 70-100.
  How the half-open rule is split between frontend and API params is the planner's call, but a score of 27% must
  land in Low and 69.9% in Mid.

#### Narrowed-range behavior
- **D-11: Severity toggles are left alone.** No dimming, no coupled state. With Mistakes selected and a narrowed
  range, mistakes simply return nothing.
- **D-12: Hint while narrowed.** A one-line note under the slider, shown only when the range is not All:
  **"Mistakes are excluded"**. Do not mention unscored blunders: basically all blunders are scored once Phase 252
  and 250-10 finish (owner).
- **D-13: Panel position.** Directly under the Flaws section (Blunders / Mistakes toggles), above Best Moves and
  Tactic Depth, on both tabs.

#### Score on the Flaws-tab card (revised 2026-11-14 during planning, owner; replaces the separate chip)
- **D-14: Inside the Blunder badge, no new chip.** The Flaws-card severity badge reads
  `Blunder <TreePalm> 94%` when the flaw has a score: the word, then the icon, then the whole percent.
- **D-15: Badge styling unchanged.** The score inherits the Blunder badge colors (`SEV_BLUNDER*`). No neutral
  pill, no grading by band.
- **D-16: The Blunder badge is the popover trigger** when it carries a score: opens on hover (desktop pointer)
  and on click or tap (owner, 2026-11-14). Keyboard focus should open it too. No Facepalm entry in the shared
  Tags legend.
- **D-17: Only when `facepalm_score` is non-NULL.** Without a score the badge is exactly today's plain,
  non-interactive `Blunder` span, with no popover. Mistake and Inaccuracy badges never change. The Games-card
  count badges (`3 Blunders`) are untouched.

#### Popover copy (owner-approved wording)
- **D-18: Blunder badge popover.** A heading line `Facepalm 94%` (the word names the icon, owner 2026-11-14),
  then:
  > How obvious this blunder was for a player at your level, as judged by our model. High means a careless slip,
  > low means it was hard to see. Not a probability.
- **D-19: Filter info popover.**
  > How obvious a blunder was for a player at your level, as judged by our model. High means a careless slip, low
  > means it was hard to see. Not a probability.
  >
  > Low keeps 0 to 29%, Mid 30 to 69%, High 70 to 100%. Drag either handle for a custom range. Any range other
  > than All shows blunders only.

  No mention of the blunder-check drill or its cut.

### Claude's Discretion
- **Percent rounding:** whole percent, rounded down, so a chip value always agrees with the filter band (a score
  of 0.697 shows 69% and sits in Mid). Offered to the owner at the area check, no objection.
- Summary text format in the label row, and when it renders in the active style (follow Tactic Depth: active
  when the range is not the default).
- Filter-store fields, the active-filter dot, URL/persistence: follow the tactic depth pattern.
- Umami event target and values (preset key or `custom`, never the bounds), `data-testid` names, the icon size
  and spacing inside the badge, the badge `aria-label` (it must say "Facepalm", since the icon carries no text).
- API param names and whether the score travels as 0-1 or 0-100.

### Deferred Ideas (OUT OF SCOPE)
- Facepalm rate stats and opponent scoring — SEED-261114-iuv.
- Score in the blunder-check solution screen — dropped by the owner in the seed.
- Tying the High preset to the drill cut, and a drill mention in the filter popover — rejected for now; revisit
  only if the 250-10 refit moves `FACEPALM_SCORE_MIN` far from 70.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are mapped; the decisions D-01..D-19 are the requirement set.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-04, D-05, D-06 | Narrowed range = non-NULL score in range; single flaw EXISTS; user flaws only | Backend clause in `build_flaw_filter_clauses`, threaded through `flaw_exists_from_table` and `apply_game_filters`; activity gate pitfall (Pitfall 1) |
| D-08, D-09, D-10 | Presets + 5% slider, half-open top bucket | `lib/facepalm.ts` design + inclusive-integer-percent API contract (Pattern 2) |
| D-11, D-12, D-13 | Severity untouched; "Mistakes are excluded" hint; panel position | `FlawFilterControl` insertion point; `PresetRangeFilter` hint slot |
| D-14..D-18 | Score inside the Blunder badge, hover + tap + keyboard popover with heading | `SeverityBadge` call sites, popover primitive survey, touch double-toggle pitfall (Pattern 4, Pitfalls 4-6) |
| D-19 | Filter info popover copy | `PresetRangeFilter.infoChildren` |
| Discretion | Floor rounding, Umami, testids, persistence | Floor/threshold consistency probe on dev DB (0 disagreements), `analytics.ts` registry |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Shared filter logic lives once: all flaw-row predicates go through `build_flaw_filter_clauses` / `flaw_exists_from_table` / `apply_game_filters` (root CLAUDE.md "Shared query filters"). Never add a per-endpoint clause.
- Routers are HTTP-only (`APIRouter(prefix="/library")`, relative paths); logic in services/repositories.
- No magic numbers: `0`, `100`, `30`, `70`, `5` must be named constants (backend and frontend).
- Type safety: explicit return types; `Literal` for fixed sets (preset keys); `Sequence[...]` for list params; ty must pass with zero errors (`uv run ty check app/ tests/ scripts/`).
- Nesting depth <= 4 (`scripts/check_function_size.py app/ --fail-over-depth 4`, eslint `max-depth`). `build_flaw_filter_clauses` is flat today; keep the new clause in a helper.
- Sentry: no variables in error messages (the existing `ValueError("flaw/tactic filter requires user_id ...")` pattern).
- Frontend: colors from `theme.ts` only; `text-sm` floor in new UI (popover bodies may use `text-xs`); `data-testid` on every interactive element; `<button>` for clickable non-link elements; apply every change to desktop AND mobile copies (GamesTab and FlawsTab each render `FlawFilterControl` twice).
- Umami: every new user-facing feature ships its `trackFeature` event through the typed registry in `frontend/src/lib/analytics.ts`; sliders track in `onValueCommit` via `useDebouncedTrackFeature`; explanation popovers use `useTrackedPopoverOpen`; never interpolate non-numeric free values into a popover `testId`.
- `npm run lint` / `npm test` do not type-check: run `npm run build` (tsc -b) after the `FlawListItem` type change. Test files are excluded from `tsc -b` (`tsconfig.app.json:38` `"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx"]`).
- Knip runs in CI: every new export must be imported somewhere.
- Pre-merge gate (root CLAUDE.md) runs once before the squash-merge.
- Out-of-scope work is flagged, not implemented (GSD).

## Summary

This is a copy-the-tactic-depth-filter phase plus a small badge change. The backend already has a clean seam: one predicate builder (`build_flaw_filter_clauses`) feeds both the Flaws-tab SELECT (`query_flaws`) and the Games-tab correlated EXISTS (`flaw_exists_from_table`, called from `apply_game_filters`). The new score clause goes into that builder once; two optional int params (`min_facepalm_pct`, `max_facepalm_pct`) are threaded through router -> service -> repository exactly like `min_tactic_depth` / `max_tactic_depth`, but only on the two list endpoints (`GET /library/games`, `GET /library/flaws`). Stats, comparison and coverage endpoints never received the tactic-depth params and must not receive these either. The one non-obvious backend trap is the activity gate in `apply_game_filters`: it only builds the EXISTS when `flaw_severity or flaw_tags or tactic_active`, so a facepalm-only filter on the Games tab silently does nothing unless the gate learns about it (the same bug class the tactic depth filter already hit, see `test_depth_filter_narrows_games_without_family`).

For D-10, the cleanest split is: the frontend owns the 5% bucket semantics and sends **inclusive integer percents on the floored display scale** (Low = 0..29, Mid = 30..69, High = 70..100, custom handles `(l, h)` -> `(l, h == 100 ? 100 : h + 4)`); the backend turns `[min_pct, max_pct]` into `score >= min_pct/100 AND score < (max_pct+1)/100`, dropping the upper bound when `max_pct == 100`. That is mathematically `floor(100*score) BETWEEN min_pct AND max_pct`, which is exactly what the badge shows. I verified on the dev DB that comparing the stored REAL against double-precision thresholds agrees with `floor(score::float8 * 100)` for every multiple of 5 (0 disagreements over 4,557 scores), and that SQLAlchemy's asyncpg dialect binds a Python float compared to the REAL column as `$1::FLOAT` (double), so the agreement holds in the real query too.

On the card, `SeverityBadge` is used by exactly two call sites: `FlawCard` (Flaws tab) and `TrainPuzzleCard` (Train Archive). The Games card no longer renders `SeverityBadge` at all (its counts are the MoveStats table), so D-17's "Games-card count badges untouched" is automatic. Add an optional score prop that only FlawCard passes. For the popover, the app has three hand-rolled Radix popover triggers (`InfoPopover`, `MetricInfoPopover`, `TagChip`); `InfoPopover`/`MetricInfoPopover` already do hover (100ms) plus click/tap through one Radix `Popover` with Umami tracking, but none opens on keyboard focus, and naively adding focus-open double-toggles on touch (tap focuses then clicks). Recommendation: a small `FacepalmBadgePopover` composition modelled on `MetricInfoPopover`, with a `<button>` trigger, mouse-only hover (pointer-type guard, as `ui/tooltip.tsx` does), Radix click toggle for tap, focus-open suppressed when the focus came from a pointer, and `onOpenAutoFocus`/`onCloseAutoFocus` prevented.

**Primary recommendation:** Inclusive integer-percent API params (`min_facepalm_pct` / `max_facepalm_pct`, 0..100) added once to `build_flaw_filter_clauses` plus the `apply_game_filters` activity gate; a `lib/facepalm.ts` module cloned from `lib/tacticDepth.ts`; a `FacepalmFilter` wrapper over `PresetRangeFilter` with a new optional hint slot; `facepalm_score: float | None` on `FlawListItem`; `SeverityBadge` gains an optional score rendered through a new `FacepalmBadgePopover`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Score range predicate on `game_flaws` | API / Backend (repository) | Database | One shared predicate builder; the DB just evaluates a residual filter on already-scoped rows |
| Games-tab "game has a matching flaw" | API / Backend (`apply_game_filters` -> EXISTS) | — | Must share the single-row EXISTS with severity/tags/tactics (D-06) |
| Param validation (0..100) | API / Backend (router `Query(ge, le)`) | — | Rejects bad input at the HTTP boundary |
| 5% bucket -> inclusive percent translation | Browser / Client (`lib/facepalm.ts`) | — | Slider step is a UI concept; the API speaks display percents |
| Filter state, dot, reset | Browser / Client (`useFlawFilterStore`) | — | Module-level store, same as tactic depth; no URL/localStorage persistence exists today |
| Floored percent display | Browser / Client | — | `Math.floor(score * 100)` on the raw float the API returns |
| Badge popover (hover/tap/keyboard) | Browser / Client | — | Pure presentation |

## Standard Stack

No new dependencies. Everything needed is installed.

| Library | Version | Purpose | Evidence |
|---------|---------|---------|----------|
| lucide-react | 1.70.0 installed (`^1.21.0` in package.json) | `TreePalm` icon | [VERIFIED: frontend/node_modules/lucide-react/package.json:4 `"version": "1.70.0"`; `dist/lucide-react.d.ts` exports `TreePalm` and `TreePalmIcon`; `dist/esm/icons/tree-palm.mjs` exists] |
| radix-ui | ^1.4.3 | `Popover` primitive (`import { Popover as PopoverPrimitive } from 'radix-ui'`) | [VERIFIED: frontend/package.json:40; used in TagChip.tsx:2, info-popover.tsx:2, metric-info-popover.tsx:15] |
| SQLAlchemy | 2.0.52 | predicate building | [VERIFIED: `uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"`] |
| vitest / @testing-library/react / jsdom | ^5.0.5 / ^16.3.2 / ^30.0.1 | frontend tests | [VERIFIED: frontend/package.json:81, 57, 72] |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase, so the gate does not apply.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Tags panel (GamesTab / FlawsTab, desktop + mobile drawer)
  FlawFilterControl
    Flaws [Blunders][Mistakes]
    FacepalmFilter (PresetRangeFilter wrapper)  --onChange-->  pendingFlawFilter.{facepalmMin,facepalmMax}
    Best Moves / Tactic Depth / ...                                   | Apply
                                                                      v
                                                     useFlawFilterStore (module state)
                                                       |-- isFlawFilterNonDefault -> filter dot
                                                       v
                                useLibraryGames / useLibraryFlaws
                                  facepalmToQueryParams(min,max)  -> {} at full range
                                                                     | else {min_facepalm_pct, max_facepalm_pct}
                                                                     v (inclusive display %)
                         GET /library/games                    GET /library/flaws
                                |                                     |
                     library_service.get_library_games   library_service.get_library_flaws
                                |                                     |
                     query_filtered_games                     query_flaws
                                |                                     |
                     apply_game_filters                      build_flaw_filter_clauses  <-- one clause here
                       gate: severity|tags|tactic|FACEPALM        (+ player_only_gate, user_id)
                                |                                     |
                     flaw_exists_from_table --------------> build_flaw_filter_clauses
                       EXISTS(game_flaws row, same row ANDs all clauses)
                                                                      |
                                                     FlawListItem.facepalm_score (raw 0..1)
                                                                      v
                                                FlawCard tagsRow -> SeverityBadge(blunder, score)
                                                  score null  -> plain span (today)
                                                  score set   -> FacepalmBadgePopover
                                                                  [Blunder <TreePalm> 94%]
                                                                  hover(mouse)/tap/keyboard -> "Facepalm 94%" + D-18 copy
```

### Files to touch (complete call-site inventory)

**Backend**

| File | Change | Lines today |
|------|--------|-------------|
| `app/routers/library.py` | Add `min_facepalm_pct: int \| None = Query(default=None, ge=0, le=100)` and `max_facepalm_pct` to `get_library_games` and `get_library_flaws`; forward to service | params at 73-74 and 321-322; forwards at 116-117 and 362-363 |
| `app/services/library_service.py` | Add the two kwargs to `get_library_games` (931-932 / forward 990-991) and `get_library_flaws` (1276-1277 / forward 1327-1328) | — |
| `app/repositories/library_repository.py` | New constants + `facepalm_range_active()` + `_facepalm_clause()`; params on `build_flaw_filter_clauses` (585), `flaw_exists_from_table` (694), `query_flaws` (1050), `query_filtered_games` (1539); `_build_flaw_item` (908) sets `facepalm_score=flaw.facepalm_score` | — |
| `app/repositories/query_utils.py` | `apply_game_filters` (signature ~194): two kwargs; lazy-import `facepalm_range_active`; extend the gate `if flaw_severity or flaw_tags or tactic_active` (line ~428) with `or facepalm_active`; forward to `flaw_exists_from_table` | 380-430 |
| `app/schemas/library.py` | `FlawListItem` (172): `facepalm_score: float \| None = None` | — |

Deliberately NOT touched (they never received tactic depth either, verified by reading the call sites): `_filtered_games_base` (1484), `count_filtered_and_analyzed` (1642), `fetch_flaw_comparison`, `fetch_tactic_comparison`, stats endpoints, `library_service.py:520/540` (`tactic_slot_visible(... min_tactic_depth=None ...)` in Games-card tactic chip building), `GameFlawCard`, `fetch_page_game_flaws`. Defaulting the new params to `None` keeps every one of these callers unchanged. Frontend Stats hooks pass `DEFAULT_FLAW_FILTER` and only send severity/tags (`useLibrary.ts:187-236`), so no change there.

**Frontend**

| File | Change |
|------|--------|
| `src/lib/facepalm.ts` (new) | Constants, presets, `derivePreset`, `presetToRange`, `sliderToRange`, `displayUpper`, `formatFacepalmSummary`, `facepalmToQueryParams`, `toFacepalmPct`, `isFacepalmNarrowed` (clone of `lib/tacticDepth.ts`) |
| `src/components/filters/FacepalmFilter.tsx` (new) | Wrapper over `PresetRangeFilter`, clone of `TacticDepthFilter.tsx`; renders the D-12 hint when narrowed |
| `src/components/filters/PresetRangeFilter.tsx` | Optional `hint?: string` prop rendered under the slider (no hint slot exists today) |
| `src/components/filters/FlawFilterControl.tsx` | Props `facepalm?: FacepalmValue`, `onFacepalmChange?`; render `FacepalmFilter` right after the severity block (line ~549) and before Best Moves (line ~552); gate on `onFacepalmChange` presence (Gem/Great precedent), not on `showTacticFilter` |
| `src/hooks/useFlawFilterStore.ts` | `facepalmMin`, `facepalmMax` fields; defaults; `isFlawFilterNonDefault` clause with `?? default` (test mocks pass partial objects) |
| `src/pages/library/GamesTab.tsx` | Two `FlawFilterControl` sites (~353 desktop, ~536 mobile): pass `facepalm` + `onFacepalmChange` |
| `src/pages/library/FlawsTab.tsx` | Two sites (~336, ~557): same |
| `src/hooks/useLibrary.ts` | `useLibraryGames` (126) and `useLibraryFlaws` (337): add `facepalmParam` to `queryKey` and spread into the API call |
| `src/api/client.ts` | `libraryApi.getGames` (483) and `getFlaws` (597): param types + conditional inclusion `...(params.min_facepalm_pct != null ? {...} : {})` |
| `src/types/library.ts` | `FlawListItem` (239): `facepalm_score: number \| null;` |
| `src/lib/analytics.ts` | `'facepalm'` in `FILTER_TARGETS` (428-446) and `\| { target: 'facepalm'; value: FacepalmPreset \| 'custom' }` in `FilterChangeProps` (469-484) |
| `src/components/library/SeverityBadge.tsx` | Optional `facepalmScore?: number \| null` (+ `ply` or a testId for unique trigger ids); render via `FacepalmBadgePopover` only when `severity === 'blunder' && facepalmScore != null` |
| `src/components/library/FacepalmBadgePopover.tsx` (new) | The popover trigger/content (see Pattern 4) |
| `src/components/library/FlawCard.tsx` | `tagsRow` (350-355): pass `facepalmScore={flaw.facepalm_score}` and `ply={flaw.ply}` |

No generated files are involved: `FlawListItem` is hand-written in `src/types/library.ts` and mirrored by hand; `frontend/src/generated/` holds only `botStrengthCurves.ts`, `endgameZones.ts`, `flawThresholds.ts`, `personaCalibration.ts` [VERIFIED: `ls frontend/src/generated/`], and no `scripts/gen_*.py` touches library types [VERIFIED: grep]. No migration: `facepalm_score` already exists.

### Pattern 1: Backend clause, once, with a named activity predicate

Column facts [VERIFIED: app/models/game_flaw.py:114-115, 123]:
```
#   facepalm_score    = score in [0, 1] derived from maia_played_prob, maia_reply_spread
#                       and the line facts; NULL when any input is missing.
facepalm_score: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
```
The migration adds it with "no server_default, no CHECK constraint, no index" [VERIFIED: alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py:21, 54]. The score is a logistic, so it is in (0, 1); float4 rounding could in principle store exactly 1.0. Dev DB today: min 0.0038650238, max 0.9991007, 0 rows at 1.0, 0 rows at 0, all 4,557 scored rows are severity 2 [VERIFIED: dev DB read-only query].

Recommended shape (mirrors `_TACTIC_DEPTH_FULL_MIN/MAX` at library_repository.py:78-79 and `_tactic_controls_active` at 292-314):

```python
# library_repository.py
# Facepalm score filter, on the floored whole-percent scale the Flaws badge shows.
# Mirrors FACEPALM_PCT_MIN / FACEPALM_PCT_MAX in frontend/src/lib/facepalm.ts.
_FACEPALM_PCT_FULL_MIN: int = 0
_FACEPALM_PCT_FULL_MAX: int = 100
_FACEPALM_PCT_SCALE: float = 100.0


def facepalm_range_active(min_pct: int | None, max_pct: int | None) -> bool:
    """True when the inclusive percent range is narrower than the full 0..100 (D-04)."""
    min_active = min_pct is not None and min_pct != _FACEPALM_PCT_FULL_MIN
    max_active = max_pct is not None and max_pct != _FACEPALM_PCT_FULL_MAX
    return min_active or max_active


def _facepalm_clause(min_pct: int | None, max_pct: int | None) -> ColumnElement[bool] | None:
    """Score clause: floor(100 * score) in [min_pct, max_pct], NULL scores excluded.

    Written as two float comparisons (no floor() on the column) so the comparison stays on
    the stored REAL widened to double, which is what the frontend floors for display.
    """
    if not facepalm_range_active(min_pct, max_pct):
        return None
    bounds: list[ColumnElement[bool]] = [GameFlaw.facepalm_score.isnot(None)]
    if min_pct is not None and min_pct > _FACEPALM_PCT_FULL_MIN:
        bounds.append(GameFlaw.facepalm_score >= min_pct / _FACEPALM_PCT_SCALE)
    if max_pct is not None and max_pct < _FACEPALM_PCT_FULL_MAX:
        bounds.append(GameFlaw.facepalm_score < (max_pct + 1) / _FACEPALM_PCT_SCALE)
    return and_(*bounds)
```
In `build_flaw_filter_clauses`, add keyword params `min_facepalm_pct: int | None = None, max_facepalm_pct: int | None = None` after `max_tactic_depth` (before `decided_lost`, or keyword-only to avoid positional slips: note `flaw_exists_from_table` and `query_flaws` call it positionally today, lines 741-749 and 1110-1118, so passing the new args by keyword is the safe choice). Append `_facepalm_clause(...)` when not None. Do NOT gate it on `decided_lost` (that gate is tactic-only by design).

`[VERIFIED]` asyncpg binding: compiling `GameFlaw.__table__.c.facepalm_score >= 0.7` with `sqlalchemy.dialects.postgresql.asyncpg.dialect()` yields `game_flaws.facepalm_score >= $1::FLOAT` (double precision), not `::REAL`.

### Pattern 2: D-10 split, frontend handles -> inclusive display percents -> API

| UI state | Handles (lo, hi) | Summary | API params | SQL |
|----------|------------------|---------|-----------|-----|
| All (default) | 0, 100 | `All` or `0-100%` | omitted | no clause |
| Low | 0, 25 | `Low: 0-29%` | `max_facepalm_pct=29` (min 0 may be sent or omitted) | `score IS NOT NULL AND score < 0.30` |
| Mid | 30, 65 | `Mid: 30-69%` | `min=30, max=69` | `score >= 0.30 AND score < 0.70` |
| High | 70, 100 | `High: 70-100%` | `min=70, max=100` | `score >= 0.70` |
| Custom | 40, 40 | `40-44%` | `min=40, max=44` | `score >= 0.40 AND score < 0.45` |

Checks against D-10: score 0.27 -> floor 27 -> Low (`0.27 < 0.30`). Score 0.699 -> floor 69 -> Mid (`0.699 < 0.70`). Score 1.0 -> High (no upper bound when max is 100).

```ts
// frontend/src/lib/facepalm.ts (sketch; names are recommendations)
export const FACEPALM_PCT_MIN = 0;
export const FACEPALM_PCT_MAX = 100;
export const FACEPALM_STEP = 5;
/** Percent cutoffs between Low/Mid/High (D-09). UI constants, NOT FACEPALM_SCORE_MIN. */
export const FACEPALM_MID_CUTOFF = 30;
export const FACEPALM_HIGH_CUTOFF = 70;
const PCT_SCALE = 100;

export type FacepalmPreset = 'all' | 'low' | 'mid' | 'high';
/** Slider handle positions (multiples of FACEPALM_STEP). hi covers [hi, hi + STEP) unless hi is the max. */
export interface FacepalmValue { min: number; max: number }

export const PRESET_RANGES: Record<FacepalmPreset, FacepalmValue> = {
  all: { min: FACEPALM_PCT_MIN, max: FACEPALM_PCT_MAX },
  low: { min: FACEPALM_PCT_MIN, max: FACEPALM_MID_CUTOFF - FACEPALM_STEP },   // 0, 25
  mid: { min: FACEPALM_MID_CUTOFF, max: FACEPALM_HIGH_CUTOFF - FACEPALM_STEP }, // 30, 65
  high: { min: FACEPALM_HIGH_CUTOFF, max: FACEPALM_PCT_MAX },                // 70, 100
};

/** Inclusive upper display percent of the upper handle's bucket: 25 -> 29, 100 -> 100. */
export function displayUpper(hi: number): number {
  return hi >= FACEPALM_PCT_MAX ? FACEPALM_PCT_MAX : hi + FACEPALM_STEP - 1;
}

/** Whole percent shown on the badge, rounded down so it agrees with the filter band. */
export function toFacepalmPct(score: number): number {
  return Math.min(FACEPALM_PCT_MAX, Math.max(FACEPALM_PCT_MIN, Math.floor(score * PCT_SCALE)));
}

export function facepalmToQueryParams(
  value: FacepalmValue,
): { min_facepalm_pct?: number; max_facepalm_pct?: number } {
  if (value.min === FACEPALM_PCT_MIN && value.max === FACEPALM_PCT_MAX) return {};
  return { min_facepalm_pct: value.min, max_facepalm_pct: displayUpper(value.max) };
}
```
Sending `{}` at the default (rather than always sending, as tactic depth does) keeps the query key and URL stable; the backend still treats an explicit 0..100 as no clause, so both directions are safe.

Why not send 0..1 floats or an exclusive upper bound: an exclusive upper bound has no clean value for "handle at 100 includes 100%" (needs 101 or a special case), and floats invite precision drift between the summary text and the SQL. Inclusive integer percents match the summary text verbatim and make the router validation a plain `ge=0, le=100`.

### Pattern 3: Filter wrapper with hint (D-08, D-12, D-19)

Clone `TacticDepthFilter.tsx` (read in full): `derivePreset` -> `activePreset`; `useDebouncedTrackFeature('filter-change')` in `onValueCommit` sending `derivePreset(...) ?? 'custom'`; `trackFeature` on preset click only when the preset changes; `isSummaryActive = activePreset !== 'all'`; `gridClassName="grid-cols-4"`; `testIdPrefix="filter-facepalm"` (yields `filter-facepalm-info`, `-summary`, `-presets`, `-preset-low`, `-slider`); `slider={{ min: 0, max: 100, step: 5, minStepsBetweenThumbs: 0, ... thumbLabels: ['Minimum facepalm score', 'Maximum facepalm score'] }}`. `PresetRangeFilter` renders the slider last inside its root div and has no hint slot (read in full); add an optional `hint?: string` rendered as `<p className="mt-1 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-hint`}>` after the slider, and pass `hint={narrowed ? 'Mistakes are excluded' : undefined}`. The D-19 info copy is two `<p>` paragraphs in `infoChildren`.

### Pattern 4: Scored Blunder badge popover (D-14..D-18)

`SeverityBadge` today [VERIFIED: frontend/src/components/library/SeverityBadge.tsx, read in full]: a `<span>` with `role="button"`/`tabIndex` only when `onActivate`; hover/lift/brighten only when `onHover || onActivate` (`interactive`); `data-testid={`severity-${severity}-${gameId}`}`; `aria-label` = `"Blunder"` when `showCount={false}`; active-filter ring when `flawFilter.severity` is exactly `[severity]`; text `text-sm font-bold`.

Call sites [VERIFIED: grep of imports]: `components/library/FlawCard.tsx:350-355` (`severity, count={1}, gameId, showCount={false}`) and `components/train/TrainPuzzleCard.tsx:173-179` (Train Archive, `showActiveFilterRing={false}`). `LibraryGameCard.tsx` only mentions it in comments (609, 612); the Games card's counts come from the MoveStats table, so D-17's "Games-card count badges untouched" holds by construction. Only FlawCard passes the new prop; TrainPuzzleCard and the existing tests stay byte-identical in behavior.

Existing popover triggers in the app, surveyed:

| Component | Primitive | Hover | Click/tap | Keyboard | Umami | Notes |
|-----------|-----------|-------|-----------|----------|-------|-------|
| `ui/info-popover.tsx` (`InfoPopover`) | `radix-ui` Popover, `<span role="button" tabIndex=0>` trigger | `onMouseEnter` 100ms timer, close on leave | Radix trigger toggle | none (span: Enter/Space do nothing, no focus-open) | `useTrackedPopoverOpen(testId)` | Has `triggerContent` for custom triggers (used by `GemMoveBadge.tsx:88`) |
| `ui/metric-info-popover.tsx` | same | same + unmount cleanup | same | none | same | Cleanest template |
| `library/TagChip.tsx` definition popover | `radix-ui` Popover, controlled `useState` | 100ms open, 80ms grace close (fixes trigger->content flicker) | Radix toggle | onFocus only sets `highlighted` | none (predates the rule) | `onCloseAutoFocus` prevented to avoid a lingering focus ring |
| `ui/tooltip.tsx` | Radix Tooltip | yes | blocked for touch/pen via `lastPointerType` ref | — | — | The in-repo precedent for a pointer-type guard |

None of these opens on keyboard focus, which D-16 now asks for. Recommendation: a new `FacepalmBadgePopover` cloned from `MetricInfoPopover` (tracked open, 100ms hover delay, unmount cleanup, same Content classes), with these deltas:

1. Trigger is a real `<button type="button">` wrapping the badge span (semantic-HTML rule; FlawCard's tags row is not inside another button or link, so no nesting issue). Native Enter/Space produce a click, which Radix turns into a toggle.
2. Hover opens only for mouse: use `onPointerEnter`/`onPointerLeave` and ignore `e.pointerType !== 'mouse'` (tooltip.tsx precedent). Touch then has exactly one opener, the Radix click toggle.
3. Keyboard focus opens it, but not pointer-initiated focus: set a ref in `onPointerDown`, and in `onFocus` open only when that ref is unset (then clear it). Without this, a tap focuses the button (opens) and then clicks (Radix toggles it closed again).
4. `onOpenAutoFocus={(e) => e.preventDefault()}` and `onCloseAutoFocus={(e) => e.preventDefault()}` on Content: otherwise Radix moves focus into the content on a hover-open, and on close returns focus to the trigger, which would re-fire focus-open (an open/close loop) and leave a stray focus ring (TagChip comment).
5. Close on `onBlur` and on mouse leave (with TagChip's 80ms grace so moving into the content does not close it).
6. `testId` for tracking built from numbers only: trigger `facepalm-badge-${gameId}-${ply}` -> Umami target `facepalm-badge` (numeric segments are stripped by `popoverTargetFromTestId`, analytics.ts:581-595). Content `facepalm-badge-${gameId}-${ply}-popover`.
7. `aria-label` on the button names the score, e.g. `Blunder, Facepalm 94%`; the icon gets `aria-hidden`.

Badge content when scored: `Blunder` + `<TreePalm className="h-3.5 w-3.5" aria-hidden />` + `{pct}%`, all inside the existing `text-sm font-bold` span and `SEV_BLUNDER*` colors (D-15). Set the badge's `interactive` affordance (lift, brighten, cursor) when scored, so it reads as clickable like TagChip. Keep the inner `data-testid="severity-blunder-${gameId}"` so FlawsTab/SeverityBadge tests keep working. Popover body: heading `<p className="font-bold">Facepalm {pct}%</p>` then the D-18 sentence (popover bodies may use `text-xs`).

### Anti-Patterns to Avoid
- **Per-endpoint score clause** in `query_flaws` or the router: violates the shared-filter rule and breaks Games/Flaws parity.
- **`floor(facepalm_score * 100)` in SQL**: `real * integer` evaluates in float4 in Postgres, so a stored 0.69999999 can round to 70.0 and disagree with the JS floor. Compare the column against double thresholds instead.
- **Binding thresholds as REAL** (`literal(x, REAL)` or `type_coerce`): float4(0.70) = 0.699999988, and a stored score equal to it would pass `>= 0.70` while the badge shows 69%.
- **Gating the facepalm section on `showTacticFilter`**: both tabs pass `true`, and it is not a tactic control.
- **Adding the params to stats/comparison/count functions**: they never took tactic depth; their denominators must stay unfiltered.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Range slider + presets UI | A new slider layout | `PresetRangeFilter` (+ new `hint` prop) | Shared look with Tactic Depth / Opponent Strength (D-08) |
| Slider analytics debounce | Own debounce | `useDebouncedTrackFeature('filter-change')` | Radix commits per keyboard step |
| Popover open tracking | Manual `trackFeature('popover-open')` | `useTrackedPopoverOpen(testId)` | Once-per-instance semantics, target normalization |
| Popover positioning/portal/escape/outside-click | Custom overlay | `radix-ui` Popover | Already used by every popover in the app |
| User scoping of flaws | New gate | existing `player_only_gate` + `GameFlaw.user_id == user_id` in both query paths | Already applied in `query_flaws` and `flaw_exists_from_table` |

## Runtime State Inventory

Not a rename/refactor/migration phase. Omitted.

## Common Pitfalls

### Pitfall 1: Facepalm-only filter does nothing on the Games tab
**What goes wrong:** `apply_game_filters` builds the flaw EXISTS only `if flaw_severity or flaw_tags or tactic_active:` [VERIFIED: app/repositories/query_utils.py ~427, read]. With only the facepalm range narrowed, the gate is false and the Games tab returns every game.
**How to avoid:** compute `facepalm_active = facepalm_range_active(min_facepalm_pct, max_facepalm_pct)` (lazy import, same as `_tactic_controls_active`) and add it to the gate; the `user_id is None` ValueError then covers it too. Also, `flaw_exists_from_table` returns `true()` when no clause is produced, so the clause must be produced there via `build_flaw_filter_clauses`.
**Warning signs:** a Games-tab integration test with no severity/tags/tactics and a narrowed range returns unscored games. Mirror `test_depth_filter_narrows_games_without_family` (tests/test_library_repository.py:428).

### Pitfall 2: Positional-argument slip in `build_flaw_filter_clauses`
**What goes wrong:** `flaw_exists_from_table` (741) and `query_flaws` (1110) pass `severity, tags, families, orientation, min_depth, max_depth` positionally. Inserting new params mid-signature silently shifts arguments.
**How to avoid:** add the new params at the end or keyword-only, and pass them by keyword everywhere.

### Pitfall 3: Float precision between SQL band and displayed percent
**What goes wrong:** band membership and the badge percent disagree near cutoffs.
**How to avoid:** SQL compares the REAL column against Python-float thresholds (bound `::FLOAT`, double); the frontend shows `Math.floor(score * 100)` of the same widened double. Verified on dev DB: for k in 5, 10, ..., 95, `(score >= k/100::float8) <> (floor(score::float8*100) >= k)` matched 0 rows of 4,557. float4-exact thresholds (0.25, 0.5, 0.75) multiply exactly by 100, so they agree too.
**Warning signs:** any `floor()` or `* 100` on the column in SQL, or a REAL-typed bind.

### Pitfall 4: Tap double-toggle on the badge
**What goes wrong:** with open-on-focus, a tap focuses the trigger (open) and then clicks (Radix toggle closes). With open-on-hover via `onMouseEnter`, mobile compat mouse events also arm the timer.
**How to avoid:** mouse-only hover (`pointerType === 'mouse'`), and focus-open skipped when a pointerdown preceded the focus (Pattern 4, items 2-3).
**Warning signs:** on a phone the popover flashes and closes on tap.

### Pitfall 5: Radix focus management fighting focus-open
**What goes wrong:** Radix Popover auto-focuses the content on open and returns focus to the trigger on close; with focus-open this reopens the popover after it closes, and leaves a focus ring after hover (TagChip.tsx comment explains the ring).
**How to avoid:** `onOpenAutoFocus` and `onCloseAutoFocus` both `preventDefault()`.

### Pitfall 6: Duplicate DOM per card
**What goes wrong:** `tagsRow` renders twice in FlawCard (mobile `sm:hidden` and desktop bodies), so test queries need `getAllByTestId`, and two tracked-popover instances exist (only the visible one is user-reachable, so tracking stays once per real open).
**How to avoid:** follow the FlawsTab test precedent (`getAllByTestId('severity-blunder-1')`).

### Pitfall 7: Partial filter objects in tests
**What goes wrong:** several tests mock `useFlawFilterStore` with `{ severity, tags }` only (SeverityBadge.test.tsx:17). A non-optional-chained read of `facepalmMin` in `isFlawFilterNonDefault` would treat `undefined !== 0` as narrowed.
**How to avoid:** `(filter.facepalmMin ?? DEFAULT_FACEPALM_VALUE.min) !== DEFAULT_FACEPALM_VALUE.min`, as the depth lines already do.

### Pitfall 8: `FlawListItem` fixture drift
**What goes wrong:** `facepalm_score: number | null` (required) breaks `makeFlaw` in `FlawCard.test.tsx` (~line 130-155). Tests are not type-checked by `tsc -b`, so the only signal is runtime `undefined` behaving like "no score".
**How to avoid:** add `facepalm_score: null` to `makeFlaw` defaults and to the FlawsTab test flaw fixtures; run `npm run build` for the source change.

### Pitfall 9: Unscored blunders vanish under any narrowed range
Dev DB: 15,198 user blunders (player-parity gate, severity 2) still have `facepalm_score IS NULL` [VERIFIED: dev DB read-only query], against 4,557 scored. Any narrowed range hides them; this is D-04 by design and D-12 deliberately does not mention it. Expect UAT on dev to show small counts. Not a bug.

## Code Examples

### Router params (copy of the tactic depth pattern)
```python
# app/routers/library.py, both get_library_games and get_library_flaws
# Inclusive whole-percent bounds on the floored facepalm score (0..100). Full range
# (both None, or 0 and 100) = no filter.
min_facepalm_pct: int | None = Query(default=None, ge=0, le=100),
max_facepalm_pct: int | None = Query(default=None, ge=0, le=100),
```
Add `0`/`100` as module constants if the reviewer treats the `ge`/`le` literals as magic numbers (the depth params use bare `0`/`11` today, router lines 73-74).

### apply_game_filters gate
```python
from app.repositories.library_repository import facepalm_range_active  # lazy, inside the function
facepalm_active = facepalm_range_active(min_facepalm_pct, max_facepalm_pct)
if flaw_severity or flaw_tags or tactic_active or facepalm_active:
    ...
    exists_pred = flaw_exists_from_table(
        user_id=user_id, severity=severities, tags=tag_list,
        tactic_families=families_seq, orientation=orientation,
        min_tactic_depth=min_tactic_depth, max_tactic_depth=max_tactic_depth,
        min_facepalm_pct=min_facepalm_pct, max_facepalm_pct=max_facepalm_pct,
    )
```

### Umami registry (analytics.ts)
```ts
export const FILTER_TARGETS = [ /* ...existing... */ 'tactic-depth', 'facepalm', 'has-gem', /* ... */ ] as const;
// FilterChangeProps union:
| { target: 'facepalm'; value: FacepalmPreset | 'custom' }
```
Never send the bounds (D-04 of the analytics rules; CONTEXT discretion).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate neutral `Facepalm 94%` chip | Score inside the Blunder badge, icon without the word | Owner, 2026-11-14 (this planning session) | No new chip component, no neutral tokens; popover heading names the icon |
| Tactic depth params always sent | Facepalm params omitted at default | Recommendation | Cleaner query key/URL; backend tolerant either way |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mobile browsers emit compat `mouseenter` before `click` on tap, so a mouse-event hover timer and the Radix toggle both resolve to "open" (why InfoPopover works on phones today); the recommended pointer-type guard sidesteps this anyway | Pattern 4 / Pitfall 4 | Low: the guard makes touch click-only regardless |
| A2 | jsdom 30 + RTL deliver `pointerType` on `fireEvent.pointerDown/pointerEnter` to React handlers (precedent: EndgameEloTimelineSection.test.tsx:496 passes `pointerType: 'mouse'`) | Validation | Low: if pointerEnter does not carry it, test hover with `pointerOver` or assert the guard via a unit-level handler test |
| A3 | Radix Popover on a native `<button>` trigger toggles on Enter/Space via the synthesized click | Pattern 4 | Low: standard DOM behavior; covered by a keyboard test |

## Open Questions

1. **Summary text at the default.** `All` vs `0-100%`. Tactic Depth shows `High: 1-12` at its default. Recommendation: `All` (shorter, matches the active preset chip), muted style.
2. **Should the badge ring when the facepalm filter is narrowed?** The badge already rings when severity is narrowed to blunders. CONTEXT does not ask for a facepalm ring; recommendation: no extra ring (scope).
3. **Inverted ranges via the API.** `min_facepalm_pct > max_facepalm_pct` returns an empty result; tactic depth does not validate either. Recommendation: leave unvalidated (the UI cannot produce it).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (docker `flawchess-dev-db-1`) | backend integration tests | ✓ | running | — |
| uv / Python | backend tests, ty | ✓ | Python 3.14 venv | — |
| node / vitest | frontend tests | ✓ | vitest ^5.0.5 | — |
| lucide `TreePalm` | badge icon | ✓ | lucide-react 1.70.0 | — |

Smoke run this session: `uv run pytest tests/repositories/test_library_repository.py tests/test_query_utils.py -n 4` -> 39 passed; `npx vitest run src/lib/__tests__/tacticDepth.test.ts src/components/library/__tests__/SeverityBadge.test.tsx` -> 36 passed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest 5 + RTL + jsdom frontend |
| Config file | `pyproject.toml` / `tests/conftest.py` (per-worker cloned DB); `frontend/vite.config.*` |
| Quick run command | `uv run pytest tests/test_library_repository.py tests/repositories/test_library_repository.py tests/test_query_utils.py tests/test_library_router.py -n auto` and `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts src/components/library/__tests__/SeverityBadge.test.tsx src/components/filters/__tests__/FlawFilterControl.test.tsx src/hooks/__tests__/useFlawFilterStore.test.ts` |
| Full suite command | root CLAUDE.md pre-merge gate (`uv run pytest -n auto -x`, `npm run lint && npm run build && npm test -- --run && npm run knip`, ruff, ty, function-size gate) |

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-04 | Full range (None/None and 0/100) adds no clause; narrowed adds `facepalm_score` predicate | unit (SQL compile) | `uv run pytest tests/test_library_repository.py -k facepalm` | ✅ file, ❌ tests (Wave 0) |
| D-04, D-10 | Flaws tab: scores 0.27 / 0.699 / 0.70 / 1.0 / NULL and a mistake land in Low / Mid / High / High / excluded / excluded | integration (`query_flaws`) | `uv run pytest tests/repositories/test_library_repository.py -k facepalm` | ✅ file, ❌ tests |
| D-06, Pitfall 1 | Games tab: facepalm-only range narrows games; combined with tags requires the SAME flaw row | integration (`query_filtered_games`) | `uv run pytest tests/test_library_repository.py -k "facepalm and games"` | ✅ file, ❌ tests |
| D-05 | Opponent-ply scored flaw never matches | integration | same file | ❌ |
| D-06 | `apply_game_filters` with only facepalm params emits EXISTS referencing `facepalm_score` | unit (SQL compile) | `uv run pytest tests/test_query_utils.py -k facepalm` | ✅ file, ❌ tests |
| Router | Params forwarded; `ge/le` 422 on 101/-1; default None | API | `uv run pytest tests/test_library_router.py -k facepalm` | ✅ file, ❌ tests |
| Schema | `FlawListItem.facepalm_score` populated from the row, None when NULL | integration | `tests/repositories/test_library_repository.py` | ❌ |
| D-09, D-10 | Presets, `displayUpper`, `derivePreset`, `formatFacepalmSummary`, `facepalmToQueryParams` ({} at default; Low -> max 29; Mid -> 30/69; High -> 70/100), `toFacepalmPct(0.697) === 69` | unit | `cd frontend && npx vitest run src/lib/__tests__/facepalm.test.ts` | ❌ new file |
| D-08, D-12, D-19 | Wrapper renders 4 presets, summary active when narrowed, hint "Mistakes are excluded" only when narrowed, preset click and slider commit track `facepalm` with preset/`custom` | component | `npx vitest run src/components/filters/__tests__/FlawFilterControl.test.tsx` (or a new `FacepalmFilter.test.tsx`) | ✅ file, ❌ tests |
| D-13 | Facepalm section renders after the severity block and before Best Moves / Tactic Depth | component (DOM order) | same | ❌ |
| Store | Defaults 0/100; `isFlawFilterNonDefault` true when narrowed, false at default and for partial mocks | unit | `npx vitest run src/hooks/__tests__/useFlawFilterStore.test.ts` | ✅ file, ❌ tests |
| Query wiring | `useLibraryGames`/`useLibraryFlaws` send params only when narrowed and include them in the query key | hook | `npx vitest run src/hooks/__tests__/useLibraryGames.test.tsx` | ✅ file, ❌ tests |
| D-14, D-17 | Scored blunder badge shows `Blunder`, icon, `94%`; unscored blunder, mistake, inaccuracy badges unchanged (no button, no popover); Train call site unchanged | component | `npx vitest run src/components/library/__tests__/SeverityBadge.test.tsx` | ✅ file, ❌ tests |
| D-16, D-18 | Click opens popover with heading `Facepalm 94%` + D-18 copy; mouse hover opens after delay; keyboard focus opens; tap (pointerdown pointerType touch, focus, click) leaves it open (no double toggle); `popover-open` tracked once with target `facepalm-badge` | component | same file, or new `FacepalmBadgePopover.test.tsx` | ❌ |
| D-14 | FlawCard passes `facepalm_score` through; `makeFlaw` default `facepalm_score: null` | component | `npx vitest run src/components/library/__tests__/FlawCard.test.tsx` | ✅ file, ❌ tests |
| Copy (D-03) | No "avoidable" / "chance" in new copy | grep | `grep -rniE "avoidable|chance you" frontend/src/components/filters/FacepalmFilter.tsx frontend/src/components/library/FacepalmBadgePopover.tsx` (expect no output) | — |
| Mutation proof | Remove `facepalm_active` from the `apply_game_filters` gate: the Games-tab facepalm-only test must fail | manual mutation | revert line, run the test, restore | — |

### Sampling Rate
- **Per task commit:** the quick-run subset for the touched stack.
- **Per wave merge:** both quick-run commands plus `cd frontend && npm run build` (type change to `FlawListItem`).
- **Phase gate:** full pre-merge gate green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `frontend/src/lib/__tests__/facepalm.test.ts` — new, covers D-09/D-10 pure logic
- [ ] `tests/test_library_repository.py` `_seed_game_flaw` (133-180): add `facepalm_score: float | None = None` kwarg (pg_insert passes the dict straight through, `bulk_insert_game_flaws` at game_flaws_repository.py:148)
- [ ] `tests/repositories/test_library_repository.py` seed helpers (`_seed_tactic_flaw` / `_seed_non_tactic_flaw`): same kwarg
- [ ] `frontend/src/components/library/__tests__/FlawCard.test.tsx` `makeFlaw`: `facepalm_score: null`
- [ ] FlawsTab test flaw fixtures: `facepalm_score` field
- No framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (existing `current_active_user`) | unchanged |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | `user_id` from the authenticated user only; `GameFlaw.user_id == user_id` + `player_only_gate` in both query paths (unchanged, the new clause rides inside them) |
| V5 Input Validation | yes | FastAPI `Query(ge=0, le=100)` ints; bound parameters only, no string interpolation |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR via filter params | Information disclosure | No user id in params; existing user scoping |
| SQL injection via bounds | Tampering | Typed ints, SQLAlchemy binds |
| Analytics leaking values | Information disclosure | Umami value is a preset key or `custom`, never bounds or scores |

## Sources

### Primary (HIGH confidence, read this session)
- `app/repositories/library_repository.py` (1-130, 230-780, 880-1240, 1484-1730), `app/repositories/query_utils.py` (96-110, 132-150, 170-460), `app/routers/library.py` (1-140, 300-380), `app/services/library_service.py` (500-550, 915-1010, 1260-1345), `app/schemas/library.py` (165-245), `app/models/game_flaw.py` (1-60, 96-135), `app/services/facepalm_score.py` (1-80), `alembic/versions/20261113_120000_e8b3c6d2f250_phase_250_facepalm.py`
- `frontend/src/lib/tacticDepth.ts`, `components/filters/TacticDepthFilter.tsx`, `PresetRangeFilter.tsx`, `FlawFilterControl.tsx` (1-108, 440-640), `hooks/useFlawFilterStore.ts`, `hooks/useLibrary.ts` (80-185, 325-375), `api/client.ts` (480-645), `types/library.ts` (235-295), `components/library/SeverityBadge.tsx`, `TagChip.tsx` (1-290), `ui/info-popover.tsx`, `ui/metric-info-popover.tsx` (1-75), `ui/tooltip.tsx` (38-63), `hooks/useTrackedOpen.ts`, `lib/analytics.ts` (420-595), `lib/theme.ts`, `FlawCard.tsx` (1-80, 320-420), `LibraryGameCard.tsx` (355-400, 530-560, 600-640)
- Tests read: `tests/test_library_repository.py` (59-185, 400-500, 1755-1800), `tests/repositories/test_library_repository.py` (1-230, 405-470), `tests/test_query_utils.py` (325-380), `tests/test_library_router.py` (1218-1260), `frontend/.../SeverityBadge.test.tsx` (1-80), `FlawFilterControl.test.tsx` (560-640), `FlawsTab.test.tsx` (325-345), `FlawCard.test.tsx` (130-160)
- Dev DB read-only probes (distribution, float/floor agreement, unscored blunder count); SQLAlchemy asyncpg compile probe

### Secondary / Tertiary
- None. No web sources were needed for this in-repo phase.

## Metadata

**Confidence breakdown:**
- Backend threading and clause: HIGH (every call site read; precision probe run)
- Frontend filter: HIGH (direct clone of read code)
- Badge popover interaction: MEDIUM-HIGH (pattern grounded in four in-repo components; touch behavior assumptions A1-A3 are low risk and test-covered)

**Research date:** 2026-11-14
**Valid until:** 2026-12-14 (stable code; re-check if Phase 250-10 changes the column or the stats seed starts)
