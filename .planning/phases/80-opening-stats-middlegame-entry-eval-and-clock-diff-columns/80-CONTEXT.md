# Phase 80: Opening stats — middlegame-entry eval and clock-diff columns - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the Openings → Stats subtab tables (bookmarked openings + most-played openings, both desktop and mobile) with new per-row metrics that consume Stockfish evals at phase transitions:

1. **Avg eval at middlegame entry (trimmed)** — signed user-perspective (positive = user better, regardless of color), rendered as a `MiniBulletChart` with a 95% CI whisker overlay. Outlier rows excluded (`|eval_cp| < 2000`) so a handful of decisive positions don't drag the mean.
2. **Eval significance at middlegame entry** — one-sample t-test of trimmed mean vs 0, surfaced as a low / medium / high confidence pill in its own column (mirrors the opening-insights cards).
3. **Avg clock diff at middlegame entry** — `+8.2% (+24s)` style, reusing the existing endgame clock-pressure formatter.
4. **Avg eval at endgame entry (trimmed)** — same machinery as (1), filtered to `phase = 2 AND MIN(ply)` per game. Answers "does this opening leave me ahead going into the endgame, after the middlegame plays out?"
5. **Eval significance at endgame entry** — same one-sample t-test on the endgame-entry trimmed mean, separate confidence pill.

Together they answer "does this opening leave me better off in position and on the clock entering the middlegame, and does that advantage carry into the endgame?"

To make horizontal room for the new columns, the chess board (currently rendered above the Stats tables on desktop) is hidden on the Stats subtab — matching what mobile already does. The `MiniBulletChart` component is extended with optional `ciLow` / `ciHigh` props (additive, no behavior change when omitted).

</domain>

<decisions>
## Implementation Decisions

### Eval column (D-01..D-03)
- **D-01:** Render the avg trimmed eval as a `MiniBulletChart` (signed, user-perspective, in pawns) for **both** middlegame entry and endgame entry. No separate `±std` text in the cell — spread information is conveyed by the CI whisker.
- **D-02:** Extend `MiniBulletChart` with optional `ciLow?` / `ciHigh?` props that draw a thin horizontal whisker with end caps over the value bar. When the props are omitted the component renders unchanged (so existing call sites in the Endgame Material Breakdown table are unaffected).
- **D-03:** Hide the chess board on the Openings → Stats subtab (desktop) to free horizontal space for the new columns. Mobile already collapses the board area, so this aligns the two layouts.

### Confidence column (D-04)
- **D-04:** Surface the t-test confidence as a separate column with a `low` / `medium` / `high` pill, mirroring the opening-insights card visual style. **One pill per phase** — middlegame-entry eval and endgame-entry eval each get their own column + pill, since the underlying samples differ (66% vs 99.99% coverage; different `eval_n`). Reuse the same N≥10 gate and one-sided p-value thresholds (`p<0.05` → high, `p<0.10` → medium, else low) as `OPENING_INSIGHTS_CONFIDENCE_*` constants in `app/services/opening_insights_constants.py`. The statistical procedure is different (one-sample t-test on continuous eval vs trinomial Wald on WDL), so a new helper is needed; the threshold semantics carry over.

### Clock diff column (D-05)
- **D-05:** Render avg clock diff at middlegame entry as `+8.2% (+24s)` — pct of base time with absolute seconds in parentheses, signed. Reuse the same `formatSignedSeconds` / pct-of-base formatter used by `EndgameClockPressureSection` so the two clock-diff cells read identically across the app.

### Mobile layout (D-06)
- **D-06:** On mobile, each opening row becomes a small stacked card. The top line keeps the existing 3-col grid (name + games + WDL bar). The new metrics stack on additional lines below (everything visible without taps; no new collapse/expand behavior):
  - **Line 2 — middlegame entry:** bullet chart (with CI whisker) + confidence pill + clock diff (3-col grid).
  - **Line 3 — endgame entry:** bullet chart (with CI whisker) + confidence pill (2-col grid; clock diff slot empty since there is no endgame-entry clock-diff in this phase).
  - Each line is prefixed by a small label (`MG entry` / `EG entry`) so the two phases are distinguishable at a glance. Planner picks the exact label rendering (could be a tiny left-aligned tag or a column-header analog).

