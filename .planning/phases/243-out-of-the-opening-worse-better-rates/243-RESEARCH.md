# Phase 243: Out of the Opening Worse/Better Rates (SEED-206) - Research

**Researched:** 2026-10-31
**Domain:** Peer-percentile pipeline (canonical-slice SQL builders, cohort CDF regen, Stage B, ranked read path) plus a React section on the Openings Stats tab
**Confidence:** HIGH (all findings come from code read this session, plus live probes on the dev and benchmark DBs; no external libraries involved)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The locked decisions in SEED-206 (`.planning/seeds/SEED-206-out-of-the-opening-worse-better-rates.md`) carry over
verbatim and are summarised here so the planner has them in one place. This discussion settled the seed's open
questions and dropped the popover histogram.

#### Metric (from SEED-206, locked)
- **D-01:** Value = the user-POV eval at the first middlegame ply minus the colour baseline
  (`EVAL_BASELINE_PAWNS_WHITE` +0.25, `EVAL_BASELINE_PAWNS_BLACK` −0.25 in
  `app/services/opening_insights_constants.py`).
  - **Worse** if ≤ −1.0, **better** if ≥ +1.0. A mate score counts by its sign.
  - The ±1.0 cut is a named constant, never a bare literal.
- **D-02:** A game that ends before the middlegame counts by result when it ends by resignation, checkmate or
  timeout (a loss counts as worse, a win as better). Abandoned games and draws are excluded.
- **D-03:** Copy says "eval", never "pawns". For example: "an eval 1.0 or more below a typical opening position".

#### Peer basis and CDF shape
- **D-04 (discussed):** **One CDF per TC per rate, pooled over colours.**
  - Each benchmark peer contributes one point per colour × TC that passes the floor, so up to 2 points per TC.
  - Both colours are ranked against the same curve.
  - That means 2 new metric ids (worse rate, better rate), not 4.
  - Justification: colour |d| ≤ 0.15 at every threshold (design note, benchmark tables).
  - Rejected: one CDF per colour (half the points per anchor cell, no evidence of need), and pooling each peer's
    two colours into one rate (it mismatches the per-colour user value we display).
  - **Reversibility:** costly. The new metric ids land in `benchmark_cohort_cdf` and in the
    `user_benchmark_percentiles` metric column, which is a native Postgres ENUM (`benchmark_metric_enum`).
    Switching to per-colour later means new ids plus a CDF regeneration.
- **D-05 (SEED-206):** A new canonical-slice builder in `app/services/canonical_slice_sql.py`, shared by
  `scripts/gen_global_percentile_cdf.py` and `app/services/user_benchmark_percentiles_service.py`.
  - Slice: the most recent 3000 games within 36 months per TC (`RECENT_GAMES_PER_TC_CAP`,
    `RECENCY_WINDOW_MONTHS`), rated games only, opponents within ±100.
  - Floor: 30 qualifying games per colour × TC. The same floor applies to peers (for CDF points) and to the user.
  - Filter-independent: page filters never change it.
  - The chess.com → lichess rating mapping applies as it does for the Endgames anchors.
- **D-06 (SEED-206):** Rank per TC, display collapsed over TC. The CDF stays per TC because the peer key is rating
  per TC.

#### Collapse, weights and significance (SEED-206 proposals, adopted as defaults)
- **D-07:** **Headline percentile per colour** = the user's per-TC percentiles averaged, weighted by **qualifying**
  games in each TC that passes the floor.
  - A qualifying game is one that reached the middlegame with an eval, or ended early by result per D-02. It is
    not every slice game.
  - A TC below the floor is dropped from both the headline and the gate, and listed in the popover as below
    floor.
  - The headline is an approximation, not a true percentile against a mixed-TC peer group. The copy must not
    overclaim it.
- **D-08:** **95% red/green gate.**
  - Pool the user's worse (better) count over the passing TCs. Its Wilson 95% CI must exclude the game-weighted
    peer median Σ w_tc · p50_tc(rating_tc), with the same weights as D-07.
  - Use `OPENING_INSIGHTS_CI_Z_95`, matching the Openings page (Phase 242 D-33), not the 99% used on Endgames and
    the Library.
  - The Endgames ranked-metric gate hardcodes `VERDICT_CI_Z_99` (`app/services/endgame_ranked_service.py`,
    `_wilson_interval`, `_rate_significant`). Pass z in as a parameter; never fork or reuse the 99% path as is.
- **Below-floor state:** if the selected colour has no TC that passes the floor, show the below-floor state as on
  Endgames. The colour that passes still renders when the user switches to it.

#### Section UI (SEED-206, sketch 013 Variant A, collapsed)
- One "Out of the opening" card at the top of the Stats tab, under the sticky White | Black switch, for the
  selected colour only. It is not one card per TC, a deviation from sketch 013.
- The card has two `RankedMetricRow` + `PercentileBar` rows:
  - **Worse** is the primary row.
  - **Better** is styled as the lesser row and never drives the card's headline.
- The words carry the inverted meaning: "Fewer worse games than 58% of peers".
- Below-floor and pending states work as on Endgames.
- No stacked worse / even / better bar: it reads as W/D/L.

#### Popover
- **D-09 (discussed; ROADMAP and SEED-206 updated to match):** **No histogram in the popover.** No other percentile
  popover has a chart, so this one follows the `RankedMetricPopover` structure
  (`frontend/src/components/endgames/stats/RankedMetricPopover.tsx`):
  - a plain WHAT sentence;
  - the percentile statement in words, with its disclosures;
  - a separator;
  - a greyed stats footer.
- **D-10:** The **per-TC breakdown** stays. It is a compact list, not a chart: rate, percentile and qualifying games
  for each passing TC, plus each below-floor TC listed as such. This is where a bullet vs. slower-TC split becomes
  visible.
- **D-11:** The footer reports the counts (pooled k of n), the peer band, and a **95%** CI (the Endgames footer says
  99%).
- **D-12:** The disclosures carry the percentile-chip contract:
  - the peers are benchmarked lichess players, **not FlawChess users**;
  - ranked games only (rated, opponents within ±100, last 36 months);
  - **filter independence**: unlike the Endgames Stats tab, the Openings page has filters, so this line is
    required;
  - rating dependence (the worse rate drops steeply with rating).

  The FlawChess population skews high (pooled mean centred eval about +40 cp vs about 0 in the benchmark), so
  expect mostly green. The "who the peers are" line carries real weight.

#### Tests
- A parity test of the slice builder: the CDF path and the user path produce identical per-user values.
- A per-eval-source check (lichess eval vs local full vs entry-lane), report-only and not a gate. SEED-206's
  feasibility data shows under ~1 pp difference.

### Claude's Discretion
- The storage shape for per-user percentiles: `user_benchmark_percentiles` has PK (user_id, metric,
  time_control_bucket) and **no colour column**, so per-colour user rows need either a colour column or per-colour
  metric ids. The planner picks one, consistent with D-04 (the CDF stays colour-pooled either way).
- How the API shape returns the collapsed headline, per-TC breakdown and gate result.
- The Umami popover target. Reuse the `popover-open` verb, and give the testid a `tc` segment only where
  `popoverTargetFromTestId` collapses it.

### Deferred Ideas (OUT OF SCOPE)
- **Opening LLM narration consuming these percentiles:** out of scope (ROADMAP). It is the open SEED-206 item and
  belongs to a later narration phase.
- **Per-opening worse/better bars in the repertoire expanded card:** cut by the owner. The original design is
  preserved in SEED-206.
- **An "out of the opening over time" chart:** mentioned in the design note as a possible later addition.
- (Also out of scope per CONTEXT domain: a histogram in the popover, D-09.)
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs exist for this phase; the coverage contract is the CONTEXT decisions. The planner should
map plans to these IDs.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | MG-entry eval minus colour baseline, ±1.0 cuts, mate by sign, named constant | §Pattern 1 (classification SQL), §Code Examples; prototype run on dev + benchmark |
| D-02 | Early-ending games by result (resignation/checkmate/timeout), abandoned + draws excluded | `termination` enum verified; §Pattern 1; Pitfall 5 |
| D-03 | Copy says "eval", never "pawns" | §Frontend copy constants |
| D-04 | One CDF per TC per rate, colour-pooled, 2 new metric ids | §Pattern 3 (colour-aware cohort ranking); §Storage recommendation |
| D-05 | Shared builder, canonical slice, floor 30 per colour × TC, filter-independent, chess.com mapping | §Pattern 2; anchor reuse |
| D-06 | Rank per TC, display collapsed | §Pattern 5 (collapse) |
| D-07 | Headline = game-weighted mean of per-TC percentiles over passing TCs | §Pattern 5 |
| D-08 | 95% Wilson gate on pooled count vs weighted peer p50, z passed as parameter | §Pattern 5; `wilson_bounds(z=...)` verified |
| D-09..D-12 | Popover structure, per-TC list, 95% footer, disclosure contract | §Frontend architecture |
| Tests | Builder parity CDF vs user path; per-eval-source check report-only | §Validation Architecture |
| UI | Card at top of Stats tab under sticky switch, worse primary, inverted wording, below-floor/pending states | §Frontend architecture; Pitfall 9 (sticky bar heading) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Root `CLAUDE.md` and `frontend/CLAUDE.md` directives that bind this phase:

- **Router convention:** `APIRouter(prefix="/openings", tags=["openings"])` with relative paths; never embed the prefix in the route path.
- **Layering:** routers = HTTP only; services = logic; repositories = DB access (no SQL in services). Note: the existing canonical-slice SQL lives in `app/services/canonical_slice_sql.py` (an established exception: pure SQL-string builders); keep the new builder there per D-05.
- **Never `asyncio.gather` on one AsyncSession;** sequential queries only.
- **Time-dependent endpoints take `now_utc` from `dev_now_utc`.** Documented exception precedent: the Endgames ranked endpoint uses SQL `NOW()` because the window must match the persisted Stage B basis byte for byte (`app/routers/endgames.py:42-46`). Reuse that exception with the same docstring rationale.
- **No magic numbers:** ±1.0 cut, floor 30, z = 1.96, percentile indices all named constants.
- **Type safety:** `Literal` for fixed sets (`"white" | "black"`, `"worse" | "better"`, metric ids); `Sequence[...]` for Literal-list params; explicit return types; `# ty: ignore[rule]` only with reason; `uv run ty check app/ tests/ scripts/` zero errors.
- **Pydantic at boundaries, TypedDict/dataclass internally.**
- **Nesting depth ≤ 4** (gated by `scripts/check_function_size.py app/ --fail-over-depth 4` and eslint `max-depth`).
- **Database rules:** FKs mandatory with `ondelete`; avoid native PG ENUM; "Align existing columns with this when you touch them" (applies to `benchmark_metric`, see Storage recommendation).
- **Sentry:** `capture_exception` in non-trivial `except` blocks in services/routers; no variables in error messages; `set_context` for ids.
- **Frontend:** theme colours from `theme.ts`; `text-sm` minimum (popover bodies may use `text-xs`); `data-testid` on every interactive element and major container; mobile parity; handle `isError` in every query render chain ("Failed to load [X]. Something went wrong. Please try again in a moment."); feature events through the typed `trackFeature` registry, popovers via `MetricInfoPopover`/`useTrackedPopoverOpen`; knip clean; run `npm run build` (tsc) because lint/test do not type-check.
- **Pre-merge gate** (mandatory before squash-merge): ruff format + check, ty (app/tests/scripts and analysis/), function-size gate, `uv run pytest -n auto -x`, frontend lint + build + test + knip.
- **Changelog:** user-facing bullet under `## [Unreleased]` in `CHANGELOG.md` when the phase merges.
- **GSD scope:** no unplanned features or refactors; flag rather than implement.
- **Copy style:** em-dashes sparingly in UI copy.
- **Never run `bin/reset_db.sh`;** plans must not gate on a dev DB reset (memory).

## Summary

Every piece of the pipeline this phase needs already exists for the Endgames percentiles, and the shapes are close
but not identical. The existing per-TC builders in `canonical_slice_sql.py` emit **one point per user per TC**
(`per_user_values(user_id, metric_value, n_games)`), the cohort CDF generator ranks those points in Python on a
50-Elo anchor grid, Stage B upserts one `user_benchmark_percentiles` row per (metric, TC), and the Endgames read
path serves on-read values next to persisted percentiles with a 99% verdict. This phase needs a **colour-split**
variant of each stage: up to 2 points per peer per TC in the CDF (D-04), 2 rows per user per TC per rate, and a
collapsed, 95%-gated read path. The colour split is the main structural change and touches the builder output, the
CDF ranking/tie-break, the user row storage key, and the Stage B write loop.

A prototype of the classification SQL ran on both DBs this session: about 180 ms warm (600 ms cold) per TC for
the heaviest dev user (3,000 blitz slice games), and 91 s for the whole benchmark cohort on rapid (560k slice
games, 14M positions scanned through the existing `(user_id, game_id, ply)` PK). No new index is needed. A full
CDF regen of the two new metrics is roughly 10 minutes of benchmark DB time. The dev result for user 31 blitz
(white 330/1491 worse, 455 better; black 495/1490 worse, 394 better) shows the shape works end to end.

Three traps dominate planning: (1) adding the new family to `STAGE_B_METRIC_FAMILIES` breaks the Endgames parity
test and two count assertions, so it needs its own tuple; (2) a full `gen_global_percentile_cdf.py` regen would
silently move every existing Endgames CDF (the benchmark DB is not static), so the regen must be scoped to the new
metrics and merged into the committed TSV; (3) the frontend `CdfMetricId` union backs several `Record<CdfMetricId,…>`
maps and the Endgames `metrics` record, so the opening ids must not be added to it.

**Primary recommendation:** Add a colour column to `user_benchmark_percentiles` (PK widened, existing rows
`'all'`), two shared metric ids `opening_worse_rate` / `opening_better_rate`, one shared colour-split builder whose
classification CTE is reused by the CDF script, Stage B and the on-read path, a scoped `--metrics` merge regen, and
a new self-fetching `OutOfOpeningSection` that reuses `PercentileBar` + `MetricInfoPopover` directly (not
`RankedMetricRow`/`RankedMetricPopover`, which are hard-typed to the Endgames payload).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-game worse/better classification (MG entry eval, early-end by result) | Database / Storage (SQL CTE in `canonical_slice_sql.py`) | — | One SQL body shared by CDF regen, Stage B and on-read keeps the three paths drift-proof (D-05) |
| Peer CDF construction (colour-pooled, per TC × anchor) | Offline script (`scripts/gen_global_percentile_cdf.py`) on benchmark DB | Database (`benchmark_cohort_cdf` seeded from TSV) | Existing pipeline; build-time artifact |
| Per-user percentile materialisation (per colour × TC) | API / Backend background task (Stage B) | Database (`user_benchmark_percentiles`) | Eval-dependent; must run after the eval drain, like the other Stage B families |
| Collapse over TC + 95% gate + rank status | API / Backend (pure service function) | — | Statistics and the gate belong server-side so frontend never re-derives significance |
| Section rendering, inverted wording, popover | Browser / Client | — | Presentation only; consumes the oriented percentile and `significant` flag |
| Cache invalidation after import / Stage B | Browser / Client (TanStack Query keys) | — | Mirrors the `['endgameOverview']` invalidation sites |

## Standard Stack

No new packages. Everything is in-repo.

### Core (existing, reused)
| Component | Location | Purpose | Why |
|-----------|----------|---------|-----|
| Canonical-slice builders | `app/services/canonical_slice_sql.py` | `selected_users_cte`, `_recent_capped_per_tc_cte`, `per_user_cte_median_anchor` | D-05 mandates the shared builder |
| Cohort CDF generator | `scripts/gen_global_percentile_cdf.py` | Per (metric, TC) query + in-Python anchor ranking + TSV emit | The only CDF path |
| CDF seed | `scripts/seed_cohort_cdf.py` + `app/data/cohort_cdf.tsv` | Upserts TSV rows into `benchmark_cohort_cdf` | Idempotent `ON CONFLICT DO UPDATE` |
| CDF read | `app/repositories/benchmark_cohort_cdf_repository.py::load_cohort_cells` | Batched (metric, anchor, TC) → `CdfTable` | Returns all metrics for the anchors × TCs |
| Interpolation | `app/services/global_percentile_cdf.py::interpolate_cohort_percentile`, `round_anchor_to_grid` | Value → percentile | Pure, already tested |
| Stage B | `app/services/user_benchmark_percentiles_service.py::compute_stage_b` | Background per-user compute, semaphore-bounded | Existing trigger sites (import completion, eval drain) |
| Wilson CI | `app/services/score_confidence.py::wilson_bounds(p, n, z=...)`, `ci_excludes` | 95% gate | Already parameterised by z |
| Frontend bar | `frontend/src/components/endgames/stats/PercentileBar.tsx` (`PercentileBar`, `RankStatusLine`) | Percentile axis + below-floor/pending/unranked slot | Generic props, no Endgames types |
| Popover shell | `frontend/src/components/ui/metric-info-popover.tsx` (`MetricInfoPopover`) | Trigger + Radix content + Umami `popover-open` | Shared shell |
| Percentile helpers | `frontend/src/components/endgames/stats/rankedMetrics.ts` (`displayPercentile`, `PERCENTILE_TYPICAL_LOW/HIGH`, `COPY_CHANCE`, `formatOrdinal`) | Display clamp + band constants | Keeps dot/ordinal/colour in step |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages (backend or frontend). **Packages removed:** none. **Packages flagged:** none.

