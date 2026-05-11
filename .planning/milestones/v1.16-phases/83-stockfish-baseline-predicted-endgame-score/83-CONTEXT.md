# Phase 83: Stockfish-baseline predicted endgame score - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a Stockfish-baseline **achievable score** to the Endgame Overall Performance area so users can read "what a 2300+ player would score from positions like mine" against their **achieved** Endgame score in the same W+0.5D units.

Per-game endgame-entry `eval_cp` is converted to an expected score in [0, 1] via the Lichess winning-chances sigmoid (`1 / (1 + e^(-0.00368208 * cp))`); mate scores map directly to 0/1 (not via the sigmoid). The cohort is filtered identically to Phase 82's `entry_eval_mean_pawns` (mate inclusion differs — see D-06). Per-user aggregation uses the project's existing Wilson chess-score util sig-tested against 50% (the equal-footing null), exactly mirroring the existing `endgame_score_p_value` plumbing.

UI: the existing `EndgameStartVsEndSection` twin-tile section restructures into a 2×2 grid:

| Tile / row | Top row | Bottom row |
|---|---|---|
| "Where you start" | Endgame entry eval (centipawns, ±2.0 pawn axis, existing) | **Achievable score** (W+0.5D axis, NEW) |
| "What you do with it" | **Win / Draw / Loss** (MiniWDLBar, NEW — duplicated from "Games with vs without Endgame" table below) | Endgame score (W+0.5D axis, existing) |

The bottom row of both tiles shares the same W+0.5D axis and cohort-band styling so the **achievable-vs-achieved gap is directly readable across the two tiles**. The existing "Games with vs without Endgame" table is left **unchanged** below (D-08); some visual redundancy on the WDL is accepted.

All Phase 81 / Phase 82 conventions carry forward: sample-size gate ≥10 games, `|eval_cp| < 2000` clip, sign convention from `_classify_endgame_bucket`, `(zone != neutral) AND p < 0.05` tile-color rule, no `verdict` field in the LLM payload.

The phase ships 5 plans (3 core + 2 optional that the user has elected to include in-phase):

1. `app/services/eval_utils.py` — Lichess sigmoid + mate→0/1 helpers + unit tests
2. Per-game expected-score plumbing in `endgame_repository.py` / `endgame_service.py` + new `entry_expected_score*` schema fields + Wilson test
3. 2×2 UI restructure of `EndgameStartVsEndSection` (new "Achievable score" bullet + duplicated `MiniWDLBar` in "What you do with it")
4. Extend `/benchmarks` SKILL.md with an `entry_expected_score` section, lock cohort bands into `endgame_zones.py`, regenerate `endgameZones.ts`
5. Glossary entry + subsection guidance in `app/prompts/endgame_insights.md` + `_PROMPT_VERSION` bump (`endgame_v24` → `endgame_v25`)

</domain>

<decisions>
## Implementation Decisions

### Plan Scope (LOCKED — user override on seed default)

- **D-01:** Ship **all 5 plans in-phase**: 3 core (sigmoid util + per-game plumbing + UI restructure) plus the seed's two "optional" plans (Plan 4 = formal `/benchmarks` calibration; Plan 5 = LLM prompt awareness). Reasoning: the LLM should narrate the new metric from day one (same logic as Phase 82 D-13 — tile and LLM agree on what is narratable from launch), and the cohort band on the new bullet must come from a formal calibration so it stays consistent with Phase 82's bands. Seed framed Plans 4-5 as splittable; user elected to include both.

### Lichess Sigmoid Conversion (LOCKED — from seed)

- **D-02:** New module `app/services/eval_utils.py` with one constant and two pure functions (no business logic):
  - `LICHESS_K = 0.00368208` (Lichess accuracy / winning-chances doc — extract as a named module-level constant, no magic numbers).
  - `eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float` — sign-flips per `user_color` (mirroring `_classify_endgame_bucket` in `app/services/endgame_service.py:170-204`), returns `1 / (1 + exp(-LICHESS_K * user_eval_cp))`. Domain: signed centipawns. Range: (0, 1), centered at 0.5 when user_eval_cp = 0.
  - `eval_mate_to_expected_score(eval_mate: int, user_color: Literal["white", "black"]) -> float` — returns `1.0` if user is the side mating, `0.0` otherwise. Mate is **not** routed through the sigmoid (a mate-in-3 with `|eval_cp| ≈ 2900` would map to ~0.999, not 1.0).