### Bullet chart zones (D-07)
- **D-07:** **Calibrated from `reports/benchmarks-2026-05-03.md` §3.** Single global zone for both metrics (Cohen's d on TC and ELO axes both ≤ 0.41 — review band, single zone defensible).
  - **Middlegame-entry bullet:** neutral zone `[-0.20, +0.20]` pawns; chart domain `±1.50` pawns. (Bench §3 line 407-408: pooled p25/p75 = -21.8/+22.0 cp, p05/p95 = -112/+60.)
  - **Endgame-entry bullet:** neutral zone `[-0.35, +0.35]` pawns; chart domain `±3.50` pawns. (Bench §3 line 462-466: pooled p25/p75 = -31.0/+41.0 cp, p05/p95 = -338/+239.)
  - Both zones are symmetric and rounded for legibility; symmetry recommendation comes from the bench report directly.

### Outlier trimming (D-08)
- **D-08:** Trim per-row evals with `|eval_cp| >= 2000` (≥ ±20 pawns) from the eval mean and from `eval_n`. Decisive positions are statistically uninformative for "typical opening character" and a handful drag the mean. Mate rows (`eval_mate IS NOT NULL`) are excluded as before. Apply identically to both middlegame-entry and endgame-entry aggregations.

### Endgame-entry eval column (D-09)
- **D-09:** Add a parallel column to the Openings → Stats tables for the avg eval at endgame entry, using the exact same machinery as the middlegame-entry eval column (bullet chart with CI whisker + significance pill). Filter is `phase = 2 AND MIN(ply)` per game (the endgame-entry row, populated by Phase 79 — bench §3 line 353 confirms 99.99% coverage). No clock-diff at endgame entry needed; the existing Endgame page already has that.
- Schema additions parallel the MG-entry set: `avg_eval_endgame_entry_pawns`, `eval_endgame_ci_low_pawns`, `eval_endgame_ci_high_pawns`, `eval_endgame_n`, `eval_endgame_p_value`, `eval_endgame_confidence`.

### Coverage caveat (D-10)
- **D-10:** Per bench §3 line 350-355, middlegame-entry eval has **66.38% coverage** (Lichess analysis gap), while endgame-entry eval has **99.99% coverage**. The MG-entry column header tooltip MUST phrase the metric as "your typical eval at the start of the middlegame **across analyzed games**" until the gap closes. Endgame-entry column header has no analogous caveat. Adrian is currently working on closing the MG eval gap; until then, the tooltip wording is mandatory.

### Claude's Discretion
- **Mate handling at phase entry.** Rare but possible (forced mate found at depth 15 right out of the opening, or near a forced sequence at endgame entry). Sensible default: exclude `eval_mate IS NOT NULL` rows from the mean (eval is undefined as a continuous quantity for forced-mate positions); include them in `total` for the WDL counts (already counted there today). Apply to both MG-entry and endgame-entry aggregations.
- **Backend payload shape.** Extending the existing `OpeningWDL` schema with new optional fields:
  - MG-entry set: `avg_eval_pawns`, `eval_ci_low_pawns`, `eval_ci_high_pawns`, `eval_n`, `eval_p_value`, `eval_confidence`, `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n`.
  - Endgame-entry set: `avg_eval_endgame_entry_pawns`, `eval_endgame_ci_low_pawns`, `eval_endgame_ci_high_pawns`, `eval_endgame_n`, `eval_endgame_p_value`, `eval_endgame_confidence`.
  - Single round trip, single response model. Planner to confirm.
- **SQL aggregation pattern.** The phase-entry row per game is `MIN(ply)` filtered to the phase. Aggregate both phases in one pass (`phase IN (1, 2)`) using `FILTER (WHERE phase = 1)` / `FILTER (WHERE phase = 2)` clauses to avoid scanning the table twice. The endgame conv/recov code in `app/repositories/endgame_repository.py` has prior art for the same `MIN(ply)` shape.
- **Sortability of new columns.** Probably yes (eval value descending makes intuitive sense; clock diff descending too). Defer to planner if it complicates the existing table state. With four new columns total (MG-eval, MG-confidence, MG-clock-diff, EG-eval, EG-confidence) — five sortable cells per row — planner picks which are sortable.
- **Tooltip / column header info popovers.** Mandatory for D-10 coverage caveat. The MG-entry column header tooltip MUST clarify "across analyzed games" wording. Endgame-entry header tooltip explains the phase-2 filter without coverage caveat. Pattern: `EndgameClockPressureSection.tsx` lines 158-163 (`Tooltip` with explainer paragraphs).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase brainstorm and design notes
- `.planning/notes/phase-aware-analytics-ideas.md` §"Active focus — Opening Success" — original brainstorm; defines the three columns and the framing.
- `.planning/ROADMAP.md` Phase 80 entry — confirmed scope, data source (`phase = 1` AND `MIN(ply)`), eval orientation (color-flip user-perspective), 10-game minimum threshold reuse.

### Statistical helpers and thresholds
- `app/services/opening_insights_constants.py` — `OPENING_INSIGHTS_CONFIDENCE_MIN_N = 10`, `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P = 0.05`, `OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P = 0.10`. Reuse these numeric thresholds for the new one-sample t-test confidence helper.
- `app/services/score_confidence.py` (referenced via `compute_confidence_bucket`) — pattern to mirror for the new helper (different stat procedure, same low/medium/high output shape). Path inferred from `app/services/opening_insights_service.py:41`; verify during research.

### SQL pattern references
- `app/repositories/endgame_repository.py` — clock-diff-at-endgame-entry SQL is the pattern to mirror for clock-diff-at-middlegame-entry. Same idea (read user clock and opponent clock at the entry row, average the diff), different `WHERE` filter.
- `app/services/endgame_service.py` `_classify_endgame_bucket` — color-flip helper for converting raw `eval_cp` to user-perspective. Same helper applies here verbatim.

### Frontend reuse
- `frontend/src/components/charts/MiniBulletChart.tsx` — to be extended with optional `ciLow?` / `ciHigh?` props.
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` lines 240-265, 336-342, 377-377, 428 — clock diff formatter (`formatSignedSeconds` + pct-of-base), tooltip pattern, mobile card pattern.
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — current row structure (3-col grid) and mobile minimap behavior; the file gets the new columns and the mobile second-line treatment.
- `frontend/src/types/stats.ts` — `OpeningWDL` interface to extend with the new fields.

### Schema / migration
- Phase 79 deliverables: `game_positions.phase` SmallInteger (0=opening, 1=middlegame, 2=endgame), `eval_cp` / `eval_mate` populated on middlegame-entry rows. No new migration in this phase — purely a downstream consumer.

### Calibration data
- `reports/benchmarks-2026-05-03.md` §3 (lines 337-473) — **authoritative calibration source** for D-07 zone bounds and chart domain on both phase-entry eval columns. Cites pooled p25/p75 + p05/p95 across 1,731 (MG) / 1,773 (EG) users; collapse verdicts on TC and ELO axes; coverage caveat that drives D-10.
- `.claude/skills/benchmarks/SKILL.md` — generator script if recalibration is needed (e.g. after MG eval backfill closes the 66% coverage gap).
- `bin/benchmark_db.sh` — start/stop the benchmark DB locally before running benchmark queries.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MiniBulletChart` (frontend) — already used in Material Breakdown; extension with CI whisker is purely additive. The same primitive renders both the MG-entry and endgame-entry bullet cells with different `domain` / `neutralMin` / `neutralMax` props.
- `formatSignedSeconds` + pct-of-base formatter in `EndgameClockPressureSection.tsx` — copy-paste-or-extract for the clock-diff cell.
- `MinimapPopover` + `MiniWDLBar` (frontend) — keep on the row; only the standalone board above the table is hidden on Stats subtab.
- `OPENING_INSIGHTS_CONFIDENCE_*` constants — reuse the N + p-value thresholds for the t-test confidence helper. Same helper used for both phase-entry confidence pills.
- Color-flip helper in `endgame_service` — reuse to sign the eval to user-perspective. Applies to both phase-entry rows.
- `OpeningWDL` schema in `app/schemas/stats.py` — extend with two parallel sets of optional fields (MG-entry + endgame-entry).

### Established Patterns
- Confidence pill UI (low/medium/high) is already established in `OpeningFindingCard` and friends from v1.14. Pattern: small badge with bg-color + text-color from theme, mute the value when `confidence === "low"`.
- Tooltip-on-column-header explainer pattern: see `EndgameClockPressureSection.tsx` lines 158-163.
- Per-row aggregation over filtered games already exists in the openings stats path — the new metrics are additional `SELECT` columns on the same `GROUP BY opening_hash` query (or a `LEFT JOIN` to a subquery on `phase = 1` MIN(ply) rows). Planner picks the cheaper shape.

### Integration Points
- Backend: `app/repositories/openings_repository.py` (or wherever `MostPlayedOpenings` is computed today) — add the new aggregations.
- Backend: `app/services/stats_service.py` — wire the new fields through the response builder.
- Backend: `app/schemas/stats.py` — extend `OpeningWDL`.
- Frontend: `frontend/src/types/stats.ts` mirrors backend schema additions.
- Frontend: `MostPlayedOpeningsTable.tsx` gets new column cells (desktop) and a stacked second-line block (mobile).
- Frontend: `Openings.tsx` Stats subtab — hide the board container on this subtab (analogous to current mobile behavior).
- Bookmarked openings table: same component family — applies once the schema and repository changes land.

</code_context>

<specifics>
## Specific Ideas

- "I think a bullet chart like we have already in the Endgame Metrics table would be best. Maybe we can extend the component to support plotting a 95% CI." — drives D-01 / D-02.
- "I would hide the chess board in the Openings → Stats table (like we already do on mobile), to make horizontal space in the opening tables." — drives D-03.
- Confidence pill should match the opening-insights cards (Phase 75 / 76 visual language) — drives D-04.
- Clock diff should mirror the existing `EndgameClockPressureSection` formatting so the two cells look identical across the app — drives D-05.
- "Add an additional column to the opening tables, which contains the median stockfish eval at the transition to the endgame" — drives D-09 (note: implementation uses trimmed mean per D-08, not median — the user accepted this simpler approach when complexity was flagged).
- "Make sure for the transition to the middlegame eval, we also take the median (robust against eval outliers)" — original framing; D-08 implements the same robustness intent via outlier trimming (`|eval_cp| < 2000`) without switching the statistical machinery.

</specifics>

<deferred>
## Deferred Ideas

- **Tabled phase-aware analytics ideas** (`.planning/notes/phase-aware-analytics-ideas.md` §"Tabled for later") — Middlegame ELO, Opening ELO, "where do you bleed centipawns" decomposition, phase-conditional conv/recov, time-vs-phase correlation, phase-flip game search filter, opponent diff per phase, LLM narrative upgrade. None of these are in Phase 80 scope; they live in the v1.16 brainstorm pool for follow-on phases.
- **Phase 81: Endgame entry eval — twin-tile decomposition in Endgame Overall Performance.** Different page (Endgames, not Openings), different decomposition (twin-tile in Overall Performance section vs per-opening row in this phase). Phase 80 surfaces the endgame-entry eval **per opening** in the Openings → Stats table (D-09); Phase 81 surfaces it as a single global twin-tile on the Endgame page. Same underlying data (`phase = 2 AND MIN(ply)`), different aggregation. No conflict — Phase 81 should reuse the `eval_confidence` helper, the bullet whisker prop, and the endgame-entry zone constants landed here.
- **Concept-explainer accordion update.** Phase 81 plans an "Avg eval at endgame entry" paragraph in its accordion. Phase 80 has no concept-explainer accordion on the Stats subtab today; if one is wanted later, it's a separate UX phase.

</deferred>

---

*Phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns*
*Context gathered: 2026-05-03*