## Verified In-Repo Facts (quoted verbatim)

| Fact | Source | Verbatim |
|------|--------|----------|
| Window constants | [VERIFIED: app/services/canonical_slice_sql.py:111-112] | `RECENT_GAMES_PER_TC_CAP: int = 3000` / `RECENCY_WINDOW_MONTHS: int = 36` |
| Anchor floor | [VERIFIED: app/services/canonical_slice_sql.py:137] | `MEDIAN_ANCHOR_MIN_GAMES: Final[int] = 30` |
| Equal footing / sub-800 | [VERIFIED: app/services/canonical_slice_sql.py:140-146] | `_EQUAL_FOOTING_TOL: int = 100` … `_SUB_800_FLOOR: int = 800` … `SUB_800_FLOOR: Final[int] = _SUB_800_FLOOR` |
| `recent_capped` projects only these columns | [VERIFIED: app/services/canonical_slice_sql.py:287-288] | `recent_capped AS (` / `  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at` |
| 95% z | [VERIFIED: app/services/opening_insights_constants.py:64] | `OPENING_INSIGHTS_CI_Z_95: float = 1.96` |
| Colour baselines | [VERIFIED: app/services/opening_insights_constants.py:85-86] | `EVAL_BASELINE_PAWNS_WHITE: float = 0.25` / `EVAL_BASELINE_PAWNS_BLACK: float = -0.25` |
| 99% z | [VERIFIED: app/services/score_confidence.py:71] | `VERDICT_CI_Z_99: float = 2.5758293035489` |
| Wilson signature | [VERIFIED: app/services/score_confidence.py:84] | `def wilson_bounds(p: float, n: int, z: float = CI_Z_95) -> tuple[float, float]:` |
| 99% hardcode sites | [VERIFIED: app/services/endgame_ranked_service.py:515-520, 780-789] | `return wilson_bounds(value, n, z=VERDICT_CI_Z_99)` and `lo, hi = wilson_bounds(successes / games, games, z=VERDICT_CI_Z_99)` |
| Median index | [VERIFIED: app/services/endgame_ranked_service.py:242-243] | `_MEDIAN_PERCENTILE: Final[float] = 50.0` / `_MEDIAN_BREAKPOINT_INDEX: Final[int] = BREAKPOINT_PERCENTILES.index(_MEDIAN_PERCENTILE)` |
| Rank-status order | [VERIFIED: app/services/endgame_ranked_service.py:876-906] | `if not has_anchor and anchor_games < MEDIAN_ANCHOR_MIN_GAMES: return "below_floor", …` → `if eval_dependent and value is None and eval_pending > 0: return "pending", …` → `if floor_n < floor_required: return "below_floor", …` → `if row is not None and row.percentile is not None: return "ranked", …` → `return "unranked", …` |
| Rank status union | [VERIFIED: app/schemas/endgames.py:426] | `RankStatus = Literal["ranked", "below_floor", "unranked", "pending"]` |
| Termination values | [VERIFIED: app/models/game.py:25-34] | `"checkmate", "resignation", "timeout", "draw", "abandoned", "unknown", name="termination"` |
| Result values | [VERIFIED: app/models/game.py:23] | `SAEnum("1-0", "0-1", "1/2-1/2", name="gameresult", create_type=False)` |
| Phase column | [VERIFIED: app/models/game_position.py:152-160] | `# Lichess Divider.scala phase classification: 0=opening, 1=middlegame, 2=endgame.` / `phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` / `eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` / `eval_mate: …` |
| Phase rule (no middlegame possible) | [VERIFIED: app/services/position_classifier.py:300-303, 336-337] | `If end_ply exists and end_ply <= mid_ply, drop mid_ply … The game then has no middlegame phase` / `if end_ply is not None and mid_ply >= end_ply: mid_ply = None` |
| PG ENUM name | [VERIFIED: app/models/user_benchmark_percentile.py:60, 88-89] | `benchmark_metric_enum = SAEnum(` … `name="benchmark_metric",` / `create_type=False,` |
| Percentile PK | [VERIFIED: app/models/user_benchmark_percentile.py:131-141] | `user_id … primary_key=True` / `metric: Mapped[CdfMetricId] = mapped_column(benchmark_metric_enum, primary_key=True)` / `time_control_bucket … primary_key=True` |
| CDF PK | [VERIFIED: app/models/benchmark_cohort_cdf.py:54-69] | `metric` / `anchor_elo` / `tc` / `percentile`, each `primary_key=True` |
| CdfMetricId values | [VERIFIED: app/services/global_percentile_cdf.py:83-97] | `"score_gap", "achievable_score_gap", "score_gap_conv", "score_gap_parity", "recovery_score_gap", "time_pressure_score_gap", "clock_gap", "net_flag_rate", "conversion_rate", "parity_rate", "recovery_rate",` |
| Snapshot month | [VERIFIED: app/services/global_percentile_cdf.py:53] | `BENCHMARK_DB_SNAPSHOT_MONTH: Final[str] = "2026-05"` |
| Cohort policy | [VERIFIED: scripts/gen_global_percentile_cdf.py:125-145] | `COHORT_MIN_USERS_PER_ANCHOR: Final[int] = 100` / `COHORT_MAX_USERS_PER_ANCHOR: Final[int] = 500` / `COHORT_MAX_WINDOW_ELO: Final[int] = 200` / `COHORT_ANCHOR_STEP_ELO: Final[int] = 50` / `COHORT_ANCHOR_MIN_ELO: Final[int] = 800` / `COHORT_ANCHOR_MAX_ELO: Final[int] = 2600` |
| Cohort tie-break | [VERIFIED: scripts/gen_global_percentile_cdf.py:461-463] | `cohort = sorted(in_window, key=lambda r: (abs(r.anchor_rating - anchor), r.user_id))[` / `:COHORT_MAX_USERS_PER_ANCHOR` |
| Output paths | [VERIFIED: scripts/gen_global_percentile_cdf.py:176-177] | `OUTPUT_SEED_PATH: Final[Path] = Path("app/data/cohort_cdf.tsv")` / `DEFAULT_REPORT_PATH: Final[Path] = Path("reports/percentile/cohort-percentile-cdf-latest.md")` |
| Prior regen basis | [VERIFIED: reports/percentile/cohort-percentile-cdf-latest.md:5-11] | `**Snapshot date (recency anchor)**: 2026-05-30` / `**Regen runtime**: 680.4s` / `--target benchmark --snapshot-date 2026-05-30` |
| Stage B families | [VERIFIED: app/services/user_benchmark_percentiles_service.py:136-147] | `STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = ("achievable_score_gap", "score_gap_conv", "score_gap_parity", "recovery_score_gap", "time_pressure_score_gap", "clock_gap", "net_flag_rate", "conversion_rate", "parity_rate", "recovery_rate",)` |
| Single-row user query | [VERIFIED: app/services/user_benchmark_percentiles_service.py:253-258] | `f"SELECT metric_value::float AS value, n_games::int AS n_games\n"` / `f"FROM per_user_values\n"` / `f"LIMIT 1"` |
| Concurrency bound | [VERIFIED: app/services/user_benchmark_percentiles_service.py:156] | `PERCENTILE_COMPUTE_LIMIT = 2` |
| ENUM extension precedent | [VERIFIED: alembic/versions/20260530_220134_52c928794fe7_add_rate_family_names_to_benchmark_metric.py:39-41] | `for value in _NEW_VALUES:` / `op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")` |
| Alembic head | [VERIFIED: `uv run alembic heads`] | `5448f030de58 (head)` (benchmark DB also at `5448f030de58`) |
| Parity test family list | [VERIFIED: tests/services/test_endgame_ranked_parity.py:78, 455, 562] | `_ALL_FAMILIES: tuple[CdfMetricId, ...] = ("score_gap", *STAGE_B_METRIC_FAMILIES)` / `@pytest.mark.parametrize("family", _ALL_FAMILIES)` / `assert set(metrics) == set(_ALL_FAMILIES)` |
| Stage B count pin | [VERIFIED: tests/services/test_user_benchmark_percentiles_service.py:85] | `assert len(STAGE_B_METRIC_FAMILIES) == 10` |
| Migration test glob | [VERIFIED: tests/integration/test_alembic_migrations.py:37-44, 83] | `"*user_benchmark_percentile*",` / `_PK_COLUMNS: frozenset[str] = frozenset({"user_id", "metric", "time_control_bucket"})` |
| Frontend metric union | [VERIFIED: frontend/src/types/endgames.ts:259-271, 326] | `export type CdfMetricId = \| 'score_gap' … \| 'recovery_rate';` / `metrics: Record<CdfMetricId, RankedMetricOut>;` |
| Frontend percentile bands | [VERIFIED: frontend/src/components/endgames/stats/rankedMetrics.ts:13-18] | `PERCENTILE_TYPICAL_LOW = 25` / `PERCENTILE_TYPICAL_HIGH = 75` / `PERCENTILE_MEDIAN = 50` / `PERCENTILE_DISPLAY_MIN = 1` / `PERCENTILE_DISPLAY_MAX = 99` |
| Popover TC collapse | [VERIFIED: frontend/src/lib/analytics.ts:552-556] | `POPOVER_TC_SEGMENTS: readonly string[] = ['bullet', 'blitz', 'rapid', 'classical'];` / `POPOVER_TC_PREFIX_SEGMENTS: readonly string[] = ['tc', 'card'];` / `POPOVER_VIEW_SUFFIXES: readonly string[] = ['mobile', 'desktop', 'sidebar', 'drawer'];` |
| Sticky bar heading contract | [VERIFIED: frontend/src/components/openings/stats/headingClasses.ts] | `export const REPERTOIRE_HEADING_CLASS = cn(SECTION_HEADING_CLASS, 'lg:flex lg:h-8 lg:items-center');` |
| Dev DB enum labels in use | [VERIFIED: dev DB query] | rows exist only for the 11 bare family names; the 12 TC-suffixed labels have 0 rows on dev (prod not checked) |