- **D-03:** Unit tests in `tests/services/test_eval_utils.py` cover: sigmoid centred at 0.5 (eval_cp=0), sign convention for both colors (a +100 cp eval is 0.59 for white-as-user and 0.41 for black-as-user), saturation at large evals, mate-for-user → 1.0, mate-against-user → 0.0. Module is pure (no I/O, no DB) — unit tests, not integration.

### Per-Game Cohort Metric (LOCKED — from seed)

- **D-04:** Mirror the existing `entry_eval_mean_pawns` plumbing in `app/repositories/endgame_repository.py:793-841` and `app/services/endgame_service.py:1670-1712`. Per endgame game in the cohort: compute one expected score (sigmoid for `eval_cp`, 0/1 for `eval_mate`), de-dupe over multi-class entry rows identically to entry-eval. Aggregate per user: mean per-game expected score + n.
- **D-05:** Sig test: project Wilson chess-score util (the same path that produces `endgame_score_p_value`), tested against 50%. Outputs: `entry_expected_score`, `entry_expected_score_n`, `entry_expected_score_p_value`, `entry_expected_score_ci_low`, `entry_expected_score_ci_high` on `EndgamePerformanceResponse`. Do not editorialize methodology in the schema docstrings (memory: `feedback_wilson_chess_score.md`).
- **D-06:** Cohort filter — `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`. Mate games are **included** (mate has a defined expected score: 0 or 1) — this differs from the Phase 81 entry-eval cohort, which excluded mate because mate has no centipawn value to average. Document the n in the response so the bullet chart's "based on N games" footer matches what users see.
- **D-07:** `|eval_cp| < 2000` clip is **applied for consistency** with Phase 82's "what counts as an analyzable endgame entry" cohort definition, even though the sigmoid saturates around ±800 cp anyway. Mate handling above takes care of true forced mates separately.

### UI: 2×2 Grid Restructure (LOCKED)

