# Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich each **analyzed** Library → Games subtab card with a per-game
**expected-score eval chart** — a recharts area chart of white-perspective ES
per ply (lichess sigmoid via `eval_utils`), with a 50% midline, the advantage
region shaded (light grey >50% / dark grey <50%), **both players' flaws** marked
as colored dots, vertical phase-transition lines, and per-ply tooltips. The
chart becomes a **dedicated middle column** that restructures the desktop card
into three equal thirds (miniboard + info · eval chart · tags); mobile stacks
the same three blocks. The per-ply series + sparse flaw markers + the (≤2)
phase-transition plies are delivered **inline** by extending the existing
`GET /api/library/games` `GameFlawCard` payload — **no new endpoint, no schema
change, no migration**. Unanalyzed cards keep the existing `NoAnalysisState`
pill and render no chart.

**SCOPE EXPANSION (2026-06-07, owner-directed):** the chart shows **both
players'** blunders/mistakes/inaccuracies, not just the user's — **filled
circles = the player (you), hollow circles = the opponent**, color by severity.
B/M tooltips show tags for **both** players. This **amends** the original
ROADMAP/LIBG-10 "dots = your flaws only" + "opponent-move classification out of
scope" framing. It is served **on the fly** (see D-02/D-10) — `game_flaws` is
NOT expanded and stays user-M+B-only ("keep it narrow", owner-confirmed).

**Heavily pre-specified, but the UI-SPEC now needs an amendment.** The frontend
contract is in `109-UI-SPEC.md` (created 2026-06-07 via `/gsd-ui-phase`), but it
was written for **user-only filled dots**. The dual-marker scheme (filled vs
hollow, 6 dot styles, opponent B/M tooltip tags, density tuning) is NOT yet in
the UI-SPEC — the planner/UI-spec must reconcile (see D-07..D-09). Everything
else in the UI-SPEC (layout, recharts pattern, gradient shading, theme
constants, dims, ARIA) still holds.

**Out of scope** (separate later phases, per SEED-036): the Analysis detail
viewer, the on-demand best-move endpoint, any new persisted columns, and any
**cross-game** query/filter over opponent or inaccuracy flaws (that would be the
trigger to materialize — see Deferred).

</domain>

<decisions>
## Implementation Decisions

### Flaw dot detection (all severities, BOTH colors, on the fly)
- **D-01 (reuse the mover-POV kernel for both colors, NOT a white-perspective
  re-derivation):** All flaw markers — B/M/I for **both** the player and the
  opponent — are detected by reusing `flaws_service.py`'s existing **mover-POV**
  drop logic (`_run_all_moves_pass` → `_classify_severity`; bands
  `INACCURACY_DROP=0.05` / `MISTAKE_DROP=0.10` / `BLUNDER_DROP=0.15`).
  `_run_all_moves_pass` already classifies **both colors** in one pass, so this
  is a direct reuse, not new logic. This is consistent across player/opponent,
  is **correct for the black player**, and has zero drift. The ROADMAP/LIBG-10
  wording "white-perspective ES-drop ∈ [0.05, 0.10)" is **loose** — the drop is
  mover-POV in the actual kernel, and this phase follows the kernel. Mate
  handling in the drop math follows the kernel's cp-equivalent path
  (`_ply_to_es`), NOT `eval_mate_to_expected_score` (Pitfall 3: no hard 1.0/0.0
  for drop math).

### Flaw dot sourcing & tooltip content
- **D-02 (chart dots come from a single on-the-fly classify pass, NOT from
  `game_flaws`):** The chart builder computes ALL dots (both colors, B/M/I) from
  one on-the-fly pass over `game_positions` for each of the 20 paginated games —
  it does NOT read dots from `game_flaws`. Rationale: opponent flaws and
  inaccuracies aren't in `game_flaws` anyway, so the kernel must run regardless;
  running it once for everything is simpler than mixing `game_flaws` (player B/M)
  + on-the-fly (opponent B/M + all I), avoids a merge/join, and is **more robust
  against a stale `game_flaws`** (e.g. threshold change before a backfill).
  `game_flaws` keeps its own job — backing the Games chips/filter + Flaws subtab
  (Phase 108 D-02). The two agree because they use the same kernel + thresholds.