## Architecture Patterns

### System Architecture Diagram

```
                         BUILD TIME (operator, benchmark DB :5433)
 benchmark games ──► selected_users_cte("benchmark") ──► _recent_capped_per_tc_cte(snapshot, tc)
                                                              │
                                                              ▼
                                   opening_out classification CTE (shared body)
                                   per game: user_id, user_color, side ∈ {-1,0,+1,NULL}
                                                              │
                     per_user_colour_values (HAVING n ≥ 30)   │   per_user_anchor (median, per TC)
                                   └──────────── JOIN USING (user_id) ─────────┘
                                                              ▼
                         Python ranking per anchor (±200 Elo window, MIN/MAX, tie-break incl. colour)
                                                              ▼
                       app/data/cohort_cdf.tsv  (MERGED: new metric rows only; existing rows byte-identical)
                                                              ▼
                       scripts/seed_cohort_cdf.py ──► benchmark_cohort_cdf (dev, then prod post-deploy)

                         RUN TIME (app DB)
 import completes / eval drain hits zero ──► compute_stage_b(user)
      ├─ existing 10 endgame families (unchanged)
      └─ NEW opening family loop: per anchored TC
            selected_users_cte("single_user") + SAME classification CTE
            ──► rows (white|black) × (worse|better): value, n
            ──► load_cohort_cells ──► interpolate_cohort_percentile (raw percentile)
            ──► upsert user_benchmark_percentiles(user, metric, tc, color)

 GET /api/openings/out-of-opening-stats (no filters, auth user only)
      ├─ on-read counts per (tc, colour): SAME classification CTE (no HAVING)
      ├─ eval_pending + anchor game counts per TC (fetch_ranked_games)
      ├─ persisted percentile rows (color ∈ white|black) + anchors + CDF p25/p50/p75 at anchor
      └─ pure builder: rank status per (colour, tc, rate) → collapse over passing TCs
             headline pct = Σ w·pct_tc ; gate = Wilson95(Σk/Σn) excludes Σ w·p50_tc ; orient (worse → 100 − pct)
      ──► OutOfOpeningStatsResponse { white: {...}, black: {...} }

 Browser: StatsTab ──► OutOfOpeningSection(color) ──► useOutOfOpeningStats() [key under an import-invalidated prefix]
      ──► card: worse row (primary) + better row (lesser) ──► PercentileBar + MetricInfoPopover body
```

### Recommended file layout

```
app/services/opening_insights_constants.py   # + OPENING_OUT_THRESHOLD_PAWNS = 1.0 (and cp mirror)
app/services/canonical_slice_sql.py          # + OPENING_OUT_MIN_GAMES_PER_COLOR, builder(s)
app/services/global_percentile_cdf.py        # + "opening_worse_rate", "opening_better_rate" in CdfMetricId
app/models/user_benchmark_percentile.py      # + color column (PK), metric column type change (see Storage)
app/models/benchmark_cohort_cdf.py           # metric column type change if ENUM→TEXT is folded in
alembic/versions/<date>_<rev>_opening_out_rates_metric_and_color.py   # name WITHOUT "user_benchmark_percentile"
app/repositories/user_benchmark_percentiles_repository.py  # upsert color param; fetch_for_user filters color='all'; new fetch for colour rows
app/services/user_benchmark_percentiles_service.py         # + STAGE_B_OPENING_FAMILIES loop (separate tuple)
app/services/opening_out_stats_service.py    # NEW: fetch inputs + pure collapse/gate builder
app/repositories/opening_out_repository.py   # NEW (optional): on-read counts query via the shared builder
app/schemas/openings.py (or new opening_out.py) # NEW response models
app/routers/openings.py                      # + GET /out-of-opening-stats
scripts/gen_global_percentile_cdf.py         # colour-aware query/ranking + --metrics merge mode + report path
app/data/cohort_cdf.tsv                      # regenerated rows for the 2 new metrics only
tests/scripts/fixtures/global_percentile_cdf/opening_{worse,better}_rate__{tc}.sql  # 8 new goldens
frontend/src/types/openingOut.ts             # NEW, do NOT extend endgames CdfMetricId
frontend/src/api/client.ts + hooks/useOutOfOpeningStats.ts
frontend/src/components/openings/stats/OutOfOpeningSection.tsx (+ Row, Popover, copy constants, tests)
```

### Pattern 1: One classification CTE, three consumers

**What:** A single SQL body classifies each slice game into worse (−1), even (0), better (+1) or non-qualifying
(NULL). The CDF path, Stage B and the on-read path all compose it; only the outer aggregation differs.

**Definition (matches the benchmark measurement in `.planning/sketches/013-out-of-the-opening/analysis/fetch_sweep.py`, read this session):**
- MG entry = `min(ply)` over `game_positions WHERE phase = 1` for the game (same rule as `stats_repository.py:657-665`, `DISTINCT ON (game_id) … ORDER BY game_id, ply`).
- No phase-1 ply → "ended before the middlegame": counts only if `termination IN ('resignation','checkmate','timeout')` AND result is decisive; user win → +1, user loss → −1. Draws, `abandoned`, `unknown`, NULL termination → NULL (excluded).
- Has MG entry with `eval_mate` → sign of mate in user POV (`sign(eval_mate) * (white ? 1 : -1)`), so `eval_mate = 0` lands at 0 (even), as in the sketch.
- Has MG entry with `eval_cp` → centred = user-POV cp − baseline cp (white: `eval_cp - 25`; black: `-eval_cp + 25`); ≤ −100 → −1, ≥ +100 → +1, else 0. No outlier trim (a ±2000 cp value is simply worse/better).
- Has MG entry but both evals NULL → NULL (non-qualifying; D-07 "reached the middlegame with an eval").
- Join `games g ON g.id = rc.id` for `termination` (do NOT widen `recent_capped`: every existing builder and the 44 golden fixtures depend on its exact text).
- Add `gp.user_id = rc.user_id` to the position join so the PK `(user_id, game_id, ply)` drives an index scan (verified in the EXPLAIN this session: `Index Scan using game_positions_pkey … Index Cond: ((user_id = rc_1.user_id) AND (game_id = rc_1.id)) Filter: (phase = 1)`).

**Sub-800 floor:** the existing raw-rate builders drop sub-800 games (`AND {ueag} >= {_SUB_800_FLOOR}`), and the design-note benchmark measured with sub-800 dropped. Recommend applying the same per-game sub-800 drop for consistency. [ASSUMED: not stated in CONTEXT; flag in the plan as a definition choice.]

### Pattern 2: Colour-split builder output

Existing builders emit `per_user_values(user_id, metric_value, n_games)`, one row per user, and Stage B reads it
with `LIMIT 1`. The new builder must emit a colour column. Recommended shape:

- `per_user_cte_opening_out_counts(tc, *, source, snapshot_date=None)` → CTE chain ending in
  `per_user_colour_counts(user_id, user_color, n_games, worse_n, better_n)`, **no floor** (used by the on-read path to show "18 of 30").