- **D-08 (WDL chart placement — discussed):** Add a `MiniWDLBar` (endgame-only) to the top of the "What you do with it" tile. **Keep the existing "Games with vs without Endgame" table unchanged below** — the endgame-only WDL appears in two places (some visual redundancy is accepted). Rejected alternative: restructuring the existing table to lift the endgame row out — would break the table's endgame-vs-non-endgame comparison and the symmetric Score Gap column it anchors. Rejected alternative: skipping the top-row WDL — would lose the 2×2 grid symmetry that makes the achievable-vs-achieved gap directly readable.
- **D-09 (new bullet label — discussed):** New bullet chart inside "Where you start" is labelled **"Achievable score"**. Rejected alternatives: "Stockfish baseline" (too sterile, doesn't convey reachability), "Predicted score" (implies prescription, exactly the bias the framing wants to avoid for sub-2300 players), "Ceiling score" (unusual chess-UI phrasing). "Achievable" implies "reachable in principle" — the popover (D-10) qualifies that hitting it requires 2300+ play.
- **D-10 (popover framing — discussed):** Popover on the "Achievable score" bullet explicitly states **"Expected for sub-2300 play to fall below"**: "This is what a 2300+ rated player would score from your endgame-entry positions, via the Lichess winning-chances sigmoid. The Lichess curve is fitted on 2300+ rapid games — scoring below this baseline from positive evals is normal at lower ratings and is not a flaw. Compare against your achieved Endgame score on the right." Do NOT use the word "underperformance" anywhere in user-facing copy.
- **D-11 (bullet-chart visuals):** The new "Achievable score" bullet reuses the existing `MiniBulletChart` component, the W+0.5D axis (`[0, 1]`, center at 0.5), and the project's score-zone Wilson-test colouring. Tile-color rule is `(zone != neutral) AND p < 0.05` — identical to Phase 82 D-12 for the existing Endgame score bullet. Borderline cases (e.g., `achievable=0.62, p<0.001` inside neutral band) read as neutral on the tile AND are not narrated by the LLM (consistency with Phase 82 D-14).
- **D-12 (component changes):** All changes localized to `frontend/src/components/charts/EndgameStartVsEndSection.tsx`. New tile interior layout: each tile becomes a 2-row stack (no nested grid needed — the existing tile container is the cell). Mobile stacking: same order as desktop (top row first, bottom row second) so the "compare bottom row" affordance survives the responsive collapse. The existing `lg:grid-cols-2` outer grid stays — only the tile interior changes.
- **D-13 (component reuse):** Top-row chart in "What you do with it" reuses `MiniWDLBar` from `frontend/src/components/charts/EndgamePerformanceSection.tsx` (already used in the "Games with vs without Endgame" table). Lift the import; do NOT reimplement. Input: `data.endgame_wdl.{win_pct, draw_pct, loss_pct}` — same shape that powers the existing table row.

### Cohort Band Source (LOCKED — Plan 4 calibration)

- **D-14:** New `entry_expected_score` cohort band comes from **formal `/benchmarks` calibration** (Plan 4 in scope), not from a v1 shortcut. Reasoning: consistency with the Phase 82 `entry_eval_pawns` band (which came from `/benchmarks-2026-05-10.md` §3) matters more than the half-day saved by pooling in-prod or hand-picking from sigmoid math. Plan 4 produces a new `reports/benchmarks-YYYY-MM-DD.md` section with the pooled distribution, TC × ELO cells, Cohen's d collapse verdict, and recommended bands. Bands lock into `app/services/endgame_zones.py` as `ENTRY_EXPECTED_SCORE_ZONES = ZoneSpec(...)` with `direction="higher_is_better"`.
- **D-15:** Apply the same editorial-judgement principle as Phase 82 D-08 (memory: `feedback_zone_band_judgement.md`): if the IQR is too wide for the metric to ever land in green/red zones, tighten inside IQR so meaningful patterns surface. Decision is deferred to Plan 4 execution time when the benchmark data is on the table.
- **D-16:** Regenerate `frontend/src/generated/endgameZones.ts` via `scripts/gen_endgame_zones_ts.py` so the frontend zone helper picks up the new band without hand-coding. CI fails on drift.

### LLM Prompt Awareness (LOCKED — Plan 5)

- **D-17:** Add new `MetricId = "entry_expected_score"` to `app/services/insights_service.py` Literal slot. New glossary entry in `app/prompts/endgame_insights.md` `## Metric glossary` defines: signed Stockfish-baseline expected score in W+0.5D units, derivation (Lichess sigmoid + mate→0/1), the "2300+ baseline / sub-2300 normally falls below" framing (D-10), cohort band from Plan 4, sig-test framing the tile uses (and that the LLM does NOT receive the sig-test outcome — narrates strictly by zone, per Phase 82 D-06).
- **D-18:** Extend the existing `### Subsection: endgame_start_vs_end` block in `endgame_insights.md` (added in Phase 82) with `entry_expected_score` guidance: the LLM should narrate **the gap between `entry_expected_score` and `endgame_score`** as the headline diagnostic, with `entry_eval_pawns` as the explanatory unit (signed pawns are more intuitive than a 0-1 score; both convey the same information). Example narrations: "Stockfish-baseline says positions like yours score 58%, but you scored 47% — about 11 points below the engine ceiling, mostly explained by entering at +0.4 pawns" / "Achievable 49%, you scored 52% — defended slightly better than the engine baseline from these positions". Do NOT use "underperformance" framing for sub-2300 users; the gap is rating-tilt by default, narrate it descriptively.
- **D-19:** Findings emitter `_findings_endgame_start_vs_end` (added in Phase 82) gains a third `SubsectionFinding` for `entry_expected_score` — same shape as the existing two (metric, zone, value, sample_quality, is_headline_eligible). Sample-size gate `entry_expected_score_n >= 10` matches D-17 of Phase 82. No `verdict` field (Phase 82 D-06).
- **D-20:** Bump `_PROMPT_VERSION` from `endgame_v24` → **`endgame_v25`** with a one-line changelog entry: "v25 (YYMMDD entry_expected_score): wire Stockfish-baseline achievable score (Lichess sigmoid) into the endgame_start_vs_end subsection alongside entry_eval_pawns and endgame_score. New `ENTRY_EXPECTED_SCORE_ZONES` from /benchmarks-YYYY-MM-DD.md. LLM narrates the achievable-vs-achieved gap as the headline diagnostic with entry_eval_pawns as the explanatory unit."

### Schema Naming (LOCKED — from seed)

- **D-21:** New schema field key is `entry_expected_score` (parallel to `entry_eval_mean_pawns`). `endgame_score` is already taken by Phase 81 for the achieved score. Companion fields: `entry_expected_score_n`, `entry_expected_score_p_value`, `entry_expected_score_ci_low`, `entry_expected_score_ci_high`. All default to safe empty values (`0.0` / `0` / `None`) per Phase 81 D-11's "Pitfall 7" pattern so existing call sites keep working.

### Methodology — Two CIs, Not Paired Test (LOCKED — from seed)

- **D-22:** The new metric is technically paired with `endgame_score` (each game contributes both an achievable score and a {0, 0.5, 1} actual). Two independent Wilson CIs slightly understate the precision of the **gap**. For a single-sentence verdict you'd want a paired test. For the **visual juxtaposition** (which is the actual UX goal — users compare bands across the bottom row of the 2×2), two CIs is the right call. Don't editorialize the paired-test asymmetry in user-facing copy or in the LLM glossary; just ship the two bullet charts.

### Claude's Discretion

- Final wording inside the popover paragraph (D-10): polish during implementation. The user-facing wording can iterate on PR review.
- Final ordering of the LLM narration when entry_eval / achievable / endgame_score all fire in the same response (D-18): lead with the gap when it is the dominant signal, lead with entry_eval when entry_eval is the dominant signal. Decide during prompt-write.
- Exact placement of the new MiniWDLBar legend / aria-label inside the "What you do with it" tile (D-13): match the surrounding tile-1 conventions; specifics in Plan 3 execution.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Seed and Direct Predecessors
- `.planning/seeds/SEED-014-stockfish-baseline-vs-achieved-endgame-score.md` — comprehensive design doc with all the locked decisions, edge cases, and methodology lessons inherited from Phase 82. Source of truth for D-02..D-07, D-21, D-22.
- `.planning/phases/82-llm-prompt-awareness-of-endgame-start-vs-end-metrics/82-CONTEXT.md` — Phase 82's locked decisions D-01..D-25, especially D-06 (no `verdict` field on `SubsectionFinding`), D-08 (cohort-band editorial tightening), D-12/D-13/D-14 (tile-color rule + LLM agreement), D-17 (≥10 sample-size gate), D-22..D-25 (prompt block structure to extend).
- `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/81-CONTEXT.md` — Phase 81's twin-tile section design (D-05 sample-size gate, D-09 sig-test gate amendment, D-11 schema defaults pattern, D-15 axis-domain decisions, D-16 score-bullet shared band).

### Benchmark / Population Data
- `.claude/skills/benchmarks/SKILL.md` — `/benchmarks` calibration skill. Plan 4 extends this with an `entry_expected_score` section. The canonical CTE (lichess_username join, `bic.status='completed'`, equal-footing `|opp_rating - user_rating| <= 100`, sparse-cell exclusion) must be copied verbatim — see SEED-014 "Methodology Lessons" + the bug-fix memory `project_benchmark_outliers_unfiltered.md`.
- `reports/benchmarks-2026-05-10.md` §3 — population reference for the existing `entry_eval_pawns` band; Plan 4 should produce an analogous section for `entry_expected_score` and lock the bands in the same format.

### Source Files (read for patterns and integration points)
- `app/services/endgame_service.py:170-204` — `_classify_endgame_bucket` shows the canonical sign-flip pattern for user-perspective eval; Plan 1 must mirror it.
- `app/services/endgame_service.py:1670-1712` — entry-eval aggregation pattern; Plan 2 mirrors this for expected-score.
- `app/repositories/endgame_repository.py:793-841` — the SQL path that builds the per-game endgame-entry cohort. Plan 2 extends this query (or adds a sibling) to select `(eval_cp, eval_mate, user_color)` per endgame game.
- `app/schemas/endgames.py:107-140` — `EndgamePerformanceResponse` schema where new `entry_expected_score*` fields land.
- `app/services/endgame_zones.py` → `frontend/src/generated/endgameZones.ts` — zone registry + frontend regen via `scripts/gen_endgame_zones_ts.py`.
- `app/services/insights_service.py` `_findings_endgame_start_vs_end` — Phase 82 emitter; Plan 5 adds a third finding here.
- `app/prompts/endgame_insights.md` — glossary + `### Subsection: endgame_start_vs_end` block; Plan 5 extends both.
- `app/services/insights_llm.py` — `_PROMPT_VERSION` constant; Plan 5 bumps to `endgame_v25`.
- `frontend/src/components/charts/EndgameStartVsEndSection.tsx` — the twin-tile section that restructures into a 2×2 grid in Plan 3.
- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — source of `MiniWDLBar` lifted into the "What you do with it" tile (D-13).
- `frontend/src/lib/scoreBulletConfig.ts` — `SCORE_BULLET_CENTER`, `scoreBulletDomain`, `scoreZoneColor` (the existing endgame_score bullet uses these). The new "Achievable score" bullet uses the same axis but its own zone helper (`entryExpectedScoreZoneColor`) generated from `endgameZones.ts`.
- `frontend/src/lib/theme.ts` — `ZONE_SUCCESS`, `ZONE_DANGER`, `ZONE_NEUTRAL` constants for the new bullet's coloring.

### Domain References (Lichess sigmoid math)
- Lichess accuracy / winning-chances doc — sigmoid `1 / (1 + e^(-0.00368208 * cp))`, scaling constant `K = 0.00368208`. Cite in the docstring of `LICHESS_K` in `eval_utils.py` so the constant is auditable.

### Memory / Conventions
- `feedback_wilson_chess_score.md` — chess-score sig tests use the project's existing Wilson-based util; don't editorialize methodology in schema docstrings or LLM glossary.
- `feedback_zone_band_judgement.md` — editorial judgement may tighten cohort bands inside IQR so meaningful patterns surface (Plan 4).
- `feedback_llm_significance_signal.md` — don't add a separate sig-test signal to the LLM payload; tighten the cohort band instead (Phase 82 D-06 precedent — applies here too).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MiniBulletChart` (`frontend/src/components/charts/MiniBulletChart.tsx`) — existing component. Reuse for the new "Achievable score" bullet; same axis as the existing Endgame score bullet (W+0.5D, center 0.5).
- `MiniWDLBar` (in `EndgamePerformanceSection.tsx`) — lift import for D-13. No reimplementation.
- Project Wilson chess-score util (the same path that already produces `endgame_score_p_value` in `endgame_service.py`) — reuse for `entry_expected_score_p_value`. Do not introduce a parallel statistical machinery.
- `_classify_endgame_bucket` sign-flip pattern (`endgame_service.py:170-204`) — Plan 1 mirrors the sign convention exactly.
- `ZoneSpec` + `assign_zone` machinery in `endgame_zones.py` — Plan 4 registers `ENTRY_EXPECTED_SCORE_ZONES` here.
- `scripts/gen_endgame_zones_ts.py` — frontend zone regen pipeline. CI checks for drift.

### Established Patterns
- **Single source of truth for cohort bands**: bands live in `endgame_zones.py` Python registry; frontend zone helpers come from regenerated `endgameZones.ts`. Plan 4 must follow this pattern, not hand-code thresholds on the frontend.
- **`MetricId` Literal + glossary entry + subsection guidance**: every metric the LLM narrates needs a Literal slot in `insights_service.py`, a glossary entry in `endgame_insights.md`, and (if it's part of an existing subsection) inclusion in that subsection's prompt block. Plan 5 follows this triad.
- **No `verdict` field on `SubsectionFinding`** (Phase 82 D-06): the LLM narrates strictly by zone. Sig-test outcome stays on the backend for tile coloring only. Do not propagate sig signals to the LLM payload — tighten the band instead if narration is too noisy/quiet (memory: `feedback_llm_significance_signal.md`).
- **Tile-color rule `(zone != neutral) AND p < 0.05`** (Phase 81 D-09 / Phase 82 D-12): the existing `EndgameStartVsEndSection.tsx` already implements this via `isConfident(level) && isInColoredZone`. The new "Achievable score" bullet reuses the same gate with its own `level` (derived from `entry_expected_score_p_value`) and `zoneHex` (derived from `entryExpectedScoreZoneColor`).
- **Schema defaults pattern** (Phase 81 D-11): new fields on `EndgamePerformanceResponse` default to safe empty values so existing call sites (tests, prior callers) keep working without explicit updates.
- **Mobile stacking order**: same as desktop. Phase 81 D-17 set the chronological "setup → execution" order via DOM order; Phase 83's tile-interior stacks maintain that by putting eval / WDL on top and score-axis bullets on bottom.

### Integration Points
- Backend: `EndgamePerformanceResponse` (`app/schemas/endgames.py`) gets 5 new fields. The aggregation lives in `endgame_service.py` next to the existing entry-eval aggregator (`_aggregate_entry_eval` or similar — see line ~1670). The SQL query in `endgame_repository.py:793-841` already SELECTs `eval_cp` and `eval_mate` — Plan 2 may not even need a new query, just a new aggregator over the same cursor.
- Frontend: `EndgameStartVsEndSection.tsx` is the only frontend file that materially changes for the UI. Tests in `EndgameStartVsEndSection.test.tsx` and `Endgames.startVsEnd.test.tsx` need to be extended for the new bullet + the new top-row WDL.
- LLM: `insights_service.py` `_findings_endgame_start_vs_end` emitter gains a third finding. `endgame_insights.md` glossary + subsection block extend. `insights_llm.py` `_PROMPT_VERSION` bumps.
- Calibration: `/benchmarks` skill (`.claude/skills/benchmarks/SKILL.md`) gains a new metric section. `endgame_zones.py` gains `ENTRY_EXPECTED_SCORE_ZONES`. Frontend `endgameZones.ts` regenerates.

</code_context>

<specifics>
## Specific Ideas

- User-facing label: **"Achievable score"** (D-09) — user-chosen on 2026-05-11. Pairs with the popover framing "Expected for sub-2300 play to fall below" (D-10) to convey "this is reachable in principle, but only by 2300+ play" without ever using the word "underperformance".
- WDL placement: **duplicate the MiniWDLBar** (D-08) into the top of "What you do with it" tile, keep the "Games with vs without Endgame" table intact below. Visual redundancy on the endgame WDL is acceptable; preserving the table's endgame-vs-non-endgame comparison + Score Gap column matters more.
- All 5 plans land in-phase (D-01) — Plan 4 (`/benchmarks` calibration) and Plan 5 (LLM prompt awareness) are NOT split off, despite the seed framing them as optional / splittable. Same logic as Phase 82 D-13: tile and LLM should agree from day one, and cohort bands should come from formal calibration to stay consistent.
- Mate handling differs from Phase 82 entry-eval cohort: mate games are **included** here (D-06) because mate has a defined expected score (0 or 1). Phase 82's entry-eval excluded mate because mate has no centipawn to average.

</specifics>

<deferred>
## Deferred Ideas

- **Per-eval-bin breakdown** ("you score below baseline specifically when entering at +1.0…+2.0"): more diagnostic than the per-game aggregate but a much bigger UI lift and inconsistent with the existing bullet-chart idiom. Not in scope; possible future Endgame Insights v2 milestone.
- **Paired sig test of the gap** (achievable vs achieved): more statistically precise than two independent Wilson CIs but UX value is marginal — the visual juxtaposition of two bullet charts is the actual UX goal (D-22). Defer indefinitely.
- **Openings-side expected score**: end-of-opening evals cluster around 0 cp, so the sigmoid emits ~0.50 nearly everywhere. Eyeball-cost without signal. Out of scope — see SEED-014 "Why not Openings".
- **Per-ELO `ENTRY_EXPECTED_SCORE_ZONES`** mirroring Phase 82 D-11's deferred per-ELO `ENDGAME_SCORE_ZONES`: defer along the same lines. Open if a later iteration shows pooled-band false-typical readings hurt narration for high-rated cohorts.
- **WDL-in-table consolidation**: if the duplication of endgame WDL (top of tile + table row) starts to feel redundant in practice, revisit a follow-up phase to restructure the "Games with vs without Endgame" table (e.g., make it non-endgame-only + a gap indicator). Not in scope here.

</deferred>

---

*Phase: 83-stockfish-baseline-predicted-endgame-score*
*Context gathered: 2026-05-11*
