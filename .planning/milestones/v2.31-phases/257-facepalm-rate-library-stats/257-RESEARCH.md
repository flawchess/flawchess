# Phase 257: Facepalm Rate in the Library Stats (SEED-261114-iuv) - Research

**Researched:** 2026-11-20
**Domain:** In-repo backend aggregation (SQLAlchemy 2 async over `game_flaws`), Pydantic schemas, React/Recharts stats UI
**Confidence:** HIGH on code structure, twin design and performance shape; MEDIUM on the share-floor recommendation (one fully scored dev user plus about 100-game benchmark users, no prod data)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (seed "Current scope" and roadmap, owner 2026-11-20; not re-discussed)
- **D-01: Stats cut.** A new named constant at 0.7 (the label meaning), separate from the drill's
  `FACEPALM_SCORE_MIN` (0.5). Scores use `FACEPALM_LIBRARY_LAMBDA`. A facepalm blunder in the stats is a scored
  blunder with score >= 0.7.
- **D-02: Type rule** on the model's raw material inputs (`loss`, `missed`, both in material units): allowed
  loss when `loss > 0 and loss >= missed`, missed win otherwise. Ties count as allowed loss; rows without
  material in either line count as missed win. The fitted coefficients are not used for typing.
- **D-03: Timeline metric.** Facepalm blunders / scored blunders, pooled over the rolling window (not a mean of
  per-game shares), not split by type. Its own small chart below the Flaws Timeline with the same x-axis,
  rolling window and per-time-control series. Source is `game_flaws`; unscored blunders are left out of both
  counts. Fallback if the share is too jumpy on real accounts: a rolling mean of the score.
- **D-04: No type-share statistic.** The types are never compared with each other (the model weights lost
  material about three times as much as a missed gain), only with the same type of the opponents. No chart or
  row puts the two type levels against each other as a split.
- **D-05: Copy rules.** State the comparison, do not diagnose. The score is a ranking, not a probability
  (253 D-03 still bans probability wording such as "chance you'd see it").
- **D-06: Opponent scores stay out of drill selection and the library tag filters** (user-only,
  `player_only_gate`).
- **D-07: Name and icon.** "Facepalm", lucide `TreePalm`, whole percent rounded down (253).

#### Chip tint scope
- **D-08: All three surfaces are tinted.** Flaws-card chip (`FacepalmChip`), analysis move-list mini-chip
  (`FacepalmMoveChip`) and the `Facepalm 95%` line in the eval chart tooltip. Teal (`TAC_MISSED*`) for missed
  win, crimson (`TAC_ALLOWED*`) for allowed loss. The type therefore has to be in every payload that carries
  `facepalm_score` (`FlawListItem`, the game-card flaw item, `FlawMarker`).
- **D-09: Every scored blunder is tinted**, not only those at or above 70%. The neutral white facepalm chip
  (`FACEPALM_CHIP*`) is no longer used for scored blunders; a chip without a type does not exist.
- **D-10: The type is named in the popover, not on the chip.** Chip text stays `<TreePalm> Facepalm 94%`. The
  shared explanation (`FacepalmExplanation`) gains one line naming the type and what it means, e.g. "Missed
  win: the best move won material that was not taken." / "Allowed loss: the move gave away material." Colour is
  never the only signal.

#### Vs-opponents placement and unit
- **D-11: A new "Facepalm blunders" card in the "You vs. your opponents" section**, next to the context-tag
  cards, reusing the row and popover components (`GapRow`, `GapPopover`). It sits behind the section's existing
  analyzed-games gate and follows the page's one TC switch.
- **D-12: Unit is per 100 of the user's moves**, like every other row in that section, with the same paired
  normalisation (both sides divided by the user's move count per game, so player rate minus opponent rate equals
  the delta). This deliberately replaces the seed's "per game" wording (owner, 2026-11-20). The comparison stays
  paired per game, never pooled.
- **D-13: Neutral bar, no verdict.** The rows have no grey benchmark band and no red/green colouring in this
  phase, like tactic rows without a viable band (`has_zone = false`). The gap, both rates and the event counts
  are shown; significance may be stated in the popover but drives no colour. Verdict colours arrive with the
  benchmark zones (SEED-261120-bzq).

#### Row names and copy
- **D-14: Row labels.** "Facepalm blunders" (total), "Missed wins", "Allowed losses". The terms "chance
  blindness" and "threat blindness" do not appear anywhere in the UI in this phase: they name a verdict, and
  without a band there is no verdict to name.
- **D-15: Row hints name the 70% cut** (owner-selected direction; exact wording may be polished):
  - Facepalm blunders: "Blunders with a facepalm score of 70% or more"
  - Missed wins: "Facepalm blunders that passed up a material win"
  - Allowed losses: "Facepalm blunders that gave away material"
- **D-16: Card intro and popovers state the comparison only**, e.g. "Your facepalm blunders per 100 of your
  moves, next to your opponents' in the same games." No mention of focus, distraction, time trouble or
  blindness, and no sentence on what a higher rate means. The popover says there is no typical range for these
  rows yet.

### Claude's Discretion
- **Share chart floor and look** (area offered, owner left it to Claude; defaults announced and not objected to):
  a point needs the existing 10-game window floor and at least 20 scored blunders in the window (a named
  constant; the researcher should check on real accounts, including thin time controls, whether 20 is enough to
  keep the line from jumping); y-axis in percent fitted to the data; the same per-week volume bars, date ticks,
  inactivity markers and rolling-window caption as the Flaws Timeline; title "Facepalm share of blunders"; a
  text fallback below two points; a tooltip that gives the share and the two counts (facepalm / scored).
- Whether the share series is added to the existing flaw-stats response or its own endpoint, and whether the
  three facepalm rows join `FlawComparisonTc` or a separate payload.
- Position of the Facepalm card among the existing cards and its layout on phones.
- Popover type-line wording for opponent blunders on the analysis surfaces ("their level" variant already
  exists via `byOpponent`).
- Schema shape of the type (a `Literal["missed_win", "allowed_loss"]`, null when the score is null).
- Umami event targets and `data-testid` names (follow the existing library-stats patterns).

### Deferred Ideas (OUT OF SCOPE)
- Benchmark zones and red/green verdicts for the facepalm rows; "chance blindness" / "threat blindness" as named
  readings — SEED-261120-bzq.
- Within-player bias against a benchmark, type-by-clock matrix, training weighting by type — SEED-261120-bzq.

#### Reviewed Todos (not folded)
- The todo matcher returned four keyword-only hits (`172-deferred-review-findings`, bitboard storage for
  partial-position queries, WR-01 invalid Tailwind class, variation-tree nested button). None relates to this
  phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs are mapped. The locked decisions are the requirement set.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Stats cut constant 0.7 next to `FACEPALM_SCORE_MIN` | §Pattern 1; the cut `score >= 0.7` equals the Facepalm filter's High preset bound (§Pitfall 7) |