- `per_user_cte_opening_out_rate(tc, *, side: Literal["worse","better"], source, snapshot_date=None)` → the counts chain plus
  `per_user_values(user_id, user_color, metric_value, n_games)` with `WHERE n_games >= OPENING_OUT_MIN_GAMES_PER_COLOR`
  (the CDF path dispatches one metric at a time, so one builder per side keeps the existing dispatcher shape).
- Keep `_ = source` and byte-identical bodies across sources (the structural parity contract in
  `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`).
- Stage B can either call the rate builder twice per TC or (cheaper, ~half the DB time) select both rates from the counts CTE with the same floor constant in SQL; either way the floor constant appears only in SQL.

### Pattern 3: Colour-aware cohort ranking in the CDF script

`_build_per_user_with_anchor_query` joins `per_user_values` to `per_user_anchor USING (user_id)`; with two colour
rows per user the join naturally yields 2 points per user. Changes needed:

- Project `puv.user_color` and add it to `_PerUserRow` (or a sibling row type for colour metrics), so the tie-break
  becomes `(distance, user_id, user_color)`; without it the cap at MAX is non-deterministic and the byte-identical
  regen contract breaks.
- **Decide what MIN/MAX count.** Recommendation: rank and cap by **distinct users** (both colours of a user enter or
  leave together), gate MIN on distinct users, and write distinct users into `n_users`. Rationale: a user's two
  colour rates are correlated draws of one trait, so counting points would overstate the cohort and halve the Elo
  span at the 500 cap compared with every other metric. [ASSUMED: owner did not decide; D-04 only says each peer
  contributes up to 2 points.]
- The anchor block renaming hack (`replace("recent_capped AS (", "recent_capped_anchor AS (")`) still works as long as
  the new builder introduces no CTE named `recent_capped_no_daily`.
- Leave every existing metric's SQL byte-identical (the 44 golden fixtures guard this).

### Pattern 4: Scoped regen, merged TSV

A full regen re-queries all 11 existing metrics against today's benchmark DB, which has grown since 2026-05 (memory:
"Benchmark DB is not static"), so every Endgames CDF and every user's Endgames percentile would shift on the next
Stage B. Out of scope. Add:

- `--metrics opening_worse_rate,opening_better_rate` (choices from `IN_SCOPE_METRICS`);
- merge mode: load the committed TSV into the cells dict (the loader exists in
  `tests/scripts/test_cohort_cdf_seed_artifact.py::_load_cells_from_tsv`; promote it into the script), replace only the
  selected metrics, rewrite with `_write_seed_tsv`. The round-trip test already proves parse→emit is byte-stable for `.4f` values.
- write the regen report to a separate path (for example `reports/percentile/cohort-percentile-cdf-opening-out-latest.md`)
  so the 1,628-cell Endgames report is not overwritten with an 8-cell one.
- run with `--snapshot-date 2026-05-30` (same basis as the committed CDFs; benchmark max `played_at` is 2026-05-26).

### Pattern 5: Collapse, orientation and the 95% gate (pure function)

Per colour, for each rate:
1. Per TC: status via the Endgames `_rank_status` order (extract it to a public helper rather than copy it). Inputs:
   anchor present, anchor game count, eval-pending count, on-read `n`, floor 30, persisted row for (metric, tc, colour).