- **D-03 (B/M tooltips show tags for both players; inaccuracies show none):** B/M
  dot tooltips (player AND opponent) show severity + tags, computed on the fly
  via `_build_tags(...)` — **verified FEN-free** (it reads `positions` +
  `all_moves` + game `result`/`increment`/`base_time_seconds`; the FEN map is
  only used by the miniboard, which the chart doesn't render). Inaccuracy
  tooltips (player AND opponent) show severity + eval only, **no tags** — the
  builder does not enrich inaccuracies.
  **GRAY AREA for researcher/planner:** `_build_tags` is currently only ever
  called for the user's own moves, and some tags are **user-framed**
  (`result-changing`, `miss`, `lucky-escape`) vs **mover-framed** (`low-clock`,
  `impatient`, `considered`, `while-ahead`). For OPPONENT B/M, decide which tags
  are mover-relative (describe the opponent's move — most should be) vs which are
  meaningless/misleading from the opponent's side, and adjust the call so an
  opponent dot's tags describe the opponent's move, not the user's. Do not ship
  user-framed tags mislabeled onto opponent moves.

### Both-players marker scheme & tooltip labeling (scope expansion)
- **D-07 (filled = player, hollow = opponent; color = severity):** Player flaws
  render as **filled** circles, opponent flaws as **hollow** (stroke-only)
  circles. Fill/stroke color is the severity color
  (`SEV_BLUNDER`/`SEV_MISTAKE`/`SEV_INACCURACY` from `theme.ts`) for both — 6 dot
  styles total (3 severities × player/opponent). Player vs opponent is decided
  by `mover_color == game.user_color`. **UI-SPEC amendment required** (it
  currently specs filled-only, user-only).
- **D-08 (tooltip labels "You" / "Opponent"):** Because the tooltip is text-only
  and can't show the fill style, the severity line is qualified — e.g.
  "You · Blunder" / "Opponent · Mistake". Applies to all dot tooltips.
- **D-09 (density — keep all, tune in implementation):** Show every flaw for both
  players, including the wide inaccuracy band. The compact 80–96px sparkline gets
  denser than the original user-only design; the UI-SPEC update / executor tunes
  dot radii + opacity for legibility (e.g. inaccuracies smaller/lighter; hollow
  strokes thin) during visual UAT. Accept some density as the cost of
  completeness. No data dropped.

### `game_flaws` stays narrow (owner-confirmed despite the new consumer)
- **D-10 (do NOT materialize opponent or inaccuracy flaws):** Even though the
  chart is now a consumer of opponent B/M and inaccuracies, `game_flaws` is NOT
  expanded — no opponent rows, no inaccuracy rows, no schema change, no
  migration, no backfill. Governing principle: **materialize only what must be
  indexed/filtered at query time; derive per-game display on the fly.** The chart
  is per-game display (reads one game, renders), not a cross-game filter — so on
  the fly is correct and cheap (no extra I/O beyond the per-ply query the chart
  already needs; FEN-free). Materialization would only be warranted by a future
  **cross-game** filter/query consumer (see Deferred revisit triggers).

### Dual perspective in the chart-series builder
- **D-04 (line is white-perspective, detection is mover-POV):** The chart
  **line** plots white-perspective ES per ply
  (`eval_cp_to_expected_score(cp, user_color="white")`; mate via
  `eval_mate_to_expected_score(..., "white")` → hard 1.0/0.0, per criterion #2).
  Inaccuracy **detection** uses mover-POV drops (D-01). Both are computed in the
  same builder from the same `game_positions` per-ply rows. Do not conflate the
  two perspectives. The tooltip eval is white-perspective `eval_cp/100` (or
  "mate in #N"), matching the line.

### Inline payload shape & size (criterion #6 — no perceptible regression)
- **D-05 (typed `EvalPoint[]` + rounded ES, rely on gzip):** Ship the UI-SPEC's
  typed `EvalPoint[]` array-of-objects contract as-is (do NOT invent a columnar
  wire format). Round ES floats to ~3 decimal places (the chart is ≤96px tall;
  more precision is wasted). Rely on HTTP gzip to compress the repeated object
  keys. The planner should **verify** the gzipped payload delta against the
  existing `/library/games` response is negligible; only revisit a more compact
  encoding if that measurement shows a real regression.
  **`FlawMarker` extension (scope expansion):** the UI-SPEC's
  `FlawMarker { ply, severity, tags }` must gain an **owner discriminator**
  (e.g. `is_user: boolean` or `mover: 'white'|'black'` + compare to user_color)
  so the frontend can render filled (player) vs hollow (opponent) and label the
  tooltip (D-07/D-08). Opponent B/M carry `tags`; all inaccuracies carry empty
  `tags` (D-03). Marker count grows (both colors, all severities) but stays
  sparse relative to the per-ply ES series, so the payload impact is minor.

### Phase-transition lines (resolve ROADMAP ↔ UI-SPEC conflict)
- **D-06 (no ply-0 line; at most two transition lines):** ROADMAP/LIBG-10 list
  "the opening (ply 0) / middlegame / endgame transitions" (implies 3 lines).
  The newer `109-UI-SPEC.md` overrides this: the opening boundary (ply 0) is
  **implicit** (the chart starts at ply 0) and gets **no** ReferenceLine —
  a line at the leftmost pixel is invisible/redundant. Draw **at most two**
  vertical lines: middlegame (first ply with `phase==1`) and endgame (first ply
  with `phase==2`), from `game_positions.phase`. A transition that never occurs
  draws no line. **This phase follows the UI-SPEC**, amending the ROADMAP's
  literal "opening (ply 0)" mention.

### Claude's Discretion (planner / researcher to settle)
- **N+1 avoidance:** the per-ply data for all 20 paginated games must be fetched
  without N+1 — a single batched query over `game_positions`
  (`WHERE game_id IN (...) ORDER BY game_id, ply`). Beyond `eval_cp` / `eval_mate`
  / `phase` (line + tooltip + transitions), the **tag pass also needs the clock
  columns** (`clock_after` / move-time, whatever `_build_tags` consumes) — select
  them in the same query. The 20 `Game` rows (`result`, `user_color`,
  `base_time_seconds`, `increment_seconds`, `time_control_str`) are also needed
  by `_build_tags`; they're already loaded by the Games-list query. Confirm the
  seam and verify the query plan on dev.
- **Where the builder lives:** reuse `flaws_service` helpers (`_run_all_moves_pass`
  + `_build_tags`, both FEN-free) over a lean ES-series builder reading
  `game_positions` directly. Avoid `classify_game_flaws` itself — it does a PGN
  replay for FENs the chart doesn't need; call the FEN-free pieces. Keep a single
  drop-math source of truth. Per-page cost is ~20 classify passes (bounded, after
  pagination) — distinct from the cross-archive filter path Phase 108 D-02 moved
  off; verify it adds no perceptible latency to `GET /library/games`.
- **Missing-eval plies:** the line breaks (`connectNulls={false}`, locked by
  UI-SPEC); the builder emits `es: null` for plies with absent eval. Confirm the
  ≥90% coverage gate keeps gaps rare (≤10%).
- **Recharts Scatter-vs-custom-dot** for flaw dots — UI-SPEC flags this as an
  executor-validated fallback (Scatter in ComposedChart vs a custom `dot` render
  prop); identical visual result either way.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked design contract (read first)
- `.planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-UI-SPEC.md`
  — the FULL frontend/visual lock: three-equal-thirds desktop grid + mobile
  stacking, the new `frontend/src/components/library/EvalChart.tsx` component
  contract (props, `EvalPoint`/`FlawMarker`/`PhaseTransitions` types), recharts
  architecture (`ComposedChart`/`AreaChart`, `isAnimationActive={false}`, no
  CartesianGrid/axes), the two-region vertical-gradient shading strategy, the
  new `theme.ts` constants to add (`EVAL_CHART_AREA_WHITE_AHEAD/BLACK_AHEAD`,
  `EVAL_CHART_LINE/MIDLINE/PHASE_LINE`), chart dims (`h-24`/`h-20`), the
  midline + phase-transition ReferenceLine specs, flaw-dot sizes/colors, the
  tooltip layout/copy contract, `connectNulls={false}` (break the line on null),
  and `data-testid`/ARIA. **Note D-06 here resolves the ROADMAP↔UI-SPEC ply-0
  line conflict in favor of this UI-SPEC.** **NEEDS AMENDMENT** for the
  2026-06-07 scope expansion: it specs user-only filled dots; the dual-marker
  scheme (filled player / hollow opponent, opponent B/M tooltip tags,
  "You/Opponent" label, density tuning) is captured in D-07/D-08/D-09 and must be
  folded into the UI-SPEC or the plan.

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — **LIBG-10** (the single requirement for this
  phase). Note its "white-perspective ES-drop" wording for inaccuracies is loose;
  D-01 follows the mover-POV kernel.
- `.planning/ROADMAP.md` §"Phase 109" — goal, 7 success criteria, scope notes.
- `.planning/seeds/SEED-036-library-page-milestone.md` — milestone context;
  this phase realizes the per-card eval sparkline deferred in Phase 107. Analysis
  detail viewer + best-move endpoint deferred here.

### Backend (the builder targets)
- `app/services/eval_utils.py` — `eval_cp_to_expected_score(cp, user_color)`
  (white-perspective for the line) and `eval_mate_to_expected_score(mate,
  user_color)` (→ 1.0/0.0); `LICHESS_K = 0.00368208`. Reuse, do not re-derive
  the sigmoid.
- `app/services/flaws_service.py` — `_run_all_moves_pass` (mover-POV per-ply
  severity for **both colors**, the kernel D-01 reuses for all chart dots),
  `_build_tags` (FEN-free B/M tag computation D-03 reuses for both players — note
  its user-framed vs mover-framed tag gray area), `_ply_to_es` (mate→cp-equivalent
  for drop math, Pitfall 3), `_classify_severity`, thresholds
  `INACCURACY_DROP=0.05` / `MISTAKE_DROP=0.10` / `BLUNDER_DROP=0.15`.
  `classify_game_flaws` is the full path (PGN replay for FENs) — the chart should
  call the FEN-free pieces, not this.
- `.planning/notes/flaw-tag-naming.md` — the tag taxonomy + tag→family mapping
  (low-clock / impatient / considered / miss / lucky-escape / while-ahead /
  result-changing / opening / middlegame / endgame); needed to reason about which
  tags are mover-framed vs user-framed for opponent B/M (D-03 gray area).
- `app/services/library_service.py` — the Games-list builder this phase extends
  with the inline per-ply series (Phase 108 D-02 migrated it onto `game_flaws`).
- `app/schemas/library.py` — `GameFlawCard` / `LibraryGamesResponse`; add the
  `eval_series` / `flaw_markers` / `phase_transitions` fields here.
- `app/routers/library.py` — `APIRouter(prefix="/library")`, `GET /games`
  (extended in place; no new route).

### Data sources
- `game_positions` — per-ply `eval_cp` / `eval_mate` / `phase` (white-perspective)
  **plus clock columns** (`clock_after` / move-time): the source for the ES line,
  phase transitions, AND the on-the-fly flaw detection + B/M tag computation for
  both players. The single batched query for the 20 paginated games must select
  the clock columns too (D-03).
- `game_flaws` — materialized user-M+B flaws with tags (Phase 108, SEED-038).
  **Backs chips/filter/Flaws-subtab only — NOT the chart dots** (D-02/D-10). The
  chart recomputes all dots on the fly; `game_flaws` is unchanged by this phase.

### Phase 108 context (the surface this phase builds on)
- `.planning/phases/108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr/108-CONTEXT.md`
  — D-02 (Games endpoints read `game_flaws`), D-03 (`game_flaws` is M+B-only;
  inaccuracies never persisted — the root reason inaccuracy dots are recomputed
  here).

### Frontend patterns (reuse, per UI-SPEC pre-population)
- `frontend/src/components/library/FlawTrendChart.tsx` — recharts-in-card
  pattern (`isAnimationActive={false}`, `ChartContainer`, custom `ChartTooltip`,
  no CartesianGrid).
- `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` — `ReferenceLine`
  + `ComposedChart` (Area + Line) + `connectNulls={false}` precedent.
- `frontend/src/components/results/LibraryGameCard.tsx` — the card being
  restructured into three thirds; `frontend/src/types/library.ts` — `GameFlawCard`
  type to extend; `frontend/src/lib/theme.ts` — severity constants + new chart
  constants.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`eval_utils.eval_cp_to_expected_score` / `eval_mate_to_expected_score`** —
  the locked white-perspective ES math for the chart line; never re-derive.
- **`flaws_service._run_all_moves_pass` / `_ply_to_es` / `_classify_severity` /
  `_build_tags`** — the mover-POV kernel reused for ALL on-the-fly chart dots
  (both colors, B/M/I) and B/M tags (D-01/D-02/D-03). `_run_all_moves_pass`
  already classifies both colors; `_build_tags` is FEN-free. Avoid
  `classify_game_flaws` (it does a PGN replay for FENs the chart doesn't need).
- **`game_flaws` table** — Phase 108's materialized user-M+B index; backs the
  Games chips/filter + Flaws subtab. **NOT the source for chart dots** — the
  chart recomputes all dots on the fly (D-02/D-10). `game_flaws` is unchanged by
  this phase.
- **FlawTrendChart / EndgameScoreOverTimeChart** — recharts patterns the new
  `EvalChart` follows (per UI-SPEC).

### Established Patterns
- Routers thin (`APIRouter(prefix="/library")`, relative paths); branching/
  aggregation lives in the service layer.
- `eval_cp` / `eval_mate` / `phase` are per-ply and white-perspective in
  `game_positions`; the chart line consumes them directly.
- TanStack Query per endpoint with mandatory `isError` branch (CLAUDE.md); chart
  colors from `theme.ts` only, no hex/oklch literals in the component.
- `noUncheckedIndexedAccess` — narrow every array/Record index access in the new
  TS.

### Integration Points
- `app/schemas/library.py` `GameFlawCard` (+ `frontend/src/types/library.ts`) —
  add `eval_series` / `flaw_markers` / `phase_transitions` (nullable for
  unanalyzed games).
- `app/services/library_service.py` Games-list builder — emit the per-ply series
  via one batched `game_positions` query (no N+1, no migration).
- `frontend/src/components/results/LibraryGameCard.tsx` — three-thirds desktop
  grid + mobile stacked block; new `EvalChart.tsx` in the middle column.
- `frontend/src/lib/theme.ts` — add the five new `EVAL_CHART_*` constants before
  implementing the component (per UI-SPEC).

</code_context>

<specifics>
## Specific Ideas

- Dots for **both players**, all severities: filled = you, hollow = opponent,
  color by severity (D-07). Detection is mover-POV via the both-color kernel
  (D-01).
- The chart **line** is white-perspective; flaw **detection** is mover-POV (D-04)
  — two perspectives, one builder.
- B/M tooltips show tags for both players (FEN-free `_build_tags`); inaccuracy
  tooltips show severity + eval only, no tags (D-03). Tooltip labels
  "You"/"Opponent" (D-08).
- `game_flaws` stays narrow — chart dots are all recomputed on the fly, not read
  from it (D-02/D-10).
- At most **two** phase lines (middlegame, endgame); **no ply-0 line** (D-06).
- Ship typed `EvalPoint[]` + `FlawMarker[]` (with an owner flag), round ES ~3 dp,
  trust gzip; planner verifies the payload delta (D-05).

</specifics>

<deferred>
## Deferred Ideas

- **Analysis detail viewer** (`/library/analysis/{game_id}?ply={N}`) and the
  **on-demand best-move endpoint** — separate later phases (SEED-036).
- **Columnar wire format for the per-ply series** — only if D-05's gzipped
  payload measurement shows a real regression.
- **Tags on inaccuracy dots** — deliberately dropped (D-03); could return if
  users want inaccuracy tooltips to match B/M.

### `game_flaws` materialization scope — kept narrow (D-10, owner-confirmed)
Whether to materialize inaccuracies and/or opponent flaws was discussed at
length. Governing principle: `game_positions` is the per-ply source of truth
(eval/phase/clock); `game_flaws` exists only as a **filter index** for the Flaws
subtab's tag-family `EXISTS`/`SELECT`/stats queries (the one shape recompute
can't serve). Rule: **materialize only what must be indexed/filtered at query
time; derive per-game display on the fly.** Phase 109's new opponent/inaccuracy
dots are *per-game display* (the chart reads one game and renders), so they are
derived on the fly and `game_flaws` is **unchanged** — even though the chart is
now a consumer of opponent B/M and inaccuracies. Materialization stays deferred:
- **Inaccuracies in `game_flaws`** — NOT materialized. Recomputed on the fly from
  the per-ply data the chart already loads (no extra query, FEN-free).
  Materializing would multiply rows (widest band), pollute the M+B-only Flaws
  semantics (forcing `severity != 'inaccuracy'` on existing queries), and trigger
  an all-users backfill. **Revisit trigger:** a **cross-game** consumer needs
  inaccuracies as indexed/filterable entities (e.g. SEED-037 Train: "drill my
  inaccuracies", or filtering the Flaws list by inaccuracy).
- **Opponent flaws in `game_flaws`** — NOT materialized, despite the chart now
  displaying them. Display ≠ query: the chart renders one game's opponent flaws
  on the fly; it never filters/queries opponent flaws across the archive.
  Materializing would also break the table's `(user_id, …)` "my flaws" semantics
  (opponent rows need a `mover_is_user` discriminator column + migration that
  Phase 108 avoided). **Revisit trigger:** a roadmapped opponent-weakness /
  "missed opportunities" / opponent-scouting surface that needs to **query/filter**
  opponent flaws across games — design the discriminator (or mover-perspective
  rows) then.

### Follow-up artifact work this scope expansion implies
- **`109-UI-SPEC.md` needs an amendment** for the dual-marker scheme (filled
  player vs hollow opponent, 6 dot styles), opponent B/M tooltip tags, the
  "You/Opponent" tooltip label, and the density-tuning note (D-07/D-08/D-09). The
  planner should either fold these into the plan or re-run `/gsd-ui-phase 109` for
  the marker contract before implementation.

None of the 10 keyword-matched pending todos were genuine Phase 109 candidates
(spurious "score"/"frontend"/"backfill" matches on unrelated work) — none folded.

</deferred>

---

*Phase: 109-per-card-expected-score-eval-chart-games-subtab*
*Context gathered: 2026-06-07*