| D-02 | Type rule on raw `loss` / `missed`, SQL + Python twin | §Pattern 1 (twin skeleton), real-data parity probe: 0 mismatches over 11,020 rows |
| D-03 | Pooled share timeline from `game_flaws` | §Pattern 3, share-floor findings, perf §Pattern 5 |
| D-04 | No type-vs-type statistic | Share is untyped; type rows are only you-vs-opponents |
| D-05 / D-16 | Comparison-only copy, no probability wording, no "what higher means" | §Pitfall 4 (GapPopover's "Fewer is better." and the better/worse caption) |
| D-06 | Opponent scores stay out of drill and tag filters | Existing gates verified (§D-06 audit); new readers are aggregate-only |
| D-07 | "Facepalm", `TreePalm`, floor to whole percent | Existing `toFacepalmPct` |
| D-08 / D-09 | Type in `FlawListItem`, `FlawMarker`; all three surfaces tinted; `FACEPALM_CHIP*` removed | §Pattern 2 (payload map), §Pitfall 5 (knip) |
| D-10 | Type named in `FacepalmExplanation`; colour never the only signal | §Pattern 6; open question on the eval-chart tooltip line |
| D-11 / D-12 | Facepalm card in vs-opponents, per 100 user moves, paired | §Pattern 4 (`_paired_series` reuse) |
| D-13 | Neutral bar, no verdict even when significant | §Pitfall 3: `effectiveVerdict` colours zoneless significant cells today |
| D-14 / D-15 | Row labels and hints | §Pattern 6 (meta table) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- SQLAlchemy 2.x async `select()` API; no SQL in services (repositories own queries); routers stay thin, with `APIRouter(prefix=..., tags=...)` and relative paths.
- All game filtering goes through `apply_game_filters()` (here via `_filtered_games_base`); never duplicate filter logic.
- Never `asyncio.gather` on one `AsyncSession`: run the new queries sequentially.
- No magic numbers: `FACEPALM_STATS_MIN`, the share floor and similar values are named constants.
- `Literal[...]` for fixed value sets in schemas and in service/repository signatures. `Sequence[...]` for parameters taking `list[Literal]`.
- ty must pass with zero errors (`uv run ty check app/ tests/ scripts/`). Explicit return types everywhere. `# ty: ignore[rule]` only with a reason.
- Nesting depth <= 4 (gated by `scripts/check_function_size.py app/ --fail-over-depth 4` and eslint `max-depth`). About 100 logic lines per function is soft guidance. `fetch_flaw_comparison` is already far past it, so do not grow it (§Pattern 4).
- Sentry: `capture_exception` in non-trivial `except` blocks in services and routers. No variables in error messages. The existing `get_flaw_stats` / `get_flaw_comparison` try blocks already cover the new calls if those calls go inside them.
- Comment every bug fix at the fix site.
- Frontend: colours with meaning live in `theme.ts`. `text-sm` is the minimum (the chip's `text-xs` is an existing, requested exception; popover bodies may use `text-xs`). Every interactive element gets a `data-testid`. Feature events go through `trackFeature`, and popovers are tracked through `useTrackedPopoverOpen` testids. Every `useQuery` chain needs an `isError` branch. Knip fails on dead exports. `npm run build` is the type check.
- Pre-merge gate: ruff format/check, ty (app + analysis), function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip.
- Never run `bin/reset_db.sh`. Never touch `.env` files. Do not plan work outside the phase scope.
- Communication: use em-dashes sparingly in UI copy.

## Summary

Every building block exists. The facepalm score is one query-time SQL expression, `facepalm_expr(lam)`, with a Python twin. The you-vs-opponents machinery (`_paired_series`, `_paired_gap_test`, zoneless cells) and the Flaws Timeline window walk (`_compute_flaw_trend`) can be reused as they are. The phase is mostly plumbing, with four real design points:

1. **A type twin.** `facepalm_type_sql` / `facepalm_type` sit next to the score twin and read exactly the `loss` / `missed` inputs the score reads (`_loss_sql` / `_missed_sql`, `material_loss` / `material_missed`). A throwaway draft of this rule matched Python and SQL on all 11,020 real blunders of dev user 28 (0 mismatches). It also showed that 244 of those rows have a type but a NULL score, so readers must null the type wherever the score is null.
2. **Neutral verdicts.** The existing zoneless path does colour significant gaps (`effectiveVerdict` returns better/worse for `hasZone=false` + `significant=true`). D-13 forbids that, so the frontend needs an explicit "no verdict" switch on the cell. A copy hazard comes with it: `GapPopover` always appends "Fewer is better." (D-16 bans stating what a higher rate means).
3. **Evaluate the score once per row.** Postgres pulls simple subqueries up and inlines the score expression into every `FILTER (...)` that references it. A fenced inner subquery (`.offset(0)`, rendered as `LIMIT ALL OFFSET 0`) cut the draft comparison query on dev user 28 from about 135 ms (expression referenced 6 times) to 50 to 69 ms. It also cut planning time from 37 ms to 2.6 ms, because the compiled expression is about 34 KB of SQL.
4. **The share floor.** In steady state the pooled share is stable: weekly step median 1.2 to 2.1 points, p90 3.6 to 5 points on dev user 28. Even 2400-rated rapid players have about 1.18 blunders per game, so a full 100-game window holds about 100 scored blunders. The scored floor therefore only bites while a time control's window is still filling. There, benchmark users with 25 to 36 scored blunders show first-point jumps of 8 to 19 points. **Recommendation: `FACEPALM_SHARE_MIN_SCORED = 50`** rather than 20. The rolling-score fallback (D-03) is not needed.

**Primary recommendation:**
- Put the type twin in `facepalm_score.py`.
- Add a nullable `facepalm_type` next to `facepalm_score` in `FlawListItem` and `FlawMarker`.
- Put the share on the existing `/flaw-stats` response, computed in the same window walk as the Flaws Timeline, keyed by `game_id`, so the dates match point for point.
- Put the three facepalm rows on `FlawComparisonTc` as `facepalm_bullets`, built by a new fenced repository query over the same anchor.
- On the frontend, add a `noVerdict` flag to `GapCell` and drop "Fewer is better." for these rows.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Type rule (D-02) | API / Backend (`app/services/facepalm_score.py`) | Database (SQL twin) | Same seam as the score: pure Python + SQL twin, pinned by tests |
| Type on chips / markers | API / Backend (repository SELECT) | Browser (tint only) | The frontend never derives the type. It reads `facepalm_type`. |
| Share timeline numbers | API / Backend (service window walk) | Database (per-game counts) | Mirrors `_compute_flaw_trend`; SQL gives per-game counts, Python does windowing |
| Vs-opponent facepalm rows | API / Backend (`_paired_series`) | Database (fenced COUNT FILTER) | Same paired machinery and CI as every other row |
| Tint colours, labels, copy | Browser (`theme.ts`, `lib/facepalm.ts`, `flawComparisonMeta.ts`) | — | Presentation only |
| User-only gates (D-06) | Database (`player_only_gate` in readers) | — | Already in place; the new readers are aggregate-only and feed no filter |

## Standard Stack

No new libraries. Everything uses what is installed:

| Library | Version (verified) | Use here |
|---------|--------------------|----------|
| SQLAlchemy async + asyncpg | repo lockfile | `case`, `func.count().filter`, `.offset(0)` fence |
| Pydantic v2 | repo lockfile | `Literal["missed_win", "allowed_loss"] | None` fields |
| Python | 3.14.3 `[VERIFIED: uv run python --version]` | — |
| recharts | 3.10.1 `[VERIFIED: frontend/node_modules/recharts/package.json]` | `ComposedChart` share line. `Line` defaults to `connectNulls: false` `[VERIFIED: node_modules/recharts/lib/cartesian/Line.js:132 "connectNulls: false,"]`, so null share points render as a gap. |
| vitest | 5.1.0 `[VERIFIED: npx vitest --version]` | frontend tests |

## Package Legitimacy Audit

Not applicable: this phase installs no external packages.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
GET /library/flaws ─────────► query_flaws ──┐
GET /library/games, /game ──► fetch_page_facepalm_scores ──┤  per row: facepalm_expr(LIB_LAMBDA) + facepalm_type_expr()
                                             │  (owner side only, player_only_gate)
                                             ▼
                          FlawListItem / FlawMarker {facepalm_score, facepalm_type}
                                             ▼
             FacepalmChip / FacepalmMoveChip / EvalChart tooltip ── tint by type (TAC_MISSED* | TAC_ALLOWED*)
                                             └─ popover: FacepalmExplanation(score, type) names the type

GET /library/flaw-stats ──► get_flaw_stats
     ├─ fetch_flaw_trend_rows (oracle cols, + game_id) ──┐
     └─ fetch_facepalm_share_counts (game_flaws, fenced) ─┤ {game_id: (scored, facepalm)}
                                                          ▼
                 _compute_flaw_trend(rows, share_by_game): one walk, 100-game window, ISO week
                                                          ▼
          FlawTrendPoint {..., facepalm_share|null, facepalm_in_window, scored_in_window}
                    ├─► FlawTrendChart (unchanged)
                    └─► FacepalmShareChart (same points, same dates, null = gap)

GET /library/flaw-comparison ──► get_flaw_comparison
     ├─ fetch_flaw_comparison (unchanged 42 columns)
     └─ fetch_facepalm_comparison (same anchor, fenced per-blunder s/ftype, 6 COUNT FILTERs)
                    ▼ _bucket_rows_by_tc → _paired_series ×3 → _build_facepalm_bullet (has_zone False)
          FlawComparisonTc.facepalm_bullets[3]
                    ▼
          VsOpponentsSection → FacepalmCard (GapRow ×3, GapPopover, noVerdict cells)
```

### Recommended file touch list

```
app/services/blunder_check_rules.py   # FACEPALM_STATS_MIN = 0.7 (next to FACEPALM_SCORE_MIN)
app/services/facepalm_score.py        # FacepalmType, facepalm_type_of, facepalm_type, facepalm_type_sql, facepalm_type_expr
app/schemas/library.py                # facepalm_type on FlawListItem + FlawMarker; share fields; FacepalmMetric, FacepalmBullet; FlawComparisonTc.facepalm_bullets
app/repositories/library_repository.py# query_flaws + fetch_page_facepalm_scores carry the type; fetch_facepalm_share_counts; fetch_facepalm_comparison; shared anchor helper
app/services/library_service.py       # facepalm_by_ply value type; _compute_flaw_trend share accumulation; _build_facepalm_bullet; wiring
frontend/src/types/library.ts         # mirror types
frontend/src/lib/facepalm.ts          # FacepalmType style/label map; export FACEPALM_HIGH_CUTOFF for the hint
frontend/src/lib/theme.ts             # delete FACEPALM_CHIP*; add a share-line constant
frontend/src/lib/gapBar.ts            # GapCell.noVerdict
frontend/src/lib/flawComparisonMeta.ts# FACEPALM_GAP_META (labels, hints, definitions, nouns)
frontend/src/components/library/{FacepalmChip,FacepalmExplanation,FacepalmBadgePopover,EvalChart}.tsx
frontend/src/components/analysis/FacepalmMoveChip.tsx, VariationTree.tsx, hooks/analysis/useAnalysisGemMarkers.ts
frontend/src/components/library/FacepalmShareChart.tsx (new), stats/FacepalmCard.tsx (new), stats/LibraryStatsSections.tsx, stats/GapPopover.tsx
```

### Pattern 1: The type twin (D-01, D-02)

The source of truth for the inputs:
- `_loss_sql` returns NULL when the played line is unknown and no mate settles it.
- `_missed_sql` never returns NULL (it falls back to 0.0).
- `material_loss` returns None in the same cases.
- `material_missed` returns a float.

`[VERIFIED: app/services/facepalm_score.py:278-346, 448-503]`. The shipped model reads aggregated inputs:

```python
# [VERIFIED: app/services/blunder_check_rules.py:60, 82, 96-99, 106, 122] verbatim:
FACEPALM_SCORE_MIN: float = 0.5
FACEPALM_LOSS_FLOOR: int | None = 0
FACEPALM_MISSED_FLOOR: int | None = 0
FACEPALM_MISSED_CAP: int = 5
FACEPALM_MISSED_MATE: int = 5
FACEPALM_SPREAD_FORM: SpreadForm = "best_prob_for_misses"
FACEPALM_MATERIAL_INPUT: MaterialInput = "decaying_mean"
FACEPALM_LIBRARY_LAMBDA: float = 1.0
```

So "raw material inputs" means the floored, capped, depth-aggregated `loss` and `missed` in material units, the same values the score multiplies by its coefficients. Recommended skeleton:

```python
# app/services/blunder_check_rules.py, next to FACEPALM_SCORE_MIN
# 257 D-01: the library stats cut (the label meaning, 253 High preset = 70-100), separate from the drill's
# FACEPALM_SCORE_MIN. A facepalm blunder in the stats is a scored blunder with score >= this.
FACEPALM_STATS_MIN: float = 0.7

# app/services/facepalm_score.py
FacepalmType = Literal["missed_win", "allowed_loss"]

def facepalm_type_of(loss: float | None, missed: float) -> FacepalmType | None:
    """257 D-02: allowed loss when loss > 0 and loss >= missed (ties allowed), else missed win."""
    if loss is None:
        return None
    return "allowed_loss" if loss > 0 and loss >= missed else "missed_win"

def facepalm_type(facts: FacepalmFacts, *, model: FacepalmModel = FACEPALM_MODEL) -> FacepalmType | None:
    """Python twin of facepalm_type_sql. Lambda-free, coefficient-free; None iff the loss input is unknown."""
    loss = material_loss(facts.played_material, facts.mate_ply,
                         material_input=model.material_input, loss_floor=model.loss_floor)
    missed = material_missed(facts.played_material, facts.best_material, facts.best_mate_ply,
                             material_input=model.material_input, missed_floor=model.missed_floor,
                             missed_cap=model.missed_cap, missed_mate=model.missed_mate)
    return facepalm_type_of(loss, missed)

def facepalm_type_sql(columns: FacepalmColumns, *, model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[str]:
    loss = _loss_sql(columns, model)
    missed = _missed_sql(columns, model)
    return case(
        (loss.is_(None), null()),
        (and_(loss > 0, loss >= missed), literal("allowed_loss")),
        else_=literal("missed_win"),
    )

def facepalm_type_expr(model: FacepalmModel = FACEPALM_MODEL) -> ColumnElement[str]:
    """facepalm_type_sql over the GameFlaw columns (same column map as facepalm_expr)."""
```

Notes:
- **No lambda and no coefficients.** The type computes `missed` even when `_missed_weight` is 0 (lam 0). `facepalm_score` skips `missed` in that case, so do not reuse the score's internal path.
- **The type alone is not "null when the score is null".** It is NULL only when the loss input is unknown. The probe found 244 of 11,020 dev rows with a type but a NULL score (missing played probability, spread or best-move probability). Every reader must null the type when the score is NULL. The simplest way is in the item builder: `facepalm_type=ftype if chip is not None else None`. A SQL gate on the same bound score object also works.
- **Exact parity is achievable.** Python and SQL compute the decaying mean with identical operand order and power-of-two weights, so ties compare equal bitwise in both. The draft matched on every real row. Assert string equality in tests, not a tolerance.
- **Do not label a SELECT column `t`.** `Row.t` is a deprecated SQLAlchemy Row attribute, and the probe crashed on it. Use `ftype`.

### Pattern 2: Where the type travels (D-08)

| Emission site | Today | Change |
|---|---|---|
| `query_flaws` | `facepalm_chip = facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`, added only to the paged statement `base_stmt.add_columns(facepalm_chip.label("facepalm_chip"))` `[VERIFIED: app/repositories/library_repository.py:1192, 1281]` | Add `facepalm_type_expr().label("facepalm_type")` to the paged statement only (not the count). Unpack a 7-tuple. `_build_flaw_item(..., facepalm_type=...)`. |
| `fetch_page_facepalm_scores` | returns `dict[int, dict[int, float]]`, owner side only (`player_only_gate`), `score.isnot(None)` `[VERIFIED: library_repository.py:1372-1404]` | Return `dict[int, dict[int, FacepalmChipValue]]` with `class FacepalmChipValue(NamedTuple): score: float; type: FacepalmType`. The score is non-null there, so the type is non-null. |
| `get_library_game` / `get_library_games` | `facepalm_by_ply = ...fetch_page_facepalm_scores(...)` `[VERIFIED: app/services/library_service.py:849-851, 1048-1050]` | Value type follows through `_build_card` (line 589) and `_build_eval_series` (line 169) |
| `_build_eval_series` | `facepalm_score=((facepalm_by_ply or {}).get(pos.ply) if severity == "blunder" else None)` `[VERIFIED: library_service.py:400-402]` | Set both `facepalm_score` and `facepalm_type` from the entry under the same blunder gate (keep the 253 WR-01 comment) |

Schemas: `FlawMarker.facepalm_score: float | None = None` (line 99) and `FlawListItem.facepalm_score: float | None = None` (line 246) `[VERIFIED: app/schemas/library.py:99, 246]`. Add `facepalm_type: FacepalmType | None = None` beside each. "The game-card flaw item" is `FlawMarker`, inside `GameFlawCard.flaw_markers`; `GameFlawCard` itself carries no score. Frontend: `FlawMarker.facepalm_score?: number | null` and `FlawListItem.facepalm_score: number | null` `[VERIFIED: frontend/src/types/library.ts:183, 297]`. Mirror them as `facepalm_type?: FacepalmType | null` and `facepalm_type: FacepalmType | null`.

Tests that pin the current value shape and must change:
- `tests/services/test_eval_chart_service.py:307,320` (`facepalm_by_ply={2: 0.87}`)
- `tests/test_library_repository.py:2911-2990` (`scores[game.id][ply] == approx(0.87)`)
- `tests/services/test_maia_flaw_scoring.py:2449` (uses keys only; probably unaffected)
- `tests/test_library_router.py:1538` (wiring docstring test)

### Pattern 3: Share timeline in the same walk (D-03)

Today:

```python
# [VERIFIED: app/services/library_service.py:1110] FLAW_TREND_WINDOW = 100
# [VERIFIED: app/services/openings_service.py:63] MIN_GAMES_FOR_TIMELINE = 10
```

`_compute_flaw_trend` walks rows chronologically and skips rows whose `_user_moves_from_ply_count(...) <= 0`. It keeps a trailing 100-game window, drops windows below 10 games, and writes one point per ISO week (last game of the week wins) `[VERIFIED: library_service.py:1126-1175]`. The rows come from `fetch_flaw_trend_rows`, which uses the oracle-present population (`white_/black_blunders IS NOT NULL` by user colour, `played_at`, `ply_count > 0`, `tc` not null), ordered by `played_at` `[VERIFIED: library_repository.py:1530-1608]`. The oracle columns are also written by our own eval apply `[VERIFIED: app/services/eval_apply.py:1398-1405]`, so this population is in effect the analyzed games.

**Recommended: one walk, keyed by game_id. Do not use a second independently windowed series.**
- `fetch_flaw_trend_rows` adds `Game.id` to its SELECT (and `Game.id` as an ORDER BY tie-breaker, so ties in `played_at` order deterministically).
- New `fetch_facepalm_share_counts(session, user_id, **same filters) -> dict[int, tuple[int, int]]` returns `{game_id: (scored, facepalm)}` over the user's own blunders (`player_only_gate`, `severity == _SEVERITY_INT["blunder"]` where `_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}` `[VERIFIED: app/repositories/game_flaws_repository.py:30]`), restricted to the same filtered games. Use a fenced inner subquery so the score is evaluated once per row.
- `_compute_flaw_trend(rows, share_by_game)` accumulates `scored` and `facepalm` per game in the same lists it already keeps. When it emits a point, it adds `facepalm_share = fp_w / scored_w if scored_w >= FACEPALM_SHARE_MIN_SCORED else None`, `facepalm_in_window`, and `scored_blunders_in_window`.
- `FacepalmShareChart` renders the same `trend_by_tc` points. The dates, volume bars, inactivity markers and window caption are then identical to the Flaws Timeline by construction. Leading weeks below the floor render as a gap (recharts `connectNulls: false`). Show the text fallback when fewer than 2 points have a non-null share.

This keeps the share a separate query (CONTEXT: "a new query, not an extra column on the trend rows"). The trend rows gain only `game_id`. It also avoids two failure modes: drift from the `moves <= 0` skip rule, and drift from `played_at` ties, both of which would shift window boundaries if the share walked its own row list. Payload choice: the same `/flaw-stats` response. Its only consumer is the timeline, which has its own load and error state, so the extra query does not block the tiles or the TC switch. `FlawStatsResponse` itself is unchanged (`trend_by_tc`, `trend_window`, `analyzed_n` `[VERIFIED: app/schemas/library.py:322-324]`). Only `FlawTrendPoint` grows.

**Share floor findings** (throwaway probe `temp/facepalm-257/probe_share.py` on the real `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`, read-only):

| Source | Series | Scored per game | Floor 20 binds? | Behaviour |
|---|---|---|---|---|
| dev user 28 rapid, 1,919 games | 91 points | 1.50 | never (min 45 in window) | share 17.6% to 40.0%, median 26.6%; weekly step median 1.2 pts, p90 3.7, max 9.4 |
| dev user 28 blitz, 999 games | 38 points | 1.67 | never (min 92) | median 27.5%; step median 2.1, p90 5.0, max 11.0 |
| benchmark user 277, 103 games | 12 points | 2.53 | yes, first point n=29 | first point 55%, then 39%, 37%, 36% (16-point drop) |
| benchmark user 3074, 102 games | 5 points | 3.17 | yes, n=36, then 60 | 58%, then 50%, then 39% |
| benchmark user 1668 | 8 points | 2.96 | yes, n=25 | 36%, 40%, 44% |
| benchmark users 1378, 2777 | 9 and 5 points | 2.2 to 2.6 | no (min 87 / 126) | steps under 2 pts |

`[VERIFIED: dev DB + benchmark DB probes this session]`. Blunders per game from the benchmark oracle columns: 2400 rapid 1.18, 2000 rapid 1.44, 2400 blitz 1.53, bullet 2.2 to 2.3 `[VERIFIED: benchmark DB, 1% games sample]`. So a full 100-game window always holds about 100 or more scored blunders, and the floor only acts while a TC's window is filling (10 games ≈ 12 to 30 scored). The binomial SE at p ≈ 0.3 is about 10 points at n=20, 6.5 at n=50 and 4.6 at n=100 `[ASSUMED: standard binomial formula]`. **Recommend `FACEPALM_SHARE_MIN_SCORED = 50`.** It drops the noisy first one or two points of a series and costs a thin TC (under about 25 games) its line, which falls back to the text state. The rolling-score fallback of D-03 is not needed on this evidence. Prod confirmation is an open item (§Open Questions 1).

### Pattern 4: Facepalm rows on `FlawComparisonTc` (D-11..D-13)

The machinery to reuse:
- `_paired_series(rows, player_col, opp_col)` divides both sides by the user's move count × 100, skips rows with `user_moves <= 0`, and returns deltas, rates and totals `[VERIFIED: library_service.py:1483-1509]`.
- `_paired_gap_test` gives the mean, p-value, 99% CI and significance (lines 1399-1408).
- `_build_tempo_phase_cell` shows the zoneless shape: `zone_lo/zone_hi = 0.0`, `has_zone=False` (lines 1538-1588).
- The gate is `FLAW_COMPARISON_GATE: int = 20` `[VERIFIED: library_service.py:1390]`.

Recommendation:
- **A new repository function `fetch_facepalm_comparison`.** Do not add columns to `fetch_flaw_comparison`. That function LEFT JOINs every flaw (all severities) and is already about 250 lines, and six more FILTER columns would each inline the 34 KB expression.
- **Reuse the anchor.** Extract the anchor subquery from `fetch_flaw_comparison` (lines 2028-2067) into a helper used by both, so the game sets cannot drift. Add a test asserting the same `(game_id, tc, user_moves)` set from both functions.
- **Fenced inner subquery.** `select(GameFlaw.game_id, GameFlaw.ply, score.label("s"), facepalm_type_expr().label("ftype")).where(GameFlaw.user_id == user_id, GameFlaw.severity == _SEVERITY_INT["blunder"]).offset(0)`. LEFT JOIN it on `game_id`, then six `func.count(scored.c.ply).filter(side, scored.c.s >= FACEPALM_STATS_MIN [, scored.c.ftype == ...])` columns using `is_opponent_expr(scored.c.ply, anchor.c.user_color)`.
- **Schema.** `FacepalmMetric = Literal["facepalm", "facepalm_missed_win", "facepalm_allowed_loss"]`. `FacepalmBullet` has the same fields as `FlawBullet` but `tag: FacepalmMetric`, with `has_zone=False` and `zone_lo=zone_hi=0.0`. `FlawComparisonTc.facepalm_bullets: list[FacepalmBullet]` (always 3, in that order, also below the gate like `bullets`). Do **not** extend `FlawDeltaMetric` / `FLAW_DELTA_METRICS`: they drive the 12-metric zone registry and benchmarks.
- **Invariants to test.** Per game, `player_facepalm == player_missed + player_allowed` (the type is non-null whenever the score is non-null). Same for the opponent side.

Payload choice: join `FlawComparisonTc`. You get one cache entry, the same `analyzed_n` / `below_gate`, the same TC list, and no new hook. The cost is that the whole Stats page (its TC switch reads this query) waits for the extra query: dev user 28 has a 294 ms baseline plus 50 to 69 ms fenced. If prod timing on the largest account is bad, the fallback is a separate `/library/facepalm-comparison` endpoint (§Open Questions 2).

**Opponent inputs (Q4).** `facepalm_expr` reads only `game_flaws` columns of the same row (`maia_played_prob`, `maia_reply_spread`, `played_line_material`, `line_mate_ply`, `best_line_material`, `best_line_mate_ply`, `maia_best_prob`, `maia_pre_spread`) `[VERIFIED: facepalm_score.py:600-613]`, so opponent rows score with the same expression. Prod coverage: opponent Maia columns 99.2% and line facts 93.9%, against user 99.9% and 93.8% `[CITED: .planning/seeds/SEED-261114-iuv…md "Refinement" State]`. **Dev is not representative:** user 28 has 4,557 of 5,396 own blunders scored but only 144 of 5,624 opponent blunders `[VERIFIED: dev DB probe]`, so a dev UAT would show opponents near zero.

**D-06 audit.** The drill reads `facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN` with `player_only_gate` (`blunder_check_repository.py:405-407, 656-670`). The library tag/facepalm filter EXISTS is player-gated (`library_repository.py:835`), and `query_flaws` is player-gated (line 1244). `fetch_page_facepalm_scores` is owner-side only (line 1397) `[VERIFIED: grep + reads this session]`. The new queries read opponent rows only as aggregate counts and feed no filter or selection. Leave all existing gates as they are.

### Pattern 5: Performance (Q7)

Dev user 28 (11,020 blunders on both sides, 2,840 analyzed games), best of 3, read-only `[VERIFIED: temp/facepalm-257/probe_perf*.py]`:

| Query | Time |
|---|---|
| count blunders, no expression | 12 ms |
| count `score >= 0.7` (one evaluation per row) | 53 ms |
| score + type | 74 ms |
| existing `fetch_flaw_comparison` | 294 ms |
| draft comparison, `s`/`ftype` referenced in 6 FILTERs, no fence | 135 ms |
| draft comparison, single class column, no fence | 95 to 115 ms (planning 37 ms) |
| draft comparison, `.offset(0)` fence | 50 to 69 ms (planning 2.6 ms) |
| share counts (`fetch_facepalm_share_counts` shape) | about 230 ms unfenced in the probe |

About 3.6 µs per blunder per evaluation. A 100k-blunder account would need about 0.4 s per evaluation pass `[ASSUMED: linear extrapolation]`. The plan uses `game_flaws_pkey (user_id, game_id, ply)` with `severity` as a row filter. No new index is useful: the score is query-time by design (254 D-01), and a functional index on a 34 KB expression would break on every refit. **Rules for the plans:**
- Evaluate the score (and type) once per row inside a fenced subquery.
- Bind the expression once per statement.
- Restrict the inner blunder scan to the filtered game ids.
- Never call the score in Python over many rows.

### Pattern 6: Frontend

- **Type styles in one place.** In `lib/facepalm.ts`, `FACEPALM_TYPE_STYLE: Record<FacepalmType, { color; bg; border }>` maps `missed_win → TAC_MISSED / TAC_MISSED_BG / TAC_MISSED`(or `_BORDER`) and `allowed_loss → TAC_ALLOWED / TAC_ALLOWED_BG / TAC_ALLOWED_BORDER`. `TacticMotifChip` uses the full colour as the missed border and `TAC_ALLOWED_BORDER` for allowed (`TacticMotifChip.tsx:196-205`). Theme values: `TAC_MISSED = 'oklch(0.70 0.15 200)'`, `TAC_MISSED_BG = 'oklch(0.70 0.15 200 / 0.15)'`, `TAC_MISSED_BORDER = 'oklch(0.70 0.15 200 / 0.30)'`, `TAC_ALLOWED = 'oklch(0.60 0.22 10)'`, `TAC_ALLOWED_BG = 'oklch(0.60 0.22 10 / 0.15)'`, `TAC_ALLOWED_BORDER = 'oklch(0.60 0.22 10 / 0.30)'` `[VERIFIED: frontend/src/lib/theme.ts:265-274]`. Add `FACEPALM_TYPE_LABEL` ("Missed win" / "Allowed loss") and the two D-10 sentences there too.
- **FacepalmChip / FacepalmMoveChip.** Take a required `type: FacepalmType` and style from the map. Callers render the chip only when both score and type are non-null (`FlawCard.tsx:359`, `VariationTree.tsx:131`, `useAnalysisGemMarkers.ts:352`, where `FlawMarkerEntry` gains `facepalmType`).
- **FacepalmExplanation.** Gains a required `type` prop and adds a line such as "**Missed win:** the best move won material that was not taken." The two sentences are mover-neutral, so `byOpponent` needs no type variant. In practice opponent markers never carry a score today (owner-side reader), so the "their level" path stays latent. `FacepalmBadgePopover` passes `type`. Make the aria-label include it ("Facepalm 94%, allowed loss") so assistive tech does not rely on colour.
- **EvalChart tooltip line** (`EvalChart.tsx:1192-1201`, `data-testid="eval-chart-tooltip-facepalm"`). Colour by type via `style={{ color }}`, matching the tactic lines that already colour `missed:` / `allowed:` (lines 1210-1216). See Open Question 3 on naming the type there.
- **Remove `FACEPALM_CHIP` / `FACEPALM_CHIP_BG`.** Today: `export const FACEPALM_CHIP = FAM_NEUTRAL;` and `export const FACEPALM_CHIP_BG = FAM_NEUTRAL_BG;` `[VERIFIED: theme.ts:195-196]`, and their only consumers are the two chips. Knip has `ignoreExportsUsedInFile: true`, so both exports become dead and **knip fails** unless they are deleted (with their comment). Add a named share-line colour constant in `theme.ts` for the new chart.
- **FacepalmShareChart.tsx.** Copy the `FlawTrendChart` structure: `Card` + `CardHeader size="compact"` "Facepalm share of blunders", one `Line` (`dataKey="facepalm_share"`), the `bars` axis with `domain [0, barMax*5]`, `inactivityGapReferenceLines`, and the caption "last {windowSize} games · rolling window". Y axis: percent, domain fitted to the non-null shares with padding, tick formatter `${Math.round(v*100)}%`. Tooltip: date, share, "{facepalm} of {scored} scored blunders", "{n} in window". It has a single series and no legend, so there is no toggle event. An optional `InfoPopover` (`testId="facepalm-share-info"`) is tracked automatically. Testids: `facepalm-share-chart`, `facepalm-share-composed-chart`, `facepalm-share-volume-bars`, `facepalm-share-empty`. Mount it in `FlawTimeline` (`LibraryStatsSections.tsx`) directly under `FlawTrendChart`, sharing the same `stats` load/error branches.
- **FacepalmCard.tsx.** A `Card` with header "Facepalm blunders", an intro `<p className="text-sm text-muted-foreground">` (D-16 sentence) and three `GapRow`s. Testids follow the context pattern: card `context-card-facepalm`, rows `context-row-facepalm`, `context-row-facepalm-missed-win`, `context-row-facepalm-allowed-loss`, popovers `gap-popover-{segment}-tc-{tc}`. These normalise to `popover-open` targets such as `gap-popover-facepalm-tc` via `popoverTargetFromTestId`, which drops the TC word after `tc` (`analytics.ts:619-633`). No `FeatureEventMap` change is needed. Placement: render it inside the `ContextTagCards` grid after the second row, a single column on lg, stacked last on phones. That leaves the heatmap slot and card order untouched. A lone half-width card in row 3 is acceptable; the alternative of spanning both columns stretches three short rows.
- **Meta.** Add `FACEPALM_GAP_META: Record<FacepalmMetric, FlawGapMeta>` with the D-14 labels and D-15 hints. Build the "70%" from an exported `FACEPALM_HIGH_CUTOFF` (today a private `const FACEPALM_HIGH_CUTOFF = 70;` `[VERIFIED: frontend/src/lib/facepalm.ts:33]`) so the hint and the High preset cannot drift. Use nouns such as "facepalm blunders", "missed-win facepalm blunders" and "allowed-loss facepalm blunders". `flawBulletToGapCell(b: Omit<FlawBullet, 'tag'>)` already accepts the `FacepalmBullet` shape.

### Anti-Patterns to Avoid

- **Computing the type or score in Python for payloads.** Readers must use the SQL twin (254 D-01: chip and filter read one expression).
- **Referencing the unfenced score expression in several FILTERs.** Each reference re-evaluates about 34 KB of SQL per row and adds planning cost.
- **Adding facepalm metrics to `FlawDeltaMetric`.** That breaks the zone registry and the benchmark generator contracts.
- **A per-game-share mean on the timeline** (D-03 says pooled).
- **Any chart or row that sets missed-win against allowed-loss** (D-04).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Paired rates, CI, p-value | new stats code | `_paired_series` + `_paired_gap_test` | Owns the user-move denominator rule; CI z = 99% |
| Rolling window / ISO weeks | a second walker | extend `_compute_flaw_trend` | The x-axes must match point for point |
| Score / loss / missed | re-derived formulas | `facepalm_expr`, `_loss_sql`, `_missed_sql`, `material_loss`, `material_missed` | Twin parity is already pinned |
| Filter population | ad-hoc WHERE | `_filtered_games_base` / the shared anchor helper | CLAUDE.md single filter implementation |
| Gap bar / popover | a new bar | `GapRow`, `GapBar`, `GapPopover`, `flawBulletToGapCell` | D-11 |
| Reader test seeding | stored scores | `tests/facepalm_seed.py` (`facepalm_fact_columns`, `seed_flaw_rows`) | Readers compute from facts (254 D-01) |

## Runtime State Inventory

Not a rename or migration phase, and no DB schema change: the type is query-time. Stored data: none. Live service config: none. OS-registered state: none. Secrets: none. Build artifacts: none. The frontend generated files are unaffected (see Q6 below).

## Common Pitfalls

### Pitfall 1: Type set while the score is NULL
**What goes wrong:** A chip-less row carries a type, or a type shows with no score.
**Why:** The type is NULL only when the loss is unknown, while the score is also NULL for a missing played probability, spread or (pure misses) best-move probability. 244 of 11,020 dev rows hit this.
**Avoid:** Null the type wherever the score is NULL, in every reader, and add a reader test with such a row.

### Pitfall 2: Inlined expression per FILTER
**What goes wrong:** The comparison and share queries get 2 to 6 times slower, and planning takes 30+ ms.
**Avoid:** Use a fenced subquery (`.offset(0)` renders `LIMIT ALL OFFSET 0`, and the fence was confirmed by timing). Reference output columns only.

### Pitfall 3: Zoneless significant cells get coloured
**What goes wrong:** `effectiveVerdict` returns better/worse for `hasZone=false` cells whose CI excludes 0 `[VERIFIED: frontend/src/lib/gapBar.ts:113-122]`, and the `GapBar` dot and words turn green or red. This violates D-13. CONTEXT's phrase "like tactic rows without a viable band" is therefore slightly off: those rows do colour.
**Avoid:** Add `noVerdict?: boolean` (or similar) to `GapCell`. `effectiveVerdict` returns null for it, and the heatmap and popover read the same function. Test that a significant facepalm cell renders neutral.

### Pitfall 4: Copy that states what higher means
**What goes wrong:** `GapPopoverBody` always renders "`{definition}`. Fewer is better.", and `ContextTagCard` ends with a better/worse axis caption (`GAP_AXIS_LABELS`). D-16 bans "a sentence on what a higher rate means". The zoneless range line only appears when there is a verdict, and its copy names "tactic".
**Avoid:** Add GapPopover props to drop "Fewer is better." and to always show "There is no typical range for facepalm blunders yet." Significance may be stated (e.g. reuse `COPY_CHANCE` for a non-significant gap, or "The gap is too large to be chance." for a significant one). Omit the better/worse caption on the Facepalm card. This is an interpretation, so confirm it (Assumptions A2).

### Pitfall 5: Knip and tsc fallout
- `FACEPALM_CHIP*` become dead exports and must be deleted.
- `frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts` is not a `.test.*` file, so `tsc -b` compiles it (`tsconfig.app.json` excludes only `*.test.ts(x)`). New required fields on `FlawComparisonTc` / `FlawTrendPoint` break `npm run build` until the fixtures are updated.
- Exporting `FACEPALM_HIGH_CUTOFF` requires a real importer.

### Pitfall 6: Response-shape pins in backend tests
`tests/services/test_library_service.py:908-912` asserts `set(FlawStatsResponse.model_fields) == {"trend_by_tc", "trend_window", "analyzed_n"}`. It stays green if only `FlawTrendPoint` grows (the recommended design). `test_flaw_comparison.py:868` pins `TempoPhaseCell` against `FlawBullet` fields. If `FacepalmBullet` copies `FlawBullet`, add a similar parity test.

### Pitfall 7: The 70% cut and the High preset
The filter clause is `score >= min_pct / _FACEPALM_PCT_SCALE` with `_FACEPALM_PCT_SCALE: float = 100.0` `[VERIFIED: library_repository.py:90, 361]`. `70 / 100.0` and `0.7` are the same double, so a row counts at `FACEPALM_STATS_MIN = 0.7` exactly when it passes the High (70-100) filter. Add a test that pins `FACEPALM_STATS_MIN == 70 / 100.0` so the "open exactly the blunders a row counts" promise holds.

### Pitfall 8: Seeds produce one type by accident
`facepalm_fact_columns` searches `played_3` from 0 down with a NULL best line. High targets end with `played_3 < 0` (loss > 0 → allowed loss), while a no-loss seed is a missed win. Type-asserting tests need an explicit `facepalm_type=` option in the seed helper. A missed-win facepalm (no loss, best line with gain, best-move probability) can reach about 0.96 under the shipped model `[ASSUMED: hand computation from the verbatim coefficients]`, so a `>= 0.7` missed-win seed is feasible.

### Pitfall 9: Dev UAT shows opponents at about zero
Opponent facts are barely filled on dev (2.6% for user 28). A dev screenshot of the Facepalm card is not a valid read. Use prod, or first run the opponent backfill for user 28 on dev (`scripts/backfill_maia_flaws.py --db dev --mode opponent --user-id 28`, then the line pass). This writes dev data, so it is an operator step and is not required for the gate.

## Code Examples

### Fenced per-blunder subquery (pattern verified on dev)
```python
# Source: temp/facepalm-257/probe_perf2.py (throwaway, read-only); timing in §Pattern 5
score = facepalm_expr(FACEPALM_LIBRARY_LAMBDA)
scored = (
    select(GameFlaw.game_id, GameFlaw.ply, score.label("s"), facepalm_type_expr().label("ftype"))
    .where(GameFlaw.user_id == user_id, GameFlaw.severity == _SEVERITY_INT["blunder"],
           GameFlaw.game_id.in_(select(anchor.c.game_id)))
    # Fence: without it Postgres pulls the subquery up and re-evaluates the score per FILTER.
    .offset(0)
    .subquery("facepalm_scored")
)
opp = is_opponent_expr(scored.c.ply, anchor.c.user_color)
is_fp = scored.c.s >= FACEPALM_STATS_MIN
cols = [
    func.count(scored.c.ply).filter(~opp, is_fp).label("player_facepalm"),
    func.count(scored.c.ply).filter(opp, is_fp).label("opp_facepalm"),
    func.count(scored.c.ply).filter(~opp, is_fp, scored.c.ftype == "missed_win").label("player_facepalm_missed_win"),
    # ... opp_ missed, player_/opp_ allowed_loss
]
```

### Type parity test (pattern of the existing twin tests)
Reuse `_grid()`, `_aggregate_grid()`, `_EXTREME_ROWS` and the `VALUES` builder of `_sql_scores` in `tests/services/test_facepalm_score.py:281-354, 572-625`. Swap `facepalm_score_sql` for `facepalm_type_sql` and assert `sql_type == facepalm_type(_facts_of(row), model=model)` (string equality). Require that the run saw at least one `None`, one `"missed_win"`, one `"allowed_loss"`, one tie row (`loss == missed > 0` → allowed) and one no-material row (→ missed win). Parametrize over `_MATERIAL_MODELS` / `_AGGREGATE_INPUTS` and `FACEPALM_MODEL`. Add a stored-facts version like `test_expr_matches_python_twin_over_stored_facts` (line 1024).

## State of the Art

| Old | Current | Impact |
|---|---|---|
| Neutral white facepalm chip (`FACEPALM_CHIP*`, 253) | Type-tinted chip (D-08/D-09) | Delete the constants |
| Opponent blunders unscored (250 D-06) | Scored on prod (Part A) | The paired comparison becomes possible; readers stay owner-gated |
| Seed "per game" rate | Per 100 user moves (D-12) | Reuse `_paired_series` unchanged |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Floor 50 (not 20) is the better share floor | Pattern 3 | Low: 20 shows jumpy first points; 50 hides thin-TC lines. Owner may prefer 20 or 30. |
| A2 | "Fewer is better." and the better/worse caption count as "what a higher rate means" (D-16) and are dropped for facepalm rows | Pitfall 4 | Medium: copy churn at UAT if the owner wants them kept |
| A3 | Prod cost scales linearly (about 3.6 µs per blunder per evaluation) | Pattern 5 | Medium: a slow comparison delays the whole Stats page; mitigated by the fence or a split endpoint |
| A4 | A missed-win facepalm seed can reach >= 0.7 under the shipped model | Pitfall 8 | Low: the seed helper raises ValueError if not |
| A5 | Binomial SE figures | Pattern 3 | None (textbook) |
| A6 | Eval-chart tooltip needs the type named in text (colour never the only signal) | Open Q3 | Low |

## Open Questions

1. **Share floor on prod (orchestrator, read-only).**
   - What we know: dev has one scored user, and the benchmark has about 100-game scored users only.
   - Recommendation: run `temp/facepalm-257/prod_share_probe.sql` (self-contained, compiled from the real `facepalm_expr`, already checked on dev, where it reproduced the Python probe: 91/38 points and medians of 26.6%/27.5%) via the prod MCP. It covers the 15 accounts with the most analyzed games, per TC, and reports points at floor 20 vs 50, median/p90/max weekly step, and max step below vs at-or-above 50 scored. Expect 1 to 3 s.
   - If `max_step_below50` is routinely above about 0.08 while `max_step_at_or_above50` stays under about 0.06, keep 50.
2. **Comparison latency on the largest prod account.**
   - Recommendation: run `EXPLAIN (ANALYZE, BUFFERS)` on `temp/facepalm-257/prod_comparison_probe.sql` after replacing `987654321` with the largest account's id.
   - If the fenced query exceeds about 1 s, move the facepalm rows to their own endpoint so the TC switch does not wait.
3. **Eval-chart tooltip.** D-10 names the type in the popover, but the tooltip has no popover. Recommendation: "Facepalm 95% · allowed loss" (lowercase, like the tactic lines "allowed: fork"). Confirm, or keep colour plus the chip popovers elsewhere.
4. **Dev UAT data.** Do you want the opponent backfill for user 28 on dev (Pitfall 9) before UAT, or UAT on prod after deploy?

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (`flawchess-dev-db-1`) | tests, probes | ✓ | PG 18 (healthy) | — |
| Benchmark DB (`flawchess-benchmark-db-1`) | research only | ✓ | healthy | — |
| Python / uv | backend | ✓ | 3.14.3 | — |
| Node / vitest | frontend | ✓ | 24.19.0 / 5.1.0 | — |
| Prod DB | Open Q1/Q2 | ✗ for subagents | — | orchestrator MCP |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist); vitest 5.1.0 + Testing Library |
| Config file | `pyproject.toml [tool.pytest.ini_options]`; `frontend/vite*.config` |
| Quick run command | `uv run pytest tests/services/test_facepalm_score.py tests/services/test_flaw_comparison.py -x` / `cd frontend && npx vitest run src/components/library` |
| Full suite command | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Decision → Test Map
| Decision | Behavior | Type | Command | Exists? |
|---|---|---|---|---|
| D-01 | `FACEPALM_STATS_MIN == 0.7 == 70/100.0`, separate from `FACEPALM_SCORE_MIN` | unit | `pytest tests/services/test_facepalm_score.py -k stats_min` | ❌ W0 |
| D-02 | Type twin parity (grid, aggregate grid, extreme rows, stored facts), tie → allowed, no material → missed, unknown loss → None | unit + DB | `pytest tests/services/test_facepalm_score.py -k type` | ❌ W0 |
| D-02 | Type is lambda-free (same at lam 0 and 1) | unit | same | ❌ W0 |
| D-08 | `query_flaws` returns the type; type None when score None | repo | `pytest tests/test_library_repository.py -k facepalm` | extend |
| D-08 | `fetch_page_facepalm_scores` returns (score, type), owner side only | repo | `pytest tests/test_library_repository.py -k FetchPageFacepalm` | extend |
| D-08 | `_build_eval_series` sets type only on blunders | unit | `pytest tests/services/test_eval_chart_service.py -k facepalm` | extend |
| D-03 | Share pooled over the window; same dates as the trend; null below the floor; unscored excluded; user side only | unit + DB | `pytest tests/services/test_library_service.py -k facepalm_share` | ❌ W0 |
| D-12 | Facepalm rows paired per 100 user moves; `player_rate - opp_rate == delta`; total = missed + allowed; same anchor game set as `fetch_flaw_comparison`; below-gate keeps bullets | DB | `pytest tests/services/test_flaw_comparison.py -k facepalm` | ❌ W0 |
| D-13 | `has_zone False`, zones 0.0; significant flag computed | unit | same | ❌ W0 |
| D-06 | Drill / filter readers unchanged (existing gate tests stay green) | regression | `pytest tests/repositories/test_blunder_check_repository.py tests/test_query_utils.py` | ✅ |
| D-08/09 | Chip, mini-chip and tooltip line take type colours; no `FACEPALM_CHIP*` | component | `npx vitest run src/components/library/__tests__/FlawCard.test.tsx src/components/analysis/__tests__/VariationTree.test.tsx` | extend |
| D-10 | Explanation names the type (both variants) | component | `npx vitest run src/components/library/__tests__/FacepalmExplanation.test.tsx` | extend |
| D-13 | Significant facepalm cell renders neutral | unit | `npx vitest run src/lib/__tests__/gapBar.test.ts` | extend |
| D-14..16 | Labels, hints with 70%, intro, popover "no typical range", no "Fewer is better." | component | `npx vitest run src/components/library/stats/__tests__/GapPopover.test.tsx` | extend; FacepalmCard test ❌ W0 |
| D-03 | Share chart: renders, text fallback below 2 non-null points, tooltip counts | component | `npx vitest run src/components/library/__tests__/FacepalmShareChart.test.tsx` | ❌ W0 |
| D-11 | Card behind the gate, follows the TC switch | component | `npx vitest run src/components/library/stats/__tests__/LibraryStatsSections.test.tsx` | extend |

### Sampling Rate
- **Per task commit:** the quick commands of the touched area.
- **Per wave merge:** `uv run pytest -n auto -x` plus `npm test -- --run`.
- **Phase gate:** the full pre-merge gate from CLAUDE.md (ruff, ty ×2, function-size, pytest, frontend lint/build/test/knip).

### Wave 0 Gaps
- [ ] `tests/facepalm_seed.py`: a `facepalm_type=` option on `facepalm_fact_columns` (missed-win seeds at >= 0.7), plus `tests/services/test_facepalm_seed.py` coverage
- [ ] Type-twin parity tests in `tests/services/test_facepalm_score.py`
- [ ] Facepalm comparison and share tests in `tests/services/test_flaw_comparison.py` / `tests/services/test_library_service.py`
- [ ] `FacepalmShareChart.test.tsx`, `FacepalmCard.test.tsx`; update `stats/__tests__/flawStatsFixtures.ts`

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (existing `current_active_user`) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | `user_id` from the auth dependency only; every new query scopes `GameFlaw.user_id == user_id` and `Game.user_id == user_id` (IDOR). Add a two-user isolation test like `test_two_user_isolation`. |
| V5 Input Validation | yes (no new params) | Existing Query validators; `Literal` response fields |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---|---|---|
| Cross-user aggregate leak | Information disclosure | user_id scoping on both the anchor and the inner blunder scan |
| Opponent scores leaking into selection or filters | Tampering / integrity of D-06 | No change to the gated readers; the new readers are aggregate-only |
| Expensive query as DoS on large accounts | Denial of service | Fence, single evaluation, filtered inner scan; prod EXPLAIN (Open Q2) |

## Generated files (Q6)

None need regenerating. `scripts/gen_flaw_thresholds_ts.py` emits only `flaws_service` / `eval_utils` constants, and no `gen_*.py` registry covers facepalm, `FLAW_DELTA_METRICS` or the share. They would only change if the planner chose to emit `FACEPALM_STATS_MIN` to TS. Recommendation: do not; derive the hint from the frontend `FACEPALM_HIGH_CUTOFF` and pin the backend constant by test.

## Sources

### Primary (HIGH confidence)
- Read this session: `app/services/facepalm_score.py`, `app/services/facepalm_material.py`, `app/services/blunder_check_rules.py:40-135`, `app/repositories/library_repository.py` (lines 80-110, 325-365, 975-1405, 1530-2254), `app/services/library_service.py` (lines 160-215, 380-410, 580-712, 840-885, 1040-1290, 1385-1834), `app/schemas/library.py`, `tests/facepalm_seed.py`, `tests/services/test_facepalm_score.py` (selected ranges), the frontend files named in Pattern 6, `frontend/knip.json`, `frontend/tsconfig.app.json`
- Read-only probes on the dev and benchmark DBs: `temp/facepalm-257/probe_*.py`, `gen_prod_*_sql.py` (gitignored)

### Secondary (MEDIUM)
- `.planning/seeds/SEED-261114-iuv-facepalm-rate-library-stats.md`: prod coverage and type-split measurements (not re-measured)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies)
- Architecture: HIGH (all seams read; twin draft validated on real rows)
- Pitfalls: HIGH for the code-derived ones (verdict colouring, knip, tsc fixtures, NULL-score type); MEDIUM for the copy interpretation (A2)
- Share floor: MEDIUM (no prod data; open item 1)

**Research date:** 2026-11-20
**Valid until:** 2026-12-20, or until the next facepalm refit (the constants move the type split)