2. **Contributing TCs** = status `ranked` (floor passed AND a persisted percentile exists, which implies a CDF cell at
   the anchor). TCs below floor, pending, or without a CDF cell are excluded from both headline and gate and listed
   in the popover with their status. [ASSUMED: D-07 names below-floor TCs only; excluding no-CDF-cell TCs follows
   necessarily because the gate needs that TC's p50.]
3. Weights `w_tc = n_tc / Σ n` over contributing TCs (on-read qualifying counts, D-07).
4. Headline raw percentile = `Σ w_tc · pct_tc`.
5. Pooled `k = Σ k_tc`, `n = Σ n_tc`; `ci = wilson_bounds(k/n, n, z=OPENING_INSIGHTS_CI_Z_95)`; null =
   `Σ w_tc · p50_tc` with `p50_tc = table.breakpoints[BREAKPOINT_PERCENTILES.index(50.0)]` at the TC's rounded anchor.
6. `significant = ci_excludes(null, *ci) and ((k/n > null) == (headline_raw > 50))` (same direction guard as
   `_metric_significant`).
7. Orientation for display: worse → `100 − raw` ("Fewer worse games than N% of peers"); better → raw ("More better
   games than N% of peers"). Do it once, server-side, and name the field so it cannot be mistaken for the raw CDF
   percentile (for example `percentile_favourable`). Apply the same orientation to the per-TC breakdown.
8. Peer band for the footer: game-weighted p25/p75 (`Σ w·p25_tc`, `Σ w·p75_tc`) labelled as approximate, plus the
   exact per-TC band in the breakdown list. [ASSUMED: D-11 says "peer band" without defining the collapse.]
9. Card-level status when nothing contributes: `pending` if any TC is pending, else `below_floor` showing the
   highest per-TC `n` of 30, else `unranked`. [ASSUMED]

Pass z as a parameter (D-08). Do not edit the Endgames 99% helpers to take z unless the plan explicitly scopes that
refactor; a small local helper that calls `wilson_bounds(…, z=OPENING_INSIGHTS_CI_Z_95)` satisfies "never fork or reuse the 99% path".

### Storage recommendation (Claude's discretion)

**Use a colour column, not per-colour metric ids.**

| | Colour column (recommended) | Per-colour metric ids |
|---|---|---|
| Metric ids | 2 shared by CDF and user rows (matches D-04 "2 new metric ids, not 4") | 2 CDF ids + 4 user-row ids |
| CDF lookup | `cohort.get((metric, anchor, tc))` unchanged | needs a user-id → CDF-id mapping |
| Types | `CdfMetricId` gains 2 values; `Mapped[CdfMetricId]` stays | `metric` column needs a wider union; `fetch_for_user` typing breaks `RankedInputs.percentile_rows: dict[CdfMetricId, …]` |
| Endgames impact | `fetch_for_user` must filter `color = 'all'` | `fetch_for_user` must filter out the 4 ids |
| Migration | add `color TEXT NOT NULL DEFAULT 'all' CHECK (color IN ('all','white','black'))`, drop + recreate PK on 4 columns | enum/CHECK values only |

`upsert_percentile` gains `color: PercentileColor = "all"` and a 4-column `index_elements`. Existing callers keep the
default. Update `tests/integration/test_alembic_migrations.py` (`_EXPECTED_COLUMNS`, `_PK_COLUMNS`).

**ENUM alignment (the CONTEXT flag):** CLAUDE.md says to align native ENUM columns with TEXT + CHECK when touched.
This phase touches `benchmark_metric` either way. Folding it in costs one more step in the same migration
(`ALTER COLUMN metric TYPE text USING metric::text` on both tables, `DROP TYPE benchmark_metric`, add
`CHECK (metric IN (…13 values…))`), model columns become `Text` + `CheckConstraint` generated from
`typing.get_args(CdfMetricId)`, and two pinned tests change (`tests/integration/test_benchmark_metric_enum.py`
becomes a CHECK introspection test; `test_alembic_migrations.py` stops asserting `USER-DEFINED` and the
"ENUM type must exist" check). The tables are small (`benchmark_cohort_cdf` 122,661 rows; prod percentiles roughly
500 users × 11 × 4). The CHECK would drop the 12 unused TC-suffixed legacy labels; `ADD CONSTRAINT` validates
existing rows, so a prod row carrying one would fail the deploy migration loudly rather than silently
(dev has none; prod not checked). **Recommendation: fold it in**, with a pre-deploy prod check
(`SELECT metric, count(*) FROM user_benchmark_percentiles GROUP BY 1`, owner/orchestrator via the prod DB MCP).
Fallback if the planner prefers minimum risk: `ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS` ×2 (precedent
`52c928794fe7`) plus an explicit "ENUM kept, alignment deferred" note in the plan. Either way, write the reason down.

### Anti-Patterns to Avoid
- **Adding the opening family to `STAGE_B_METRIC_FAMILIES`.** It breaks `test_endgame_ranked_parity.py` (parametrised over it, and asserts `set(metrics) == set(_ALL_FAMILIES)`) and the 10-count pins. Use a separate `STAGE_B_OPENING_FAMILIES` tuple processed in `compute_stage_b` after the endgame loop.
- **A Python mirror of the classification for the read path.** The Endgames page needed a Python mirror plus a numeric parity gate because its on-read helpers predated the CTEs. Here, compose the same SQL for on-read counts; parity becomes structural.
- **Running a full CDF regen.** See Pattern 4.
- **Reusing `RankedMetricRow` / `RankedMetricPopover` as is.** Both take `RankedMetricOut` + `RankedTcStats` (Endgames payload), call `METRIC_LABELS[metric.metric]` and hardcode "Better than N% of … players" and "99% CI". Reuse `PercentileBar`, `RankStatusLine`, `MetricInfoPopover` and the `rankedMetrics.ts` helpers; build an opening-specific row and popover body. If the planner generalises `RankedMetricRow` with a popover slot, keep Endgames rendering byte-identical.
- **Extending the frontend `CdfMetricId` union.** `METRIC_LABELS`, `METRIC_WHAT` and `RankedTcStats.metrics` are `Record<CdfMetricId, …>`; widening forces fake Endgames entries.
- **A colour segment in the popover testid.** `popoverTargetFromTestId` keeps `white`/`black`, splitting the Umami row; no `tc` segment is needed either (the card is not per TC).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wilson CI | new interval math | `score_confidence.wilson_bounds(p, n, z=OPENING_INSIGHTS_CI_Z_95)` + `ci_excludes` | Already clamped and tested |
| Percentile interpolation | bisect code | `interpolate_cohort_percentile` + `round_anchor_to_grid` | Tail clamps, degenerate intervals |
| Rating anchors / chess.com mapping | per-colour anchors or new conversion | existing `user_rating_anchors` per (user, TC) via `fetch_anchors_for_user` | D-05: mapping "as for the Endgames anchors"; anchor is per TC, not per colour |
| CDF cell read | ad-hoc SELECT | `load_cohort_cells(session, anchors, tcs)` | Batched, groups 99 rows per cell |
| Pending / anchor game counts | new SQL | `fetch_ranked_games(session, user_id=…, tc=…)` (`eval_pending`, platform, `time_control_str`) + the existing anchor-game rule | Same canonical sample |
| Popover shell + Umami | custom Radix wiring | `MetricInfoPopover` (`useTrackedPopoverOpen`) | `popover-open` via testid |
| Percentile bar / status slot | new bar | `PercentileBar`, `RankStatusLine` | Same red/blue/green rules, "N of 30", pending copy |
| TSV load/merge | new parser | promote `_load_cells_from_tsv` from the seed-artifact test | Proven byte-stable round trip |

## Runtime State Inventory

Not a rename phase, but the change has runtime state outside git that the plan must carry explicitly:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `benchmark_cohort_cdf` on dev and prod holds only the 11 existing metrics; `user_benchmark_percentiles` has no opening rows | Dev: `uv run python -m scripts.seed_cohort_cdf` after the TSV regen (`bin/run_local.sh` seeds only when the table is empty). Prod: seed post-deploy in the container (`docker compose exec backend /app/.venv/bin/python -m scripts.seed_cohort_cdf`), then backfill Stage B |
| Live service config | None found | None |
| OS-registered state | None | None |
| Secrets/env vars | None (benchmark DB URL already in `.env` as used by `db_url_for_target("benchmark")`) | None |
| Build artifacts | Test DB template auto-refreshes on Alembic head change (`tests/conftest.py`) | None. Benchmark DB needs `alembic upgrade head` if the migration changes the metric column type (the script writes no rows there, but the model/ENUM must match if any benchmark-lane code reads it) |
| Existing users' rows | Stage B only runs on import completion or eval-drain zero crossing, so existing users never get opening rows on their own | Backfill: `uv run python -m scripts.archive.backfill_user_percentiles --target prod --skip-anchors` (verified `--help` works as a module this session; it calls `compute_stage_b`). Must run AFTER the prod seed, otherwise rows get `percentile=NULL` and show "Not ranked yet". Prod tunnel + owner decision (memory: prod writes from agents are denied in auto mode) |

## Common Pitfalls

### Pitfall 1: Stage B family tuple coupling
**What goes wrong:** Endgames parity test and the Stage B count tests fail, or the Endgames payload gains opening keys.
**Why:** `_ALL_FAMILIES = ("score_gap", *STAGE_B_METRIC_FAMILIES)` drives both parametrisation and a set-equality assertion.
**How to avoid:** separate `STAGE_B_OPENING_FAMILIES`; a colour-aware upsert helper next to `_compute_and_upsert_cell`.
**Warning signs:** `test_endgame_ranked_parity.py` failures mentioning an opening metric.

### Pitfall 2: Silent CDF drift from a full regen
**What goes wrong:** All Endgames percentiles shift after deploy.
**Why:** the regen re-queries every metric against a grown benchmark DB.
**How to avoid:** scoped `--metrics` + merge; a test asserting every non-opening TSV row is unchanged versus `git show HEAD:app/data/cohort_cdf.tsv` (or a row-count/hash check in the plan's verification).

### Pitfall 3: Non-deterministic cohort cap with 2 points per user
**What goes wrong:** Two regens produce different TSVs.
**Why:** tie-break `(distance, user_id)` ties between a user's two colour rows.
**How to avoid:** include colour in the sort key (or rank by distinct users, Pattern 3).

### Pitfall 4: `LIMIT 1` in the per-user query
**What goes wrong:** Only one colour gets a row.
**Why:** `_compute_metric_for_user_per_tc` assumes one row per user.
**How to avoid:** a colour-aware fetch returning `dict[Color, tuple[float, int]]`.

### Pitfall 5: Definition drift from the benchmark measurement
**What goes wrong:** Peer CDF built with a different rule than the one the design note measured.
**Why:** easy to forget the early-ending rule, the excluded `unknown` termination, mate-by-sign, or that a NULL-eval MG entry is non-qualifying.
**How to avoid:** copy the `fetch_sweep.py` semantics (Pattern 1) and seed every edge case in the DB parity test. Note that a game can have no phase-1 ply only by ending in the opening (Divider drops the middlegame when the endgame fires first, but piece counts fall one capture per ply, so in practice the middlegame always comes first).

### Pitfall 6: ALTER TYPE ADD VALUE in a migration that also uses the value
**What goes wrong:** `unsafe use of new value` if the same transaction inserts or casts the new label.
**Why:** PG restriction on newly added enum values inside the adding transaction.
**How to avoid:** only add values (precedent migration does exactly that), or move to TEXT + CHECK.

### Pitfall 7: Migration filename matched by test globs
**What goes wrong:** `test_alembic_migrations.py` and `test_benchmark_metric_enum.py` glob `*user_benchmark_percentile*` and read `migration_files[0]` for the downgrade-ordering check.
**How to avoid:** do not put `user_benchmark_percentile` in the new migration's filename, or update the tests to target their intended file.

### Pitfall 8: Stale frontend cache
**What goes wrong:** Section shows "Analyzing…"/"Not ranked yet" until a hard refresh after Stage B.
**Why:** Endgames solved this by invalidating `['endgameOverview']` in `App.tsx::handleJobDone` and `Import.tsx` (interval + completion).
**How to avoid:** put the new query key under a prefix invalidated at those sites (add explicit `invalidateQueries` lines; do not overload `endgameOverview`).

### Pitfall 9: Sticky colour bar overlays the first heading
**What goes wrong:** Desktop White | Black switch overlaps or misaligns with the new section title.
**Why:** `StickyTcBar` takes no layout height and overlays the first section's heading row, which must be `lg:h-8` (`REPERTOIRE_HEADING_CLASS`). Today that is "Bookmarked Openings".
**How to avoid:** the new "Out of the opening" `h2` uses `REPERTOIRE_HEADING_CLASS` and sits first inside the `flex flex-col gap-6` wrapper; phones render the switch in the Filters row (`showOnMobile={false}`), so no change there.

### Pitfall 10: Inverted metric orientation
**What goes wrong:** A high worse rate reads green, or the gate direction check uses the oriented value.
**How to avoid:** gate on raw values and raw percentile; orient only the displayed percentile (Pattern 5 step 7); unit-test both colours and both rates.

### Pitfall 11: Long benchmark runs inside a subagent
**What goes wrong:** The executor dies mid-regen (memory: backgrounded executor runs die; SSE timeout on long DB plans).
**How to avoid:** run the regen (~10 min) from the orchestrator inline in the foreground or via `setsid nohup` + Monitor; commit code before the run.

## Code Examples

### Classification CTE (prototype run this session on dev and benchmark)
```sql
-- Source: prototype in scratchpad, semantics from .planning/sketches/013-out-of-the-opening/analysis/fetch_sweep.py
mg_entry AS (
  SELECT DISTINCT ON (gp.game_id) gp.game_id, gp.eval_cp, gp.eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id AND gp.user_id = rc.user_id
  WHERE gp.phase = 1
  ORDER BY gp.game_id, gp.ply
),
classified AS (
  SELECT rc.user_id, rc.user_color,
    CASE
      WHEN me.game_id IS NULL THEN
        CASE WHEN g.termination IN ('resignation','checkmate','timeout') AND g.result <> '1/2-1/2'
             THEN CASE WHEN (g.result = '1-0') = (rc.user_color = 'white') THEN 1 ELSE -1 END END
      WHEN me.eval_mate IS NOT NULL
        THEN sign(me.eval_mate) * (CASE WHEN rc.user_color = 'white' THEN 1 ELSE -1 END)
      WHEN me.eval_cp IS NOT NULL THEN
        CASE WHEN (me.eval_cp * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END))
                  - (CASE WHEN rc.user_color='white' THEN {baseline_cp} ELSE -{baseline_cp} END) <= -{cut_cp} THEN -1
             WHEN (me.eval_cp * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END))
                  - (CASE WHEN rc.user_color='white' THEN {baseline_cp} ELSE -{baseline_cp} END) >= {cut_cp} THEN 1
             ELSE 0 END
    END AS side
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  LEFT JOIN mg_entry me ON me.game_id = rc.id
),
per_user_colour_counts AS (
  SELECT user_id, user_color,
         count(side) AS n_games,
         count(*) FILTER (WHERE side = -1) AS worse_n,
         count(*) FILTER (WHERE side = 1)  AS better_n
  FROM classified GROUP BY user_id, user_color
)
```
`{baseline_cp}` = `round(EVAL_BASELINE_PAWNS_WHITE * 100)` = 25 and `{cut_cp}` = `round(OPENING_OUT_THRESHOLD_PAWNS * 100)` = 100, f-stringed from Python constants (int literals, no injection surface; same convention as `_SUB_800_FLOOR`). The sub-800 per-game drop (Pattern 1) adds `AND {ueag} >= {_SUB_800_FLOOR}` in `classified`. `count(side)` counts non-NULL only, which is exactly the qualifying-game count.

Measured: user 31 blitz on dev → `white | 1491 | 330 | 455`, `black | 1490 | 495 | 394`; ~180 ms warm. Benchmark cohort, rapid, snapshot 2026-05-30 → 91 s execution.

### Stage B colour-aware upsert (shape)
```python
# Source: pattern of user_benchmark_percentiles_service._compute_and_upsert_cell
STAGE_B_OPENING_FAMILIES: tuple[CdfMetricId, ...] = ("opening_worse_rate", "opening_better_rate")

for family, (tc, anchor) in itertools.product(STAGE_B_OPENING_FAMILIES, anchors.items()):
    await _compute_and_upsert_colour_cells(
        session, user_id=user_id, metric=family, tc=tc, anchor=anchor, cohort=cohort_b,
    )
# inside: one query → {"white": (value, n), "black": (value, n)}; per colour interpolate against
# cohort.get((family, round_anchor_to_grid(anchor.anchor_rating), tc)); upsert with color=...
# same CancelledError re-raise + Sentry set_context/capture as the existing helper.
```

### Gate (shape)
```python
# Source: app/services/score_confidence.py (wilson_bounds, ci_excludes), D-08
lo, hi = wilson_bounds(k / n, n, z=OPENING_INSIGHTS_CI_Z_95)
significant = ci_excludes(peer_median_weighted, lo, hi) and (
    (k / n > peer_median_weighted) == (headline_raw_percentile > MEDIAN_PERCENTILE)
)
```

### Frontend copy constants
```ts
// D-03: "eval", never "pawns". Sketch 013 labels and hints.
const LABEL_WORSE = 'Came out worse';
const LABEL_BETTER = 'Came out better';
const WHAT_WORSE = 'how often you leave the opening with an eval 1.0 or more below a typical opening position for your colour.';
const WHAT_BETTER = 'how often you leave the opening with an eval 1.0 or more above a typical opening position for your colour.';
const hintWorse = (p: number) => `Fewer worse games than ${p}% of peers`;
const hintBetter = (p: number) => `More better games than ${p}% of peers`;
```
Disclosures (D-12, memory "percentile chip tooltip disclosure"): peers are benchmarked lichess players, not FlawChess
users; ranked games only (rated, opponents within ±100, last 36 months, per time control); not affected by the page
filters; the rate depends strongly on rating, so peers are matched by rating per time control; the headline averages
the per-time-control percentiles weighted by games (do not call it a single percentile against a mixed group, D-07).
Footer: `k of n games`, `95% CI a% to b%`, peer typical range. No "Wilson", no p-values (copy minimalism).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat pooled CDF in source | Per (metric, anchor, TC) cohort CDF in `benchmark_cohort_cdf`, seeded from TSV | Phase 94.4 / 99.1 | New metrics = TSV rows + seed |
| Filter-applied chip value | Canonical-slice, filter-independent value | Phase 94.1 | D-12 filter-independence disclosure |
| Endgames 99% verdicts | Openings 95% verdicts | Phase 242 D-33 | This phase passes z = 1.96 |

**Deprecated:** the 12 TC-suffixed `benchmark_metric` labels (`conversion_rate_bullet` …) are unused by the write path (model comment, dev DB has 0 rows).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Apply the per-game sub-800 drop in the new builder | Pattern 1 | Small level shift vs the design note; low-rated users reach the floor later |
| A2 | Cohort MIN/MAX and `n_users` count distinct users, not colour points | Pattern 3 | Narrower/wider cohorts than intended; regen report semantics |
| A3 | TCs without a CDF cell (no percentile) drop out of headline and gate like below-floor TCs | Pattern 5 | Different headline for users at suppressed anchors (very high/low ratings, classical) |
| A4 | Footer peer band = game-weighted p25/p75 (approximate), exact bands per TC in the list | Pattern 5 | Copy may need rewording |
| A5 | Card status precedence when nothing contributes: pending > below_floor (max n of 30) > unranked | Pattern 5 | UX wording only |
| A6 | Pending rule: a TC with eval-pending games and no persisted row shows pending, not "Not ranked yet" | Pattern 5 | Mirrors Endgames intent; Endgames itself shows pending only when value is None |
| A7 | Prod has no rows on the 12 legacy TC-suffixed labels | Storage | If wrong, a CHECK-based migration fails at deploy (loudly) |
| A8 | Colour column over per-colour ids; ENUM→TEXT folded in | Storage | Planner may choose the fallback; both are workable |

## Open Questions

1. **Fold the ENUM→TEXT alignment in or defer it?**
   - Known: cost is one migration step + two test rewrites; tables are small.
   - Unclear: prod usage of legacy labels (A7).
   - Recommendation: fold in, with a prod `GROUP BY metric` check before deploy; otherwise document the deferral.
2. **Distinct-user vs point-based cohort caps (A2).** Recommendation: distinct users; record it in the regen report header.
3. **Backfill ownership.** The prod backfill needs the tunnel and an owner go-ahead. Recommendation: a human-action checkpoint after deploy: seed, then `-m scripts.archive.backfill_user_percentiles --target prod --skip-anchors`, then spot-check user 28.
4. **Per-eval-source check delivery.** "Report-only" can mean a deterministic unit test (identical classification across the three source flags for identical positions, which is a code-path check) plus an empirical report run against the benchmark/dev DB (SEED-206 measured < 1 pp). Recommendation: both; the empirical numbers go in the plan SUMMARY, not a pytest assertion.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (:5432) | tests, dev seed, on-read | ✓ | PostgreSQL 18.6 | — |
| Benchmark PostgreSQL (:5433, `flawchess_benchmark`) | CDF regen | ✓ (up, at Alembic head `5448f030de58`, 9,523 selected users, ~2.78M games, ~191M positions) | 18.x | — |
| uv | backend | ✓ | 0.10.9 | — |
| Node | frontend | ✓ | v24.19.0 | — |
| Prod DB MCP / tunnel | pre-deploy label check, backfill | not available to this agent | — | orchestrator/owner runs it |
| Flawchess DB MCP servers | optional probes | not exposed to this subagent | — | used `psql` read-only instead |

Missing with no fallback: none. Prod steps are owner/orchestrator actions.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend | pytest (asyncio), per-session cloned Postgres DB from a migrated template (`tests/conftest.py`) |
| Frontend | vitest ^5.0.5 (`npm test` = `vitest run`) |
| Quick run (backend) | `uv run pytest tests/services/test_canonical_slice_sql.py tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py tests/scripts/test_gen_global_percentile_cdf_unchanged.py -x` |
| Full suite | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Decision → Test Map
| ID | Behavior | Type | Automated Command | File Exists? |
|----|----------|------|-------------------|-------------|
| D-01/D-02 | Edge cases: MG eval at −0.75/−0.76 white and −1.25/−1.26 black (cut boundaries), +1.0 boundary, mate ±, `eval_mate = 0`, NULL eval at MG entry (non-qualifying), early end by resignation/checkmate/timeout win+loss, early draw, `abandoned`, `unknown`, out-of-slice games (37 months old, +150 opponent, unrated, computer) | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -x` | ❌ Wave 0 |
| D-05 | Builder body byte-identical across `source="benchmark"` / `"single_user"`; contains per-TC predicate; emits `user_color` | unit | `uv run pytest tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py -x` | ✅ extend |
| D-05 parity | Same seeded user via (a) CDF query path (`selected_users_cte("benchmark")` with `benchmark_selected_users` + completed `benchmark_ingest_checkpoints` rows), (b) Stage B persisted rows, (c) on-read counts → identical value and n per colour × TC | DB integration | `uv run pytest tests/services/test_opening_out_rates_parity.py -x` | ❌ Wave 0 |
| D-04 | Colour-aware cohort ranking deterministic (tie-break incl. colour), distinct-user MIN/MAX, 2 points per user | unit (synthetic rows) | `uv run pytest tests/scripts/test_gen_global_percentile_cdf_pooled.py -x` (or new file) | ✅ extend / ❌ |
| D-04 | Existing 44 golden SQL fixtures unchanged; 8 new goldens for the opening metrics | unit | `uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py -x` | ✅ extend |
| Regen scope | Merge mode rewrites only selected metrics; non-opening rows byte-identical; TSV round trip | unit | `uv run pytest tests/scripts/test_cohort_cdf_seed_artifact.py -x` | ✅ extend |
| Storage | Migration: color column + PK (and CHECK if folded in); enum/CHECK label set | DB integration | `uv run pytest tests/integration/test_alembic_migrations.py tests/integration/test_benchmark_metric_enum.py -x` | ✅ update |
| Repo | `upsert_percentile(color=…)`, `fetch_for_user` returns only `color='all'` rows (Endgames unaffected) | DB integration | `uv run pytest tests/repositories/test_user_benchmark_percentiles_repository.py -x` | ✅ extend |
| Stage B | Opening family writes up to 4 rows per anchored TC; endgame families untouched; per-cell Sentry isolation | unit + DB | `uv run pytest tests/services/test_user_benchmark_percentiles_service.py tests/services/test_endgame_ranked_parity.py -x` | ✅ extend (parity must still pass unchanged) |
| D-07/D-08 | Weights over contributing TCs; below-floor and no-cell TCs excluded; z = 1.96 used (a case significant at 95% but not 99%); direction guard; orientation (worse inverted) | unit (pure builder) | `uv run pytest tests/services/test_opening_out_stats_service.py -x` | ❌ Wave 0 |
| Rank status | below_floor (anchor and own floor, "n of 30"), pending, unranked, ranked; colour that passes renders while the other is below floor | unit | same file | ❌ Wave 0 |
| API | GET endpoint requires auth, uses `current_active_user.id`, ignores query params, response schema | router | `uv run pytest tests/routers/test_openings_out_of_opening.py -x` | ❌ Wave 0 |
| Eval source | Identical classification for identical positions under lichess / local-full / entry-lane flags (deterministic); empirical per-source difference report (not asserted) | DB unit + report | `uv run pytest tests/services/test_opening_out_rates_parity.py -k eval_source` | ❌ Wave 0 |
| UI | Card renders worse primary + better lesser; inverted hint text; red/green only when significant; below-floor/pending/unranked/error/loading states; testids | component | `cd frontend && npx vitest run src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx` | ❌ Wave 0 |
| D-09..D-12 | Popover: WHAT sentence, percentile words, all four disclosures incl. filter independence, per-TC list with below-floor TCs, "95% CI" footer, no chart | component | same dir, `OutOfOpeningPopover.test.tsx` | ❌ Wave 0 |
| Analytics | New popover testid maps to one stable target (no colour/TC split) | unit | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ extend |
| Cache | Import completion invalidates the new query key | component/unit | extend `src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts` pattern | ✅ pattern exists |

### Sampling Rate
- **Per task commit:** the quick run above plus the task's own new test file.
- **Per wave merge:** `uv run pytest -n auto -x`; frontend `npm test -- --run && npm run build`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green, plus a serial run of the touched DB test files (memory: serial CI catches isolation bugs that `-n auto` hides).

### Wave 0 Gaps
- [ ] `tests/services/test_opening_out_rates_parity.py` (seeded edge-case user; every non-guest `Game` insert cleaned up in `finally`, per the eval-lottery isolation memory; seed benchmark selection rows for the CDF path)
- [ ] `tests/services/test_opening_out_stats_service.py` (pure collapse/gate/status)
- [ ] `tests/routers/test_openings_out_of_opening.py`
- [ ] `tests/scripts/fixtures/global_percentile_cdf/opening_{worse,better}_rate__{bullet,blitz,rapid,classical}.sql`
- [ ] `frontend/src/components/openings/stats/__tests__/OutOfOpeningSection.test.tsx`, `OutOfOpeningPopover.test.tsx`

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (endpoint) | `current_active_user` (FastAPI-Users), as `/endgames/ranked-stats` |
| V3 Session Management | no change | existing |
| V4 Access Control | yes | `user_id` only from the authenticated user, never a query param (repository docstring "V4 Information Disclosure mitigation") |
| V5 Input Validation | minimal | endpoint takes no parameters; internal args are `Literal` (tc, side, colour) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via f-string builders | Tampering | f-string only `Literal` values and Python int constants; `user_id` via `CAST(:user_id AS int)` bindparam (module security note, `canonical_slice_sql.py:61-68`) |
| Cross-user data read | Information disclosure | auth-derived `user_id`; no id in the URL |
| DoS via heavy on-read SQL | Denial of service | ~0.2-0.6 s per TC; 4 TCs sequential on one session; consider sharing the 5-minute frontend staleTime pattern; no unbounded fan-out |

## Sources

### Primary (HIGH confidence, read or executed this session)
- `app/services/canonical_slice_sql.py`, `app/services/user_benchmark_percentiles_service.py`, `scripts/gen_global_percentile_cdf.py`, `scripts/seed_cohort_cdf.py`, `app/services/global_percentile_cdf.py`, `app/repositories/benchmark_cohort_cdf_repository.py`, `app/repositories/user_benchmark_percentiles_repository.py`, `app/services/endgame_ranked_service.py`, `app/schemas/endgames.py`, `app/services/score_confidence.py`, `app/services/opening_insights_constants.py`, `app/services/position_classifier.py`, `app/repositories/stats_repository.py`, `app/models/{game,game_position,user_benchmark_percentile,benchmark_cohort_cdf}.py`, migration `52c928794fe7`
- Tests: `test_endgame_ranked_parity.py`, `test_canonical_slice_per_user_vs_benchmark_parity.py`, `test_gen_global_percentile_cdf_unchanged.py`, `test_cohort_cdf_seed_artifact.py`, `test_alembic_migrations.py`, `test_benchmark_metric_enum.py`, `test_user_benchmark_percentiles_service.py`
- Frontend: `RankedMetricRow.tsx`, `PercentileBar.tsx`, `RankedMetricPopover.tsx`, `rankedMetrics.ts`, `types/endgames.ts`, `pages/openings/StatsTab.tsx`, `OpeningColorSwitch.tsx`, `headingClasses.ts`, `StickyTcBar.tsx`, `lib/analytics.ts`, `hooks/useEndgames.ts`, `App.tsx`, `pages/Import.tsx`
- Live probes: dev DB enum labels and row counts; EXPLAIN ANALYZE of the prototype on dev (user 7, user 31) and benchmark (rapid cohort, 91 s); `uv run alembic heads`; archived backfill `--help`
- Planning: SEED-206, `.planning/notes/out-of-the-opening-metric-design.md`, `.planning/notes/percentile-chip-canonical-slice.md`, `.planning/notes/eval-completion-columns.md`, sketch 013 README + Variant A + `analysis/fetch_sweep.py`, `reports/percentile/cohort-percentile-cdf-latest.md`

### Secondary / Tertiary
- None. No web sources were needed; no claims rest on training data except those listed in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (all in-repo, read this session)
- Architecture: HIGH for the pipeline shape and the coupling traps; MEDIUM for the discretion recommendations (storage, cohort counting, card status), which are flagged as assumptions
- Pitfalls: HIGH (each traced to a file/line or a live probe)

**Research date:** 2026-10-31
**Valid until:** 2026-11-30 (stable internal code; re-check if Phase 242 follow-ups or another percentile phase lands first)
