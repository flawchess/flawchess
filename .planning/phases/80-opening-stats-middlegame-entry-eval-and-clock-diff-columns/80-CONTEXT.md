# Phase 80: Opening stats — middlegame-entry eval and clock-diff columns - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the Openings → Stats subtab tables (bookmarked openings + most-played openings, both desktop and mobile) with three new per-row metrics that consume the Phase 79 middlegame-entry Stockfish evals:

1. **Avg eval at middlegame entry** — signed user-perspective (positive = user better, regardless of color), rendered as a `MiniBulletChart` with a 95% CI whisker overlay.
2. **Eval significance** — one-sample t-test of mean eval vs 0, surfaced as a low / medium / high confidence pill in its own column (mirrors the opening-insights cards).
3. **Avg clock diff at middlegame entry** — `+8.2% (+24s)` style, reusing the existing endgame clock-pressure formatter.

Together they answer "does this opening leave me better off in position and on the clock when the real fight starts?"

To make horizontal room for the new columns, the chess board (currently rendered above the Stats tables on desktop) is hidden on the Stats subtab — matching what mobile already does. The `MiniBulletChart` component is extended with optional `ciLow` / `ciHigh` props (additive, no behavior change when omitted).

</domain>

<decisions>
## Implementation Decisions

### Eval column (D-01..D-03)
- **D-01:** Render the avg eval as a `MiniBulletChart` (signed, user-perspective, in pawns). No separate `±std` text in the cell — spread information is conveyed by the CI whisker.
- **D-02:** Extend `MiniBulletChart` with optional `ciLow?` / `ciHigh?` props that draw a thin horizontal whisker with end caps over the value bar. When the props are omitted the component renders unchanged (so existing call sites in the Endgame Material Breakdown table are unaffected).
- **D-03:** Hide the chess board on the Openings → Stats subtab (desktop) to free horizontal space for the new columns. Mobile already collapses the board area, so this aligns the two layouts.

### Confidence column (D-04)
- **D-04:** Surface the t-test confidence as a separate column with a `low` / `medium` / `high` pill, mirroring the opening-insights card visual style. Reuse the same N≥10 gate and one-sided p-value thresholds (`p<0.05` → high, `p<0.10` → medium, else low) as `OPENING_INSIGHTS_CONFIDENCE_*` constants in `app/services/opening_insights_constants.py`. The statistical procedure is different (one-sample t-test on continuous eval vs trinomial Wald on WDL), so a new helper is needed; the threshold semantics carry over.

### Clock diff column (D-05)
- **D-05:** Render avg clock diff at middlegame entry as `+8.2% (+24s)` — pct of base time with absolute seconds in parentheses, signed. Reuse the same `formatSignedSeconds` / pct-of-base formatter used by `EndgameClockPressureSection` so the two clock-diff cells read identically across the app.

### Mobile layout (D-06)
- **D-06:** On mobile, each opening row becomes a small stacked card. The top line keeps the existing 3-col grid (name + games + WDL bar). A second line below stacks the three new metrics: bullet chart (with CI whisker) → confidence pill → clock diff. Everything visible without taps; no new collapse/expand behavior.

### Bullet chart zones (D-07)
- **D-07:** **Calibration deferred to research.** The researcher pulls the population distribution of avg-eval-at-middlegame-entry from the benchmark DB (per ELO / TC bucket if needed, via the `/benchmarks` skill) and proposes neutral-zone bounds + bar domain backed by that data. Avoids guessing magic numbers. Report neutral zone choice + collapse verdict (whether zones can be globally collapsed across TC/ELO via Cohen's d, like other benchmark-calibrated metrics).

### Claude's Discretion
- **Mate handling at middlegame entry.** Rare but possible (forced mate found at depth 15 right out of the opening). Sensible default: exclude `eval_mate IS NOT NULL` rows from the mean (eval is undefined as a continuous quantity for forced-mate positions); include them in `total` for the WDL counts (already counted there today). Researcher / planner can confirm with a quick benchmark-DB count of how many MG-entry rows have `eval_mate IS NOT NULL`.
- **Backend payload shape.** Extending the existing `OpeningWDL` schema with new optional fields (`avg_eval_pawns`, `eval_ci_low`, `eval_ci_high`, `eval_n`, `eval_p_value`, `eval_confidence`, `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n`) is the obvious shape — single round trip, single response model. Planner to confirm.
- **SQL aggregation pattern.** The middlegame-entry row per game is `MIN(ply)` filtered to `phase = 1`. Planner picks between (a) a window function `ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ply) WHERE phase = 1` or (b) a correlated subquery / `DISTINCT ON`. The endgame conv/recov code in `app/repositories/endgame_repository.py` has prior art for the same shape on endgame-entry — researcher should reference it.
- **Sortability of new columns.** Probably yes (eval value descending makes intuitive sense; clock diff descending too). Defer to planner if it complicates the existing table state.
- **Tooltip / column header info popovers.** Worthwhile so users understand what "eval at middlegame entry" means and why CI matters. Planner adds these following the pattern in `EndgameClockPressureSection.tsx` (lines 158-163 use `Tooltip` with explainer paragraphs).

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
- `.claude/skills/benchmarks/SKILL.md` — projects for pulling population distributions from the benchmark DB (per ELO / TC bucket) for neutral-zone calibration.
- `bin/benchmark_db.sh` — start/stop the benchmark DB locally before running benchmark queries.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MiniBulletChart` (frontend) — already used in Material Breakdown; extension with CI whisker is purely additive.
- `formatSignedSeconds` + pct-of-base formatter in `EndgameClockPressureSection.tsx` — copy-paste-or-extract for the clock-diff cell.
- `MinimapPopover` + `MiniWDLBar` (frontend) — keep on the row; only the standalone board above the table is hidden on Stats subtab.
- `OPENING_INSIGHTS_CONFIDENCE_*` constants — reuse the N + p-value thresholds for the t-test confidence helper.
- Color-flip helper in `endgame_service` — reuse to sign the eval to user-perspective.
- `OpeningWDL` schema in `app/schemas/stats.py` — extend with the new optional fields.

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

</specifics>

<deferred>
## Deferred Ideas

- **Tabled phase-aware analytics ideas** (`.planning/notes/phase-aware-analytics-ideas.md` §"Tabled for later") — Middlegame ELO, Opening ELO, "where do you bleed centipawns" decomposition, phase-conditional conv/recov, time-vs-phase correlation, phase-flip game search filter, opponent diff per phase, LLM narrative upgrade. None of these are in Phase 80 scope; they live in the v1.16 brainstorm pool for follow-on phases.
- **Phase 81: Endgame entry eval — twin-tile decomposition in Endgame Overall Performance.** Different page (Endgames, not Openings), different data subset (endgame-entry rows, not middlegame-entry). Independent of Phase 80; no shared components beyond `MiniBulletChart`.
- **Concept-explainer accordion update.** Phase 81 plans an "Avg eval at endgame entry" paragraph in its accordion. Phase 80 has no concept-explainer accordion on the Stats subtab today; if one is wanted later, it's a separate UX phase.

</deferred>

---

*Phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns*
*Context gathered: 2026-05-03*
